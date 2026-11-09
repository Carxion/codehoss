import { useEffect, useState } from "react";
import { api, exportUrl, type PortfolioItem } from "../api";
import Markdown from "./Markdown";

const LEVEL_LABEL = { guided: "Guided", assisted: "Assisted", solo: "Solo" } as const;
const MODULE_NAMES: Record<string, string> = {
  "python-basics": "Python Basics",
  "data-science": "Data Science",
  ai: "AI",
};

/** Finished projects: the learner's own final code, ready to download and share. */
export default function Portfolio() {
  const [items, setItems] = useState<PortfolioItem[] | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api.portfolio().then(setItems, (e) => setError(e.message));
  }, []);

  if (error) return <main className="page"><p className="error-text">{error}</p></main>;
  if (!items) return <main className="page muted">Loading your portfolio…</main>;

  return (
    <main className="page">
      <h1>Your portfolio</h1>
      <p className="muted">
        Projects you've finished, built from your own code. Download one as a zip with a README, ready to put on
        GitHub or GitLab.
      </p>
      {items.length === 0 && (
        <div className="card empty-portfolio">
          <p>No finished projects yet.</p>
          <p className="muted small">
            Finish every checkpoint of a project in the <a href="#/">Projects</a> course and it appears here.
          </p>
        </div>
      )}
      {items.map((item) => {
        const key = `${item.module_id}/${item.slug}`;
        return (
          <article key={key} className="card portfolio-card">
            <div className="module-head">
              <div>
                <h2>{item.title}</h2>
                <p className="muted">{item.summary}</p>
                <p className="small">
                  <span className="pill">{LEVEL_LABEL[item.level]}</span>{" "}
                  {item.uses.map((u) => (
                    <span key={u} className="pill">
                      {MODULE_NAMES[u] ?? u}
                    </span>
                  ))}{" "}
                  <span className="muted">Finished {new Date(item.completed_at * 1000).toLocaleDateString()}</span>
                </p>
              </div>
              <a className="button primary" href={exportUrl(item)} download>
                ⬇ Download .zip
              </a>
            </div>
            <details>
              <summary>The brief and checkpoints</summary>
              <Markdown>{item.brief}</Markdown>
              <ol>
                {item.checkpoints.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ol>
            </details>
            <button className="link small" onClick={() => setOpen(open === key ? null : key)}>
              {open === key ? "Hide code" : "View code"}
            </button>
            {open === key && <pre className="portfolio-code">{item.code}</pre>}
          </article>
        );
      })}
    </main>
  );
}
