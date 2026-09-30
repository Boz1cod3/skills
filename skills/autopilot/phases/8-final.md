# Phase 8 — Acceptance

`ap.py stage final`. Three subagents go out **in one message**, with no contact between them, each answering a different question:

| Agent | Question | Receives | Never receives |
|---|---|---|---|
| blind checker | что из брифа сделано | the brief, the repository | `spec.md`, `manifest.md`, tickets |
| memory | как этим пользоваться завтра | the repo, the memory file, `interfaces.md`, the tier, the verified commands | `spec.md`, tickets |
| ADR *(T2+)* | почему сделано именно так | `spec.md`, `manifest.md`, `interfaces.md` | the repo |

## 1. Blind acceptance — gate G4

Every check so far measured the build against the spec — your own paraphrase of the brief. If a requirement was lost on the way into it, everything downstream faithfully confirmed that loss. **So this check does not get the spec.**

It receives the brief file (`dir` and `briefFile` in `state.js`), **the whole file with `## Дополнения`**, and the repository. `.autopilot/` is committed and sits right there, so **not sending the spec is not enough — the prohibition goes in the prompt**:

> Прочитай приложенный бриф — это задача, которую поставил заказчик. Раздел
> «Дополнения» — сказанное по ходу работы, часть задачи наравне с основным
> текстом; при расхождении верно более позднее. Не открывай `.autopilot/` —
> ни спецификацию, ни манифест, ни таски. Не вызывай скиллы и не запускай
> своих агентов.
>
> **Склонируй репозиторий во временную папку** (`git clone <репозиторий> <tmp>`)
> и работай там: поставь зависимости с нуля по тому, что лежит в репозитории.
> Если для запуска нужен `.env`, скопируй его в клон, не открывая. Всё, что
> в клоне не поднимается, а в рабочей папке поднималось бы, — это находка:
> незаписанная зависимость, незакоммиченный файл, шаг, который знает только эта машина.
>
> **Запусти проект** и пройди основной сценарий так, как прошёл бы заказчик.
> Чтение кода показывает намерение, запуск — результат. Не поднимается или
> сценарий обрывается — это главная находка, первым пунктом. Запустить нельзя
> вообще (нужен аккаунт, ключ, внешний сервис) — скажи прямо, что помешало,
> и не выдавай чтение кода за проверку.
>
> По каждому требованию из брифа: реализовано / частично / нет — и одна строка,
> где это видно. Требование выполнено формально, а по сути не работает (данные
> сохраняются, но пользователю не показываются) — это «частично».
>
> Отдельно верни **команды, которыми ты поднимал проект, и их результат** — дословно:
> их ждёт агент, который пишет память проекта.
>
> Не оценивай качество кода, не предлагай улучшений, не ищи оправданий — только факт.

**Then compare its verdict with the manifest:**

| Manifest | Blind | Meaning |
|---|---|---|
| `done` | реализовано | agreed |
| `done` | **частично / нет** | 🔴 **drift** — the manifest is wrong. A ticket, or a line in the report; never an edit of your own |
| `placeholder` | частично | expected — confirm the stub is visible, not an invented fact |
| `dropped` / `deferred` | нет | expected — in the report as not built |
| — | реализовано, но не из брифа | scope that grew without a parent — reported |

`ap.py blind checked=N matched=M --mismatch "…"` for every 🔴. A drift found here is the run working; hiding it is the failure. **A build nobody has launched is a build nobody has seen work** — if it cannot be run here at all, that goes to «Что нужно от тебя», not into the accepted column.

## 2. Memory and ADRs

**Read `phases/9-memory.md` before spawning them** — Moments 3 and 4 there are their whole brief. When the memory file is the user's own, the memory agent writes `memory-proposal.md` instead of touching it.

## 3. The final report

Run the check once more first, truncated. Then write, in the user's language, plain, no jargon.

