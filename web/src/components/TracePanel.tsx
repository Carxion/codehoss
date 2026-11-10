import { useEffect, useRef, useState } from "react";
import { api, type Trace, type TraceFrame } from "../api";

interface Props {
  sessionId: string;
  /** The program, frozen while stepping (the editor is read-only meanwhile). */
  code: string;
  /** Highlight this line in the editor (null: none). */
  onLine: (line: number | null, error: boolean) => void;
  onClose: () => void;
}

const PLAY_MS = 700;

/** Steps through a pseudocode program: the line about to run, every variable, the output. */
export default function TracePanel({ sessionId, code, onLine, onClose }: Props) {
  const asks = /\bINPUT\s*\(/.test(code);
  const [inputs, setInputs] = useState("");
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState("");
  const [at, setAt] = useState(0);
  const [playing, setPlaying] = useState(false);
  const panel = useRef<HTMLElement>(null);

  async function start() {
    setLoading(true);
    setFailed("");
    try {
      const result = await api.trace(sessionId, code, inputs ? inputs.split("\n") : []);
      setTrace(result);
      setAt(0);
      panel.current?.focus();
    } catch (e) {
      setFailed((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // Programs without INPUT start straight away.
  useEffect(() => {
    if (!asks) start();
  }, []);

  const steps = trace?.steps ?? [];
  const last = steps.length - 1;
  const step = steps[at];
  const errorHere = !!trace?.error && at === last;

  useEffect(() => {
    onLine(step && step.line > 0 ? step.line : null, errorHere);
  }, [step, errorHere]);
  useEffect(() => () => onLine(null, false), []);

  useEffect(() => {
    if (!playing) return;
    if (at >= last) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => setAt((i) => Math.min(i + 1, last)), PLAY_MS);
    return () => window.clearTimeout(timer);
  }, [playing, at, last]);

  const go = (i: number) => {
    setPlaying(false);
    setAt(Math.max(0, Math.min(last, i)));
  };

  function onKey(event: React.KeyboardEvent) {
    if (event.target instanceof HTMLTextAreaElement) return;
    if (event.key === "ArrowRight") go(at + 1);
    else if (event.key === "ArrowLeft") go(at - 1);
  }

  const previous = at > 0 ? steps[at - 1] : undefined;

  return (
    <section className="trace" aria-label="Step through" ref={panel} tabIndex={-1} onKeyDown={onKey}>
      <div className="trace-head">
        <strong>👣 Step through</strong>
        {trace && steps.length > 0 && (
          <div className="trace-controls">
            <button className="small" onClick={() => go(0)} disabled={at === 0} aria-label="First step">⏮</button>
            <button className="small" onClick={() => go(at - 1)} disabled={at === 0}>◀ Back</button>
            <span className="small trace-count">Step {at + 1} of {steps.length}</span>
            <button className="small primary" onClick={() => go(at + 1)} disabled={at >= last}>Next ▶</button>
            <button className="small" onClick={() => go(last)} disabled={at >= last} aria-label="Last step">⏭</button>
            <button className="small" onClick={() => (playing ? setPlaying(false) : at >= last ? (setAt(0), setPlaying(true)) : setPlaying(true))}>
              {playing ? "⏸ Pause" : "⏵ Play"}
            </button>
          </div>
        )}
        <span className="spacer" />
        {trace && asks && (
          <button className="small" onClick={() => setTrace(null)}>Change input</button>
        )}
        <button className="small" onClick={onClose}>✕ Close</button>
      </div>

      <div className="trace-body">
        {!trace && asks && (
          <div className="trace-inputs">
            <label htmlFor="trace-inputs">
              This program uses <code>INPUT</code>. Type what you'd answer, one line for each question:
            </label>
            <textarea
              id="trace-inputs"
              rows={3}
              value={inputs}
              onChange={(e) => setInputs(e.target.value)}
              placeholder={"Ada\n36"}
              autoFocus
            />
            <button className="primary" onClick={start} disabled={loading}>
              {loading ? "Working it out…" : "Start stepping"}
            </button>
          </div>
        )}
        {!trace && !asks && loading && <p className="muted">Working out every step…</p>}
        {failed && <p className="error-text">{failed}</p>}

        {trace && step && (
          <>
            <p className={`trace-status ${errorHere ? "bad" : step.line === 0 ? "ok" : ""}`} role="status">
              {errorHere
                ? `✗ Line ${trace.error!.line ?? "?"}: ${trace.error!.message}`
                : step.line === 0
                  ? "✓ Finished: every line has run."
                  : at === 0
                    ? `The highlighted line (${step.line}) runs first. Press Next ▶ (or →) to run it.`
                    : `Line ${step.line} runs next.`}
            </p>
            {trace.truncated && at === last && (
              <p className="small muted">
                Stopped after {steps.length} steps. Is there a loop that never ends? (Long programs can be
                traced in smaller pieces.)
              </p>
            )}
            <div className="trace-grid">
              <div>
                <h3 className="small">Variables</h3>
                {step.frames.map((frame, i) => (
                  <FrameView key={i} frame={frame} before={previous?.frames[i]} nested={i > 0} />
                ))}
              </div>
              <div>
                <h3 className="small">Output</h3>
                <pre className="trace-output">{trace.output.slice(0, step.out) || " "}</pre>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function FrameView({ frame, before, nested }: { frame: TraceFrame; before?: TraceFrame; nested: boolean }) {
  const names = Object.keys(frame.vars);
  const same = before && before.name === frame.name;
  return (
    <div className={`trace-frame ${nested ? "nested" : ""}`}>
      <div className="small muted">{nested ? `inside ${frame.name}(…)` : frame.name}</div>
      {names.length === 0 ? (
        <p className="small muted trace-empty">No variables yet.</p>
      ) : (
        <table>
          <tbody>
            {names.map((name) => {
              const changed = !same || before.vars[name] !== frame.vars[name];
              return (
                <tr key={name} className={changed ? "changed" : ""}>
                  <th scope="row">{name}</th>
                  <td>
                    <code>{frame.vars[name]}</code>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
