import { KeyboardEvent, useEffect, useRef, useState } from "react";
import type { RunExit } from "../useRunner";
import ExplanationCard from "./ExplanationCard";

interface Props {
  output: string;
  running: boolean;
  exit: RunExit | null;
  onInput: (text: string) => void;
  onStop: () => void;
  onGoToLine: (line: number) => void;
}

export default function Console({ output, running, exit, onInput, onStop, onGoToLine }: Props) {
  const [typed, setTyped] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  // Braces matter: newer browsers return a Promise from scrollIntoView, and React
  // would try to call a returned value as the effect's cleanup.
  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [output, exit]);
  useEffect(() => {
    if (running) input.current?.focus();
  }, [running]);

  function onKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      onInput(typed);
      setTyped("");
    }
  }

  const status = running
    ? "Running…"
    : exit?.cancelled
      ? "Stopped"
      : exit?.timedOut
        ? "Took too long"
        : exit
          ? exit.exitCode === 0
            ? "Finished"
            : "Finished with an error"
          : "Output";

  return (
    <section className="console" aria-label="Program output">
      <div className="console-head">
        <span className={`status-dot ${running ? "running" : exit && exit.exitCode !== 0 ? "bad" : ""}`} />
        <span>{status}</span>
        {running && (
          <button className="small danger" onClick={onStop}>
            ■ Stop
          </button>
        )}
      </div>
      <div className="console-body">
        {!output && !running && !exit && (
          <p className="muted">Press <kbd>Run</kbd> (or <kbd>Ctrl</kbd>+<kbd>Enter</kbd>) to run your code.</p>
        )}
        <pre>{output}</pre>
        {running && (
          <div className="console-input">
            <span aria-hidden>›</span>
            <input
              ref={input}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={onKey}
              placeholder="If your program asks a question, type the answer here and press Enter"
              aria-label="Program input"
            />
          </div>
        )}
        {exit?.timedOut && (
          <p className="error-text">
            Your program used too much time. Is there a loop that never ends?
          </p>
        )}
        {exit?.explanation && <ExplanationCard explanation={exit.explanation} onGoToLine={onGoToLine} />}
        <div ref={end} />
      </div>
    </section>
  );
}
