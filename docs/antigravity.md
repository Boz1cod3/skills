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
| End of a turn in `-p` | the process exits; a wave-waiting turn end therefore ends the run (see Task 0b) |
| Stream events (`stream-json`) | `init` (`conversation_id`, `init.tools`, `init.permission_mode`, `init.expanded_commands`), `step_update`, `result` (`status`, `response`, `conversation_id`, `denied_actions`) |
| Tools seen in `init.tools` | `invoke_subagent`, `manage_subagents`, `ask_question`, `wait`, `open_browser_url`, `run_command`, no `Agent` |
| `python3` on the owner's machine | Microsoft Store stub (does not run); `python` 3.11 and `py -3` 3.12 work |
| `&&` | works in pwsh 7.6; parse error in Windows PowerShell 5.1 (`a; if ($?) { b }` works) |

Reference adapter (aif-handoff PR #184, `adapters/antigravity/cli.ts`, read at `763052d`): prompt via stdin, args `--model`, `--output-format stream-json`, `--print-timeout <N>m`, `--log-file`, `--mode accept-edits`, `--project`, `--add-dir`, `--effort`, `--conversation <uuid>`, `--dangerously-skip-permissions` only when bypass is on; tree kill via `taskkill /PID <pid> /T /F` (Windows) or `SIGKILL` of the process group.

## Baseline: unmodified Autopilot under `agy -p`

`/autopilot semi A tiny CLI that prints hello` (headless, permissions skipped) reached the Разработка stage in one process: it found the skill directory by searching the disk (three wasted commands), bootstrapped `.autopilot/` with PowerShell by itself, ran `init` without a `runtime` field, opened the dashboard with `cmd /c start`, dispatched a spec reviewer (`invoke_subagent`, `Model: flash`, `TypeName: research`) and an executor (`Model: inherit`, `TypeName: self`), committed the plan — and then ended its turn to wait for the executor, which ended the process with ticket 01 `in-progress`.
