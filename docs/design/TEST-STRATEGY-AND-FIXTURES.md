# Стратегия проверок и фикстур первого среза

## Назначение и границы

Документ делает проверяемыми контракты из [предметной спецификации](DOMAIN-MODEL-AND-CONTRACTS.md) для потока:

```text
JSON-фикстура
  -> строгая граничная валидация
  -> адаптер фиктивного источника
  -> нормализация
  -> атомарная коллекция в памяти
  -> стандартный поиск
  -> байтово-детерминированный JSON
```

Фикстуры полностью вымышлены, не описывают реальные объявления и не требуют сети. Этот документ задаёт будущие тестовые данные и ожидаемое поведение, но не вводит Python-код, Pydantic-модели, pytest-тесты или CLI.

## Уровни будущих проверок

Один сценарий проверяется на минимальном уровне, способном локализовать дефект. Полный валидный поток, атомарный отказ и байтовая повторяемость дополнительно проверяются на интеграционном уровне, потому что это свойства композиции.

| Уровень | Что создаётся напрямую | Что подменяется | Минимальная ответственность и локализуемые дефекты |
| --- | --- | --- | --- |
| Чистые предметные типы и состояния | `PublicationRef`, канонические value-типы, `Present`, `Missing`, `Unsupported`, происхождение | JSON, Pydantic, файлы и все адаптеры отсутствуют | Диапазоны и инварианты типов; различие студии `0`, отсутствия и неподдерживаемого; запрет `raw_value` у `Missing`; обязательность полного происхождения у `Present` и `Unsupported` |
| Контракт фиктивного адаптера | Строго типизированный `ValidatedSourceBatch` с `InputLocation` | Граничный разбор заменён прямым конструированием; нормализатор не вызывается | Назначение `fixture_portal`, формат `PublicationId`, согласованность URL и идентификатора, перенос сырых значений и путей без преобразования единиц |
| Нормализация | Один `SourcePublicationSnapshot` и версии правил | Адаптер и Pydantic не участвуют | Точное преобразование времени, денег, площади, комнат и пробелов; `Missing`/`Unsupported`; `precision_loss`, диапазоны и неполная денежная пара |
| Атомарная коллекция | Несколько `NormalizedListing` | Источник, нормализация и поиск отсутствуют | Уникальность `PublicationRef`; либо полный неизменяемый снимок, либо `COLLECTION_CONFLICT` без частичной коллекции |
| Стандартный поиск | `CollectionSnapshot` и `SearchCriteria` | JSON, CLI и выходное отображение отсутствуют | Конъюнкция критериев, поведение `Missing`/`Unsupported`, поиск без критериев, успешное несовпадение и составная стабильная сортировка |
| Выходное отображение и сериализация | `SearchResult` со всеми состояниями | CLI и файловый ввод отсутствуют | Точная форма `search-result@1`, полнота происхождения, отсутствие недетерминированных метаданных, сортировка ключей и массивов, форматы денег/площади/времени |
| JSON/Pydantic-граница | Разобранные JSON-значения или фактические файлы | Прикладные операции заменены заглушкой, которую нельзя вызвать при ошибке | Строгие типы, обязательность, запрет лишних полей и `null`, версия документа, стабильное преобразование ошибок в `ContractIssue` |
| CLI-интеграция полного среза | Фактические файлы из `tests/fixtures/v1` | Ничего; сеть, часы и случайность не нужны | Код завершения, разделение stdout/stderr, полный поток, атомарный запрет частичного результата и совпадение stdout с golden-файлом |
| Повторяемость и байтовый детерминизм | Один и тот же валидный пакет и критерии | В будущей кроссплатформенной проверке меняются порядок перечисления файлов, локаль и часовой пояс процесса | Несколько запусков и Windows/Linux дают одинаковые байты; выявляются зависимости от locale, timezone, CRLF, порядка словарей/файлов и текущего времени |

Параметризуемые проверки нормализации используют строки матрицы ниже и не копируют весь CLI-сценарий для каждого числового края. Golden-тест проверяет форму документа целиком, но не заменяет точечные проверки причины ошибки.

TASK-012 покрывает чистое структурное отображение в `SearchResultDocument` без
Pydantic и JSON. TASK-013 отдельно покрывает strict output boundary,
канонические UTF-8 JSON bytes, OUT-001 и byte-exact сравнение трёх
утверждённых search golden через offline fixture pipeline. CLI-интеграция
полного среза остаётся следующим отдельным уровнем.

