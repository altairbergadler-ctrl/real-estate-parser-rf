# Повторные наблюдения и изменения source publication

## Назначение и границы

Документ уточняет принятое [решение 0005](../decisions/0005-publication-observations-and-changes.md)
до уровня, достаточного для следующей чистой реализации. Здесь описана
логическая форма immutable-типов и операций, а не Python-код, Pydantic-схема,
JSON-документ или таблица базы данных.

Модель расширяет понятия `PublicationRef`, `ObservedAt`, `NormalizedListing` и
полевого provenance из
[контрактов первого среза](DOMAIN-MODEL-AND-CONTRACTS.md), не изменяя сам
первый срез, его CLI, `CollectionSnapshot`, fixtures или `search-result@1`.

В scope находятся несколько наблюдений **одной source publication**,
детерминированное сравнение последовательных наблюдений, подтверждённая
недоступность и reappearance. Physical property identity, cross-source dedup,
постоянное хранение и источник данных остаются вне модели.

## Термины и инварианты identity

### Поток наблюдений

`PublicationObservationStream` — упорядоченная история ровно одной
`PublicationRef`. `PublicationRef = (SourceId, PublicationId)` остаётся
идентичностью публикации на одной площадке. Поток не является квартирой, домом,
предложением собственника или группой дублей.

Разные `PublicationRef`, даже с одинаковыми адресом, ценой и площадью, всегда
образуют разные потоки. Будущий dedup может ссылаться на потоки, но не
переписывать их identity.

### Ключ наблюдения

```text
ObservationKey(
  reference: PublicationRef,
  observed_at: ObservedAt
)
```

Ключ структурный; его не требуется превращать в строку или hash. Он полностью
детерминирован и не содержит случайность, текущее время, порядок batch, путь к
файлу или revision хранилища.

В одном потоке `reference` всех ключей совпадает. Для одного
`PublicationRef + ObservedAt` допустимо ровно одно полное содержимое
наблюдения:

- полное равенство существующему наблюдению — exact replay, успешный no-op;
- любое различие kind, listing, canonical value, provenance или unavailable
  evidence — `OBSERVATION_CONFLICT/timestamp_content_conflict`.

### Доступное наблюдение

```text
AvailableObservation(
  key: ObservationKey,
  listing: NormalizedListing
)
```

`NormalizedListing` уже полностью и успешно нормализован и остаётся immutable.
Наблюдение не принимает partial listing и не нормализует сырые данные.

Обязательные согласования:

- `listing.reference.value == key.reference`;
- `listing.observed_at.value == key.observed_at`;
- provenance reference, source id и publication id каждого traced/outcome поля
  совпадают с `key.reference`;
- `provenance.observed_at == key.observed_at` для каждого поля.

Нарушение этих условий — невозможный предметный объект, а не альтернативная
identity.

### Подтверждённо недоступное наблюдение

```text
UnavailableObservation(
  key: ObservationKey,
  evidence: DirectSourceStateEvidence | TargetedPublicationCheckEvidence
)

DirectSourceStateEvidence(
  raw_source_state: string,
  source_field: string,
  adapter_rule_version: AvailabilityRuleVersion,
  source_reported_cause: SourceReportedCause | absent
)

TargetedPublicationCheckEvidence(
  outcome_code: ConclusiveUnavailableOutcomeCode,
  check_rule_version: AvailabilityRuleVersion,
  adapter_rule_version: AvailabilityRuleVersion
)
```

Оба evidence-типа относятся к точной `key.reference` и моменту
`key.observed_at`; эти координаты не дублируются как новая identity внутри
evidence. `AvailabilityRuleVersion` — непустой стабильный opaque ASCII code.

Достаточные основания:

1. `DirectSourceStateEvidence`: источник прямо сообщает состояние конкретной
   публикации, raw state и место/поле сохранены, а интерпретация имеет версию.
2. `TargetedPublicationCheckEvidence`: отдельная проверка была адресована ровно
   этой `PublicationRef`, а её versioned правило определяет полученный outcome
   как conclusive unavailable.

Недостаточные основания не создают `UnavailableObservation`:

- публикации нет в полном или частичном batch;
- pagination/filter/limit не вернул запись;
- timeout, DNS/TLS/network failure;
- блокировка, rate limit, captcha или отказ авторизации;
- общий source failure, неполный scan или неизвестный ответ;
- отсутствие сохранённого versioned правила интерпретации.

Такие исходы означают `UnknownAttemptOutcome` за пределами истории. Они могут
быть операционной диагностикой будущего collector, но не меняют состояние
публикации.

`source_reported_cause` допускается только в прямом source evidence. Значения
вроде `source_reported_deleted` и `source_reported_expired` остаются claim
источника. Без такого evidence канонический факт — только «подтверждённо
недоступна», а не «удалена» или «истекла».

