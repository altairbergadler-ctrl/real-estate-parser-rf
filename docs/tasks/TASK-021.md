# TASK-021 — design deterministic duplicate candidate generation

- Статус: завершено в task-ветке, готово к review
- Рабочая ветка: `task/021-duplicate-candidate-design`
- Целевая ветка: `main`
- Стартовый SHA: `17f0edf1a89aaffc687f24b3023a7617fcaa7b53`

## Цель

Принять design-only контракт детерминированного формирования ограниченного
набора duplicate candidate pairs из явно переданных current
`AvailableObservation`. Контракт должен использовать явные exact blocking
keys, исключать скрытый quadratic all-pairs scan, целиком показывать
oversized buckets и позволять точно измерить blocking missed-pair risk на
полностью вымышленном reviewed control set.

## Включённый объём

- ADR 0008 с вариантами all-pairs, одного exact key, multi-pass union, silent
  truncation и explicit oversized outcome.
- Одна согласованная design-спецификация immutable pseudotypes, input/policy
  invariants, blocking keys, ordering, complexity bound, replay/conflicts,
  coverage metric и fully fictional scenarios.
- Отдельная `publication-duplicate-candidate-policy@1` с двумя exact passes:
  `total_area + rooms` и `total_area + location_text`.
- Непустой canonical current available input, at most one observation per
  `PublicationRef`, exact `ObservationKey` и atomic failures.
- Same-source/cross-source pair semantics, canonical candidate identity и
  ordered union всех materialized blocking matches.
- Explicit caller-supplied positive bucket pair limit, exact
  `n * (n - 1) / 2` и whole-bucket oversized outcome без partial first-N.
- Stable result collections, empty-candidate success, deterministic replay и
  future consumer conflict coordinates без repository API.
- Exact blocking coverage для eligible confirmed fictional control cases с
  отдельными ineligible/unrepresented counts и typed unavailable reasons.
- Согласование только проектной Markdown-документации и ровно одна следующая
  рекомендуемая задача — TASK-022.

## Исключённый объём

- Любой production Python code, types/functions/exports, Python tests,
  fixtures/golden, `pyproject.toml`, `uv.lock` или dependencies.
- Фактическая generation pairs, all-pairs enumeration, benchmark и выбор
  universal bucket limit.
- Assessment, evidence, manual review, изменение ADR 0006,
  `publication-duplicate-policy@1`, ADR 0007 или quality metrics TASK-020.
- Physical property, canonical winner, merge/collapse/hide, cluster,
  connected components и transitive closure.
- Fuzzy/tolerance/geocoding/coordinates/photo/AI/embedding/LLM и персональные
  признаки.
- Storage, repository/index/database/ORM/migrations, Pydantic/JSON/filesystem,
  CLI/API/UI.
- Real data, реальные sources, HTTP, OpenClaw, Telegram, notifications,
  publication/push, merge в `main` и удаление ветки/worktree.
- Реализация или начало TASK-022.

## Критерии готовности

- [x] ADR 0008 сравнивает все назначенные варианты и принимает multi-pass union
  без all-pairs fallback и silent truncation.
- [x] Input непустой, immutable/canonical, current available и one-reference;
  unavailable, duplicate reference и same-key content conflict дают exact
  contract failures.
- [x] Candidate policy v1 отдельно версионирована и содержит только два exact
  rules candidate gate ADR 0006.
- [x] Missing/Unsupported создают явные per-rule non-participation reasons, а
  поля вне policy не становятся blocking keys.
- [x] Typed blocking keys не используют float/hash/locale identity; candidate
  связывает canonical pair и exact left/right observation keys.
- [x] Caller limit положителен, prospective pair count exact, oversized bucket
  не materializes ни одной своей пары и не допускает first-N.
- [x] Result хранит policy/configuration, canonical input keys, unique
  candidates, complete ordered matches, non-participations и oversized buckets
  в stable order; empty candidates — success.
