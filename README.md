# DataDojo

An interactive, self-hosted learning platform for Python, data structures & algorithms, and
data science — with a browser IDE, auto-graded hands-on exercises, interactive showcases, and
real infrastructure labs (Docker, Kubernetes, databases) that learners actually run.

> Status: **M6 done**: guided browser IDE with live IntelliSense and notebooks;
> **Python Basics**, **Data Science**, **AI** and **Data Structures & Algorithms** modules
> (12 lessons and 24 exercises each) plus **Projects**: six multi-checkpoint builds at
> Guided / Assisted / Solo level, collected in a downloadable portfolio. DSA lessons open
> with step-through algorithm animations, and its tests fail code that is too slow. AI work
> runs on a local model (Ollama) or Claude with your own key. M7 adds hands-on labs with a
> real terminal in the browser: a 12-lesson **Docker** module (a private Docker engine per
> learner) and **Kubernetes** (a private k3s cluster plus registry). Next: more Kubernetes,
> then the MLOps capstone. See
> [ROADMAP.md](ROADMAP.md).

## Run it (needs Docker running)

```bash
uv sync
uv run dojo build-images            # sandbox images + Library Explorer indexes (~1.8 GB)
cd web && npm install && npm run build && cd ..
uv run dojo serve                   # open http://127.0.0.1:8000 and create an account
```

**AI lessons:** pick a model with **🤖 AI** in the top bar. For the local option,
install [Ollama](https://ollama.com) and run `ollama pull llama3.2` (and
`ollama pull nomic-embed-text` for better embeddings). For the hosted option, paste an
Anthropic API key; it's stored encrypted (key in `DOJO_SECRET_KEY`, or `var/secret.key`
is generated) and never enters the sandbox. `DOJO_OLLAMA_URL` points at a non-default
Ollama.

For frontend work, run `uv run dojo serve` and `cd web && npm run dev` side by side;
Vite (http://localhost:5173) forwards `/api` to the server.

Keep the server on localhost for now: accounts exist, but there's no HTTPS, rate
limiting, or admin tooling yet.

## Terminal tools

```bash
uv run dojo list                    # browse modules, lessons, exercises
uv run dojo start py.hello          # read the exercise, get a starter in workspace/
uv run dojo check py.hello          # run the tests against your code (--sandbox: in Docker)
uv run dojo hint py.hello 2         # escalating hints
uv run dojo validate                # authors: every exercise solvable (--sandbox: in Docker)
uv run pytest                       # platform tests (Docker tests skip if Docker is off)
```

`dojo check` and `dojo validate` without `--sandbox` run code directly on your machine.
That's fine for your own code and authored content; the browser app always uses the
sandbox.

## What it is

- **Modular courses** — self-contained modules that plug in. v1 ships **Python Basics**,
  **Data Science**, **AI**, **Data Structures & Algorithms** and **Projects** (guided build
  plans), plus hands-on **Docker** and **Kubernetes** labs; MLOps is next. See [docs/CURRICULUM.md](docs/CURRICULUM.md).
- **Hand-holding** — bite-sized guided steps, escalating hints, a friendly error explainer,
  and scaffolding that fades as you improve. See
  [docs/LEARNING-EXPERIENCE.md](docs/LEARNING-EXPERIENCE.md).
- **An IDE that shows you what's possible** — live IntelliSense from the libraries actually
  installed for your module (type `df.` and see every DataFrame method with docs), plus a
  Library Explorer panel to browse and insert examples.
- **An autograder** — every exercise ships hidden `pytest` checks; learners get instant
  feedback, hints, and progress tracking.
- **Showcases** — step-through algorithm visualizers and interactive data demos that explain
  a concept before you practice it.
- **Labs** — exercises that need real tools (Docker, `kubectl`, Postgres, Spark) get a
  disposable lab environment spun up on demand.

## Docs

| Doc | What's in it |
|---|---|
| [ROADMAP.md](ROADMAP.md) | Milestones M0–M8, scope of each, exit criteria |
| [docs/CURRICULUM.md](docs/CURRICULUM.md) | Modules, lesson outlines, build plans, module format |
| [docs/LEARNING-EXPERIENCE.md](docs/LEARNING-EXPERIENCE.md) | IntelliSense, Library Explorer, guided steps, hints, error explainer |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, module registry, LSP, sandboxing, tech choices |

## Local prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Docker Desktop (or Rancher Desktop — pick one; running both wastes disk)
- Node 20+ (frontend)
- Later: `kubectl` + `kind` (Kubernetes module, M7)