## Внешний документ пакета публикаций v1

### Корень

Документ — JSON-объект ровно с тремя полями. Лишние поля запрещены на каждом уровне.

| Поле | JSON-тип | Обязательность | Правило |
| --- | --- | --- | --- |
| `schema_version` | string | обязательно | Точное значение `fixture-source-batch@1`; иное значение — `INPUT_SCHEMA/unsupported_schema_version` |
| `source` | string | обязательно | Граница проверяет только тип; адаптер требует точное значение `fixture_portal`, иначе `SOURCE_ADAPTER/source_mismatch` |
| `listings` | array of object | обязательно | Непустой массив; порядок записей и индексы сохраняются; пустой массив даёт `INPUT_SCHEMA/invalid_value/$.listings` |

Каждая запись `listings[i]` допускает только следующие поля:

| Поле | JSON-тип | Обязательность | Source-specific смысл |
| --- | --- | --- | --- |
| `publication_id` | string | обязательно | Непрозрачный ASCII `PublicationId`; содержательное правило проверяет адаптер |
| `url` | string | обязательно | Исходная строка URL; согласованность проверяет адаптер |
| `observed_at` | string | обязательно | RFC 3339 с секундами и обязательным `Z` или числовым смещением; до 6 цифр долей секунды |
| `location_text` | string | необязательно | Unicode-текст; нормализация удаляет крайние и схлопывает внутренние Unicode-пробелы |
| `price_major` | string | структурно необязательно; семантически только парой с `currency` | Десятичная сумма в основных единицах валюты: ASCII-знак только для отрицательного теста, цифры, необязательная точка и 1–2 дробные цифры |
| `currency` | string | структурно необязательно; семантически только парой с `price_major` | Ровно три заглавные ASCII-буквы; `RUB` поддерживается, иной корректный код даёт `Unsupported` |
| `total_area_sqm` | string | необязательно | Десятичное число квадратных метров; преобразование в сотые должно быть точным |
| `rooms` | string | необязательно | `studio` или ASCII-десятичное целое `1..99` без знака; числовой ноль не заменяет явный токен студии |

Отсутствующее необязательное поле создаёт `MissingField` с ожидаемым путём. Явный `null` является предоставленным значением неверного типа и даёт `INPUT_SCHEMA/wrong_type`; он никогда не преобразуется в `Missing`. JSON-числа и boolean не принимаются вместо строк, даже если Pydantic мог бы их привести.

### Source-specific правила адаптера

- Адаптер назначает `SourceId = fixture_portal`; внешний `source` не переносится как произвольный идентификатор.
- `publication_id` имеет 1–128 ASCII-символов из `[A-Za-z0-9._:-]`. Пустая или не соответствующая строка даёт `SOURCE_ADAPTER/inconsistent_record` на поле идентификатора.
- `url` — абсолютный ASCII HTTPS URL без userinfo, порта, query и fragment. Host обязан быть ровно `listings.fixture.example`, а path — ровно `/offers/{publication_id}` без percent-decoding. Любое нарушение даёт `SOURCE_ADAPTER/invalid_source_url` на поле URL.
- Адаптер не разбирает цену, время, площадь и комнаты, не схлопывает пробелы и не определяет `Unsupported`; он переносит сырые JSON-скаляры и `InputLocation` в нейтральный снимок.
- Отсутствие ровно одного из `price_major`/`currency` переносится до нормализации и даёт там `NORMALIZATION/incomplete_money` на расположении всей записи `$.listings[i]`.

### Правила нормализации фиктивного источника

- `observed_at` требует реальный RFC 3339-момент с явным смещением, не допускает leap second и преобразуется в UTC без потери микросекунд.
- `location_text` после нормализации пробелов должен иметь 1–500 Unicode-кодовых точек.
- `price_major` переводится в минимальные единицы умножением на 100 без округления. Допустим итог `1..9_223_372_036_854_775_807`.
- `currency = RUB` создаёт `Present`; другой лексически корректный трёхбуквенный код создаёт `Unsupported` с `reason_code = unsupported_currency`. Некорректная лексема даёт `NORMALIZATION/invalid_value`.
- `total_area_sqm` переводится в целое число сотых м² без округления; итоговый диапазон `1..9_223_372_036_854_775_807`. Лишние ненулевые дробные цифры дают `precision_loss`; дополнительные нулевые цифры допустимы, потому что значение выражается точно.
- `rooms = studio` даёт `0`; десятичная строка даёт соответствующее целое
  `1..99`. Числовая строка со значением ноль даёт `invalid_value`, потому что
  канонический ноль означает только явно указанный source token `studio`;
  значение выше 99 даёт `out_of_range`, иные лексемы — `invalid_value`.

