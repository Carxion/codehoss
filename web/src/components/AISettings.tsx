import { useEffect, useRef, useState, type FormEvent } from "react";
import { aiApi, type AIProvider, type AIStatus, type AITestResult } from "../api";

interface Props {
  status: AIStatus | null;
  onSaved: (status: AIStatus) => void;
  onClose: () => void;
}

/** Pick the model that answers dojo_ai calls: local Ollama or Claude with your key. */
export default function AISettings({ status, onSaved, onClose }: Props) {
  const [provider, setProvider] = useState<AIProvider | null>(status?.provider ?? null);
  const [ollamaModel, setOllamaModel] = useState(
    status?.ollama.selected_model ?? status?.ollama.models[0] ?? "",
  );
  const [claudeModel, setClaudeModel] = useState(
    status?.anthropic.selected_model ?? status?.anthropic.models[0] ?? "",
  );
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [test, setTest] = useState<AITestResult | null>(null);
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialog.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!status) {
    return (
      <Shell dialog={dialog} onClose={onClose}>
        <p className="muted">Loading AI settings…</p>
      </Shell>
    );
  }

  const { ollama, anthropic } = status;

  async function save(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    setTest(null);
    try {
      const saved = await aiApi.save({
        provider,
        model: provider === "ollama" ? ollamaModel || null : provider === "anthropic" ? claudeModel : null,
        api_key: provider === "anthropic" && apiKey ? apiKey : undefined,
      });
      onSaved(saved);
      setApiKey("");
      if (provider) setTest(await aiApi.test());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function forgetKey() {
    const saved = await aiApi.save({
      provider: provider === "anthropic" ? null : provider,
      model: provider === "ollama" ? ollamaModel : null,
      clear_key: true,
    });
    onSaved(saved);
    if (provider === "anthropic") setProvider(null);
  }

  return (
    <Shell dialog={dialog} onClose={onClose}>
      <p className="muted">
        AI lessons call a model with <code>dojo_ai.chat(...)</code>. Choose which one answers. Your code stays the
        same either way, and you can switch at any time.
      </p>
      <form onSubmit={save}>
        <div className="ai-options" role="radiogroup" aria-label="AI model">
          {/* A card, not a <label>: it contains its own form fields. */}
          <div
            className={`ai-option ${provider === "ollama" ? "selected" : ""}`}
            onClick={() => setProvider("ollama")}
          >
            <input
              id="ai-provider-ollama"
              type="radio"
              name="provider"
              checked={provider === "ollama"}
              onChange={() => setProvider("ollama")}
            />
            <div>
              <label htmlFor="ai-provider-ollama">
                <strong>Local model (Ollama)</strong>
              </label>
              <span className="pill">free · private · offline</span>
              <p className="muted small">Runs on this computer. Nothing leaves the machine.</p>
              {ollama.available ? (
                <>
                  <p className="ok-text small">✓ Ollama is running at {ollama.url}</p>
                  {ollama.models.length ? (
                    <label className="field">
                      Model
                      <select
                        aria-label="Ollama model"
                        value={ollamaModel}
                        onChange={(e) => setOllamaModel(e.target.value)}
                      >
                        {ollama.models.map((m) => (
                          <option key={m}>{m}</option>
                        ))}
                      </select>
                    </label>
                  ) : (
                    <p className="small">
                      No chat models yet. In a terminal run <code>ollama pull llama3.2</code>, then reopen this panel.
                    </p>
                  )}
                  <p className="muted small">
                    Embeddings:{" "}
                    {ollama.embedding ? (
                      <>nomic-embed-text ✓</>
                    ) : (
                      <>
                        built-in simple embeddings (for better ones: <code>ollama pull nomic-embed-text</code>)
                      </>
                    )}
                  </p>
                </>
              ) : (
                <p className="small error-text">
                  Ollama isn't running. Install it from ollama.com, start it, and run{" "}
                  <code>ollama pull llama3.2</code>.
                </p>
              )}
            </div>
          </div>

          <div
            className={`ai-option ${provider === "anthropic" ? "selected" : ""}`}
            onClick={() => setProvider("anthropic")}
          >
            <input
              id="ai-provider-anthropic"
              type="radio"
              name="provider"
              checked={provider === "anthropic"}
              onChange={() => setProvider("anthropic")}
            />
            <div>
              <label htmlFor="ai-provider-anthropic">
                <strong>Hosted model (Claude)</strong>
              </label>
              <span className="pill">your API key · usage billed to you</span>
              <p className="muted small">
                Anthropic's Claude models. Get a key at console.anthropic.com. Requests go from the CodeHoss server to
                Anthropic. Your key is stored encrypted and never enters your notebook or code.
              </p>
              <label className="field">
                API key
                <input
                  type="password"
                  aria-label="Anthropic API key"
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    if (e.target.value) setProvider("anthropic");
                  }}
                  placeholder={anthropic.configured ? `Saved key ${anthropic.key_hint}. Type to replace it` : "sk-ant-…"}
                  autoComplete="off"
                />
              </label>
              {anthropic.configured && (
                <button type="button" className="link small" onClick={forgetKey}>
                  Forget saved key
                </button>
              )}
              <label className="field">
                Model
                <select aria-label="Claude model" value={claudeModel} onChange={(e) => setClaudeModel(e.target.value)}>
                  {anthropic.models.map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </label>
              <p className="muted small">Embeddings use the built-in simple embeddings (Claude has no embeddings service).</p>
            </div>
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}
        {test && (
          <div className={`feedback ${test.ok ? "pass" : "fail"}`} role="status">
            {test.ok ? (
              <>
                ✓ Connected: {test.model} replied “{test.reply}” in {(test.ms / 1000).toFixed(1)}s
              </>
            ) : (
              <>✗ {test.error}</>
            )}
          </div>
        )}
        <div className="dialog-actions">
          <button type="button" onClick={onClose}>
            Close
          </button>
          <button className="primary" disabled={busy || !provider}>
            {busy ? "Saving and testing…" : "Save and test"}
          </button>
        </div>
      </form>
    </Shell>
  );
}

function Shell({
  dialog,
  onClose,
  children,
}: {
  dialog: React.RefObject<HTMLDivElement | null>;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog card" role="dialog" aria-modal="true" aria-labelledby="ai-settings-title" tabIndex={-1} ref={dialog}>
        <div className="dialog-head">
          <h2 id="ai-settings-title">AI model</h2>
          <button className="link" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
