# Текущая контрольная точка

## Завершённая задача

TASK-008 — детерминированная нормализация одного
`SourcePublicationSnapshot` в полный immutable `NormalizedListing` либо
упорядоченные ошибки `NORMALIZATION` без partial listing.

## Состояние основной ветки

- TASK-001…TASK-008 слиты в `main` отдельными merge-коммитами.
- Короткоживущая ветка `task/008-single-snapshot-normalization` сохраняет
  исходный атомарный содержательный коммит после безопасной интеграции.
- Удалённый репозиторий не настроен и не требуется в текущем объёме.

Текущий SHA, активную ветку, факт интеграции и чистоту дерева следует подтверждать
через Git, поскольку документ не дублирует изменяемые идентификаторы истории.

## Что уже существует

- Локальный Git-репозиторий, проектные правила и переносимые документы состояния.
- CPython `>=3.14,<3.15`, `.python-version` для 3.14.7, `uv`, зафиксированный
  `uv.lock`, устанавливаемый `src`-пакет и единая команда `uv run quality`.
- Pydantic 2.x только на недоверенной внешней границе; pytest, Ruff и strict
  mypy; полностью офлайн fixture catalog integrity.
- Публичная строгая граница `load_fixture_source_batch(Path)` для одного
  локального UTF-8 документа `fixture-source-batch@1` со стабильными
  `INPUT_SYNTAX`/`INPUT_SCHEMA` issues.
- Нейтральные immutable-типы структурных locations, provided/missing source
  fields, `ValidatedSourceBatch`, `ContractIssue` и атомарных результатов.
- Чистая операция `adapt_fixture_source_batch(ValidatedSourceBatch)`, которая
  назначает `fixture_portal`, проверяет publication id/URL и возвращает полный
  `SourceBatch` либо упорядоченные `SOURCE_ADAPTER` issues.
- Нейтральные `SourceId`, `PublicationId`, `PublicationRef`, `RawField`,
  `MissingField`, `SourcePublicationSnapshot` и `SourceBatch`.
- Канонические immutable-типы `SourceUrl`, `ObservedAt`, `LocationText`,
  `MoneyAmount`, `Currency`, `Area`, `RoomCount` и версии правил.
- `TracedValue`, отдельные `ValueProvenance`, `MissingProvenance`,
  `UnsupportedProvenance`, закрытые `Present`/`Missing`/`Unsupported` и полный
  `NormalizedListing`.
- Явный неизменяемый `FIXTURE_NORMALIZATION_RULES_V1` с восемью утверждёнными
  версиями правил.
- Чистая публичная операция `normalize_fixture_snapshot(snapshot, rules)` для
  одного snapshot: строгий RFC 3339 → UTC, Unicode whitespace, точные деньги,
  валюта, площадь и комнаты, полное происхождение и атомарный failure.
- Прямые unit-тесты нормализатора без Pydantic/JSON/filesystem и ограниченные
  offline integration tests существующих loader/adapter со статическими
  fixtures без пакетного normalizer.
- Проект первого локального среза, точные внешние документы, негативная матрица,
  byte-exact golden-файлы и правила детерминизма TASK-002…TASK-004.

## Что намеренно не реализовано

- Нормализация полного `SourceBatch` и orchestration loader/adapter/normalizer.
- `CollectionSnapshot`, пакетная атомарность, duplicate conflict и проверка
  уникальности `PublicationRef`.
- Pydantic-модели критериев/результата, поиск, mapper, output validation и
  сериализация.
- Пользовательский CLI первого среза.
- Несколько наблюдений, постоянное хранилище, история изменений и дедупликация.
- Физический объект недвижимости, база данных, API, HTTP, HTML и реальные
  площадки.
- Нестандартные сигналы, ИИ, уведомления, UI, OpenClaw и Telegram.
- Docker, CI, развёртывание, удалённый репозиторий и динамический загрузчик
  плагинов.

## Рекомендуемая следующая задача

**TASK-009 — атомарная нормализация пакета и immutable collection.** Принять
полный `SourceBatch`, нормализовать все snapshots, собрать все независимо
доказуемые ошибки и только при полном успехе построить immutable
`CollectionSnapshot` с проверкой уникальности `PublicationRef`. Не добавлять
criteria, search, output mapping, serialization, пользовательский CLI или
реальные источники.

## Открытые архитектурные вопросы

- Как представить несколько наблюдений и изменения одной публикации после
  подтверждения первого среза?
- Когда и на каких доказательствах вводить сущность или группу физического
  объекта для дедупликации?
- Какое постоянное хранение потребуется и какие измеренные требования определят
  его выбор?
- Какие правила законного и бережного получения данных обязательны для первого
  реального источника?
- Когда составному нормализованному значению понадобится происхождение из
  нескольких исходных полей?
- Как измерять качество дедупликации и доказательных сигналов?

Ответы не должны приниматься молча: существенные решения оформляются в
`docs/decisions/` в рамках назначенных задач.
