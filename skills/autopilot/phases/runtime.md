# Runtime contract

Phases never branch on the host. Everything host-specific lives here, one section per runtime.
Read this file once in Phase 0, after `0-preflight.md`.

## Which section applies

- You have the `invoke_subagent` tool → **antigravity**.
- You have the `Agent` tool and not `invoke_subagent` → **claude**.
- Neither → ask the user once which host this is. **codex** is a stub (below).

Record it with `init --runtime <id>`. On a resume read `runtime` from `state.js` and do not detect again.

## claude

- **Dispatch:** one `Agent` call per ticket, in the background; a whole wave in one message (`phases/5-subagents.md`).
- **Ask:** plain chat text.
- **Dashboard:** `preview_start`, then `navigate` (`phases/0-instruments.md` §3, Path A).
- **Model tier:** `обычная` → `model: "sonnet"` on the `Agent` call; `сильная` → the session model.
- **Bootstrap:** the bash block in `phases/0-instruments.md` §1, `python3` (on Windows `python` or `py -3`).

## antigravity

- **Dispatch:** `invoke_subagent` per ticket — `TypeName: "self"`, `Role: "Executor T<NN>"`, `Workspace: "inherit"` (one shared checkout, zones and commit-by-zone work exactly as in `phases/5-subagents.md`), `Prompt` = the paths-not-contents contract and the return contract from that file. Launch a whole wave in one tool-call block. Ending your turn is how you wait: the subagent's message wakes you (in a headless `agy -p` run `invoke_subagent` blocks inside the turn, so a wave is simply awaited; if the process ends early the launcher re-enters `/autopilot` and a ticket that is `in-progress` without a commit is re-checked before it is launched again). Subagents do not spawn subagents. Do not use `Workspace: "branch"` — it moves commits onto branches, which breaks commit-by-zone.
- **Ask:** plain chat text. `ask_question` is allowed for the forks of `interview` and `manual`, one question per call.
- **Dashboard:** `ap.py` serves it. Open it with `Start-Process "http://localhost:<PORT>/dashboard.html"` through `run_command`, and print the address in the chat. A failure to open is not an error. There is no side pane.
- **Model tier:** every executor → `Model: "inherit"` (in the live trial a `flash` executor reported DONE without writing files; `обычная` therefore does not mean a cheaper model here). Read-only roles (spec reviewer, blind checker, whole-branch reviewer) may use `Model: "flash"`.
- **Bootstrap:** `<skillDir>` is the directory that contains the `SKILL.md` you were given. If you were not given its path, look — in this order, stop at the first hit — for `skills/autopilot/SKILL.md` under `.agents/skills/autopilot`, `~/.agents/skills/autopilot`, `~/.gemini/config/skills/autopilot`; do not search the whole disk. Run `python "<skillDir>/tools/ap.py" setup` (it prints `skillDir`), then `python .autopilot/ap.py init … --runtime antigravity --skill-dir "<skillDir>"`. If `python` is not a working interpreter use `py -3`.
- **Shell:** the shell is PowerShell. `&&` chains work in PowerShell 7 (`pwsh`); in Windows PowerShell 5.1 write `a; if ($?) { b }`. Read exit codes from `$LASTEXITCODE`.
- **Memory file:** unchanged — Antigravity reads `AGENTS.md` natively.

## codex

Not implemented. Say so in one line and stop; do not guess a mapping.

- **Dispatch:** not implemented.
- **Ask:** not implemented.
- **Dashboard:** not implemented.
- **Model tier:** not implemented.
