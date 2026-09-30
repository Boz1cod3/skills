# Phase 9 — Project memory

The file the **next** session reads first. Chosen in Phase 0 (`phases/0-memory.md`), topped up during the build, finished in Phase 8. This file is read inside Phase 5 for Moment 2 and in Phase 8 for Moments 3 and 4.

| File | Answers | Lifetime |
|---|---|---|
| `.autopilot/<dir>/` | what was promised and delivered **in this run** | history |
| `interfaces.md` | what earlier tickets built, for the tickets still to come | dies with the run |
| the memory file | what an agent needs to work here **tomorrow** | present tense |
| `docs/adr/` | **why** it is this way, and what was rejected | past tense on purpose |

Everything in the memory file must be true of the repository as it stands — not of the plan.

## Whose file it is

`memoryOwner` in `state.js` decides everything below.

- **`autopilot`** — its content lives between `<!-- autopilot:start -->` and `<!-- autopilot:end -->`, and updating means replacing what is between them. Text outside the markers is the user's and is never touched. Markers missing but Autopilot's sections recognisably there → wrap them, do not append a second copy.
- **`user`** — nothing is written into the file during the run. Moments 2 and 3 produce `.autopilot/<dir>/memory-proposal.md` instead, and the file changes only on the user's word.

## Moment 2 — during the build

Only facts that cost something to discover, one line each: the real check command and how to run one test file; a trap that ate time — an ordering dependency, a version pin, a platform quirk; a new variable in `.env.example`; a decision the next ticket must not re-litigate. Most tickets add nothing, and that is the correct rate.

Never: generic advice, restatements of what names already say, commit history, explanations of standard technology, anything `interfaces.md` holds while the run is going.

Autopilot's file → one line appended between the markers. The user's → one line appended to `memory-proposal.md`.

## Moment 3 — the description (Phase 8)

**A subagent on the cheaper model, launched with the blind acceptance** — they read the same finished repo and never see each other. It receives the repository, the current memory file, `interfaces.md`, the tier, and the commands already verified: the full suite you ran, and the commands the blind checker returns. **Not `spec.md`, not the tickets** — a memory written from the plan documents intentions, and the next session trusts it.

**The memory file carries pointers and traps, not a retelling.** Every line is read by every future session; a directory tree, a paraphrase of `package.json` or a description of what a module «does» is a cache of what the repo already says, and it goes stale first.

| Section | What |
|---|---|
| Заголовок | one line: what this is, for whom |
| Команды | install, run, check (tests + types + lint), one test file — every one verified |
| Где что | 3–8 pointers to entry points and the places most edits land — not a tree |
| Подводные камни | what is not obvious and has already bitten someone |
| Окружение | variable names and what each is for — **never values** |
| Как здесь работает Autopilot | from the skeleton, unchanged |

**At tier T2+ the architecture goes to `docs/architecture.md`** — data flow, module boundaries, the conventions this project settled, folded from `interfaces.md` minus its per-ticket framing — with one pointer line to it from the memory file. The memory file stays short; the reasoning for decisions is Moment 4's.

Its brief:

> Опиши проект так, чтобы агент, впервые открывший этот репозиторий, начал
> работать без разведки. Источник — только код, который ты видишь; не открывай
> `.autopilot/`. Не вызывай скиллы и слэш-команды и не запускай своих агентов.
>
> Пиши указателями, одна строка на мысль: где что лежит, как запустить, где
> больно. Не пересказывай очевидное из имён и не описывай известные технологии.
> Каждая команда должна запускаться копипастом, каждый путь — существовать.
> Чего в коде нет — того раздела нет.

Before the block is written:

1. **Commands are verified** — install, run, check. Take what you were handed as already run and name the command that ran; verify only what nobody covered. A command that fails does not go in.
2. **Every path exists.**
3. **No secret values** — the redaction gate from `phases/1-manifest.md` applies here as everywhere.
4. **Length fits the tier.** A landing page with a two-page memory file has been padded.

### When the file is the user's

The same agent writes `memory-proposal.md` instead of the block: what is missing — new commands, variables, traps, pointers — and what in their text is now false, each as a ready-to-paste line. Nothing else.

The report asks once, at the end: «Предлагаю дополнить твой `CLAUDE.md`: 4 пункта — команды запуска и две переменные `.env`. Применить?» — in semi, interview and manual. **In full nothing is asked**: the proposal stays a file, and the report names it. On a yes, the additions go into a marked Autopilot block at the end of their file; a line of their own text changes only as they approved it.

## Moment 4 — the ADRs (Phase 8, tier T2+)

The memory file answers «как этим пользоваться»; ADRs answer «почему так» — what was chosen, what was rejected and why. `spec.md` holds that reasoning now and is worthless the day the work ships, so what deserves to survive is routed into `docs/adr/`.

Three sources, nothing else: **every `D##` row** (the plan proved wrong — the most valuable kind); **load-bearing implementation decisions** (data model, module boundaries, an external service — anything whose reversal means rebuilding); **a term the project uses its own way**, one ADR for the vocabulary. Not: a decision with no alternative, anything a linter or framework decided, the obvious default. Three to six files on T2, five to twelve on T3.

**A subagent, in parallel with the other two, on the cheaper model.** It receives `spec.md`, `manifest.md` and `interfaces.md` (the boundaries live there), **not the repository** — it documents decisions, not code.

> По приложенным спецификации и манифесту напиши по одному ADR на каждое решение,
> которое дорого отменять, и на каждую строку `D##`. Не вызывай скиллы
> и не запускай своих агентов.
>
> Формат — `docs/adr/NNNN-<краткое-название>.md`, нумерация с `0001`, по файлу
> на решение. Внутри четыре раздела и больше ничего:
>
> **Контекст** — что было известно на момент решения. Одна-две строки.
> **Решение** — что решили, в настоящем времени: «Заявки хранятся в SQLite».
> **Почему** — и, главное, что рассмотрели и отвергли. Отвергнутый вариант
> без причины бесполезен: пиши, чем именно он не подошёл.
> **Последствия** — с чем теперь придётся жить, включая неприятное.
>
> Для `D##` контекст — то, что план предполагал, а решение — то, что код
> доказал. Не пиши ADR на решение без альтернативы. Не пересказывай
> спецификацию. Не описывай код — ты его не видел.

If `docs/adr/` exists, **continue its numbering and format**; never renumber what is there. ADRs go into the final commit with the memory file and get one line in the report.

## On resume

The memory file is read **first**, before `state.js` — the cheapest re-entry into a project. Missing or plainly stale against the code (and Autopilot's) → fix it as part of this run. `docs/adr/` is not read on resume; open one only when a decision is about to be reversed.
