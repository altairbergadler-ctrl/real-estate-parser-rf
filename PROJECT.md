# Проект

## Назначение продукта

«Парсер недвижимости» помогает искать объявления о недвижимости по России в едином представлении, даже если исходные данные опубликованы на разных площадках и различаются по формату. Продукт должен собирать объявления, нормализовать их, выявлять дубли и предоставлять поиск по обычным характеристикам и по осторожно сформулированным нестандартным признакам.

Проект не должен превращать предположение в установленный факт. Любой вывод, который нельзя получить напрямую из структурированного поля объявления, должен оставаться проверяемой гипотезой с прозрачным основанием.

## Основные пользовательские сценарии

- Задать единый набор критериев и искать подходящие объявления сразу в нескольких источниках.
- Сравнить нормализованные карточки без необходимости вручную сопоставлять форматы площадок.
- Не тратить время на повторные публикации одного объекта благодаря группировке дублей.
- Сохранить поиск и получать уведомления о новых или существенно изменившихся предложениях.
- Отфильтровать небольшой набор кандидатов по нестандартным сигналам и вручную проверить основания каждого сигнала.
- Понять происхождение данных: источник, время получения, исходную ссылку и доступные доказательства.

## Параметры поиска

### Стандартные параметры

К стандартным относятся явно опубликованные и относительно однозначные характеристики: тип сделки и объекта, регион и адресная привязка, цена, площадь, число комнат, этаж, параметры дома, состояние, наличие мебели и другие поля, которые конкретный источник действительно предоставляет.

Конкретная каноническая схема и правила разрешения противоречий будут спроектированы отдельными задачами. Отсутствующее значение не подменяется догадкой.

### Нестандартные параметры и сигналы

Нестандартный параметр — это поисковый признак, который обычно не представлен готовым структурированным полем. Например: вероятность того, что собственник находится за границей и редко посещает сдаваемый объект.

Такой признак хранится и показывается только как сигнал, а не как безусловный факт. Сигнал должен содержать:

- точное утверждение или тип гипотезы;
- основания и ссылки на исходные данные;
- короткие цитаты или наблюдаемые признаки, если они допустимы;
- способ получения сигнала и версию правила или модели;
- уровень уверенности с понятной интерпретацией;
- явную пометку о необходимости ручной проверки;
- время формирования и возможность пересмотра.

Недостаток данных должен уменьшать уверенность или приводить к отсутствию сигнала, а не к выдуманному значению. Чувствительные предположения требуют особенно строгого обоснования и осторожной формулировки.

## Экономичная каскадная обработка

Обработка строится от дешёвых и детерминированных шагов к дорогим и вероятностным:

1. Получение только необходимых данных в рамках правил источника.
2. Структурная валидация, нормализация и раннее отбрасывание заведомо неподходящих объявлений.
3. Устранение дублей и применение обычных фильтров и правил.
4. Вычисление недорогих сигналов по уже отобранным кандидатам.
5. Необязательный ИИ-анализ только малого предварительно отобранного набора, если он отдельно включён и экономически оправдан.
6. Представление результата пользователю с доказательствами и возможностью ручной проверки.

Основной рабочий контур не требует ИИ. Отказ или отсутствие ИИ-модуля не должны останавливать сбор, нормализацию, дедупликацию и стандартный поиск.

## Доказательный подход

- Сохраняется происхождение каждого существенного значения.
- Факты из источника отделяются от вычисленных выводов.
- Предположительные признаки сопровождаются основаниями, уверенностью и статусом проверки.
- Пользователь может перейти от сигнала к подтверждающим фрагментам и исходному объявлению.
- Правила и модели должны быть версионируемыми, чтобы результат можно было объяснить и пересчитать.
- Спорный или недостаточно подтверждённый сигнал не используется как окончательное решение без участия пользователя.

## Текущие границы

После TASK-014 к документальному фундаменту, каркасу, границе пакета
`fixture-source-batch@1`, фиктивному source adapter, нормализации и
атомарному `CollectionSnapshot` добавлена строгая внешняя граница
`search-criteria@1` и чистая операция стандартного поиска. Граница criteria
атомарно преобразует один Path/UTF-8/JSON документ
в полный neutral immutable `SearchCriteria` из канонических `Money`, `Area` и
`RoomCount` либо в упорядоченные `ContractIssue`; поиск применяет готовые
criteria к `CollectionSnapshot` и возвращает упорядоченный immutable
`SearchResult`, сохраняющий ссылки на исходные listings. Чистый mapper
преобразует готовый результат в строго типизированный frozen/slots
`SearchResultDocument` версии `search-result@1`, сохраняя все состояния и
provenance без Pydantic, JSON и файлов. Отдельная внешняя output
boundary строго проверяет готовый document приватными Pydantic-моделями
и атомарно возвращает канонические UTF-8 JSON bytes либо безопасную
`OUTPUT_CONTRACT` issue. Первый срез
по-прежнему различает публикацию источника и будущий физический объект.

