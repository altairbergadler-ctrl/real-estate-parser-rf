# Архитектура

## Начальная форма

Проект начинается как модульный монолит: единое развёртываемое приложение с жёстко обозначенными внутренними границами. Это позволяет быстрее построить минимальный сквозной сценарий без преждевременных сетевых границ и при этом сохранить возможность позднее отделить действительно независимые части.

Модульный монолит — архитектурное направление, а не обязанность использовать конкретный веб-фреймворк, базу данных или способ развёртывания. Минимальный языковой и инструментальный базис принят в [решении 0001](docs/decisions/0001-python-application-baseline.md); остальные технологии выбираются только отдельными задачами.

## Минимальное стабильное ядро

Ядро содержит только устойчивые предметные понятия и контракты, необходимые нескольким модулям. Для первого среза это идентичность источника и публикации, наблюдаемый снимок публикации, нормализованное объявление, происхождение отдельного значения, состояния поля, критерии поиска и совпадение. Точные типы приняты в [решении 0003](docs/decisions/0003-domain-model-and-contract-boundaries.md) и описаны в [спецификации модели](docs/design/DOMAIN-MODEL-AND-CONTRACTS.md).

Ядро:

- не знает форматы и особенности конкретных сайтов;
- не вызывает конкретного ИИ-провайдера;
- не зависит от OpenClaw, Telegram или пользовательского интерфейса;
- не содержит сетевой, файловой или иной инфраструктуры, если она не является частью предметной модели;
- не принимает решений о доставке уведомлений или способе запуска процесса.

Физический объект недвижимости не является сущностью первого среза: до дедупликации приложение знает только публикации источников. Будущие сущности объектов, доказательные сигналы и результаты сопоставления добавляются отдельными задачами и не изменяют идентичность исходных публикаций.

## Технологический базис

Для первого среза принят CPython 3.14, управление проектом через `uv`, Pydantic для строгой проверки недоверенных входных и выходных данных, pytest для тестов, Ruff для форматирования и линтинга и mypy для статической проверки типов. Подробности, ограничения и рассмотренные варианты находятся в [решении 0001](docs/decisions/0001-python-application-baseline.md).

Pydantic не является моделью ядра по умолчанию. Ядро и прикладные правила используют обычные явно типизированные Python-объекты; технологические модели преобразуются на границах. Это сохраняет минимальное стабильное ядро независимым от формата JSON, CLI и будущего API.

Первый срез запускается локально через командный интерфейс, использует только фикстуры и память процесса и описан в [решении 0002](docs/decisions/0002-first-local-vertical-slice.md) и [детальном проекте](docs/design/FIRST-VERTICAL-SLICE.md). Наличие CLI не делает ядро зависимым от интерфейса запуска.

Стратегия проверок, точные source-specific документы и byte-exact эталоны приняты в [решении 0004](docs/decisions/0004-test-fixture-and-golden-policy.md) и [спецификации fixtures](docs/design/TEST-STRATEGY-AND-FIXTURES.md). Статические JSON-файлы являются данными внешней границы и не превращаются в модели ядра.

Граница TASK-006 читает ровно один явно переданный локальный файл и преобразует строгую Pydantic-модель `fixture-source-batch@1` в обычный неизменяемый `ValidatedSourceBatch`. Структурные locations, provided/missing source fields и ошибки границы не зависят от Pydantic, JSON или filesystem; содержательные правила источника остаются ответственностью отдельного внешнего адаптера.

TASK-007 реализует эту отдельную границу как чистую операцию `ValidatedSourceBatch → SourceBatch | SOURCE_ADAPTER`. Фиктивный адаптер назначает канонический `fixture_portal`, проверяет только его publication id и исходный URL и без преобразования переносит строки и locations в нейтральные `SourcePublicationSnapshot`. Он не знает файлов, JSON, Pydantic, сети, нормализации или коллекции.

Граница TASK-010 читает один явно переданный UTF-8 JSON-документ
`search-criteria@1`, строго проверяет его Pydantic-модель и атомарно
преобразует её в обычный immutable `SearchCriteria`. Канонические `Money`,
`Area`, `RoomCount`, результат и `ContractIssue` не зависят от Pydantic, JSON,
filesystem и абсолютного пути. Поиск остаётся отдельной чистой операцией.

TASK-011 реализует эту операцию как
`CollectionSnapshot + SearchCriteria → SearchResult`. Она применяет критерии
конъюнктивно, сохраняет ссылки на исходные `NormalizedListing` и канонически
сортирует совпадения независимо от порядка коллекции. Поиск не знает Pydantic,
JSON, filesystem, output mapping, CLI и внешние источники.

