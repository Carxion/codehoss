// Algorithm "recorders": each runs an algorithm on an input and returns the frames to
// animate. A frame is a snapshot of what to draw plus a sentence explaining the step.
// Names must match SHOWCASES in src/dojo/models.py.

export type CellState = "compare" | "swap" | "done" | "found" | "active" | "dim";

export interface ArrayFrame {
  kind: "array";
  values: number[];
  states?: Record<number, CellState>;
  pointers?: Record<string, number>;
  message: string;
}

export interface StackFrame {
  kind: "stack";
  input: string;
  position: number;
  stack: string[];
  status?: "ok" | "bad";
  message: string;
}

export interface TreeNode {
  id: string;
  label: string;
  children: (string | null)[]; // null keeps left/right positions in binary trees
}

export interface TreeFrame {
  kind: "tree";
  nodes: TreeNode[];
  root: string | null;
  states?: Record<string, CellState>;
  array?: number[]; // heaps also show their array
  message: string;
}

export interface GraphFrame {
  kind: "graph";
  nodes: { id: string; x: number; y: number }[];
  edges: { a: string; b: string; w?: number }[];
  states: Record<string, "current" | "frontier" | "visited">;
  labels?: Record<string, string>;
  activeEdge?: [string, string];
  list?: { title: string; items: string[] };
  message: string;
}

export interface GridFrame {
  kind: "grid";
  rowLabels: string[];
  colLabels: string[];
  cells: (number | string | null)[][];
  active?: [number, number];
  uses?: [number, number][];
  message: string;
}

export type Frame = ArrayFrame | StackFrame | TreeFrame | GraphFrame | GridFrame;

export interface Algorithm {
  title: string;
  /** Which input the learner may edit, if any. */
  editable?: { key: string; label: string; kind: "numbers" | "text" | "number" };
  defaults: Record<string, unknown>;
  run: (input: Record<string, unknown>) => Frame[];
}

// --- helpers -------------------------------------------------------------------------

const nums = (v: unknown, fallback: number[]): number[] =>
  Array.isArray(v) && v.every((x) => typeof x === "number") ? (v as number[]) : fallback;

function arrayFrame(values: number[], message: string, extra: Partial<ArrayFrame> = {}): ArrayFrame {
  return { kind: "array", values: [...values], message, ...extra };
}

const doneUpTo = (n: number, from = 0): Record<number, CellState> =>
  Object.fromEntries(Array.from({ length: Math.max(0, n - from) }, (_, i) => [i + from, "done" as CellState]));

// --- searching -----------------------------------------------------------------------

const linearSearch: Algorithm = {
  title: "Linear search",
  editable: { key: "values", label: "Numbers", kind: "numbers" },
  defaults: { values: [7, 3, 9, 4, 1, 8, 6], target: 8 },
  run(input) {
    const values = nums(input.values, [7, 3, 9, 4, 1, 8, 6]);
    const target = typeof input.target === "number" ? input.target : values[values.length - 1];
    const frames: Frame[] = [arrayFrame(values, `Look for ${target} by checking each item in turn.`)];
    for (let i = 0; i < values.length; i++) {
      if (values[i] === target) {
        frames.push(arrayFrame(values, `${values[i]} = ${target}: found it after ${i + 1} checks.`, { states: { [i]: "found" }, pointers: { i } }));
        return frames;
      }
      frames.push(arrayFrame(values, `${values[i]} isn't ${target}. Move on. (${i + 1} checked)`, { states: { [i]: "compare" }, pointers: { i } }));
    }
    frames.push(arrayFrame(values, `${target} isn't in the list: we had to check all ${values.length} items. That's O(n).`));
    return frames;
  },
};

