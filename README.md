# Парсер недвижимости

Модульное приложение для поиска и анализа объявлений о недвижимости по России. Проект задуман как независимое ядро с подключаемыми источниками, правилами нормализации, устранением дублей, поиском, доказательными сигналами и внешними интеграциями.

Сейчас в репозитории находится документальный фундамент, проект первого локального сквозного среза, спецификация его предметной модели, полностью вымышленные JSON-фикстуры, минимальный устанавливаемый Python-каркас, строгая граница `fixture-source-batch@1`, чистый фиктивный source adapter, детерминированная нормализация, атомарная immutable-коллекция, строгая граница `search-criteria@1`, чистый детерминированный стандартный поиск, каноническое immutable-представление `search-result@1` и отдельная строгая output boundary для его атомарной сериализации в канонические UTF-8 JSON bytes. Path-level orchestration, пользовательский CLI, база данных, API, интерфейс, парсеры реальных площадок, ИИ и интеграции ещё не реализованы.

## С чего начать

1. Прочитать [PROJECT.md](PROJECT.md) — назначение, сценарии и границы продукта.
2. Прочитать [ARCHITECTURE.md](ARCHITECTURE.md) — архитектурные принципы и границы модулей.
3. Прочитать [ROADMAP.md](ROADMAP.md) — последовательность небольших задач.
4. Прочитать [CHECKPOINT.md](CHECKPOINT.md) — текущее состояние и следующий шаг.
5. Перед изменениями выполнить правила из [AGENTS.md](AGENTS.md).

## Проектная документация

- `docs/tasks/` — постановки, критерии готовности и результаты задач.
- `docs/decisions/` — существенные архитектурные решения и их обоснования.
- `docs/design/` — подробные проекты ограниченных сквозных сценариев.

Предметные типы, состояния и границы первого среза описаны в [DOMAIN-MODEL-AND-CONTRACTS.md](docs/design/DOMAIN-MODEL-AND-CONTRACTS.md).

Точные входные документы, матрица сценариев и правила golden-файлов описаны в [TEST-STRATEGY-AND-FIXTURES.md](docs/design/TEST-STRATEGY-AND-FIXTURES.md); фактические данные перечислены в [manifest fixtures v1](tests/fixtures/v1/MANIFEST.md).

Актуальное состояние определяется файлами репозитория и историей Git, а не историей чатов.

## Локальная разработка

Требуется установленный `uv`. Версия CPython и все зависимости воспроизводятся из
файлов проекта:

```text
uv sync --frozen
```

Весь текущий репозиторий проверяется одной переносимой командой:

```text
uv run quality
```

Команда только проверяет форматирование, линтинг, строгие типы, тесты и каталог
fixtures v1. Она не исправляет файлы и не обновляет эталоны или lock-файл.

## Граничная загрузка пакета публикаций

Публичная функция `load_fixture_source_batch(path: pathlib.Path)` читает ровно
один локальный UTF-8 JSON-файл и возвращает либо полный неизменяемый
`ValidatedSourceBatch`, либо типизированную ошибку содержимого. Она проверяет
только синтаксис и строгую структуру `fixture-source-batch@1`; содержательные
правила фиктивного источника применяет отдельный адаптер ниже, а нормализация
остаётся следующей отдельной задачей.

## Фиктивный source adapter

Публичная функция `adapt_fixture_source_batch(batch: ValidatedSourceBatch)`
принимает только уже структурно проверенный пакет. Она назначает канонический
`SourceId = fixture_portal`, проверяет source-specific правила
`publication_id` и URL и возвращает либо полный неизменяемый `SourceBatch`,
либо атомарную непустую последовательность ошибок `SOURCE_ADAPTER`.

Адаптер не читает файлы, не зависит от Pydantic и не нормализует время, пробелы,
деньги, валюту, площадь или комнаты. Исходные строки и `InputLocation`
переносятся в нейтральные снимки без изменения.

## Нормализация одного снимка

Публичная функция
`normalize_fixture_snapshot(snapshot, FIXTURE_NORMALIZATION_RULES_V1)` принимает
ровно один уже адаптированный `SourcePublicationSnapshot` и возвращает
либо полный immutable `NormalizedListing`, либо упорядоченные ошибки
`NORMALIZATION` без partial listing. Операция не знает batch, файлы, JSON,
Pydantic, CLI, сеть, базу данных или текущее время.

## Атомарная коллекция

Публичная функция
`build_fixture_collection(batch, FIXTURE_NORMALIZATION_RULES_V1)` принимает
полный `SourceBatch`, нормализует каждый снимок существующим
normalizer и возвращает либо полный immutable `CollectionSnapshot`, либо
непустую упорядоченную последовательность `NORMALIZATION` или
`COLLECTION_CONFLICT` issues. Частичные listings и коллекция наружу не
выдаются; входной порядок сохраняется.

## Граница критериев поиска

Публичная функция `load_search_criteria(path: pathlib.Path)` читает ровно
один UTF-8 JSON-документ `search-criteria@1` и возвращает либо
полный neutral immutable `SearchCriteria`, либо атомарную непустую
последовательность `ContractIssue`. Операция не выполняет поиск и
не передаёт в канонические типы Pydantic, JSON, filesystem или путь файла.

## Стандартный поиск

Публичная функция `search_collection(collection, criteria)` принимает только
готовые immutable `CollectionSnapshot` и `SearchCriteria`, применяет заданные
критерии конъюнктивно и всегда возвращает успешный immutable `SearchResult`.
Каждый `SearchMatch` ссылается на исходный `NormalizedListing`, а совпадения
сортируются канонически независимо от порядка коллекции. Операция не знает
Pydantic, JSON, filesystem, output mapping или CLI.

## Каноническое отображение результата

Публичная функция `map_search_result(result)` принимает только готовый
immutable `SearchResult` и возвращает строго типизированное frozen/slots-дерево
`SearchResultDocument` версии `search-result@1`. Оно сохраняет порядок matches,
все `Present`/`Missing`/`Unsupported` и provenance каждого поля. Mapper не знает
Pydantic, JSON, bytes, filesystem, CLI или текущее время.

## Output boundary результата

Публичная функция `serialize_search_result_document(document)` принимает
только готовый `SearchResultDocument`, строго проверяет его внешнюю
форму и возвращает `SearchResultSerializationSuccess(json_bytes)` либо
`SearchResultSerializationFailure(issues)`. Успешные bytes имеют стабильный
порядок ключей, compact JSON, UTF-8 без BOM и ровно один завершающий
LF. Невозможный document даёт одну безопасную root issue без
частичных bytes. Операция не читает и не пишет файлы, не выполняет
поиск и не сортирует matches.
