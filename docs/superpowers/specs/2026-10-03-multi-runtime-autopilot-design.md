# Multi-runtime Autopilot (Claude Code + Antigravity) — Design

**Status:** approved in chat 2026-10-03 (revision C′ supersedes the earlier "C" because of finding F1).
**Repo:** `Boz1cod3/skills` (fork of `nick-vels/skills`), local clone `d:\ANTIGRAVITY\Autopilot`.

## Goal

One Autopilot skill that runs unchanged in Claude Code and additionally runs natively in
Google Antigravity (IDE and `agy` CLI) on Windows/PowerShell, with a clean extension point
for Codex later. Claude Code behaviour must not regress.

## Findings that shaped the design

- **F1 — distribution already exists.** The skill is installed with
  `npx skills add <repo> --skill autopilot -a <agent> [-g]`, which places *identical files*
  for any agent (symlink or `--copy`). An install-time step that substitutes a per-runtime
  file therefore cannot be relied on. Runtime selection must happen at run time.
- **F2 — coupling is narrow.** Claude-specific behaviour lives in exactly four places:
  executor dispatch (`phases/5-subagents.md`), asking the user, opening the dashboard
  (`phases/0-instruments.md` §1 and §3: `find -L`, `ln -sfn`, `cygpath`, `preview_start`),
  and the cheap-model mapping (`model: "sonnet"`).
- **F3 — `ap.py` is mostly portable.** It already has Windows branches (`_ps`, `cmdline`,
  `kill`, `_detached`). The `.autopilot/ap.py` copy resolves all paths from its own
  location (`A = dirname(__file__)`), so a bootstrap command run from the skill directory
  must not reuse `A`.
- **F4 — local agy CLI (verified with `agy --help`).** Binary:
  `%LOCALAPPDATA%\agy\bin\agy.exe`. Flags: `-p/--print`, `--output-format
  text|json|stream-json`, `--input-format`, `--mode accept-edits|plan`, `--model`,
  `--effort low|medium|high|max`, `--conversation <id>`, `-c/--continue`,
  `--dangerously-skip-permissions`, `--add-dir`, `--agent`, `--sandbox`,
  `--print-timeout`, `--disable-slash-commands`.
- **F6 — verified by a live baseline run (2026-10-03).** Unmodified Autopilot already runs
  under `agy -p` (`/autopilot` expands; `disable-model-invocation` honoured) but wastes calls
  hunting for `skillDir`, records no `runtime`, and in `semi` stops when its turn ends. `invoke_subagent`
  is synchronous in print mode; `full` finished in one round. A `flash` executor failed to write files. Details in
  `docs/antigravity.md`.
- **F5 — reference implementations** (read for ideas, not copied): aif-handoff PR #184
  (binary discovery, NDJSON, `--conversation` continuity, process-tree kill) and
  ai-factory PR #166 (target registry, receipts, `.agents/skills|rules|agents`,
  `.agents` collision between Antigravity and Codex app).

## Design (C′)

### 1. Shared core, one runtime contract file
`skills/autopilot/phases/runtime.md` holds the four coupling points as **named sections per
runtime** (`## claude`, `## antigravity`, `## codex`). Phases do not branch; they say
"dispatch / ask / open dashboard / model tier — see `phases/runtime.md`".
The agent picks its section by its own tool list (deterministic rule inside the file):
has `invoke_subagent` → `antigravity`; has the `Agent` tool → `claude`; otherwise ask once.
The choice is recorded: `ap.py init --runtime <id>` stores `runtime` in `state.js`, so a
resume never re-detects.

| Point | claude | antigravity |
|---|---|---|
| Dispatch executor | `Agent`, background, whole wave in one message | `invoke_subagent` (`TypeName: self`, `Workspace: inherit` — shared checkout, because Autopilot commits by zone and `branch` worktrees would break that; revisit later), automatic wake-up |
| Ask the user | chat text | chat text; `ask_question` allowed for forks in `interview`/`manual` |
| Open dashboard | `preview_start` + `navigate` | `Start-Process <http url>`, print the URL |
| Model tier | `обычная` → `sonnet` | executors → `Model: inherit` (a `flash` executor reported DONE without writing files in the live trial); `flash` only for read-only reviewers |

### 2. Cross-platform bootstrap: `ap.py setup`
New command, run from the **skill** directory copy of `ap.py` (not from `.autopilot/`):
`python <skillDir>/tools/ap.py setup`. It resolves `skillDir` from `__file__`, finds the
project root (git toplevel, else cwd), creates `.autopilot/`, copies `dashboard.html`,
`index.html` (copy, no symlink) and `ap.py`, and prints `skillDir = <abs path>`.
Claude keeps its existing bash block unchanged (no regression risk); Antigravity uses `setup`.

### 3. State
`init --runtime claude|antigravity|codex` (default `claude`, validated). Stored as
`state["runtime"]`.

### 4. Headless runner: `tools/agy-run.py`
Pure `find_agy()` (env `ANTIGRAVITY_BIN_PATH` → `PATH` → `%LOCALAPPDATA%\agy\bin\agy.exe`
→ `~/.local/bin/agy`) and `build_args(...)` (mode/depth/brief → argv, F4 flags), plus a thin
`run_round`/`main` that stream the output and kill the process tree on interrupt
(`taskkill /T /F` on Windows, process group on POSIX). Two verified headless facts shape it
(F6): without `--dangerously-skip-permissions` every `run_command` is auto-denied, so
permissions are auto-approved for all modes (`--ask-permissions` opts out); and a turn that
ends early (`semi` right after announcing the plan) ends the `-p` process, so the launcher
re-enters a bare `/autopilot` (the skill's own resume, `phases/0-resume.md`) until
`state.js` reports `finishedAt`, with a round cap and a no-progress guard. Only `full` mode
runs without a human.

### 5. Distribution and docs
No custom installer in v1. Docs state the install command per agent and the verified
Antigravity paths (Task 0 spike). `docs/antigravity.md` + README section + CHANGELOG entry.

## Out of scope (YAGNI)
Own installer/renderer, native `.agents/agents/*.md` executor profiles, stream-json
parsing UI, Codex runtime content (stub only), MCP wiring.

## Risks / unverified (resolved by Task 0)
1. Which path `npx skills add -a antigravity` writes, and whether Antigravity discovers it.
2. Whether Antigravity honours `disable-model-invocation` / `argument-hint`.
3. ~~Whether `/autopilot` expands under `agy -p`~~ — verified yes. Still open: whether a bare
   `/autopilot` resume picks up a cut-off `semi` run without redoing work (Task 6).
4. `invoke_subagent` concurrency limit (keep the existing "at most three in flight").
5. `.agents/skills` is shared with Codex app (slash vs `$` rendering): document only.

## Acceptance
- `python -m unittest tests.test_ap tests.test_agy_run` green on Windows (baseline: 24 pass).
- Claude path text unchanged except one pointer line per phase.
- A real Antigravity session completes `ap.py setup` → `init --runtime antigravity` → stage
  calls, and the dashboard serves.
