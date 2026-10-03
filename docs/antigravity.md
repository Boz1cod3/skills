# Autopilot on Antigravity

## Verified facts (2026-10-03, Windows 11, pwsh 7.6, `agy` from `%LOCALAPPDATA%\agy\bin`)

| Question | Result |
|---|---|
| Agent id for `npx skills add -a` | `antigravity` |
| Project install path | `.agents/skills/autopilot` (`--copy` avoids symlinks) |
| Global install path (`-g`) | the `skills` CLI writes `~/.agents/skills/autopilot`, but **`agy` does not discover skills there** (live probe: `/gepeto` from `~/.agents/skills` → not expanded). `agy` discovers global skills in `~/.gemini/config/skills/` (`/caveman` and a copied `/autopilot` → expanded). A `~/.gemini/config/skills.json` entry pointing at `~/.agents/skills` did not help either. |
| Skill discovered by `agy` | project `.agents/skills/` yes; global `~/.gemini/config/skills/` yes; `~/.agents/skills/` no |
| `disable-model-invocation` honoured | yes — the model denies having the skill and does not auto-invoke it on a matching request; `/autopilot` still works |
| `/autopilot` expands under `agy -p` | yes — `init.expanded_commands = [{"name":"autopilot","type":"skill"}]` |
| Prompt delivery | `-p "<prompt>"` and stdin (no `-p`) both work |
| Headless permissions | without `--dangerously-skip-permissions` every `run_command` is auto-denied and the process ends with empty output |
| `invoke_subagent` in `-p` | the CLI keeps the process alive while background subagents run (`root agent idle; waiting up to 30m0s for 1 background task(s)`; ~30 min cap observed) and the turn continues when they report. A wave longer than the cap, or a turn that ends early, ends the process. Whether running subagents die with it is unverified. |
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
| Rounds to `finishedAt` | **1** (442 s, 1.14 M tokens, 3 commits: plan, T01, final). The CLI waited for the background subagents (see the facts table). |
| Executor reliability | the first executor (`Model: flash`, `TypeName: self`) reported DONE **without writing files** (`retries 1`, `repairs 1`: "files not created on disk, tests fail"); the retry on `pro` and a third `code_builder` call produced the code. Autopilot's own failed-ticket rule handled it, but at the cost of two extra executors. |
| Read-only roles | spec reviewer (`flash`, `research`), whole-branch reviewer and blind checker (`pro`) worked. |
| Duplicate commits / stalls | none; ticket 01 `done`, blind check 4/4, `denied_actions` empty. |
| `runtime` in `state.js` | empty — the field does not exist yet (Task 2). |
| Bare `/autopilot` resume of a cut-off run | not needed in this run; see "Live resume" below. |

Consequences: the launcher's resume loop is for runs whose process ends before `finishedAt` (a wave longer than the CLI's wait cap, a turn that ends early, a crash or Ctrl+C); executors, the blind checker and the branch reviewer map to `Model: "inherit"`; `flash` is kept for the spec reviewer only.

## Install

This fork lives at <https://github.com/Boz1cod3/skills> (upstream: `nick-vels/skills`). The agent id is `antigravity`.

```powershell
# project (recommended): .agents/skills/autopilot
npx skills add Boz1cod3/skills --skill autopilot -a antigravity --copy -y

# global: the skills CLI writes ~/.agents/skills, which agy does not read — copy it on
npx skills add Boz1cod3/skills --skill autopilot -a antigravity -g --copy -y
New-Item -ItemType Directory -Force ~/.gemini/config/skills | Out-Null
Copy-Item -Recurse -Force ~/.agents/skills/autopilot ~/.gemini/config/skills/
```

`--copy` avoids symlinks, which are unreliable on Windows. After `npx skills update` repeat the `Copy-Item` for the global install.

## Run

Interactive (Antigravity IDE or `agy`): type `/autopilot [full|semi|interview|manual] [strict|deep] <what to build>`.

Headless:

