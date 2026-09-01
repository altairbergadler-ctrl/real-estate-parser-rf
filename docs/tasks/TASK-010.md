# TASK-010 — строгая граница search criteria

- Статус: завершено
- Рабочая ветка: `task/010-search-criteria-boundary`
- Целевая ветка: `main`

## Цель

Реализовать публичную библиотечную операцию
`Path → UTF-8 → JSON → strict Pydantic boundary → SearchCriteria` для одного
документа `search-criteria@1`, не выполняя поиск.

## Включённый объём

- Строгие Pydantic-модели корня, `criteria` и `maximum_price`, а также
  полный запрет extra, coercion и явного `null` на границе.
- Точные правила версии, RUB/amount minor, десятичной площади в сотых
  м² без округления и уникальных комнат `0..99`.
- Neutral frozen/slots `Money` и `SearchCriteria` из существующих `MoneyAmount`,
  `Currency`, `Area` и `RoomCount`.
- Frozen/slots success/failure/result с атомарным непустым tuple
  `ContractIssue` и без partial criteria.
- Стабильные `INPUT_SYNTAX`/`INPUT_SCHEMA` codes, структурные
  `InputLocation(document="criteria", ...)` и общий порядок диагностик.
- Offline pytest для четырёх статических criteria fixtures и полной
  граничной матрицы TASK-010.

## Исключённый объём

- Совместное чтение listings/criteria и path-level orchestration полного потока.
- Изменение коллекции, search/matching/sorting, `SearchMatch`/`SearchResult`.
- Output mapper, output Pydantic validation, JSON serialization, golden и CLI.
- Изменение fixtures v1, expected/golden, lock-файла и зависимостей.
- БД, API, сеть, реальные площадки, Docker/CI, AI, сигналы, OpenClaw,
  Telegram и публикация.

## Решения задачи

- Канонические типы и типы результата живут в `search_criteria`, а
  filesystem/JSON/Pydantic код — в `search_criteria_boundary`.
- Pydantic проверяет структуру и строгие JSON-типы; содержательные
  правила критериев собираются отдельно, чтобы не терять независимые ошибки
  и не наследовать порядок библиотеки.
- Десятичная площадь разбирается как ASCII-цифры без float и округления;
  дополнительные нулевые знаки не меняют точное значение.
- `allowed_rooms` становится `frozenset[RoomCount]`; входной порядок не
  входит в каноническую модель, а дубли отклоняются на внешней границе.
- Ошибки файла и UTF-8 остаются `OSError`/`UnicodeError`; нового
  долгосрочного error contract и ADR задача не вводит.

## Критерии готовности

- [x] Четыре static criteria fixtures дают точные канонические значения.
- [x] Отсутствие, strict integer, null, extra/missing/type, version и syntax
  проверены точными issues.
- [x] Границы amount/area/rooms, RUB, пустой и дублированный
  `allowed_rooms`, `47.125` и `47.120` проверены.
- [x] Несколько независимых ошибок возвращаются атомарно и в общем
  стабильном порядке.
- [x] I/O policy не утекает в `ContractIssue`; success/failure не содержат
  partial результата.
- [x] Публичный API доступен из установленного src-layout package.
- [x] Новых dependencies, fixture/golden/lock changes и логики поиска нет.

## Фактически выполненная работа

- Добавлены `Money`, `SearchCriteria`, `SearchCriteriaLoadSuccess`/
  `SearchCriteriaLoadFailure` и публичная `load_search_criteria(Path)`.
- Граница строго различает JSON-типы и недопустимые значения
  критериев, собирает независимые issues и сортирует их независимо от
  Pydantic.
- Добавлены 68 сфокусированных тестов канонических типов, четырёх
  fixtures, негативной матрицы, атомарности, порядка и I/O policy.
- Публичные exports дополнены только типами и операцией TASK-010.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run pytest tests/test_search_criteria_boundary.py -q` — успешно,
  `68 passed`.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  `220 passed` pytest и `44 passed` fixture catalog integrity.
- Импорт публичного API из установленного src-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: add strict search criteria boundary`. Точный SHA подтверждается Git после
создания коммита и не дублируется внутри его собственного снимка.

Из task-worktree `main` не изменялась; merge, force-push и публикация не
выполнялись. Ветка оставлена для отдельной проверки и merge координатором.

## Следующая рекомендуемая задача

**TASK-011 — чистая операция стандартного поиска.** Принять
`CollectionSnapshot + SearchCriteria`, применить критерии конъюнктивно и вернуть
детерминированный результат без output mapping и CLI.
