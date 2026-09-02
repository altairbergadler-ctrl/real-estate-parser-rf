# Доказательная оценка возможных дублей source publications

## Назначение и границы

Документ уточняет [решение 0006](../decisions/0006-publication-duplicate-evidence.md)
до уровня, достаточного для следующей чистой реализации. Он описывает
логическую форму immutable-типов и pure operations, а не Python-код,
Pydantic/JSON schema, repository, таблицу базы данных или интерфейс.

Модель использует существующие `PublicationRef`, `ObservationKey`,
`AvailableObservation`, `NormalizedListing`, `FieldOutcome` и provenance из
[контрактов первого среза](DOMAIN-MODEL-AND-CONTRACTS.md) и
[спецификации observations](PUBLICATION-OBSERVATIONS-AND-CHANGES.md). Эти типы,
histories и правила TASK-015…TASK-017 не изменяются.

В scope находится только детерминированная оценка **одной пары** двух разных
source publications и отдельная immutable запись ручной проверки. Модель не
создаёт физический объект, не объединяет listings или histories, не выбирает
canonical publication и не ищет пары в коллекции.

## Что является фактом до оценки

До дедупликации существуют только:

- независимые `PublicationRef = (SourceId, PublicationId)`;
- независимые observation histories каждой reference;
- точные available/unavailable observations этих histories;
- полные `NormalizedListing` и provenance внутри available observation.

Совпадение полей двух публикаций является основанием гипотезы, а не новым
фактом о физическом объекте. Даже подтверждённая человеком pairwise relation
остаётся assertion о двух публикациях и не создаёт `PhysicalProperty`.

## Неупорядоченная identity пары

### Канонические стороны

Для любой `PublicationRef` определён structural sort key:

```text
(reference.source_id.value, reference.publication_id.value)
```

Обе строки сравниваются побайтно в уже валидированной форме. Для двух разных
references меньшая по этому ключу всегда называется `left`, большая — `right`:

```text
PublicationPair(
  left: PublicationRef,
  right: PublicationRef
)
```

Инварианты:

- `left != right`; одинаковая `PublicationRef` не является duplicate pair;
- `sort_key(left) < sort_key(right)`;
- разные публикации одного source разрешены;
- публикации разных sources разрешены;
- вход `(A, B)` и `(B, A)` создаёт один и тот же `PublicationPair`.

`PublicationRef` и source URL остаются identity публикации, а не физического
объекта. Совпадение или различие URL не объединяет references.

### Identity автоматической assessment

```text
DuplicateAssessmentIdentity(
  pair: PublicationPair,
  left_observation_key: ObservationKey,
  right_observation_key: ObservationKey,
  policy_version: DuplicatePolicyVersion
)
```

`left_observation_key.reference == pair.left`, а right key относится к
`pair.right`. Identity не содержит UUID, arrival order, текущего времени,
storage revision или hash сериализации.

Автоматическая assessment всегда привязана не только к keys, но и к полным
immutable `AvailableObservation` обеих сторон. Keys образуют structural
identity, а полное содержимое observations участвует в equality/replay
проверке. Это не позволяет молча принять другое содержимое под тем же key.

## Eligibility и недоступная сторона

Сравнение listing выполняется только когда обе стороны — согласованные
`AvailableObservation`.

`UnavailableObservation` не содержит listing и не оценивается как будто все
его поля отсутствуют. Ни один из следующих исходов не создаёт supporting или
contradicting duplicate evidence:

- подтверждённая unavailable observation одной стороны;
- отсутствие publication в batch;
- timeout, rate limit, блокировка, network/source failure;
- incomplete scan или неизвестный operational outcome;
- отсутствие выбранного current available observation.

Pure operation для такого входа возвращает `PairNotAssessed` с keys и
безопасным reason code `side_not_available`; это **не** automatic assessment,
не categorical duplicate outcome и не отрицательное evidence. Если обе
стороны позже имеют available observations, для этих точных keys выполняется
новая assessment.

