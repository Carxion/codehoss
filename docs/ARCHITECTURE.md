# Architecture

## Components

```
Browser (React + Monaco + xterm.js + notebook view + Library Explorer + showcase renderer)
   │  HTTPS / WebSocket (incl. LSP-over-WebSocket)
   ▼
API (FastAPI)
   ├── module registry   — discovers modules in /content, resolves prerequisites
   ├── content service   — serves lessons/steps/exercises (solutions never leave the server)
   ├── session manager   — creates/destroys learner sandboxes from the module's image
   ├── LSP proxy         — bridges Monaco ↔ language server inside the session
   ├── grader            — runs hidden tests inside the sandbox, parses results
   ├── error explainer   — traceback → plain-English message + did-you-mean
   ├── progress store    — SQLite (M0–M2) → Postgres (M3+)
   └── tutor (M8)        — Ollama client
   │
   ▼
Sandbox runtime (one per session; image chosen by module.yaml)
   ├── learner workspace + Python
   ├── basedpyright language server  — completions/signatures/hover from installed packages
   ├── Jupyter kernel (notebook modules)
   ├── optional sidecars (e.g. Postgres)
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

The language server runs **inside** the session container, not on the API host, so it
sees exactly the packages the learner's code will run with. The API proxies LSP messages
over WebSocket to `monaco-languageclient` in the browser. A thin middleware layer adds
beginner snippets, curated hover docs, and lesson-aware ranking on top of raw LSP results.

## Sandboxing (the part that must be right)

Learner code is untrusted. Every session container gets:

| Control | Setting |
|---|---|
| Network | none, except: AI module (allowlist to Ollama / model API) and lab modules (isolated network) |
| User | non-root, no capabilities, `no-new-privileges` |
| Filesystem | read-only image; writable tmpfs workspace only |
| Resources | CPU quota, memory cap, pids limit, wall-clock timeout |
| Lifetime | idle sessions reaped after N minutes |

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
| IntelliSense | basedpyright + monaco-languageclient | real completions from installed packages |
| Terminal | xterm.js | standard |
| Notebooks | Jupyter kernel protocol | reuse existing kernels, rich output |
| Grading | pytest + custom plugin (JSON results) | familiar to learners |
| Local k8s | kind | lightweight, scriptable |
| CI | GitLab CI | team preference |