### Псевдотип истории

```text
PublicationObservation = AvailableObservation | UnavailableObservation

PublicationObservationHistory(
  reference: PublicationRef,
  comparison_policy_version: ComparisonPolicyVersion,
  observations: tuple[PublicationObservation, ...]
)
```

`observations` строго возрастает по `key.observed_at` и не содержит повторных
ключей. Пустая история допустима до первого наблюдения. Version policy
принадлежит истории и каждому созданному `ChangeSet`; разные версии не
смешиваются молча.

## Порядок, replay и out-of-order

Алгоритм проверки кандидата концептуально выполняется в таком порядке:

1. Проверить совпадение `PublicationRef` с потоком.
2. Если ключ уже есть, сравнить полный immutable observation: exact equal даёт
   `REPLAYED`, любое различие — timestamp conflict.
3. Если ключ новый и его `observed_at` меньше последнего принятого времени,
   вернуть out-of-order conflict.
4. Если ключ новый и время больше последнего, сравнить его с последним
   наблюдением и добавить атомарно.

Равный timestamp не имеет arrival-order tie-breaker: ingest order, UUID и
текущее время не могут выбрать победителя.

Для набора кандидатов внешний порядок tuple не является смыслом. Операция
сначала проверяет весь набор, сворачивает только exact duplicates, затем
сортирует новые ключи по `ObservedAt` и применяет их как одну транзакцию. Все
новые ключи должны быть позже текущего tail. Любой конфликт reference,
timestamp, порядка или policy отклоняет весь набор без частичной новой истории
и без частичных `ChangeSet`.

## Версионированная политика сравнения

Первая версия имеет opaque code:

```text
ComparisonPolicyVersion("publication-change-policy@1")
```

Она сравнивает ровно шесть полей и всегда выдаёт их в этом порядке:

1. `source_url`;
2. `location_text`;
3. `price_amount`;
4. `currency`;
5. `total_area`;
6. `rooms`.

`PublicationRef` задаёт поток и не является сравниваемым полем.
`ObservedAt` задаёт ключ наблюдения и сам по себе не является изменением
публикации. `listing.reference` и `listing.observed_at` участвуют только в
проверке инвариантов.

### Каноническая проекция поля

Для сравнения каждое поле представляется одинаковой формой:

```text
CanonicalFieldOutcome[T] =
  PresentValue(value: T)
  | MissingValue
  | UnsupportedValue(reason_code: string)

FieldSnapshot[T](
  canonical: CanonicalFieldOutcome[T],
  provenance: ValueProvenance | MissingProvenance | UnsupportedProvenance
)
```

Для обязательного `source_url` допустим только `PresentValue(SourceUrl)`.
Для остальных полей используются все три состояния. `Unsupported.reason_code`
является частью канонической проекции: изменение причины — substantive change,
даже если raw value совпало.

`FieldOutcome.Missing` означает отсутствие одного необязательного поля внутри
доступного listing. Оно никогда не означает недоступность публикации. Последняя
выражается только отдельным доказательным `UnavailableObservation`.

### Три класса различий

Классы взаимоисключающие для одной пары одного поля:

1. **Substantive canonical change** — различается `canonical`. Результат хранит
   полные canonical before/after и оба полных provenance. Дополнительные
   различия raw/provenance отдельно не дублируются.
2. **Source-representation-only change** — canonical равен, но `raw_value`
   различается. Для `Missing`, у которого raw отсутствует, этот класс
   невозможен. Если одновременно изменились другие части provenance, приоритет
   остаётся у source-representation-only; оба provenance позволяют увидеть
   всё различие.
3. **Provenance refresh** — canonical и raw равны, но различается provenance
   после исключения координаты `observed_at`. Например, изменилась версия
   нормализации, source field или structural input path, а canonical/raw
   остались прежними.

Если canonical, raw и сравниваемое provenance равны, а различается только
`observed_at`, поле не создаёт delta. Поэтому повторная успешная фиксация в
новый момент может дать пустой `ChangeSet`.

Exact replay строже: для него полные observation, включая timestamp и всё
provenance/evidence, должны быть равны.

### Переходы `FieldOutcome`