- [x] Спецификация доказывает `E <= 2NL` pair attempts и отсутствие global
  quadratic fallback при максимум двух memberships на observation.
- [x] Replay/conflict semantics имеют exact codes и subjects без выбора
  repository API.
- [x] Blocking coverage использует только eligible confirmed exact-key cases,
  считает no-shared/oversized misses внутри denominator, отдельно показывает
  PairNotAssessed/outside/stale и возвращает typed unavailable при
  inconclusive labels или нулевом eligible denominator.
- [x] Metric использует exact integer ratio и явно ограничена supplied fully
  fictional population без production recall/representativeness/legal claim.
- [x] Fully fictional matrix покрывает passes, non-participation, same/cross
  source, replay, conflicts, bucket boundary, oversized alternate route и
  coverage/unavailable cases.
- [x] PROJECT/ARCHITECTURE/ROADMAP/CHECKPOINT/task registry согласованы и
  называют только TASK-022 следующим шагом.
- [x] Все назначенные проверки успешны, changed paths содержат только
  назначенные Markdown-документы, создан один commit и worktree чист.

## Фактически выполненная работа

- Создан [ADR 0008](../decisions/0008-duplicate-candidate-generation.md):
  отклонены quadratic all-pairs, single-key policy и silent truncation;
  принят bounded two-pass union с explicit oversized outcome.
- Создана
  [design-спецификация](../design/PUBLICATION-DUPLICATE-CANDIDATES.md) с
  точными pseudotypes и invariants current input, отдельной candidate policy,
  typed keys, non-participation, candidate/result identities и stable order.
- Зафиксированы exact prospective count, whole-bucket skip, pair recovery через
  другой допустимый key и upper bound `2NL` materialization attempts.
- Описаны atomic generation/future replay conflicts с stable codes и subject
  coordinates без storage/repository design.
- Добавлена denominator-explicit blocking coverage поверх fully fictional
  reviewed control set TASK-020: exact ratio, два вида eligible miss, отдельные
  PairNotAssessed/outside/stale counts и typed unavailable reasons.
- Согласованы `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и
  `docs/tasks/README.md`. Исполняемый код и существующие ADR/policies не
  изменялись.

## Проверки

- `uv sync --frozen` — успешно; CPython 3.14.7, установлены 18 зафиксированных
  packages, lock не изменён.
- `uv lock --check` — успешно; разрешены 18 packages, lock соответствует
  project metadata.
- `uv run quality` — успешно: Ruff format-check (`80 files`), Ruff lint,
  strict mypy (`35 source files`), основной pytest (`503 passed`) и fixture
  catalog integrity (`44 passed`).
- Все относительные Markdown links во всех 8 изменённых документах — успешно:
  проверено 46 локальных ссылок, broken links отсутствуют.
- Согласованность с ADR 0006/0007 проверена: candidate gate совпадает, candidate
  match не назван evidence/outcome, quality contracts TASK-020 не изменены.
- `git diff --check` — успешно.
- Changed paths проверены: только назначенные Markdown-документы;
  `pyproject.toml`, `uv.lock`, `src/`, `tests/`, `tests/fixtures` и
  `fixtures/golden` не изменены.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-021 завершена только в `task/021-duplicate-candidate-design`, готова к
отдельному review и намеренно не слита в `main`. Принят только design contract;
pair generation, tests, storage, real data и TASK-022 не начинались.

## Итоговый коммит

Один атомарный documentation commit находится в истории по сообщению
`docs: define bounded duplicate candidate generation`. Точный SHA
подтверждается Git после создания commit и не дублируется внутри его
собственного снимка.

## Следующая рекомендуемая задача

TASK-022 — реализовать neutral frozen/slots blocking/candidate types и pure deterministic generation по ADR 0008 для explicit available observations с oversized-bucket outcomes, без storage, JSON, CLI, real data или pair assessment
