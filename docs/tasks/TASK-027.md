# TASK-027 — neutral persistence ports и in-memory reference adapter

- Статус: завершено и слито в `main`
- Рабочая ветка: `task/027-persistence-ports-in-memory`
- Целевая ветка: `main`
- Стартовый SHA: `6c844845b8f5fd9644b1bd3f2daea70f7f8495f2`

## Цель

Реализовать storage-neutral Python contracts ADR 0010 и deterministic
in-memory reference adapter с exact replay, optimistic expected revisions и
all-or-nothing failures без durable technology и production executor.

## Включённый объём

- Opaque adapter-issued `PersistenceRevision`, explicit
  `ExpectAbsent | ExpectExact`, `CommitDisposition` и typed operational failures.
- Пять узких consumer-owned Protocol ports:
  `ObservationHistoryPort`, `DuplicateGenerationArtifactPort`,
  `DuplicateAssessmentArtifactPort`, `ManualReviewRevisionPort` и
  `DuplicateQualityAuditPort`.
- Frozen/slots request, success, failure, outcome, identity и structural subject
  types с tuple-only collections, runtime invariants и canonical conflicts.
- Deterministic in-memory reference adapter, реализующий все пять
  ports как проверяемый эталон.
- Exact histories/observations/generation/batch/pair/review/quality reads без
  hidden newest selection или absent-as-empty substitution.
- Replay-before-revision, equal-identity/different-content conflicts, explicit
  expected revisions и no-last-write-wins.
- Atomic multi-history receipt/head unit, complete generation artifact,
  generation+assessment+pair unit, assessment supersession link, manual-review
  revision/edge/head unit и immutable quality audit input revision.
- Прямые fully fictional tests контрактов и adapter operations.
- Package-root exports и согласование project state documents.

## Исключённый объём

- SQLite, PostgreSQL, SQL, ORM, migrations, filesystem, JSON/Pydantic
  serialization и иная durable technology.
- Production executor/orchestrator, scheduler, queue, retry/backoff loop,
  cache, distributed lock и transaction manager API.
- Вызов pure generation, assessment, review и quality operations внутри
  adapter; existing policies и pure operations не изменяются.
- Real data, HTTP, scraping, source adapter, browser automation и external
  services.
- Raw archive, deletion/legal retention implementation, observation correction,
  out-of-order backfill и multi-policy migration.
- API, CLI, UI, AI, OpenClaw, Telegram, physical property, winner,
  merge/collapse/hide, clustering и transitive relation.
- Dependencies, `pyproject.toml`, `uv.lock`, fixtures/golden, push/publication,
  merge в `main`, удаление ветки/worktree и начало TASK-028.

## Критерии готовности

- [x] Все public records frozen/slots и runtime-validated; collections tuple-only.
- [x] Пять узких public Protocol ports реализованы без generic
  `Repository[T]` и storage-owned domain API.
- [x] Revision tokens выдаются adapter-ом, opaque для consumer,
  stable при replay и не используют clock/UUID/random/hash/domain time.
- [x] Exact replay проверяется до expected revision; content conflict
  и stale revision не выбирают winner.
- [x] Каждая назначенная atomic unit полностью видима либо
  полностью отсутствует; failure не содержит partial success.
- [x] Assessment batch не виден без exact generation; failure не
  сохраняет generation или pair prefix.
- [x] Manual-review fork и quality audit revisions имеют exact lineage и
  optimistic head semantics.
- [x] Metrics/coverage не становятся authoritative persistence state.
- [x] Adapter не выполняет pure operations за consumer и не вводит I/O,
  serialization, durable storage или production orchestration.
- [x] Прямые tests покрывают constructors/protocols, first write,
  retry, content/stale conflicts, competing writers, atomic rollback, exact reads,
  supersession, immutability и forbidden surface.
- [x] Документация отражает только фактический scope и literal
  next TASK-028 с отдельным подтверждением источника и сети.
- [x] Все назначенные checks успешны; один implementation commit,
  чистое дерево, без merge в `main`.

## Фактически выполненная работа

- Добавлен `publication_persistence.py` с common primitives, typed operational
  failures, exact load/commit contracts, port-specific structural conflicts и
  пять runtime-checkable Protocol ports.
- Добавлен `in_memory_publication_persistence.py`; один stateful adapter
  реализует все ports и выдаёт revisions только при новом
  successful content commit.
- Observation receipts сохраняют exact candidates, prepared outcomes/changes
  и post-head revisions; replay возвращает те же heads без новых
  revisions.
- Assessment commit до записи проверяет generation, batch, pair contents
  и оба expected slots, затем атомарно публикует всю unit.
- Manual-review и quality heads хранят supplied positive domain revision
  отдельно от opaque persistence token; exact old retries возвращают
  исходный commit token.
- Добавлены package-root exports и 15 direct fully fictional tests.

## Проверки

- `uv run pytest -q tests/test_publication_persistence.py` — успешно:
  `15 passed`.
- `uv sync --frozen` — успешно; dependencies и lock не изменены.
- `uv lock --check` — успешно; lock соответствует project metadata.
- `uv run quality` — успешно: Ruff format-check (`99 files`), Ruff
  lint, strict mypy (`44 source files`), основной pytest (`618 passed`) и
  fixture catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Все относительные Markdown links в изменённых документах —
  успешно; broken links отсутствуют.
- Changed-path audit — успешно: `pyproject.toml`, `uv.lock`, fixtures
  и golden не изменены; новых dependencies нет.
- Public forbidden-surface audit — успешно: нет SQL/JSON/filesystem/
  network/executor/generic Repository imports и exports.
- Проверки выполнены на Windows; Linux не запускался.

## Итог

TASK-027 реализует только neutral contracts и in-memory reference
adapter ADR 0010. Durable storage, external source access, production execution,
real data и physical-property semantics намеренно отсутствуют.

## Итоговый коммит

Один атомарный implementation commit будет создан после полного
successful audit. Точный SHA подтверждается Git после commit и не
дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-028 — выбрать первый реальный источник и принять
legal/ethical/technical контракт ограниченного read-only пилота,
включая разрешённый способ доступа, rate limits, минимальный набор
данных, блокировки, персональные данные, stop conditions и доказательства
соблюдения правил. Без scraper/source adapter и без сбора real data.
TASK-028 не начата и требует отдельного подтверждения пользователем
источника и использования сети.