## Логические псевдотипы

Обозначения задают форму будущих нейтральных frozen/slots типов:

```text
DuplicatePolicyVersion(value: opaque ASCII code)
DuplicateRuleId(value: stable opaque ASCII code)
DuplicateRuleVersion(value: stable opaque ASCII code)
DuplicateReasonCode(value: stable safe opaque ASCII code)

EvidencePolarity = SUPPORTS | CONTRADICTS
EvidenceStrength = MATERIAL | CORROBORATING | AUXILIARY

DuplicateFieldSnapshot(
  field: DuplicateComparableFieldName,
  canonical: PresentValue(value) | MissingValue | UnsupportedValue(reason_code),
  provenance: ValueProvenance | MissingProvenance | UnsupportedProvenance
)

DuplicateEvidenceItem(
  rule_id: DuplicateRuleId,
  rule_version: DuplicateRuleVersion,
  polarity: EvidencePolarity,
  strength: EvidenceStrength,
  compared_fields: non-empty tuple[DuplicateComparableFieldName, ...],
  left_snapshots: non-empty tuple[DuplicateFieldSnapshot, ...],
  right_snapshots: non-empty tuple[DuplicateFieldSnapshot, ...],
  reason_code: DuplicateReasonCode
)

RuleNonComparison(
  rule_id: DuplicateRuleId,
  rule_version: DuplicateRuleVersion,
  compared_fields: non-empty tuple[DuplicateComparableFieldName, ...],
  left_snapshots: non-empty tuple[DuplicateFieldSnapshot, ...],
  right_snapshots: non-empty tuple[DuplicateFieldSnapshot, ...],
  reason_code: DuplicateReasonCode
)

DuplicateAutomaticOutcome =
  CANDIDATE_REQUIRES_MANUAL_REVIEW
  | CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW
  | INSUFFICIENT_EVIDENCE_NO_CANDIDATE

DuplicatePairAssessment(
  identity: DuplicateAssessmentIdentity,
  left_observation: AvailableObservation,
  right_observation: AvailableObservation,
  evidence: tuple[DuplicateEvidenceItem, ...],
  non_comparisons: tuple[RuleNonComparison, ...],
  outcome: DuplicateAutomaticOutcome
)
```

`DuplicateEvidenceItem` существует только с polarity `SUPPORTS` или
`CONTRADICTS`. Недостаток ввода и намеренно нейтральное различие находятся в
отдельном `RuleNonComparison` и не маскируются как evidence с нулевым весом.

Snapshots обеих сторон сохраняют canonical outcome и полное provenance.
`Missing` не получает вымышленный raw value; `Unsupported` сохраняет свой
reason code и предоставленное raw value внутри provenance. `left/right`
назначаются только canonical pair order, поэтому перестановка входа не меняет
snapshots или equality результата.

## Версионированная policy первой реализации

### Версия, порядок и роли strength

Первая версия имеет opaque code:

```text
DuplicatePolicyVersion("publication-duplicate-policy@1")
```

Rules всегда выполняются и выводятся в порядке:

1. `total_area`;
2. `rooms`;
3. `location_text`;
4. полная пара `price_amount + currency`.

Внутри одного rule сначала может появиться не более одного evidence item либо
один non-comparison. Порядок `evidence` и `non_comparisons` наследует этот
policy order; polarity, strength, входной порядок и значения не пересортируют
его.

`EvidenceStrength` не является числом и не имеет общего математического веса:

- `MATERIAL` — структурное основание, которое policy использует как
  обязательную опору candidate gate либо как значимое противоречие;
- `CORROBORATING` — дополнительное основание, способное завершить candidate
  gate только вместе с material support;
- `AUXILIARY` — объяснимое наблюдение, которое сохраняется, но не влияет на
  aggregate outcome policy v1.

