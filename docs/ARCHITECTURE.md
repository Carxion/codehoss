# Architecture

## Components

```
Browser (React + Monaco + console + Library Explorer; notebook view M3, showcases M6)
   │  HTTP + WebSockets (interactive runs, LSP), all under /api, cookie auth
   ▼
API (FastAPI, src/dojo/api.py)
   ├── module registry   — discovers modules in /content, resolves prerequisites
   ├── content service   — lessons/steps with answers stripped; hints one level at a time
   ├── session manager   — one sandbox per (user, module), reused across page loads
   ├── LSP bridge        — WebSocket ↔ stdio of a per-connection language-server container
   ├── grader            — runs hidden tests / try-it checks inside the sandbox
   ├── error explainer   — traceback → plain-English message + did-you-mean
   ├── store             — accounts, tokens, per-step progress: SQLite (→ Postgres later)
   └── tutor (M8)        — Socratic help on the learner's AI backend, with a leak guard
   │
   ▼
Sandbox containers (image chosen by module.yaml, same lockdown for all)
   ├── session container   — learner runs, tests, try-its (one folder per run)
   ├── LSP container       — basedpyright, 512 MB, lives as long as the editor connection
   ├── Jupyter kernel (notebook modules, M3) · sidecars e.g. Postgres (M3)
   └── runtime: Docker (M1–M6) → Kubernetes pods + lab namespaces (M7+)
```

## Modules

The platform has no course content baked in. On startup the module registry scans
`content/*/module.yaml`, validates each module, and builds:
- the catalog and prerequisite graph
- the per-module sandbox image spec (`dojo-python`, `dojo-ds`, `dojo-ai`, …)
- the Library Explorer index — generated at image build time by introspecting the
  installed packages (module → classes/functions → signatures + docstrings), stored as
  JSON so the panel loads instantly without a live session

Adding a course = adding a folder. A module only needs platform changes if it requires a
new capability (notebook view, sidecar services, network allowlist, labs).

## IntelliSense

basedpyright runs from the **module's own image**, in its own locked-down container
(not the session's, so learner code can't starve or kill it), so it sees exactly the
packages the learner's code will run with. The API relays LSP JSON messages between a
WebSocket and the server's stdio (`src/dojo/lsp.py`).

In the browser, `web/src/lsp.ts` is a small purpose-built LSP client (completion +
resolve, hover, signature help, diagnostics) rather than `monaco-languageclient`. It
keeps the bundle smaller and lets us post-process results for beginners: identifiers
the current step mentions rank first, and common diagnostics are reworded. Beginner
snippets (`web/src/snippets.ts`) are a separate completion provider. Curated hover docs
are planned for M3.

## Notebooks

Notebook modules (`default_view: notebook`) run cells on a kernel: one long-lived
IPython process inside the learner's session container, started with
`docker exec -i ... python -c <dojo/_kernel.py>`, so images need no extra files. It
speaks JSON lines over stdio and uses IPython's `InteractiveShell` for real notebook
behaviour (last expression shown, rich reprs, inline matplotlib). The API bridges it to
the browser over `/api/sessions/<id>/kernel`; each cell gets a 60 s limit (interrupt,
then restart). Errors come back with the same plain-English explanation as runs.

Notebook content is stored as Python with `# %%` cell markers, so grading is
unchanged: the whole notebook runs as one script against hidden tests. Test helpers in
`dojo_checks` (copied into each grading run) give friendly failures for DataFrames,
Series, numbers and charts.

For IntelliSense the client stitches the cells into one virtual document (plus a
`display` import), so names from earlier cells complete in later ones; results are
mapped back to the right cell.

## Projects and portfolio

A lesson with a `project:` block is a project; its exercise steps are checkpoints. The
lesson payload sends every level's starter plus the learner's latest passing code for
each checkpoint, so the browser can carry code forward (Solo, or "start from my code")
without another round trip. The level is stored per user and project, and the hint
endpoint enforces it (Solo: no hints; Assisted: no show me). Every passing check is
stored in `submissions`; a project is finished when every checkpoint has one, and
`/api/portfolio/.../export` zips the final code with a generated README (notebooks are
also converted to `.ipynb`).

## Labs