Версии правил golden-набора: `fixture-publication-id@1`, `fixture-source-url@1`, `fixture-observed-at@1`, `fixture-location-text@1`, `fixture-price-major@1`, `fixture-currency@1`, `fixture-total-area-sqm@1`, `fixture-rooms@1`. Версия меняется только вместе с осознанным пересмотром ожидаемой семантики.

## Внешний документ критериев v1

Корень — объект ровно из `schema_version` и `criteria`; лишние поля запрещены.

| Путь | JSON-тип | Обязательность | Правило |
| --- | --- | --- | --- |
| `$.schema_version` | string | обязательно | Точное значение `search-criteria@1` |
| `$.criteria` | object | обязательно | Может быть пустым; допускает только три поля ниже |
| `$.criteria.maximum_price` | object | необязательно | Ровно `amount_minor` и `currency` |
| `$.criteria.maximum_price.amount_minor` | integer | обязательно внутри объекта | Строгий JSON integer, не boolean; `1..9_223_372_036_854_775_807` |
| `$.criteria.maximum_price.currency` | string | обязательно внутри объекта | Точное значение `RUB`; конвертации нет |
| `$.criteria.minimum_total_area` | string | необязательно | Положительное точное десятичное число м², выразимое в сотых и в допустимом диапазоне |
| `$.criteria.allowed_rooms` | array of integer | необязательно | Непустой массив уникальных строгих integer `0..99`; boolean запрещён |

Отсутствующее поле означает отсутствие критерия. `null` запрещён. Иная версия обоих документов даёт `INPUT_SCHEMA/unsupported_schema_version/$.schema_version`. Некорректное значение критерия при корректном JSON-типе даёт `INPUT_SCHEMA/invalid_criterion` на самом узком доступном пути; неверный тип, лишнее или отсутствующее структурное поле сохраняют общие коды `wrong_type`, `extra_field`, `missing_field`. В каноническом результате присутствуют только заданные критерии; комнаты сортируются по возрастанию, а площадь выводится с двумя знаками.

## `InputLocation` и порядок диагностик

Путь всегда относится к содержимому документа, а не к абсолютному пути файла:

- синтаксис или корень документа: `$`;
- корневое поле: `$.source` или `$.criteria`;
- запись: `$.listings[2]`;
- поле записи: `$.listings[2].price_major`;
- вложенный критерий: `$.criteria.maximum_price.amount_minor`.

Для нескольких независимых ошибок порядок фиксирован составным ключом:

1. ранг документа: `listings` перед `criteria`;
2. индекс записи, где корень имеет ранг `-1`;
3. путь по Unicode-кодовым точкам;
4. `category` по Unicode-кодовым точкам;
5. `code` по Unicode-кодовым точкам.

Порядок не наследуется от Pydantic, исключений или обхода словаря. Ошибка синтаксиса одного документа не разрешает угадывать его структуру. Независимо разобранные ошибки второго документа можно сообщить, но результат запрещён при любой ошибке.

## Матрица отрицательных и граничных сценариев

`База` означает файл `valid/listings-comprehensive.json` или соответствующий файл критериев; мутация применяется в памяти будущего параметризованного теста и не требует отдельного файла. `JSON результата` означает успешный документ `search-result@1`, а не диагностическую спецификацию.