Эти категории применимы только к указанным ниже rules версии v1. Их нельзя
складывать, переводить в проценты или сравнивать как probability.

### Точная таблица rules

| Порядок | Rule id / version | Сравнимый ввод | Равные present values | Разные present values | `Missing` / `Unsupported` |
| --- | --- | --- | --- | --- | --- |
| 1 | `total-area-comparison` / `duplicate-total-area@1` | оба `total_area` имеют `Present(Area)` | `SUPPORTS/MATERIAL`, `exact_total_area` | `CONTRADICTS/MATERIAL`, `different_total_area` | `RuleNonComparison/not_comparable_total_area` |
| 2 | `rooms-comparison` / `duplicate-rooms@1` | оба `rooms` имеют `Present(RoomCount)` | `SUPPORTS/CORROBORATING`, `exact_room_count` | `CONTRADICTS/MATERIAL`, `different_room_count` | `RuleNonComparison/not_comparable_rooms` |
| 3 | `location-text-exact` / `duplicate-location-text@1` | оба `location_text` имеют `Present(LocationText)` | `SUPPORTS/CORROBORATING`, `exact_location_text` | `RuleNonComparison/free_text_mismatch_is_neutral` | `RuleNonComparison/not_comparable_location_text` |
| 4 | `price-exact` / `duplicate-price@1` | обе суммы и обе currency имеют `Present`, currency равны | суммы равны: `SUPPORTS/AUXILIARY`, `exact_price_same_currency` | `RuleNonComparison/price_difference_is_neutral` | `RuleNonComparison/not_comparable_price` |

Если обе currency present, но различаются, price rule выдаёт
`RuleNonComparison/currency_difference_is_neutral`: конвертации и вывода о
физическом объекте нет. Совпадение только currency evidence не создаёт.

### Поля, которые намеренно не сравниваются

- `reference` и `source_url` определяют публикацию и не являются признаком
  физического объекта;
- `observed_at` определяет observation и не является duplicate evidence;
- raw representation и различия normalization provenance сами по себе не
  говорят о физической identity;
- unavailable evidence говорит о доступности publication, а не о её
  отношении к другой publication.

`location_text` — свободный текст без доказанного уровня адресной точности.
Поэтому exact canonical equality используется только как corroboration, а
любой mismatch нейтрален. Различие цены или времени также нейтрально. Exact
price match сохраняется лишь как auxiliary context и никогда не создаёт
кандидата самостоятельно.

## Детерминированная decision table

Policy v1 сначала вычисляет два булевых условия без чисел:

```text
qualifying_support =
  evidence contains SUPPORTS/MATERIAL from total-area-comparison
  AND evidence contains SUPPORTS/CORROBORATING from either
      rooms-comparison or location-text-exact

material_contradiction =
  evidence contains any CONTRADICTS/MATERIAL
```

Затем применяется ровно эта таблица:

| `qualifying_support` | `material_contradiction` | Outcome |
| --- | --- | --- |
| да | нет | `CANDIDATE_REQUIRES_MANUAL_REVIEW` |
| да | да | `CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW` |
| нет | нет | `INSUFFICIENT_EVIDENCE_NO_CANDIDATE` |
| нет | да | `INSUFFICIENT_EVIDENCE_NO_CANDIDATE` |

В последней строке противоречие сохраняется в evidence, но отсутствие
минимального supporting gate не создаёт manual-review candidate. Это outcome
о достаточности оснований текущей policy, а не утверждение, что объекты разные.

Все supporting и contradicting items сохраняются независимо от outcome.
Например, exact area и exact location вместе с different rooms дают
`CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW`: room contradiction не стирает
два supports, а supports не скрывают contradiction.

## Ограничения данных первой policy

Первый срез не содержит структурного адреса, дома/квартиры, координат,
кадастрового идентификатора, этажа, фото-хэшей или иного устойчивого
неперсонального property key. Площадь и комнаты могут совпадать у разных
объектов либо различаться из-за ошибок/способа публикации. Свободный location
может быть районом, улицей или маркетинговым текстом. Цена меняется во времени
и повторяется у разных объектов.

