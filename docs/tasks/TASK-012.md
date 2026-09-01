# TASK-012 — чистое каноническое отображение результата поиска

- Статус: завершено
- Рабочая ветка: `task/012-search-result-mapping`
- Целевая ветка: `main`

## Цель

Реализовать чистую публичную операцию
`map_search_result(SearchResult) → SearchResultDocument`, которая отображает
готовый канонический результат поиска в обычное строго типизированное
immutable-дерево `search-result@1` со всеми состояниями полей и полным
provenance.

## Включённый объём

- Frozen/slots document-типы для корня, criteria, match, `PublicationRef`,
  mandatory traced value, `Present`, `Missing`, `Unsupported` и provenance.
- Отдельные `ProvidedProvenanceDocument` и `MissingProvenanceDocument`, чтобы
  отсутствие `raw_value` у `Missing` обеспечивалось структурой типа.
- Точное отображение трёх необязательных criteria; сортировка rooms в
  возрастающий tuple только внутри criteria document.
- Точные преобразования канонических wrapper-типов в строки, integer и площадь
  м² с двумя знаками без float.
- Полный перенос provenance именно соответствующего исходного поля.
- Сохранение уже установленного порядка `SearchResult.matches` без поиска и
  повторной сортировки.
- Прямые unit-тесты mapper и ограниченная offline integration существующих
  boundaries для четырёх утверждённых criteria fixtures.

## Исключённый объём

- Pydantic output model/validation и категория `OUTPUT_CONTRACT`.
- Преобразование document в dict/JSON, порядок JSON-ключей, escaping, UTF-8,
  LF и byte-exact сравнение golden.
- CLI, stdout/stderr, exit codes и path-level orchestration полного потока.
- Изменения search/filter/order, normalizer, collection, criteria boundary и
  source boundaries.
- Изменения fixtures v1, expected/golden, `pyproject.toml`, `uv.lock` и
  зависимостей.
- База данных, API, сеть, реальные площадки, Docker/CI, AI, сигналы, OpenClaw,
  Telegram и публикация.

## Решения задачи

- Document tree находится в отдельном нейтральном модуле и зависит только от
  готовых предметных типов поиска, criteria и нормализации.
- `SearchCriteriaDocument` сохраняет отсутствие как `None` только внутри
  immutable Python-типа; будущая внешняя граница обязана опускать такие поля.
- `ProvidedProvenanceDocument` используется mandatory values, `Present` и
  `Unsupported`; `reason_code` находится на уровне `UnsupportedDocument`, а не
  внутри provenance.
- `MissingDocument` не имеет `value`, его provenance отдельного типа не имеет
  `raw_value`; `UnsupportedDocument` не имеет канонического `value`.
- Площадь форматируется целочисленным `divmod` в строку с двумя знаками.
- Mapper обходит tuple matches ровно в его существующем порядке и не вызывает
  поиск, сортировку или внешние границы.
- Нового ADR нет: форма `search-result@1` уже утверждена ADR 0003, ADR 0004 и
  design-спецификациями.

## Критерии готовности

- [x] Публичный mapper возвращает `SearchResultDocument` версии
  `search-result@1` и точные канонические criteria/matches.
- [x] Корень, criteria, match, nested values/outcomes и оба provenance-типа
  frozen/slots; публичные последовательности представлены tuple.
- [x] Mandatory traced fields и все `Present`-типы отображаются с точными
  значениями и provenance.
- [x] `Missing` структурно не имеет `value` и `raw_value`; `Unsupported`
  структурно не имеет `value`, но имеет `raw_value` и `reason_code`.
- [x] Площадь, UTC RFC 3339, студия `0`, строки wrapper-типов и integer minor
  units отображаются без потери точности.
- [x] Все, частичные и отсутствующие criteria, пустой результат, заданный
  порядок matches и повторяемое равенство проверены.
- [x] Четыре static pipeline-сценария дают утверждённые документы по ids и
  состояниям без JSON serialization или golden-byte comparison.
- [x] Новых dependencies и изменений fixtures/golden нет.
- [x] Полная команда качества и обязательные точечные проверки успешны.

## Фактически выполненная работа

- Добавлен `real_estate_parser.search_result_mapping` с двенадцатью минимальными
  document-типами, закрытым outcome union и операцией `map_search_result`.
- Публичная поверхность пакета дополнена document-контрактом TASK-012.
- Добавлены 18 сфокусированных тестов точной формы, всех состояний,
  provenance, immutable/slots, criteria, порядка, детерминизма и четырёх
  offline fixture-сценариев.
- Документация состояния переведена на завершённую TASK-012 и единственный
  следующий шаг TASK-013.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run pytest tests/test_search_result_mapping.py -q` — успешно,
  `18 passed`.
- `uv run quality` — успешно: Ruff format-check, Ruff lint, strict mypy,
  `251 passed` в обычном pytest и `44 passed` fixture catalog integrity.
- Импорт публичного API из установленного `src`-layout — успешно.
- `git diff --check`, полный просмотр diff и `git status` — успешно перед
  коммитом.
- Проверка выполнена на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: map canonical search result document`. Точный SHA подтверждается Git
после создания коммита и не дублируется внутри его собственного снимка.

Из task-worktree `main` не изменялась; merge, force-push и публикация не
выполнялись. Ветка оставлена для отдельной проверки и merge координатором.

## Следующая рекомендуемая задача

**TASK-013 — строгая Pydantic output boundary и детерминированная UTF-8 JSON
serialization `SearchResultDocument`.** Добавить byte-exact проверку
существующих golden без CLI и path-level orchestration.