| ID | Вход или мутация | Граница | Ожидаемые `category/code/location` | JSON результата |
| --- | --- | --- | --- | --- |
| SYN-001 | `invalid/syntax-truncated.json` | JSON parser | `INPUT_SYNTAX/invalid_json/$` | запрещён |
| SCH-001 | удалить `listings[0].url` | listings schema | `INPUT_SCHEMA/missing_field/$.listings[0].url` | запрещён |
| SCH-002 | `listings[0].price_major = 100` | listings schema | `INPUT_SCHEMA/wrong_type/$.listings[0].price_major` | запрещён |
| SCH-003 | добавить `listings[0].extra_note` | listings schema | `INPUT_SCHEMA/extra_field/$.listings[0].extra_note` | запрещён |
| SCH-004 | `listings[0].location_text = null` | listings schema | `INPUT_SCHEMA/wrong_type/$.listings[0].location_text` | запрещён |
| ADP-001a | `publication_id = ""` | fixture adapter | `SOURCE_ADAPTER/inconsistent_record/$.listings[0].publication_id` | запрещён |
| ADP-001b | `publication_id = "bad id"` | fixture adapter | `SOURCE_ADAPTER/inconsistent_record/$.listings[0].publication_id` | запрещён |
| ADP-002a | URL с HTTP, query, fragment или иным host | fixture adapter | `SOURCE_ADAPTER/invalid_source_url/$.listings[0].url` | запрещён |
| ADP-002b | URL path содержит другой `publication_id` | fixture adapter | `SOURCE_ADAPTER/invalid_source_url/$.listings[0].url` | запрещён |
| ADP-003 | `source = other_fixture` | fixture adapter | `SOURCE_ADAPTER/source_mismatch/$.source` | запрещён |
| NRM-001 | `observed_at = "2026-02-03T10:15:30"` | normalization | `NORMALIZATION/invalid_value/$.listings[0].observed_at` | запрещён |
| NRM-002 | `location_text = "   "` | normalization | `NORMALIZATION/invalid_value/$.listings[0].location_text` | запрещён |
| NRM-003a | `price_major = "0.00"` | normalization | `NORMALIZATION/out_of_range/$.listings[0].price_major` | запрещён |
| NRM-003b | `price_major = "-1.00"` | normalization | `NORMALIZATION/out_of_range/$.listings[0].price_major` | запрещён |
| NRM-004 | удалить только `currency` у записи с ценой | normalization | `NORMALIZATION/incomplete_money/$.listings[0]` | запрещён |
| NRM-005 | `currency = "USD"` при корректной цене | normalization | ошибки нет; `Unsupported(reason_code=unsupported_currency)` | разрешён |
| NRM-006 | `total_area_sqm = "47.125"`; также файл `invalid/normalization-atomic.json` | normalization | `NORMALIZATION/precision_loss/$.listings[1].total_area_sqm` в статическом файле | запрещён |
| NRM-007 | `total_area_sqm = "92233720368547758.08"` | normalization | `NORMALIZATION/out_of_range/$.listings[0].total_area_sqm` | запрещён |
| NRM-008 | `rooms = "100"` | normalization | `NORMALIZATION/out_of_range/$.listings[0].rooms` | запрещён |
| CRI-001 | `allowed_rooms = []` | criteria schema | `INPUT_SCHEMA/invalid_criterion/$.criteria.allowed_rooms` | запрещён |
| COL-001 | `invalid/duplicate-publication-ref.json` | collection | `COLLECTION_CONFLICT/duplicate_publication_ref/$.listings[1]` | запрещён |
| MULTI-001 | `invalid/schema-multiple-errors.json` | listings schema | точная последовательность из `expected/schema-multiple-errors.diagnostics.json` | запрещён |
| SRCH-EMPTY-001 | comprehensive + `criteria/no-match.json` | search | ошибок нет | разрешён, `matches=[]` |
| OUT-001 | вручную создать невозможный `SearchResultDocument`, например `Missing` с `raw_value` | output boundary | `OUTPUT_CONTRACT/invalid_result_document/$` | запрещён |

`OUT-001` нельзя получить обычной внешней фикстурой: корректные внутренние типы и mapper обязаны исключать такое состояние. Он создаётся только прямым тестом выходной границы; корень `$` выбран намеренно, потому что у внутреннего дефекта нет честного `InputLocation` внешнего документа. Для любой запрещающей строки атомарность означает отсутствие совпадений, частичной коллекции и успешного JSON в stdout.

## Положительные сценарии

| ID | Пакет | Критерии | Ожидание |
| --- | --- | --- | --- |
| E2E-ALL-001 | `valid/listings-comprehensive.json` | `criteria/all-three.json` | `studio-002`, затем `alpha-001`; точные байты `expected/search-all-three.json` |
| SEARCH-PARTIAL-001 | тот же | `criteria/partial-area.json` | только `currency-004`; неподдерживаемая валюта не мешает незаданному ценовому критерию |
| E2E-NONE-001 | тот же | `criteria/none.json` | все четыре записи в порядке `studio-002`, `alpha-001`, `missing-003`, `currency-004`; точные байты `expected/search-none.json` |
| E2E-EMPTY-001 | тот же | `criteria/no-match.json` | успешный пустой результат; точные байты `expected/search-no-match.json` |

