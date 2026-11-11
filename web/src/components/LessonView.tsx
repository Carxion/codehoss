import { useCallback, useEffect, useRef, useState } from "react";
import { navigate } from "../App";
import { api, progressApi, reviewPath, type Lesson, type Level, type Step, type StepProgress, type TestResult } from "../api";
import { useAI } from "../aiContext";
import { loadMonaco } from "../monacoSetup";
import type { WorkspaceHandle } from "../workspace";
import EditorWorkspace from "./EditorWorkspace";
import LibraryExplorer from "./LibraryExplorer";
import Markdown from "./Markdown";
import NotebookWorkspace from "./NotebookWorkspace";
import LabWorkspace, { type LabHandle } from "./LabWorkspace";
import ShowcaseView from "../showcase/ShowcaseView";
import TutorPanel from "./TutorPanel";

interface Props {
  moduleId: string;
  lessonSlug: string;
  stepIndex: number;
  /** Review mode: the step again from its starter, answered from memory (spaced review). */
  review?: boolean;
}

type Feedback =
  | { kind: "pass" | "fail"; message: string }
  | { kind: "results"; passed: boolean; timedOut: boolean; results: TestResult[] };

const PLAYGROUND = "# Your playground: try things out here, then press Run.\n";
const LANGUAGE_NAMES: Record<string, string> = {
  python: "Python",
  pseudo: "Pseudocode",
  javascript: "JavaScript",
  r: "R",
  cpp: "C++",
  csharp: "C#",
};
const BLANK_PROGRESS: StepProgress = { done: false, attempts: 0, hints_used: 0, showed_solution: false };

