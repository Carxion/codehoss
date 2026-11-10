import Editor from "@monaco-editor/react";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { api, type Exercise } from "../api";
import { prefersDark } from "./editorUtils";
import LabTerminal from "./LabTerminal";

export interface LabHandle {
  /** Write any unsaved edits to the session (before Check). */
  saveAll(): Promise<void>;
  /** Re-read files from the session (the terminal may have changed them). */
  reload(): Promise<void>;
  /** Put the starter files back; `engine` also removes containers, networks, volumes. */
  reset(engine: boolean): Promise<void>;
}

interface Props {
  sessionId: string | null;
  /** The current lab exercise, or null on reading steps (terminal only). */
  exercise: Exercise | null;
}

const SAVE_DELAY_MS = 600;

function languageFor(path: string): string {
  const name = path.split("/").pop()!.toLowerCase();
  if (name === "dockerfile" || name.endsWith(".dockerfile")) return "dockerfile";
  if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
  if (name.endsWith(".py")) return "python";
  if (name.endsWith(".md")) return "markdown";
  if (name.endsWith(".json")) return "json";
  if (name.endsWith(".sh")) return "shell";
  return "plaintext";
}

/** Files in the lab session on top, a real terminal underneath. */
const LabWorkspace = forwardRef<LabHandle, Props>(function LabWorkspace({ sessionId, exercise }, ref) {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [current, setCurrent] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "saved" | "saving" | "unsaved" | "error">("loading");
  const [error, setError] = useState("");
  const pending = useRef(new Map<string, string>());
  const timer = useRef<number | null>(null);
  const exerciseId = exercise?.lab ? exercise.id : null;

  const apply = useCallback((next: Record<string, string>) => {
    setFiles(next);
    setCurrent((c) => (c && c in next ? c : (Object.keys(next).find((f) => f !== "README.md") ?? Object.keys(next)[0] ?? null)));
  }, []);

  const flush = useCallback(async () => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = null;
    if (!sessionId || !exerciseId || pending.current.size === 0) return;
    const writes = [...pending.current];
    pending.current.clear();
    setStatus("saving");
    try {
      await Promise.all(writes.map(([path, text]) => api.labWrite(sessionId, exerciseId, path, text)));
      setStatus(pending.current.size ? "unsaved" : "saved");
    } catch (e) {
      setStatus("error");
      setError((e as Error).message);
    }
  }, [sessionId, exerciseId]);

  useEffect(() => {
    if (!sessionId || !exerciseId) return;
    setStatus("loading");
    pending.current.clear();
    api.labOpen(sessionId, exerciseId).then(
      (state) => {
        apply(state.files);
        setStatus("saved");
      },
      (e) => {
        setStatus("error");
        setError(e.message);
      },
    );
    return () => {
      void flush();
    };
  }, [sessionId, exerciseId]);

  const reload = useCallback(async () => {
    if (!sessionId || !exerciseId) return;
    await flush();
    apply((await api.labFiles(sessionId, exerciseId)).files);
  }, [sessionId, exerciseId, flush, apply]);

  useImperativeHandle(
    ref,
    () => ({
      saveAll: flush,
      reload,
      async reset(engine: boolean) {
        if (!sessionId || !exerciseId) return;
        pending.current.clear();
        apply((await api.labReset(sessionId, exerciseId, engine)).files);
        setStatus("saved");
      },
    }),
    [flush, reload, sessionId, exerciseId, apply],
  );

  function edit(text: string | undefined) {
    if (current === null || text === undefined) return;
    setFiles((f) => ({ ...f, [current]: text }));
    pending.current.set(current, text);
    setStatus("unsaved");
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void flush(), SAVE_DELAY_MS);
  }

  async function newFile() {
    if (!sessionId || !exerciseId) return;
    const name = window.prompt("New file name (for example .dockerignore or app/main.py):")?.trim();
    if (!name) return;
    try {
      await api.labWrite(sessionId, exerciseId, name, "");
      await reload();
      setCurrent(name.replace(/^\/+/, ""));
    } catch (e) {
      setStatus("error");
      setError((e as Error).message);
    }
  }

  async function deleteFile(path: string) {
    if (!sessionId || !exerciseId || !window.confirm(`Delete ${path}?`)) return;
    pending.current.delete(path);
    apply((await api.labDelete(sessionId, exerciseId, path)).files);
  }

  if (!exercise?.lab) {
    return (
      <div className="lab lab-terminal-only">
        <LabTerminal sessionId={sessionId} dir="/work" />
      </div>
    );
  }

  const names = Object.keys(files);
  return (
    <div className="lab">
      <div className="lab-files">
        <div className="lab-tabs" role="tablist" aria-label="Files">
          {names.map((name) => (
            <span key={name} className={`lab-tab ${name === current ? "current" : ""}`}>
              <button role="tab" aria-selected={name === current} onClick={() => setCurrent(name)}>
                {name}
              </button>
              <button className="lab-tab-close" aria-label={`Delete ${name}`} title="Delete file" onClick={() => deleteFile(name)}>
                ×
              </button>
            </span>
          ))}
          <button className="lab-tab-add" onClick={newFile} title="New file" aria-label="New file">
            +
          </button>
          <span className="spacer" />
          <button className="small" onClick={() => void reload()} title="Re-read files changed from the terminal">
            ↻ Refresh
          </button>
          <span className={`small lab-status ${status}`}>
            {status === "loading" && "Loading…"}
            {status === "saving" && "Saving…"}
            {status === "unsaved" && "Unsaved"}
            {status === "saved" && "Saved"}
            {status === "error" && `Couldn't save: ${error}`}
          </span>
        </div>
        <div className="lab-editor">
          {current !== null ? (
            <Editor
              path={`${exercise.id}/${current}`}
              value={files[current] ?? ""}
              language={languageFor(current)}
              theme={prefersDark() ? "vs-dark" : "vs"}
              onChange={edit}
              options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false, automaticLayout: true, tabSize: 2 }}
            />
          ) : (
            <p className="muted lab-waiting">{status === "loading" ? "Opening your files…" : "No files yet: press + to create one."}</p>
          )}
        </div>
      </div>
      {/* Only once the folder exists, so the shell starts inside it. */}
      <LabTerminal sessionId={status === "loading" ? null : sessionId} dir={exercise.lab.dir} beforeCommand={flush} />
    </div>
  );
});

export default LabWorkspace;
