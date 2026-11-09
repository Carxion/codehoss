import Editor, { type OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { useCallback, useEffect, useRef, useState } from "react";
import { navigate } from "../App";
import { api, type Lesson, type Step, type StepProgress, type TestResult } from "../api";
import { DOCUMENT_URI, PythonLanguageClient } from "../lsp";
import { registerSnippets } from "../snippets";
import { useRunner } from "../useRunner";
import Console from "./Console";
import LibraryExplorer from "./LibraryExplorer";
import Markdown from "./Markdown";

interface Props {
  moduleId: string;
  lessonSlug: string;
  stepIndex: number;
}

type Feedback =
  | { kind: "pass" | "fail"; message: string }
  | { kind: "results"; passed: boolean; timedOut: boolean; results: TestResult[] };

const PLAYGROUND = "# Your playground: try things out here, then press Run.\n";
const BLANK_PROGRESS: StepProgress = { done: false, attempts: 0, hints_used: 0, showed_solution: false };

export default function LessonView({ moduleId, lessonSlug, stepIndex }: Props) {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loadError, setLoadError] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState("");
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({});
  const [hints, setHints] = useState<Record<number, string[]>>({});
  const [busy, setBusy] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [showingSolution, setShowingSolution] = useState(false);
  const [editorReady, setEditorReady] = useState(false);

  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const lspRef = useRef<PythonLanguageClient | null>(null);
  const savedCode = useRef<string>("");
  const animation = useRef<number | null>(null);
  const runner = useRunner(sessionId);

  const index = lesson ? Math.min(Math.max(stepIndex, 0), lesson.steps.length - 1) : 0;
  const step: Step | undefined = lesson?.steps[index];
  const progress = (i: number) => lesson?.progress[String(i)] ?? BLANK_PROGRESS;

  // --- loading -----------------------------------------------------------------

  useEffect(() => {
    api.lesson(moduleId, lessonSlug).then(setLesson, (e) => setLoadError(e.message));
  }, [moduleId, lessonSlug]);

  useEffect(() => {
    api.session(moduleId).then(
      (s) => setSessionId(s.session_id),
      (e) => setSessionError(e.message),
    );
  }, [moduleId]);

  useEffect(() => {
    if (!sessionId || !editorReady || !monacoRef.current || !editorRef.current) return;
    const client = new PythonLanguageClient(
      sessionId,
      monacoRef.current,
      editorRef.current.getModel()!,
    );
    lspRef.current = client;
    if (step) client.focusNames = focusNamesFor(step);
    return () => {
      client.dispose();
      lspRef.current = null;
    };
    // The language server lives as long as the session and editor; steps don't restart it.
  }, [sessionId, editorReady]);

  const markDone = useCallback((i: number) => {
    setLesson((previous) =>
      previous && {
        ...previous,
        progress: {
          ...previous.progress,
          [String(i)]: { ...(previous.progress[String(i)] ?? BLANK_PROGRESS), done: true },
        },
      },
    );
  }, []);

  // Entering a step: load its code, reset output, record that explanations were read.
  useEffect(() => {
    if (!lesson || !step || !editorReady || !editorRef.current) return;
    stopAnimation();
    setShowingSolution(false);
    editorRef.current.updateOptions({ readOnly: false });
    const fallback = defaultCode(step);
    const code = loadDraft(draftKey(moduleId, lessonSlug, step)) ?? fallback;
    if (code !== null && code !== editorRef.current.getValue()) editorRef.current.setValue(code);
    if (code === null && !editorRef.current.getValue()) editorRef.current.setValue(PLAYGROUND);
    runner.clear();
    if (lspRef.current) lspRef.current.focusNames = focusNamesFor(step);
    if ((step.type === "explain" || step.type === "example") && !progress(index).done) {
      api.viewed(moduleId, lessonSlug, index).then(() => markDone(index), () => {});
    }
  }, [lesson?.slug, index, editorReady]);

  useEffect(() => () => stopAnimation(), []);

  // --- editor ------------------------------------------------------------------

  const runRef = useRef<() => void>(() => {});
  runRef.current = () => {
    if (!runner.running && editorRef.current) runner.run(editorRef.current.getValue());
  };

  const onMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    const snippets = registerSnippets(monaco);
    editor.onDidDispose(() => snippets.dispose());
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => runRef.current());
    setEditorReady(true);
  };

  function onChange(value: string | undefined) {
    if (!step || showingSolution || value === undefined) return;
    saveDraft(draftKey(moduleId, lessonSlug, step), value);
  }

  function goToLine(line: number) {
    const editor = editorRef.current;
    if (!editor) return;
    editor.revealLineInCenter(line);
    editor.setSelection({ startLineNumber: line, startColumn: 1, endLineNumber: line, endColumn: 1000 });
    editor.focus();
  }

  function insert(text: string, importModule: string | null) {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (!editor || !model) return;
    const selection = editor.getSelection()!;
    editor.executeEdits("library", [{ range: selection, text, forceMoveMarkers: true }]);
    if (text.endsWith("()")) {
      const position = editor.getPosition()!;
      editor.setPosition({ lineNumber: position.lineNumber, column: position.column - 1 });
    }
    if (importModule && !new RegExp(`^\\s*import\\s+${importModule}\\b`, "m").test(model.getValue())) {
      editor.executeEdits("library", [
        { range: { startLineNumber: 1, startColumn: 1, endLineNumber: 1, endColumn: 1 }, text: `import ${importModule}\n` },
      ]);
    }
    editor.focus();
  }

  function resetCode() {
    if (!step || !editorRef.current) return;
    clearDraft(draftKey(moduleId, lessonSlug, step));
    editorRef.current.setValue(defaultCode(step) ?? PLAYGROUND);
  }

  // --- actions -----------------------------------------------------------------

  async function check() {
    if (!step || !sessionId || !editorRef.current) return;
    const code = editorRef.current.getValue();
    setBusy(true);
    try {
      if (step.type === "try-it") {
        const result = await api.tryIt(sessionId, lessonSlug, index, code);
        setFeedback((f) => ({
          ...f,
          [index]: result.passed
            ? { kind: "pass", message: "That's right!" }
            : { kind: "fail", message: result.message || "Not quite yet. Try again, or ask for a hint." },
        }));
        if (result.passed) markDone(index);
      } else if (step.type === "exercise") {
        const result = await api.check(sessionId, step.exercise.id, code);
        setFeedback((f) => ({
          ...f,
          [index]: { kind: "results", passed: result.passed, timedOut: result.timed_out, results: result.results },
        }));
        if (result.passed) markDone(index);
      }
    } catch (e) {
      setFeedback((f) => ({ ...f, [index]: { kind: "fail", message: (e as Error).message } }));
    } finally {
      setBusy(false);
    }
  }

  async function nextHint() {
    if (!step) return;
    const level = (hints[index]?.length ?? 0) + 1;
    try {
      const result = await api.hint(moduleId, lessonSlug, index, level);
      if ("hint" in result) {
        setHints((h) => ({ ...h, [index]: [...(h[index] ?? []), result.hint] }));
      } else {
        showSolution(result.solution);
      }
    } catch (e) {
      setFeedback((f) => ({ ...f, [index]: { kind: "fail", message: (e as Error).message } }));
    }
  }

  // "Show me": type the solution out in a read-only editor, then hand control back.
  function showSolution(solution: string) {
    const editor = editorRef.current;
    if (!editor) return;
    savedCode.current = editor.getValue();
    setShowingSolution(true);
    editor.updateOptions({ readOnly: true });
    const chunk = Math.max(1, Math.ceil(solution.length / 80));
    let shown = 0;
    stopAnimation();
    animation.current = window.setInterval(() => {
      shown = Math.min(solution.length, shown + chunk);
      editor.setValue(solution.slice(0, shown));
      if (shown >= solution.length) stopAnimation();
    }, 20);
  }

  function backToMyCode() {
    stopAnimation();
    editorRef.current?.updateOptions({ readOnly: false });
    editorRef.current?.setValue(savedCode.current);
    setShowingSolution(false);
  }

  function stopAnimation() {
    if (animation.current !== null) window.clearInterval(animation.current);
    animation.current = null;
  }

  async function answer(option: number) {
    if (!step) return;
    const result = await api.answer(moduleId, lessonSlug, index, option);
    setFeedback((f) => ({
      ...f,
      [index]: result.correct
        ? { kind: "pass", message: result.explanation || "Correct!" }
        : { kind: "fail", message: "Not quite. Have another look and try again." },
    }));
    if (result.correct) markDone(index);
  }

  const go = (i: number) => navigate(`/learn/${moduleId}/${lessonSlug}/${i}`);

  // --- render ------------------------------------------------------------------

  if (loadError) return <main className="page"><p className="error-text">{loadError}</p></main>;
  if (!lesson || !step) return <main className="page muted">Loading lesson…</main>;

  const checkable = step.type === "try-it" || step.type === "exercise";
  const hintCount = step.type === "try-it" ? step.hint_count : step.type === "exercise" ? step.exercise.hint_count : 0;
  const hintsShown = hints[index]?.length ?? 0;
  const isLast = index === lesson.steps.length - 1;
  const done = progress(index).done;

  return (
    <div className={`lesson-layout ${showLibrary ? "with-library" : ""}`}>
      <section className="lesson-panel">
        <div className="lesson-head">
          <a href="#/" className="small">← All lessons</a>
          <h1>{lesson.title}</h1>
          <nav className="step-dots" aria-label="Lesson steps">
            {lesson.steps.map((s, i) => (
              <button
                key={i}
                className={`dot ${i === index ? "current" : ""} ${progress(i).done ? "done" : ""}`}
                onClick={() => go(i)}
                title={`Step ${i + 1}: ${STEP_LABEL[s.type]}`}
                aria-label={`Step ${i + 1}: ${STEP_LABEL[s.type]}${progress(i).done ? " (done)" : ""}`}
                aria-current={i === index ? "step" : undefined}
              />
            ))}
          </nav>
        </div>

        <div className="step-body">
          <p className="step-kind">
            Step {index + 1} of {lesson.steps.length} · {STEP_LABEL[step.type]}
          </p>
          <StepContent step={step} feedback={feedback[index]} onAnswer={answer} />

          {hints[index]?.map((hint, i) => (
            <div key={i} className="hint">
              <strong>Hint {i + 1}</strong>
              <Markdown>{hint}</Markdown>
            </div>
          ))}
          {feedback[index] && step.type !== "quiz" && <FeedbackView feedback={feedback[index]} />}
        </div>

        <div className="step-nav">
          <button onClick={() => go(index - 1)} disabled={index === 0}>
            ← Back
          </button>
          {isLast ? (
            lesson.next ? (
              <a className={`button ${done ? "primary" : ""}`} href={`#/learn/${moduleId}/${lesson.next}/0`}>
                Next lesson →
              </a>
            ) : (
              <a className="button primary" href="#/">Finish 🎉</a>
            )
          ) : (
            <button className={done || !checkable ? "primary" : ""} onClick={() => go(index + 1)}>
              {done || !checkable ? "Next →" : "Skip for now →"}
            </button>
          )}
        </div>
      </section>

      <section className="workspace">
        <div className="toolbar">
          <button className="primary" onClick={() => runRef.current()} disabled={!sessionId || runner.running}>
            ▶ Run
          </button>
          {checkable && (
            <button className="success" onClick={check} disabled={!sessionId || busy || showingSolution}>
              {busy ? "Checking…" : "✓ Check"}
            </button>
          )}
          {checkable && (
            <button onClick={nextHint} disabled={showingSolution}>
              {hintsShown < hintCount ? `💡 Hint (${hintsShown}/${hintCount})` : "👀 Show me"}
            </button>
          )}
          <button onClick={resetCode} disabled={showingSolution} title="Go back to the starting code">
            ↺ Reset
          </button>
          <span className="spacer" />
          <button onClick={() => setShowLibrary(!showLibrary)} aria-pressed={showLibrary}>
            📚 Library
          </button>
        </div>
        {sessionError && (
          <div className="banner error">
            Can't reach your sandbox: {sessionError}. Lessons still work, but Run and Check are off.
          </div>
        )}
        {showingSolution && (
          <div className="banner info">
            <span>This is one way to solve it. Read it through, then try writing it yourself.</span>
            <button className="small" onClick={backToMyCode}>
              Back to my code
            </button>
          </div>
        )}
        <div className="editor-wrap">
          <Editor
            path={DOCUMENT_URI}
            defaultLanguage="python"
            theme={prefersDark() ? "vs-dark" : "vs"}
            onMount={onMount}
            onChange={onChange}
            options={{
              fontSize: 15,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              tabSize: 4,
              insertSpaces: true,
              automaticLayout: true,
              quickSuggestions: { other: true, comments: false, strings: false },
              suggestOnTriggerCharacters: true,
              parameterHints: { enabled: true },
              wordBasedSuggestions: "off",
              fixedOverflowWidgets: true,
            }}
          />
        </div>
        <Console
          output={runner.output}
          running={runner.running}
          exit={runner.exit}
          onInput={runner.sendInput}
          onStop={runner.stop}
          onGoToLine={goToLine}
        />
      </section>

      {showLibrary && (
        <LibraryExplorer moduleId={moduleId} onInsert={insert} onClose={() => setShowLibrary(false)} />
      )}
    </div>
  );
}

