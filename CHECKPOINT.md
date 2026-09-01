# Текущая контрольная точка

## Завершённая задача

TASK-010 — строгая внешняя граница `search-criteria@1` и канонический
immutable `SearchCriteria`, без выполнения поиска.

## Состояние основной ветки

- TASK-001…TASK-009 слиты в `main` отдельными merge-коммитами.
- TASK-010 завершена в короткоживущей ветке
  `task/010-search-criteria-boundary`, созданной от точного SHA
  `f760637ac0f0e456453bcaf9e9c2345c6b7bfe57`; ветка готова к отдельному merge
  координатором, а `main` из task-worktree не изменялась.
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
- Frozen/slots `CollectionSnapshot`, `CollectionBuildSuccess`/
  `CollectionBuildFailure` и чистая операция
  `build_fixture_collection(SourceBatch, rules)`.
- Пакетная операция обходит все snapshots, глобально сортирует
  independently provable `NORMALIZATION` issues и только после полного
  успеха проверяет точную уникальность `PublicationRef`.
- Коллекция хранит полный tuple `NormalizedListing` в порядке входа;
  каждое повторное вхождение после первого даёт устойчивый
  `COLLECTION_CONFLICT/duplicate_publication_ref`.
- Канонические frozen/slots `Money` и `SearchCriteria` с тремя необязательными
  ограничениями; `allowed_rooms` хранится как непустой
  `frozenset[RoomCount]` и не сохраняет входной порядок.
- Публичная граница `load_search_criteria(Path)` для одного UTF-8
  `search-criteria@1`: strict Pydantic structure/types, точные amount/area/rooms
  правила, атомарный immutable success/failure и упорядоченные
  `INPUT_SYNTAX`/`INPUT_SCHEMA` issues без пути и входных значений.
- Прямые unit-тесты нормализатора без Pydantic/JSON/filesystem и ограниченные
  offline integration tests существующих loader/adapter со статическими
  fixtures, включая атомарный batch-to-collection переход.
- Проект первого локального среза, точные внешние документы, негативная матрица,
  byte-exact golden-файлы и правила детерминизма TASK-002…TASK-004.

## Что намеренно не реализовано

- Path-level orchestration loader/adapter/normalizer/collection.
- Поиск, `SearchMatch`/`SearchResult`, mapper, Pydantic output validation и
  JSON-сериализация.
- Пользовательский CLI первого среза.
- Несколько наблюдений, постоянное хранилище, история изменений и дедупликация.
- Физический объект недвижимости, база данных, API, HTTP, HTML и реальные
  площадки.
- Нестандартные сигналы, ИИ, уведомления, UI, OpenClaw и Telegram.
- Docker, CI, развёртывание, удалённый репозиторий и динамический загрузчик
  плагинов.

## Рекомендуемая следующая задача

**TASK-011 — чистая операция стандартного поиска.** Принять
`CollectionSnapshot + SearchCriteria`, применить критерии конъюнктивно и вернуть
детерминированный результат без output mapping и CLI.

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
