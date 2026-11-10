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
   └── tutor (M8)        — Ollama client
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
delete the learner's namespaces and objects. The session gets a kubeconfig pointing at
`https://k3s:6443`; `kubectl` is the k3s multi-call binary.

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