const STEP_LABEL: Record<Step["type"], string> = {
  explain: "Read",
  example: "Example",
  "try-it": "Try it",
  exercise: "Exercise",
  quiz: "Quiz",
};

function StepContent({
  step,
  feedback,
  onAnswer,
}: {
  step: Step;
  feedback: Feedback | undefined;
  onAnswer: (option: number) => void;
}) {
  switch (step.type) {
    case "explain":
      return <Markdown>{step.md}</Markdown>;
    case "example":
      return (
        <>
          {step.md && <Markdown>{step.md}</Markdown>}
          <p className="muted small">The example is in the editor. Press Run to see what it does, then change it and run it again.</p>
        </>
      );
    case "try-it":
      return (
        <>
          <Markdown>{step.prompt}</Markdown>
          <p className="muted small">Edit the code in the editor, then press ✓ Check.</p>
        </>
      );
    case "exercise":
      return (
        <>
          <h2>
            {step.exercise.title} <span className="stars">{"★".repeat(step.exercise.difficulty)}</span>
          </h2>
          <Markdown>{step.exercise.prompt}</Markdown>
          <details className="visible-tests">
            <summary>See an example test</summary>
            <pre>{step.exercise.visible_tests}</pre>
          </details>
        </>
      );
    case "quiz":
      return (
        <>
          <Markdown>{step.question}</Markdown>
          <div className="quiz-options">
            {step.options.map((option, i) => (
              <button key={i} className="quiz-option" onClick={() => onAnswer(i)}>
                <code>{option}</code>
              </button>
            ))}
          </div>
          {feedback && <FeedbackView feedback={feedback} />}
        </>
      );
  }
}