const binarySearch: Algorithm = {
  title: "Binary search",
  editable: { key: "values", label: "Sorted numbers", kind: "numbers" },
  defaults: { values: [2, 5, 8, 12, 16, 23, 38, 56, 72, 91], target: 23 },
  run(input) {
    const values = [...nums(input.values, [2, 5, 8, 12, 16, 23, 38, 56, 72, 91])].sort((a, b) => a - b);
    const target = typeof input.target === "number" ? input.target : values[Math.floor(values.length / 2)];
    const dim = (lo: number, hi: number) =>
      Object.fromEntries(values.map((_, i) => [i, i < lo || i > hi ? ("dim" as CellState) : undefined]).filter(([, s]) => s));
    const frames: Frame[] = [arrayFrame(values, `The list is sorted, so we can halve it each step. Looking for ${target}.`)];
    let lo = 0;
    let hi = values.length - 1;
    let steps = 0;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      steps++;
      frames.push(arrayFrame(values, `Check the middle: position ${mid} holds ${values[mid]}.`, { states: { ...dim(lo, hi), [mid]: "compare" }, pointers: { lo, mid, hi } }));
      if (values[mid] === target) {
        frames.push(arrayFrame(values, `Found ${target} in ${steps} steps. A linear search could take ${values.length}. That's O(log n).`, { states: { ...dim(mid, mid), [mid]: "found" }, pointers: { mid } }));
        return frames;
      }
      if (values[mid] < target) {
        lo = mid + 1;
        frames.push(arrayFrame(values, `${values[mid]} < ${target}, so it can only be to the right. Drop the left half.`, { states: dim(lo, hi), pointers: { lo, hi } }));
      } else {
        hi = mid - 1;
        frames.push(arrayFrame(values, `${values[mid]} > ${target}, so it can only be to the left. Drop the right half.`, { states: dim(lo, hi), pointers: { lo, hi } }));
      }
    }
    frames.push(arrayFrame(values, `Nothing left to search: ${target} isn't in the list (${steps} steps).`, { states: dim(1, 0) }));
    return frames;
  },
};

const twoPointers: Algorithm = {
  title: "Two pointers: pair with a target sum",
  editable: { key: "values", label: "Sorted numbers", kind: "numbers" },
  defaults: { values: [1, 3, 4, 6, 8, 11, 15], target: 14 },
  run(input) {
    const values = [...nums(input.values, [1, 3, 4, 6, 8, 11, 15])].sort((a, b) => a - b);
    const target = typeof input.target === "number" ? input.target : 14;
    const frames: Frame[] = [arrayFrame(values, `Find two numbers that add to ${target}. Start one pointer at each end.`)];
    let left = 0;
    let right = values.length - 1;
    while (left < right) {
      const sum = values[left] + values[right];
      const states = { [left]: "compare" as CellState, [right]: "compare" as CellState };
      if (sum === target) {
        frames.push(arrayFrame(values, `${values[left]} + ${values[right]} = ${target}. Found the pair in one pass: O(n).`, { states: { [left]: "found", [right]: "found" }, pointers: { left, right } }));
        return frames;
      }
      if (sum < target) {
        frames.push(arrayFrame(values, `${values[left]} + ${values[right]} = ${sum}, too small. Move left up to a bigger number.`, { states, pointers: { left, right } }));
        left++;
      } else {
        frames.push(arrayFrame(values, `${values[left]} + ${values[right]} = ${sum}, too big. Move right down to a smaller number.`, { states, pointers: { left, right } }));
        right--;
      }
    }
    frames.push(arrayFrame(values, `The pointers met: no pair adds up to ${target}.`));
    return frames;
  },
};

// --- stacks --------------------------------------------------------------------------

