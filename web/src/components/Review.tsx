import { useEffect, useState } from "react";
import { progressApi, reviewPath, type DueReview } from "../api";

const KIND_LABEL = { quiz: "Quiz", "try-it": "Try it", exercise: "Exercise" } as const;

/** Reviews due now: steps from finished lessons, answered again from memory. */
export default function Review() {
  const [due, setDue] = useState<DueReview[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    progressApi.reviews().then(setDue, (e) => setError(e.message));
  }, []);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!due) return <main className="page muted">Loading your reviews…</main>;

  return (
    <main className="page">
      <h1>Review</h1>
      <p className="muted">
        Each step you've passed comes back after a day, then less and less often each time you answer it from memory.
        Get one wrong, or use a hint, and it comes back sooner. A few minutes a day is enough.
      </p>
      {due.length === 0 ? (
        <div className="card empty-portfolio">
          <p>Nothing to review right now. 🎉</p>
          <p className="muted small">
            Finish quizzes, try-its and exercises in any course and they'll come back here to keep them fresh. See how
            it's going on your <a href="#/skills">skill map</a>.
          </p>
        </div>
      ) : (
        <>
          <a className="button primary" href={`#${reviewPath(due[0])}`}>
            Start: {due.length} to review
          </a>
          <ul className="review-list">
            {due.map((r) => (
              <li key={reviewPath(r)} className="card">
                <a href={`#${reviewPath(r)}`}>
                  <span className="pill">{KIND_LABEL[r.kind]}</span>
                  <span className="review-title">
                    {r.title}
                    <small className="muted">
                      {r.module_title} · {r.lesson_title}
                      {r.overdue_days >= 1 && ` · ${Math.floor(r.overdue_days)} day${r.overdue_days >= 2 ? "s" : ""} overdue`}
                    </small>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
