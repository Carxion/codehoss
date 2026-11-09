# DataDojo

An interactive, self-hosted learning platform for Python, data structures & algorithms, and
data science — with a browser IDE, auto-graded hands-on exercises, interactive showcases, and
real infrastructure labs (Docker, Kubernetes, databases) that learners actually run.

> Status: **M1 done** — module system, validator, CLI, first 5 Python Basics lessons,
> Docker sandbox and API. Next: M2 (guided browser IDE). See [ROADMAP.md](ROADMAP.md).

## Quick start

```bash
uv sync
uv run dojo list                    # browse modules, lessons, exercises
uv run dojo start py.hello          # read the exercise, get a starter in workspace/
uv run dojo check py.hello          # run the tests against your code
uv run dojo hint py.hello 2         # escalating hints
uv run dojo validate                # authors: check all content is solvable
uv run pytest                       # platform tests (Docker tests skip if Docker is off)
```

### Sandbox & API (needs Docker running)

```bash
uv run dojo build-images            # build per-module sandbox images (dojo-python ~210 MB)
uv run dojo check py.hello --sandbox   # grade inside a locked-down container
uv run dojo serve                   # API on http://127.0.0.1:8000 (docs at /docs)
uv run python scripts/api_demo.py   # end-to-end: session -> run -> check -> close
```

`dojo check` without `--sandbox` and `dojo validate` still run code directly on your
machine. That's fine for your own code and authored content, but anything from other
people should go through the sandbox. The API has no auth yet (M2), so keep it on
localhost.

## What it is

- **Modular courses** — self-contained modules that plug in. v1 ships **Python Basics**,
  **Data Science**, **AI**, and **Projects** (guided build plans); DSA, Docker, Kubernetes
  and MLOps come later. See [docs/CURRICULUM.md](docs/CURRICULUM.md).
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

## Local prerequisites (planned)

- Python 3.12+ (3.13 installed)
- Docker Desktop (or Rancher Desktop — pick one; running both wastes disk)
- `kubectl` + `kind` (for the Kubernetes track and the M6 runtime)
- Node 20+ (frontend)
