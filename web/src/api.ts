// Typed client for the CodeHoss API (see src/dojo/api.py).

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
/** What learners write in a module: Python, or Dojo pseudocode (Programming Basics). */
export type Language = "python" | "pseudo";

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
  view: "editor" | "notebook" | "lab";
  language: Language;
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
  /** Worked examples of the techniques the exercise needs, on other problems. */
  guide: { md: string; code: string }[];
  starter: string;
  visible_tests: string;
  /** Projects only: the starter for each level (null: continue from your own code). */
  starters?: Record<Level, string | null>;
  /** Projects only: the learner's latest passing code for this checkpoint. */
  submission?: string | null;
  /** Lab exercises: files live in this folder in the session, not in `starter`. */
  lab?: { dir: string } | null;
}

export interface LabState {
  dir: string;
  files: Record<string, string>;
}

export type Step =
  | { index: number; type: "explain"; md: string }
  | {
      index: number;
      type: "example";
      md: string;
      code: string;
      runnable: boolean;
      /** Set when shown in another language than the module's (read-only, in the lesson). */
      language: string | null;
    }
  | { index: number; type: "try-it"; prompt: string; starter: string; hint_count: number }
  | { index: number; type: "exercise"; exercise: Exercise }
  | { index: number; type: "quiz"; question: string; options: string[] }
  | { index: number; type: "showcase"; algorithm: string; md: string; input: Record<string, unknown> };

export interface StepProgress {
  done: boolean;
  attempts: number;
  hints_used: number;
  showed_solution: boolean;
  tutor_questions?: number;
}

export interface Lesson {
  module_id: string;
  slug: string;
  title: string;
  summary: string;
  view: "editor" | "notebook" | "lab";
  language: Language;
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

export interface TraceFrame {
  name: string;
  /** Variable -> value as shown (text in quotes). */
  vars: Record<string, string>;
}

export interface TraceStep {
  /** The line about to run; 0 once the program has finished. */
  line: number;
  frames: TraceFrame[];
  /** How much of Trace.output had been shown by this step. */
  out: number;
}

export interface Trace {
  steps: TraceStep[];
  output: string;
  error: { line: number | null; message: string } | null;
  truncated: boolean;
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
  | { level: number; of: number; solution: string; solution_files?: Record<string, string> };

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
  me: () => request<{ username: string; author?: boolean }>("GET", "/me"),
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
  labOpen: (sessionId: string, exerciseId: string) =>
    request<LabState>("POST", `/sessions/${sessionId}/lab/${exerciseId}/open`),
  labFiles: (sessionId: string, exerciseId: string) =>
    request<LabState>("GET", `/sessions/${sessionId}/lab/${exerciseId}/files`),
  labWrite: (sessionId: string, exerciseId: string, path: string, content: string) =>
    request<{ saved: string }>("PUT", `/sessions/${sessionId}/lab/${exerciseId}/files`, { path, content }),
  labDelete: (sessionId: string, exerciseId: string, path: string) =>
    request<LabState>(
      "DELETE",
      `/sessions/${sessionId}/lab/${exerciseId}/files?path=${encodeURIComponent(path)}`,
    ),
  labReset: (sessionId: string, exerciseId: string, engine: boolean) =>
    request<LabState>("POST", `/sessions/${sessionId}/lab/${exerciseId}/reset`, { engine }),
  trace: (sessionId: string, code: string, inputs: string[]) =>
    request<Trace>("POST", `/sessions/${sessionId}/trace`, { code, inputs }),
  tryIt: (sessionId: string, lesson: string, step: number, code: string) =>
    request<{ passed: boolean; message: string }>("POST", `/sessions/${sessionId}/try-it`, {
      lesson,
      step,
      code,
    }),
};

// --- skills, review, streaks -------------------------------------------------------

export type SkillState = "new" | "learning" | "practising" | "strong" | "fading";

export interface LessonSkill {
  slug: string;
  title: string;
  mastery: number;
  state: SkillState;
  due: number;
  practice: number;
  practised: number;
}

export interface ModuleSkill {
  id: string;
  title: string;
  level: string;
  depth: number;
  prerequisites: string[];
  mastery: number;
  due: number;
  lessons: LessonSkill[];
}

export interface Streak {
  current: number;
  best: number;
  today: boolean;
  calendar: { date: string; count: number }[];
}

export interface SkillMap {
  streak: Streak;
  reviews_due: number;
  modules: ModuleSkill[];
}

export interface DueReview {
  module_id: string;
  module_title: string;
  lesson: string;
  lesson_title: string;
  step: number;
  kind: "quiz" | "try-it" | "exercise";
  title: string;
  overdue_days: number;
  reps: number;
}

/** Minutes east of UTC, so streak days follow the learner's own calendar. */
const tzOffset = () => -new Date().getTimezoneOffset();

export const progressApi = {
  skills: () => request<SkillMap>("GET", `/skills?tz=${tzOffset()}`),
  reviews: () => request<DueReview[]>("GET", "/review"),
};

export const reviewPath = (r: DueReview) => `/review/${r.module_id}/${r.lesson}/${r.step}`;

// --- studio (authoring) ------------------------------------------------------------

export interface AuthorMarker {
  level: "error" | "warning";
  path: string;
  line: number | null;
  message: string;
}

export interface AuthorPreview {
  markers: AuthorMarker[];
  module: { id: string; title: string; language: Language; view: string; lessons: string[] } | null;
  lesson: { slug: string; title: string; summary: string; steps: (Step | { index: number; type: "missing"; ref: string })[] } | null;
}

export interface AuthorNew {
  kind: "module" | "lesson" | "exercise";
  module: string;
  lesson?: string;
  slug: string;
  title: string;
  language?: Language;
}

export const authorApi = {
  tree: () => request<{ modules: { id: string; files: string[] }[]; markers: AuthorMarker[] }>("GET", "/author/tree"),
  read: (path: string) => request<{ path: string; text: string }>("GET", `/author/file?path=${encodeURIComponent(path)}`),
  save: (path: string, text: string) =>
    request<{ saved: string; markers: AuthorMarker[] }>("PUT", "/author/file", { path, text }),
  preview: (path: string, text: string) => request<AuthorPreview>("POST", "/author/preview", { path, text }),
  test: (path: string, text: string) =>
    request<{ checks: number; markers: AuthorMarker[] }>("POST", "/author/test", { path, text }),
  create: (body: AuthorNew) => request<{ files: string[]; markers: AuthorMarker[] }>("POST", "/author/new", body),
};

// --- tutor ----------------------------------------------------------------------

export interface TutorMessage {
  role: "user" | "assistant";
  content: string;
}

export interface TutorRequest {
  module_id: string;
  lesson: string;
  step: number;
  code: string;
  session_id: string | null;
  /** The last Check, as the learner saw it. */
  feedback: unknown;
  messages: TutorMessage[];
}

export type TutorEvent =
  | { type: "meta"; provider: AIProvider; model: string }
  | { type: "text"; text: string }
  | { type: "done"; redactions: number }
  | { type: "error"; message: string };

/** Ask the tutor; the reply streams back as JSON lines, one event per line. */
export async function askTutor(body: TutorRequest, onEvent: (e: TutorEvent) => void, signal: AbortSignal) {
  const response = await fetch("/api/tutor", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line));
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}

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
  view: "editor" | "notebook" | "lab";
  checkpoints: string[];
  code: string;
  completed_at: number;
}

export const exportUrl = (item: PortfolioItem) => `/api/portfolio/${item.module_id}/${item.slug}/export`;
