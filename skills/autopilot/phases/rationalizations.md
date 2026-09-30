# Rationalizations and red flags

**Read at three moments, and not otherwise:** when a gate fails, when you catch yourself building an argument for skipping something, and once before the final report. A checklist, not an instruction — the five rules that never lose are in `SKILL.md`; this is the long tail.

## Excuses that end with the user getting something else

| Excuse | Reality |
|---|---|
| «Пользователь сказал не задавать вопросов» | Он сказал не задавать лишних. Решающие вопросы — часть работы. |
| «Бриф весь в диалоге, зачем файл» | Диалог сжимается, и бриф в нём — самое старое. Через три фазы ты синтезируешь по пересказу пересказа. |
| «Он про это больше не вспоминал — значит, отменил» | Молчание не отменяет. Предложить `deferred` можешь ты; вычеркнуть — только он, цитатой. |
| «Он передумал — поправлю манифест, бриф трогать нельзя» | Переписывать сказанное нельзя, дописывать сказанное позже — обязательно: `## Дополнения`. Обе независимые проверки манифест не видят. |
| «Новое пожелание посреди сборки — оформлю как `D##`» | `D##` — то, что доказала сборка. Слова пользователя — всегда `G##`, плюс строка в «Дополнения» и вслух: беру таском, откладываю или в отчёт. |
| «Сделаю заглушку, уточнит потом» | Оплата, хостинг, аккаунты решаются в брифинге, в первом раунде, до сборки. |
| «Исполнитель не смог — доделаю сам» / «тут две строки» | Твой контекст тратится один раз и не возвращается. Дозапрос ему или свежий контекст — не твоя клавиатура. |
| «Бриф краткий — значит, и спецификация краткая» | Бриф — силуэт. Пустые состояния, ошибки и обрывы на обычной и глубокой проработке продумываешь ты. |
| «Придумал полезную фичу, добавлю» | Углубление заказанного — да. Новая возможность — только с родителем, в пропорции и в отчёт; на `strict` — нельзя. |
| «Полный автомат — значит, можно и задеплоить» | Автомат снимает вопросы о продукте, а не право на необратимое. |
| «В полном автомате можно додумать за пользователя всё» | Решения — да, все в ASSUMPTIONS. Факты о нём — нет: заглушка и строка в отчёте. |
| «Покрытие проверю сам — я же спецификацию и писал» | Тот, кто писал, не видит, чего не написал. На G2 и G4 читает субагент, по брифу, без спеки и манифеста. |
| «Правило про тесты записано в фазе — значит, действует» | Действует только то, что доехало в промпт исполнителя. |
| «Интерфейсы устаканятся по ходу — первый таск задаст» | Тогда их задаст тот, кто видел одну восьмую задачи. |
| «Отчёт напишу по памяти» | К финалу твой контекст самый загрязнённый. Отчёт собирается из файлов, перечитанных с диска. |
| «Блокирующего нет, но раз уж нашлось — пусть поправит» | Блокирует то, что ревьюер записал в `BLOCKING`. Остальное ждёт ревью ветки; расширить — строка пользователю с ценой. |
| «Таск простой — ревью ему не нужно, хотя он помечен» | Пометку `Ревью: да` ставит план, а не настроение: фундамент и риск ревьюятся всегда. |
| «Проект собран, тесты зелёные — значит, работает» | Тесты писал тот же процесс, что и код. Пока проект никто не запустил, «работает» — гипотеза. |
| «Пользователь не спрашивал про режимы — не буду грузить» | В чате нет `--help`. Стартовый блок — единственное место, где он узнаёт, что у сборки есть ручки. |

## Red flags — start the phase over

- Code written before the spec exists, or the brief never written to its file.
- A requirement without a status, or `dropped` without the user's quote.
- `ap.py check-plan` left with `!` lines — a ticket tracing to nothing, a requirement in no ticket.
- Spec or tickets that exist only in the dialogue.
- The dashboard disagreeing with the chat — a stage still active after you moved on, a ticket running while the screen says it has not started, `state.js` edited by hand.
- The announced depth and the spec diverge: a bare restatement of the brief at normal or deep, any `A##` at strict.
- G2 or G4 judged by you, or a blind checker / coverage checker / memory agent handed the spec, the manifest or the tickets — or left free to open `.autopilot/`.
- The report composed from memory instead of from the files and the checkers' returns.
- A T2+ run that ended with no ADR.
- The finished project never actually run.
- Starting without announcing mode and depth, or announcing one and behaving as another.
- A comparable in `reference.md` the user never named.
- The adversarial pass skipped in interview, or used to argue the user out of a requirement.
- A blocking unknown — payment, hosting, an account, where the data lives — left unasked because the brief «looked clear»; or a question manufactured to fill a round.
- A promised wait — «через минуту», «если не ответишь за N секунд» — you cannot honour.
- An invented fact about the user where a stub belongs.
- A process question outside manual — which tracker, which memory file, ticket granularity.
- A requirement quietly narrowed to whatever worked, or the spec amended with no `D##`.
- Two tickets in one context or one commit; a commit that took files outside the ticket's zone.
- The orchestrator editing a file outside `.autopilot/` and the memory file.
- A diff or a raw test log read into the orchestrator's context.
- A дозапрос carrying more than the reviewer's `BLOCKING` lines.
- A reviewer kept alive across tickets, or a ticket marked `Ревью: да` committed without its review.
- Parallel executors on the same files — or independent tickets flown one at a time.
- A subagent launched without `interfaces.md` or `prompts/executor.md`, or finishing without the contract block.
- A secret asked for, repeated back, or written anywhere.
- A package installed or remote code fetched without the user asking.
- Text outside the `autopilot` markers edited, or the user's own memory file written into without their yes.
