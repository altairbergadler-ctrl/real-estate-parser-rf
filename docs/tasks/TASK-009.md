# TASK-009 — атомарная нормализация пакета и immutable collection

- Статус: завершено
- Рабочая ветка: `task/009-atomic-collection-snapshot`
- Целевая ветка: `main`

## Цель

Добавить чистую атомарную операцию
`SourceBatch → CollectionBuildSuccess(CollectionSnapshot) |
CollectionBuildFailure(tuple[ContractIssue, ...])`, которая нормализует
все снимки существующим поштучным normalizer, собирает все
независимо доказуемые ошибки и только при полном успехе строит
коллекцию с уникальными `PublicationRef`.

## Включённый объём

- Frozen/slots `CollectionSnapshot` с полным tuple `NormalizedListing` в
  порядке исходного `SourceBatch`.
- Минимальные immutable success/failure/result-типы полной операции.
- Поштучный вызов `normalize_fixture_snapshot` с явно переданными
  неизменяемыми `FixtureNormalizationRules`.
- Полный сбор и глобальная сортировка `NORMALIZATION` issues.
- Точная проверка уникальности `PublicationRef` только после полного
  успеха нормализации.
- `COLLECTION_CONFLICT/duplicate_publication_ref` для каждого повторного
  occurrence после первого, с расположением всей повторной записи.
- Прямые unit-тесты `SourceBatch` без JSON/Pydantic/filesystem и три
  ограниченных offline integration-сценария статических fixtures.

## Исключённый объём

- Path-level orchestration loader/adapter/normalizer/collection.
- Pydantic-граница criteria и канонический `SearchCriteria`.
- Search, matching, search ordering, output mapping, output validation,
  JSON-сериализация и пользовательский CLI.
- Физический объект недвижимости, fuzzy deduplication, история,
  persistence, ORM, база данных и cache.
- Реальные площадки, сеть, HTTP/HTML/browser/API, Docker, CI, ИИ,
  сигналы, уведомления, OpenClaw и Telegram.
- Изменение или регенерация fixtures и golden-файлов v1.

## Решения задачи

- Новая публичная операция принимает только `SourceBatch`; она не
  знает `Path`, JSON, Pydantic, loader, adapter, CLI, criteria и output.
- Один snapshot по-прежнему нормализует только существующий
  `normalize_fixture_snapshot`; его parsing, codes, locations и provenance не
  дублируются и не переименовываются.
- При любой normalization issue операция возвращает только atomic
  failure. Duplicate-check не выполняется, потому что полной
  последовательности `NormalizedListing` ещё нет.
- Уникальность сравнивает точную пару `(SourceId, PublicationId)`:
  source id побайтно, publication id с учётом регистра. Схожесть
  адресов и физических объектов не анализируется.
- Первое вхождение reference занимает seen-set; каждое последующее
  создаёт отдельный issue. Время наблюдения не влияет на выбор.
- Общий ключ сортировки issues остаётся: ранг документа,
  индекс записи, JSONPath, category, code.
- Нового долгосрочного архитектурного решения нет: владелец
  контракта, атомарность, уникальность и диагностики уже приняты
  ADR 0003 и 0004, поэтому новый ADR не создавался.

## Критерии готовности

- [x] Полный valid `SourceBatch` атомарно становится immutable
  `CollectionSnapshot` в исходном порядке.
- [x] Каждый snapshot обрабатывается existing single-snapshot normalizer без
  дублирования exact parsing и provenance.
- [x] Все независимые normalization issues собираются и глобально
  сортируются; collection и duplicate issues при них запрещены.
- [x] Каждое повторное вхождение `PublicationRef` после первого даёт
  точный устойчиво упорядоченный `COLLECTION_CONFLICT`.
- [x] Failure всегда непуст и не предоставляет partial listings или
  partial collection.
- [x] Разные source ids и publication ids с разным регистром не
  конфликтуют; unsupported currency остаётся успешным состоянием.
- [x] Три утверждённые static fixtures дают точные успех,
  `NORMALIZATION` failure и `COLLECTION_CONFLICT` failure.
- [x] Новых dependencies, fixture/golden changes и логики criteria/search/output/CLI
  нет.
- [x] Полная команда качества и обязательные точечные проверки
  успешны.

## Фактически выполненная работа

- Добавлен `real_estate_parser.collection` с immutable collection/result-типами
  и операцией `build_fixture_collection`.
- Операция обходит весь batch, собирает поштучные normalization
  failures и не выпускает наружу успешную часть batch.
- После полной нормализации builder сохраняет первое вхождение
  как кандидата и создаёт issue на каждый дальнейший дубль; при
  любом конфликте кандидаты не выдаются.
- Добавлены 14 сфокусированных тестов атомарности,
  immutability, порядка, происхождения, агрегации ошибок, точной
  уникальности, многократных дублей и трёх static fixtures.
- Публичные exports дополнены только контрактом TASK-009.

## Проверки

- `uv sync --frozen` — успешно; локальная среда CPython 3.14.7
  воспроизведена из lock-файла.
- `uv lock --check` — успешно; `uv.lock` согласован с
  `pyproject.toml`.
- `uv run pytest tests/test_fixture_collection.py -q` — успешно,
  `14 passed`.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  `152 passed` в обычном pytest и `44 passed` fixture catalog integrity.
- Импорт публичного API из установленного `src`-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно
  перед коммитом.
- Проверка выполнена на Windows. Linux в текущей среде не
  проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: build atomic normalized collection`. Точный SHA подтверждается Git
после создания коммита и не дублируется внутри его собственного
снимка.

`main` checkout’нута в другом worktree. Из назначенного worktree
merge не выполнялся, так как границы задачи запрещают изменять
другие worktree и ветки. Ветка TASK-009 оставлена чистой и готовой к
отдельному merge-коммиту в `main`.

## Следующая рекомендуемая задача

**TASK-010 — строгая граница `search-criteria@1` и канонический
`SearchCriteria`.** Прочитать один локальный criteria JSON, строго
валидировать Pydantic boundary и преобразовать его в neutral immutable
criteria без выполнения поиска.