Modules with `sandbox.lab: docker` get a second container per session: `docker:dind`
(privileged, or `DOJO_LAB_RUNTIME` such as sysbox) on a per-session `--internal` network,
reachable from the session as `tcp://docker:2375` and from nowhere else. The session
container keeps its lockdown (read-only root, no capabilities, uid 1000) and gains only that
network plus the Docker CLI (copied from `docker:cli`). `sandbox.lab_images` are piped in
with `docker save | docker load` at start, since labs can't pull. The engine's storage is an
anonymous volume, removed with the session (`docker rm --volumes`); orphans and labelled
networks are cleaned at server start.

Lab exercises live in `/work/<name>` in the session: seeded from `files/` on first open
(never over the learner's work; emptied in place on reset so an open shell stays valid),
edited through `/api/sessions/{id}/lab/{exercise}/files`, and graded by `grade_lab`, which
runs the tests in the session with `LAB_DIR` set. The terminal is `dojo._term` (a PTY around
bash, JSON-lines input so resizes travel with keystrokes) bridged to xterm.js by
`/api/sessions/{id}/terminal`.

Kubernetes labs (`sandbox.lab: kubernetes`) also start `rancher/k3s` on that network
(alias `k3s`, NodePorts at `http://k3s:PORT`). It is created stopped, given an image tarball
(k3s system images plus `lab_images`) and a `registries.yaml` through `docker cp -`, then
started with a dummy default route (k3s won't pick a node IP without one; the network has
no way out regardless). The engine runs with `--insecure-registry docker:5000` and a
`registry` container labelled `dojo.keep=1`, which lab resets leave alone; resets also
delete the learner's namespaces (waiting, so the next exercise can reuse a name) and
objects. The session gets a kubeconfig pointing at `https://k3s:6443`; `kubectl` is the k3s
multi-call binary and `helm` is copied from `alpine/helm`.

k3s's bundled Traefik installs through its Helm controller, which would mean more images and
a slower start, so the cluster gets a plain Traefik instead: a manifest dropped into k3s's
auto-applied `server/manifests` folder (RBAC, a default IngressClass, a Deployment with
`hostPort: 80`). Ingress rules answer at `http://k3s/`; `dojo_checks.ingress_get` waits out
the moment a new rule isn't picked up yet. The local-path provisioner's helper image is
preloaded too, so PersistentVolumeClaims bind without internet.

## Pseudocode and step-through

A module with `language: pseudo` (Programming Basics) is written in Dojo pseudocode,
run by `src/dojo/_dojo_pseudo.py`: a tokenizer, a recursive-descent parser and a
tree-walking interpreter in one standard-library file. It's copied into each run as
`dojo_pseudo.py` next to the learner's `main.pseudo` and a two-line `main.py` that runs it
and copies its variables into `main.py`'s globals. Everything built for Python (interactive
runs, the pytest `run_program` fixture, try-it checks) works unchanged: tests read
variables and call pseudocode functions as Python callables. Mistakes raise `PseudoError`
(message already written for beginners, plus a line number); an excepthook prints it in
traceback shape so the explainer and "Go to line" work.

`POST /sessions/{id}/trace` runs `dojo_pseudo.py --trace` in the sandbox. The interpreter
records a step before each statement and each loop check: the line, every active
function's variables (rendered as shown values), and how much output existed. The output
is sent once, not per step. Traces stop at 1,000 steps so an endless loop still returns.
`TracePanel` plays it back, highlights the line in Monaco with a decoration, and marks
changed variables; the editor is read-only while stepping.

## Showcases and speed grading

A `showcase` step names an algorithm and optional input; the API passes it through and the
browser does the rest. `web/src/showcase/algorithms.ts` has one recorder per algorithm: it
runs the algorithm in TypeScript and returns a list of frames (array, stack, tree, graph or
grid, each with a message). `ShowcaseView` is the player and renderers. Recording in the
browser means no sandbox round trip, instant replays, and safe custom input (recorders clamp
sizes). The editor stays mounted but hidden during a showcase, so code isn't lost.

Speed tests call `dojo_checks.assert_fast(fn, *args, budget=…, size=…, hint=…)`. In the
sandbox it arms `setitimer(ITIMER_REAL)`; SIGALRM raises an `AssertionError` that says
which input was too slow, so an O(n²) attempt fails within the budget instead of running
until the exercise's `time_limit_s`.

## AI gateway

Sandboxes have no network, yet AI lessons call models. The path:

