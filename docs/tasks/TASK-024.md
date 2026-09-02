# TASK-024 — design pure atomic duplicate-candidate assessment batch

- Статус: завершено и слито в `main`
- Рабочая ветка: `task/024-duplicate-assessment-batch-design`
- Целевая ветка: `main`
- Стартовый SHA: `8d13bbca42ca5ed1fcd34199164a0a7ff6a21a33`

## Цель

Спроектировать отдельную pure deterministic atomic batch composition, которая
принимает готовый `DuplicateCandidateGenerationResult`, полный exact current
context из caller-supplied `AvailableObservation` и явную assessment policy,
проверяет их полное structural binding и передаёт все и только materialized
candidate pairs в существующую `assess_publication_pair`.

## Включённый объём

- ADR 0009 с вариантами, решением, последствиями и условиями пересмотра.
- Детальная design-спецификация input/configuration, batch/item identities,
  success/failure, conflicts, atomicity, replay и complexity.
- Exact binding non-empty tuple current available observations к полному
  generation identity с раздельными missing/extra/current-key mismatch.
- Явная поддержка только full candidate policy v1 и full assessment policy v1
  как разных identities.
- Preflight zero-call semantics, exact one-call-per-candidate semantics и
  deterministic full downstream conflict pass без partial item outcomes.
- Stable typed taxonomy input, policy, binding, downstream и future-consumer
  conflicts.
- Полностью вымышленная scenario matrix, включая empty candidates,
  permutations, crafted mismatch, downstream failures, replay и
  non-transitivity.
- Согласование project/architecture/roadmap/checkpoint/task registry только по
  принятому design-only результату.

## Исключённый объём

- Python implementation, public exports, Python tests, fixtures/golden,
  `pyproject.toml`, `uv.lock` и dependencies.
- Изменение candidate generation, blocking coverage, pair assessment,
  evidence, manual review, ADR 0006/0007/0008 и существующих policies.
- Regeneration, all-pairs scan, hidden fallback, fuzzy/tolerance/AI rules.
- Storage/repository/index/database, concurrency/revision, JSON/Pydantic,
  filesystem, CLI/API/UI, HTTP и real data.
- Physical property, canonical winner, merge/collapse/hide, clustering,
  connected components и transitive closure.
- Push/publication, merge в `main`, удаление ветки/worktree и начало TASK-025.

## Критерии готовности

- [x] Batch identity отдельно связывает exact generation identity и explicit
  assessment policy version, не смешивая candidate и assessment policies.
- [x] Current input tuple-only, non-empty, available-only, canonical и
  one-reference; content/key/reference conflicts имеют exact semantics.
- [x] Full current keys exact связаны с generation keys; missing, extra и
  same-reference/new-key context структурно различаются.
- [x] Full observations используются только как exact assessment sides;
  snapshots/candidate metadata их не заменяют.
- [x] Каждый candidate связан с generation policy, canonical pair и exact
  left/right current keys; blocking matches остаются routing metadata.
- [x] Empty candidate result успешен с пустыми item outcomes и zero calls.
- [x] Каждый valid candidate вызывает существующую pair operation ровно один
  раз в canonical order; same/cross-source допустимы, self-pair невозможна.
- [x] Preflight собирает unique canonical conflicts до первого call и при
  failure гарантирует zero calls.
- [x] Unexpected `PairNotAssessed`, downstream failure и malformed success
  становятся typed atomic batch conflicts без exception/result leak.
- [x] После downstream conflict pure pass проверяет остальные candidates для
  полного canonical conflict set, но failure не содержит partial outcomes.
- [x] Success хранит full generation result binding, assessment policy и
  ordered exact item outcomes; future equal-identity/different-content
  conflicts не выбирают winner.
- [x] Доказан `O(N + C)` lookup/composition bound плюс ровно `C` pair
  assessments без regeneration, all-pairs или transitive work.
- [x] Fully fictional matrix покрывает все назначенные cases и явно запрещает
  physical-property/merge/cluster semantics.
- [x] Все назначенные проверки успешны, changed paths содержат только
  назначенные Markdown documents, создан один documentation commit и дерево
  чистое.

## Фактически выполненная работа

- Создан [ADR 0009](../decisions/0009-duplicate-candidate-assessment-batch.md),
  принявший отдельную pure atomic composition без regeneration и partial
  success.
- Создана
  [детальная design-спецификация](../design/PUBLICATION-DUPLICATE-ASSESSMENT-BATCH.md)
  с pseudotypes, constructor invariants, exact binding, typed conflicts,
  validation/call order, atomicity, replay и complexity proof.
- Зафиксирована отдельная batch identity из exact generation identity и
  explicit assessment policy version; full generation result и full
  assessment policy сохраняются в success content.
- Принято продолжение pure downstream pass после failure для полного conflict
  set: valid preflight даёт ровно `C` calls, а failure не раскрывает partial
  successful items.
- Candidate blocking matches сохранены только как routing metadata; pair
  assessment получает exact current full available sides и не создаёт
  physical property, merge или transitive relation.
- Согласованы `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и
  `docs/tasks/README.md`; TASK-023 отражена как уже слитая в `main`.

## Проверки

- `uv sync --frozen` — успешно: CPython 3.14.7, установлены 18 зафиксированных
  packages, lock не изменён.
- `uv lock --check` — успешно: разрешены 18 packages, lock соответствует
  project metadata.
- `uv run quality` — успешно: Ruff format-check (`89 files`), Ruff lint,
  strict mypy (`39 source files`), основной pytest (`570 passed`) и fixture
  catalog integrity (`44 passed`).
- Все относительные Markdown links во всех 8 изменённых документах — успешно:
  проверено 50 локальных ссылок, broken links отсутствуют.
- `git diff --check` — успешно.
- Changed-path audit — успешно: изменены только назначенные Markdown files;
  `src/`, `tests/`, `tests/fixtures`, `fixtures/golden`, `pyproject.toml` и
  `uv.lock` не изменены.
- Review согласованности с ADR 0006/0008 и public types TASK-019/022/023 —
  успешно; production quality/recall claims не добавлены.

## Итог

TASK-024 завершена и слита в `main` merge-коммитом
`8e9d941`. Принят только design contract; implementation/tests реализованы
отдельной TASK-025, а storage, external boundaries и physical-property
semantics по-прежнему отсутствуют.

## Итоговый коммит

Один атомарный documentation commit находится в истории ветки по сообщению
`docs: design atomic duplicate assessment batch`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-025 — реализовать neutral frozen/slots batch-assessment contracts и pure deterministic composition по ADR 0009 для exact DuplicateCandidateGenerationResult/current AvailableObservation binding, без storage, JSON, CLI, real data или изменения candidate/assessment policies