export default function LessonView({ moduleId, lessonSlug, stepIndex, review = false }: Props) {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loadError, setLoadError] = useState("");
  const [glossary, setGlossary] = useState<Record<string, string>>({});
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState("");
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({});
  const [hints, setHints] = useState<Record<number, string[]>>({});
  const [checking, setChecking] = useState(false);
  const [running, setRunning] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [showTutor, setShowTutor] = useState(false);
  const [tutorQuestion, setTutorQuestion] = useState<string | null>(null);
  const [showingSolution, setShowingSolution] = useState(false);
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const [monacoLoaded, setMonacoLoaded] = useState(false);

  const workspace = useRef<WorkspaceHandle | null>(null);
  const labRef = useRef<LabHandle | null>(null);
  const [labSolutions, setLabSolutions] = useState<Record<number, { commands: string; files: Record<string, string> }>>({});
  const ai = useAI();
  const savedCode = useRef("");

  const index = lesson ? Math.min(Math.max(stepIndex, 0), lesson.steps.length - 1) : 0;
  const level: Level | null = lesson?.project?.level ?? null;
  /** The learner's passing code from the checkpoint before this one, if any. */
  const previousSubmission = (i: number): string | null => {
    if (!lesson) return null;
    for (let j = i - 1; j >= 0; j--) {
      const s = lesson.steps[j];
      if (s.type === "exercise") return s.exercise.submission ?? null;
    }
    return null;
  };
  const startingCode = (s: Step, forLevel: Level | null = level): string | null => {
    if (s.type === "exercise" && forLevel && s.exercise.starters) {
      if (forLevel === "solo") return previousSubmission(s.index) ?? s.exercise.starters.solo ?? s.exercise.starter;
      return s.exercise.starters[forLevel] ?? s.exercise.starter;
    }
    return defaultCode(s);
  };
  const step: Step | undefined = lesson?.steps[index];
  const progress = (i: number) => lesson?.progress[String(i)] ?? BLANK_PROGRESS;
  const notebook = lesson?.view === "notebook";
  const isLab = lesson?.view === "lab";
  const pseudo = lesson?.language === "pseudo";

  // --- loading -----------------------------------------------------------------

  useEffect(() => {
    api.lesson(moduleId, lessonSlug).then(setLesson, (e) => setLoadError(e.message));
    api.glossary(moduleId).then(setGlossary, () => setGlossary({}));
  }, [moduleId, lessonSlug]);

  useEffect(() => {
    loadMonaco().then(() => setMonacoLoaded(true));
  }, []);

  useEffect(() => {
    api.session(moduleId).then(
      (s) => setSessionId(s.session_id),
      (e) => setSessionError(e.message),
    );
  }, [moduleId]);

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

  // Entering a step: load its code, reset outputs, record that explanations were read.
  useEffect(() => {
    const ws = workspace.current;
    if (!lesson || !step) return;
    // Labs keep their files in the session (LabWorkspace loads them), not in drafts.
    if (!isLab) {
      if (!workspaceReady || !ws) return;
      if (showingSolution) setShowingSolution(false);
      const fallback = startingCode(step);
      // In review the step starts fresh: last time's answer would give it away.
      const code = (review ? null : loadDraft(draftKey(moduleId, lessonSlug, step))) ?? fallback;
      if (code !== null) ws.restore(code);
      else if (!ws.getCode().trim()) ws.restore(notebook ? "" : PLAYGROUND);
      ws.reset();
      ws.setFocusNames(focusNamesFor(step));
    }
    if ((step.type === "explain" || step.type === "example" || step.type === "showcase") && !progress(index).done) {
      api.viewed(moduleId, lessonSlug, index).then(() => markDone(index), () => {});
    }
    // Only when the step changes; not on every progress update.
  }, [lesson?.slug, index, workspaceReady]);

  const onCodeChange = useCallback(
    (code: string) => {
      if (!step || showingSolution || review) return;
      saveDraft(draftKey(moduleId, lessonSlug, step), code);
    },
    [step, showingSolution, moduleId, lessonSlug, review],
  );
  const onReady = useCallback(() => setWorkspaceReady(true), []);

  // --- actions -----------------------------------------------------------------

  async function resetLab(engine: boolean) {
    const question = engine
      ? "Remove everything you've made in this lab: containers, networks, volumes and Kubernetes objects? (Images stay.) Your files are put back to the starter too."
      : "Put this exercise's files back to how they started? Your changes will be lost.";
    if (!window.confirm(question)) return;
    try {
      await labRef.current?.reset(engine);
    } catch (e) {
      setFeedback((f) => ({ ...f, [index]: { kind: "fail", message: (e as Error).message } }));
    }
  }

  function resetCode() {
    if (!step || !workspace.current) return;
    clearDraft(draftKey(moduleId, lessonSlug, step));
    workspace.current.restore(startingCode(step) ?? (notebook ? "" : PLAYGROUND));
  }

  async function changeLevel(next: Level) {
    if (!lesson?.project || next === lesson.project.level) return;
    await api.setLevel(moduleId, lessonSlug, next);
    setLesson((l) => l && l.project && { ...l, project: { ...l.project, level: next } });
    // Swap in the new level's starter, but never over code the learner has written.
    if (step && !showingSolution && workspace.current && loadDraft(draftKey(moduleId, lessonSlug, step)) === null) {
      const code = startingCode(step, next);
      if (code !== null) workspace.current.restore(code);
    }
  }

  function useMyPreviousCode() {
    const code = previousSubmission(index);
    if (code && workspace.current) workspace.current.restore(code);
  }

  async function check() {
    if (!step || !sessionId || (!isLab && !workspace.current)) return;
    if (isLab) await labRef.current?.saveAll();
    const code = isLab ? "" : workspace.current!.getCode();
    setChecking(true);
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
        if (result.passed && isLab) markDone(index);
        else if (result.passed) {
          markDone(index);
          // The next checkpoint can carry this code forward (Solo / "use my code").
          setLesson((l) => l && {
            ...l,
            steps: l.steps.map((s) =>
              s.index === index && s.type === "exercise" ? { ...s, exercise: { ...s.exercise, submission: code } } : s,
            ),
          });
        }
      }
    } catch (e) {
      setFeedback((f) => ({ ...f, [index]: { kind: "fail", message: (e as Error).message } }));
    } finally {
      setChecking(false);
    }
  }

  async function nextHint() {
    if (!step || (!isLab && !workspace.current)) return;
    const level = (hints[index]?.length ?? 0) + 1;
    try {
      const result = await api.hint(moduleId, lessonSlug, index, level);
      if ("hint" in result) {
        setHints((h) => ({ ...h, [index]: [...(h[index] ?? []), result.hint] }));
      } else if (isLab) {
        // A lab's answer is files plus commands: shown beside the lesson, nothing overwritten.
        setLabSolutions((s) => ({ ...s, [index]: { commands: result.solution, files: result.solution_files ?? {} } }));
      } else if (workspace.current) {
        savedCode.current = workspace.current.getCode();
        setShowingSolution(true);
        workspace.current.showSolution(result.solution);
      }
    } catch (e) {
      setFeedback((f) => ({ ...f, [index]: { kind: "fail", message: (e as Error).message } }));
    }
  }

  function backToMyCode() {
    workspace.current?.restore(savedCode.current);
    setShowingSolution(false);
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

  async function nextReview() {
    const due = await progressApi.reviews().catch(() => []);
    navigate(due.length ? reviewPath(due[0]) : "/review");
  }

  function openTutor(question: string | null = null) {
    setShowLibrary(false);
    setShowTutor(true);
    setTutorQuestion(question);
  }

  /** What the tutor sees, gathered when the learner sends a question. */
  const tutorContext = () => ({
    module_id: moduleId,
    lesson: lessonSlug,
    step: index,
    code: isLab || showingSolution ? (isLab ? "" : savedCode.current) : (workspace.current?.getCode() ?? ""),
    session_id: sessionId,
    feedback: feedbackForTutor(feedback[index]),
  });

  // --- render ------------------------------------------------------------------

  if (loadError) return <main className="page"><p className="error-text">{loadError}</p></main>;
  if (!lesson || !step) return <main className="page muted">Loading lesson…</main>;

  const checkable = step.type === "try-it" || step.type === "exercise";
  const hintCount = step.type === "try-it" ? step.hint_count : step.type === "exercise" ? step.exercise.hint_count : 0;
  const hintsShown = hints[index]?.length ?? 0;
  const isLast = index === lesson.steps.length - 1;
  const done = progress(index).done;
  const Workspace = notebook ? NotebookWorkspace : EditorWorkspace;
  const tutorAllowed = level !== "solo";
  const passed = feedback[index] !== undefined && (feedback[index].kind === "pass" || (feedback[index].kind === "results" && feedback[index].passed));
  const failing = feedback[index] !== undefined && feedback[index].kind !== "pass" && !(feedback[index].kind === "results" && feedback[index].passed);

  return (
    <div className={`lesson-layout ${showLibrary || (showTutor && tutorAllowed) ? "with-side" : ""}`}>
      <section className="lesson-panel">
        <div className="lesson-head">
          <a href="#/" className="small">← All lessons</a>
          <h1>{lesson.title}</h1>
          {lesson.project && <LevelPicker level={lesson.project.level} onChange={changeLevel} />}
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
          {review && (
            <div className="banner info review-banner">
              <span>
                🔁 <strong>Review:</strong> answer from memory. Hints and the tutor still help, but then it comes back
                sooner.
              </span>
            </div>
          )}
          <p className="step-kind">
            Step {index + 1} of {lesson.steps.length} · {lesson.project && step.type === "exercise" ? "Checkpoint" : STEP_LABEL[step.type]}
          </p>
          <StepContent step={step} notebook={notebook} pseudo={pseudo} feedback={feedback[index]} onAnswer={answer} />

          {lesson.project && step.type === "exercise" && (
            <div className="level-note small">
              {LEVEL_NOTE[lesson.project.level]}
              {previousSubmission(index) && (
                <button className="link small" onClick={useMyPreviousCode}>
                  Start from my code from the last checkpoint
                </button>
              )}
            </div>
          )}
          {hints[index]?.map((hint, i) => (
            <div key={i} className="hint">
              <strong>Hint {i + 1}</strong>
              <Markdown>{hint}</Markdown>
            </div>
          ))}
          {labSolutions[index] && <LabSolution {...labSolutions[index]} />}
          {review && passed && (
            <button className="primary next-review" onClick={nextReview}>
              Next review →
            </button>
          )}
          {feedback[index] && step.type !== "quiz" && (
            <FeedbackView
              feedback={feedback[index]}
              onAskTutor={tutorAllowed && failing ? () => openTutor(WHY_FAILING) : undefined}
            />
          )}
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
          {!isLab && (
            <button className="primary" onClick={() => workspace.current?.run()} disabled={!sessionId || running || showingSolution}>
              ▶ {notebook ? "Run all" : "Run"}
            </button>
          )}
          {pseudo && (
            <button
              onClick={() => workspace.current?.stepThrough?.()}
              disabled={!sessionId || running || showingSolution}
              title="Run it one line at a time and watch every variable change"
            >
              👣 Step through
            </button>
          )}
          {checkable && (
            <button className="success" onClick={check} disabled={!sessionId || checking || showingSolution}>
              {checking ? "Checking…" : "✓ Check"}
            </button>
          )}
          {checkable && level !== "solo" && !(level === "assisted" && hintsShown >= hintCount) && !labSolutions[index] && (
            <button onClick={nextHint} disabled={showingSolution}>
              {hintsShown < hintCount ? `💡 Hint (${hintsShown}/${hintCount})` : "👀 Show me"}
            </button>
          )}
          {isLab || pseudo ? (
            <>
              {pseudo && (
                <button onClick={resetCode} disabled={showingSolution} title="Go back to the starting code">
                  ↺ Reset
                </button>
              )}
              {isLab && step.type === "exercise" && (
                <button onClick={() => resetLab(false)} disabled={!sessionId} title="Put the starter files back">
                  ↺ Reset files
                </button>
              )}
              <span className="spacer" />
              {tutorAllowed && <TutorButton open={showTutor} onClick={() => (showTutor ? setShowTutor(false) : openTutor())} />}
              {isLab && (
                <button onClick={() => resetLab(true)} disabled={!sessionId || step.type !== "exercise"} title="Remove your containers, networks, volumes and Kubernetes objects">
                  🧹 Clean up lab
                </button>
              )}
            </>
          ) : (
            <>
              <button onClick={resetCode} disabled={showingSolution} title="Go back to the starting code">
                ↺ Reset
              </button>
              <span className="spacer" />
              {tutorAllowed && <TutorButton open={showTutor} onClick={() => (showTutor ? setShowTutor(false) : openTutor())} />}
              <button
                onClick={() => {
                  setShowLibrary(!showLibrary);
                  setShowTutor(false);
                }}
                aria-pressed={showLibrary}
              >
                📚 Library
              </button>
            </>
          )}
        </div>
        {lesson.ai && (
          <div className={`banner ai-banner ${ai.status?.current ? "" : "warn"}`}>
            {ai.status?.current ? (
              <span>
                🤖 <code>dojo_ai</code> calls go to <strong>{ai.label.replace("AI: ", "")}</strong>
              </span>
            ) : (
              <span>🤖 Choose an AI model to run this lesson's AI cells: local (Ollama) or hosted (your key).</span>
            )}
            <button className="small" onClick={ai.openSettings}>
              {ai.status?.current ? "Change" : "Set up AI"}
            </button>
          </div>
        )}
        {isLab && !sessionId && !sessionError && (
          <div className="banner info">
            <span>Starting your lab: a private Docker engine just for you (plus a Kubernetes cluster in Kubernetes lessons). This takes 20 to 40 seconds…</span>
          </div>
        )}
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
        {step.type === "showcase" && (
          // Keyed by step: each showcase starts fresh (input box, position).
          <ShowcaseView key={`${lesson.slug}/${index}`} algorithm={step.algorithm} input={step.input} />
        )}
        <div className={step.type === "showcase" ? "workspace-hidden" : "workspace-body"}>
        {monacoLoaded && isLab ? (
          <LabWorkspace ref={labRef} sessionId={sessionId} exercise={step.type === "exercise" ? step.exercise : null} />
        ) : monacoLoaded ? (
          <Workspace
            key={notebook ? "notebook" : "editor"}
            ref={workspace}
            sessionId={sessionId}
            language={lesson.language}
            glossary={glossary}
            onChange={onCodeChange}
            onBusyChange={setRunning}
            onReady={onReady}
          />
        ) : (
          <div className="editor-wrap muted loading-editor">Loading the editor…</div>
        )}
        </div>
      </section>

      {showTutor && tutorAllowed && (
        <TutorPanel
          conversationKey={`${moduleId}/${lessonSlug}/${index}`}
          context={tutorContext}
          suggestions={tutorSuggestions(step, failing)}
          pending={tutorQuestion}
          onPendingSent={() => setTutorQuestion(null)}
          onClose={() => setShowTutor(false)}
        />
      )}
      {showLibrary && (
        <LibraryExplorer
          moduleId={moduleId}
          glossary={glossary}
          onInsert={(text, importModule) => workspace.current?.insert(text, importModule)}
          onClose={() => setShowLibrary(false)}
        />
      )}
    </div>
  );
}