const bracketStack: Algorithm = {
  title: "Stack: balanced brackets",
  editable: { key: "text", label: "Brackets", kind: "text" },
  defaults: { text: "{[()()]}" },
  run(input) {
    const text = typeof input.text === "string" && input.text ? input.text.slice(0, 24) : "{[()()]}";
    const pairs: Record<string, string> = { ")": "(", "]": "[", "}": "{" };
    const stack: string[] = [];
    const frames: Frame[] = [{ kind: "stack", input: text, position: -1, stack: [], message: "Read left to right. Push every opening bracket; a closing bracket must match the top." }];
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if ("([{".includes(ch)) {
        stack.push(ch);
        frames.push({ kind: "stack", input: text, position: i, stack: [...stack], message: `"${ch}" opens: push it on the stack.` });
      } else if (ch in pairs) {
        if (stack[stack.length - 1] === pairs[ch]) {
          stack.pop();
          frames.push({ kind: "stack", input: text, position: i, stack: [...stack], message: `"${ch}" matches the top "${pairs[ch]}": pop it.` });
        } else {
          frames.push({ kind: "stack", input: text, position: i, stack: [...stack], status: "bad", message: `"${ch}" doesn't match ${stack.length ? `the top "${stack[stack.length - 1]}"` : "anything (the stack is empty)"}: not balanced.` });
          return frames;
        }
      }
    }
    frames.push(
      stack.length
        ? { kind: "stack", input: text, position: text.length, stack: [...stack], status: "bad", message: `The end, but ${stack.length} bracket(s) never closed: not balanced.` }
        : { kind: "stack", input: text, position: text.length, stack: [], status: "ok", message: "The end, and the stack is empty: balanced!" },
    );
    return frames;
  },
};

// --- recursion -----------------------------------------------------------------------

const fibTree: Algorithm = {
  title: "Recursion: fib(n) call tree",
  editable: { key: "n", label: "n (2 to 6)", kind: "number" },
  defaults: { n: 5 },
  run(input) {
    const n = Math.min(6, Math.max(2, typeof input.n === "number" ? Math.round(input.n) : 5));
    const nodes: TreeNode[] = [];
    const states: Record<string, CellState> = {};
    const frames: Frame[] = [];
    let counter = 0;
    const snapshot = (message: string) =>
      frames.push({ kind: "tree", nodes: nodes.map((x) => ({ ...x, children: [...x.children] })), root: nodes[0]?.id ?? null, states: { ...states }, message });

    function call(k: number, parent: TreeNode | null): number {
      const node: TreeNode = { id: `c${counter++}`, label: `fib(${k})`, children: [] };
      nodes.push(node);
      parent?.children.push(node.id);
      states[node.id] = "active";
      snapshot(`Call fib(${k}).`);
      let result: number;
      if (k < 2) {
        result = k;
        snapshot(`fib(${k}) is a base case: return ${k}.`);
      } else {
        states[node.id] = "compare";
        result = call(k - 1, node) + call(k - 2, node);
        states[node.id] = "active";
      }
      node.label = `fib(${k})=${result}`;
      states[node.id] = "done";
      if (k >= 2) snapshot(`fib(${k}) = fib(${k - 1}) + fib(${k - 2}) = ${result}.`);
      return result;
    }

    const result = call(n, null);
    snapshot(`fib(${n}) = ${result}, using ${counter} calls. Notice fib(${n - 2}) and smaller get computed again and again; memoisation fixes that.`);
    return frames;
  },
};

// --- sorting -------------------------------------------------------------------------

const bubbleSort: Algorithm = {
  title: "Bubble sort",
  editable: { key: "values", label: "Numbers", kind: "numbers" },
  defaults: { values: [5, 1, 4, 2, 8, 3] },
  run(input) {
    const a = [...nums(input.values, [5, 1, 4, 2, 8, 3])];
    const frames: Frame[] = [arrayFrame(a, "Compare neighbours and swap them if they're in the wrong order. Big values bubble to the end.")];
    const n = a.length;
    for (let pass = 0; pass < n - 1; pass++) {
      let swapped = false;
      for (let i = 0; i < n - 1 - pass; i++) {
        const sorted = doneUpTo(n, n - pass);
        frames.push(arrayFrame(a, `Compare ${a[i]} and ${a[i + 1]}.`, { states: { ...sorted, [i]: "compare", [i + 1]: "compare" } }));
        if (a[i] > a[i + 1]) {
          [a[i], a[i + 1]] = [a[i + 1], a[i]];
          swapped = true;
          frames.push(arrayFrame(a, `${a[i + 1]} > ${a[i]}: swap them.`, { states: { ...sorted, [i]: "swap", [i + 1]: "swap" } }));
        }
      }
      frames.push(arrayFrame(a, `Pass ${pass + 1} done: ${a[n - 1 - pass]} is in its final place.`, { states: doneUpTo(n, n - 1 - pass) }));
      if (!swapped) break;
    }
    frames.push(arrayFrame(a, "Sorted. Bubble sort makes about n² comparisons: fine for 6 items, slow for a million.", { states: doneUpTo(n) }));
    return frames;
  },
};

