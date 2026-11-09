import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Catalog from "./components/Catalog";
import LessonView from "./components/LessonView";
import Login from "./components/Login";

// Hash routes keep the server simple (no SPA fallback needed):
//   #/                          catalog
//   #/learn/<module>/<lesson>/<step>
type Route = { page: "catalog" } | { page: "learn"; module: string; lesson: string; step: number };

function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/");
  if (parts[0] === "learn" && parts[1] && parts[2]) {
    return { page: "learn", module: parts[1], lesson: parts[2], step: Number(parts[3] ?? 0) || 0 };
  }
  return { page: "catalog" };
}

export function navigate(path: string) {
  location.hash = path;
}

export default function App() {
  const [user, setUser] = useState<string | null | undefined>(undefined);
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash));

  useEffect(() => {
    const onHash = () => setRoute(parseRoute(location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api
      .me()
      .then((me) => setUser(me.username))
      .catch(() => setUser(null));
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  if (user === undefined) return <div className="splash">Loading…</div>;
  if (user === null) return <Login onLogin={setUser} />;

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          <span className="brand-mark">D</span> DataDojo
        </a>
        <div className="topbar-right">
          <span className="muted">{user}</span>
          <button className="link" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      {route.page === "catalog" ? (
        <Catalog />
      ) : (
        <LessonView
          key={`${route.module}/${route.lesson}`}
          moduleId={route.module}
          lessonSlug={route.lesson}
          stepIndex={route.step}
        />
      )}
    </div>
  );
}