function FeedbackView({ feedback }: { feedback: Feedback }) {
  if (feedback.kind !== "results") {
    return (
      <div className={`feedback feedback-line ${feedback.kind}`} role="status">
        <strong className="feedback-icon">{feedback.kind === "pass" ? "✓" : "✗"}</strong>
        <Markdown>{feedback.message}</Markdown>
      </div>
    );
  }
  if (feedback.timedOut) {
    return <div className="feedback fail">Your program took too long. Is there a loop that never ends?</div>;
  }
  return (
    <div className={`feedback ${feedback.passed ? "pass" : "fail"}`} role="status">
      <strong>
        {feedback.passed
          ? `✓ All ${feedback.results.length} tests passed. Nice work!`
          : `${feedback.results.filter((r) => r.outcome === "passed").length} of ${feedback.results.length} tests passed`}
      </strong>
      <ul className="results">
        {feedback.results.map((r) => (
          <li key={r.name} className={r.outcome === "passed" ? "ok" : "bad"}>
            <span>{r.outcome === "passed" ? "✓" : "✗"}</span>
            <div>
              {r.label}
              {r.outcome !== "passed" && <Markdown>{r.explanation || r.message}</Markdown>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function defaultCode(step: Step): string | null {
  switch (step.type) {
    case "example":
      return step.code;
    case "try-it":
      return step.starter;
    case "exercise":
      return step.exercise.starter;
    default:
      return null; // reading and quiz steps keep whatever is in the editor
  }
}

/** Identifiers mentioned in `backticks` in the step text: the things this step teaches. */
function focusNamesFor(step: Step): Set<string> {
  const text =
    step.type === "explain" ? step.md
    : step.type === "example" ? step.md
    : step.type === "try-it" ? step.prompt
    : step.type === "exercise" ? step.exercise.prompt
    : step.question;
  const names = new Set<string>();
  for (const [, inner] of text.matchAll(/`([^`]+)`/g)) {
    for (const [name] of inner.matchAll(/[A-Za-z_]\w*/g)) names.add(name);
  }
  return names;
}

function draftKey(moduleId: string, lessonSlug: string, step: Step) {
  return defaultCode(step) === null
    ? `dojo:draft:${moduleId}/playground`
    : `dojo:draft:${moduleId}/${lessonSlug}/${step.index}`;
}

// Drafts are a per-browser convenience; storage can be unavailable (private mode etc.).
function loadDraft(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function saveDraft(key: string, code: string) {
  try {
    localStorage.setItem(key, code);
  } catch {
    /* ignore */
  }
}

function clearDraft(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

function prefersDark() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}
