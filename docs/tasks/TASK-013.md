# TASK-013 — строгая output boundary и канонический JSON

- Статус: завершено
- Рабочая ветка: `task/013-output-boundary-json`
- Целевая ветка: `main`

## Цель

Добавить отдельную строгую Pydantic output boundary, которая
атомарно проверяет готовый immutable `SearchResultDocument` TASK-012 и
сериализует его в канонические UTF-8 JSON bytes `search-result@1`
либо возвращает единственную безопасную ошибку output-контракта.

## Публичный API

- `serialize_search_result_document(document: SearchResultDocument) -> SearchResultSerializationResult`
- `SearchResultSerializationSuccess(json_bytes: bytes)`
- `SearchResultSerializationFailure(issues: tuple[ContractIssue, ...])`
- `SearchResultSerializationResult = SearchResultSerializationSuccess | SearchResultSerializationFailure`

Все публичные result-типы минимальные, frozen/slots. Успех содержит
только полные канонические bytes; failure не содержит частичных bytes.

## Включённый объём

- Отдельный внешний модуль с приватными strict Pydantic-моделями,
  точно зеркалящими корень, criteria, match, mandatory traced values,
  `PublicationRef` и два provenance-варианта `search-result@1`.
- `extra="forbid"`, строгие типы, точные `Literal` и discriminated
  states `present`/`missing`/`unsupported`.
- Структурный запрет `value` и `raw_value` для `Missing`,
  канонического `value` для `Unsupported` и обязательный `raw_value`
  для provided provenance.
- Атомарное преобразование любого невозможного или повреждённого
  внутреннего документа в ровно один
  `OUTPUT_CONTRACT/invalid_result_document/$` без Pydantic error,
  входных значений и traceback.
- Каноническая сериализация: UTF-8 без BOM, `sort_keys=True`, compact
  separators, standard JSON escaping, `allow_nan=False`, ровно один
  завершающий LF.
- Отсутствующие criteria полностью опускаются; успешный JSON не
  содержит `null`; `matches` сохраняют переданный порядок,
  `allowed_rooms` остаётся возрастающим массивом.
- Прямые unit-тесты strict validation, OUT-001, детерминизма,
  канонических bytes, immutable result-типов и порядка.
- Offline integration через существующий fixture pipeline до
  `SearchResultDocument`: byte-exact сравнение трёх утверждённых golden
  и семантическая проверка `criteria/partial-area.json`.
- Публичные экспорты и согласованная документация состояния.

## Исключённый объём

- CLI, argparse/Typer, stdout/stderr, exit codes.
- Path-level orchestration полного потока и чтение input paths новым API.
- Поиск, пересчёт значений, повторная сортировка matches и изменение
  mapper/search/criteria/normalization/source semantics.
- Запись JSON на диск production-кодом.
- Изменения `pyproject.toml`, `uv.lock`, dependencies, fixtures и golden.
- База, API, HTTP, HTML, реальные площадки, Docker, CI, AI, OpenClaw,
  Telegram и публикация.

## Решения задачи

- Новый ADR не создаётся: точная форма и байтовые правила уже
  утверждены ADR 0003, ADR 0004 и design-спецификациями.
- Output boundary проверяет и сериализует только готовое document tree
  TASK-012; она не зависит от search, normalizer, filesystem и CLI.

## Критерии готовности

- [x] Публичный API атомарно возвращает канонические bytes либо ровно одну
  безопасную `OUTPUT_CONTRACT/invalid_result_document/$` issue.
- [x] Strict private Pydantic-модели отвергают лишние поля,
  coercion и невозможные outcome/provenance-формы; absent criteria не
  попадают в JSON как `null`.
- [x] Сериализация совпадает с каноническими байтовыми правилами и
  не меняет порядок matches.
- [x] Три existing search golden проходят byte-exact через offline fixture
  pipeline; partial-area проходит семантическую проверку.
- [x] Result-типы frozen/slots; публичный импорт работает из installed
  src-layout.
- [x] `uv sync --frozen`, `uv lock --check`, точечные тесты,
  `uv run quality` и `git diff --check` успешны.
- [x] Dependencies, fixtures и golden не изменены; diff не содержит посторонних
  изменений.

## Фактически выполненная работа

- Добавлен `real_estate_parser.search_result_boundary` с приватными
  strict/frozen Pydantic-моделями точной формы `search-result@1`.
- Реализована атомарная операция
  `serialize_search_result_document` с минимальными frozen/slots
  success/failure/result-типами и безопасной единичной
  `OUTPUT_CONTRACT` issue.
- Каноническая serialization опускает absent criteria, сохраняет
  matches, выдаёт sorted compact JSON, UTF-8 без BOM и один LF.
- Добавлено 20 точечных тестов strict validation, OUT-001, всех
  states, детерминизма, canonical bytes, immutability, порядка, трёх
  byte-exact golden и partial-area semantics.
- Обновлены публичные экспорты и согласованная переносимая
  документация; новый ADR не потребовался.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run pytest tests/test_search_result_boundary.py -q` — успешно,
  `20 passed`.
- Публичный импорт четырёх имён API из installed src-layout — успешно.
- `uv run quality` — успешно: Ruff format-check, Ruff lint,
  strict mypy, `271 passed` в обычном pytest и `44 passed` fixture catalog
  integrity.
- Все три search golden сравнены как bytes через offline pipeline;
  `partial-area.json` проверен семантически.
- `git diff --check`, проверка неизменности dependencies/fixtures/golden
  и полный просмотр diff — успешно перед коммитом.
- Проверки выполнены на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: add canonical search result output boundary`. Точный SHA подтверждается Git
после создания коммита и не дублируется внутри его собственного
снимка.

## Следующий рекомендуемый шаг

После завершения TASK-013 допустим ровно один малый следующий шаг из
утверждённого плана: отдельная TASK-014 для CLI и итогового сквозного теста.
