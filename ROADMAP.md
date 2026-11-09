# DataDojo Roadmap

Guiding rules:
1. **Every milestone ships something a learner can use end-to-end.** Content and platform
   grow together.
2. **Modular.** The platform is a shell; courses are self-contained modules that plug in.
   A new module never requires platform changes unless it needs a new capability
   (e.g. labs).
3. **Hand-holding first.** Beginners should never be stuck staring at a blank editor or a
   raw traceback. See [docs/LEARNING-EXPERIENCE.md](docs/LEARNING-EXPERIENCE.md).

## Starter modules (v1)

| Module | Who it's for | Milestone |
|---|---|---|
| **Python Basics** | complete beginners | M2 |
| **Data Science** | after Python Basics | M3 |
| **AI** | after Python Basics (Data Science recommended) | M4 |
| **Projects** | guided build plans that combine the above | M5 |

Later modules: DSA, Docker, Kubernetes, MLOps (see [docs/CURRICULUM.md](docs/CURRICULUM.md)).

---

## M0 — Skeleton & module system ✅ (2026-11-08)
Goal: the content format and module loader exist and are validated.

Shipped: `dojo list/start/check/hint/validate`; validator runs every reference solution
(must pass) and every starter (must fail) for exercises and try-it steps; lessons 1–5 of
Python Basics (10 exercises, 10 try-its, 5 quizzes).

