# Manifest фикстур v1

Каталог содержит только полностью вымышленные статические данные для [стратегии TASK-004](../../../docs/design/TEST-STRATEGY-AND-FIXTURES.md). Домены оканчиваются на `.example`; даты и значения фиксированы; сеть, текущее время и случайность не используются.

## Файлы и сценарии

| Файл | Сценарий | Будущий уровень | Oracle |
| --- | --- | --- | --- |
| [valid/listings-comprehensive.json](valid/listings-comprehensive.json) | E2E-ALL-001, SEARCH-PARTIAL-001, E2E-NONE-001, E2E-EMPTY-001 | CLI integration, normalization, search | Совместно с одним из criteria и соответствующим expected |
| [criteria/all-three.json](criteria/all-three.json) | E2E-ALL-001 | Boundary, search, CLI integration | [expected/search-all-three.json](expected/search-all-three.json) |
| [criteria/partial-area.json](criteria/partial-area.json) | SEARCH-PARTIAL-001 | Boundary, search | Единственный `PublicationRef`: `fixture_portal/currency-004` |
| [criteria/none.json](criteria/none.json) | E2E-NONE-001 | Boundary, search, output | [expected/search-none.json](expected/search-none.json) |
| [criteria/no-match.json](criteria/no-match.json) | E2E-EMPTY-001, SRCH-EMPTY-001 | Boundary, search, CLI integration | [expected/search-no-match.json](expected/search-no-match.json) |
| [invalid/syntax-truncated.json](invalid/syntax-truncated.json) | SYN-001 | JSON syntax boundary | Должен не разбираться; `INPUT_SYNTAX/invalid_json/$`; result запрещён |
| [invalid/schema-multiple-errors.json](invalid/schema-multiple-errors.json) | MULTI-001 | JSON/Pydantic boundary | [expected/schema-multiple-errors.diagnostics.json](expected/schema-multiple-errors.diagnostics.json) |
| [invalid/normalization-atomic.json](invalid/normalization-atomic.json) | NRM-006 | Normalization + orchestration | `NORMALIZATION/precision_loss/$.listings[1].total_area_sqm`; result запрещён несмотря на корректную первую запись |
| [invalid/duplicate-publication-ref.json](invalid/duplicate-publication-ref.json) | COL-001 | Atomic collection | `COLLECTION_CONFLICT/duplicate_publication_ref/$.listings[1]`; result запрещён |
| [expected/search-all-three.json](expected/search-all-three.json) | E2E-ALL-001 | Output mapping and byte serialization | Сам файл; два совпадения в стабильном порядке |
| [expected/search-none.json](expected/search-none.json) | E2E-NONE-001 | Output mapping and byte serialization | Сам файл; все `Present`, `Missing`, `Unsupported` |
| [expected/search-no-match.json](expected/search-no-match.json) | E2E-EMPTY-001 | Output mapping and byte serialization | Сам файл; успешный пустой `matches` |
| [expected/schema-multiple-errors.diagnostics.json](expected/schema-multiple-errors.diagnostics.json) | MULTI-001 | Diagnostic ordering | Точная структурная последовательность issues; это test oracle, не успешный output |

## Правила использования

- Все JSON, кроме зарегистрированного `invalid/syntax-truncated.json`, обязаны разбираться стандартным JSON parser.
- `valid` и `criteria` являются внешними документами, `expected/search-*.json` — точные байты stdout, а `expected/*.diagnostics.json` — структурная тестовая спецификация диагностики.
- Отсутствующее необязательное поле нельзя заменять `null` при «упрощении» fixtures.
- Новая фикстура обязана получить scenario ID и строку в этой таблице. Почти одинаковые числовые края следует добавлять в параметризуемую матрицу документа, а не копировать целый batch.
- Golden обновляется только точечно после semantic diff и byte diff; автоматическое массовое принятие запрещено.
- Несовместимое изменение форматов или правил создаёт новый каталог версии, сохраняя `v1` для проверки совместимости.
