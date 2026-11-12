import Editor, { type OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { authorApi, type AuthorMarker, type AuthorPreview, type Step } from "../api";
import { loadMonaco } from "../monacoSetup";
import { PSEUDO, registerPseudo } from "../pseudo";
import { prefersDark } from "./editorUtils";
import { StepContent } from "./LessonView";

// The Studio: write course content with live validation and a preview of each lesson
// exactly as learners will see it. Previews and tests use the unsaved text (the server
// loads it from a temporary copy); Save writes the file and learners see it at once.

const STEP_LABEL: Record<string, string> = {
  explain: "Explanation",
  example: "Example",
  "try-it": "Try it",
  exercise: "Exercise",
  quiz: "Quiz",
  showcase: "Showcase",
  missing: "Missing exercise",
};

function languageOf(path: string): string {
  const name = path.split("/").pop() ?? "";
  if (name === "Dockerfile") return "dockerfile";
  const ext = name.split(".").pop();
  return (
    { yaml: "yaml", yml: "yaml", md: "markdown", py: "python", pseudo: PSEUDO, sh: "shell", json: "json", toml: "ini", cfg: "ini" }[
      ext ?? ""
    ] ?? "plaintext"
  );
}

export default function Studio() {
  const [modules, setModules] = useState<{ id: string; files: string[] }[] | null>(null);
  const [allMarkers, setAllMarkers] = useState<AuthorMarker[]>([]);
  const [error, setError] = useState("");
  const [path, setPath] = useState<string | null>(null);
  const [saved, setSaved] = useState("");
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<AuthorPreview | null>(null);
  const [tab, setTab] = useState<"preview" | "problems">("preview");
  const [busy, setBusy] = useState<"" | "saving" | "testing">("");
  const [testResult, setTestResult] = useState<{ checks: number; markers: AuthorMarker[] } | null>(null);
  const [monacoReady, setMonacoReady] = useState(false);
  const [filter, setFilter] = useState("");
  const editor = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monaco = useRef<typeof Monaco | null>(null);
  const dirty = path !== null && text !== saved;

  const refreshTree = useCallback(async () => {
    const tree = await authorApi.tree();
    setModules(tree.modules);
    setAllMarkers(tree.markers);
  }, []);

  useEffect(() => {
    refreshTree().catch((e) => setError(e.message));
    loadMonaco().then(() => setMonacoReady(true));
  }, [refreshTree]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  // Live preview of the unsaved text, a moment after typing stops.
  useEffect(() => {
    if (!path) return;
    const timer = window.setTimeout(() => {
      authorApi.preview(path, text).then(setPreview, (e) => setError(e.message));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [path, text]);

  // Problems in this file become squiggles in the editor.
  const fileMarkers = useMemo(() => (preview?.markers ?? []).filter((m) => m.path === path), [preview, path]);
  useEffect(() => {
    const model = editor.current?.getModel();
    if (!model || !monaco.current) return;
    monaco.current.editor.setModelMarkers(
      model,
      "hoss",
      fileMarkers.map((m) => {
        const line = Math.min(m.line ?? 1, model.getLineCount());
        return {
          severity: m.level === "error" ? monaco.current!.MarkerSeverity.Error : monaco.current!.MarkerSeverity.Warning,
          message: m.message,
          startLineNumber: line,
          endLineNumber: line,
          startColumn: model.getLineFirstNonWhitespaceColumn(line) || 1,
          endColumn: model.getLineMaxColumn(line),
        };
      }),
    );
  }, [fileMarkers]);

  async function open(next: string) {
    if (next === path) return;
    if (dirty && !window.confirm(`Discard your unsaved changes to ${path}?`)) return;
    try {
      const file = await authorApi.read(next);
      setPath(next);
      setSaved(file.text);
      setText(file.text);
      setPreview(null);
      setTestResult(null);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const save = useCallback(async () => {
    if (!path) return;
    setBusy("saving");
    try {
      const result = await authorApi.save(path, text);
      setSaved(text);
      setAllMarkers(result.markers);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }, [path, text]);
  const saveRef = useRef(save);
  saveRef.current = save;

  async function test() {
    if (!path) return;
    setBusy("testing");
    setTestResult(null);
    try {
      setTestResult(await authorApi.test(path, text));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function create(kind: "module" | "lesson" | "exercise", module = "", lesson?: string) {
    const what = kind === "module" ? "module id (e.g. web-basics)" : kind === "lesson" ? "lesson folder (e.g. 05-loops)" : "exercise folder (e.g. ex01-countdown)";
    const slug = window.prompt(`New ${kind}: ${what}`)?.trim();
    if (!slug) return;
    const title = window.prompt(`Title for ${slug}`)?.trim();
    if (!title) return;
    const language = kind === "module" && window.confirm("Write it in Hoss pseudocode? (Cancel for Python)") ? "pseudo" : "python";
    try {
      const result = await authorApi.create({ kind, module: kind === "module" ? slug : module, lesson, slug, title, language });
      await refreshTree();
      setAllMarkers(result.markers);
      const first = result.files.find((f) => f.endsWith("exercise.yaml")) ?? result.files[result.files.length - 1];
      await open(first);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const onMount: OnMount = (instance, m) => {
    editor.current = instance;
    monaco.current = m;
    registerPseudo(m);
    instance.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.KeyS, () => void saveRef.current());
  };

  function jump(marker: AuthorMarker) {
    if (marker.path !== path) {
      if (/\.(ya?ml|md|py|pseudo|sh|txt)$/.test(marker.path)) void open(marker.path);
      return;
    }
    if (marker.line && editor.current) {
      editor.current.revealLineInCenter(marker.line);
      editor.current.setPosition({ lineNumber: marker.line, column: 1 });
      editor.current.focus();
    }
  }

  if (error && !modules) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!modules) return <main className="page muted">Loading the Studio…</main>;

  const parts = path?.split("/") ?? [];
  const lessonSlug = parts.length >= 3 ? parts[1] : null;
  const otherProblems = allMarkers.filter((m) => m.path !== path);

  return (
    <div className="studio">
      <aside className="studio-files" aria-label="Content files">
        <div className="studio-files-head">
          <strong>Content</strong>
          <button className="small" onClick={() => create("module")}>
            + Module
          </button>
        </div>
        <input
          className="studio-filter"
          placeholder="Filter files…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter files"
        />
        <div className="studio-tree">
          {modules.map((m) => (
            <ModuleFiles
              key={m.id}
              module={m}
              filter={filter.toLowerCase()}
              current={path}
              problems={allMarkers}
              onOpen={open}
              onNewLesson={() => create("lesson", m.id)}
              onNewExercise={(lesson) => create("exercise", m.id, lesson)}
            />
          ))}
        </div>
      </aside>

      <section className="studio-editor">
        <div className="toolbar">
          <span className="studio-path">
            {path ?? "Pick a file to edit"}
            {dirty && <span className="dirty" title="Unsaved changes"> ●</span>}
          </span>
          <span className="spacer" />
          {path && lessonSlug && (
            <button onClick={test} disabled={busy !== ""} title="Run every solution and starter in this lesson in the sandbox">
              {busy === "testing" ? "Testing…" : "▶ Test lesson"}
            </button>
          )}
          {path && lessonSlug && (
            <a className="button" href={`#/learn/${parts[0]}/${lessonSlug}/0`} title="Open the saved lesson as a learner">
              👁 As learner
            </a>
          )}
          <button className="primary" onClick={save} disabled={!dirty || busy !== ""} title="Save (Ctrl+S)">
            {busy === "saving" ? "Saving…" : "Save"}
          </button>
        </div>
        {error && <div className="banner error">{error}</div>}
        <div className="editor-wrap">
          {path && monacoReady ? (
            <Editor
              key={path}
              path={`file:///studio/${path}`}
              defaultLanguage={languageOf(path)}
              defaultValue={saved}
              theme={prefersDark() ? "vs-dark" : "vs"}
              onMount={onMount}
              onChange={(value) => value !== undefined && setText(value)}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 2,
                insertSpaces: true,
                automaticLayout: true,
                wordWrap: languageOf(path) === "markdown" ? "on" : "off",
                fixedOverflowWidgets: true,
              }}
            />
          ) : (
            <div className="studio-empty muted">
              <p>Pick a file on the left, or start a new module.</p>
              <p className="small">
                Lessons live in <code>lesson.yaml</code>; each exercise is a folder with <code>exercise.yaml</code>, a
                starter, a solution and tests. The preview updates as you type, and ▶ Test lesson checks every solution
                passes and every starter doesn't.
              </p>
            </div>
          )}
        </div>
      </section>

      <aside className="studio-side">
        <div className="studio-tabs" role="tablist">
          <button role="tab" aria-selected={tab === "preview"} className={tab === "preview" ? "active" : ""} onClick={() => setTab("preview")}>
            Preview
          </button>
          <button role="tab" aria-selected={tab === "problems"} className={tab === "problems" ? "active" : ""} onClick={() => setTab("problems")}>
            Problems{" "}
            {fileMarkers.length + otherProblems.length > 0 && <span className="count-badge">{fileMarkers.length + otherProblems.length}</span>}
          </button>
        </div>

        {testResult && (
          <div className={`feedback ${testResult.markers.some((m) => m.level === "error") ? "fail" : "pass"}`}>
            {testResult.markers.length === 0 ? (
              <strong>✓ {testResult.checks} check{testResult.checks === 1 ? "" : "s"} passed: every solution passes, every starter doesn't.</strong>
            ) : (
              <>
                <strong>Test found {testResult.markers.length} problem{testResult.markers.length === 1 ? "" : "s"}</strong>
                <MarkerList markers={testResult.markers} onJump={jump} />
              </>
            )}
          </div>
        )}

        {tab === "problems" ? (
          <div className="studio-problems">
            {fileMarkers.length + otherProblems.length === 0 && <p className="muted small">No problems found. ✓</p>}
            {fileMarkers.length > 0 && (
              <>
                <h3 className="small">This file (unsaved)</h3>
                <MarkerList markers={fileMarkers} onJump={jump} />
              </>
            )}
            {otherProblems.length > 0 && (
              <>
                <h3 className="small">Other saved files</h3>
                <MarkerList markers={otherProblems} onJump={jump} />
              </>
            )}
          </div>
        ) : (
          <LessonPreview preview={preview} markers={fileMarkers} onJump={jump} />
        )}
      </aside>
    </div>
  );
}

function ModuleFiles({
  module,
  filter,
  current,
  problems,
  onOpen,
  onNewLesson,
  onNewExercise,
}: {
  module: { id: string; files: string[] };
  filter: string;
  current: string | null;
  problems: AuthorMarker[];
  onOpen: (path: string) => void;
  onNewLesson: () => void;
  onNewExercise: (lesson: string) => void;
}) {
  const files = module.files.filter((f) => !filter || f.toLowerCase().includes(filter));
  const top = files.filter((f) => f.split("/").length === 2);
  const lessons = new Map<string, string[]>();
  for (const f of files) {
    const parts = f.split("/");
    if (parts.length > 2 && (parts.length > 3 || parts[2] === "lesson.yaml")) {
      if (!lessons.has(parts[1])) lessons.set(parts[1], []);
      lessons.get(parts[1])!.push(f);
    }
  }
  const hasProblem = (prefix: string) => problems.some((m) => m.level === "error" && m.path.startsWith(prefix));
  if (filter && files.length === 0) return null;
  return (
    <details open={Boolean(filter) || current?.startsWith(module.id + "/")}>
      <summary className={hasProblem(module.id + "/") ? "has-problem" : ""}>
        {module.id}
        <button className="link small" onClick={(e) => { e.preventDefault(); onNewLesson(); }} title="New lesson">
          + lesson
        </button>
      </summary>
      {top.map((f) => (
        <FileLink key={f} path={f} label={f.split("/").pop()!} current={current} onOpen={onOpen} />
      ))}
      {[...lessons].map(([lesson, lessonFiles]) => (
        <details key={lesson} className="studio-lesson" open={Boolean(filter) || current?.startsWith(`${module.id}/${lesson}/`)}>
          <summary className={hasProblem(`${module.id}/${lesson}/`) ? "has-problem" : ""}>
            {lesson}
            <button className="link small" onClick={(e) => { e.preventDefault(); onNewExercise(lesson); }} title="New exercise">
              + exercise
            </button>
          </summary>
          {lessonFiles.sort(byLessonOrder).map((f) => (
            <FileLink key={f} path={f} label={f.split("/").slice(2).join("/")} current={current} onOpen={onOpen} />
          ))}
        </details>
      ))}
    </details>
  );
}

/** lesson.yaml first, then each exercise's files with exercise.yaml leading. */
function byLessonOrder(a: string, b: string): number {
  const rank = (f: string) => (f.endsWith("/lesson.yaml") && f.split("/").length === 3 ? "0" : f.replace(/exercise\.yaml$/, " exercise.yaml"));
  return rank(a).localeCompare(rank(b));
}

function FileLink({ path, label, current, onOpen }: { path: string; label: string; current: string | null; onOpen: (p: string) => void }) {
  return (
    <button className={`studio-file ${path === current ? "current" : ""}`} onClick={() => onOpen(path)} title={path}>
      {label}
    </button>
  );
}

function MarkerList({ markers, onJump }: { markers: AuthorMarker[]; onJump: (m: AuthorMarker) => void }) {
  return (
    <ul className="marker-list">
      {markers.map((m, i) => (
        <li key={i} className={m.level}>
          <button className="link small" onClick={() => onJump(m)}>
            {m.level === "error" ? "✗" : "⚠"} {m.path}
            {m.line ? `:${m.line}` : ""}
          </button>
          <span className="small">{m.message}</span>
        </li>
      ))}
    </ul>
  );
}

function LessonPreview({ preview, markers, onJump }: { preview: AuthorPreview | null; markers: AuthorMarker[]; onJump: (m: AuthorMarker) => void }) {
  if (!preview) return <p className="muted small">The preview appears here as you edit a lesson.</p>;
  const errors = markers.filter((m) => m.level === "error");
  return (
    <div className="studio-preview">
      {errors.length > 0 && (
        <div className="feedback fail">
          <strong>Learners won't see this until it's fixed:</strong>
          <MarkerList markers={errors} onJump={onJump} />
        </div>
      )}
      {!preview.lesson ? (
        preview.module ? (
          <div>
            <h2>{preview.module.title}</h2>
            <p className="muted small">
              {preview.module.lessons.length} lesson{preview.module.lessons.length === 1 ? "" : "s"} · written in{" "}
              {preview.module.language === "pseudo" ? "Hoss pseudocode" : "Python"} · opens in the {preview.module.view} view
            </p>
            <ol className="small">
              {preview.module.lessons.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ol>
          </div>
        ) : (
          <p className="muted small">Nothing to preview for this file.</p>
        )
      ) : (
        <>
          <h2>{preview.lesson.title}</h2>
          {preview.lesson.summary && <p className="muted">{preview.lesson.summary}</p>}
          {preview.lesson.steps.map((step) => (
            <section key={step.index} className="card studio-step">
              <p className="step-kind">
                Step {step.index + 1} · {STEP_LABEL[step.type]}
              </p>
              {step.type === "missing" ? (
                <p className="error-text small">No exercise folder called {step.ref}.</p>
              ) : (
                <StepContent
                  step={step as Step}
                  notebook={preview.module?.view === "notebook"}
                  pseudo={preview.module?.language === "pseudo"}
                  feedback={undefined}
                  onAnswer={() => {}}
                />
              )}
            </section>
          ))}
        </>
      )}
    </div>
  );
}