const insertionSort: Algorithm = {
  title: "Insertion sort",
  editable: { key: "values", label: "Numbers", kind: "numbers" },
  defaults: { values: [7, 2, 5, 1, 9, 3] },
  run(input) {
    const a = [...nums(input.values, [7, 2, 5, 1, 9, 3])];
    const frames: Frame[] = [arrayFrame(a, "Grow a sorted part on the left. Take the next item and slide it left into place.", { states: doneUpTo(1) })];
    for (let i = 1; i < a.length; i++) {
      const key = a[i];
      let j = i - 1;
      frames.push(arrayFrame(a, `Take ${key} and insert it into the sorted part.`, { states: { ...doneUpTo(i), [i]: "active" }, pointers: { key: i } }));
      while (j >= 0 && a[j] > key) {
        a[j + 1] = a[j];
        a[j] = key;
        frames.push(arrayFrame(a, `${a[j + 1]} > ${key}: shift ${a[j + 1]} right.`, { states: { ...doneUpTo(i + 1), [j]: "active", [j + 1]: "swap" } }));
        j--;
      }
      frames.push(arrayFrame(a, `${key} is in place; the first ${i + 1} items are sorted.`, { states: doneUpTo(i + 1) }));
    }
    frames.push(arrayFrame(a, "Sorted. Fast on nearly-sorted lists, but still about n² in the worst case.", { states: doneUpTo(a.length) }));
    return frames;
  },
};

const mergeSort: Algorithm = {
  title: "Merge sort",
  editable: { key: "values", label: "Numbers", kind: "numbers" },
  defaults: { values: [8, 3, 5, 1, 9, 2, 7, 4] },
  run(input) {
    const a = [...nums(input.values, [8, 3, 5, 1, 9, 2, 7, 4])];
    const frames: Frame[] = [arrayFrame(a, "Split the list in half again and again, then merge the sorted halves back together.")];
    const range = (lo: number, hi: number, state: CellState) =>
      Object.fromEntries(Array.from({ length: hi - lo }, (_, k) => [lo + k, state]));

    function sort(lo: number, hi: number) {
      if (hi - lo <= 1) return;
      const mid = Math.floor((lo + hi) / 2);
      frames.push(arrayFrame(a, `Split positions ${lo}-${hi - 1} into ${lo}-${mid - 1} and ${mid}-${hi - 1}.`, { states: { ...range(lo, mid, "compare"), ...range(mid, hi, "active") } }));
      sort(lo, mid);
      sort(mid, hi);
      const merged: number[] = [];
      let i = lo;
      let j = mid;
      while (i < mid || j < hi) {
        if (j >= hi || (i < mid && a[i] <= a[j])) merged.push(a[i++]);
        else merged.push(a[j++]);
      }
      a.splice(lo, merged.length, ...merged);
      frames.push(arrayFrame(a, `Merge them by repeatedly taking the smaller front item: ${merged.join(", ")}.`, { states: range(lo, hi, "swap") }));
    }

    sort(0, a.length);
    frames.push(arrayFrame(a, "Sorted. log n levels of splitting, n work per level: O(n log n).", { states: doneUpTo(a.length) }));
    return frames;
  },
};

