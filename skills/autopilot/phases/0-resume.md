# Resuming an interrupted flight

Read only when `.autopilot/state.js` exists with `finishedAt: null`. The files are the memory — do not re-read the dialogue, do not redo finished phases, do not re-ask answered questions.

1. **Read, in this order:** the memory file (`memoryFile` in `state.js`), `state.js` itself (`dir`, `skillDir`, `mode`, `depth`, `tier`, the tickets), `manifest.md`, `interfaces.md`, and the newest `*-brief.md` in `dir`, `## Дополнения` included.
2. **Raise the instruments again.** Run §1 of `phases/0-instruments.md` (the copy — a run from an older version gets the current `ap.py` and page), then `python3 .autopilot/ap.py`, which re-raises the server on its old port. **Always re-point the pane** (§3 there) and say the address: a tab does not outlive the session that opened it.
3. **Tell the user in one line where things stand:** «Продолжаю: 7 из 12 тасков готовы, следующий — корзина».
4. **Tickets caught mid-flight** — `in-progress`, `review` or `repair` with no commit behind them: `ap.py ticket <id> reset`, and relaunch them as ordinary tickets. Tell the new executor that its zone may hold uncommitted edits from an interrupted attempt — to finish from them or discard them, its call. A half-applied ticket is never committed as it stands.
5. **Run the project's check once** before the next launch. Red → name the failure in the next executor's prompt, so it does not read someone else's breakage as its own.
6. **Continue from the frontier** — the current phase, or the next launchable tickets.
