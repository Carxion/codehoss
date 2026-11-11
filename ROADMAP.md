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
| **Programming Basics** | complete beginners, before any one language | M6.5 |
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

## M3 — Data Science module ✅ (2026-11-09)

Shipped: notebook view (cells, Shift+Enter, Run all, interrupt/restart, rich outputs:
sanitised HTML tables, PNG charts, explained errors) on an IPython kernel inside the
session; IntelliSense across cells (cells stitched into one virtual document);
beginner glossary notes on hover and in the Library Explorer; read-only `/data`
datasets (synthetic, generated by `scripts/make_datasets.py`); per-module memory;
grading helpers (`dojo_checks`: DataFrames, Series, numbers, charts); all 12 lessons
(24 exercises) validated in the sandbox; Monaco now loads only on lesson pages (first
page 474 KB instead of 4.4 MB). Verified with a 13-step notebook browser walkthrough.

Changed from the plan:
- **SQLite instead of a Postgres sidecar** for the SQL lesson: same SQL concepts, no
  extra containers. Service sidecars move to M7, where real services matter.
- **Capstone** (guided EDA + model report) moves to the Projects module (M5), which is
  built for multi-step projects.
- The language server gets the module's memory (pandas analysis needs ~1 GB).

Original plan:
- Notebook view (cells, rich outputs: tables, charts) on a Jupyter kernel in the session
- IntelliSense works in notebook cells too
- Read-only dataset library mounted into sessions
- Graders for DataFrames (shape/columns/values within tolerance), chart metadata, model
  metrics
- Per-session Postgres container for the SQL lessons
- Module content: NumPy, pandas, visualization, stats, SQL, intro ML (scikit-learn)

**Exit:** a learner completes a guided EDA + first-model project in the browser.

## M4 — AI module ✅ (2026-11-09)

Shipped: the learner picks the model that answers `dojo_ai.chat` / `dojo_ai.embed`:
**Local (Ollama)** or **Hosted (Claude, own API key)**, shown in a top-bar chip, a
banner in AI lessons, a settings panel with both options side by side (status, model
pickers, Save and test), and a "via <model>" badge under every cell that called a
model. Calls leave the network-less sandbox through the kernel channel to the server's
AI gateway, which holds the encrypted key, rate-limits (30 calls/min) and caps tokens.
Exercises are graded against a practice model (`dojo_ai.fake`), so checks are fast,
free and deterministic. 12 lessons / 24 exercises validated in the sandbox; verified
against the local Ollama install and with a 12-step browser walkthrough.

Changed from the plan:
- **No sandbox network allowlist**: AI requests are relayed by the kernel instead, so
  keys never enter the sandbox and there is one place to enforce limits.
- **No PyTorch**: neurons and gradient descent in NumPy, networks with scikit-learn's
  `MLPClassifier`; same concepts, ~700 MB smaller. The module reuses the `dojo-ds` image.
- Hosted option is Claude only for now (default `claude-opus-5-5`; Sonnet 5.5 and
  Haiku 5.5 selectable). Other providers fit behind the same gateway.
- Capstone (document Q&A with evals) moves to the Projects module.

Original plan:
- AI concepts with hands-on code: how LLMs work, tokens, prompting, embeddings, RAG,
  tool use / agents, evaluating outputs
- Two backends, learner's choice: **local Ollama** (free, offline) or a hosted model API
  key the learner supplies; key is stored per-user, never baked into images
- Sandbox network allowlist for AI lessons only (Ollama host / model API endpoint)
- Module content: PyTorch basics → neural nets → LLM apps (prompting, RAG with a vector
  store, simple agent)

**Exit:** a learner builds and runs a working RAG app inside DataDojo.

## M5 — Projects module (build plans) ✅ (2026-11-09)
Goal: bridge "I did exercises" → "I can build things".

Shipped: a `project:` block makes a lesson a multi-checkpoint project (each exercise
step is a checkpoint; hidden tests re-check every earlier checkpoint). Per-project
levels, switchable any time: **Guided** (TODO skeleton, hints, show me), **Assisted**
(function outlines, hints), **Solo** (your own passing code from the last checkpoint,
no hints; enforced by the API). "Start from my code" works at every level. Passing code
is saved server-side; a **Portfolio** page lists finished projects and exports each as
a zip (README + `main.py`, or `project.ipynb` + `project.py`). Six projects, 24
checkpoints, all three starters of each validated in the sandbox (72 starter checks).
Projects can override the view (editor/notebook) and turn on the AI picker. Verified
with an 11-step browser walkthrough that completes the Expense Tracker end to end.

