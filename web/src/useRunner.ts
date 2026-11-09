import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl, type Explanation } from "./api";

export interface RunExit {
  exitCode: number | null;
  timedOut: boolean;
  cancelled: boolean;
  explanation: Explanation | null;
}

/** Interactive runs over /sessions/<id>/stream: output streams in, typed input goes out. */
export function useRunner(sessionId: string | null) {
  const [output, setOutput] = useState("");
  const [running, setRunning] = useState(false);
  const [exit, setExit] = useState<RunExit | null>(null);
  const socket = useRef<WebSocket | null>(null);

  useEffect(() => () => socket.current?.close(), []);

  const run = useCallback(
    (code: string) => {
      if (!sessionId) return;
      socket.current?.close();
      setOutput("");
      setExit(null);
      setRunning(true);
      const ws = new WebSocket(wsUrl(`/sessions/${sessionId}/stream`));
      socket.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ type: "run", code }));
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "output") {
          setOutput((previous) => previous + message.data);
        } else if (message.type === "exit") {
          setExit({
            exitCode: message.exit_code,
            timedOut: message.timed_out,
            cancelled: message.cancelled,
            explanation: message.explanation,
          });
          setRunning(false);
        }
      };
      ws.onclose = () => setRunning(false);
      ws.onerror = () => {
        setOutput((previous) => previous + "\n[Lost connection to the sandbox]\n");
        setRunning(false);
      };
    },
    [sessionId],
  );

  const sendInput = useCallback((text: string) => {
    // Programs don't echo what's typed, so show it ourselves like a terminal would.
    setOutput((previous) => previous + text + "\n");
    socket.current?.send(JSON.stringify({ type: "stdin", data: text + "\n" }));
  }, []);

  const stop = useCallback(() => {
    socket.current?.send(JSON.stringify({ type: "stop" }));
  }, []);

  const clear = useCallback(() => {
    setOutput("");
    setExit(null);
  }, []);

  return { output, running, exit, run, sendInput, stop, clear };
}