Поэтому:

- ни один одиночный rule не подтверждает relationship;
- candidate outcome всегда требует ручной проверки;
- большое число пар законно получает insufficient evidence;
- policy не изобретает tolerance, геокодирование, адрес, координаты,
  собственника, фото-сходство, score или probability;
- калибровка качества требует отдельного reviewed контрольного набора.

## Symmetry, equality и стабильный порядок

Алгоритм conceptually выполняет:

1. Проверить, что references различны.
2. Канонически назначить `left/right` по structural pair key.
3. Переставить observations вместе с references; не копировать отдельные поля.
4. Проверить, что оба observations available и их keys соответствуют сторонам.
5. Выполнить rules ровно в policy order.
6. Построить evidence/non-comparisons и применить точную decision table.

Для любого допустимого `A`, `B`:

```text
assess(A, B, policy) == assess(B, A, policy)
```

Равенство assessment структурное и включает identity, полные observations,
весь ordered evidence, non-comparisons и outcome. Hash, JSON bytes, object
identity или порядок вызова не являются равенством.

## Replay, новая observation и смена policy

### Exact replay и conflict равной identity

Если consumer уже знает assessment с той же `DuplicateAssessmentIdentity`:

- полностью равная assessment — `REPLAYED`, no-op;
- любое отличие full observation content, evidence, non-comparisons или
  outcome — `DUPLICATE_ASSESSMENT_CONFLICT/assessment_identity_content_conflict`;
- conflict не выбирает winner и не переписывает прежний результат.

Одинаковые observation keys с разным полным содержимым должны быть отклонены
раньше observation contracts как `timestamp_content_conflict`; duplicate layer
не исправляет и не нормализует такой конфликт.

### Новое observation

Новый `ObservationKey` хотя бы одной стороны создаёт новую assessment identity
и требует полного повторного выполнения rules. Старый evidence не копируется
и не переиспользуется. Предыдущая assessment сохраняет историческое объяснение
ровно для прежней пары observations.

### Новая версия policy

Та же пара observation keys с новой `DuplicatePolicyVersion` также создаёт
новую identity и полный recompute. Новая policy не переписывает outcome или
rule versions старой assessment.

## Current, stale и superseded

`CURRENT`/`STALE` не являются mutable полем assessment. Это производный статус
от явно переданного current context:

```text
CurrentPairContext(
  pair: PublicationPair,
  left_available_key: ObservationKey,
  right_available_key: ObservationKey,
  policy_version: DuplicatePolicyVersion
)
```

Assessment current только при полном равенстве identity этому context. Иной
key любой стороны и/или policy version делает её stale. Если current available
observation одной стороны отсутствует, прежняя assessment также не считается
current и не заменяется отрицательным результатом.

Supersession задаётся отдельной явной immutable связью, а не выводится из
времени или порядка поступления:

```text
AssessmentSupersession(
  previous: DuplicateAssessmentIdentity,
  replacement: DuplicateAssessmentIdentity
)
```

Обе identities обязаны относиться к одной pair и различаться observation key
и/или policy version. Link не удаляет previous assessment. Exact replay link —
no-op; попытка связать один previous с двумя разными replacements является
конфликтом и требует явного разрешения consumer. Pure assessment не создаёт
link сама, потому что не читает историю или storage.

Stale и superseded различаются: stale выводится относительно current context,
а superseded означает сохранённое явное указание replacement. Assessment может
быть stale до записи supersession link; historical replay остаётся допустимым.

## Атомарность будущего append без выбора storage

Будущий consumer может сохранять assessments, reviews и supersession links,
но обязан сначала полностью проверить вход:

- canonical pair и observation binding;
- policy/rule versions и стабильный порядок;
- exact replays;
- все equal-identity/different-content conflicts;
- корректность supersession/review revision links.

