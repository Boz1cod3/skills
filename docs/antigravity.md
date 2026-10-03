# Autopilot on Antigravity

## Verified facts (2026-10-03, Windows 11, pwsh 7.6, `agy` from `%LOCALAPPDATA%\agy\bin`)

| Question | Result |
|---|---|
| Agent id for `npx skills add -a` | `antigravity` |
| Project install path | `.agents/skills/autopilot` (`--copy` avoids symlinks) |
| Global install path (`-g`) | `~/.agents/skills/autopilot` (reported by the CLI; not exercised in a live IDE session) |
| Skill discovered by `agy` | yes (project path) |
| `disable-model-invocation` honoured | yes — the model denies having the skill and does not auto-invoke it on a matching request; `/autopilot` still works |
| `/autopilot` expands under `agy -p` | yes — `init.expanded_commands = [{"name":"autopilot","type":"skill"}]` |
| Prompt delivery | `-p "<prompt>"` and stdin (no `-p`) both work |
| Headless permissions | without `--dangerously-skip-permissions` every `run_command` is auto-denied and the process ends with empty output |
| `invoke_subagent` in `-p` | synchronous: `[subagent DONE]` arrives inline and the same turn continues; a turn that ends early (e.g. `semi` mode right after announcing the plan) ends the whole process |
| Stream events (`stream-json`) | `init` (`conversation_id`, `init.tools`, `init.permission_mode`, `init.expanded_commands`), `step_update`, `result` (`status`, `response`, `conversation_id`, `denied_actions`) |
| Tools seen in `init.tools` | `invoke_subagent`, `manage_subagents`, `ask_question`, `wait`, `open_browser_url`, `run_command`, no `Agent` |
| `python3` on the owner's machine | Microsoft Store stub (does not run); `python` 3.11 and `py -3` 3.12 work |
| `&&` | works in pwsh 7.6; parse error in Windows PowerShell 5.1 (`a; if ($?) { b }` works) |

Reference adapter (aif-handoff PR #184, `adapters/antigravity/cli.ts`, read at `763052d`): prompt via stdin, args `--model`, `--output-format stream-json`, `--print-timeout <N>m`, `--log-file`, `--mode accept-edits`, `--project`, `--add-dir`, `--effort`, `--conversation <uuid>`, `--dangerously-skip-permissions` only when bypass is on; tree kill via `taskkill /PID <pid> /T /F` (Windows) or `SIGKILL` of the process group.

## Baseline: unmodified Autopilot under `agy -p`

`/autopilot semi A tiny CLI that prints hello` (headless, permissions skipped) reached the Разработка stage in one process: it found the skill directory by searching the disk (three wasted commands), bootstrapped `.autopilot/` with PowerShell by itself, ran `init` without a `runtime` field, opened the dashboard with `cmd /c start`, dispatched a spec reviewer (`invoke_subagent`, `Model: flash`, `TypeName: research`) and an executor (`Model: inherit`, `TypeName: self`), committed the plan — the executor returned inside the turn, then the model ended its turn after announcing the plan (`semi` mode) and the process exited with the run unfinished.

## Headless waves (verified 2026-10-03)

`/autopilot full A tiny CLI that prints hello` under `agy -p … --dangerously-skip-permissions`, one invocation:

| Question | Result |
|---|---|
| Rounds to `finishedAt` | **1** (442 s, 1.14 M tokens, 3 commits: plan, T01, final). `invoke_subagent` blocks inside the turn, so there is nothing to wait for. |
| Executor reliability | the first executor (`Model: flash`, `TypeName: self`) reported DONE **without writing files** (`retries 1`, `repairs 1`: "files not created on disk, tests fail"); the retry on `pro` and a third `code_builder` call produced the code. Autopilot's own failed-ticket rule handled it, but at the cost of two extra executors. |
| Read-only roles | spec reviewer (`flash`, `research`), whole-branch reviewer and blind checker (`pro`) worked. |
| Duplicate commits / stalls | none; ticket 01 `done`, blind check 4/4, `denied_actions` empty. |
| `runtime` in `state.js` | empty — the field does not exist yet (Task 2). |
| Bare `/autopilot` resume of a cut-off run | **not exercised** (never needed in `full`); the earlier `semi` run is the case that needs it. Verified in the Task 6 `semi` smoke. |

Consequences: the launcher's resume loop is for modes that end their turn early (`semi`), not for waiting on subagents; executors map to `Model: "inherit"`; `flash` is kept for read-only reviewers only.

## Install

This fork lives at <https://github.com/Boz1cod3/skills> (upstream: `nick-vels/skills`). The agent id is `antigravity`.

```powershell
npx skills add Boz1cod3/skills --skill autopilot -a antigravity --copy -y      # project: .agents/skills/autopilot
npx skills add Boz1cod3/skills --skill autopilot -a antigravity -g --copy -y   # global:  ~/.agents/skills/autopilot
```

`--copy` avoids symlinks, which are unreliable on Windows. The global path comes from the `skills` CLI and was not exercised in a live IDE session.

## Run

Interactive (Antigravity IDE or `agy`): type `/autopilot [full|semi|interview|manual] [strict|deep] <what to build>`.

Headless:

```powershell
python <skillDir>/tools/agy-run.py --mode full --project D:\work\my-app "Telegram bot for repair requests"
```

Headless cannot answer permission prompts, so tool permissions are auto-approved (`--ask-permissions` turns that off and every command is then denied). A finished turn ends the `agy -p` process, so the launcher re-enters a bare `/autopilot` (the skill's own resume) until `finishedAt`; `--max-rounds` (default 12) caps it and a round with no change in `updatedAt` stops it. Only `full` runs without a human; the other modes stop to ask questions.

Exit codes: 0 finished, 1 agent error, 2 round cap, 3 no progress, 127 `agy` not found, 130 interrupted.

## How it adapts

Phases are shared with Claude Code. Host-specific behaviour (dispatch, questions, dashboard, model tier, bootstrap) lives in `phases/runtime.md`; the agent picks the `antigravity` section because it has the `invoke_subagent` tool and records it as `runtime` in `.autopilot/state.js`. Bootstrap on Antigravity is `ap.py setup` (no bash, no symlinks) instead of the bash block.

## Known limits

- Executors share one checkout (`Workspace: "inherit"`); `branch` worktrees are not used because Autopilot commits by zone.
- Executors run on `Model: "inherit"`: a `flash` executor reported DONE without writing files in one trial. `flash` is used for read-only reviewers only.
- No side pane: the dashboard opens in the browser via `Start-Process`.
- `.agents/skills` is shared with the Codex app (slash vs `$` commands); installing both into one project is not handled.
- Codex runtime is a stub.