```
notebook cell: dojo_ai.chat(...)          (dojo_ai is installed in every image)
  → kernel sends {"type": "ai_request"} on its protocol channel
  → Kernel host (notebook.py) calls the API's ai_handler
  → Gateway (ai.py): rate limit, size caps, then Ollama (HTTP on the host)
                     or Claude (anthropic SDK, the learner's decrypted key)
  → reply written back to the kernel's stdin; a {"type": "ai"} event to the browser
    becomes the "via <model>" badge under the cell
```

So keys never enter the sandbox, there's one place for limits, and switching model in
the UI applies to the very next call (settings are read per call). Time spent waiting
for a model doesn't count against the cell's 60 s limit. Claude requests opt in to
server-side refusal fallbacks. Embeddings use Ollama's `nomic-embed-text` when
available, else the deterministic built-in `simple_embed` (Claude has no embeddings API).

Outside a kernel (grading, try-its, editor runs) `dojo_ai` runs in **practice mode**:
`chat` returns a practice reply or whatever a test scripts with `dojo_ai.fake(...)`,
and records every call in `dojo_ai.calls`. The grader resets it before each test.
Exercises therefore check what learners control (prompts, history, parsing, retrieval,
loops) without paying for or depending on a real model.

## Tutor

The 🧑‍🏫 Tutor panel sits beside every lesson step (off in Solo projects). It runs on the
same backend the learner picked for AI lessons, through the gateway's `chat_stream`.

```
TutorPanel: question + the step's code and last Check (gathered at send time)
  → POST /api/tutor
  → tutor.context_for: lesson text so far, the step's task, visible tests, author hints,
    the reference solution, the learner's code (numbered) or lab files, the last Check
  → tutor.system_prompt: Socratic rules + that context; last 12 turns of the chat
  → Gateway.chat_stream (Ollama /api/chat stream, or Claude messages.stream)
  → LeakGuard → JSON lines back: meta (model), text chunks, done / error
```

The model sees the solution so its nudges point the right way. The prompt tells it never
to write it, and `LeakGuard` checks what comes out anyway: prose streams straight
through, but code (fenced blocks, inline spans) is held until it closes and compared
line by line, ignoring whitespace and comments, with the solution. A block that repeats
solution lines the learner hasn't written and that weren't in the starter is replaced by
a note: one such line is enough when the solution is short, two otherwise. Quizzes never
send the answer at all. Each question adds to the step's `tutor_questions` progress
counter. Conversations live in the browser (sessionStorage), one per step.

## Skill map, spaced review and streaks

All three are computed by `dojo/skills.py` (pure functions) from what the store already
records, plus two tables: `reviews` (one card per step) and `activity` (one row per
progress event).

- **Cards.** The first pass of a quiz, try-it or non-lab exercise (not project
  checkpoints) creates a card due in 1 day (3 for exercises). An answer while it's due
  multiplies the interval by 2.5, or 1.3 if a hint or the tutor helped since it fell due
  (`hinted`); a wrong answer or "Show me" sets it to 0.4 days and keeps it due, so one
  clean pass brings it back tomorrow. Answers before the due date change nothing. Cards
  whose step has since moved are skipped, not deleted.
- **Review mode** is the lesson view at `#/review/<module>/<lesson>/<step>`: the step
  starts from its starter, not the learner's saved draft, and drafts aren't saved.
- **Mastery** per practice step: 1 for a clean pass, minus 0.12 per hint (max 0.4) and
  0.05 per tutor question (max 0.15), 0.4 after "Show me"; successful reviews raise it to
  0.6 + 0.2 × reps; an overdue card fades it towards half. A lesson is the average; its
  state is new / learning (< 50%) / practising / strong (≥ 85%) / fading (a review due).
  `GET /api/skills` returns every module with its prerequisite depth so the map can lay
  courses out in columns and draw the prerequisite lines.
- **Streaks** group activity by the learner's calendar day: the browser sends its UTC
  offset (`?tz=` minutes east), so studying at 11 pm in Denver counts for that day. A day
  with no activity yet doesn't break the current streak until it's over.

## Studio (authoring)

`dojo/authoring.py` backs the Studio page and `dojo new`. Only usernames in
`DOJO_AUTHORS` (or `dojo serve --author`) get the `/api/author/*` routes; it edits files
on the server, so it's off unless someone is named. It only touches text files (YAML,
Markdown, code, tests; 200 KB max) inside the content folder.