Только conflict-free набор применяется целиком. Любой конфликт запрещает
partial assessments, partial links и partial reviews. Этот consumer contract
не выбирает repository API, expected revision, DB/ORM, migrations, JSON,
filesystem или транзакционную технологию.

## Отдельная immutable ручная проверка

### Псевдотипы

```text
ReviewReferenceCode(value: supplied stable safe opaque ASCII code)
ReviewerCode(value: supplied stable pseudonymous safe opaque ASCII code)
ReviewRationaleCode(value: stable safe opaque ASCII code)
ReviewedAt(value: supplied canonical timestamp)

ManualReviewOutcome =
  CONFIRMED_RELATIONSHIP
  | REJECTED_RELATIONSHIP
  | INCONCLUSIVE

AssessmentFindingKind = EVIDENCE | NON_COMPARISON

AssessmentFindingReference(
  assessment_identity: DuplicateAssessmentIdentity,
  finding_kind: AssessmentFindingKind,
  rule_id: DuplicateRuleId,
  rule_version: DuplicateRuleVersion,
  polarity: EvidencePolarity | absent,
  ordinal: non-negative integer
)

ManualReviewIdentity(
  review_reference_code: ReviewReferenceCode,
  revision: positive integer
)

DuplicatePairManualReview(
  identity: ManualReviewIdentity,
  assessment_identity: DuplicateAssessmentIdentity,
  reviewed_at: ReviewedAt,
  reviewer_code: ReviewerCode,
  outcome: ManualReviewOutcome,
  rationale_codes: non-empty tuple[ReviewRationaleCode, ...],
  evidence_references: non-empty tuple[AssessmentFindingReference, ...],
  supersedes: ManualReviewIdentity | absent
)
```

`reviewed_at`, reviewer code и review reference code всегда передаются
вызывающей стороной; core не читает часы и не создаёт identity. Codes не
должны содержать имя, контакт, адрес человека или произвольный sensitive text.

Каждая reference обязана указывать существующий evidence либо non-comparison
item exact bound assessment и совпадать с его kind, rule/version/ordinal. Для
evidence polarity обязательна и должна совпасть; для non-comparison polarity
отсутствует. Поэтому inconclusive review возможна и для assessment без
положительного/отрицательного evidence, но review не добавляет и не редактирует
automatic findings.

### Revision и supersession

- revision `1` не имеет `supersedes`;
- revision `n > 1` обязана supersede ровно revision `n - 1` того же
  `ReviewReferenceCode`;
- previous record сохраняется immutable;
- `reviewed_at` новой revision строго позже previous `reviewed_at`;
- replacement может ссылаться на новую assessment только той же
  `PublicationPair`; это позволяет пересмотреть human assertion после нового
  observation или policy;
- equal review identity с полностью равным content — exact replay;
- equal review identity с иным content —
  `MANUAL_REVIEW_CONFLICT/review_identity_content_conflict`;
- две разные revision `n`, superseding одну revision `n-1`, образуют
  `MANUAL_REVIEW_CONFLICT/review_revision_fork`; winner не выбирается молча.

Текущей review считается только единственная непротиворечивая head revision.
Если её assessment stale, review остаётся исторически объяснимой, но не
становится review новой assessment автоматически.

### Смысл outcomes

- `CONFIRMED_RELATIONSHIP` — человек утверждает relationship этой exact pair на
  основании указанной assessment/evidence;
- `REJECTED_RELATIONSHIP` — человек отвергает relationship exact pair;
- `INCONCLUSIVE` — указанных оснований недостаточно для human assertion.

Даже `CONFIRMED_RELATIONSHIP` не создаёт physical property, не сливает streams,
не скрывает карточки и не изменяет automatic outcome. Все три outcomes можно
пересмотреть только новой immutable revision.

## Non-transitivity и запрет cluster/merge