| Before | After | Результат canonical comparison |
| --- | --- | --- |
| `Present(a)` | `Present(a)` | не substantive; затем raw/provenance classification |
| `Present(a)` | `Present(b)`, `a != b` | substantive, сохранить оба values и provenance |
| `Present` | `Missing` | substantive |
| `Present` | `Unsupported(reason)` | substantive, сохранить after reason и оба provenance |
| `Missing` | `Present` | substantive |
| `Missing` | `Missing` | не substantive; затем provenance classification |
| `Missing` | `Unsupported(reason)` | substantive, сохранить after reason и оба provenance |
| `Unsupported(reason)` | `Present` | substantive, сохранить before reason и оба provenance |
| `Unsupported(reason)` | `Missing` | substantive, сохранить before reason и оба provenance |
| `Unsupported(a)` | `Unsupported(a)` | не substantive; затем raw/provenance classification |
| `Unsupported(a)` | `Unsupported(b)`, `a != b` | substantive, сохранить обе причины и оба provenance |

Таким образом `Missing` не равно `Unsupported`, а изменение raw при том же
`Present` value или том же `Unsupported(reason)` не выдаётся за изменение
канонического объявления.

## Availability transitions и `ChangeSet`

```text
AvailabilityChange =
  ConfirmedUnavailable(
    before: AvailableObservation,
    after: UnavailableObservation
  )
  | Reappeared(
    before: UnavailableObservation,
    after: AvailableObservation
  )

FieldDeltaKind = SUBSTANTIVE | SOURCE_REPRESENTATION_ONLY | PROVENANCE_REFRESH

FieldDelta(
  field: ComparableFieldName,
  kind: FieldDeltaKind,
  before: FieldSnapshot,
  after: FieldSnapshot
)

AvailabilityEvidenceDelta(
  before: DirectSourceStateEvidence | TargetedPublicationCheckEvidence,
  after: DirectSourceStateEvidence | TargetedPublicationCheckEvidence
)

ChangeSet(
  policy_version: ComparisonPolicyVersion,
  from_key: ObservationKey,
  to_key: ObservationKey,
  availability_change: AvailabilityChange | absent,
  field_deltas: tuple[FieldDelta, ...],
  availability_evidence_delta: AvailabilityEvidenceDelta | absent
)
```

`field_deltas` сортируется только утверждённым policy field order. Для одного
поля бывает не более одной delta. `AvailabilityEvidenceDelta` применяется лишь
к двум последовательным unavailable observations, когда их semantic
availability равна, но их полные evidence-типы или значения различаются.
`ObservedAt` находится во внешних keys и сам evidence delta не создаёт. Delta
сохраняет оба полных evidence; если они равны, она отсутствует.

Таблица пар последовательных observations:

| Before | After | Availability | Сравнение полей |
| --- | --- | --- | --- |
| Available | Available | без availability change | все шесть полей |
| Available | Unavailable | `ConfirmedUnavailable` | не выполняется: after listing отсутствует |
| Unavailable | Available | `Reappeared` | не выполняется: before listing отсутствует |
| Unavailable | Unavailable | без availability change; возможен evidence delta | не выполняется |

Reappearance не утверждает, что publication была удалена и создана заново.
Также она не сравнивается автоматически с последним available listing до
периода недоступности: `ChangeSet` всегда относится только к двум
последовательным observations.

Пустой `ChangeSet` имеет отсутствующий `availability_change`, пустой
`field_deltas` и отсутствующий `availability_evidence_delta`. Это успешный
результат «новое наблюдение принято, доказуемых изменений нет», а не ошибка.

## Минимальный будущий чистый API

Следующая реализация может выразить контракт такими псевдооперациями:

```text
compare_consecutive_observations(
  previous: PublicationObservation,
  current: PublicationObservation,
  policy: ComparisonPolicy
) -> ChangeSet | ObservationConflict

append_observation(
  history: PublicationObservationHistory,
  candidate: PublicationObservation,
  policy: ComparisonPolicy
) -> ObservationAppendSuccess | ObservationAppendFailure

ObservationAppendSuccess(
  disposition: APPENDED | REPLAYED,
  history: PublicationObservationHistory,
  change_set: ChangeSet | absent
)

ObservationAppendFailure(
  conflicts: non-empty tuple[ObservationConflict, ...]
)
```

При `APPENDED` возвращается новая immutable history и `ChangeSet` только если у
нового observation был predecessor; для первого наблюдения `change_set`
отсутствует. При `REPLAYED` возвращается исходная history и `change_set`
отсутствует. Failure не содержит partial history или partial changes.

Операции не читают часы, не создают UUID, не знают JSON/Pydantic, filesystem,
CLI, batch первого среза и storage.

## Стабильные будущие конфликты

`ObservationConflict` содержит category, code и структурный subject
(`PublicationRef` или `ObservationKey`), но не требует JSONPath, exception text
или конкретной библиотеки.