// --- trees ---------------------------------------------------------------------------

const bstInsert: Algorithm = {
  title: "Binary search tree: inserting",
  editable: { key: "values", label: "Numbers to insert", kind: "numbers" },
  defaults: { values: [50, 30, 70, 20, 40, 60, 80, 35] },
  run(input) {
    const values = nums(input.values, [50, 30, 70, 20, 40, 60, 80, 35]).slice(0, 15);
    const nodes: TreeNode[] = [];
    const frames: Frame[] = [];
    const byId = new Map<string, TreeNode>();
    const snap = (message: string, states: Record<string, CellState> = {}) =>
      frames.push({ kind: "tree", nodes: nodes.map((x) => ({ ...x, children: [...x.children] })), root: nodes[0]?.id ?? null, states, message });
    values.forEach((v, idx) => {
      const node: TreeNode = { id: `n${idx}`, label: String(v), children: [null, null] };
      if (!nodes.length) {
        nodes.push(node);
        byId.set(node.id, node);
        snap(`${v} becomes the root.`, { [node.id]: "found" });
        return;
      }
      let current = nodes[0];
      for (;;) {
        const goLeft = v < Number(current.label);
        snap(`Insert ${v}: ${v} ${goLeft ? "<" : "≥"} ${current.label}, go ${goLeft ? "left" : "right"}.`, { [current.id]: "compare" });
        const slot = goLeft ? 0 : 1;
        const next = current.children[slot];
        if (next === null) {
          current.children[slot] = node.id;
          nodes.push(node);
          byId.set(node.id, node);
          snap(`Empty spot: place ${v} here.`, { [node.id]: "found" });
          break;
        }
        current = byId.get(next)!;
      }
    });
    snap("Every left child is smaller and every right child is bigger, so a search only follows one path: O(height).");
    return frames;
  },
};

const heap: Algorithm = {
  title: "Min-heap: push and pop",
  editable: { key: "values", label: "Numbers to push", kind: "numbers" },
  defaults: { values: [7, 3, 9, 1, 5, 2] },
  run(input) {
    const values = nums(input.values, [7, 3, 9, 1, 5, 2]).slice(0, 15);
    const h: number[] = [];
    const frames: Frame[] = [];
    const tree = (): TreeNode[] =>
      h.map((v, i) => ({
        id: `h${i}`,
        label: String(v),
        children: [2 * i + 1 < h.length ? `h${2 * i + 1}` : null, 2 * i + 2 < h.length ? `h${2 * i + 2}` : null],
      }));
    const snap = (message: string, states: Record<string, CellState> = {}) =>
      frames.push({ kind: "tree", nodes: tree(), root: h.length ? "h0" : null, states, array: [...h], message });
    snap("A min-heap keeps the smallest value at the top. Every parent is ≤ its children.");
    for (const v of values) {
      h.push(v);
      let i = h.length - 1;
      snap(`Push ${v}: add it at the bottom.`, { [`h${i}`]: "active" });
      while (i > 0) {
        const parent = Math.floor((i - 1) / 2);
        if (h[parent] <= h[i]) break;
        [h[parent], h[i]] = [h[i], h[parent]];
        snap(`${h[parent]} < ${h[i]}: swap with its parent (sift up).`, { [`h${parent}`]: "swap", [`h${i}`]: "swap" });
        i = parent;
      }
    }
    if (h.length) {
      const top = h[0];
      const last = h.pop()!;
      if (h.length) h[0] = last;
      snap(`Pop: remove the smallest (${top}) and move the last item to the top.`, { h0: "active" });
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = 2 * i + 2;
        let smallest = i;
        if (l < h.length && h[l] < h[smallest]) smallest = l;
        if (r < h.length && h[r] < h[smallest]) smallest = r;
        if (smallest === i) break;
        [h[i], h[smallest]] = [h[smallest], h[i]];
        snap(`Swap with the smaller child (sift down).`, { [`h${i}`]: "swap", [`h${smallest}`]: "swap" });
        i = smallest;
      }
      snap(`Back in heap order. Push and pop each take O(log n): just one path up or down.`);
    }
    return frames;
  },
};