Для любых трёх publications `A`, `B`, `C`:

```text
relation(A, B) AND relation(B, C) DOES NOT IMPLY relation(A, C)
```

Правило действует для automatic candidates и любых manual review outcomes.
Каждая пара требует собственной assessment и, при необходимости, review.
Connected components, transitive closure, cluster id, canonical winner,
automatic collapse и перенос evidence между парами запрещены. Исходные
publications и histories всегда остаются видимыми и независимыми.

## Privacy и safety boundary

Duplicate evidence ограничивается опубликованными неперсональными полями
первого среза. Модель не выводит и не хранит утверждения о:

- личности, контактах или роли собственника/жильца;
- текущем или предполагаемом местонахождении человека;
- гражданстве, здоровье, финансах, семейном статусе или иных чувствительных
  признаках;
- поведенческом профиле человека по времени публикации или изменениям цены.

`location_text` относится только к опубликованному описанию недвижимости и не
может интерпретироваться как местонахождение человека. Evidence и rationale
используют короткие утверждённые reason codes; произвольные цитаты, заметки и
персональные данные в эти контракты не входят.

## Минимальный будущий pure API

```text
assess_publication_pair(
  first: PublicationObservation,
  second: PublicationObservation,
  policy: DuplicatePolicy
) -> PairAssessmentSuccess | PairNotAssessed | PairAssessmentFailure

PairAssessmentSuccess(
  assessment: DuplicatePairAssessment
)

PairNotAssessed(
  pair: PublicationPair,
  left_key: ObservationKey,
  right_key: ObservationKey,
  reason_code: side_not_available
)

PairAssessmentFailure(
  conflicts: non-empty tuple[DuplicateAssessmentConflict, ...]
)

create_manual_review(
  assessment: DuplicatePairAssessment,
  supplied_review: ManualReviewDraft,
  previous: DuplicatePairManualReview | absent
) -> ManualReviewSuccess | ManualReviewFailure
```

`assess_publication_pair` канонизирует стороны и возвращает assessment только
для двух available observations разных references. `create_manual_review`
только валидирует binding/revision/supersession и возвращает immutable record;
оно не пересчитывает assessment и не изменяет histories.

Обе операции не знают batch candidate generation, storage, JSON/Pydantic,
filesystem, CLI/API/UI, сеть, часы, UUID, AI или hidden state.

## Стабильные будущие conflicts

| Category | Code | Subject | Смысл |
| --- | --- | --- | --- |
| `DUPLICATE_ASSESSMENT_CONFLICT` | `same_publication_ref` | `PublicationRef` | обе стороны ссылаются на одну publication |
| `DUPLICATE_ASSESSMENT_CONFLICT` | `observation_pair_mismatch` | `ObservationKey` | key не соответствует canonical стороне пары |
| `DUPLICATE_ASSESSMENT_CONFLICT` | `assessment_identity_content_conflict` | `DuplicateAssessmentIdentity` | та же identity имеет иное полное содержимое |
| `DUPLICATE_ASSESSMENT_CONFLICT` | `assessment_supersession_conflict` | `AssessmentSupersession` | previous связан с несовместимым replacement |
| `MANUAL_REVIEW_CONFLICT` | `review_assessment_mismatch` | `ManualReviewIdentity` | review/evidence refs не относятся к bound assessment |
| `MANUAL_REVIEW_CONFLICT` | `review_identity_content_conflict` | `ManualReviewIdentity` | equal review identity имеет иное содержимое |
| `MANUAL_REVIEW_CONFLICT` | `review_revision_mismatch` | `ManualReviewIdentity` | revision/supersedes не образуют следующий шаг |
| `MANUAL_REVIEW_CONFLICT` | `review_revision_fork` | `ManualReviewIdentity` | одна previous revision имеет два replacements |