TASK-012 реализует следующий чистый переход
`SearchResult → SearchResultDocument`. Mapper переводит канонические wrapper-типы
в утверждённые строки и integer, структурно разделяет provided и missing
provenance, сохраняет состояния каждого поля и уже заданный порядок matches.
Document tree остаётся обычным frozen/slots Python-контрактом без Pydantic,
JSON, bytes, filesystem, CLI, часов и внешних источников.

TASK-013 добавляет внешнюю output boundary поверх этого готового
document tree. Приватные strict Pydantic-модели зеркалят точную
форму `search-result@1`; публичная операция атомарно возвращает
канонические UTF-8 JSON bytes либо одну безопасную
`OUTPUT_CONTRACT/invalid_result_document/$` issue. Граница не выполняет
поиск, не пересчитывает значения, не сортирует matches и не знает
filesystem или CLI.

TASK-014 завершает первый локальный срез отдельным application orchestrator:
он принимает два явных `Path`, независимо загружает оба документа, глобально
сортирует их content issues и только при полном успехе последовательно вызывает
готовые adapter, collection, search, mapper и serializer. Минимальные
frozen/slots result-типы содержат либо полные canonical bytes, либо непустые
issues; operational file/decode failures остаются отдельным исключительным
каналом. Тонкий `argparse` CLI переводит эти исходы в stdout/stderr и exit codes,
не проникая в ядро и не сериализуя успешные bytes повторно.

TASK-015 принимает архитектуру повторных наблюдений без программной
реализации. Один `PublicationObservationStream` принадлежит ровно одной
`PublicationRef`; `ObservationKey` образуют reference и канонический
`ObservedAt`. Готовый `NormalizedListing` переносится в available observation
целиком с provenance, а unavailable observation допускается только с прямым
source state либо conclusive targeted-check evidence. Отсутствие записи в batch
и операционная ошибка не являются событиями истории.

Чистая версионированная comparison policy различает canonical field change,
source-representation-only change, provenance refresh и пустой успешный
`ChangeSet`. История принимает только строго возрастающие новые наблюдения;
exact replay идемпотентен, equal-timestamp/different-content и новый
out-of-order key являются конфликтами. Точные типы и переходы заданы в
[решении 0005](docs/decisions/0005-publication-observations-and-changes.md) и
[спецификации наблюдений](docs/design/PUBLICATION-OBSERVATIONS-AND-CHANGES.md).
Конкретное хранилище остаётся внешним адаптером будущего consumer-owned port и
этой задачей не выбирается.

TASK-016 реализует эту семантику одним нейтральным модулем ядра. Frozen/slots
`PublicationObservationHistory` хранит tuple строго возрастающих available и
доказательно unavailable observations одной `PublicationRef` и версии policy.
Чистые `compare_consecutive_observations` и `append_observation` не знают
Pydantic, JSON, filesystem, CLI или storage: они возвращают immutable
`ChangeSet`, exact replay либо стабильный atomic conflict без partial history.
Первая policy сравнивает только шесть утверждённых полей, исключает координату
`ObservedAt` из изменения provenance и не превращает missing field или
операционную ошибку в недоступность публикации.

TASK-017 реализует batch/multi-history boundary отдельным нейтральным модулем
прикладной композиции, зависящим от публичного pure append TASK-016.
`PublicationObservationHistories` принимает только tuple, обеспечивает
уникальность stream по `PublicationRef` и хранит histories канонически.
Композиция группирует и сортирует непустой tuple observations, сворачивает
exact duplicates, создаёт отсутствующие streams как пустые histories текущей
policy и вызывает `append_observation` для каждого уникального допустимого
key. Только полностью успешный batch выдаёт новые histories и item outcomes;
любой globally ordered conflict set выдаётся без partial state. Эта граница не
является repository port и не вводит storage lookup, revision или I/O.

TASK-018 принимает отдельную pairwise-модель duplicate evidence в
[решении 0006](docs/decisions/0006-publication-duplicate-evidence.md) и
[детальной спецификации](docs/design/PUBLICATION-DUPLICATE-EVIDENCE.md).
Неупорядоченная пара строится из двух разных `PublicationRef`, а assessment
привязана к точным available observation keys и версии policy. Supporting и
contradicting evidence не схлопываются в numeric score; missing, unsupported и
unavailable input не становятся отрицательным фактом. Manual review хранится
отдельной immutable revision. Ни автоматический, ни human outcome не создаёт
physical property, не объединяет histories и не допускает transitive cluster.

