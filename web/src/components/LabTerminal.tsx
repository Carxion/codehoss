import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api";
import { prefersDark } from "./editorUtils";

interface Props {
  sessionId: string | null;
  /** Folder the shell starts in. Changing it opens a fresh shell there. */
  dir: string;
}

const LIGHT = { background: "#ffffff", foreground: "#1f2328", cursor: "#1f2328", selectionBackground: "#b6d4fe" };
const DARK = { background: "#0d1117", foreground: "#e6edf3", cursor: "#e6edf3", selectionBackground: "#264f78" };

/** A real bash shell in the lab session (dojo._term on the other end). */
export default function LabTerminal({ sessionId, dir }: Props) {
  const host = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<"connecting" | "open" | "closed">("connecting");
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    if (!sessionId || !host.current) return;
    const term = new Terminal({
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      fontSize: 13,
      cursorBlink: true,
      scrollback: 5000,
      theme: prefersDark() ? DARK : LIGHT,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(host.current);
    fit.fit();
    setState("connecting");

    const ws = new WebSocket(wsUrl(`/sessions/${sessionId}/terminal?dir=${encodeURIComponent(dir)}`));
    ws.binaryType = "arraybuffer";
    const send = (message: object) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
    };
    const sendSize = () => send({ r: [term.cols, term.rows] });
    ws.onopen = () => {
      setState("open");
      sendSize();
      term.focus();
    };
    ws.onmessage = (event) => {
      term.write(typeof event.data === "string" ? event.data : new Uint8Array(event.data));
    };
    ws.onclose = () => {
      setState("closed");
      term.write("\r\n\x1b[2m[shell closed]\x1b[0m\r\n");
    };
    const typing = term.onData((data) => send({ i: data }));
    const resized = term.onResize(sendSize);
    const observer = new ResizeObserver(() => {
      try {
        fit.fit();
      } catch {
        // hidden (zero size): nothing to fit
      }
    });
    observer.observe(host.current);

    return () => {
      observer.disconnect();
      typing.dispose();
      resized.dispose();
      ws.onclose = null;
      ws.close();
      term.dispose();
    };
  }, [sessionId, dir, generation]);

  return (
    <div className="lab-terminal">
      <div className="lab-terminal-head small">
        <span>
          Terminal <code>{dir}</code>
        </span>
        <span className="spacer" />
        {state === "connecting" && sessionId && <span className="muted">connecting…</span>}
        {state === "closed" && (
          <button className="small" onClick={() => setGeneration((g) => g + 1)}>
            New shell
          </button>
        )}
      </div>
      {sessionId ? (
        <div className="lab-terminal-body" ref={host} aria-label="Terminal" />
      ) : (
        <div className="lab-terminal-body muted lab-waiting">Starting your lab…</div>
      )}
    </div>
  );
}