| Category | Code | Смысл |
| --- | --- | --- |
| `OBSERVATION_CONFLICT` | `stream_reference_mismatch` | кандидат относится к другой `PublicationRef` |
| `OBSERVATION_CONFLICT` | `timestamp_content_conflict` | тот же ключ имеет неравное полное содержимое/evidence |
| `OBSERVATION_CONFLICT` | `out_of_order_observation` | новый неизвестный ключ старше текущего tail |
| `OBSERVATION_CONFLICT` | `comparison_policy_mismatch` | history и операция используют разные версии policy |
| `OBSERVATION_CONFLICT` | `expected_revision_mismatch` | атомарный storage append увидел изменившуюся revision |

Порядок конфликтов набора: `PublicationRef` (`SourceId`, затем
`PublicationId`), `ObservedAt` при наличии, затем category и code — всё
каноническим сравнением соответствующих типов. Conflict одной записи запрещает
применение всего набора.

## Потребительский контракт будущего repository/storage port

Storage port нужен только как внешний потребитель уже принятых типов:

```text
load_observation_stream(reference: PublicationRef)
  -> LoadedObservationStream(history, revision)

append_observations_atomically(
  reference: PublicationRef,
  expected_revision: StreamRevision,
  observations: non-empty tuple[PublicationObservation, ...],
  policy_version: ComparisonPolicyVersion
) -> AtomicAppendSuccess | AtomicAppendConflict
```

Порт обязан:

- сохранять полные immutable observations и все provenance/evidence без
  семантической потери;
- не смешивать `PublicationRef` и не менять канонический порядок;
- применять весь проверенный набор либо ничего;
- защищать compare-and-append через opaque `expected_revision`;
- возвращать стабильный `expected_revision_mismatch`, а не частичный успех;
- не вычислять предметные изменения иной скрытой policy.

`StreamRevision` — технический concurrency token, не observation identity и не
время. Этот контракт не выбирает SQLite, PostgreSQL, ORM, event store,
filesystem, JSON, транзакционный API или схему миграций. Адаптер и выбор
технологии остаются отдельной будущей задачей.

## Полностью вымышленные сценарии

Все публикации ниже относятся к `PublicationRef(fixture_portal, demo-015)` и
не описывают реальный объект.

| Сценарий | Предыдущее / вход | Новое доказательство | Ожидаемый результат |
| --- | --- | --- | --- |
| Первая фиксация | пустая history | Available в `2026-09-01T10:00:00Z` | `APPENDED`, ChangeSet отсутствует |
| Exact replay | уже есть полное observation в `10:00` | тот же immutable observation | `REPLAYED`, history не меняется |
| Обновление цены | Available `price_amount=10_000_000` | Available в `11:00`, `price_amount=9_500_000` | один `SUBSTANTIVE` delta `price_amount` с before/after provenance |
| Raw-only | площадь raw `"47.0"`, canonical `4700` | raw `"47.00"`, canonical `4700` | один `SOURCE_REPRESENTATION_ONLY` delta `total_area` |
| Provenance refresh | canonical/raw те же | новая normalization rule version даёт тот же outcome | один `PROVENANCE_REFRESH` delta |
| No change | canonical/raw/provenance кроме времени те же | новое Available позднее | успешный пустой ChangeSet |
| `Present -> Missing` | location present | поле отсутствует в следующем Available | substantive delta с обоими provenance |
| `Missing -> Present` | rooms missing | rooms present | substantive delta |
| `Present -> Unsupported` | currency present | корректное, но unsupported значение с reason | substantive delta с reason и обоими provenance |
| Equal timestamp conflict | Available в `11:00` уже принят | тот же key, иная цена | `timestamp_content_conflict`, ничего не добавлено |
| Out-of-order новое | tail `11:00` | неизвестный key `10:30` | `out_of_order_observation`, история неизменна |
| Частичный batch без публикации | tail Available | batch не содержит `demo-015` | history не вызывается и не меняется; не disappearance |
| Подтверждённая недоступность | Available `11:00` | explicit source state в `12:00` | `ConfirmedUnavailable`, evidence сохранён |
| Reappearance | Unavailable `12:00` | Available `13:00` | `Reappeared`; field comparison не выполняется |
| Повторная недоступность | Unavailable `12:00` | conclusive targeted check `12:30` | новое Unavailable; evidence delta либо пустой ChangeSet |
| Replay недоступности | Unavailable `12:00` уже есть | точное то же evidence и key | `REPLAYED`, no-op |
| Network/source failure | последний state любой | timeout, block или source error | unknown attempt; observation не создаётся, state не меняется |

## Намеренно отложено

- Python-типы и тесты этого дизайна;
- batch API поверх pure append одного наблюдения;
- сохранение, запросы истории, retention и миграции;
- JSON/API/CLI представление observations и changes;
- backfill и пересчёт истории при out-of-order данных;
- сравнение reappearance с последним earlier available observation;
- polling, scheduler, retries и реальные source checks;
- physical property identity, cross-source dedup, уведомления и сигналы.
