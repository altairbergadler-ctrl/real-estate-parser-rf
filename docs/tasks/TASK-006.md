# TASK-006 — граничная загрузка локального пакета публикаций v1

- Статус: завершено
- Рабочая ветка: `task/006-local-source-batch-boundary`
- Целевая ветка: `main`

## Цель

Создать внешнюю библиотечную границу `Path → UTF-8 → JSON → строгая Pydantic
schema → ValidatedSourceBatch` для одного локального документа
`fixture-source-batch@1`, не начиная source-specific адаптацию, нормализацию или
поиск.

## Включённый объём

- Строгие Pydantic-модели корня и записи `fixture-source-batch@1` с запретом
  лишних полей, преобразования типов и явного `null`.
- Точное правило версии документа и непустого массива `listings`.
- Чтение ровно одного явно переданного `pathlib.Path` как UTF-8 и отдельное
  распознавание JSON syntax и schema validation.
- Обычные неизменяемые типизированные объекты `InputLocation`,
  `ValidatedSourceField`, `MissingSourceField`, `ValidatedSourceListing` и
  `ValidatedSourceBatch` без зависимости от Pydantic, JSON и filesystem.
- Закрытый типизированный результат `SourceBatchLoadSuccess |
  SourceBatchLoadFailure` и непустая immutable-последовательность
  `ContractIssue` при ожидаемой ошибке содержимого.
- Собственное отображение типов и locations Pydantic в стабильные коды и
  структурные расположения, а также независимая сортировка нескольких ошибок.
- Offline pytest-проверки статических fixtures и параметризованных мутаций
  TASK-004.

## Исключённый объём

- Проверка `source = fixture_portal`, publication id и URL фиктивным source
  adapter.
- Разбор или нормализация времени, пробелов, денег, валюты, площади и комнат.
- Предметные `SourceId`, `PublicationRef`, `SourcePublicationSnapshot`,
  нормализованные сущности, коллекция, дедупликация и поиск.
- Документы критериев и результата, пользовательский CLI и полный сквозной
  сценарий.
- Реальные площадки, сеть, браузер, БД, API, Docker, CI, AI, сигналы,
  уведомления, OpenClaw и Telegram.
- Изменение или перегенерация fixtures и golden-файлов v1.

## Решения задачи

- Нейтральные типы размещены в `real_estate_parser.source_batch`, а внешний
  filesystem/JSON/Pydantic-код — в `real_estate_parser.fixture_source_batch`.
  Направление зависимости остаётся к нейтральному контракту.
- Каждое предоставленное source-поле хранится как точная строка вместе с
  `InputLocation`. Отсутствующее необязательное поле хранится отдельным
  `MissingSourceField` с ожидаемым расположением; `None` для этого не
  используется.
- `InputLocation` структурно хранит документ, индекс записи и source path;
  `json_path` строится только из этих данных. Абсолютный путь файла в контракт
  не входит.
- Pydantic используется только как внутренняя boundary-модель. В публичный
  результат не выходят `ValidationError`, пользовательские сообщения,
  входные значения или порядок ошибок Pydantic.
- Ошибки доступа к файлу и декодирования UTF-8 остаются операционными
  исключениями (`OSError`/`UnicodeError`), поскольку ADR 0001–0004 не задают
  для них стабильную категорию. Они не маскируются под ошибку JSON syntax или
  schema; нового долгосрочного error contract и ADR задача не вводит.

## Критерии готовности

- [x] Валидный comprehensive batch превращается в полный неизменяемый
  `ValidatedSourceBatch`, порядок четырёх записей и сырые строки сохранены.
- [x] Строгие строки, запрет extra/null, точная версия и непустой `listings`
  соблюдены.
- [x] Предоставленное поле и `MissingSourceField` различаются типом и оба
  сохраняют структурный `InputLocation`.
- [x] Syntax/schema ошибки возвращаются типизированно, атомарно и в стабильном
  порядке; Pydantic/JSON exceptions не выходят для ожидаемых ошибок содержимого.
- [x] `schema-multiple-errors.json` точно совпадает с существующим diagnostic
  oracle.
- [x] Source-specific и normalization-невалидности будущих задач остаются
  исходными строками и не классифицируются на этой границе.
- [x] Новых зависимостей и логики TASK-007 нет; fixtures/golden не изменены.
- [x] Полная команда качества и обязательные точечные проверки успешны.

## Фактически выполненная работа

- Добавлен публичный `load_fixture_source_batch(path: Path)` с чтением одного
  файла, строгим JSON-разбором и полной schema validation.
- Добавлены frozen/slots dataclasses и tuple-последовательности для locations,
  полей, missing-state, listing, batch, issues и атомарного результата.
- Реализовано явное преобразование Pydantic error type/location в
  `missing_field`, `wrong_type`, `extra_field`, `invalid_value` и
  `unsupported_schema_version` без разбора текста исключения.
- Добавлены 19 сфокусированных тестов boundary: положительный пакет,
  неизменяемость, syntax, точный multi-error oracle, SCH-001…SCH-004, version,
  empty-list, null/Missing, атомарность, отложенные правила и I/O policy.
- Публичные типы и loader экспортированы из устанавливаемого
  `real_estate_parser` package.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  обычный pytest и fixture catalog integrity.
- `uv run pytest tests/test_fixture_source_batch.py -q` — успешно, `19 passed`.
- Импорт публичного API из установленного src-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: add strict fixture source batch boundary`. Точный SHA подтверждается Git
после создания коммита и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

**TASK-007 — фиктивный source adapter.** Принять `ValidatedSourceBatch`,
проверить `source = fixture_portal`, правила `publication_id` и URL и вернуть
либо полный нейтральный `SourceBatch`, либо упорядоченные ошибки
`SOURCE_ADAPTER`, не выполняя нормализацию, коллекцию или поиск.
