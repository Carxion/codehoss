import { useEffect, useState } from "react";
import { api, progressApi, type ModuleSummary, type SkillMap } from "../api";

export default function Catalog() {
  const [modules, setModules] = useState<ModuleSummary[] | null>(null);
  const [error, setError] = useState("");
  const [skills, setSkills] = useState<SkillMap | null>(null);

  useEffect(() => {
    api.modules().then(setModules, (e) => setError(e.message));
    progressApi.skills().then(setSkills, () => {});
  }, []);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!modules) return <main className="page muted">Loading courses…</main>;

  return (
    <main className="page">
      <h1>Your courses</h1>
      {skills && (
        <div className="card today-strip">
          <span>
            🔥 <strong>{skills.streak.current}</strong> day{skills.streak.current === 1 ? "" : "s"} in a row
          </span>
          <span>
            🔁 <strong>{skills.reviews_due}</strong> review{skills.reviews_due === 1 ? "" : "s"} due
          </span>
          <span className="spacer" />
          {skills.reviews_due > 0 && (
            <a className="button primary small" href="#/review">
              Review now
            </a>
          )}
          <a className="button small" href="#/skills">
            Skill map
          </a>
        </div>
      )}
      {modules.map((module) => {
        const total = module.lessons.reduce((n, l) => n + l.steps, 0);
        const done = module.lessons.reduce((n, l) => n + l.done, 0);
        const resume = module.lessons.find((l) => l.done < l.steps) ?? module.lessons[0];
        return (
          <section key={module.id} className="card module-card">
            <div className="module-head">
              <div>
                <h2>{module.title}</h2>
                <p className="muted">{module.description}</p>
              </div>
              <a className="button primary" href={`#/learn/${module.id}/${resume.slug}/0`}>
                {done === 0 ? "Start" : "Continue"}
              </a>
            </div>
            <Progress done={done} total={total} />
            <ol className="lesson-list">
              {module.lessons.map((lesson, i) => (
                <li key={lesson.slug}>
                  <a href={`#/learn/${module.id}/${lesson.slug}/0`}>
                    <span className={`lesson-num ${lesson.done === lesson.steps ? "complete" : ""}`}>
                      {lesson.done === lesson.steps ? "✓" : i + 1}
                    </span>
                    <span className="lesson-title">
                      {lesson.title}
                      <small className="muted">{lesson.summary}</small>
                      {lesson.project && (
                        <span className="uses">
                          {lesson.project.uses.map((u) => (
                            <span key={u} className="pill">
                              uses {MODULE_NAMES[u] ?? u}
                            </span>
                          ))}
                        </span>
                      )}
                    </span>
                    <span className="muted small">
                      {lesson.done}/{lesson.steps}
                    </span>
                  </a>
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </main>
  );
}

const MODULE_NAMES: Record<string, string> = {
  "python-basics": "Python Basics",
  "data-science": "Data Science",
  ai: "AI",
};

function Progress({ done, total }: { done: number; total: number }) {
  const percent = total ? Math.round((done / total) * 100) : 0;
  return (
    <div className="progress" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-fill" style={{ width: `${percent}%` }} />
      <span className="progress-label">{percent}% complete</span>
    </div>
  );
}
