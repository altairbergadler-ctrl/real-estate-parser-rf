# TASK-008 — детерминированная нормализация одного снимка

- Статус: завершено
- Рабочая ветка: `task/008-single-snapshot-normalization`
- Целевая ветка: `main`

## Цель

Добавить чистую библиотечную операцию
`SourcePublicationSnapshot → NormalizationSuccess(NormalizedListing) |
NormalizationFailure(tuple[ContractIssue, ...])` для ровно одного уже
адаптированного снимка фиктивного источника. Операция выполняет точные
преобразования, сохраняет происхождение каждого значения и различает состояния
`Present`, `Missing` и `Unsupported` без пакетной оркестрации, коллекции или
поиска.

## Включённый объём

- Обычные immutable value objects `SourceUrl`, `ObservedAt`, `LocationText`,
  `MoneyAmount`, `Currency`, `Area`, `RoomCount` и
  `NormalizationRuleVersion`.
- `TracedValue`, отдельные `ValueProvenance`, `MissingProvenance`,
  `UnsupportedProvenance` и закрытый `FieldOutcome`.
- Полный `NormalizedListing`, атомарные success/failure/result-типы и
  неизменяемый типизированный набор правил фиктивного источника v1.
- Строгий RFC 3339 с обязательными секундами и offset, UTC-приведение и
  сохранение микросекунд.
- Unicode whitespace normalization, exact integer arithmetic для денег и
  площади, парная семантика цены/валюты и точные правила комнат.
- Стабильные `NORMALIZATION` issues, сбор независимо доказуемых ошибок одного
  снимка и общий порядок диагностик.
- Прямые unit-тесты без loader/adapter и один ограниченный offline integration
  test существующей цепочки до поштучного вызова normalizer.
- Обновление состояния и документации проекта.

## Исключённый объём

- Нормализация полного `SourceBatch` и общий orchestration loader/adapter/
  normalizer.
- `CollectionSnapshot`, проверка duplicate `PublicationRef`, пакетная
  атомарность и поведение duplicate fixture.
- Критерии, поиск, output mapping/validation/serialization и пользовательский
  CLI.
- Физический объект, дедупликация реальных объектов, история и хранилище.
- Реальные площадки, HTTP, HTML, browser automation, API и база данных.
- Docker, CI, ИИ, сигналы, уведомления, OpenClaw и Telegram.
- Изменение или регенерация fixtures и golden-файлов.

## Решения задачи

- Нейтральные входные типы остаются в `source_batch`; канонические типы,
  provenance, outcomes и чистая операция размещены в независимом от Pydantic,
  JSON и filesystem модуле `normalization`.
- `ObservedAt` принимает только заданное подмножество RFC 3339: обязательные
  секунды, `Z` или `±HH:MM`, 0–6 цифр дробной части, реальные календарные дата,
  время и offset. После разбора значение всегда хранится как aware UTC
  `datetime`; каноническое представление имеет шесть микросекунд и `Z`.
- Деньги и площадь масштабируются разбором ASCII-цифр в целое значение. Float,
  Decimal, округление и зависимость от locale не используются. Числа за
  контрактным пределом определяются до потенциально неограниченного `int()`.
- Каждый `Present`, `Missing` и `Unsupported` получает отдельный provenance.
  Reference использует исходный `publication_id` и структурно производный путь
  записи; остальные пути переносятся непосредственно из `RawField` или
  `MissingField`. `MissingProvenance` конструктивно не имеет `raw_value`.
- Для raw `rooms` общий инвариант «канонический `0` означает только явно
  указанную студию» уточняет source-specific правило v1: только токен `studio`
  даёт `RoomCount(0)`, числовые строки допустимы в диапазоне `1..99`, а `"0"`
  и его варианты с ведущими нулями дают `invalid_value`. Это локальное
  уточнение фиктивного источника, а не правило будущих реальных адаптеров.
- Неподдерживаемая корректная валюта, включая `USD`, является успешным
  `Unsupported` с `unsupported_currency`; цена при этом остаётся `Present`.
- Новый ADR не создавался: типы, владелец операции, provenance, состояния,
  точная арифметика, атомарность и порядок ошибок уже приняты ADR 0003 и 0004.

## Критерии готовности

- [x] Один валидный snapshot детерминированно превращается в полный immutable
  `NormalizedListing`.
- [x] Канонические value objects защищают единицы и диапазоны; время хранится в
  UTC без потери микросекунд.
- [x] `Present`, `Missing` и `Unsupported` различаются типами, а не `None`,
  нулём или исключением.
- [x] Каждое значение и состояние имеет полное отдельное происхождение и точную
  версию правила; у `Missing` нет вымышленного `raw_value`.
- [x] NRM-001…NRM-008 имеют точные code/location; USD успешен как
  `Unsupported`.
- [x] Несколько независимых ошибок стабильно сортируются, failure непуст и не
  предоставляет partial listing.
- [x] Unit-тесты создают `SourcePublicationSnapshot` напрямую; единственный
  integration test не создаёт batch normalizer или collection.
- [x] Новых зависимостей, fixture/golden changes и логики TASK-009 нет.
- [x] Полная команда качества и обязательные точечные проверки успешны.

## Фактически выполненная работа

- Добавлен `real_estate_parser.normalization` с каноническими value objects,
  тремя provenance-формами, outcome/result-контрактами и явно экспортированным
  `FIXTURE_NORMALIZATION_RULES_V1` с восемью утверждёнными версиями.
- Реализован `normalize_fixture_snapshot(snapshot, rules)` для одного снимка:
  точное UTC-время, location whitespace, price/currency, площадь и комнаты.
- Реализованы полное происхождение reference/URL/time и каждого optional state,
  `Missing` без raw value и `Unsupported` с raw value/reason code.
- Добавлены прямые проверки comprehensive, missing, currency и studio снимков,
  RFC 3339, Unicode, диапазонов, точности, парных денег, сортировки,
  атомарности, неизменяемости и всех сценариев NRM.
- Добавлен один ограниченный integration test: valid comprehensive batch и
  второй снимок `invalid/normalization-atomic.json` проходят существующие
  loader/adapter с отдельным вызовом normalizer для каждого выбранного
  snapshot, но без batch orchestrator.
- Публичная поверхность пакета дополнена только типами и операцией текущей
  границы.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  `138 passed` в обычном pytest и `44 passed` fixture catalog integrity.
- `uv run pytest tests/test_fixture_normalization.py -q` — успешно,
  `75 passed`.
- Импорт публичного API из установленного src-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: normalize one fixture publication snapshot`. Точный SHA подтверждается
Git после создания коммита и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

**TASK-009 — атомарная нормализация пакета и immutable collection.** Принять
полный `SourceBatch`, нормализовать все snapshots, собрать все независимо
доказуемые ошибки и только при полном успехе построить immutable
`CollectionSnapshot` с проверкой уникальности `PublicationRef`. Не добавлять
criteria, search, output mapping, serialization, пользовательский CLI или
реальные источники.
