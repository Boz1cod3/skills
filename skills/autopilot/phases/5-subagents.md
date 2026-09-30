# Phase 5 — Build

Where the code gets written. **Identical in all four modes, and hands-free**: manual buys control over *what* gets built, not over each edit.

## One ticket, one subagent, one fresh context

Never two tickets in one context — accumulated context is what makes long sessions start breaking what used to work. At T0 the one ticket goes to one executor like any other.

**You dispatch; you do not build.** Your keyboard reaches `.autopilot/**`, the memory file between its markers, and git (`add`, `commit`, `--stat` — never the diff). Every other file is written by someone whose context dies with the ticket. This is rule 5, and it loses to the two arguments that always arrive — «тут две строки» and «исполнитель не смог, доделаю сам»: a diff you read at ticket 02 is still in your context at ticket 08, and your context is the one that is never refreshed.

## What an executor gets — paths, not contents

| | |
|---|---|
| `prompts/executor.md` | by path (`skillDir` in `state.js`), **required reading before the first edit** — the testing contract and the return format |
| its ticket | by path; it already carries the verbatim brief quotes |
| the spec sections the ticket names | `spec.md` by path **and section headings** — not the whole spec, not pasted |
| `interfaces.md` | by path, read first |
| `notes.md` | by path, in a brownfield repo |
| `reference.md` | by path, when the ticket builds something the user will look at |
| the check command and how to run one test file | from `interfaces.md` — so it does not derive them |
| its zone, and what it must not touch | zones of tickets flying beside it included |
| credentials | variable **names**, never a value |

A subagent has a filesystem; pasting what it can read writes the same words twice into the bill, and the second copy stays in your context for the rest of the run. Every rule the executor must follow travels in its prompt or in `prompts/executor.md` — a rule that lives only in a phase file does not exist for the one writing the code.

**The model.** A ticket marked `Модель: сильная` runs on the session's model. `обычная` runs on a cheaper one — in Claude Code, `model: "sonnet"` on the Agent call; a harness without a model choice ignores this silently. A ticket that already failed once is relaunched on the strong model.

## Waves

Phase 4 gave every ticket a wave and a zone. **Launch a whole wave in one message, one subagent call per ticket, in the background** — two calls in two messages run one after the other, and the parallelism computed in the plan is thrown away in the delivery.

- **At most three in flight.** A wave of five goes out as three, then two.
- **Zones disjoint** — checked again at launch; same files → serialise.
- **A wave is not a barrier.** When a ticket returns, first launch the next ticket whose dependencies are all committed, then process the one that landed.
- **A dependent never launches on an uncommitted parent.**
- `ap.py ticket 02 03 start` goes **before** the launch — one call for the whole wave.

**One working tree, several writers.** Parallel executors share the checkout, so each touches only its zone, and you commit by zone: `git add -- <zone>`. A red check whose failing tests sit in a neighbour's zone is the neighbour's unfinished work, not this ticket's defect — let the neighbour land and run the check again before blaming anyone.

## The return contract

Required in the prompt, not suggested — without it you cannot update anything:

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
FILES: созданные и изменённые — только пути
TESTS: команда проверки → результат и сколько было до тебя (`npm run check` → 34 passed, было 21)
REDPROOF: новый тест → чем он падал до кода (одна строка на тест, до пяти)
INTERFACES: публичные сигнатуры, схемы, форматы событий, которые ты выставил
REQUIREMENTS: R01 done | R01.1 placeholder — <чего не хватило>
CONCERNS: что сделано с оговоркой и почему
BLOCKERS: чего не хватило (зависимость, решение, доступ)
```

**No more than 25 lines, no code, no diffs, no account of the work.** A block longer than that is not read: ask for it again in one line — an essay skimmed once is re-read on every remaining turn of your context.

## After each ticket

In this order:

1. **Read the contract.** No block → the ticket is not finished; ask for it.
2. **Append its `INTERFACES` to `interfaces.md`** — you, never the executors; parallel writers collide. Two returns claiming one interface is a plan defect: keep the one that fits and re-cut the other.
3. **Point review, if the ticket says `Ревью: да`** — `ap.py ticket NN review`, then `phases/6-review.md`. Otherwise straight to 4. A contract whose `REQUIREMENTS` line reports a row of this ticket as not done, or a `CONCERNS` line about a requirement rather than about craft, sends the ticket to point review too.
4. **Run the check**, full, truncated: `<check> 2>&1 | tail -30`. You need green-or-red, the names of what failed, and **the count** — compare it with the contract: a `DONE` that added criteria and no tests is a дозапрос, and a suite reporting zero tests is red however it exits.
5. **A red check or a `BLOCKING` finding → `phases/5-repair.md`**, opened now and not before. `BLOCKED` and `NEEDS_CONTEXT` go there too. `DONE_WITH_CONCERNS` → each concern into `ap.py add concerns`.
6. **Commit and record in one call** — one commit per ticket, its number in the subject, only its zone: the chained command in `phases/0-instruments.md` §4. Only now is the ticket `done`; these commits are the user's rollback points.
7. **Project memory — only if something was discovered** (`phases/9-memory.md`, Moment 2). Most tickets add nothing.
8. **One plain line to the user**: «Бот принимает заявки — 3 из 8 готово».

Nothing is committed on red, and nothing is repaired by you. **Two tickets returning together are processed one at a time**, each through the whole list: one commit each, a check after each — otherwise a red has two possible authors.

## When the last ticket lands

`ap.py stage review` and `phases/6-review.md` — the whole-branch review, before the final phase.
