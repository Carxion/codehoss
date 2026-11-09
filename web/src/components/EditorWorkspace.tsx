import Editor, { type OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { PythonLanguageClient, SingleModelMapping } from "../lsp";
import { registerSnippets } from "../snippets";
import { useRunner } from "../useRunner";
import type { WorkspaceHandle, WorkspaceProps } from "../workspace";
import Console from "./Console";
import { insertAtCursor, prefersDark } from "./editorUtils";

/** One file, one Run button, and an interactive console (Python Basics). */
const EditorWorkspace = forwardRef<WorkspaceHandle, WorkspaceProps>(function EditorWorkspace(
  { sessionId, glossary, onChange, onBusyChange, onReady },
  ref,
) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const lspRef = useRef<PythonLanguageClient | null>(null);
  const focusNames = useRef(new Set<string>());
  const animation = useRef<number | null>(null);
  const suppressChange = useRef(false);
  const [editorReady, setEditorReady] = useState(false);
  const runner = useRunner(sessionId);

  useEffect(() => onBusyChange(runner.running), [runner.running, onBusyChange]);

  useEffect(() => {
    if (!sessionId || !editorReady || !monacoRef.current || !editorRef.current) return;
    const client = new PythonLanguageClient(
      sessionId,
      monacoRef.current,
      new SingleModelMapping(editorRef.current.getModel()!),
    );
    client.focusNames = focusNames.current;
    client.glossary = glossary;
    lspRef.current = client;
    return () => {
      client.dispose();
      lspRef.current = null;
    };
  }, [sessionId, editorReady, glossary]);

  useEffect(() => () => stopAnimation(), []);

  function stopAnimation() {
    if (animation.current !== null) window.clearInterval(animation.current);
    animation.current = null;
  }

  function setValue(code: string) {
    suppressChange.current = true;
    editorRef.current?.setValue(code);
    suppressChange.current = false;
  }

  const run = () => {
    if (!runner.running && editorRef.current) runner.run(editorRef.current.getValue());
  };
  const runRef = useRef(run);
  runRef.current = run;

  useImperativeHandle(ref, () => ({
    getCode: () => editorRef.current?.getValue() ?? "",
    setCode: (code) => {
      if (code !== editorRef.current?.getValue()) setValue(code);
    },
    reset: () => runner.clear(),
    run: () => runRef.current(),
    insert: (text, importModule) => {
      if (editorRef.current) insertAtCursor(editorRef.current, text, importModule);
    },
    setFocusNames: (names) => {
      focusNames.current = names;
      if (lspRef.current) lspRef.current.focusNames = names;
    },
    showSolution: (solution) => {
      const editor = editorRef.current;
      if (!editor) return;
      editor.updateOptions({ readOnly: true });
      const chunk = Math.max(1, Math.ceil(solution.length / 80));
      let shown = 0;
      stopAnimation();
      animation.current = window.setInterval(() => {
        shown = Math.min(solution.length, shown + chunk);
        setValue(solution.slice(0, shown));
        if (shown >= solution.length) stopAnimation();
      }, 20);
    },
    restore: (code) => {
      stopAnimation();
      editorRef.current?.updateOptions({ readOnly: false });
      setValue(code);
    },
  }));

  const onMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    const snippets = registerSnippets(monaco);
    editor.onDidDispose(() => snippets.dispose());
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => runRef.current());
    setEditorReady(true);
    onReady();
  };

  function goToLine(line: number) {
    const editor = editorRef.current;
    if (!editor) return;
    editor.revealLineInCenter(line);
    editor.setSelection({ startLineNumber: line, startColumn: 1, endLineNumber: line, endColumn: 1000 });
    editor.focus();
  }

  return (
    <>
      <div className="editor-wrap">
        <Editor
          path="file:///work/main.py"
          defaultLanguage="python"
          theme={prefersDark() ? "vs-dark" : "vs"}
          onMount={onMount}
          onChange={(value) => {
            if (!suppressChange.current && value !== undefined) onChange(value);
          }}
          options={{
            fontSize: 15,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            tabSize: 4,
            insertSpaces: true,
            automaticLayout: true,
            quickSuggestions: { other: true, comments: false, strings: false },
            suggestOnTriggerCharacters: true,
            parameterHints: { enabled: true },
            wordBasedSuggestions: "off",
            fixedOverflowWidgets: true,
          }}
        />
      </div>
      <Console
        output={runner.output}
        running={runner.running}
        exit={runner.exit}
        onInput={runner.sendInput}
        onStop={runner.stop}
        onGoToLine={goToLine}
      />
    </>
  );
});

export default EditorWorkspace;
