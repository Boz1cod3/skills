# Phase 5 — Repair, failure and amendments

Read only when a ticket comes back as anything other than a clean `DONE` — a `BLOCKING` finding, a red check, `BLOCKED`, `NEEDS_CONTEXT`, or a build that proved the plan wrong. Most tickets never open this file.

Two counters, both capped at two: `repairs` (дозапросы) and `retries` (fresh restarts). Running out of either means the cut was wrong, and that belongs in the report, not in another attempt.

## Repair — two kinds, two addresses

**Not every finding comes here.** Only the reviewer's `BLOCKING` lines and a red check become a дозапрос — and the дозапрос carries those lines **verbatim and nothing else**. `FINDINGS` go to `ap.py add concerns` and wait for the whole-branch review.

| | Недоделка — could have, did not | Отказ — tried, could not |
|---|---|---|
| What | a red check, a blocking finding, a criterion met in letter and dodged in substance | `BLOCKED`, `NEEDS_CONTEXT`, a repair that already failed |
| Goes to | **the same executor**, by message, its context intact — a **дозапрос** | **a fresh context**, on the strong model (below) |
| You send | the condition, nothing else | the ticket again, the error, the failing test named, the path now spelled out |
| Because | it holds why the code is the way it is; a cold reader repairs the symptom and breaks the reason | its context *is* the failure — the same request gets the same answer |

`ap.py ticket NN repair --note "условие одной строкой"` before the message goes out — and for a reviewed ticket `git add -A -- <zone>` too, so the re-review sees only the fix. A дозапрос is short:

```
Тест `parses empty address` красный:
<последние 10 строк вывода>

Назови причину одной строкой, потом чини — так, чтобы тест проходил.
Больше ничего не трогай. Верни контракт заново.
```

- **The cause first, then the fix.** No cause found → `BLOCKED`, not a workaround. **A weakened or deleted assertion is not a repair.**
- **A condition, never «поправь»** — this test green, this field visible, this error handled.
- **The repair returns the contract again** — new `FILES`, new `TESTS`.
- **A reviewed ticket's repair is re-reviewed, scoped to the fix** — mode «ремонт» in `prompts/review.md`: a fresh reviewer gets `git diff -- <zone>` and the conditions, verdicts each closed or not, and flags new breakage inside the fix only. Never the whole ticket again. A repair of an unreviewed ticket (a red check) needs only the check green again.
- **Two re-reviews per ticket, then it lands.** What the second re-review still finds open goes to the report with its reproduction (`ap.py add report`), unless it is a red check or a requirement not delivered — those stay blocking. A sanitizer a reviewer can always find one more bypass for is the typical case.
- **Two дозапроса into one context, then the right-hand column.**
- If the harness cannot continue a subagent, the fallback is a fresh context with the full ticket prompt plus the finding — never your own keyboard.

## BLOCKED for a missing dependency

Not a failure. If the dependency fits a decision the spec already made, add it to «Решения по реализации» and relaunch the ticket with permission to install exactly that (`phases/5-subagents.md`). If it would be a new decision — a paid service, a heavy framework, a different stack — it is the user's question in semi, interview and manual, an `ASSUMPTION` in full.

## When a ticket fails

`ap.py ticket NN retry`, then a fresh context with the error attached, on the strong model. A second retry only **with a changed approach** — a different design decision, a different library, a path the ticket now names explicitly; the same attempt with more hope is the one forbidden move.

After that the flight stops for this ticket: `ap.py ticket NN fail --note "что блокирует"`, the reason in its manifest rows' Основание, and a plain sentence to the user — what is blocking, what you need from them, and which tickets are now waiting on it. Never improvise around a blocker and never narrow the ticket to whatever happened to work: a quietly reduced ticket is a lost requirement. Its wave-mates are independent by construction — let them land.

## When the build contradicts the plan

Sometimes the code is right and the plan is wrong: a data model that does not hold, an interface that cannot exist, two requirements that collide in practice. The executor returns `BLOCKED` or `DONE_WITH_CONCERNS` with what it found. **You decide, never the executor** — and the code that follows is still written below you:

1. **Amend the spec section** in place, keeping the marks, with one line on what the code proved and at which ticket.
2. **Add a `D##` row** to the manifest — the finding as Основание, naming the requirement it serves.
3. **Re-cut only what the change invalidates.** Landed tickets stay; unstarted ones get their references updated; one whose point disappeared is cut and its rows go back to `in-spec`. `ap.py tickets` again.
4. **Tell the user one line, in every mode:** «Схема из плана не держала два адреса на одну заявку — поправил, требование то же».

A `D##` never drops a requirement — one the code proves impossible is a question for the user (in full, an `ASSUMPTION` and a placeholder). And it is never a route for an idea you had while building — that is an `A##`, with a parent, and forbidden at strict.