Changed from the plan:
- Projects: Expense Tracker, Weather Dashboard, **House Price Report** (the Data Science
  capstone, replacing the data-cleaning pipeline, which repeated DS lesson 5), Movie
  Recommender, **Document Q&A Bot** (the AI capstone), **Digit Classifier** (instead of
  an image classifier with a web demo; sandboxes can't serve web apps yet).
- Portfolio has code and READMEs but no screenshots yet.

Original plan:

- Build plan format: a multi-milestone project with a spec, checkpoints, and graded
  milestones (each checkpoint = tests the learner's project must pass)
- Scaffolding levels per plan: *Guided* (starter files + step hints), *Assisted*
  (spec + checkpoints only), *Solo* (spec only)
- Starter plans: CLI expense tracker, weather dashboard, data-cleaning pipeline,
  movie recommender, document Q&A bot (RAG), image classifier
- Portfolio page: completed projects with README + screenshots, exportable to a git repo

**Exit:** 6 build plans playable at all three scaffolding levels.

## M6 — DSA module + showcases ✅ (2026-11-09)
Goal: watch algorithms work, then write them fast enough to pass on big inputs.

Shipped: a `showcase` lesson step that swaps the editor for an animation player
(play/pause, step, scrub, speed, and "try your own input"). Fourteen algorithms are
recorded in the browser and drawn by five renderers: array (search, two pointers,
sorting), stack (bracket matching), tree (recursion tree, BST insert, heap with its array),
graph (BFS, DFS, Dijkstra with queue/stack and distance labels) and grid (DP table).
`dojo_checks.assert_fast` gives speed-graded tests: a timer in the sandbox stops slow code
after its budget and fails with the size and a Big-O hint. The **DSA** module has 12
lessons and 24 exercises (Big-O → dynamic programming), validated in the sandbox; some
exercises also check the source (write the sort yourself, no `bisect`). Verified with a
23-step browser walkthrough of every showcase.

Changed from the plan:
- Showcases are recorded in TypeScript in the browser, not traced from Python in the
  sandbox, so they play instantly and work with no session. Learners can still change the
  input; the graph showcases use one fixed six-node graph.
- Speed limits are per-test budgets (`assert_fast`) rather than one time limit per
  exercise, so a failure can say exactly which input was too slow.

Original plan:
- Showcase framework: algorithms emit trace events → frontend animates them with
  play/step/scrub (sorting, binary search, BFS/DFS, Dijkstra, heaps, DP tables)
- Perf-graded exercises (large hidden inputs + time limits)

**Exit:** DSA module with a showcase for every core algorithm and speed-graded exercises.

## M6.5 — Programming Basics (concepts before code) ✅ (2026-11-10)
A language-agnostic first course: what a program is, variables, types, input and output,
decisions, loops, lists, functions, algorithms and problem solving, debugging and testing,
maps and records, and a closing lesson that shows one program in Python, JavaScript, R, C++
and C# side by side, with two final projects (grade book, guessing game). 12 lessons, 24
exercises.

Learners write **Dojo pseudocode**: textbook-style pseudocode (`IF ... THEN ... END IF`,
`FOR i FROM 1 TO 10`, `FUNCTION`, `OUTPUT`, `INPUT`) that really runs. It's a small
interpreter (`src/dojo/_dojo_pseudo.py`, standard library only) that is deliberately strict
(no mixing text and numbers, conditions must be TRUE/FALSE, 0-based positions) and explains
every mistake in plain words with the line number. Platform additions:
- `language: pseudo` on a module: `.pseudo` starters and solutions, a pseudocode editor mode
  (colours, auto-indent, completions and hover notes for built-ins), no language server.
- **👣 Step through**: the interpreter records each step (line about to run, every active
  function's variables, output so far); the browser highlights the line and shows a
  variables table that marks what changed, with Back/Next/Play. Programs that use INPUT
  take their answers up front.
- Grading reuses everything built for Python: pseudocode runs through a two-line `main.py`,
  so pytest tests read its variables and call its functions directly; `dojo_checks.run_pseudo`
  re-runs a learner's program with values changed to catch hard-coded answers.
- Example steps can show code in another language (read-only), for the comparison lesson.
- The catalog lists courses in prerequisite order, so the two beginner courses come first.

## M7 — Infrastructure modules (Docker, Kubernetes, MLOps) ✅ (2026-11-10)
Part 1 ✅ (2026-11-09): the **lab capability** and the **Docker** module, lessons 1–6.
A lab session is the usual locked-down session container plus a private `docker:dind`
engine on an internal network with no internet; base images are copied in at start
(about 20 s). The browser gets a lab view: the exercise's files (tabs, autosave) above a
real bash terminal (xterm.js over a WebSocket, a PTY in the session). Lab exercises have
`files/`, `solution/` and `solution.sh`; checks inspect real state (`dojo_checks`: files,
images, containers, volumes, HTTP via `http://docker:PORT`). The validator runs each
starter (must fail) and solution.sh + solution (must pass) against a reset engine.
Docker lessons: containers, Dockerfiles, layers/cache and `.dockerignore`, ports and env
config, volumes, Compose (12 exercises). Verified with an 11-step browser walkthrough.

Part 2 ✅ (2026-11-09): Docker lessons 7–12, completing the module (24 exercises): multi-stage
builds and test stages, user-defined and internal networks, health checks and restart
policies, non-root and locked-down containers, a self-hosted registry (`registry:3.1.2`
preloaded) with tagging and releases, and debugging (a CMD typo, an app bound to 127.0.0.1).

Part 3 ✅ (2026-11-09): **Kubernetes labs** and the Kubernetes module, lessons 1–6.
`sandbox.lab: kubernetes` adds a single-node k3s (`rancher/k3s:v1.37.1-k3s1`) per session on
the same internal network, plus a registry inside the lab's engine at `docker:5000` (the
engine trusts it; k3s mirrors it), so learners build, push and deploy their own images.
k3s's three system images and the module's base images are copied into it before start, so
nothing is pulled; a full lab (engine, registry, cluster) is ready in about 20 s.
`kubectl` is the k3s binary under that name, already configured. Lessons: pods and kubectl,
Deployments and rolling updates, Services (ClusterIP and NodePort), ConfigMaps and Secrets,
build-push-deploy with a rollback, probes and resources (12 exercises). The terminal now
saves edited files before running a command.

Part 4 ✅ (2026-11-10): Kubernetes lessons 7–12, completing the module (24 exercises):
namespaces and ResourceQuotas, emptyDir sidecars and PVCs, Jobs and CronJobs, Ingress by host
and path, Helm (templating, upgrade, rollback) and debugging (a broken image, selector and
port; a CrashLoopBackOff from a ConfigMap key). Platform: an ingress controller (plain
Traefik applied from k3s's manifests folder, at `http://k3s/`), the local-path helper image
preloaded so PVCs bind offline, `helm` in the lab image, resets that wait for namespaces.

Part 5 ✅ (2026-11-10): the **MLOps** capstone (6 lessons, 12 exercises), a Kubernetes lab:
train a plain-Python house-price model with versioned metrics and a quality gate, serve it
over HTTP, package it with a multi-stage build, release versions to the lab registry with a
script that refuses bad models, deploy behind an Ingress with upgrade and rollback, write a
GitLab CI pipeline (artifacts, rules, a smoke test) and run it with `ci.py` (a local
`.gitlab-ci.yml` runner: clean checkouts, artifacts, `needs`, rules, manual jobs), then
Prometheus metrics and a canary release. M7 is complete.

Changed from the plan:
- Rootful `docker:dind` (it needs `--privileged`; set `DOJO_LAB_RUNTIME=sysbox-runc` to run
  it unprivileged where sysbox is installed). Rootless dind still needs privileges on
  Docker Desktop, so it buys little here.
- Moving session orchestration onto Kubernetes is deferred to "Later": it's an operations
  change with no learner-visible benefit, and Docker Desktop runs everything fine today.
- Bind mounts aren't taught hands-on: the engine runs beside the session, so the learner's
  folders aren't on its filesystem (the lesson explains why; volumes are used instead).

Original plan:
- Lab capability: per-learner rootless Docker-in-Docker and `kind` cluster / k8s namespace
- Lab graders inspect real state (`kubectl get`, image layers, HTTP checks)
- MLOps capstone: deploy a Projects-module model to Kubernetes with a GitLab CI pipeline
  (built with its own small plain-Python model instead: labs have no internet for
  scikit-learn, and the MLOps ideas don't depend on the model)
- Session orchestration moves onto Kubernetes (one pod per session)

## M8 — AI tutor & polish
Part 1 ✅ (2026-11-10): the **AI tutor**, a 🧑‍🏫 panel beside every step (off in Solo
projects) on the learner's own backend (Ollama or Claude), streamed. It sees the lesson so
far, the step, visible tests, author hints, the learner's code or lab files and the last
Check; it's given the reference solution so its nudges are accurate, and a leak guard holds
back every code block and hides any that repeats solution lines. "Ask the tutor why" under
a failed Check; suggested questions per step type; tutor questions are recorded as progress
(feeds spaced review). Checked live with qwen2.5:7b.

Part 2 ✅ (2026-11-10): **skill map, spaced review, streaks**. Passing a quiz, try-it or
exercise creates a review card (1 day, then x2.5 per remembered review, x1.3 if a hint or
the tutor helped, back to tomorrow if forgotten). Review queue page, a review mode that
starts the step fresh, a "Review (n)" badge in the top bar. The skill map lays courses out
by prerequisites with a chip per lesson coloured by mastery (hints, "Show me", tutor use and
overdue reviews lower it). Streaks and a 12-week calendar use the learner's time zone.

Part 3 ✅ (2026-11-10): the **Studio**, a module authoring tool for users in
`DOJO_AUTHORS`: content file tree, editor with live problem markers on the right line,
a preview of the lesson as learners see it (from the unsaved text, via a temporary copy),
**▶ Test lesson** (solutions pass, starters fail, in the sandbox), Save goes live at once
(a module that breaks keeps its last good version), and templates for new modules, lessons
and exercises, also as `dojo new module|lesson|exercise`.

Part 4 ✅ (2026-11-10): **self-hosting**. A `Dockerfile` for the app and a **Helm chart**
(`deploy/helm/datadojo`): one pod with a privileged Docker-in-Docker native sidecar on a
pod-local unix socket (never TCP), content seeded onto a volume both containers mount
(sandbox data bind mounts resolve), sandbox images built at start-up and cached
(`sandbox.buildModules` to limit them; `dojo build-images --module`), persistent data,
images and content, a generated secret key kept across upgrades, optional Ingress and
Ollama. Tested by installing into k3s v1.37. M8 is complete.

- Tutor on local Ollama: sees the lesson, the learner's code and failing tests; gives
  Socratic hints, never full solutions
- Spaced-repetition review, skill map, streaks
- Module authoring tool (live preview + validation) so new modules are easy to add
- Helm chart for self-hosting

## M9–M12 — More languages, building real projects
Each language gets a **Basics** module that maps the Programming Basics concepts onto its
syntax (so learners who did Programming Basics move fast), then a set of **Projects** in
that language at Guided / Assisted / Solo level, collected in the portfolio. Order is by
demand and cost (image size, tooling).

### M9 — Multi-language platform + JavaScript
Platform (done once, used by every later language):
- `language` grows beyond `python`/`pseudo`: each language declares a sandbox image, a run
  command (plus a compile step where needed), a Monaco mode and a language server.
- Language-neutral grading: pytest still drives every exercise. I/O tests (run with inputs,
  check output) work in any language; function-level tests go through a small per-language
  harness that calls a learner's function with JSON arguments and returns JSON.
- The friendly error explainer gets a rule set per language (compiler and runtime errors).
- Step-through for real languages where a debugger protocol makes it cheap (Node inspector,
  Python's `sys.settrace`), reusing the pseudocode trace view.

JavaScript Basics (image `dojo-node`, Node 22, `typescript-language-server`): values and
`let`/`const`, strings and template literals, decisions and loops, arrays and objects,
functions and arrow functions, callbacks, modules, errors, classes, async/`await`, testing.
Projects: command-line to-do list (JSON file), quiz game, a web page with live preview
(needs a preview pane), a small REST API (local only, no internet).

### M10 — R
R Basics (image `dojo-r`, `r-base` plus tidyverse, `languageserver`, notebook view through
IRkernel): vectors (1-based!), data frames, functions, apply and the pipe, factors, dplyr,
ggplot2, simple statistics and models. Projects: survey analysis report, A/B test analysis,
a reproducible notebook report exported to HTML.

### M11 — C++
C++ Basics (image `dojo-cpp`, gcc and `clangd`): compiling and the compile-run cycle (with a
compiler-error explainer), types, control flow, functions, `std::vector` and `std::string`,
references and pointers, memory and RAII, classes, the STL and algorithms, a first look at
performance. Projects: text adventure, bank account simulator, a speed race against the
Python versions of the DSA exercises.

### M12 — C#
C# Basics (image `dojo-dotnet`, .NET SDK, `csharp-ls`): types, control flow, methods,
`List`/`Dictionary`, classes and interfaces, LINQ, exceptions, async, unit tests with xUnit.
Projects: inventory manager, console game, a small web API with ASP.NET Core minimal APIs.
The .NET SDK image is large (~800 MB); see the disk budget.

## Later / maybe
- Classrooms (instructor dashboard, cohorts)
- Pyodide offline mode for Python Basics (no backend)
- Community module registry

## Disk budget (this machine)
C: has ~100 GB free. Keep per-module images lean (AI/DL image is the big one — CPU
PyTorch only), use one Docker runtime, and have `dojo clean` prune images.
Target: whole dev setup < 15 GB. The language milestones add roughly: Node ~180 MB,
R with tidyverse ~1.2 GB, gcc ~400 MB, .NET SDK ~800 MB.