```powershell
python <skillDir>/tools/agy-run.py --mode full --project D:\work\my-app "Telegram bot for repair requests"
python <skillDir>/tools/agy-run.py --resume --project D:\work\my-app      # continue a cut-off run
```

Headless cannot answer permission prompts, so tool permissions are auto-approved (`--ask-permissions` turns that off and every command is then denied). A finished turn ends the `agy -p` process, so the launcher re-enters a bare `/autopilot` (the skill's own resume) until the run has a new `finishedAt`; a `finishedAt` left by an earlier run does not count. Before every resume round it stops the run's dashboard server (`ap.py --stop-now`, ~12 s), otherwise preflight would read the live server as "the run is going on in another window" and stop to ask. `--max-rounds` (default 12) caps the loop and a resume round with no change in `updatedAt` stops it. A new brief is refused while an unfinished run exists — use `--resume`. `agy` is always asked for `stream-json`; `--output-format text` prints only the final response. `full` is the only mode designed to run without a human; `semi` finished unattended in the smoke below, but that is not guaranteed.

Exit codes: 0 finished, 1 agent error, 2 round cap, 3 no progress, 4 refused (unfinished run without `--resume`, or `--resume` with nothing to resume), 127 `agy` not found, 130 interrupted.

## How it adapts

Phases are shared with Claude Code. Host-specific behaviour (dispatch, questions, dashboard, model tier, bootstrap) lives in `phases/runtime.md`; the agent picks the `antigravity` section because it has the `invoke_subagent` tool and records it as `runtime` in `.autopilot/state.js`. Bootstrap on Antigravity is `ap.py setup` (no bash, no symlinks) instead of the bash block.

## Known limits

- Executors share one checkout (`Workspace: "inherit"`); `branch` worktrees are not used because Autopilot commits by zone.
- Executors run on `Model: "inherit"`: a `flash` executor reported DONE without writing files in one trial. `flash` is used for the spec reviewer only.
- No side pane: the dashboard opens in the browser (`Start-Process` / `open` / `xdg-open`); headless runs open nothing.
- Verified on Windows only; the macOS/Linux wording in `runtime.md` is untested.
- `.agents/skills` is shared with the Codex app (slash vs `$` commands); installing both into one project is not handled.
- Codex runtime is a stub.

## Live smoke of `agy-run.py` (2026-10-03, `A tiny CLI that prints hello`)

| Mode | Rounds | Time | Exit | Commits | Runtime in state.js |
|---|---|---|---|---|---|
| `full` | 1 | 569 s | 0 | plan, T01, final | antigravity |
| `semi` | 1 | 633 s | 0 | plan, T01, final | antigravity |

- `semi` also finished in one round on this task, so these smokes did not exercise the resume path.
- By default the launcher prints the raw `stream-json` events (noisy); `--output-format text` prints only the final response.
- No duplicated work or double commits were observed.
- Both logs contain `root agent idle; waiting up to 30m0s for 1 background task(s)`: in `agy -p` the CLI itself keeps the process alive while background subagents run (cap seen: 30 min). That is why `semi` did not need a second round here; a wave longer than that cap is the case the resume loop exists for.

## Live resume (2026-10-03)

Project with the skill installed by `npx skills add <local repo> --skill autopilot -a antigravity --copy -y`. `agy-run --mode full "A tiny Python CLI with two subcommands: hello prints hello, bye prints bye"`, then the whole launcher tree was killed (`taskkill /T /F`) 280 s in, 25 s after ticket 01 went `in-progress`. At that point the repo had only the plan commit.

| Step | Result |
|---|---|
| `agy-run --resume --mode full` | exit 0, **1 round**, 759 s |
| Preflight | took the resume path (`phases/0-resume.md`); no "another window" question (the launcher stops the server before a resume round; whether the server had survived the kill was not checked) |
| Ticket 01 | `done`, `retries 0`, one commit `T01`, no duplicate |
| Commits | plan → T01 → final |
| Orphans after the run | no `agy.exe` left running |

