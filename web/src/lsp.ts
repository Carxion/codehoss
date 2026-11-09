// Minimal LSP client: Monaco <-> basedpyright (in the sandbox) over a WebSocket.
//
// We implement just what the beginner editor needs (completion, hover, signature help,
// diagnostics) instead of pulling in a full VS Code layer. That keeps the bundle small
// and lets us post-process results: lesson-aware ranking, beginner glossary notes on
// hover, and friendlier diagnostics.
//
// The server always sees ONE document. A DocumentMapping says how editor models map
// onto it: the plain editor is one model; a notebook stitches its cells together so
// names from earlier cells are known in later ones.

import type * as Monaco from "monaco-editor";
import { wsUrl } from "./api";

type Json = any; // eslint-disable-line @typescript-eslint/no-explicit-any
type Model = Monaco.editor.ITextModel;

export interface DocumentMapping {
  uri: string;
  text(): string;
  models(): Model[];
  /** Editor position -> 0-based document line/character, or null if not ours. */
  toDocument(model: Model, position: Monaco.IPosition): { line: number; character: number } | null;
  /** 0-based document line -> the model and 1-based line it belongs to. */
  fromDocument(line: number): { model: Model; lineNumber: number } | null;
  onDidChange(listener: () => void): Monaco.IDisposable;
}

export class SingleModelMapping implements DocumentMapping {
  uri = "file:///work/main.py";
  constructor(private model: Model) {}
  text = () => this.model.getValue();
  models = () => [this.model];
  toDocument(model: Model, p: Monaco.IPosition) {
    return model === this.model ? { line: p.lineNumber - 1, character: p.column - 1 } : null;
  }
  fromDocument(line: number) {
    return { model: this.model, lineNumber: line + 1 };
  }
  onDidChange(listener: () => void) {
    return this.model.onDidChangeContent(listener);
  }
}

/** Notebook cells as one document: a prelude, then "# %%" + each cell's lines. */
export class NotebookMapping implements DocumentMapping {
  uri = "file:///work/notebook.py";
  // display() exists in notebooks; tell the type checker about it.
  private prelude = ["from IPython.display import display"];
  private listeners = new Set<() => void>();
  constructor(private cells: () => Model[]) {}

  models = () => this.cells();

  private starts(): number[] {
    let line = this.prelude.length;
    return this.cells().map((model) => {
      const start = line + 1; // after the "# %%" marker
      line = start + model.getLineCount();
      return start;
    });
  }

  text() {
    const parts = [...this.prelude];
    for (const model of this.cells()) parts.push("# %%", model.getValue());
    return parts.join("\n");
  }

  toDocument(model: Model, p: Monaco.IPosition) {
    const index = this.cells().indexOf(model);
    if (index < 0) return null;
    return { line: this.starts()[index] + p.lineNumber - 1, character: p.column - 1 };
  }

  fromDocument(line: number) {
    const cells = this.cells();
    const starts = this.starts();
    for (let i = 0; i < cells.length; i++) {
      if (line >= starts[i] && line < starts[i] + cells[i].getLineCount()) {
        return { model: cells[i], lineNumber: line - starts[i] + 1 };
      }
    }
    return null;
  }

  /** Call when cells are added, removed, reordered or edited. */
  changed() {
    this.listeners.forEach((listener) => listener());
  }

  onDidChange(listener: () => void) {
    this.listeners.add(listener);
    return { dispose: () => this.listeners.delete(listener) };
  }
}

const ANALYSIS_SETTINGS = {
  typeCheckingMode: "basic",
  diagnosticMode: "openFilesOnly",
  autoImportCompletions: false,
  // A bare expression is how notebooks show a value; don't flag it.
  diagnosticSeverityOverrides: { reportUnusedExpression: "none" },
  inlayHints: { variableTypes: false, callArgumentNames: false, functionReturnTypes: false },
};

