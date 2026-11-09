// Notebooks are stored as plain Python with "# %%" cell markers (the "percent" format
// VS Code and Jupytext use), so content files stay readable and graders can run them
// as ordinary scripts.

const MARKER = /^# %%.*$/m;

export interface Cell {
  id: string;
  code: string;
}

let counter = 0;
export const newCellId = () => `cell-${Date.now().toString(36)}-${(counter++).toString(36)}`;

export function splitCells(source: string): Cell[] {
  const parts = source.split(MARKER).map((part) => part.replace(/^\n+|\s+$/g, ""));
  // Text before the first marker is a cell too, unless it's empty.
  const cells = (parts[0] === "" ? parts.slice(1) : parts).map((code) => ({ id: newCellId(), code }));
  return cells.length ? cells : [{ id: newCellId(), code: "" }];
}

export function joinCells(cells: { code: string }[]): string {
  return cells.map((cell) => `# %%\n${cell.code.trimEnd()}\n`).join("\n");
}