// --- graphs --------------------------------------------------------------------------

const GRAPH = {
  nodes: [
    { id: "A", x: 60, y: 60 },
    { id: "B", x: 200, y: 30 },
    { id: "C", x: 200, y: 140 },
    { id: "D", x: 340, y: 60 },
    { id: "E", x: 340, y: 180 },
    { id: "F", x: 470, y: 110 },
  ],
  edges: [
    { a: "A", b: "B", w: 4 },
    { a: "A", b: "C", w: 2 },
    { a: "B", b: "C", w: 1 },
    { a: "B", b: "D", w: 5 },
    { a: "C", b: "D", w: 8 },
    { a: "C", b: "E", w: 10 },
    { a: "D", b: "E", w: 2 },
    { a: "D", b: "F", w: 6 },
    { a: "E", b: "F", w: 3 },
  ],
};

function neighbours(id: string) {
  return GRAPH.edges
    .filter((e) => e.a === id || e.b === id)
    .map((e) => ({ id: e.a === id ? e.b : e.a, w: e.w }))
    .sort((x, y) => x.id.localeCompare(y.id));
}

function traversal(kind: "bfs" | "dfs"): Algorithm {
  const isBfs = kind === "bfs";
  return {
    title: isBfs ? "Breadth-first search" : "Depth-first search",
    defaults: { start: "A" },
    run() {
      const frames: Frame[] = [];
      const states: GraphFrame["states"] = {};
      const order: string[] = [];
      const pending = ["A"];
      states.A = "frontier";
      const snap = (message: string, activeEdge?: [string, string]) =>
        frames.push({
          kind: "graph",
          ...GRAPH,
          states: { ...states },
          activeEdge,
          labels: Object.fromEntries(order.map((id, i) => [id, `#${i + 1}`])),
          list: { title: isBfs ? "Queue (first in, first out)" : "Stack (last in, first out)", items: [...pending] },
          message,
        });
      snap(isBfs ? "Start at A. A queue visits nodes in rings: all neighbours first, then theirs." : "Start at A. A stack goes as deep as it can before backing up.");
      while (pending.length) {
        const id = isBfs ? pending.shift()! : pending.pop()!;
        if (states[id] === "visited") continue;
        states[id] = "current";
        order.push(id);
        snap(`Visit ${id} (${isBfs ? "taken from the front of the queue" : "taken from the top of the stack"}).`);
        const next = neighbours(id).filter((n) => !states[n.id]);
        for (const n of isBfs ? next : [...next].reverse()) {
          states[n.id] = "frontier";
          pending.push(n.id);
          snap(`Found neighbour ${n.id}: add it to the ${isBfs ? "queue" : "stack"}.`, [id, n.id]);
        }
        states[id] = "visited";
      }
      snap(`Visit order: ${order.join(" → ")}. Every node and edge is handled once: O(V + E).`);
      return frames;
    },
  };
}

