import { useEffect, useRef, useState } from "react";
import { askTutor, PROVIDER_LABEL, type TutorMessage, type TutorRequest } from "../api";
import { useAI } from "../aiContext";
import Markdown from "./Markdown";

// The AI tutor, beside the lesson. It sees the step, the learner's code and the last
// Check (gathered at send time by `context`), and nudges rather than solves; the server
// hides any reply that repeats the solution. One conversation per step, kept for the
// browser session.

interface Props {
  conversationKey: string;
  context: () => Omit<TutorRequest, "messages">;
  suggestions: string[];
  /** A question to send straight away (e.g. "Ask the tutor why" under a failed Check). */
  pending: string | null;
  onPendingSent: () => void;
  onClose: () => void;
}

interface Turn extends TutorMessage {
  model?: string;
  error?: boolean;
}

const STORE = "dojo.tutor.";

function load(key: string): Turn[] {
  try {
    return JSON.parse(sessionStorage.getItem(STORE + key) ?? "[]");
  } catch {
    return [];
  }
}

function save(key: string, turns: Turn[]) {
  try {
    sessionStorage.setItem(STORE + key, JSON.stringify(turns.slice(-40)));
  } catch {
    /* storage full or blocked: the conversation just won't survive a reload */
  }
}

export default function TutorPanel({ conversationKey, context, suggestions, pending, onPendingSent, onClose }: Props) {
  const ai = useAI();
  const [turns, setTurns] = useState<Turn[]>(() => load(conversationKey));
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement | null>(null);
  const ready = Boolean(ai.status?.current);

  useEffect(() => {
    abort.current?.abort();
    setTurns(load(conversationKey));
  }, [conversationKey]);

  useEffect(() => {
    if (!busy) save(conversationKey, turns);
    bottom.current?.scrollIntoView({ block: "end" });
  }, [turns, busy, conversationKey]);

  useEffect(() => {
    if (pending && ready && !busy) {
      onPendingSent();
      void send(pending);
    }
  }, [pending, ready, busy]);

  useEffect(() => () => abort.current?.abort(), []);

  async function send(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    const asked: TutorMessage = { role: "user", content: text };
    const history: TutorMessage[] = [...turns.filter((t) => !t.error), asked].map(({ role, content }) => ({
      role,
      content,
    }));
    setTurns((t) => [...t, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setDraft("");
    setBusy(true);
    const controller = new AbortController();
    abort.current = controller;
    const update = (change: (last: Turn) => Turn) =>
      setTurns((t) => [...t.slice(0, -1), change(t[t.length - 1])]);
    try {
      await askTutor(
        { ...context(), messages: history },
        (event) => {
          if (event.type === "meta") update((last) => ({ ...last, model: `${PROVIDER_LABEL[event.provider]} · ${event.model}` }));
          else if (event.type === "text") update((last) => ({ ...last, content: last.content + event.text }));
          else if (event.type === "error") update((last) => ({ ...last, content: event.message, error: true }));
        },
        controller.signal,
      );
    } catch (e) {
      if (!controller.signal.aborted) update((last) => ({ ...last, content: (e as Error).message, error: true }));
    } finally {
      setBusy(false);
      // A stopped or failed reply with nothing in it isn't worth keeping.
      setTurns((t) => (t.length && !t[t.length - 1].content ? t.slice(0, -2) : t));
    }
  }

  function startOver() {
    abort.current?.abort();
    setTurns([]);
  }

  return (
    <aside className="tutor" aria-label="AI tutor">
      <div className="tutor-head">
        <strong>🧑‍🏫 Tutor</strong>
        <span className="spacer" />
        {turns.length > 0 && (
          <button className="link small" onClick={startOver} disabled={busy}>
            New chat
          </button>
        )}
        <button className="link" onClick={onClose} aria-label="Close the tutor">
          ✕
        </button>
      </div>
      <button className="tutor-model small" onClick={ai.openSettings} title="Change which AI model answers">
        {ready ? ai.label.replace("AI: ", "via ") : "Set up AI first"}
      </button>

      <div className="tutor-log" aria-live="polite">
        {turns.length === 0 && (
          <div className="tutor-intro small">
            <p>
              Ask about this step: an error, a failing test, or what to try next. The tutor sees the lesson and your code,
              and helps you find the answer yourself; it won't write it for you.
            </p>
            {!ready && (
              <p>
                It runs on the AI model you choose: local with Ollama (free, private) or Claude with your own key.{" "}
                <button className="link small" onClick={ai.openSettings}>
                  Set up AI
                </button>
              </p>
            )}
          </div>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={`tutor-turn ${turn.role} ${turn.error ? "error" : ""}`}>
            {turn.role === "assistant" ? (
              turn.content ? (
                <Markdown>{turn.content}</Markdown>
              ) : (
                <span className="muted small">Thinking…</span>
              )
            ) : (
              <p>{turn.content}</p>
            )}
            {turn.model && !turn.error && <span className="tutor-via">{turn.model}</span>}
          </div>
        ))}
        <div ref={bottom} />
      </div>

      {ready && !busy && (
        <div className="tutor-suggestions">
          {suggestions.filter((s) => !turns.some((t) => t.role === "user" && t.content === s)).map((s) => (
            <button key={s} className="small" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        className="tutor-input"
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(draft);
            }
          }}
          placeholder={ready ? "Ask the tutor… (Enter to send)" : "Choose an AI model to use the tutor"}
          disabled={!ready}
          rows={2}
          aria-label="Your question"
        />
        {busy ? (
          <button type="button" onClick={() => abort.current?.abort()}>
            ■ Stop
          </button>
        ) : (
          <button type="submit" className="primary" disabled={!ready || !draft.trim()}>
            Send
          </button>
        )}
      </form>
    </aside>
  );
}
