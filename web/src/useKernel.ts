import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl } from "./api";

export type CellOutput =
  | { kind: "stream"; name: "stdout" | "stderr"; text: string }
  | { kind: "data"; data: Record<string, string> }
  | {
      kind: "error";
      ename: string;
      evalue: string;
      traceback: string;
      explanation: string;
      line: number | null;
    };

/** One hoss_ai call made by a cell: shown as a "via <model>" badge under it. */
export interface AICall {
  kind: string;
  ok: boolean;
  provider?: string;
  model?: string;
  ms: number;
  error?: string;
}

export type KernelState = "disconnected" | "starting" | "idle" | "busy" | "dead";

/** A notebook kernel over /sessions/<id>/kernel. Outputs are kept per cell id. */
export function useKernel(sessionId: string | null) {
  const [state, setState] = useState<KernelState>("disconnected");
  const [outputs, setOutputs] = useState<Record<string, CellOutput[]>>({});
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [deadReason, setDeadReason] = useState("");
  const [aiCalls, setAiCalls] = useState<Record<string, AICall[]>>({});
  const socket = useRef<WebSocket | null>(null);
  const waiting = useRef(new Map<string, (ok: boolean) => void>());

  const append = useCallback((cell: string, output: CellOutput) => {
    setOutputs((all) => {
      const list = all[cell] ?? [];
      const last = list[list.length - 1];
      // Merge consecutive text from the same stream so prints read as one block.
      if (output.kind === "stream" && last?.kind === "stream" && last.name === output.name) {
        return { ...all, [cell]: [...list.slice(0, -1), { ...last, text: last.text + output.text }] };
      }
      return { ...all, [cell]: [...list, output] };
    });
  }, []);

  const finish = useCallback((cell: string, ok: boolean) => {
    setRunning((set) => {
      const next = new Set(set);
      next.delete(cell);
      return next;
    });
    waiting.current.get(cell)?.(ok);
    waiting.current.delete(cell);
  }, []);

  const connect = useCallback((): WebSocket | null => {
    if (!sessionId) return null;
    const existing = socket.current;
    if (existing && existing.readyState <= WebSocket.OPEN) return existing;
    const ws = new WebSocket(wsUrl(`/sessions/${sessionId}/kernel`));
    socket.current = ws;
    ws.onmessage = (event) => {
      const m = JSON.parse(event.data);
      switch (m.type) {
        case "status":
          setState(m.state === "restarted" ? "idle" : m.state);
          break;
        case "stream":
          append(m.cell, { kind: "stream", name: m.name, text: m.text });
          break;
        case "display":
        case "result":
          append(m.cell, { kind: "data", data: m.data });
          break;
        case "error":
          append(m.cell, {
            kind: "error",
            ename: m.ename,
            evalue: m.evalue,
            traceback: m.traceback,
            explanation: m.explanation,
            line: m.line,
          });
          break;
        case "ai":
          setAiCalls((all) => ({
            ...all,
            [m.cell]: [...(all[m.cell] ?? []), { kind: m.kind, ok: m.ok, provider: m.provider, model: m.model, ms: m.ms, error: m.error }],
          }));
          break;
        case "done":
          setCounts((c) => ({ ...c, [m.cell]: m.execution_count }));
          finish(m.cell, m.status === "ok");
          break;
        case "dead":
          setState("dead");
          setDeadReason(m.reason);
          for (const cell of waiting.current.keys()) finish(cell, false);
          break;
      }
    };
    ws.onclose = () => {
      setState("disconnected");
      for (const cell of [...waiting.current.keys()]) finish(cell, false);
    };
    return ws;
  }, [sessionId, append, finish]);

  useEffect(() => () => socket.current?.close(), []);

  /** Run a cell; resolves true if it finished without an error. */
  const execute = useCallback(
    (cell: string, code: string): Promise<boolean> => {
      const ws = connect();
      if (!ws) return Promise.resolve(false);
      setOutputs((all) => ({ ...all, [cell]: [] }));
      setAiCalls((all) => ({ ...all, [cell]: [] }));
      setRunning((set) => new Set(set).add(cell));
      setDeadReason("");
      const message = JSON.stringify({ type: "execute", cell, code });
      if (ws.readyState === WebSocket.OPEN) ws.send(message);
      else ws.addEventListener("open", () => ws.send(message), { once: true });
      return new Promise((resolve) => waiting.current.set(cell, resolve));
    },
    [connect],
  );

  const interrupt = useCallback(() => {
    socket.current?.send(JSON.stringify({ type: "interrupt" }));
  }, []);

  const restart = useCallback(() => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: "restart" }));
    }
    for (const cell of [...waiting.current.keys()]) finish(cell, false);
    setOutputs({});
    setAiCalls({});
    setCounts({});
    setDeadReason("");
  }, [finish]);

  return { state, outputs, aiCalls, running, counts, deadReason, execute, interrupt, restart };
}
