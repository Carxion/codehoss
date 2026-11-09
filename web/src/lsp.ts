// Minimal LSP client: Monaco <-> basedpyright (in the sandbox) over a WebSocket.
//
// We implement just what the beginner editor needs (completion, hover, signature help,
// diagnostics) instead of pulling in a full VS Code layer. That keeps the bundle small
// and lets us post-process results: lesson-aware ranking and friendlier diagnostics.

import type * as Monaco from "monaco-editor";
import { wsUrl } from "./api";

type Json = any; // eslint-disable-line @typescript-eslint/no-explicit-any

export const DOCUMENT_URI = "file:///work/main.py";

const ANALYSIS_SETTINGS = {
  typeCheckingMode: "basic",
  diagnosticMode: "openFilesOnly",
  autoImportCompletions: false,
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
  /** Names the current lesson step is about; their completions rank first. */
  focusNames = new Set<string>();

  constructor(
    sessionId: string,
    private monaco: typeof Monaco,
    private model: Monaco.editor.ITextModel,
  ) {
    this.socket = new WebSocket(wsUrl(`/sessions/${sessionId}/lsp`));
    this.socket.onmessage = (event) => this.receive(JSON.parse(event.data));
    this.ready = new Promise((resolve, reject) => {
      this.socket.onopen = () => this.initialize().then(resolve, reject);
      this.socket.onerror = () => reject(new Error("language server connection failed"));
    });
    this.registerProviders();
    this.disposables.push(model.onDidChangeContent(() => this.didChange()));
  }

  dispose() {
    this.disposables.forEach((d) => d.dispose());
    this.monaco.editor.setModelMarkers(this.model, "pyright", []);
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
        uri: DOCUMENT_URI,
        languageId: "python",
        version: this.version,
        text: this.model.getValue(),
      },
    });
    this.opened = true;
  }

  private didChange() {
    if (!this.opened) return;
    this.notify("textDocument/didChange", {
      textDocument: { uri: DOCUMENT_URI, version: ++this.version },
      contentChanges: [{ text: this.model.getValue() }],
    });
  }

  private position(position: Monaco.Position) {
    return { line: position.lineNumber - 1, character: position.column - 1 };
  }

  // --- features ----------------------------------------------------------------

  private registerProviders() {
    const { languages } = this.monaco;
    const owns = (model: Monaco.editor.ITextModel) => model === this.model;

    this.disposables.push(
      languages.registerCompletionItemProvider("python", {
        triggerCharacters: ["."],
        provideCompletionItems: async (model, position) => {
          if (!owns(model)) return { suggestions: [] };
          await this.ready;
          const result = await this.request("textDocument/completion", {
            textDocument: { uri: DOCUMENT_URI },
            position: this.position(position),
          });
          const items: Json[] = Array.isArray(result) ? result : (result?.items ?? []);
          const word = model.getWordUntilPosition(position);
          const range = new this.monaco.Range(
            position.lineNumber,
            word.startColumn,
            position.lineNumber,
            word.endColumn,
          );
          return { suggestions: items.map((item) => this.toSuggestion(item, range)) };
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
          if (!owns(model)) return null;
          await this.ready;
          const result = await this.request("textDocument/hover", {
            textDocument: { uri: DOCUMENT_URI },
            position: this.position(position),
          });
          if (!result?.contents) return null;
          const contents = Array.isArray(result.contents) ? result.contents : [result.contents];
          return { contents: contents.map(toMarkdown) };
        },
      }),
      languages.registerSignatureHelpProvider("python", {
        signatureHelpTriggerCharacters: ["(", ","],
        provideSignatureHelp: async (model, position) => {
          if (!owns(model)) return null;
          await this.ready;
          const result = await this.request("textDocument/signatureHelp", {
            textDocument: { uri: DOCUMENT_URI },
            position: this.position(position),
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
    return {
      label: item.label,
      kind: languages.CompletionItemKind[kindName],
      detail: item.detail,
      documentation: item.documentation ? toMarkdown(item.documentation) : undefined,
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
    if (params.uri !== DOCUMENT_URI) return;
    const severity = this.monaco.MarkerSeverity;
    const toSeverity = (s: number) =>
      s === 1 ? severity.Error : s === 2 ? severity.Warning : s === 3 ? severity.Info : severity.Hint;
    this.monaco.editor.setModelMarkers(
      this.model,
      "pyright",
      (params.diagnostics as Json[]).map((d) => ({
        severity: toSeverity(d.severity ?? 1),
        message: friendlyDiagnostic(d.message),
        startLineNumber: d.range.start.line + 1,
        startColumn: d.range.start.character + 1,
        endLineNumber: d.range.end.line + 1,
        endColumn: d.range.end.character + 1,
      })),
    );
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
