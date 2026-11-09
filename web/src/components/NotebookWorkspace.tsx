import Editor, { useMonaco } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import {
  forwardRef,
  memo,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { NotebookMapping, PythonLanguageClient } from "../lsp";
import { type Cell, joinCells, newCellId, splitCells } from "../notebook";
import { registerSnippets } from "../snippets";
import { type AICall, useKernel } from "../useKernel";
import type { WorkspaceHandle, WorkspaceProps } from "../workspace";
import CellOutputView from "./CellOutputView";
import { insertAtCursor, prefersDark } from "./editorUtils";

type CodeEditor = Monaco.editor.IStandaloneCodeEditor;

/** Cells you run one at a time against a live kernel (Data Science). */
const NotebookWorkspace = forwardRef<WorkspaceHandle, WorkspaceProps>(function NotebookWorkspace(
  { sessionId, glossary, onChange, onBusyChange, onReady },
  ref,
) {
  const [cells, setCells] = useState<Cell[]>(() => splitCells(""));
  const [readOnly, setReadOnly] = useState(false);
  const cellsRef = useRef(cells);
  cellsRef.current = cells;
  const editors = useRef(new Map<string, CodeEditor>());
  const activeCell = useRef<string | null>(null);
  const focusNext = useRef<string | null>(null);
  const focusNames = useRef(new Set<string>());
  const lspRef = useRef<PythonLanguageClient | null>(null);
  const monaco = useMonaco();
  const kernel = useKernel(sessionId);

  const mapping = useMemo(
    () =>
      new NotebookMapping(() =>
        cellsRef.current
          .map((cell) => editors.current.get(cell.id)?.getModel())
          .filter((model): model is Monaco.editor.ITextModel => Boolean(model)),
      ),
    [],
  );

  const currentCode = useCallback(
    () => joinCells(cellsRef.current.map((c) => ({ code: editors.current.get(c.id)?.getValue() ?? c.code }))),
    [],
  );

  useEffect(() => onReady(), [onReady]);
  useEffect(() => onBusyChange(kernel.running.size > 0), [kernel.running, onBusyChange]);
  useEffect(() => mapping.changed(), [cells, mapping]);

  useEffect(() => {
    if (!monaco) return;
    const snippets = registerSnippets(monaco);
    return () => snippets.dispose();
  }, [monaco]);

  useEffect(() => {
    if (!sessionId || !monaco) return;
    const client = new PythonLanguageClient(sessionId, monaco, mapping);
    client.focusNames = focusNames.current;
    client.glossary = glossary;
    lspRef.current = client;
    return () => {
      client.dispose();
      lspRef.current = null;
    };
  }, [sessionId, monaco, mapping, glossary]);

  // --- cells -------------------------------------------------------------------

  const runCell = useCallback(
    async (id: string, advance: boolean) => {
      const editor = editors.current.get(id);
      if (!editor) return false;
      const run = kernel.execute(id, editor.getValue());
      if (advance) {
        const list = cellsRef.current;
        const index = list.findIndex((c) => c.id === id);
        if (index === list.length - 1) {
          const cell = { id: newCellId(), code: "" };
          focusNext.current = cell.id;
          setCells([...list, cell]);
        } else {
          editors.current.get(list[index + 1].id)?.focus();
        }
      }
      return run;
    },
    [kernel],
  );

  const runAll = useCallback(async () => {
    for (const cell of cellsRef.current) {
      const ok = await runCell(cell.id, false);
      if (!ok) break; // like Jupyter: stop at the first error
    }
  }, [runCell]);

  function addCellAfter(index: number) {
    const cell = { id: newCellId(), code: "" };
    focusNext.current = cell.id;
    setCells((list) => [...list.slice(0, index + 1), cell, ...list.slice(index + 1)]);
    queueChange();
  }

  function deleteCell(id: string) {
    setCells((list) => (list.length > 1 ? list.filter((c) => c.id !== id) : list));
    queueChange();
  }

  function moveCell(id: string, delta: -1 | 1) {
    setCells((list) => {
      const index = list.findIndex((c) => c.id === id);
      const target = index + delta;
      if (target < 0 || target >= list.length) return list;
      // Keep the edited text: cells remount when reordered.
      const synced = list.map((c) => ({ ...c, code: editors.current.get(c.id)?.getValue() ?? c.code }));
      [synced[index], synced[target]] = [synced[target], synced[index]];
      return synced;
    });
    queueChange();
  }

  function queueChange() {
    // After React has applied the new cell list.
    window.setTimeout(() => onChange(currentCode()), 0);
  }

  const onCellMount = useCallback((id: string, editor: CodeEditor) => {
    editors.current.set(id, editor);
    mapping.changed();
    if (focusNext.current === id) {
      focusNext.current = null;
      editor.focus();
    }
  }, [mapping]);

  const onCellUnmount = useCallback((id: string) => {
    editors.current.delete(id);
  }, []);

  const onCellEdit = useCallback(() => {
    mapping.changed();
    onChange(currentCode());
  }, [mapping, onChange, currentCode]);

  const onCellFocus = useCallback((id: string) => {
    activeCell.current = id;
  }, []);

  // --- handle ------------------------------------------------------------------

  useImperativeHandle(ref, () => ({
    getCode: currentCode,
    setCode: (code) => {
      if (code !== currentCode()) setCells(splitCells(code));
    },
    reset: () => kernel.restart(),
    run: () => void runAll(),
    insert: (text, importModule) => {
      const list = cellsRef.current;
      const target = editors.current.get(activeCell.current ?? "") ?? editors.current.get(list[list.length - 1].id);
      if (!target) return;
      insertAtCursor(target, text, null);
      const top = importModule?.split(".")[0];
      if (importModule && !new RegExp(`^\\s*(import|from)\\s+${top}\\b`, "m").test(currentCode())) {
        // Imports belong at the top of the notebook.
        editors.current.get(list[0].id)?.executeEdits("library", [
          { range: { startLineNumber: 1, startColumn: 1, endLineNumber: 1, endColumn: 1 }, text: `import ${importModule}\n` },
        ]);
      }
      target.focus();
    },
    setFocusNames: (names) => {
      focusNames.current = names;
      if (lspRef.current) lspRef.current.focusNames = names;
    },
    showSolution: (code) => {
      setReadOnly(true);
      setCells(splitCells(code));
    },
    restore: (code) => {
      setReadOnly(false);
      setCells(splitCells(code));
    },
  }));

  // --- render ------------------------------------------------------------------

  const busy = kernel.running.size > 0;
  return (
    <div className="notebook">
      <div className="notebook-head">
        <span className={`kernel-badge ${kernel.state}`}>
          Kernel: {KERNEL_LABEL[kernel.state]}
        </span>
        <span className="muted small">
          <kbd>Shift</kbd>+<kbd>Enter</kbd> runs a cell
        </span>
        <span className="spacer" />
        {busy && (
          <button className="small danger" onClick={kernel.interrupt}>
            ■ Interrupt
          </button>
        )}
        <button className="small" onClick={kernel.restart} title="Clear all variables and outputs">
          ↻ Restart
        </button>
      </div>
      {kernel.state === "dead" && (
        <div className="banner error">{kernel.deadReason} Run a cell to start a new kernel.</div>
      )}
      <div className="cells">
        {cells.map((cell, index) => (
          <div key={cell.id} className={`cell ${kernel.running.has(cell.id) ? "running" : ""}`}>
            <div className="cell-gutter">
              <button
                className="cell-run"
                onClick={() => runCell(cell.id, false)}
                disabled={!sessionId || readOnly}
                aria-label={`Run cell ${index + 1}`}
                title="Run this cell"
              >
                {kernel.running.has(cell.id) ? "…" : "▶"}
              </button>
              <span className="cell-count">[{kernel.counts[cell.id] ?? " "}]</span>
            </div>
            <div className="cell-main">
              <CellEditor
                cell={cell}
                readOnly={readOnly}
                onMount={onCellMount}
                onUnmount={onCellUnmount}
                onEdit={onCellEdit}
                onFocus={onCellFocus}
                onRun={runCell}
              />
              <AICallBadges calls={kernel.aiCalls[cell.id]} />
              {(kernel.outputs[cell.id] ?? []).map((output, i) => (
                <div key={i} className="cell-output">
                  <CellOutputView
                    output={output}
                    onGoToLine={(line) => {
                      const editor = editors.current.get(cell.id);
                      editor?.revealLine(line);
                      editor?.setSelection({ startLineNumber: line, startColumn: 1, endLineNumber: line, endColumn: 1000 });
                      editor?.focus();
                    }}
                  />
                </div>
              ))}
            </div>
            {!readOnly && (
              <div className="cell-actions">
                <button className="link small" onClick={() => moveCell(cell.id, -1)} disabled={index === 0} aria-label="Move cell up">↑</button>
                <button className="link small" onClick={() => moveCell(cell.id, 1)} disabled={index === cells.length - 1} aria-label="Move cell down">↓</button>
                <button className="link small" onClick={() => deleteCell(cell.id)} disabled={cells.length === 1} aria-label="Delete cell">✕</button>
                <button className="link small" onClick={() => addCellAfter(index)} aria-label="Add a cell below">＋</button>
              </div>
            )}
          </div>
        ))}
        {!readOnly && (
          <button className="add-cell" onClick={() => addCellAfter(cells.length - 1)}>
            ＋ Add cell
          </button>
        )}
      </div>
    </div>
  );
});

export default NotebookWorkspace;

const PROVIDER_NAME: Record<string, string> = { ollama: "Ollama", anthropic: "Claude", builtin: "built-in" };

/** Which model answered each dojo_ai call in a cell (summarised when there are many). */
function AICallBadges({ calls }: { calls: AICall[] | undefined }) {
  if (!calls?.length) return null;
  const failed = calls.filter((c) => !c.ok);
  const ok = calls.filter((c) => c.ok);
  const last = ok[ok.length - 1];
  const totalMs = calls.reduce((sum, c) => sum + c.ms, 0);
  return (
    <div className="ai-badges">
      {last && (
        <span className="ai-badge" title={`${ok.length} AI call(s)`}>
          🤖 via {PROVIDER_NAME[last.provider ?? ""] ?? last.provider}
          {last.model ? ` · ${last.model}` : ""} · {(totalMs / 1000).toFixed(1)}s
          {ok.length > 1 ? ` · ${ok.length} calls` : ""}
        </span>
      )}
      {failed.length > 0 && <span className="ai-badge failed">⚠ {failed.length} AI call(s) failed</span>}
    </div>
  );
}

const KERNEL_LABEL: Record<string, string> = {
  disconnected: "not started",
  starting: "starting…",
  idle: "ready",
  busy: "busy",
  dead: "stopped",
};

const LINE_HEIGHT = 21;

interface CellEditorProps {
  cell: Cell;
  readOnly: boolean;
  onMount: (id: string, editor: CodeEditor) => void;
  onUnmount: (id: string) => void;
  onEdit: () => void;
  onFocus: (id: string) => void;
  onRun: (id: string, advance: boolean) => void;
}

const CellEditor = memo(function CellEditor({ cell, readOnly, onMount, onUnmount, onEdit, onFocus, onRun }: CellEditorProps) {
  const [height, setHeight] = useState(() => (cell.code.split("\n").length + 1) * LINE_HEIGHT);
  const onRunRef = useRef(onRun);
  onRunRef.current = onRun;

  useEffect(() => () => onUnmount(cell.id), [cell.id, onUnmount]);

  return (
    <div className="cell-editor" style={{ height }}>
      <Editor
        path={`file:///work/cells/${cell.id}.py`}
        defaultLanguage="python"
        defaultValue={cell.code}
        theme={prefersDark() ? "vs-dark" : "vs"}
        onChange={onEdit}
        onMount={(editor, monaco) => {
          editor.onDidContentSizeChange((e) => setHeight(Math.min(640, Math.max(2 * LINE_HEIGHT, e.contentHeight + 8))));
          editor.onDidFocusEditorText(() => onFocus(cell.id));
          editor.addCommand(monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => onRunRef.current(cell.id, true));
          editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => onRunRef.current(cell.id, false));
          onMount(cell.id, editor);
        }}
        options={{
          readOnly,
          fontSize: 14,
          lineHeight: LINE_HEIGHT,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          scrollbar: { vertical: "hidden", alwaysConsumeMouseWheel: false },
          overviewRulerLanes: 0,
          folding: false,
          glyphMargin: false,
          lineNumbersMinChars: 3,
          renderLineHighlight: "none",
          tabSize: 4,
          insertSpaces: true,
          automaticLayout: true,
          quickSuggestions: { other: true, comments: false, strings: false },
          wordBasedSuggestions: "off",
          fixedOverflowWidgets: true,
        }}
      />
    </div>
  );
});
