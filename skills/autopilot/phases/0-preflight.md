# Phase 0 — Preflight

Configure the repo, raise the instruments, pick the project memory. Decide which case you are in **before** doing anything else:

| On disk | Case | What happens |
|---|---|---|
| no `.autopilot/state.js` | **new run** | everything below, in order |
| `state.js` with `finishedAt: null` | **resume** | read `phases/0-resume.md` and follow it instead of this file |
| `state.js` with `finishedAt` set | **new feature in a configured repo** | everything below; `init` archives the finished run's state into its own directory |
| `updatedAt` under five minutes old **and** the server in `.autopilot/serve.pid` answering | **the run is going on in another window** | nothing — say so in one line and ask which window carries on |

The last case needs both marks: two sessions writing one `state.js` overwrite each other, and the first to finish freezes the other's dashboard. One mark alone is an ordinary interruption — a resume.

**«Доделай ещё вот это» for a flight that already landed**, continuing it rather than starting a new one: the new brief is a new dated file in the same run directory (`phases/1-manifest.md`), and `python3 .autopilot/ap.py reopen` puts the `--wip` back and the register row into «в работе».

**Nothing here is a question for the user.** Where files live is a process decision.

## 1. Look before writing

- `git rev-parse --git-dir` — is this a repo?
- `CLAUDE.md`, `AGENTS.md` — for `phases/0-memory.md`.
- `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml` — an existing stack to respect.
- **Existing code at all** — a brownfield repo gets exploration notes in Phase 4.
- `CONTEXT.md`, `GLOSSARY.md`, `docs/adr/` — the project's vocabulary and settled decisions. The spec and tickets speak that vocabulary and flag, not silently override, anything that contradicts a recorded decision.

## 2. Git

No repo → `git init` now, so the first ticket can commit the moment it lands. Write `.gitignore` before anything else is created, with at least `.env`, `.env.*`, `!.env.example`, `node_modules/`, `__pycache__/`, `.DS_Store`. `.autopilot/` is **committed**, not ignored — it is the user's record of what was promised and delivered; only its `serve.*` files are ignored, and `init` adds that line.

A dirty working tree → say so in one line and continue; never stash, reset or clean the user's work.

## 3. Instruments

**Read `phases/0-instruments.md`**: copy the template and `ap.py`, run `init`, open the dashboard. The command table there is the whole of the instruments for the rest of the run.

The **slug** is short, kebab-case, latin (`telegram-repair-bot`) and never changes mid-flight. `init` names the run directory `<YYYY-MM-DD>-<slug>--wip` — the date the flight started, the suffix until it lands — and records it as `dir` in `state.js`. **Every path is built from `dir`**, never rebuilt from the slug.

## 4. Project memory

**Read `phases/0-memory.md`**: it picks the file — `AGENTS.md` with a `CLAUDE.md` pointer, or the user's own file, which the run does not write into — and holds the skeleton. Pass the result to `init` as `--memory-file` and `--memory-owner`. Do **not** read `phases/9-memory.md` here.

## 5. Announce and go

The opening block from `phases/0-modes.md` — mode, depth, dashboard address, memory file, and the `↑` line if `init` printed one. It is a hint, not a question: say it, then `python3 .autopilot/ap.py stage manifest` and go straight into Phase 1.
