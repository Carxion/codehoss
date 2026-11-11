# Learning Experience

DataDojo is built for beginners. The design goal: **a learner is never stuck without a next
step.** This doc defines how that works in the UI.

## 1. Discoverability while typing (IntelliSense)

The editor knows what's available *in this module's environment* — not a generic list.

| As the learner types… | They see |
|---|---|
| `import ` | every library installed for this module, with a one-line description |
| `import pandas as pd` then `pd.` | all pandas functions/classes, grouped and filterable |
| `df.` | DataFrame methods and columns, each with a short docstring |
| `df.groupby(` | signature help: parameters, types, defaults, and which one they're on |
| hovering any name | full docs + a "see example" link |
| a typo / wrong type | squiggle with a plain-English message |

**How:** a Python language server (basedpyright) runs from the module's own sandbox image
and talks to Monaco over a WebSocket (a small purpose-built client, `web/src/lsp.ts`).
Since it sees exactly the installed packages, completions always match what will actually
run. In notebooks, all cells form one document, so names from earlier cells complete in
later ones.

**Beginner extras on top of the language server:**
- *Snippet completions* for common patterns ("for loop over list", "read CSV", "train/test
  split") — tab-stops guide what to fill in
- *Curated docs:* a module's `glossary.yaml` gives short beginner-written notes, shown
  on hover (💡) before the official docstring and in the Library Explorer
- *Lesson-aware ranking:* items taught in the current lesson rank first (e.g. in the lists
  lesson, `.append` tops the `fruits.` completion list)

## 2. Library Explorer panel

A sidebar tree of everything installed for the module:
`pandas → DataFrame → groupby` → docstring, parameters, a runnable example, and
"Insert into editor". Featured libraries (from `module.yaml`) are pinned to the top.
Search across all libraries ("how do I sort" → `sorted`, `list.sort`, `DataFrame.sort_values`).

## 3. Guided lessons

Lessons are sequences of small steps (explain → example → try-it → exercise → quiz), not
walls of text. Each `try-it` is a one- or two-line change checked instantly, so learners get
feedback every minute or two. Progress is saved per step.

Before the exercises, a lesson shows an example that uses every technique they need, so
nobody meets an exercise cold. Each exercise can also carry its own worked examples (a
`guide`): working code for a similar problem, open beside the prompt while the learner
types. The guide shows the pattern without the answer; the validator warns if it repeats
lines of the solution.

## 4. Never stuck: escalating help

| Level | What happens | Trigger |
|---|---|---|
| 0 | Visible tests show what "correct" looks like | always |
| 0 | 📘 Worked examples: the same technique on a *different* problem, beside the prompt | always (when the exercise has a `guide`) |
| 1 | Nudge hint ("What method adds to a list?") | Hint button |
| 2 | Specific hint ("Use `fruits.append(...)`") | second press |
| 3 | "Show me" — animated walkthrough of the solution, then reset to try again | third press |
| 4 | AI tutor conversation (M8) | optional |

Hints used are recorded so the skill map can suggest review, but never block progress.

## 5. Friendly error explainer

Raw tracebacks are translated before they're shown (the raw one is one click away):

> **NameError: name 'pirnt' is not defined**
> Python doesn't recognize `pirnt`. Did you mean **`print`**? (line 3)

Rule-based at first (common errors → templates + did-you-mean using the same name lists as
IntelliSense); the M8 tutor can explain unusual errors.

## 6. Scaffolding fades over time

Early lessons: starter code with `# TODO` blanks. Mid-module: function signatures only.
End of module and Projects (Solo level): empty file + spec. Learners can drop back a
level on any project if they get stuck.