Набор доказывает `Present`, `Missing`, `Unsupported`, студию `0`, смещения времени, точные площади, RUB в копейках, частичные и отсутствующие критерии, конъюнкцию всех трёх критериев и сортировку нескольких совпадений.

## Выходной документ `search-result@1`

### Структура

Корень имеет ровно `criteria`, `matches`, `schema_version`. `criteria` повторяет канонические заданные критерии и не содержит отсутствующие ключи или `null`. Каждый match имеет ровно:

`currency`, `location_text`, `observed_at`, `price_amount`, `publication_ref`, `rooms`, `source_url`, `total_area`.

Обязательные traced-поля кодируются объектом `{"provenance": ..., "value": ...}`. Необязательные outcomes:

- `Present`: `{"provenance": ..., "state": "present", "value": ...}`;
- `Missing`: `{"provenance": ..., "state": "missing"}` без `raw_value` и `value`;
- `Unsupported`: `{"provenance": ..., "reason_code": ..., "state": "unsupported"}` без канонического `value`, но с исходным `raw_value`.

`provenance` содержит `input_path`, `normalization_rule_version`, `observed_at`, `publication_id`, `source_field`, `source_id` и, кроме `Missing`, `raw_value`. `publication_ref.value` содержит `publication_id` и `source_id`. Деньги выводятся integer минимальных единиц, площадь — строкой с двумя знаками, время — UTC RFC 3339 с `Z` и шестью цифрами, комнаты — integer.

### Канонические байты

- UTF-8 без BOM;
- ключи каждого объекта лексикографически по Unicode-кодовым точкам;
- разделители `,` и `:` без необязательных пробелов;
- стандартное JSON-экранирование без зависимости от локали;
- ровно один `LF` после документа;
- порядок matches по ключу TASK-003; `allowed_rooms` — возрастающий массив;
- нет времени запуска, длительности, абсолютного пути, hostname, случайного ID, диагностик или порядка чтения каталога.

Golden-файл сравнивается как байты целиком. Семантическое сравнение JSON полезно для диагностики diff, но не заменяет байтовую проверку.

## Каталог, именование и сопровождение

Каталог [tests/fixtures/v1](../../tests/fixtures/v1/MANIFEST.md) версионирует внешний формат целиком. `v1` меняется только при несовместимом изменении входных документов, правил или output schema. Имена имеют вид `<назначение>.json`, сценарии имеют стабильный `<ОБЛАСТЬ>-NNN`, а манифест связывает каждый файл со сценарием, уровнем и oracle.

Golden разрешено обновить только когда принято отдельное изменение контракта или исправлен доказанный ошибочный oracle. Обязательны:

1. просмотр semantic diff разобранных JSON;
2. отдельный просмотр byte diff, включая кодировку и последний LF;
3. объяснение изменения в задаче и, для контракта, в decision record;
4. точечное принятие файлов.

Команда «обновить все goldens» без просмотра запрещена. Тест никогда не перезаписывает oracle автоматически.

До появления каркаса стандартная библиотека должна разобрать все `.json`, кроме явно зарегистрированного `SYN-001`, а он обязан завершиться ошибкой. После каркаса одна ожидаемая команда качества — `uv run quality`; она должна в установленном порядке запустить Ruff format-check, Ruff lint, строгий mypy, pytest, проверку manifest и байтовых golden-файлов.

На Windows и Linux проверяются одинаковые семантические результаты и байты. Тесты задают входы явно, не используют текущие locale/timezone/time, сортируют найденные пути, открывают JSON как UTF-8, сериализуют `\n`, не применяют platform newline translation и не полагаются на порядок файловой системы.

## Связь с архитектурой

JSON-схемы принадлежат внешней границе. Фиктивный формат не становится `SourcePublicationSnapshot`, а Pydantic-модель не становится моделью ядра. Чистые уровни создают предметные объекты напрямую; CLI и JSON проверяются только снаружи. Это сохраняет направление зависимостей из [ARCHITECTURE.md](../../ARCHITECTURE.md).
