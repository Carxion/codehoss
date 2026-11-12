import { useCallback, useEffect, useState } from "react";
import { AIProviderRoot, useAI } from "./aiContext";
import { api, progressApi } from "./api";
import Catalog from "./components/Catalog";
import LessonView from "./components/LessonView";
import Login from "./components/Login";
import Portfolio from "./components/Portfolio";
import Review from "./components/Review";
import SkillMap from "./components/SkillMap";
import Studio from "./components/Studio";

// Hash routes keep the server simple (no SPA fallback needed):
//   #/                          catalog
//   #/learn/<module>/<lesson>/<step>
//   #/review/<module>/<lesson>/<step>   the same step, answered from memory
//   #/skills, #/review, #/portfolio, #/studio (authors)
type Route =
  | { page: "catalog" }
  | { page: "portfolio" }
  | { page: "skills" }
  | { page: "review" }
  | { page: "studio" }
  | { page: "learn" | "review-step"; module: string; lesson: string; step: number };

function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/");
  if (parts[0] === "learn" && parts[1] && parts[2]) {
    return { page: "learn", module: parts[1], lesson: parts[2], step: Number(parts[3] ?? 0) || 0 };
  }
  if (parts[0] === "review" && parts[1] && parts[2]) {
    return { page: "review-step", module: parts[1], lesson: parts[2], step: Number(parts[3] ?? 0) || 0 };
  }
  if (parts[0] === "portfolio") return { page: "portfolio" };
  if (parts[0] === "skills") return { page: "skills" };
  if (parts[0] === "review") return { page: "review" };
  if (parts[0] === "studio") return { page: "studio" };
  return { page: "catalog" };
}

export function navigate(path: string) {
  location.hash = path;
}

export default function App() {
  const [user, setUser] = useState<string | null | undefined>(undefined);
  const [author, setAuthor] = useState(false);
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash));

  useEffect(() => {
    const onHash = () => setRoute(parseRoute(location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        setUser(me.username);
        setAuthor(Boolean(me.author));
      })
      .catch(() => setUser(null));
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  if (user === undefined) return <div className="splash">Loading…</div>;
  if (user === null) {
    return (
      <Login
        onLogin={(name) => {
          setUser(name);
          api.me().then((me) => setAuthor(Boolean(me.author)), () => {});
        }}
      />
    );
  }

  return (
    <AIProviderRoot>
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          <span className="brand-mark">C</span> CodeHoss
        </a>
        <div className="topbar-right">
          {author && (
            <a href="#/studio" className="small">
              Studio
            </a>
          )}
          <ReviewLink route={route} />
          <a href="#/skills" className="small">
            Skill map
          </a>
          <a href="#/portfolio" className="small">
            Portfolio
          </a>
          <AIChip />
          <span className="muted username">{user}</span>
          <button className="link" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      {route.page === "catalog" ? (
        <Catalog />
      ) : route.page === "portfolio" ? (
        <Portfolio />
      ) : route.page === "skills" ? (
        <SkillMap />
      ) : route.page === "review" ? (
        <Review />
      ) : route.page === "studio" ? (
        <Studio />
      ) : (
        <LessonView
          key={`${route.page}/${route.module}/${route.lesson}`}
          moduleId={route.module}
          lessonSlug={route.lesson}
          stepIndex={route.step}
          review={route.page === "review-step"}
        />
      )}
    </div>
    </AIProviderRoot>
  );
}

/** "Review" with how many are due; refreshed whenever the page changes. */
function ReviewLink({ route }: { route: Route }) {
  const [due, setDue] = useState(0);
  useEffect(() => {
    progressApi.reviews().then((r) => setDue(r.length), () => {});
  }, [route]);
  return (
    <a href="#/review" className="small review-link">
      Review{due > 0 && <span className="count-badge">{due}</span>}
    </a>
  );
}

/** Always-visible indicator of which model answers hoss_ai calls; opens the picker. */
function AIChip() {
  const { status, label, openSettings } = useAI();
  return (
    <button
      className={`ai-chip ${status?.current ? "" : "unset"}`}
      onClick={openSettings}
      title="Choose which AI model answers hoss_ai calls"
    >
      🤖 {label}
    </button>
  );
}