// LSP CompletionItemKind -> Monaco CompletionItemKind name
const KIND_NAMES: Record<number, keyof typeof Monaco.languages.CompletionItemKind> = {
  1: "Text", 2: "Method", 3: "Function", 4: "Constructor", 5: "Field", 6: "Variable",
  7: "Class", 8: "Interface", 9: "Module", 10: "Property", 11: "Unit", 12: "Value",
  13: "Enum", 14: "Keyword", 15: "Snippet", 16: "Color", 17: "File", 18: "Reference",
  19: "Folder", 20: "EnumMember", 21: "Constant", 22: "Struct", 23: "Event",
  24: "Operator", 25: "TypeParameter",
};

export class PythonLanguageClient {
  private socket: WebSocket;
  private nextId = 1;
  private pending = new Map<number, (result: Json) => void>();
  private version = 1;
  private opened = false;
  private ready: Promise<void>;
  private disposables: Monaco.IDisposable[] = [];
  private changeTimer: number | null = null;
  private markedModels = new Set<Model>();
  /** Names the current lesson step is about; their completions rank first. */
  focusNames = new Set<string>();
  /** Beginner notes (glossary.yaml), shown on hover before the official docs. */
  glossary: Record<string, string> = {};

  constructor(
    sessionId: string,
    private monaco: typeof Monaco,
    private mapping: DocumentMapping,
  ) {
    this.socket = new WebSocket(wsUrl(`/sessions/${sessionId}/lsp`));
    this.socket.onmessage = (event) => this.receive(JSON.parse(event.data));
    this.ready = new Promise((resolve, reject) => {
      this.socket.onopen = () => this.initialize().then(resolve, reject);
      this.socket.onerror = () => reject(new Error("language server connection failed"));
    });
    this.registerProviders();
    this.disposables.push(mapping.onDidChange(() => this.scheduleChange()));
  }

  dispose() {
    this.disposables.forEach((d) => d.dispose());
    if (this.changeTimer !== null) window.clearTimeout(this.changeTimer);
    for (const model of this.markedModels) {
      if (!model.isDisposed()) this.monaco.editor.setModelMarkers(model, "pyright", []);
    }
    this.socket.close();
  }

  // --- protocol ----------------------------------------------------------------

