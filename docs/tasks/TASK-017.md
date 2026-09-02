# TASK-017 — атомарное добавление observations в несколько histories

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/017-atomic-observation-batch`
- Целевая ветка: `main`
- Стартовый SHA: `f518a4e227c20317a4920b2ad3bab4bac1d87191`

## Цель

Реализовать одну чистую детерминированную операцию, которая атомарно добавляет
непустой tuple observations в несколько независимых publication histories
поверх готового `append_observation` TASK-016. Внешний порядок histories и
candidates не влияет на результат; любой конфликт отклоняет весь batch и
возвращает полный глобально упорядоченный набор доказуемых conflicts без
частичных histories, item outcomes или `ChangeSet`.

## Включённый объём

- Небольшой отдельный нейтральный модуль прикладной композиции, который
  повторно использует публичные типы и single-history operation TASK-016.
- Frozen/slots контейнер histories: только tuple, не более одной history на
  `PublicationRef`, каноническое хранение по `SourceId.value`, затем
  `PublicationId.value`.
- Pure operation над контейнером histories, непустым tuple candidates и
  `ComparisonPolicy`; для отсутствующей reference создаётся логически пустая
  history версии переданной policy.
- Группировка кандидатов по `PublicationRef`, сворачивание полных exact
  duplicates одного `ObservationKey`, выявление одного
  `timestamp_content_conflict` для одного key с разным полным содержимым и
  обработка уникальных keys строго по `ObservedAt`.
- Exact replay любого существующего ключа, out-of-order и policy semantics,
  делегированные `append_observation` TASK-016.
- Полный дедуплицированный набор independently provable conflicts в порядке
  reference, наличия/`ObservedAt` subject key, category и code.
- Atomic immutable success с полным каноническим контейнером histories и одним
  item outcome на уникальный успешный `ObservationKey`; atomic immutable
  failure только с непустым tuple conflicts.
- Прямые fully fictional unit-тесты формы, атомарности, конфликтов,
  детерминизма, permutation invariance, идемпотентности и сохранения
  `ChangeSet`/availability/reappearance semantics TASK-016.
- Осознанный экспорт новых composition types и операции из package root и
  согласование только фактически затронутых проектных документов.

## Исключённый объём

- Изменение семантики или публичных контрактов TASK-016.
- Storage/repository adapter, expected revision, база данных, ORM, schema,
  migrations, JSON/Pydantic/filesystem boundary, CLI/API/UI.
- Изменение первого application flow, `search-result@1`, normalization,
  fixtures, golden, `pyproject.toml` или `uv.lock`.
- Часы, UUID, I/O, hidden state, реальные источники, HTTP, polling, scheduler,
  retries и rate limits.
- Physical property, cross-source dedup implementation, duplicate scoring,
  сигналы, уведомления, AI, OpenClaw, Telegram и динамическая plugin-система.
- Реализация или начало TASK-018, слияние в `main`, публикация и удаление
  ветки/worktree.

## Критерии готовности

- [x] Новая композиция использует `append_observation` как единственный
  источник single-history append/comparison semantics и сохраняет направление
  зависимостей внутрь.
- [x] Все новые публичные контейнеры и результаты frozen/slots, tuple-only;
  mutable/empty candidate container и неверная форма histories отклоняются.
- [x] Histories хранятся канонически и уникальны по `PublicationRef`; candidates
  группируются и обрабатываются независимо от внешнего порядка.
- [x] Exact duplicates сворачиваются; same-key/different-content, replay,
  out-of-order и policy mismatch дают точные существующие conflicts без новых
  category/code и без `expected_revision_mismatch`.
- [x] Все independently provable conflicts собираются один раз в точном
  глобальном порядке; один conflict запрещает применение всех streams.
- [x] Success содержит полный новый набор histories и канонические item
  outcomes, точно сохраняющие `APPENDED`/`REPLAYED` и `ChangeSet` TASK-016.
- [x] Повторный успешный batch не меняет histories по значению и возвращает
  только `REPLAYED`; permutation invariance доказана несколькими перестановками.
- [x] Тесты доказывают создание и обновление нескольких streams, untouched
  history, full conflict accumulation, atomic failure и делегированные field/
  availability/reappearance semantics.
- [x] Публичная поверхность экспортирована осознанно; модуль не зависит от
  Pydantic, JSON, filesystem, CLI, storage или первого application flow.
- [x] `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и реестр
  задач отражают только фактический результат TASK-017 и ровно TASK-018 как
  следующий малый шаг.