const dijkstra: Algorithm = {
  title: "Dijkstra's shortest paths",
  defaults: { start: "A" },
  run() {
    const frames: Frame[] = [];
    const dist: Record<string, number> = Object.fromEntries(GRAPH.nodes.map((n) => [n.id, Infinity]));
    const states: GraphFrame["states"] = {};
    dist.A = 0;
    const label = () => Object.fromEntries(Object.entries(dist).map(([id, d]) => [id, d === Infinity ? "∞" : String(d)]));
    const snap = (message: string, activeEdge?: [string, string]) =>
      frames.push({ kind: "graph", ...GRAPH, states: { ...states }, labels: label(), activeEdge, message });
    snap("Distances start at ∞, except A at 0. Repeatedly settle the closest unsettled node.");
    for (;;) {
      const candidates = GRAPH.nodes.map((n) => n.id).filter((id) => states[id] !== "visited" && dist[id] < Infinity);
      if (!candidates.length) break;
      const u = candidates.reduce((best, id) => (dist[id] < dist[best] ? id : best));
      states[u] = "current";
      snap(`Closest unsettled node: ${u} at distance ${dist[u]}. Its distance is now final.`);
      for (const { id: v, w } of neighbours(u)) {
        if (states[v] === "visited") continue;
        const through = dist[u] + (w ?? 1);
        if (through < dist[v]) {
          const before = dist[v];
          dist[v] = through;
          states[v] = "frontier";
          snap(`Via ${u}, ${v} costs ${dist[u]} + ${w} = ${through}, better than ${before === Infinity ? "∞" : before}. Update it.`, [u, v]);
        } else {
          snap(`Via ${u}, ${v} would cost ${through}: no better than ${dist[v]}.`, [u, v]);
        }
      }
      states[u] = "visited";
    }
    snap("Done: every label is the shortest distance from A. With a heap this runs in O((V + E) log V).");
    return frames;
  },
};

// --- dynamic programming ---------------------------------------------------------------

const coinChange: Algorithm = {
  title: "Dynamic programming: fewest coins",
  editable: { key: "coins", label: "Coin values", kind: "numbers" },
  defaults: { coins: [1, 3, 4], amount: 6 },
  run(input) {
    const coins = [...new Set(nums(input.coins, [1, 3, 4]).filter((c) => c > 0 && c <= 20))].sort((a, b) => a - b).slice(0, 5);
    const amount = typeof input.amount === "number" ? Math.min(12, Math.max(1, Math.round(input.amount))) : 6;
    const best: (number | null)[] = [0, ...Array(amount).fill(null)];
    const frames: Frame[] = [];
    const show = (x: number | null) => (x === null ? "·" : x === Infinity ? "∞" : x);
    const snap = (message: string, active?: number, uses: number[] = []) =>
      frames.push({
        kind: "grid",
        rowLabels: ["fewest coins"],
        colLabels: best.map((_, i) => String(i)),
        cells: [best.map(show)],
        active: active === undefined ? undefined : [0, active],
        uses: uses.map((u) => [0, u] as [number, number]),
        message,
      });
    snap(`Coins: ${coins.join(", ")}. Build up answers for amounts 0 to ${amount}, reusing smaller ones. Amount 0 needs 0 coins.`);
    for (let a = 1; a <= amount; a++) {
      let value = Infinity;
      const used: number[] = [];
      const tries: string[] = [];
      for (const c of coins) {
        if (c > a) continue;
        const rest = best[a - c] as number;
        tries.push(rest === Infinity ? `coin ${c} → ∞` : `coin ${c} → 1 + ${rest} = ${rest + 1}`);
        if (rest + 1 < value) {
          value = rest + 1;
          used.length = 0;
          used.push(a - c);
        }
      }
      best[a] = value;
      snap(
        value === Infinity
          ? `Amount ${a}: ${tries.join(", ")}. It can't be made with these coins.`
          : `Amount ${a}: ${tries.join(", ")}. Best: one coin of ${a - used[0]} plus the best for ${used[0]} = ${value} coins.`,
        a,
        used,
      );
    }
    snap(`The answer for ${amount} is ${show(best[amount])}. Each amount was solved once: O(amount × coins), not exponential.`, amount);
    return frames;
  },
};

export const ALGORITHMS: Record<string, Algorithm> = {
  "linear-search": linearSearch,
  "binary-search": binarySearch,
  "two-pointers": twoPointers,
  "bracket-stack": bracketStack,
  "fib-tree": fibTree,
  "bubble-sort": bubbleSort,
  "insertion-sort": insertionSort,
  "merge-sort": mergeSort,
  "bst-insert": bstInsert,
  heap,
  bfs: traversal("bfs"),
  dfs: traversal("dfs"),
  dijkstra,
  "coin-change": coinChange,
};