- Repo layout, `pyproject.toml` (uv), ruff + pytest, pre-commit
- Module spec: `module.yaml` manifest (id, title, prerequisites, sandbox image, packages,
  lessons) — see [docs/CURRICULUM.md](docs/CURRICULUM.md#module-format)
- Module loader + validator: every exercise has a passing reference solution, every
  prerequisite resolves, every declared package exists in the module's image
- First 5 Python Basics lessons written in guided-step format
- GitLab CI: lint + `dojo validate` over all modules

**Exit:** `dojo validate` passes; modules can be added/removed by dropping a folder.

## M1 — Sandboxed execution service ✅ (2026-11-08)
Goal: run untrusted learner code safely.

Shipped: executor abstraction (local / Docker), `SessionManager` (one container per
session, idle reaping, orphan cleanup, session cap), FastAPI with `/run`, `/check`,
`/try-it`, and a WebSocket stream; `dojo build-images`, `dojo serve`,
`dojo check --sandbox`. Tests prove: no network, read-only root, uid 1000, memory and
pids limits, timeouts with the session surviving, runs isolated from each other.
Deferred to M2: interactive stdin over the WebSocket (M1 takes inputs up front).

- FastAPI backend: `/run`, `/check`, session lifecycle
- One Docker container per session: no network, non-root, read-only image, writable tmpfs
  workspace, CPU/mem/pids limits, timeout
- Per-module images built from `module.yaml` package lists (`dojo-python`, `dojo-ds`,
  `dojo-ai`)
- Output + test results streamed over WebSocket

**Exit:** a script can start a session, run code, and get graded results back.

## M2 — Guided IDE + Python Basics module ✅ (2026-11-08)
Goal: a beginner can learn Python from zero in the browser.

Shipped: React/Vite app (login, course catalog with progress, guided lesson view);
Monaco editor with completions, signature help, hover and diagnostics from basedpyright
running in its own sandbox container; beginner snippets and lesson-aware ranking;
Library Explorer (index built with the image); interactive console (type at `input()`,
Stop button, CPU-time limit); escalating hints ending in an animated "show me"; error
explainer for runs and test failures; accounts + per-step progress in SQLite; all 12
Python Basics lessons (24 exercises incl. 2 mini-projects); `dojo validate --sandbox`.
Verified with a 15-step headless-browser walkthrough.

Changed from the plan:
- **Own LSP client** (~300 lines in `web/src/lsp.ts`) instead of `monaco-languageclient`:
  smaller, and lets us re-rank and reword results for beginners.
- **Console instead of an xterm.js shell**: beginners need "type an answer", not a shell.
  A real terminal comes with the Docker/Kubernetes modules, where it matters.
- **Lesson 12** teaches the standard library + testing instead of `requests` (sandboxes
  have no network).
- Deferred: curated beginner hover docs (M3), trimming the 4.4 MB Monaco bundle (M3).

- React + Vite frontend; Monaco editor, lesson pane, output pane, terminal (xterm.js)
- **Live IntelliSense:** a Python language server (basedpyright) runs inside the session
  container, so completions reflect the libraries actually installed for that module:
  - completions as you type (`import pa` → `pandas`, `df.` → every DataFrame method)
  - signature help with parameter docs while typing arguments
  - hover docs, inline type/error squiggles
- **Library Explorer panel:** browse the module's installed libraries → modules →
  functions, with docstrings and one-click "insert example"
- **Guided mode:** step-by-step lessons, staged hints, friendly error explainer, "show me"
  walkthroughs (details in LEARNING-EXPERIENCE.md)
- Local accounts + progress tracking (SQLite)
- Python Basics module complete (~12 lessons, ~60 exercises, 2 mini-projects)

**Exit:** someone who has never coded can finish Python Basics without outside help.

## M3 — Data Science module
- Notebook view (cells, rich outputs: tables, charts) on a Jupyter kernel in the session
- IntelliSense works in notebook cells too
- Read-only dataset library mounted into sessions
- Graders for DataFrames (shape/columns/values within tolerance), chart metadata, model
  metrics
- Per-session Postgres container for the SQL lessons
- Module content: NumPy, pandas, visualization, stats, SQL, intro ML (scikit-learn)

**Exit:** a learner completes a guided EDA + first-model project in the browser.

## M4 — AI module
- AI concepts with hands-on code: how LLMs work, tokens, prompting, embeddings, RAG,
  tool use / agents, evaluating outputs
- Two backends, learner's choice: **local Ollama** (free, offline) or a hosted model API
  key the learner supplies; key is stored per-user, never baked into images
- Sandbox network allowlist for AI lessons only (Ollama host / model API endpoint)
- Module content: PyTorch basics → neural nets → LLM apps (prompting, RAG with a vector
  store, simple agent)

**Exit:** a learner builds and runs a working RAG app inside DataDojo.

## M5 — Projects module (build plans)
Goal: bridge "I did exercises" → "I can build things".

- Build plan format: a multi-milestone project with a spec, checkpoints, and graded
  milestones (each checkpoint = tests the learner's project must pass)
- Scaffolding levels per plan: *Guided* (starter files + step hints), *Assisted*
  (spec + checkpoints only), *Solo* (spec only)
- Starter plans: CLI expense tracker, weather dashboard, data-cleaning pipeline,
  movie recommender, document Q&A bot (RAG), image classifier
- Portfolio page: completed projects with README + screenshots, exportable to a git repo

**Exit:** 6 build plans playable at all three scaffolding levels.

## M6 — DSA module + showcases
- Showcase framework: algorithms emit trace events → frontend animates them with
  play/step/scrub (sorting, binary search, BFS/DFS, Dijkstra, heaps, DP tables)
- Perf-graded exercises (large hidden inputs + time limits)

## M7 — Infrastructure modules (Docker, Kubernetes, MLOps)
- Lab capability: per-learner rootless Docker-in-Docker and `kind` cluster / k8s namespace
- Lab graders inspect real state (`kubectl get`, image layers, HTTP checks)
- MLOps capstone: deploy a Projects-module model to Kubernetes with a GitLab CI pipeline
- Session orchestration moves onto Kubernetes (one pod per session)

## M8 — AI tutor & polish
- Tutor on local Ollama: sees the lesson, the learner's code and failing tests; gives
  Socratic hints, never full solutions
- Spaced-repetition review, skill map, streaks
- Module authoring tool (live preview + validation) so new modules are easy to add
- Helm chart for self-hosting

## Later / maybe
- Classrooms (instructor dashboard, cohorts)
- Pyodide offline mode for Python Basics (no backend)
- Community module registry

## Disk budget (this machine)
C: has ~100 GB free. Keep per-module images lean (AI/DL image is the big one — CPU
PyTorch only), use one Docker runtime, and have `dojo clean` prune images.
Target: whole dev setup < 15 GB.
