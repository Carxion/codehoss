import type * as Monaco from "monaco-editor";

/** Insert text at the cursor; put the cursor inside "()" and add the import if needed. */
export function insertAtCursor(
  editor: Monaco.editor.IStandaloneCodeEditor,
  text: string,
  importModule: string | null,
  /** The whole program, when the import should check more than this editor (notebooks). */
  allCode?: string,
) {
  const model = editor.getModel();
  if (!model) return;
  editor.executeEdits("library", [{ range: editor.getSelection()!, text, forceMoveMarkers: true }]);
  if (text.endsWith("()")) {
    const position = editor.getPosition()!;
    editor.setPosition({ lineNumber: position.lineNumber, column: position.column - 1 });
  }
  const top = importModule?.split(".")[0];
  const imported = top && new RegExp(`^\\s*(import|from)\\s+${top}\\b`, "m").test(allCode ?? model.getValue());
  if (importModule && !imported) {
    editor.executeEdits("library", [
      {
        range: { startLineNumber: 1, startColumn: 1, endLineNumber: 1, endColumn: 1 },
        text: `import ${importModule}\n`,
      },
    ]);
  }
  editor.focus();
}

export function prefersDark() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}