Минимальный application orchestrator связывает эти готовые границы в один
атомарный path-level flow, а тонкий CLI предоставляет команды
`uv run real-estate-parser search ...` и `python -m real_estate_parser`.
Успех выдаёт только canonical JSON bytes, contract failure — только безопасные
issue-строки, operational file/decode failure — безопасную роль входа и общий
код причины. Первый детерминированный локальный срез завершён и проверен
subprocess E2E-тестами без сети, часов и случайности.

TASK-016 реализует принятый следующий предметный слой, не изменяя исполняемый
срез: frozen/slots history объединяет observations только одной
`PublicationRef` и одной comparison policy, а чистые операции сравнивают
последовательные observations и атомарно добавляют ровно одно новое наблюдение.
`publication-change-policy@1` детерминированно различает substantive,
source-representation-only и provenance refresh для шести утверждённых полей.
Exact replay идемпотентен, конфликты не выдают partial history или changes.
Подтверждённая недоступность по-прежнему требует direct source state либо
conclusive targeted check; batch omission и operational failures не имеют пути
создания unavailable observation. Reappearance не создаёт физический объект и
не стирает provenance предыдущих наблюдений.

TASK-017 добавляет отдельную чистую прикладную композицию поверх single-history
операции TASK-016. Immutable контейнер хранит не более одной history на
`PublicationRef` в каноническом порядке, а непустой tuple candidates
группируется по reference и времени независимо от порядка входа. Exact
duplicates одного observation сворачиваются; успешный batch возвращает полный
набор histories и канонические item outcomes, а любой набор доказуемых
conflicts атомарно отклоняет все streams без partial histories, dispositions
или `ChangeSet`. Новые streams начинаются с логически пустой history версии
переданной policy; storage lookup и concurrency в этой композиции отсутствуют.

TASK-018 документально принимает доказательную модель возможных дублей без
программной реализации. Автоматическая оценка относится только к
неупорядоченной паре двух разных `PublicationRef`, точным
`AvailableObservation` обеих сторон и версии policy. Она сохраняет отдельно
supporting, contradicting и not-comparable основания и возвращает только
категориальную необходимость ручной проверки либо недостаточность данных —
никогда подтверждённый физический объект. Ручная проверка является отдельной
immutable revision; она не меняет evidence, не сливает streams и не делает
pairwise relation транзитивной. Точный контракт принят в
[ADR 0006](docs/decisions/0006-publication-duplicate-evidence.md) и
[спецификации duplicate evidence](docs/design/PUBLICATION-DUPLICATE-EVIDENCE.md).

TASK-019 реализует этот контракт одним нейтральным pure-модулем. Canonical
`PublicationPair`, точные observation keys и версия policy образуют
структурную identity; полные field outcomes и provenance сохраняются в
policy-ordered evidence либо non-comparison. Чистая симметричная операция
оценивает только две available observations, а unavailable side возвращает
отдельный `PairNotAssessed` без categorical outcome. `publication-duplicate-policy@1`
строго применяет четыре правила и консервативную decision table без score,
probability или tolerance. Current/stale context, explicit assessment
supersession и отдельные immutable manual-review revisions также не создают
physical property, merge, cluster или transitive relation.

TASK-020 добавляет отдельный neutral pure quality layer над готовыми exact
pair results. Непустой immutable control set хранит не более одного case на
canonical pair, единую explicit policy version, exact
`PairAssessmentSuccess | PairNotAssessed` и independently supplied pair-bound
confirm/reject/inconclusive label. Чистая evaluation сохраняет categorical
outcome/not-assessed/review-required counts, exact assessment coverage и
population review load. Precision и recall представлены только integer
numerator/denominator либо typed причиной недоступности; recall требует
conclusive labels всей population, поэтому confirmed insufficient и
not-assessed cases остаются видимыми false negatives. Human label не выводится
из policy outcome и не создаёт physical property, merge или cluster.

TASK-021 design-only принимает отдельный bounded candidate-generation
контракт в [ADR 0008](docs/decisions/0008-duplicate-candidate-generation.md) и
[детальной спецификации](docs/design/PUBLICATION-DUPLICATE-CANDIDATES.md).
Непустой canonical набор current `AvailableObservation` участвует
максимум в двух exact blocking passes — `total_area + rooms` и
`total_area + location_text` — по отдельной
`publication-duplicate-candidate-policy@1`. Caller передаёт positive bucket
pair limit; oversized bucket целиком не разворачивается и остаётся явным
outcome с exact prospective count. Multi-pass union сохраняет exact matches,
но не создаёт duplicate evidence или assessment. Missed-pair risk выражается
exact blocking coverage только на supplied fully fictional reviewed control
population с отдельными PairNotAssessed/outside/stale counts.

