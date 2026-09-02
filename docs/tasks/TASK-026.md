# TASK-026 — design consumer-owned persistence и replay boundary

- Статус: завершено и слито в `main`
- Рабочая ветка: `task/026-persistence-replay-boundary-design`
- Целевая ветка: `main`
- Стартовый SHA: `e5b42769437863e195d4a5e1bbec390009f199c0`

## Цель

Принять один storage-neutral архитектурный контракт, который классифицирует
authoritative и derived publication/duplicate artifacts и задаёт
consumer-owned ports, structural identity, exact replay, optimistic revision,
atomic commit, conflict, recompute и retention для будущего side-effecting
слоя.

## Включённый объём

- ADR 0010 с явным сравнением трёх вариантов и одним выбранным решением.
- Детальная design-спецификация authority/retention classes, lineage,
  port ownership, logical requests/outcomes, revisions и conflicts.
- Классификация source snapshots, available/unavailable observations,
  histories, changes, candidate generation, pair/batch assessments,
  manual-review revisions и quality/control artifacts.
- Узкие `ObservationHistoryPort`, `DuplicateGenerationArtifactPort`,
  `DuplicateAssessmentArtifactPort`, `ManualReviewRevisionPort` и
  `DuplicateQualityAuditPort` вместо generic repository.
- Exact identity/equality, replay-before-revision, explicit
  `ExpectAbsent | ExpectExact`, stale/concurrent writer и no-last-write-wins
  semantics.
- Отдельные atomic units для multi-history append, generation result,
  assessment batch с exact generation dependency и manual-review revision.
- Crash/unknown-outcome reconciliation, safe recompute, derived backfill,
  explicit supersession и запрет observation backfill bypass.
- Retention immutable evidence/audit и rebuildable projections.
- Stable typed persistence conflicts, structural subjects и canonical order.
- Полностью вымышленная scenario matrix всех назначенных случаев.
- Согласование project/architecture/roadmap/checkpoint/task registry только по
  принятому design-only результату; отражение TASK-025 как integrated в main.

## Исключённый объём

- Python implementation, tests нового runtime-кода и package exports.
- SQLite/PostgreSQL/иная БД, SQL schema, ORM, migrations, filesystem layout,
  JSON/Pydantic serialization и durable adapter.
- Cache, queue, scheduler, distributed lock, transaction manager и
  side-effecting executor/orchestrator.
- Изменение observation/candidate/assessment/manual-review contracts или
  policies, real data, HTTP, scraping, первый source и юридические решения.
- AI, UI, API, CLI, OpenClaw, Telegram, notifications.
- Physical property, automatic merge/collapse/hide, clustering и transitive
  duplicate semantics.
- Dependencies, `pyproject.toml`, `uv.lock`, source/tests/fixtures/golden.
- Push/publication, merge в `main`, удаление worktree/ветки и начало TASK-027.

## Критерии готовности

- [x] ADR 0010 сравнивает три назначенных варианта и однозначно принимает
  hybrid model.
- [x] Authoritative/derived и immutable-audit/rebuildable-projection axes
  определены точно с rationale для каждого existing artifact class.
- [x] Port contracts принадлежат consumers, зависимости направлены к
  application/core, generic `Repository[T]` и dynamic plugins отсутствуют.
- [x] Logical load/commit requests, successes, failures, opaque revisions и
  structural conflict subjects описаны без Python implementation.
- [x] Structural identity, full content equality, exact replay и
  equal-identity/different-content conflict согласованы с ADR 0005/0006/0008/0009.
- [x] Explicit expected revisions не допускают unconditional write или hidden
  last-write-wins; replay разрешается до stale-revision conflict только для
  exact identity/content.
- [x] Multi-history, generation/assessment и manual-review atomic units не
  допускают partial state при conflict, crash или retry.
- [x] Rerun, unknown outcome, stale read, concurrent writer, recompute,
  derived backfill и supersession имеют deterministic semantics.
- [x] Minimal reads достаточны будущему side-effecting executor, но сам
  executor не спроектирован и не реализован.
- [x] Retention сохраняет evidence/lineage/policy/version coordinates, а
  disposable projections перечислены отдельно.
- [x] Stable typed taxonomy и canonical ordering заданы только на уровне
  design и не зависят от backend ids/hash/locale.
- [x] Fully fictional matrix покрывает first write, exact retry, stale
  revision, concurrent writers, history/batch/manual conflicts, new-policy
  recompute, interrupted attempt и no partial state.
- [x] Документация внутренне согласована; TASK-025 отмечена integrated, а
  TASK-027 сформулирована буквально.
- [x] Все назначенные проверки успешны, changed paths содержат только
  назначенные Markdown files, создан один documentation commit и дерево
  оставлено чистым.

## Фактически выполненная работа

- Создан [ADR 0010](../decisions/0010-publication-persistence-and-replay.md),
  принявший hybrid: authoritative immutable observations/human assertions,
  version-bound derived audit artifacts и rebuildable projections.
- Создана
  [детальная design-спецификация](../design/PUBLICATION-PERSISTENCE-AND-REPLAY.md)
  с двумя осями классификации, five consumer-owned ports, logical pseudotypes,
  atomic units, exact read requirements, conflicts и retention.
- Зафиксирован общий commit protocol: validate, resolve identity/content,
  exact replay, затем expected revision и только потом all-or-nothing write.
- Для lost response/interrupt введён immutable receipt/reconciliation: exact
  found content означает replay, absence разрешает exact retry только при
  прежних revisions, different content является conflict.
- Generation сохраняется complete; assessment batch атомарно связывает full
  embedded generation и все pair results; manual review фиксирует revision,
  supersedes и head одной unit.
- Normal observation backfill bypass запрещён; derived historical artifacts
  можно materialize только под exact identity. Новая policy/configuration
  создаёт новую identity и не переписывает historical audit.
- Quality/control inputs отделены от rebuildable metrics/coverage; raw source
  capture оставлен отдельной будущей legal/audit boundary.
- Согласованы `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md`,
  `docs/tasks/README.md` и TASK-025 integration state.

## Проверки

- `uv sync --frozen` — успешно; lock и зависимости не изменены.
- `uv lock --check` — успешно; lock соответствует project metadata.
- `uv run quality` — успешно: Ruff format-check (`95 files`), Ruff lint,
  strict mypy (`41 source files`), основной pytest (`603 passed`) и fixture
  catalog integrity (`44 passed`).
- Все 59 относительных Markdown links в 9 изменённых документах — успешно;
  broken links отсутствуют.
- `git diff --check` — успешно.
- Changed-path audit — успешно: изменены только назначенные Markdown files;
  `src/`, `tests/`, fixtures/golden, `pyproject.toml` и `uv.lock` не изменены.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-026 принимает только storage-neutral persistence/replay design. Python
ports/reference adapter, durable technology, executor, external boundaries,
real data и physical-property semantics намеренно отсутствуют. Ветка не
сливается в `main` этой задачей.

## Итоговый коммит

Один атомарный documentation commit будет создан после полного successful
quality/documentation audit. Точный SHA подтверждается Git после commit и не
дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-027 — реализовать neutral Python port contracts и deterministic in-memory
reference adapter по ADR 0010 с exact replay, optimistic revision и atomic
failures, без SQL/JSON/filesystem/CLI/real data и без side-effecting production
executor. Задача выполнена в `task/027-persistence-ports-in-memory`; в
`main` ещё не слита.
