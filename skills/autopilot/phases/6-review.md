# Phase 6 — Review

Two moments, both done by someone who did not write the code:

- **Point review during the build** — only for tickets whose file says `Ревью: да` (the foundation and the risky ones, `phases/4-plan.md`), before their commit.
- **The whole-branch review** — once, after the last ticket, as the `review` stage.

Every other ticket is committed on a green check and is reviewed as part of the branch. This is deliberate: measured across real runs, per-ticket review by two long-lived reviewers cost 13–47 % of a run's tokens, and the defects worth stopping a ticket for sat in the foundation and in the risky tickets. A whole-branch pass also sees what no per-ticket reviewer can: ticket 05 quietly contradicting ticket 02.

## Three axes, reported separately

| Axis | Question | Fails when |
|---|---|---|
| **Manifest** | does it deliver what the user asked for, in their words? | a requirement quietly shrank |
| **Spec** | does it implement what the spec decided? | the executor improvised |
| **Craft** | is the code fit to build on? | it works today and blocks tomorrow |

Merged or ranked together, one axis masks another: clean code implementing the wrong thing looks fine. **Which axis a finding belongs to: could the executor have known?** It saw its ticket, the spec sections named, `interfaces.md`. Yes → Spec or Craft, fixed in this ticket. No → Manifest, and the defect is in the spec or the cut — repair those first, never re-run the executor against words it was never given.

## Point review

**One fresh subagent per reviewed ticket**, on the strong model — never a reviewer kept alive across tickets: a long-lived reviewer's context grows to hundreds of thousands of tokens and is rewritten at full price every time it wakes.

It gets, by path: **`prompts/review.md`** (`skillDir`), required reading before the diff; the ticket file — its brief quotes are the Manifest axis; the spec sections the ticket names; `interfaces.md`; whatever the repo documents about how code is written; and the command that shows the uncommitted work of its zone — `git add -N -- <zone> && git diff -- <zone>`, where `-N` makes new files visible. **Say why it is reviewed** — «фундамент» or the named risk: that decides what blocks. It must not repair, refactor, invoke skills or spawn agents.

What comes back is a verdict per axis and a `BLOCKING` line. `BLOCKING` → `phases/5-repair.md`, verbatim. `FINDINGS` → `ap.py add concerns`, one call per finding with its file and line. Neither the diff nor the reasoning reaches you.

## What blocks

**Only the reviewer's `BLOCKING` line holds up a commit**, and what may appear there is short:

- **Manifest `partial` or `missing`** — a requirement the user asked for is not delivered.
- **An invented fact** — a plausible price, address or text where the user's own fact belongs.
- **Spec *extra*** — surface nobody asked for, unless the rest genuinely needs it.
- **A red check.**
- **In the foundation, a defect the following tickets will build on** — a wrong key in the schema, a shared client that fails the next ticket's call, access that ignores the boundary the spec drew.
- **For a risky ticket, a hole in that risk** — the security list in `prompts/review.md`.

Everything else waits for the whole-branch review. **You do not widen the list**: not «блокирующего нет, но раз уж нашлось», not a finding from `FINDINGS` you happen to agree with. That is the cost rule in `SKILL.md` — widening it is a line to the user with its price, never a quiet decision.

## The whole-branch review — the `review` stage

After the last ticket commits: `ap.py stage review`.

**One fresh subagent** on the strong model — at T3 with a large diff, up to three in parallel, each given a group of zones. It gets `prompts/review.md` (whole-branch mode), the range `git diff <baseCommit>..HEAD` (`baseCommit` in `state.js`) to run itself, `spec.md` and `interfaces.md` by path, the repo's conventions, and the deferred findings from `state.js` → `concerns`, so it can confirm or drop them rather than rediscover them. Here it may open files outside the diff where an interaction needs it.

It returns every finding sorted into three: **fix now** — it costs more to leave than to close, and the fix is bounded; **report** — real, not worth holding delivery for; **drop** — taste, or the code it pointed at is gone. Anything repeated across three or more tickets is **fix now** regardless of size: that is a convention the project never settled. Every security finding is fix now or report — never drop.

**All the fix-now findings become one ticket**, `F1`, written like any other ticket (its zone is the union of the files named, its review `да`, its model strong): `ap.py tickets`, one executor, the check, a re-review scoped to the fix, one commit. Not by you, not by the reviewer — a fix that skips the ticket path skips the rollback point and the green check. The «report» findings go to the final report in the user's language.

Then `phases/8-final.md`.

## Reporting

To the user, nothing per ticket. After the whole-branch review, one line: «Код-ревью: нашлось 7 замечаний, 4 поправил, 3 — в отчёте».