  private send(message: Json) {
    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ jsonrpc: "2.0", ...message }));
    }
  }

  private request(method: string, params: Json): Promise<Json> {
    const id = this.nextId++;
    return new Promise((resolve) => {
      this.pending.set(id, resolve);
      this.send({ id, method, params });
    });
  }

  private notify(method: string, params: Json) {
    this.send({ method, params });
  }

  private receive(message: Json) {
    if (message.id !== undefined && message.method === undefined) {
      this.pending.get(message.id)?.(message.result ?? null);
      this.pending.delete(message.id);
      return;
    }
    if (message.method && message.id !== undefined) {
      this.send({ id: message.id, result: this.answerServerRequest(message) });
      return;
    }
    if (message.method === "textDocument/publishDiagnostics") {
      this.showDiagnostics(message.params);
    }
  }

  private answerServerRequest(message: Json): Json {
    if (message.method === "workspace/configuration") {
      return message.params.items.map((item: Json) =>
        item.section === "basedpyright.analysis" || item.section === "python.analysis"
          ? ANALYSIS_SETTINGS
          : item.section === "basedpyright"
            ? { analysis: ANALYSIS_SETTINGS }
            : {},
      );
    }
    return null; // client/registerCapability, window/workDoneProgress/create, ...
  }

  private async initialize() {
    await this.request("initialize", {
      processId: null,
      rootUri: "file:///work",
      workspaceFolders: [{ uri: "file:///work", name: "work" }],
      capabilities: {
        workspace: { configuration: true },
        textDocument: {
          synchronization: { didSave: false },
          completion: {
            completionItem: {
              snippetSupport: true,
              documentationFormat: ["markdown", "plaintext"],
            },
          },
          hover: { contentFormat: ["markdown", "plaintext"] },
          signatureHelp: {
            signatureInformation: {
              documentationFormat: ["markdown", "plaintext"],
              parameterInformation: { labelOffsetSupport: true },
            },
          },
          publishDiagnostics: {},
        },
      },
    });
    this.notify("initialized", {});
    this.notify("workspace/didChangeConfiguration", { settings: {} });
    this.notify("textDocument/didOpen", {
      textDocument: {
        uri: this.mapping.uri,
        languageId: "python",
        version: this.version,
        text: this.mapping.text(),
      },
    });
    this.opened = true;
  }

  private scheduleChange() {
    // Coalesce bursts (typing, or a notebook replacing all its cells).
    if (this.changeTimer !== null) window.clearTimeout(this.changeTimer);
    this.changeTimer = window.setTimeout(() => {
      this.changeTimer = null;
      this.flushChange();
    }, 50);
  }

  private flushChange() {
    if (!this.opened) return;
    this.notify("textDocument/didChange", {
      textDocument: { uri: this.mapping.uri, version: ++this.version },
      contentChanges: [{ text: this.mapping.text() }],
    });
  }

  /** Requests must see the latest text, even if a change is still being coalesced. */
  private async prepare(model: Model, position: Monaco.IPosition) {
    await this.ready;
    if (this.changeTimer !== null) {
      window.clearTimeout(this.changeTimer);
      this.changeTimer = null;
      this.flushChange();
    }
    return this.mapping.toDocument(model, position);
  }

  // --- features ----------------------------------------------------------------

  private registerProviders() {
    const { languages } = this.monaco;

    this.disposables.push(
      languages.registerCompletionItemProvider("python", {
        triggerCharacters: ["."],
        provideCompletionItems: async (model, position) => {
          const at = await this.prepare(model, position);
          if (!at) return { suggestions: [] };
          const result = await this.request("textDocument/completion", {
            textDocument: { uri: this.mapping.uri },
            position: at,
          });
          const items: Json[] = Array.isArray(result) ? result : (result?.items ?? []);
          const word = model.getWordUntilPosition(position);
          // Private names (_like_this) are noise for beginners unless they typed "_".
          const visible = word.word.startsWith("_") ? items : items.filter((i) => !String(i.label).startsWith("_"));
          const range = new this.monaco.Range(
            position.lineNumber,
            word.startColumn,
            position.lineNumber,
            word.endColumn,
          );
          return { suggestions: visible.map((item) => this.toSuggestion(item, range)) };
        },
        resolveCompletionItem: async (suggestion) => {
          const original = (suggestion as Json)._lsp;
          if (!original || suggestion.documentation) return suggestion;
          const resolved = await this.request("completionItem/resolve", original);
          if (resolved?.documentation) suggestion.documentation = toMarkdown(resolved.documentation);
          if (resolved?.detail) suggestion.detail = resolved.detail;
          return suggestion;
        },
      }),
      languages.registerHoverProvider("python", {
        provideHover: async (model, position) => {
          const at = await this.prepare(model, position);
          if (!at) return null;
          const result = await this.request("textDocument/hover", {
            textDocument: { uri: this.mapping.uri },
            position: at,
          });
          const contents: Monaco.IMarkdownString[] = [];
          const word = model.getWordAtPosition(position)?.word;
          if (word && this.glossary[word]) contents.push({ value: `💡 ${this.glossary[word]}` });
          if (result?.contents) {
            const raw = Array.isArray(result.contents) ? result.contents : [result.contents];
            contents.push(...raw.map(toMarkdown));
          }
          return contents.length ? { contents } : null;
        },
      }),
      languages.registerSignatureHelpProvider("python", {
        signatureHelpTriggerCharacters: ["(", ","],
        provideSignatureHelp: async (model, position) => {
          const at = await this.prepare(model, position);
          if (!at) return null;
          const result = await this.request("textDocument/signatureHelp", {
            textDocument: { uri: this.mapping.uri },
            position: at,
          });
          if (!result?.signatures?.length) return null;
          return {
            value: {
              activeSignature: result.activeSignature ?? 0,
              activeParameter: result.activeParameter ?? 0,
              signatures: result.signatures.map((sig: Json) => ({
                label: sig.label,
                documentation: sig.documentation ? toMarkdown(sig.documentation) : undefined,
                activeParameter: sig.activeParameter,
                parameters: (sig.parameters ?? []).map((param: Json) => ({
                  label: param.label,
                  documentation: param.documentation ? toMarkdown(param.documentation) : undefined,
                })),
              })),
            },
            dispose() {},
          };
        },
      }),
    );
  }

  private toSuggestion(item: Json, range: Monaco.IRange): Monaco.languages.CompletionItem {
    const { languages } = this.monaco;
    const kindName = KIND_NAMES[item.kind as number] ?? "Text";
    const insert = item.textEdit?.newText ?? item.insertText ?? item.label;
    const focused = this.focusNames.has(item.label);
    const note = this.glossary[item.label];
    return {
      label: item.label,
      kind: languages.CompletionItemKind[kindName],
      detail: item.detail,
      documentation: note
        ? { value: `💡 ${note}` }
        : item.documentation
          ? toMarkdown(item.documentation)
          : undefined,
      insertText: insert,
      insertTextRules:
        item.insertTextFormat === 2
          ? languages.CompletionItemInsertTextRule.InsertAsSnippet
          : undefined,
      // Lesson-aware ranking: what this step teaches comes first.
      sortText: focused ? `0_${item.label}` : `1_${item.sortText ?? item.label}`,
      preselect: focused,
      range,
      _lsp: item,
    } as Monaco.languages.CompletionItem;
  }

  private showDiagnostics(params: Json) {
    if (params.uri !== this.mapping.uri) return;
    const severity = this.monaco.MarkerSeverity;
    const toSeverity = (s: number) =>
      s === 1 ? severity.Error : s === 2 ? severity.Warning : s === 3 ? severity.Info : severity.Hint;
    const byModel = new Map<Model, Monaco.editor.IMarkerData[]>();
    for (const model of this.mapping.models()) byModel.set(model, []);
    for (const d of params.diagnostics as Json[]) {
      const start = this.mapping.fromDocument(d.range.start.line);
      if (!start) continue; // e.g. on a "# %%" marker line
      const sameLine = d.range.end.line === d.range.start.line;
      byModel.get(start.model)?.push({
        severity: toSeverity(d.severity ?? 1),
        message: friendlyDiagnostic(d.message),
        startLineNumber: start.lineNumber,
        startColumn: d.range.start.character + 1,
        endLineNumber: sameLine ? start.lineNumber : start.lineNumber + (d.range.end.line - d.range.start.line),
        endColumn: d.range.end.character + 1,
      });
    }
    for (const [model, markers] of byModel) {
      if (model.isDisposed()) continue;
      this.monaco.editor.setModelMarkers(model, "pyright", markers);
      this.markedModels.add(model);
    }
  }
}

function toMarkdown(content: Json): Monaco.IMarkdownString {
  if (typeof content === "string") return { value: content };
  if (content.kind === "markdown" || content.kind === "plaintext") {
    return { value: content.kind === "plaintext" ? escapeMarkdown(content.value) : content.value };
  }
  if (content.language) return { value: "```" + content.language + "\n" + content.value + "\n```" };
  return { value: String(content.value ?? "") };
}

function escapeMarkdown(text: string) {
  return text.replace(/[\\`*_{}[\]()#+\-.!]/g, "\\$&");
}

/** Put pyright's terse messages in beginner terms where we can. */
function friendlyDiagnostic(message: string): string {
  const undefinedName = message.match(/^"(\w+)" is not defined/);
  if (undefinedName) {
    return `Python doesn't know "${undefinedName[1]}" yet. Check the spelling, or create it with = first.`;
  }
  if (message.startsWith('Operator "+" not supported for types "str" and "int"')) {
    return 'You can\'t add text and a number with +. Use str(...) or an f-string like f"{x}".';
  }
  return message;
}