Conflicts сортируются по canonical pair, затем observation keys/policy version,
category и code. Review conflicts после pair coordinates сортируются по review
reference code и revision. Один conflict запрещает весь future append.

## Полностью вымышленные сценарии и decision matrix

Все examples используют `fixture_portal`, `mirror_fixture` и `.example`, не
описывают реальную недвижимость или людей.

| Сценарий | Вход / evidence | Ожидаемый результат |
| --- | --- | --- |
| Симметрия | `assess(A, B)` и `assess(B, A)` над теми же full observations | полностью равные identity, snapshots, ordered evidence и outcome |
| Exact replay | уже известна полностью равная assessment той же identity | `REPLAYED`, ничего не меняется |
| Новая observation | у `B` новый available key, значения прежние | новая identity и полный recompute; старая assessment stale, но сохранена |
| Новая policy | keys те же, policy `@2` | новая identity; evidence `@1` не копируется и не переписывается |
| Equal identity conflict | тот же assessment key/policy, но иной evidence/outcome | `assessment_identity_content_conflict`, no overwrite |
| Одинаковые present поля с provenance | area `4700`, rooms `2`, location `"Demo district"` равны; provenance каждой стороны указывает свою reference | три supporting items сохраняют отдельные left/right provenance; candidate manual review |
| `Missing` / `Unsupported` | area missing слева, rooms unsupported справа | два `RuleNonComparison`; нет contradicting evidence; insufficient |
| Supporting + contradicting | area и location равны, rooms `2` против `3` | два supports и room contradiction сохранены; conflicting manual review |
| Insufficient input | равна только цена либо только rooms/location без exact area | auxiliary/corroborating evidence сохранено; insufficient/no candidate |
| Same-source repost | `fixture_portal/a-1` и `fixture_portal/a-2`, area+rooms равны | допустимая pair; candidate при выполненном gate, без merge |
| Cross-source candidate | `fixture_portal/a-1` и `mirror_fixture/z-9`, area+location равны, rooms missing | candidate manual review; sources остаются независимы |
| Location mismatch | area+rooms равны, свободный location text различается | location non-comparison neutral; candidate по area+rooms |
| Price/time mismatch | area+rooms равны, price и observed times различаются | price neutral, times не rule; candidate по area+rooms |
| Unavailable side | `A` available, `B` unavailable | `PairNotAssessed/side_not_available`; zero duplicate evidence/outcome |
| Manual confirm | review revision 1 с exact evidence refs | separate `CONFIRMED_RELATIONSHIP`; no merge/stream change |
| Manual reject | review revision 1 с exact evidence refs | separate `REJECTED_RELATIONSHIP`; automatic evidence неизменно |
| Manual inconclusive | review revision 1 с exact evidence refs | separate `INCONCLUSIVE`; automatic outcome неизменно |
| Review supersession | revision 2 позже supersedes revision 1 и ссылается на новую assessment той же pair | обе revisions сохранены; head — revision 2 |
| Review identity conflict | revision 2 replayed с иным outcome | `review_identity_content_conflict`; revision 1/head не переписаны |
| Non-transitivity | reviews подтверждают `A~B` и `B~C` | `A~C` отсутствует до отдельной assessment/review; cluster не создаётся |

## Намеренно отложено

- Python-типы, pure operations и тесты этой спецификации — TASK-019;
- batch candidate generation, blocking/indexing и performance optimization;
- хранение assessments/reviews, repository adapter, revision implementation,
  DB/ORM/migrations и внешний формат;
- JSON/Pydantic/filesystem boundary, CLI/API/UI;
- реальные sources, HTTP, polling, scheduler, retries/rate limits;
- новые нормализованные поля, tolerance, геокодирование и фото-сходство;
- quality dataset, precision/recall и любая числовая калибровка;
- `PhysicalProperty`, merge/collapse, canonical winner, clustering и
  transitive closure;
- AI/embeddings/LLM, персональные сигналы, OpenClaw, Telegram и уведомления.