TASK-022 реализует generation-часть этого контракта отдельным neutral
frozen/slots-модулем. `publication-duplicate-candidate-policy@1` содержит
ровно два exact typed blocking passes; pure operation атомарно валидирует
явный непустой tuple current observations, канонизирует его и создаёт максимум
две memberships на observation. Для каждого bucket exact prospective count
вычисляется до pair loops: bucket сверх caller limit целиком остаётся
`OversizedBucket`, а допустимый bucket полностью materializes canonical pairs.
Union сохраняет все и только materialized matches в policy order, включая
alternate route при oversized другом pass. Missing/Unsupported participation,
empty candidate success и generation conflicts остаются явными; assessment и
blocking coverage не выполняются.

TASK-023 реализует отдельный neutral pure blocking-coverage слой поверх уже
валидных `DuplicatePolicyControlSet` и `DuplicateCandidateGenerationResult`.
Evaluation сохраняет разные assessment/candidate policy identities и exact
generation identity, затем классифицирует каждый conclusively confirmed case
как PairNotAssessed, outside input, stale keys либо eligible. Eligible cases
считаются covered, no-shared-key miss или whole-oversized-bucket miss; общий
non-oversized key без exact candidate даёт атомарный
`generation_result_inconsistent` без partial metrics. Exact ratio остаётся
несокращённой integer-дробью, а inconclusive labels и нулевой eligible
denominator имеют typed unavailable reasons. Метрика относится только к
supplied fully fictional population и не заявляет production recall.

TASK-024 design-only принимает отдельную pure atomic composition в
[ADR 0009](docs/decisions/0009-duplicate-candidate-assessment-batch.md) и
[детальной спецификации](docs/design/PUBLICATION-DUPLICATE-ASSESSMENT-BATCH.md).
Она exact связывает готовый `DuplicateCandidateGenerationResult` с полным
caller-supplied canonical context только из `AvailableObservation` и отдельно
переданной `publication-duplicate-policy@1`. Все preflight conflicts дают zero
assessment calls; valid input вызывает существующую
`assess_publication_pair` ровно один раз для каждого и только materialized
candidate. Downstream conflicts собираются полным pure pass, но failure не
содержит partial item outcomes. Blocking matches остаются routing metadata, а
batch не повторяет generation, не создаёт physical property, merge, cluster
или transitive relation.

TASK-025 реализует этот контракт отдельным neutral frozen/slots core-модулем.
Phase-gated preflight атомарно проверяет exact full candidate/assessment
policies, caller-supplied current available context, generation/current keys и
каждый supplied candidate до первого pair call. Valid empty candidates дают
complete empty success; остальные вызывают existing `assess_publication_pair`
ровно один раз в canonical candidate order с exact full current sides и
explicit assessment policy. Downstream conflicts собираются полным pure pass,
но failure не содержит partial item outcomes. Success сохраняет full generation
result, full assessment policy и ordered exact bound assessments; blocking
matches остаются только routing metadata.

TASK-026 design-only принимает consumer-owned persistence/replay boundary в
[ADR 0010](docs/decisions/0010-publication-persistence-and-replay.md) и
[детальной спецификации](docs/design/PUBLICATION-PERSISTENCE-AND-REPLAY.md).
Authoritative state ограничен immutable available/unavailable observations и
supplied human assertions в их точном контексте. Deterministic generation,
assessment и version-bound control artifacts остаются derived, но committed
экземпляр, использованный side-effecting workflow, сохраняется как immutable
audit; current/stale, heads/indexes и quality metrics являются rebuildable
projections. Пять небольших consumer-owned ports задают explicit expected
revisions, exact replay до stale-revision conflict, equal-identity/different-
content conflicts и отдельные all-or-nothing units для multi-history append,
generation/assessment и manual-review revision без generic repository или
выбора storage technology.

В текущий объём по-прежнему не входят запись JSON на диск, постоянное хранение,
реальный persistence adapter, side-effecting assessment execution, clustering,
база данных, API, интерфейс, парсеры реальных площадок, Docker, ИИ, OpenClaw,
Telegram и публикация удалённого репозитория. Persistence design не выбирает
SQL/JSON/filesystem schema, transaction manager, cache, queue, scheduler или
distributed lock. Candidate policy не выбирает bucket limit, не запускает
assessment и не заявляет production recall, репрезентативность или юридическую
допустимость сбора. Выбор Python-базиса не является выбором всех будущих
инфраструктурных компонентов: они добавляются только по подтверждённой
потребности. Соблюдение правовых требований, условий площадок, ограничений на
сбор и хранение данных будет конкретизировано до реализации реальных
источников.