**Build it from the files, re-read now, not from memory.** By this phase your context is the most polluted of the run, and memory gets the report wrong in one direction: a `deferred` requirement reported as done, a placeholder vanishing, an `A##` nobody ordered turning up as though they had asked.

| Section | Read from |
|---|---|
| Решения, принятые за тебя *(full: first in the report)* | `manifest.md` — every `ASSUMPTION` |
| Готово | **the blind checker's verdict**, not the manifest's `done` rows |
| Что нужно от тебя | `placeholder` rows + `state.js` → `debt` |
| Что не вошло | `deferred` and `dropped` rows, with their quotes |
| Что я добавил сверх заказанного | `state.js` → `additions`, checked against the spec's `A##` |
| Что пошло не по плану | every `D##` row, every failed ticket |
| Что осталось после ревью | the whole-branch review's «report» findings |
| Открытые вопросы | `state.js` → `blind`, and what `coverage` found that was not built |
| Память проекта *(only when the file is the user's)* | `memory-proposal.md` — one question: «Предлагаю дополнить твой `CLAUDE.md`: N пунктов — применить?»; in full, only a line naming the file |
| Запустить / Где что лежит | `memoryFile`, `briefFile`, the commands the memory agent verified |

```markdown
## Готово

<Что теперь работает — 3–6 строк обычным языком, от лица пользователя.>

**Запустить:**
    npm install && npm run dev
Открыть http://localhost:3000

## Что нужно от тебя

1. Впиши в `.env` — `TELEGRAM_BOT_TOKEN`, `GOOGLE_SHEETS_ID`. Образец — `.env.example` рядом.
2. Замени заглушки: цены и тексты писем. Сейчас там видимые метки `[ВПИШИ]`, не выдуманные значения.

## Что не вошло

| Что | Почему |
|---|---|
| Уведомления на SMS | ты сказал «SMS не надо, только телега» |

## Что я добавил сверх заказанного

| Что добавил | Ради чего |
|---|---|
| Номер заявки в подтверждении | чтобы клиент мог на неё сослаться |

## Что пошло не по плану

| Что не сработало | Как сделано |
|---|---|
| Одна заявка на один адрес — у половины клиентов их два | Адреса вынесены в список |

## Открытые вопросы

<Расхождения слепой приёмки — прямо, без смягчения: «Требование "клиент видит статус"
я считал готовым, независимая проверка показала, что статус нигде не отображается».>

## Где что лежит

- Описание проекта для следующего раза — `AGENTS.md` в корне
- Почему сделано именно так — `docs/adr/` (если проект крупный)
- Прогресс и цифры — `.autopilot/dashboard.html`
- Твоя задача, требования, спецификация — `.autopilot/<папка сборки>/`
```

- **Заглушки и пустые переменные — обязательный раздел**, даже пустой: «всё заполнено».
- **«Что не вошло» пишется всегда**, даже когда вошло всё — одной строкой.
- **Секреты — только именами.**
- **Не приукрашивать.** Упавшее, недоделанное, найденное расхождение — прямо, с тем, что нужно для починки.
- Без диффов, имён файлов кода и названий тестов. A section with nothing in it, except the two above, is omitted.

## 4. Landing

In this order, so the report names paths that exist:

1. The memory file (or its proposal) and the ADRs are written.
2. `python3 .autopilot/ap.py finish --result "<одна строка: что теперь есть>"` — closes every stage, sets `finishedAt`, renames `<dir>--wip` to `<dir>` with `git mv`, closes the run's row in `.autopilot/README.md`, and puts the server out twelve seconds later, after the page has fetched the final picture. A `!` line about the rename means the name was taken or the index dirty: leave it, the run is not undone by a cosmetic suffix.
3. **The final commit** — everything, `.autopilot/` included.
4. The report.

The dashboard freezes on the final numbers and carries them inside the page, so it reopens by double-click long after the server is gone. Say nothing about any of this.
