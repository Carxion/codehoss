// Typed client for the DataDojo API (see src/dojo/api.py).

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

// --- types -------------------------------------------------------------------

export type Level = "guided" | "assisted" | "solo";

export interface LessonSummary {
  slug: string;
  title: string;
  summary: string;
  project: { uses: string[] } | null;
  steps: number;
  done: number;
}

export interface ModuleSummary {
  id: string;
  title: string;
  description: string;
  level: string;
  view: "editor" | "notebook";
  ai: boolean;
  prerequisites: string[];
  lessons: LessonSummary[];
}

export interface Exercise {
  id: string;
  module_id: string;
  title: string;
  prompt: string;
  difficulty: number;
  hint_count: number;
  starter: string;
  visible_tests: string;
  /** Projects only: the starter for each level (null: continue from your own code). */
  starters?: Record<Level, string | null>;
  /** Projects only: the learner's latest passing code for this checkpoint. */
  submission?: string | null;
}

export type Step =
  | { index: number; type: "explain"; md: string }
  | { index: number; type: "example"; md: string; code: string; runnable: boolean }
  | { index: number; type: "try-it"; prompt: string; starter: string; hint_count: number }
  | { index: number; type: "exercise"; exercise: Exercise }
  | { index: number; type: "quiz"; question: string; options: string[] };

export interface StepProgress {
  done: boolean;
  attempts: number;
  hints_used: number;
  showed_solution: boolean;
}

export interface Lesson {
  module_id: string;
  slug: string;
  title: string;
  summary: string;
  view: "editor" | "notebook";
  ai: boolean;
  project: { brief: string; uses: string[]; level: Level } | null;
  previous: string | null;
  next: string | null;
  steps: Step[];
  progress: Record<string, StepProgress>;
}

export interface Explanation {
  title: string;
  message: string;
  line: number | null;
  raw: string;
}

export interface TestResult {
  name: string;
  label: string;
  outcome: "passed" | "failed" | "error" | "skipped";
  message: string;
  explanation: string;
}

export interface CheckResult {
  passed: boolean;
  timed_out: boolean;
  results: TestResult[];
}

export type HintResult =
  | { level: number; of: number; hint: string }
  | { level: number; of: number; solution: string };

export interface LibraryMember {
  name: string;
  kind: "function" | "class" | "exception" | "value";
  signature?: string;
  doc: string;
  members?: LibraryMember[];
}

export interface Library {
  name: string;
  doc?: string;
  error?: string;
  members: LibraryMember[];
}

export interface LibraryIndex {
  featured: string[];
  libraries: Library[];
}

// --- calls -------------------------------------------------------------------

const lessonPath = (moduleId: string, slug: string) => `/modules/${moduleId}/lessons/${slug}`;

export const api = {
  me: () => request<{ username: string }>("GET", "/me"),
  login: (username: string, password: string) =>
    request<{ username: string }>("POST", "/auth/login", { username, password }),
  register: (username: string, password: string) =>
    request<{ username: string }>("POST", "/auth/register", { username, password }),
  logout: () => request<void>("POST", "/auth/logout"),

  modules: () => request<ModuleSummary[]>("GET", "/modules"),
  lesson: (moduleId: string, slug: string) => request<Lesson>("GET", lessonPath(moduleId, slug)),
  library: (moduleId: string) => request<LibraryIndex>("GET", `/modules/${moduleId}/library`),
  glossary: (moduleId: string) => request<Record<string, string>>("GET", `/modules/${moduleId}/glossary`),
  hint: (moduleId: string, slug: string, step: number, level: number) =>
    request<HintResult>("GET", `${lessonPath(moduleId, slug)}/steps/${step}/hints/${level}`),
  answer: (moduleId: string, slug: string, step: number, answer: number) =>
    request<{ correct: boolean; explanation: string }>(
      "POST",
      `${lessonPath(moduleId, slug)}/steps/${step}/answer`,
      { answer },
    ),
  viewed: (moduleId: string, slug: string, step: number) =>
    request<void>("POST", `${lessonPath(moduleId, slug)}/steps/${step}/viewed`),

  setLevel: (moduleId: string, slug: string, level: Level) =>
    request<{ level: Level }>("PUT", `${lessonPath(moduleId, slug)}/level`, { level }),
  portfolio: () => request<PortfolioItem[]>("GET", "/portfolio"),

  session: (moduleId: string) =>
    request<{ session_id: string }>("POST", "/sessions", { module_id: moduleId }),
  check: (sessionId: string, exerciseId: string, code: string) =>
    request<CheckResult>("POST", `/sessions/${sessionId}/check`, { exercise_id: exerciseId, code }),
  tryIt: (sessionId: string, lesson: string, step: number, code: string) =>
    request<{ passed: boolean; message: string }>("POST", `/sessions/${sessionId}/try-it`, {
      lesson,
      step,
      code,
    }),
};

export function wsUrl(path: string): string {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}/api${path}`;
}

// --- AI backends ---------------------------------------------------------------

export type AIProvider = "ollama" | "anthropic";

export interface AIStatus {
  provider: AIProvider | null;
  current: { provider: AIProvider; model: string | null } | null;
  ollama: {
    available: boolean;
    models: string[];
    embedding: boolean;
    error: string | null;
    url: string;
    selected_model: string | null;
  };
  anthropic: { configured: boolean; key_hint: string | null; models: string[]; selected_model: string | null };
  embeddings: "ollama" | "builtin";
}

export type AITestResult =
  | { ok: true; reply: string; provider: AIProvider; model: string; ms: number }
  | { ok: false; error: string };

export const aiApi = {
  status: () => request<AIStatus>("GET", "/ai/status"),
  save: (body: { provider: AIProvider | null; model?: string | null; api_key?: string; clear_key?: boolean }) =>
    request<AIStatus>("PUT", "/ai/settings", body),
  test: () => request<AITestResult>("POST", "/ai/test"),
};

export const PROVIDER_LABEL: Record<AIProvider, string> = { ollama: "Local", anthropic: "Claude" };

export interface PortfolioItem {
  module_id: string;
  slug: string;
  title: string;
  summary: string;
  brief: string;
  uses: string[];
  level: Level;
  view: "editor" | "notebook";
  checkpoints: string[];
  code: string;
  completed_at: number;
}

export const exportUrl = (item: PortfolioItem) => `/api/portfolio/${item.module_id}/${item.slug}/export`;