function LabSolution({ commands, files }: { commands: string; files: Record<string, string> }) {
  return (
    <div className="hint lab-solution">
      <strong>One way to solve it</strong>
      <p className="small">Compare it with yours, then make the changes yourself: nothing has been overwritten.</p>
      {Object.entries(files).map(([name, text]) => (
        <div key={name}>
          <p className="small">
            <code>{name}</code>
          </p>
          <pre>
            <code>{text}</code>
          </pre>
        </div>
      ))}
      <p className="small">Then in the terminal:</p>
      <pre>
        <code>{commands}</code>
      </pre>
    </div>
  );
}

const LEVELS: { id: Level; label: string; help: string }[] = [
  { id: "guided", label: "Guided", help: "Skeleton with TODOs, hints and show me" },
  { id: "assisted", label: "Assisted", help: "Function outlines and hints" },
  { id: "solo", label: "Solo", help: "Just your code; no hints" },
];

const LEVEL_NOTE: Record<Level, string> = {
  guided: "Guided: fill in the TODOs. Hints and show me are available.",
  assisted: "Assisted: the outlines tell you what to build. Hints are available.",
  solo: "Solo: you're building on your own code. Switch level any time if you want help.",
};

function LevelPicker({ level, onChange }: { level: Level; onChange: (l: Level) => void }) {
  return (
    <div className="level-picker" role="radiogroup" aria-label="Project level">
      {LEVELS.map((l) => (
        <button
          key={l.id}
          role="radio"
          aria-checked={level === l.id}
          className={level === l.id ? "selected" : ""}
          onClick={() => onChange(l.id)}
          title={l.help}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}

const STEP_LABEL: Record<Step["type"], string> = {
  showcase: "Watch",
  explain: "Read",
  example: "Example",
  "try-it": "Try it",
  exercise: "Exercise",
  quiz: "Quiz",
};

export function StepContent({
  step,
  notebook,
  pseudo,
  feedback,
  onAnswer,
}: {
  step: Step;
  notebook: boolean;
  pseudo: boolean;
  feedback: Feedback | undefined;
  onAnswer: (option: number) => void;
}) {
  const where = notebook ? "notebook" : "editor";
  switch (step.type) {
    case "explain":
      return <Markdown>{step.md}</Markdown>;
    case "showcase":
      return (
        <>
          {step.md && <Markdown>{step.md}</Markdown>}
          <p className="muted small">Press ▶ Play, or step through it with ◀ ▶. Try your own input underneath.</p>
        </>
      );
    case "example":
      if (step.language) {
        return (
          <>
            {step.md && <Markdown>{step.md}</Markdown>}
            <div className="foreign-example">
              <span className="small muted">{LANGUAGE_NAMES[step.language] ?? step.language}</span>
              <pre>
                <code>{step.code}</code>
              </pre>
            </div>
          </>
        );
      }
      return (
        <>
          {step.md && <Markdown>{step.md}</Markdown>}
          <p className="muted small">
            The example is in the {where}. {notebook ? "Run each cell" : "Press Run"} to see what it does
            {pseudo ? ", or 👣 Step through it one line at a time" : ""}, then change it and run it again.
          </p>
        </>
      );
    case "try-it":
      return (
        <>
          <Markdown>{step.prompt}</Markdown>
          <p className="muted small">Edit the code in the {where}, then press ✓ Check.</p>
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

const WHY_FAILING = "My check didn't pass. Can you help me understand why?";

function TutorButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} aria-pressed={open} title="Ask the AI tutor about this step">
      🧑‍🏫 Tutor
    </button>
  );
}

function tutorSuggestions(step: Step, failing: boolean): string[] {
  switch (step.type) {
    case "exercise":
    case "try-it":
      return failing
        ? [WHY_FAILING, "What should I try next?"]
        : ["Where do I start?", "Explain the task in simpler words", "Is my approach on the right track?"];
    case "quiz":
      return ["Help me think this question through"];
    default:
      return ["Explain this in simpler words", "Give me a quick question to test myself"];
  }
}

/** The last Check in the shape the tutor endpoint expects. */
function feedbackForTutor(feedback: Feedback | undefined) {
  if (!feedback) return null;
  if (feedback.kind === "results") {
    return {
      passed: feedback.passed,
      timed_out: feedback.timedOut,
      results: feedback.results.map((r) => ({ label: r.label, outcome: r.outcome, message: r.explanation || r.message })),
    };
  }
  return { message: feedback.message };
}

function FeedbackView({ feedback, onAskTutor }: { feedback: Feedback; onAskTutor?: () => void }) {
  const ask = onAskTutor && (
    <button className="small ask-tutor" onClick={onAskTutor}>
      🧑‍🏫 Ask the tutor why
    </button>
  );
  if (feedback.kind !== "results") {
    return (
      <div className={`feedback feedback-line ${feedback.kind}`} role="status">
        <strong className="feedback-icon">{feedback.kind === "pass" ? "✓" : "✗"}</strong>
        <Markdown>{feedback.message}</Markdown>
        {ask}
      </div>
    );
  }
  if (feedback.timedOut) {
    return (
      <div className="feedback fail">
        Your program took too long. Is there a loop that never ends? {ask}
      </div>
    );
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
      {ask}
    </div>
  );
}

function defaultCode(step: Step): string | null {
  switch (step.type) {
    case "example":
      return step.language ? null : step.code;
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
    step.type === "explain" || step.type === "showcase" ? step.md
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
