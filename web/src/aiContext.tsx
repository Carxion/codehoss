import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { aiApi, PROVIDER_LABEL, type AIStatus } from "./api";
import AISettings from "./components/AISettings";

// Which AI model answers dojo_ai calls is shown in the top bar and in AI lessons, and
// both open the same settings panel. This context keeps them in sync.

interface AIContextValue {
  status: AIStatus | null;
  label: string;
  openSettings: () => void;
  refresh: () => Promise<void>;
}

const AIContext = createContext<AIContextValue>({
  status: null,
  label: "AI: not set up",
  openSettings: () => {},
  refresh: async () => {},
});

export function AIProviderRoot({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await aiApi.status());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const current = status?.current;
  const label = current
    ? `AI: ${PROVIDER_LABEL[current.provider]}${current.model ? ` · ${current.model}` : ""}`
    : "AI: not set up";

  return (
    <AIContext.Provider value={{ status, label, openSettings: () => setOpen(true), refresh }}>
      {children}
      {open && (
        <AISettings
          status={status}
          onSaved={setStatus}
          onClose={() => {
            setOpen(false);
            void refresh();
          }}
        />
      )}
    </AIContext.Provider>
  );
}

export const useAI = () => useContext(AIContext);
