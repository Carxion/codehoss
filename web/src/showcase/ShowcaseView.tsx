import { useEffect, useMemo, useState } from "react";
import {
  ALGORITHMS,
  type ArrayFrame,
  type CellState,
  type Frame,
  type GraphFrame,
  type GridFrame,
  type StackFrame,
  type TreeFrame,
} from "./algorithms";

const SPEEDS = [
  { label: "Slow", ms: 1400 },
  { label: "Normal", ms: 800 },
  { label: "Fast", ms: 350 },
];

/** Plays an algorithm step by step: controls, scrubber, editable input. */
export default function ShowcaseView({ algorithm, input }: { algorithm: string; input: Record<string, unknown> }) {
  const spec = ALGORITHMS[algorithm];
  const [params, setParams] = useState<Record<string, unknown>>({ ...spec?.defaults, ...input });
  const [draft, setDraft] = useState(() => formatInput(params, spec?.editable));
  const [inputError, setInputError] = useState("");
  const frames = useMemo(() => (spec ? spec.run(params) : []), [spec, params]);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(SPEEDS[1].ms);

  useEffect(() => {
    setParams({ ...spec?.defaults, ...input });
  }, [algorithm, input, spec]);
  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [frames]);
  useEffect(() => {
    if (!playing) return;
    if (index >= frames.length - 1) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => setIndex((i) => i + 1), speed);
    return () => window.clearTimeout(timer);
  }, [playing, index, frames.length, speed]);

  if (!spec) return <p className="error-text">Unknown showcase: {algorithm}</p>;
  const frame = frames[Math.min(index, frames.length - 1)];
  const atEnd = index >= frames.length - 1;

  function applyInput() {
    const editable = spec.editable!;
    const parsed = parseInput(draft, editable.kind);
    if (parsed === null) {
      setInputError(editable.kind === "numbers" ? "Use numbers separated by commas, e.g. 5, 2, 9" : "That doesn't look right.");
      return;
    }
    setInputError("");
    setParams({ ...params, [editable.key]: parsed });
  }

  return (
    <section className="showcase" aria-label={`${spec.title} animation`}>
      <div className="showcase-head">
        <strong>{spec.title}</strong>
        <span className="muted small">
          Step {index + 1} of {frames.length}
        </span>
      </div>
      <div className="showcase-stage">{frame && <FrameView frame={frame} />}</div>
      <p className="showcase-message" aria-live="polite">
        {frame?.message}
      </p>
      <div className="showcase-controls">
        <button onClick={() => setIndex(0)} disabled={index === 0} aria-label="First step">
          ⏮
        </button>
        <button onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0} aria-label="Previous step">
          ◀
        </button>
        <button
          className="primary"
          onClick={() => {
            if (atEnd) setIndex(0);
            setPlaying(!playing);
          }}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "⏸ Pause" : atEnd ? "↻ Replay" : "▶ Play"}
        </button>
        <button onClick={() => setIndex((i) => Math.min(frames.length - 1, i + 1))} disabled={atEnd} aria-label="Next step">
          ▶
        </button>
        <button onClick={() => setIndex(frames.length - 1)} disabled={atEnd} aria-label="Last step">
          ⏭
        </button>
        <input
          type="range"
          className="scrubber"
          min={0}
          max={Math.max(0, frames.length - 1)}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            setIndex(Number(e.target.value));
          }}
          aria-label="Scrub through the steps"
        />
        <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label="Speed">
          {SPEEDS.map((s) => (
            <option key={s.ms} value={s.ms}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {spec.editable && (
        <form
          className="showcase-input"
          onSubmit={(e) => {
            e.preventDefault();
            applyInput();
          }}
        >
          <label>
            Try your own {spec.editable.label.toLowerCase()}
            <input value={draft} onChange={(e) => setDraft(e.target.value)} aria-label={spec.editable.label} />
          </label>
          <button>Run it</button>
          {inputError && <span className="error-text small">{inputError}</span>}
        </form>
      )}
    </section>
  );
}

function formatInput(params: Record<string, unknown>, editable?: { key: string; kind: string }) {
  if (!editable) return "";
  const value = params[editable.key];
  return Array.isArray(value) ? value.join(", ") : String(value ?? "");
}

function parseInput(text: string, kind: "numbers" | "text" | "number"): unknown {
  if (kind === "text") return text.trim() || null;
  if (kind === "number") {
    const n = Number(text);
    return Number.isFinite(n) ? n : null;
  }
  const parts = text.split(/[,\s]+/).filter(Boolean).map(Number);
  if (!parts.length || parts.some((n) => !Number.isFinite(n)) || parts.length > 16) return null;
  return parts;
}

// --- renderers -------------------------------------------------------------------------

function FrameView({ frame }: { frame: Frame }) {
  switch (frame.kind) {
    case "array":
      return <ArrayView frame={frame} />;
    case "stack":
      return <StackView frame={frame} />;
    case "tree":
      return <TreeView frame={frame} />;
    case "graph":
      return <GraphView frame={frame} />;
    case "grid":
      return <GridView frame={frame} />;
  }
}

const stateClass = (s: CellState | undefined) => (s ? `sc-${s}` : "");

function ArrayView({ frame }: { frame: ArrayFrame }) {
  const max = Math.max(1, ...frame.values.map(Math.abs));
  const width = 520;
  const slot = width / Math.max(1, frame.values.length);
  const barHeight = 130;
  const pointerAt = new Map<number, string[]>();
  for (const [name, i] of Object.entries(frame.pointers ?? {})) pointerAt.set(i, [...(pointerAt.get(i) ?? []), name]);
  return (
    <svg viewBox={`0 0 ${width} 200`} className="sc-svg" role="img" aria-label={`Values: ${frame.values.join(", ")}`}>
      {frame.values.map((v, i) => {
        const h = Math.max(6, (Math.abs(v) / max) * barHeight);
        return (
          <g key={i} className={`sc-bar ${stateClass(frame.states?.[i])}`}>
            <rect x={i * slot + 4} y={150 - h} width={slot - 8} height={h} rx={4} />
            <text x={i * slot + slot / 2} y={145 - h} textAnchor="middle" className="sc-value">
              {v}
            </text>
            <text x={i * slot + slot / 2} y={166} textAnchor="middle" className="sc-index">
              {i}
            </text>
            {pointerAt.has(i) && (
              <text x={i * slot + slot / 2} y={188} textAnchor="middle" className="sc-pointer">
                ▲ {pointerAt.get(i)!.join(", ")}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function StackView({ frame }: { frame: StackFrame }) {
  return (
    <div className={`sc-stack-view ${frame.status ? `sc-status-${frame.status}` : ""}`}>
      <div className="sc-input-row" aria-label="Input">
        {[...frame.input].map((ch, i) => (
          <span key={i} className={i === frame.position ? "sc-char current" : i < frame.position ? "sc-char read" : "sc-char"}>
            {ch}
          </span>
        ))}
      </div>
      <div className="sc-stack" aria-label={`Stack: ${frame.stack.join(" ") || "empty"}`}>
        {frame.stack.length === 0 && <span className="muted small">(empty stack)</span>}
        {[...frame.stack].reverse().map((ch, i) => (
          <span key={frame.stack.length - i} className={i === 0 ? "sc-plate top" : "sc-plate"}>
            {ch}
          </span>
        ))}
      </div>
    </div>
  );
}

function TreeView({ frame }: { frame: TreeFrame }) {
  const byId = new Map(frame.nodes.map((n) => [n.id, n]));
  const position = new Map<string, { x: number; depth: number }>();
  let order = 0;
  let maxDepth = 0;
  // In-order layout keeps left children left and right children right.
  function place(id: string | null, depth: number) {
    if (!id || !byId.has(id)) return;
    const node = byId.get(id)!;
    const [left, ...rest] = node.children;
    place(left ?? null, depth + 1);
    position.set(id, { x: order++, depth });
    maxDepth = Math.max(maxDepth, depth);
    for (const child of rest) place(child, depth + 1);
  }
  place(frame.root, 0);
  const width = 520;
  const slot = width / Math.max(1, order);
  const levelHeight = Math.min(56, 170 / Math.max(1, maxDepth));
  const at = (id: string) => {
    const p = position.get(id)!;
    return { x: p.x * slot + slot / 2, y: 22 + p.depth * levelHeight };
  };
  const radius = Math.min(18, slot / 2.4);
  // Label boxes (e.g. "fib(4)=3") stay a readable size however few nodes there are.
  const boxWidth = Math.min(slot - 4, 96);
  return (
    <div>
      <svg viewBox={`0 0 ${width} ${Math.max(80, 50 + maxDepth * levelHeight)}`} className="sc-svg" role="img" aria-label="Tree">
        {frame.nodes.flatMap((n) =>
          n.children
            .filter((c): c is string => !!c && position.has(c))
            .map((c) => <line key={`${n.id}-${c}`} {...pointsOf(at(n.id), at(c))} className="sc-edge" />),
        )}
        {frame.nodes
          .filter((n) => position.has(n.id))
          .map((n) => {
            const { x, y } = at(n.id);
            const long = n.label.length > 3;
            return (
              <g key={n.id} className={`sc-node ${stateClass(frame.states?.[n.id])}`}>
                {long ? (
                  <rect x={x - boxWidth / 2} y={y - 12} width={boxWidth} height={24} rx={8} />
                ) : (
                  <circle cx={x} cy={y} r={radius} />
                )}
                <text x={x} y={y + 4} textAnchor="middle" className={long ? "sc-label small" : "sc-label"}>
                  {n.label}
                </text>
              </g>
            );
          })}
      </svg>
      {frame.array && (
        <div className="sc-heap-array" aria-label="Heap as an array">
          <span className="muted small">As an array:</span>
          {frame.array.map((v, i) => (
            <span key={i} className={`sc-cell ${stateClass(frame.states?.[`h${i}`])}`}>
              {v}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function pointsOf(a: { x: number; y: number }, b: { x: number; y: number }) {
  return { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
}

function GraphView({ frame }: { frame: GraphFrame }) {
  const at = new Map(frame.nodes.map((n) => [n.id, n]));
  const isActive = (a: string, b: string) =>
    !!frame.activeEdge && ((frame.activeEdge[0] === a && frame.activeEdge[1] === b) || (frame.activeEdge[0] === b && frame.activeEdge[1] === a));
  return (
    <div>
      <svg viewBox="0 0 530 215" className="sc-svg" role="img" aria-label="Graph">
        {frame.edges.map((e) => {
          const a = at.get(e.a)!;
          const b = at.get(e.b)!;
          return (
            <g key={`${e.a}${e.b}`} className={isActive(e.a, e.b) ? "sc-graph-edge active" : "sc-graph-edge"}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
              {e.w !== undefined && (
                <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 5} textAnchor="middle" className="sc-weight">
                  {e.w}
                </text>
              )}
            </g>
          );
        })}
        {frame.nodes.map((n) => (
          <g key={n.id} className={`sc-gnode ${frame.states[n.id] ? `sc-g-${frame.states[n.id]}` : ""}`}>
            <circle cx={n.x} cy={n.y} r={19} />
            <text x={n.x} y={n.y + 5} textAnchor="middle" className="sc-label">
              {n.id}
            </text>
            {frame.labels?.[n.id] && (
              <text x={n.x} y={n.y + 36} textAnchor="middle" className="sc-node-note">
                {frame.labels[n.id]}
              </text>
            )}
          </g>
        ))}
      </svg>
      {frame.list && (
        <div className="sc-heap-array">
          <span className="muted small">{frame.list.title}:</span>
          {frame.list.items.length ? frame.list.items.map((id, i) => <span key={i} className="sc-cell">{id}</span>) : <span className="muted small">empty</span>}
        </div>
      )}
      <p className="sc-legend small muted">
        <span className="sc-dot current" /> current <span className="sc-dot frontier" /> waiting <span className="sc-dot visited" /> done
      </p>
    </div>
  );
}

function GridView({ frame }: { frame: GridFrame }) {
  const isUsed = (r: number, c: number) => frame.uses?.some(([ur, uc]) => ur === r && uc === c);
  return (
    <div className="sc-grid-wrap">
      <table className="sc-grid">
        <thead>
          <tr>
            <th scope="col">amount →</th>
            {frame.colLabels.map((label, i) => (
              <th key={i} scope="col">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {frame.cells.map((row, r) => (
            <tr key={r}>
              <th scope="row">{frame.rowLabels[r]}</th>
              {row.map((cell, c) => (
                <td
                  key={c}
                  className={
                    frame.active && frame.active[0] === r && frame.active[1] === c ? "sc-active" : isUsed(r, c) ? "sc-used" : ""
                  }
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
