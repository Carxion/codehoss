// Beginner snippet completions: common patterns with tab-stops to fill in.

import type * as Monaco from "monaco-editor";

const SNIPPETS: { label: string; detail: string; body: string }[] = [
  { label: "print", detail: "Show a message", body: 'print("${1:message}")' },
  { label: "input", detail: "Ask the user a question", body: '${1:answer} = input("${2:Question? }")' },
  { label: "input number", detail: "Ask for a whole number", body: '${1:number} = int(input("${2:Number? }"))' },
  { label: "if", detail: "Do something only when a condition is true", body: "if ${1:condition}:\n    ${2:pass}" },
  { label: "if / else", detail: "Choose between two options", body: "if ${1:condition}:\n    ${2:pass}\nelse:\n    ${3:pass}" },
  { label: "for loop over range", detail: "Repeat for each number", body: "for ${1:i} in range(${2:1}, ${3:11}):\n    ${4:print(i)}" },
  { label: "for loop over list", detail: "Repeat for each item", body: "for ${1:item} in ${2:items}:\n    ${3:print(item)}" },
  { label: "while loop", detail: "Repeat while a condition is true", body: "while ${1:condition}:\n    ${2:pass}" },
  { label: "def", detail: "Define a function", body: 'def ${1:name}(${2:params}):\n    """${3:What it does.}"""\n    ${4:return}' },
  { label: "f-string", detail: "Text with values inside", body: 'f"${1:text} {${2:value}}"' },
  { label: "try / except", detail: "Handle an error", body: "try:\n    ${1:pass}\nexcept ${2:ValueError}:\n    ${3:print(\"Something went wrong\")}" },
];

export function registerSnippets(monaco: typeof Monaco): Monaco.IDisposable {
  return monaco.languages.registerCompletionItemProvider("python", {
    provideCompletionItems(model, position) {
      const line = model.getLineContent(position.lineNumber).slice(0, position.column - 1);
      if (/\.\w*$/.test(line)) return { suggestions: [] }; // after a dot: members only
      const word = model.getWordUntilPosition(position);
      const range = new monaco.Range(
        position.lineNumber,
        word.startColumn,
        position.lineNumber,
        word.endColumn,
      );
      return {
        suggestions: SNIPPETS.map((s) => ({
          label: { label: s.label, description: "snippet" },
          kind: monaco.languages.CompletionItemKind.Snippet,
          detail: s.detail,
          documentation: { value: "```python\n" + s.body.replace(/\$\{\d+:([^}]*)\}/g, "$1") + "\n```" },
          insertText: s.body,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          sortText: `2_${s.label}`,
          range,
        })),
      };
    },
  });
}
