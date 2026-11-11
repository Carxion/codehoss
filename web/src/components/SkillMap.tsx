import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { progressApi, type ModuleSkill, type SkillMap as SkillMapData, type SkillState, type Streak } from "../api";

// Every course as a node, in columns by prerequisite depth, with lines from each course
// to the ones that build on it. Each lesson is a chip coloured by how well it's known;
// "fading" means a review is due. Above: streak, reviews due and a 12-week calendar.

export const STATE_LABEL: Record<SkillState, string> = {
  new: "Not started",
  learning: "Learning",
  practising: "Practising",
  strong: "Strong",
  fading: "Needs review",
};

export default function SkillMap() {
  const [data, setData] = useState<SkillMapData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    progressApi.skills().then(setData, (e) => setError(e.message));
  }, []);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!data) return <main className="page muted">Loading your skill map…</main>;

  const columns: ModuleSkill[][] = [];
  for (const m of data.modules) (columns[m.depth] ??= []).push(m);

  return (
    <main className="page page-wide">
      <h1>Your skill map</h1>
      <div className="skill-summary">
        <StreakCard streak={data.streak} />
        <div className="card summary-card">
          <div className="summary-big">🔁 {data.reviews_due}</div>
          <div>
            <strong>{data.reviews_due === 1 ? "review due" : "reviews due"}</strong>
            <p className="muted small">
              Quick questions from lessons you've finished, spaced out so they stick.
            </p>
            {data.reviews_due > 0 && (
              <a className="button primary small" href="#/review">
                Start reviewing
              </a>
            )}
          </div>
        </div>
        <Calendar streak={data.streak} />
      </div>

      <div className="skill-legend small" aria-label="Legend">
        {(Object.keys(STATE_LABEL) as SkillState[]).map((s) => (
          <span key={s}>
            <span className={`skill-chip ${s}`} aria-hidden /> {STATE_LABEL[s]}
          </span>
        ))}
      </div>

      <Graph modules={data.modules} columns={columns} />
    </main>
  );
}

function Graph({ modules, columns }: { modules: ModuleSkill[]; columns: ModuleSkill[][] }) {
  const box = useRef<HTMLDivElement | null>(null);
  const nodes = useRef<Record<string, HTMLElement | null>>({});
  const [lines, setLines] = useState<{ key: string; d: string; strong: boolean }[]>([]);

  useLayoutEffect(() => {
    const draw = () => {
      const root = box.current?.getBoundingClientRect();
      if (!root) return;
      const next = [];
      for (const m of modules) {
        const to = nodes.current[m.id]?.getBoundingClientRect();
        for (const p of m.prerequisites) {
          const from = nodes.current[p]?.getBoundingClientRect();
          if (!from || !to) continue;
          const x1 = from.right - root.left, y1 = from.top + from.height / 2 - root.top;
          const x2 = to.left - root.left, y2 = to.top + Math.min(40, to.height / 2) - root.top;
          const bend = Math.max(24, (x2 - x1) / 2);
          const prereq = modules.find((x) => x.id === p);
          next.push({
            key: `${p}-${m.id}`,
            d: `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`,
            strong: (prereq?.mastery ?? 0) >= 0.85,
          });
        }
      }
      setLines(next);
    };
    draw();
    const observer = new ResizeObserver(draw);
    if (box.current) observer.observe(box.current);
    return () => observer.disconnect();
  }, [modules]);

  return (
    <div className="skill-graph" ref={box}>
      <svg className="skill-lines" aria-hidden>
        {lines.map((l) => (
          <path key={l.key} d={l.d} className={l.strong ? "strong" : ""} />
        ))}
      </svg>
      {columns.map((column, depth) => (
        <div key={depth} className="skill-column">
          {column.map((m) => (
            <section key={m.id} className="card skill-node" ref={(el) => { nodes.current[m.id] = el; }}>
              <div className="skill-node-head">
                <a href={`#/learn/${m.id}/${m.lessons[0].slug}/0`}>
                  <strong>{m.title}</strong>
                </a>
                {m.due > 0 && <span className="pill due-pill">{m.due} due</span>}
              </div>
              <div className="mastery-bar" title={`${Math.round(m.mastery * 100)}% mastered`}>
                <div style={{ width: `${Math.round(m.mastery * 100)}%` }} />
              </div>
              <div className="skill-chips">
                {m.lessons.map((lesson, i) => (
                  <a
                    key={lesson.slug}
                    className={`skill-chip ${lesson.state}`}
                    href={`#/learn/${m.id}/${lesson.slug}/0`}
                    title={`${i + 1}. ${lesson.title}: ${STATE_LABEL[lesson.state]}${lesson.state === "new" ? "" : ` (${Math.round(lesson.mastery * 100)}%)`}`}
                    aria-label={`${lesson.title}: ${STATE_LABEL[lesson.state]}`}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      ))}
    </div>
  );
}

function StreakCard({ streak }: { streak: Streak }) {
  return (
    <div className="card summary-card">
      <div className="summary-big">🔥 {streak.current}</div>
      <div>
        <strong>day{streak.current === 1 ? "" : "s"} in a row</strong>
        <p className="muted small">
          {streak.current === 0
            ? "Do any step today to start a streak."
            : streak.today
              ? "You've studied today. See you tomorrow!"
              : "Do one step today to keep it going."}
          {streak.best > 0 && ` Best: ${streak.best}.`}
        </p>
      </div>
    </div>
  );
}

function Calendar({ streak }: { streak: Streak }) {
  // Columns are weeks (oldest left); the first column is padded so rows line up by weekday.
  const first = new Date(streak.calendar[0].date + "T00:00:00");
  const cells: ({ date: string; count: number } | null)[] = [
    ...Array<null>(first.getDay()).fill(null),
    ...streak.calendar,
  ];
  const max = Math.max(1, ...streak.calendar.map((d) => d.count));
  return (
    <div className="card calendar-card">
      <strong className="small">Last 12 weeks</strong>
      <div className="calendar" role="img" aria-label={`${streak.calendar.filter((d) => d.count).length} active days in the last 12 weeks`}>
        {cells.map((cell, i) =>
          cell ? (
            <span
              key={i}
              className="calendar-day"
              title={`${cell.date}: ${cell.count} step${cell.count === 1 ? "" : "s"}`}
              style={{ opacity: cell.count ? 0.35 + 0.65 * (cell.count / max) : undefined }}
              data-active={cell.count > 0 || undefined}
            />
          ) : (
            <span key={i} />
          ),
        )}
      </div>
    </div>
  );
}