- [x] `uv sync --frozen`, `uv lock --check`, новые unit-тесты,
  `uv run quality` и `git diff --check` успешны.
- [x] `pyproject.toml`, `uv.lock`, `tests/fixtures` и golden не изменены; diff
  не содержит посторонних изменений.
- [x] Создан один атомарный commit, рабочее дерево чистое, task-ветка не слита.

## Фактически выполненная работа

- Добавлен отдельный нейтральный модуль
  `publication_observation_batches.py`. Он импортирует готовые observation,
  history, conflict, outcome и policy types TASK-016 и вызывает
  `append_observation` для single-history append/comparison semantics.
- Реализован frozen/slots `PublicationObservationHistories`: только tuple,
  type validation, уникальность `PublicationRef` и каноническое хранение по
  `SourceId.value`, затем `PublicationId.value`. Перестановка входного tuple
  даёт равный контейнер; вход не мутируется.
- Реализованы frozen/slots `ObservationBatchItemOutcome`, atomic
  `ObservationBatchAppendSuccess`/`Failure` и result union. Success хранит
  полный контейнер histories и непустой канонический tuple outcomes; failure
  хранит только непустой уникальный канонический tuple conflicts.
- `append_observation_batch` строго принимает контейнер histories, непустой
  tuple candidates и явную `ComparisonPolicy`. Внутри candidates группируются
  по structural `ObservationKey`, full exact duplicates сворачиваются, а
  разные observations одного key дают один `timestamp_content_conflict`.
- Уникальные keys обрабатываются в порядке reference + `ObservedAt`. Для новой
  reference создаётся пустая history версии переданной policy; existing replay,
  same-key conflict, out-of-order и все `ChangeSet` получаются через
  `append_observation` без повторной field comparison.
- Все policy, timestamp/content и out-of-order conflicts собираются по всем
  независимым streams, дедуплицируются и сортируются по reference,
  наличию/времени subject key, category и code. При любом conflict построенные
  локальные промежуточные значения не попадают в public failure.
- Добавлены 14 прямых fully fictional unit-тестов. Они покрывают tuple/shape
  invariants, multi-stream creation, несколько возрастающих кандидатов одного
  нового stream, update и untouched history, tail/non-tail replay, duplicate
  collapsing, same-key content/kind/evidence conflicts, out-of-order нескольких
  streams, policy mismatch, полный global conflict order и atomic failure.
- Несколько перестановок histories/candidates дают равный результат; повторный
  успешный batch сохраняет histories по значению и возвращает только
  `REPLAYED`. Равенство с последовательными результатами TASK-016 доказывает
  сохранение confirmed unavailable и reappearance `ChangeSet` без пересчёта.
- Новая публичная поверхность экспортирована из package root. Первый
  application flow, normalization, external boundaries, fixtures и golden не
  менялись; storage/revision/I/O surface не добавлялся.

## Проверки

- `uv sync --frozen` — успешно; проверены 18 зафиксированных packages без
  изменения lock.
- `uv lock --check` — успешно; разрешены 18 packages без изменения `uv.lock`.
- `uv run pytest -q tests/test_publication_observation_batches.py` — успешно,
  `14 passed`.
- `uv run quality` — успешно: Ruff format-check (`66 files`), Ruff lint,
  strict mypy (`31 source files`), основной pytest (`386 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно; предупреждения Git о будущем LF→CRLF checkout
  не являются whitespace errors.
- Проверка changed paths подтвердила отсутствие изменений `pyproject.toml`,
  `uv.lock`, `tests/fixtures` и golden и отсутствие посторонних файлов.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-017 завершена в `task/017-atomic-observation-batch`, готова к отдельному
review/merge и намеренно не слита в `main`. Реализована только чистая
multi-history composition; storage, expected revision, внешние boundaries и
TASK-018 не начинались.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`feat: implement atomic observation batch composition`. Точный SHA
подтверждается Git после создания commit и не дублируется внутри его
собственного снимка.

## Следующая рекомендуемая задача

TASK-018 — принять доказательную модель возможных дублей публикаций с
объяснимыми положительными и отрицательными основаниями, ручной проверкой и без
программной реализации, physical-property merge, storage или AI. Эта задача
здесь не начинается.