TASK-019 реализует эту модель отдельным нейтральным core-модулем, который
зависит только от готовых normalization и publication-observation contracts.
`assess_publication_pair` канонизирует две publications вместе с полными
observations, выполняет ровно четыре rules `publication-duplicate-policy@1` и
возвращает immutable assessment, `PairNotAssessed` либо atomic conflicts.
Field snapshots повторно используют canonical outcome и provenance типов
TASK-016; supporting, contradicting и non-comparable findings остаются
раздельными и policy-ordered. Current/stale вычисляется только из явно
переданного context, supersession является отдельной immutable link, а
`create_manual_review` валидирует supplied identity/time, exact finding
references и revision chain без часов, UUID, I/O, storage или hidden state.

TASK-020 реализует отдельный neutral quality-модуль поверх публичных pair
results TASK-019. Pair-bound independently supplied label намеренно не
переиспользует assessment-bound manual review. Непустой tuple-only control set
атомарно валидирует exact pair/result/policy binding, unique pairs и canonical
order. Pure evaluation считает counts и только exact integer ratios;
precision требует conclusive labels своего review-required denominator, а
recall — всей population. Typed unavailable reasons сохраняют недостаточность
labels без нуля или исключения. Модуль не пересчитывает assessment и не вводит
candidate generation, storage, sampling, physical property, merge или cluster.

TASK-021 принимает design-only bounded boundary перед вызовом assessment
TASK-019 в
[ADR 0008](docs/decisions/0008-duplicate-candidate-generation.md) и
[design-спецификации](docs/design/PUBLICATION-DUPLICATE-CANDIDATES.md).
Отдельная `publication-duplicate-candidate-policy@1` проецирует каждый current
`AvailableObservation` максимум в два exact typed keys, группирует только
совпавшие keys и union/deduplicates materialized pairs. Caller-supplied positive
limit применяется к exact prospective count каждого bucket; oversized bucket
целиком остаётся immutable outcome без partial first-N. Candidate identity
сохраняет canonical pair и exact observation keys, но blocking match не
становится duplicate evidence. При фиксированном limit pair attempts
ограничены `2NL`, global quadratic scan и fallback отсутствуют. Отдельная
blocking coverage использует только eligible confirmed cases supplied fully
fictional control set и не заявляет production recall.

TASK-022 реализует только generation boundary отдельным neutral core-модулем,
зависящим от normalization/observation contracts и canonical
`PublicationPair`. Pure operation принимает явный caller-selected current
tuple, атомарно отклоняет unavailable/unsupported/identity conflicts и после
канонизации проецирует каждую available observation максимум в два exact typed
keys либо ordered non-participations. Whole-bucket limit применяется к exact
prospective count до pair materialization; допустимые buckets разворачиваются
полностью, oversized buckets сохраняют canonical membership без partial
first-N. Candidate union не вызывает assessment и не создаёт evidence,
outcome, storage/index или blocking coverage.

TASK-023 добавляет отдельную pure composition над публичными contracts
TASK-019/020/022. Она не повторяет generation или assessment: exact snapshots
готовой assessment определяют общие v1 blocking keys, а canonical generation
identity, candidates и oversized outcomes определяют eligibility и coverage.
Все disjoint counts и разные policy identities сохраняются в одном immutable
success; отсутствие candidate при общем non-oversized key атомарно возвращает
только canonical coverage conflicts без partial metric. Эта композиция не
вводит I/O, storage/index, hidden all-pairs scan, physical property, merge или
cluster и не интерпретирует fictional coverage как production recall.

TASK-024 design-only принимает следующую отдельную pure composition поверх
public contracts TASK-019/022. Batch identity сохраняет exact generation
identity и независимую explicit assessment policy version, а success — полный
generation result, assessment policy и ordered item outcomes. Canonical current
available context обязан exact совпасть с generation keys; missing, extra и
new-key той же reference различаются structural conflicts. Preflight failure
не вызывает assessment, valid pass вызывает существующую single-pair operation
ровно один раз на materialized candidate и атомарно отклоняет весь batch при
любом downstream conflict без partial outcomes. Composition не повторяет
blocking/generation, не превращает routing matches в evidence и не вводит
storage, physical property, merge, cluster или transitive closure.

TASK-025 реализует эту composition отдельным neutral core-модулем, зависящим
только от public contracts TASK-019/022. Frozen/slots batch identity сохраняет
exact generation identity и отдельную assessment policy version, а complete
success — full generation result, full assessment policy и ordered exact item
assessments. Phase-gated preflight валидирует весь current context и candidate
binding до первого call. Затем linear reference lookup передаёт existing pair
operation exact full available sides ровно один раз на supplied candidate;
любой downstream conflict оставляет только canonical atomic failure после
полного pure pass. Модуль не повторяет generation, не вводит storage/I/O или
side-effecting execution и не создаёт physical property либо transitive
relation.

