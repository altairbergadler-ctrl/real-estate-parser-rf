# TASK-007 — фиктивный source adapter

- Статус: завершено
- Рабочая ветка: `task/007-fixture-source-adapter`
- Целевая ветка: `main`

## Цель

Добавить чистую, офлайн и детерминированную операцию
`ValidatedSourceBatch → FixtureSourceAdaptationSuccess(SourceBatch) |
FixtureSourceAdaptationFailure(tuple[ContractIssue, ...])`, которая применяет
только правила источника `fixture_portal` и не начинает нормализацию.

## Включённый объём

- Обычные строго типизированные immutable-типы `SourceId`, `PublicationId`,
  `PublicationRef`, `RawField`, `MissingField`, `SourcePublicationSnapshot` и
  упорядоченный `SourceBatch`.
- Атомарные success/failure/result-типы фиктивной адаптации.
- Каноническое назначение `SourceId = fixture_portal` и точная проверка внешнего
  `batch.source`.
- Source-specific правила `publication_id` и исходного HTTPS URL без сетевого
  разрешения и новых зависимостей.
- Прямой перенос provided/missing полей и структурных `InputLocation` в
  нейтральные слоты без преобразования значений.
- Стабильные `SOURCE_ADAPTER` issues и их независимая сортировка по общему ключу.
- Прямые unit-тесты адаптера без JSON/Pydantic/filesystem и один offline
  интеграционный тест существующего loader с адаптером.
- Обновление состояния проекта и документации задачи.

## Исключённый объём

- Изменение Path/JSON/Pydantic-границы и общий orchestration loader + adapter.
- Любая нормализация времени, пробелов, денег, валюты, площади или комнат.
- `Provenance`, `Present`, `Unsupported`, нормализованные типы и версии правил.
- Атомарная коллекция, duplicate detection, критерии, поиск, output mapper,
  сериализация и пользовательский CLI.
- Физический объект недвижимости, история, хранилище, реальные площадки, сеть,
  HTTP/HTML/browser automation, API, БД, Docker, CI, ИИ, сигналы, уведомления,
  OpenClaw и Telegram.
- Изменение или перегенерация fixtures и golden-файлов v1.

## Решения задачи

- Нейтральные контракты размещены рядом с существующим предадаптерным
  контрактом в `real_estate_parser.source_batch`; реализация конкретного
  источника изолирована в `real_estate_parser.fixture_source_adapter`.
- `SourceId` и `PublicationId` являются frozen value objects и сами защищают
  общий ASCII-формат. Адаптер преобразует невалидный внешний identifier в
  стабильную диагностику, не выпуская `ValueError` наружу.
- URL разбирается только стандартным `urllib.parse.urlsplit`; схема сравнивается
  с HTTPS по стандартной семантике URL, а исходная строка сохраняется без
  переписывания.
- Проверка URL разделена на независимую структуру offer URL и зависимое равенство
  идентификатору записи. Если `publication_id` невалиден, равенство не
  проверяется и ADP-001 не получает каскадную ошибку; самостоятельно невалидная
  структура URL по-прежнему создаёт ADP-002.
- Адаптер может внутренне обойти все записи для сбора независимых ошибок, но при
  любой ошибке возвращает только failure без доступного частичного `SourceBatch`.
- Повторяющийся `PublicationRef` намеренно не проверяется: это ответственность
  будущей атомарной коллекции.
- Нового долгосрочного архитектурного решения нет; ADR 0003 и 0004 уже задают
  типы, владельца границы, атомарность и порядок ошибок, поэтому новый ADR не
  создавался.

## Критерии готовности

- [x] Адаптер принимает только `ValidatedSourceBatch` и не зависит от loader,
  Pydantic, JSON, filesystem, CLI, сети или базы данных.
- [x] Source, publication id и URL проверяются по утверждённой спецификации.
- [x] Валидный вход даёт полный immutable `SourceBatch` в исходном порядке.
- [x] Сырые строки, регистр, пробелы и объекты `InputLocation` переносятся без
  изменения; provided и missing различаются отдельными типами.
- [x] Ошибки атомарны, типизированы, не содержат входных значений и стабильно
  отсортированы.
- [x] ADP-001a/b, ADP-002a/b и ADP-003, URL matrix и составные ошибки доказаны
  прямыми тестами.
- [x] Неполная денежная пара и normalization-specific строки успешно
  переносятся; duplicate publication id не отклоняется адаптером.
- [x] Нормализация, коллекция и поиск не начаты; dependencies и fixtures/golden
  не изменены.
- [x] Полная команда качества и обязательные точечные проверки успешны.

## Фактически выполненная работа

- Реализованы минимальные value objects, нейтральные raw/missing поля, снимок,
  пакет и закрытый результат адаптации на frozen/slots dataclasses и tuples.
- Добавлен публичный `adapt_fixture_source_batch(batch)` с точными правилами
  `fixture_portal`, publication id и исходного URL.
- Реализован буквальный перенос `url → source_url`, `price_major →
  price_amount`, `total_area_sqm → total_area` и остальных полей без разбора.
- Добавлены сфокусированные прямые тесты валидного comprehensive batch,
  идентичности, границ ID, URL matrix, raw/missing, отложенной нормализации,
  атомарности, сортировки и duplicate boundary.
- Добавлен один offline integration test статической valid fixture через
  существующий loader и новый adapter.
- Публичные exports и переносимая документация проекта приведены в соответствие
  реализованной границе.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  обычный pytest и fixture catalog integrity.
- `uv run pytest tests/test_fixture_source_adapter.py -q` — успешно, `43 passed`.
- Отдельный импорт публичного API из установленного src-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: add fixture source adapter`. Точный SHA подтверждается Git после создания
коммита и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

**TASK-008 — детерминированная нормализация одного снимка.** Принять один
`SourcePublicationSnapshot` и вернуть `NormalizedListing` либо упорядоченные
ошибки `NORMALIZATION`, выполняя exact parsing и формируя происхождение и
состояния `Present`/`Missing`/`Unsupported`. Не начинать атомарную коллекцию,
duplicate detection или поиск.
