# Curriculum & Modules

DataDojo content is organized as **modules** — self-contained course packs. The platform
discovers modules from `content/`, shows them in the course catalog, and enforces
prerequisites. Each module declares its own sandbox image and libraries, which is also what
drives IntelliSense and the Library Explorer.

```
Python Basics ──► Data Science ──► AI
      │                │            │
      └────────────────┴────────────┴──► Projects (build plans)

Later: DSA · Docker · Kubernetes · MLOps
```

## Starter modules

### 1. Python Basics — `python-basics`
Audience: never coded before. Image: `dojo-python` (stdlib + pytest + rich).

| # | Lesson | Hands-on |
|---|---|---|
| 1 | Your first program — print, comments, running code | greeting card |
| 2 | Variables & types — str, int, float, bool | unit converter |
| 3 | Input & strings — f-strings, methods, slicing | name formatter |
| 4 | Decisions — if/elif/else, comparisons, logic | grade calculator |
| 5 | Loops — for, while, range, break/continue | number guessing game |
| 6 | Lists & tuples | shopping list |
| 7 | Dictionaries & sets | word counter |
| 8 | Functions — params, return, scope, docstrings | tip calculator library |
| 9 | Errors & debugging — reading tracebacks, try/except | fix-the-bugs challenge |
| 10 | Files & modules — open, csv, json, import | contact book saved to JSON |
| 11 | Classes & objects | bank account simulator |
| 12 | Using libraries — pip, venvs, requests, datetime; testing with pytest | API-powered quote app |

Mini-projects: Text Adventure (after L7), Personal Budget CLI (after L12).

### 2. Data Science — `data-science`
Prereq: Python Basics. Image: `dojo-ds` (numpy, pandas, matplotlib, seaborn, plotly,
scipy, scikit-learn, sqlalchemy, jupyter). Notebook view by default.

| # | Lesson | Hands-on |
|---|---|---|
| 1 | What data science is; notebooks | explore a tiny dataset |
| 2 | NumPy arrays & vectorization | grade statistics without loops |
| 3 | pandas Series & DataFrames | load and inspect a CSV |
| 4 | Selecting, filtering, sorting | answer questions about movies data |
| 5 | Cleaning — missing values, types, duplicates | clean a messy survey |
| 6 | groupby, merge, pivot | sales report |
| 7 | Visualization — matplotlib, seaborn, plotly | build a chart gallery |
| 8 | Statistics — distributions, sampling, hypothesis tests | A/B test analysis |
| 9 | SQL for analysts (Postgres) | query a store database from Python |
| 10 | Intro machine learning — scikit-learn workflow | predict house prices |
| 11 | Classification & evaluation | spam classifier, confusion matrix |
| 12 | Clustering & feature engineering | customer segments |

Capstone: guided end-to-end EDA + model report on a real dataset.

### 3. AI — `ai`
Prereq: Python Basics (Data Science recommended). Image: `dojo-ai` (CPU PyTorch, numpy,
an LLM client, embeddings lib, a lightweight vector store).
Model backend: local Ollama or a learner-supplied API key.

| # | Lesson | Hands-on |
|---|---|---|
| 1 | What "AI" means — ML vs deep learning vs LLMs | sort examples into categories |
| 2 | Neural networks from scratch (NumPy) | a single neuron learns AND/OR |
| 3 | PyTorch basics — tensors, autograd | fit a line with gradient descent |
| 4 | Training a small network | handwritten digit classifier |
| 5 | How LLMs work — tokens, context, sampling | tokenizer explorer |
| 6 | Calling an LLM from Python | build a chat loop |
| 7 | Prompt engineering & structured output | extract JSON from messy text |
| 8 | Embeddings & semantic search | search your notes by meaning |
| 9 | RAG — retrieval-augmented generation | Q&A bot over a document set |
| 10 | Tool use & simple agents | agent that calls a calculator + weather tool |
| 11 | Evaluating AI output | build a small eval suite |
| 12 | Responsible AI — bias, privacy, safety | audit a model's outputs |

Capstone: document Q&A assistant with evals.

### 4. Projects — `projects`
Build plans that combine modules. Each plan has a spec, checkpoints (graded by tests),
and three scaffolding levels: **Guided → Assisted → Solo**.

| Plan | Uses | Checkpoints |
|---|---|---|
| CLI Expense Tracker | Python Basics | add/list → categories → save to JSON → monthly report |
| Weather Dashboard | Basics + DS | fetch API → clean → chart → export HTML |
| Data-Cleaning Pipeline | DS | load → validate → clean → test → schedule |
| Movie Recommender | DS + ML | explore → similarity → recommend → evaluate |
| Document Q&A Bot | AI | chunk → embed → retrieve → answer → eval |
| Image Classifier | AI | dataset → train → evaluate → simple web demo |

## Later modules

| Module | Highlights | Needs |
|---|---|---|
| DSA | Big-O, hashing, pointers, trees, graphs, DP; animated showcases; perf grading | showcases (M6) |
| Docker | images, Dockerfiles, compose, multi-stage builds | lab capability (M7) |
| Kubernetes | pods, deployments, services, config, probes, Helm | lab capability (M7) |
| MLOps | serve a model, containerize, deploy to k8s, GitLab CI, monitoring | lab capability (M7) |

## Module format

```
content/
  python-basics/
    module.yaml
    01-first-program/
      lesson.yaml          # ordered guided steps (see below)
      ex01-hello/
        exercise.yaml
        starter.py
        solution.py        # reference — never sent to the browser
        tests/
          test_visible.py  # learner can run these
          test_hidden.py   # grading, edge cases
```

`module.yaml`:

```yaml
id: data-science
title: Data Science
level: beginner-intermediate
prerequisites: [python-basics]
sandbox:
  image: dojo-ds
  packages: [numpy, pandas, matplotlib, seaborn, plotly, scipy, scikit-learn, sqlalchemy]
  services: [postgres]        # optional per-session sidecars
  network: none               # or an allowlist (AI module)
default_view: notebook        # editor | notebook
library_explorer:             # what the explorer panel highlights first
  featured: [pandas, numpy, matplotlib.pyplot]
lessons: [01-intro, 02-numpy, 03-pandas]
```

`lesson.yaml` (guided steps):

```yaml
title: Lists
steps:
  - type: explain
    md: "A list holds many values in order..."
  - type: example
    code: "fruits = ['apple', 'banana']\nprint(fruits[0])"
    runnable: true
  - type: try-it              # small typed step, checked instantly
    prompt: "Add 'cherry' to fruits using .append()"
    check: "assert fruits[-1] == 'cherry'"
    hints: ["Lists have an append method", "fruits.append('cherry')"]
  - type: exercise
    ref: ex01-shopping-list
  - type: quiz
    question: "What does fruits[-1] return?"
    options: [first item, last item, an error]
    answer: 1
```