- **Preview** copies the edited module's text files to a temporary folder, writes the
  unsaved text over its copy and loads it with the normal loader, so it shows exactly
  what saving would: problems (YAML errors carry a line; pydantic locations such as
  `steps.3.md` are found in the YAML node tree) and the lesson rendered with the same
  `_public_step` JSON the lesson page uses, never solutions.
- **Test lesson** runs `validate._check_execution` on that temporary copy, limited to
  the lesson, in the author's sandbox session for the module (labs included).
- **Save** writes the file and reloads content *in place* (the app and session manager
  share the `Content` object). A module that stops loading keeps its last good version,
  so learners never see it vanish mid-edit.
- **Templates** (`new_module`, `new_lesson`, `new_exercise`) add the lesson to
  `module.yaml` / the step to `lesson.yaml` by text edit, keeping comments, and each
  template is tested to pass validation and its own solution/starter check.

## Deployment (Docker image, Helm)

The `Dockerfile` builds one image: the web app, the Python app, the courses (twice: a
live copy and a pristine `content.dist`) and the Docker CLI. The server drives sandboxes
through `DOCKER_HOST`, so anywhere it runs it needs an engine.

The Helm chart (`deploy/helm/codehoss`) runs one pod: `seed-content` (init) copies the
courses onto the content volume; `docker` is a privileged `docker:dind` **native
sidecar** (an init container with `restartPolicy: Always`, so it's up before the steps
after it) listening only on a unix socket in a pod-local `emptyDir`, never TCP (the
image's default entrypoint would also open an unauthenticated 2375, so the chart runs
`dind dockerd` directly, with its networks' MTU taken from the pod's interface, since
overlay networks are often below Docker's 1500); `build-images` (init) runs `dojo build-images`, cached on the
docker volume; then the server. Course data is bind-mounted into sandboxes by path, and
a bind source resolves on the engine's filesystem, so the engine mounts the content
volume at the same `/app/content` path as the server. One replica, `Recreate`: SQLite and
in-memory sessions. Data and content volumes and the secret key are kept on uninstall.

## Interactive runs

The Run button uses a WebSocket: output streams back as it's printed, keystrokes typed in
the console are fed to the program's stdin, and Stop kills the run's process group.
Because a run may sit waiting for typing, wall-clock time is generous (5 minutes) and
**CPU time** (`ulimit -t 10`) is what stops runaway loops. Check/try-it runs are not
interactive and keep short wall-clock limits.

## Sandboxing (the part that must be right)

Learner code is untrusted. Every session container gets:

| Control | Setting |
|---|---|
| Network | none, except: AI module (allowlist to Ollama / model API) and lab modules (isolated network) |
| User | non-root, no capabilities, `no-new-privileges` |
| Filesystem | read-only image; writable tmpfs workspace only |
| Resources | CPU quota, memory cap, pids limit, wall-clock timeout |
| Lifetime | idle sessions reaped after N minutes |

Implementation notes (M1): containers are driven through the `docker` CLI rather than the
SDK, because files are streamed into the tmpfs workspace as a tar over `docker exec -i`
(`docker cp` can't write into tmpfs mounts). Each run gets its own `/work/run-<id>`
folder that is deleted afterwards. Time limits are enforced *inside* the container with
`timeout`, since killing the host-side `docker exec` would leave the process running.

Hidden tests are copied in at grade time and removed after, so learners can't read them
from the workspace. Lab tracks (Docker/K8s) are the exception to "no network/no privileges"
and run in their own isolated environment — never on the host Docker socket.

## Content as code

Lessons live in `content/` as plain files and are validated in CI: every exercise must
have a reference solution that passes its hidden tests. Content can be authored and
reviewed like code.

## Tech choices

| Area | Choice | Why |
|---|---|---|
| Backend | FastAPI + Pydantic | async, WebSockets, typed |
| Package mgmt | uv | fast, already in use on this machine |
| Frontend | React + Vite + Monaco | Monaco = VS Code editor |
| IntelliSense | basedpyright + own small LSP client | real completions from installed packages |
| Terminal | xterm.js | standard |
| Notebooks | Jupyter kernel protocol | reuse existing kernels, rich output |
| Grading | pytest + custom plugin (JSON results) | familiar to learners |
| Local k8s | kind | lightweight, scriptable |
| CI | GitLab CI | team preference |
