// Dojo pseudocode in Monaco: colours, auto-indent, and beginner completions with notes.
// The language itself lives in src/dojo/_dojo_pseudo.py; keep these lists in step with it.

import type * as Monaco from "monaco-editor";

export const PSEUDO = "pseudo";

const KEYWORDS = [
  "IF", "THEN", "ELSE", "END", "WHILE", "DO", "FOR", "FROM", "TO", "STEP", "EACH", "IN",
  "REPEAT", "UNTIL", "FUNCTION", "RETURN", "OUTPUT", "AND", "OR", "NOT", "MOD", "DIV",
];
const CONSTANTS = ["TRUE", "FALSE", "NOTHING"];

const BUILTINS: Record<string, { signature: string; doc: string }> = {
  INPUT: { signature: 'INPUT("question")', doc: "Asks a question and gives back what was typed, **as text**." },
  LENGTH: { signature: "LENGTH(list)", doc: "How many items in a list (or letters in text, or entries in a map)." },
  APPEND: { signature: "APPEND(list, item)", doc: "Adds `item` to the end of `list`." },
  REMOVE: { signature: "REMOVE(list, position)", doc: "Takes out the item at `position` and gives it back." },
  TO_NUMBER: { signature: 'TO_NUMBER("42")', doc: "Turns text that holds a number into a number you can do maths with." },
  TO_TEXT: { signature: "TO_TEXT(42)", doc: "Turns any value into text, so it can be joined onto other text with `+`." },
  ROUND: { signature: "ROUND(number, places)", doc: "Rounds to a number of decimal places (0 if left out). `ROUND(3.14159, 2)` is `3.14`." },
  RANDOM: { signature: "RANDOM(low, high)", doc: "A random whole number from `low` to `high`, both included." },
  UPPER: { signature: "UPPER(text)", doc: "The text in CAPITALS." },
  LOWER: { signature: "LOWER(text)", doc: "The text in small letters." },
  CONTAINS: { signature: "CONTAINS(list, value)", doc: "`TRUE` if the value is in the list (or the text is inside the text, or the key is in the map)." },
  KEYS: { signature: "KEYS(map)", doc: "A list of the map's keys." },
};

const SNIPPETS: { label: string; detail: string; body: string }[] = [
  { label: "OUTPUT", detail: "Show something", body: 'OUTPUT "${1:Hello}"' },
  { label: "INPUT", detail: "Ask a question", body: '${1:answer} = INPUT("${2:Question? }")' },
  { label: "INPUT number", detail: "Ask for a number", body: '${1:number} = TO_NUMBER(INPUT("${2:Number? }"))' },
  { label: "IF", detail: "Do something only when a condition is TRUE", body: "IF ${1:condition} THEN\n    ${2}\nEND IF" },
  { label: "IF ELSE", detail: "Choose between two options", body: "IF ${1:condition} THEN\n    ${2}\nELSE\n    ${3}\nEND IF" },
  { label: "WHILE", detail: "Repeat while a condition is TRUE", body: "WHILE ${1:condition} DO\n    ${2}\nEND WHILE" },
  { label: "REPEAT", detail: "Repeat until a condition becomes TRUE", body: "REPEAT\n    ${1}\nUNTIL ${2:condition}" },
  { label: "FOR", detail: "Count from one number to another", body: "FOR ${1:i} FROM ${2:1} TO ${3:10} DO\n    ${4:OUTPUT i}\nEND FOR" },
  { label: "FOR EACH", detail: "Go through every item in a list", body: "FOR EACH ${1:item} IN ${2:items} DO\n    ${3:OUTPUT item}\nEND FOR" },
  { label: "FUNCTION", detail: "Define a function", body: "FUNCTION ${1:name}(${2:value})\n    ${3:RETURN value}\nEND FUNCTION" },
];

let registered = false;

/** Registers the language once per page (Monaco is shared by every editor). */
export function registerPseudo(monaco: typeof Monaco): void {
  if (registered) return;
  registered = true;
  monaco.languages.register({ id: PSEUDO });
  monaco.languages.setMonarchTokensProvider(PSEUDO, {
    keywords: KEYWORDS,
    constants: CONSTANTS,
    builtins: Object.keys(BUILTINS),
    tokenizer: {
      root: [
        [/(#|\/\/).*$/, "comment"],
        [/"[^"]*"?/, "string"],
        [/'[^']*'?/, "string"],
        [/\d+(\.\d+)?/, "number"],
        [
          /[A-Za-z_]\w*/,
          {
            cases: {
              "@keywords": "keyword",
              "@constants": "constant",
              "@builtins": "type.identifier",
              "@default": "identifier",
            },
          },
        ],
        [/==|!=|<=|>=|[-+*/<>=]/, "operator"],
      ],
    },
  } as Monaco.languages.IMonarchLanguage);
  monaco.languages.setLanguageConfiguration(PSEUDO, {
    comments: { lineComment: "//" },
    brackets: [["(", ")"], ["[", "]"], ["{", "}"]],
    autoClosingPairs: [
      { open: "(", close: ")" },
      { open: "[", close: "]" },
      { open: "{", close: "}" },
      { open: '"', close: '"' },
    ],
    indentationRules: {
      increaseIndentPattern: /^\s*(IF\b.*\bTHEN|ELSE\b.*|WHILE\b.*\bDO|FOR\b.*\bDO|REPEAT|FUNCTION\b.*)\s*$/,
      decreaseIndentPattern: /^\s*(END\b|ELSE\b|UNTIL\b)/,
    },
  });
  monaco.languages.registerCompletionItemProvider(PSEUDO, {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn);
      const { Snippet, Function, Keyword, Constant, Variable } = monaco.languages.CompletionItemKind;
      const snippet = monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;
      const variables = new Set(
        [...model.getValue().matchAll(/^\s*([a-z_]\w*)\s*=(?!=)/gim)].map((m) => m[1]),
      );
      return {
        suggestions: [
          ...SNIPPETS.map((s) => ({
            label: { label: s.label, description: "snippet" },
            kind: Snippet,
            detail: s.detail,
            documentation: { value: "```\n" + s.body.replace(/\$\{\d+:?([^}]*)\}/g, "$1") + "\n```" },
            insertText: s.body,
            insertTextRules: snippet,
            sortText: `1_${s.label}`,
            range,
          })),
          ...Object.entries(BUILTINS).map(([name, b]) => ({
            label: name,
            kind: Function,
            detail: b.signature,
            documentation: { value: b.doc },
            insertText: `${name}(\${1})`,
            insertTextRules: snippet,
            sortText: `2_${name}`,
            range,
          })),
          ...KEYWORDS.map((k) => ({ label: k, kind: Keyword, insertText: k, sortText: `3_${k}`, range })),
          ...CONSTANTS.map((c) => ({ label: c, kind: Constant, insertText: c, sortText: `3_${c}`, range })),
          ...[...variables].map((v) => ({ label: v, kind: Variable, insertText: v, sortText: `0_${v}`, range })),
        ],
      };
    },
  });
  monaco.languages.registerHoverProvider(PSEUDO, {
    provideHover(model, position) {
      const word = model.getWordAtPosition(position);
      const builtin = word && BUILTINS[word.word];
      if (!builtin) return null;
      return { contents: [{ value: "```\n" + builtin.signature + "\n```" }, { value: builtin.doc }] };
    },
  });
}
