import type { Language } from "./api";

// The lesson view drives either workspace (code editor or notebook) through this handle,
// so step logic (drafts, Check, hints, show-me, Library insert) doesn't care which it is.

export interface WorkspaceHandle {
  getCode(): string;
  setCode(code: string): void;
  /** Clear outputs (and restart the notebook kernel) when moving to another step. */
  reset(): void;
  run(): void;
  insert(text: string, importModule: string | null): void;
  setFocusNames(names: Set<string>): void;
  /** "Show me": display the solution read-only (the editor types it out). */
  showSolution(code: string): void;
  /** Leave show-me: make it editable again with this code. */
  restore(code: string): void;
  /** Pseudocode only: open the step-through view for the current code. */
  stepThrough?(): void;
}

export interface WorkspaceProps {
  sessionId: string | null;
  language?: Language;
  glossary: Record<string, string>;
  onChange: (code: string) => void;
  onBusyChange: (busy: boolean) => void;
  onReady: () => void;
}
