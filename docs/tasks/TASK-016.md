# TASK-016 — нейтральное ядро наблюдений и изменений публикации

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/016-observation-change-core`
- Целевая ветка: `main`
- Стартовый SHA: `835989cf49db25ee0f6dfd103885be1a21d8cce4`

## Цель

Реализовать нейтральные immutable frozen/slots типы наблюдений и изменений
ровно одной `PublicationRef`, а также чистые детерминированные операции
сравнения двух последовательных наблюдений и добавления одного наблюдения в
историю по ADR 0005. Реализация повторно использует канонические типы первого
среза и не меняет его поведение.

## Включённый объём

- Один небольшой нейтральный модуль ядра с валидируемыми opaque версиями и
  codes, `ObservationKey`, available/unavailable observations и двумя
  достаточными evidence-типами.
- `PublicationObservationHistory` строго одной `PublicationRef` и одной
  comparison policy со строго возрастающими уникальными observations.
- Версионированная `publication-change-policy@1` с порядком `source_url`,
  `location_text`, `price_amount`, `currency`, `total_area`, `rooms`.
- Immutable `FieldSnapshot`, `FieldDelta`, availability transitions,
  `AvailabilityEvidenceDelta`, `ChangeSet`, стабильные conflicts и атомарные
  append success/failure.
- Чистые `compare_consecutive_observations(previous, current, policy)` и
  `append_observation(history, candidate, policy)` с replay, conflict,
  out-of-order и policy semantics ADR 0005.
- Полная проверка согласованности available observation с key, listing и
  provenance обязательных/необязательных полей.
- Прямые полностью вымышленные unit-тесты конструкторных инвариантов, полного
  `Present`/`Missing`/`Unsupported` transition matrix, трёх классов field
  delta, timestamp-only no-change, append/replay/conflict/order/policy,
  unavailable/reappearance, immutability, детерминизма и отсутствия partial
  failure results.
- Осознанный экспорт публичных типов/операций и согласование только фактически
  затронутых проектных документов.

## Исключённый объём

- Batch/multi-history append TASK-017.
- Постоянное хранение, repository adapter, SQLite/PostgreSQL/ORM, schema,
  migrations, JSON/Pydantic/filesystem boundary, CLI/API/UI.
- Изменение `search-result@1`, application flow, нормализации, fixtures,
  golden и контрактов TASK-006…TASK-014.
- Конструкторы или shortcuts, превращающие batch omission, timeout,
  блокировку, network/source failure в `UnavailableObservation`.
- Реальные источники, HTTP, polling, scheduler, retries/rate limits.
- Physical property, cross-source dedup, сигналы, уведомления, AI, OpenClaw и
  Telegram.
- Новые зависимости, изменения `pyproject.toml` или `uv.lock`.
- Начало TASK-017, слияние в `main`, публикация и удаление ветки/worktree.

## Критерии готовности

- [x] Все типы frozen/slots, tuples и результаты immutable; конструкторы
  обеспечивают инварианты ADR 0005 без I/O, часов, UUID и скрытого состояния.
- [x] Available observation проверяет reference/observed_at у key, listing и
  provenance каждого обязательного и optional поля.
- [x] Exact replay ищется по любому принятому key; same-key difference,
  out-of-order, stream reference и policy mismatch возвращают точные стабильные
  conflicts без partial history/changes.
- [x] Первый append не создаёт `ChangeSet`; последующие сравнивают только с
  непосредственным predecessor; replay возвращает исходную history.
- [x] Available→Available сравнивает ровно шесть полей и выдаёт максимум одну
  delta на поле в policy order с приоритетом substantive, raw-only,
  provenance refresh; timestamp-only refresh даёт пустой `ChangeSet`.
- [x] Available→Unavailable, Unavailable→Available и повторная недоступность
  реализуют точные availability/evidence semantics без field comparison.
- [x] Exhaustive unit-тесты доказывают назначенные переходы, reason-code,
  append/conflict semantics, детерминизм, immutability и atomic failures.
- [x] Публичная поверхность экспортирована осознанно; core не зависит от
  Pydantic, JSON, storage или первого application flow.
- [x] `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и реестр
  задач отражают только фактический результат TASK-016 и ровно TASK-017 как
  следующий малый шаг.
- [x] `uv sync --frozen`, `uv lock --check`, `uv run quality` и
  `git diff --check` успешны.
- [x] `pyproject.toml`, `uv.lock`, `tests/fixtures` и golden не изменены; diff
  не содержит посторонних изменений.
- [x] Создан один атомарный commit, рабочее дерево чистое, task-ветка не слита.

## Фактически выполненная работа

- Добавлен один нейтральный модуль `publication_observations.py`, повторно
  использующий `PublicationRef`, `ObservedAt`, `NormalizedListing`, все
  канонические field-типы и provenance первого среза.
- Реализованы валидируемые opaque policy/availability/cause/outcome codes,
  `ObservationKey`, два вида observation, два достаточных evidence-типа и
  строго возрастающая history одной reference/policy.
- `AvailableObservation` проверяет identity и timestamp listing, а также
  source/publication reference и `observed_at` provenance каждого обязательного
  и optional поля. Unavailable принимает только direct source state либо
  conclusive targeted-check evidence; operational failure shortcuts отсутствуют.
- Реализована immutable `publication-change-policy@1` с точным порядком шести
  полей, canonical projections, полными field snapshots/deltas, availability
  transitions, evidence delta и versioned `ChangeSet`.
- `compare_consecutive_observations` реализует приоритет substantive → raw-only
  → provenance refresh, исключает только `observed_at` из provenance comparison
  и возвращает успешный пустой `ChangeSet` при timestamp-only refresh.
- `append_observation` ищет replay по любому принятому key, различает same-key
  conflict и новый out-of-order key, проверяет stream/policy, сравнивает только
  с tail и возвращает либо полную новую history, либо исходную replay history,
  либо conflicts без partial state.
- Добавлены 75 прямых fully fictional unit-тестов: constructor invariants,
  provenance всех восьми обязательных/optional slots, шесть policy fields,
  полная `Present`/`Missing`/`Unsupported` matrix, reason/raw/provenance/time,
  first append, tail/non-tail replay, conflicts, unavailable/reappearance,
  immutability, tuple discipline и atomic failures.
- Публичные типы/операции осознанно экспортированы из пакета. Первый application
  flow, normalization, внешние contracts, fixtures и golden не менялись.

## Проверки

- `uv sync --frozen` — успешно; проверены 18 зафиксированных packages без
  изменения lock.
- `uv lock --check` — успешно; разрешены 18 packages без изменения `uv.lock`.
- `uv run quality` — успешно: Ruff format-check (`63 files`), Ruff lint,
  strict mypy (`29 source files`), основной pytest (`372 passed`) и fixture
  catalog integrity (`44 passed`).
- Отдельный новый модуль: strict mypy успешно, `75 passed`.
- `git diff --check` — успешно.
- Проверка changed paths подтвердила отсутствие изменений `pyproject.toml`,
  `uv.lock`, `tests/fixtures` и golden.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-016 завершена в `task/016-observation-change-core`, готова к отдельному
review/merge и намеренно не слита в `main`. Реализован только pure append одного
observation одной history; storage, boundary и multi-history composition не
начинались.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`feat: implement publication observation change core`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-017 — реализовать чистую атомарную операцию добавления набора observations
в несколько независимых publication histories с глобально детерминированными
conflicts и без storage, JSON, CLI и изменений первого среза. Эта задача здесь
не начинается.