TASK-026 design-only принимает storage-neutral persistence/replay boundary в
[ADR 0010](docs/decisions/0010-publication-persistence-and-replay.md) и
[спецификации](docs/design/PUBLICATION-PERSISTENCE-AND-REPLAY.md). Immutable
observations и supplied human assertions authoritative только в своих exact
contexts; deterministic changes, generation, assessments и committed quality
inputs остаются version-bound derived/audit records, а heads, current/stale,
indexes и metrics — rebuildable projections. Application consumers владеют
пятью узкими ports для histories, generation, assessment batch, manual review
и quality audit. Exact replay проверяется до optimistic expected revision,
equal identity/different content никогда не overwrite, а multi-history,
generation/assessment и review units фиксируются all-or-nothing.

TASK-027 реализует этот application boundary отдельным neutral
contracts-модулем и отдельным in-memory infrastructure adapter. Пять
consumer-owned Protocol ports принимают только exact typed requests и
возвращают frozen/slots outcomes; generic repository, backend session и
transaction API отсутствуют. Reference adapter выдаёт opaque revisions
детерминированным внутренним счётчиком без clock/UUID/random/hash,
проверяет exact replay до expected revision и делает каждую
назначенную unit видимой только целиком. Он не вызывает pure
generation/assessment/review/quality operations и не определяет
production orchestration или durable technology.

## Модули и ответственность

- **Источники** получают сырые объявления и метаданные происхождения. Каждый источник изолирует особенности площадки за общим входным контрактом.
- **Нормализация** преобразует сырые значения в каноническое представление, не скрывая исходные данные и неопределённость.
- **Устранение дублей** pairwise оценивает две независимые публикации как
  возможный relationship: bounded exact blocking сначала формирует объяснимые
  candidates, а отдельная assessment хранит симметричные положительные и
  отрицательные основания и отдельную ручную проверку. Ни один шаг не
  уничтожает identity, provenance или histories исходных объявлений и не
  создаёт transitive cluster.
- **Сигналы** вычисляют доказательные стандартные и нестандартные признаки, уверенность и необходимость ручной проверки. ИИ в будущем может быть одной из необязательных реализаций внутри этой границы.
- **Поиск** применяет критерии к нормализованным объявлениям и сигналам, не зная, откуда и каким интерфейсом пришёл запрос.
- **Уведомления** определяют события и предпочтения доставки, но не привязывают ядро к конкретному каналу.
- **Интеграции** адаптируют внешние системы и интерфейсы — в будущем, например, OpenClaw и Telegram — к прикладным контрактам проекта.

Хранилище, планирование запусков, наблюдаемость и пользовательские интерфейсы
являются инфраструктурными или внешними аспектами. Persistence contracts
принадлежат consuming application boundaries: adapters реализуют их снаружи и
не передают внутрь backend query/session/transaction types. Общий
`Repository[T]` не вводится. Opaque revisions являются только concurrency
tokens конкретных slots, не domain identities или timestamps. Конкретные
technology, schema, serialization и transaction mechanism выбираются позднее
по измеренным требованиям и не меняют exact replay/no-partial-write contract.

## Явные контракты

Модули взаимодействуют через небольшие явные контракты: входные и выходные структуры, интерфейсы операций, события и описанные ошибки. Контракт принадлежит потребляющей предметной границе, а адаптер конкретной технологии реализует его снаружи.

Контракты должны позволять:

- тестировать модуль без реального сайта, ИИ и мессенджера;
- заменять источник или интеграцию без изменения ядра;
- сохранять происхождение и доказательства на каждом переходе;
- отличать отсутствие данных, ошибку и отрицательный результат;
- версионировать несовместимые изменения осознанно.

Зависимости направляются к ядру и прикладным контрактам. Циклические зависимости между модулями не допускаются.

В первом срезе контракт приёма публикаций принадлежит прикладной границе, контракт коллекции — потребляющей границе поиска, а source-specific и выходные адаптеры реализуют их снаружи. Происхождение принадлежит каждому значению; передача нормализованного значения без происхождения через корректный контракт не допускается. Коллекция строится атомарно, а ошибка любой записи исключает частичный результат всего пакета.

## Плагины

Динамический загрузчик внешних плагинов пока не создаётся. На начальном этапе вариативность обеспечивается обычными внутренними интерфейсами и явно подключёнными адаптерами. Механизм динамических плагинов может появиться только после подтверждённой потребности и отдельного архитектурного решения.

## Архитектурные изменения

Существенное решение, меняющее границы, направление зависимостей, модель данных или эксплуатационные свойства, фиксируется отдельной записью в `docs/decisions/`. Документ должен описывать контекст, решение, последствия и рассмотренные варианты.
