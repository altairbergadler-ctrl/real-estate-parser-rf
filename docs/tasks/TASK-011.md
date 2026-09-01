# TASK-011 — чистая операция стандартного поиска

- Статус: завершено
- Рабочая ветка: `task/011-standard-search`
- Целевая ветка: `main`

## Цель

Реализовать чистую публичную операцию
`search_collection(CollectionSnapshot, SearchCriteria) → SearchResult`, которая
применяет готовые канонические критерии к уже построенной коллекции и всегда
возвращает успешный детерминированный immutable результат.

## Включённый объём

- Минимальные frozen/slots `SearchMatch` и `SearchResult` в нейтральном модуле
  поиска.
- Ссылка каждого match на исходный `NormalizedListing` без копирования полей и
  потери provenance.
- Конъюнктивное применение `maximum_price`, `minimum_total_area` и
  `allowed_rooms`; отсутствие критерия не ограничивает результат.
- Обычное несовпадение `Missing`/`Unsupported` только при заданном критерии
  соответствующего поля.
- Точный canonical ordering по состоянию полной денежной пары, currency/amount,
  `SourceId`, case-sensitive `PublicationId`, `ObservedAt` и `SourceUrl`.
- Успешный пустой результат и fail-fast `ValueError` для невозможной внутренней
  пары `Present + Missing` без нового error contract.
- Прямые unit-тесты без Pydantic/JSON/filesystem и ограниченная offline
  интеграция существующих boundaries на утверждённых static fixtures.

## Исключённый объём

- Output mapping, `SearchResultDocument`, Pydantic output boundary, JSON
  serialization, golden comparison и CLI.
- Совместный path-level workflow и orchestration полного среза.
- Изменения loader, source adapter, normalizer, collection builder и criteria
  boundary, кроме минимального публичного импорта поиска.
- Изменения fixtures v1, expected/golden, `pyproject.toml`, `uv.lock` и
  зависимостей.
- Валютная конвертация, геопоиск, fuzzy matching, scoring и дедупликация.
- База данных, API, сеть, реальные площадки, Docker/CI, AI, сигналы, OpenClaw,
  Telegram и публикация.

## Решения задачи

- `SearchResult` хранит тот же immutable `SearchCriteria`, который был передан
  операции, и tuple `SearchMatch`; каждый match хранит исходный listing по
  ссылке.
- Цена совпадает только при двух `Present`, равной currency и amount не выше
  maximum; площадь и комнаты требуют соответствующий `Present`.
- Студия `RoomCount(0)` сравнивается как обычное каноническое значение.
- Для сортировки полная денежная пара имеет ранг `Present`, `Missing`,
  `Unsupported`; наличие любой `Unsupported` составляющей делает пару
  `Unsupported`.
- ASCII-идентификаторы, currency и URL явно сравниваются как bytes; время — как
  канонический UTC `datetime`.
- Корректный normalizer не создаёт `Present + Missing`; при прямом создании
  такого невозможного listing поиск локально завершает работу `ValueError`.
- Нового ADR нет: модель, правила совпадения и порядок уже утверждены ADR 0003,
  ADR 0004 и предметной спецификацией.

## Критерии готовности

- [x] Каждый критерий отдельно проверен вместе с точным равенством на границе.
- [x] Студия `0` и конъюнкция всех трёх критериев проверены.
- [x] Отсутствие всех критериев возвращает все записи.
- [x] `Missing` и `Unsupported` исключают только при соответствующем заданном
  критерии; unsupported currency не совпадает с заданной ценой.
- [x] Пустой результат остаётся успешным.
- [x] Результат immutable, сохраняет исходный listing и полный provenance.
- [x] Полный составной порядок и независимость от порядка коллекции проверены.
- [x] Четыре утверждённых static criteria fixtures дают точные tuples
  publication ids без обращения к output goldens.
- [x] Новых dependencies, fixture/golden changes и логики output/CLI нет.
- [x] Полная команда качества и обязательные точечные проверки успешны.

## Фактически выполненная работа

- Добавлен `real_estate_parser.search` с `SearchMatch`, `SearchResult` и
  `search_collection`.
- Операция фильтрует только по заданным критериям, затем сортирует совпадения
  полным каноническим ключом и возвращает новые match wrappers вокруг исходных
  listings.
- Публичная поверхность пакета дополнена только тремя именами TASK-011.
- Добавлены 13 сфокусированных тестов чистой операции, невозможного внутреннего
  состояния и четырёх offline fixture-сценариев.
- Документация состояния переведена на завершённую TASK-011 и единственный
  рекомендуемый следующий шаг TASK-012.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run pytest tests/test_standard_search.py -q` — успешно, `13 passed`.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  `233 passed` pytest и `44 passed` fixture catalog integrity.
- Импорт публичного API из установленного `src`-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: add deterministic standard search`. Точный SHA подтверждается Git после
создания коммита и не дублируется внутри его собственного снимка.

Из task-worktree `main` не изменялась; merge, force-push и публикация не
выполнялись. Ветка оставлена для отдельной проверки и merge координатором.

## Следующая рекомендуемая задача

**TASK-012 — чистое каноническое отображение `SearchResult` в immutable
`SearchResultDocument` со всеми состояниями и provenance, без Pydantic output
validation, JSON serialization и CLI.**
