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
