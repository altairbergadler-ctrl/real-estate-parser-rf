# 0008. Ограниченное deterministic blocking для duplicate candidate pairs

- Статус: принято
- Дата: 2026-09-02
- Задача: TASK-021

## Контекст

TASK-019 умеет чисто оценить ровно одну явно переданную пару публикаций по
`publication-duplicate-policy@1`, а TASK-020 измеряет качество уже готовых
pair results на полностью вымышленном reviewed control set. Ни один из этих
контрактов не определяет, как из набора current observations получить
ограниченный набор пар для последующей оценки.

Полный перебор всех `n * (n - 1) / 2` пар скрыто сделал бы candidate generation
квадратичной. Один blocking key, напротив, хрупок: отсутствие одного поля
необъяснимо исключило бы потенциальную пару. Ограничение bucket через первые
`N` пар зависело бы от порядка и молча теряло остальные пары. Нужен отдельный
версионированный pure-контракт, который использует только доступные canonical
значения, ограничивает materialization, сохраняет причины непопадания и
позволяет отдельно измерить риск пропуска.

## Рассмотренные варианты

### Полный quadratic all-pairs scan

Отклонено. Даже если assessment остаётся pure, предварительное создание всех
пар имеет квадратичную работу и память, не использует принятый candidate gate
ADR 0006 и скрывает отсутствие реального ограничения.

### Один exact blocking key

Отклонено. Только `total_area + rooms` теряет observations без rooms, а только
`total_area + location_text` зависит от свободного location text. Один pass не
соответствует дизъюнкции candidate gate ADR 0006 и повышает риск пропуска без
явного измерения.

### Union нескольких deterministic blocking passes

Принято. Каждое observation независимо участвует максимум в двух exact passes,
а итоговые пары объединяются структурно. Одна пара может сохранить оба
совпавших ключа. Полного fallback scan нет.

### Silent truncation oversized bucket

Отклонено. Выбор первых `N` пар зависит от порядка materialization, выдаёт
частичный bucket за полный и не позволяет отличить сформированную пару от
молча отброшенной.

### Explicit oversized-bucket outcome

Принято. До materialization вычисляется точное число prospective pairs.
Bucket, превышающий переданный caller limit, целиком не разворачивается и
остаётся явным immutable outcome с полным membership и причиной. Partial
first-N запрещён.

## Решение

- Вход — непустой immutable набор current `AvailableObservation`. После
  атомарной проверки он хранится в canonical order и содержит не более одного
  observation на `PublicationRef`.
- `UnavailableObservation`, unsupported input object, повтор reference и
  одинаковый `ObservationKey` с разным полным содержимым являются contract
  failures. Они не превращаются в отсутствие ключа или пустой результат.
- Same-source и cross-source pairs разрешены. Одна `PublicationRef` никогда не
  образует пару сама с собой.
- Candidate policy версионируется отдельно от assessment policy. Первая версия
  `publication-duplicate-candidate-policy@1` содержит ровно два passes в
  указанном порядке:
  1. exact present `total_area + rooms`;
  2. exact present `total_area + location_text`.
- Эти passes совпадают с двумя допустимыми ветвями candidate gate ADR 0006.
  Candidate generation не выполняет assessment и не создаёт supporting либо
  contradicting evidence.
- `Missing` или `Unsupported` любого компонента исключает observation только
  из соответствующего pass и создаёт явную ordered non-participation запись.
  Observation всё ещё может участвовать в другом pass.
- Цена, currency, source id, `observed_at`, raw text, provenance, AI
  similarity, tolerance, coordinates и персональные признаки не входят в
  blocking key v1. Source id остаётся только частью publication identity.
- Blocking key хранит rule id/version и typed canonical `Area`,
  `RoomCount` либо `LocationText`. Float, locale formatting и digest/hash как
  identity запрещены; hash collision не может означать equality.
- Candidate identity включает canonical `PublicationPair`, соответствующие
  exact left/right `ObservationKey` и candidate policy version. Новая current
  observation создаёт другую identity, поэтому stale context различим.
- Итоговая candidate хранит непустой ordered tuple всех exact blocking matches,
  которые действительно materialized эту пару. Совпадение blocking key — лишь
  route к будущей assessment, не duplicate evidence и не automatic outcome.
- Bucket pair limit — явное положительное integer value, переданное caller.
  Policy v1 не содержит выбранной без измерений константы.
- Для bucket размера `n` до materialization вычисляется exact
  `n * (n - 1) / 2`. Если count больше limit, bucket целиком пропускается и
  создаёт `OversizedBucket` с key, canonical member keys, exact count и stable
  reason. Если count не больше limit, разворачиваются все его пары.
- Пара из oversized bucket может появиться через другой допустимый key. Тогда
  candidate сохраняет только match pass, который действительно её
  materialized; skipped oversized key остаётся в отдельном outcome.
- Результат содержит полную policy identity/configuration, canonical input
  keys, unique candidates, blocking non-participations и oversized buckets в
  стабильном порядке. Пустой candidate tuple — успешный объяснимый результат.
- Никакого global scan, fallback all-pairs, partial bucket, cluster,
  transitive closure, merge или physical-property identity нет.
- При `N` observations каждое создаёт максимум два memberships. Число bucket
  не больше `2N`. При limit `L` число pair materialization attempts не больше
  `2NL`; при фиксированном `L` оно линейно по `N`. Canonical sorting добавляет
  не более `O(N log N + NL log(NL))` structural work, то есть при фиксированном
  limit `O(N log N)`, без `O(N²)` fallback.
- Одинаковые full input + policy + limit дают структурно равный result.
  Equal generation/candidate identity с иным полным content является future
  consumer conflict, а не overwrite. Решение задаёт codes и coordinates, но не
  выбирает repository API или storage.
- Missed-pair risk измеряется отдельно на fully fictional reviewed control set
  TASK-020. Blocking coverage использует denominator только из conclusively
  `CONFIRMED_RELATIONSHIP` cases с `PairAssessmentSuccess`, exact observation
  keys которых представлены как available в generation input.
- Numerator — такие eligible confirmed pairs, присутствующие в candidates;
  denominator — все eligible confirmed pairs. Eligible пары, пропущенные из-за
  отсутствия общего key либо oversized bucket, остаются misses denominator.
- `PairNotAssessed`, stale/mismatched keys и confirmed pairs вне generation
  input сохраняются отдельными ineligible/unrepresented counts и не
  подменяются blocking miss. Любой `INCONCLUSIVE` label либо нулевой
  eligible-confirmed denominator даёт typed unavailable reason.
- Coverage хранится как exact integer ratio без float, percent или rounding и
  описывает только переданную fully fictional control population. Это не
  production recall, не доказательство репрезентативности и не утверждение
  юридической допустимости сбора.

Точные pseudotypes, invariants, ordering, conflicts, complexity proof,
coverage semantics и scenario matrix заданы в
[PUBLICATION-DUPLICATE-CANDIDATES.md](../design/PUBLICATION-DUPLICATE-CANDIDATES.md).

## Последствия

- Следующая реализация сможет формировать bounded candidate set без скрытого
  all-pairs scan, I/O, storage, часов или случайности.
- Пропуски из-за неполных полей и oversized buckets остаются наблюдаемыми и
  измеримыми, а не превращаются в отрицательное duplicate evidence.
- Multi-pass union уменьшает хрупкость одного key, но exact v1 rules всё ещё
  могут пропускать реальные relationships; это честно отражает blocking
  coverage на control population.
- Caller обязан выбрать limit из будущих измерений и эксплуатационного
  контекста; ADR намеренно не задаёт универсальное число.
- Крупный общий key может не создать ни одной пары. Это предсказуемая защита,
  а не ошибка и не разрешение частичного результата.
- Assessment policy, evidence, manual review и quality metrics TASK-020 не
  меняются.

## Проверка и условия пересмотра

Решение проверяется следующей pure реализацией frozen/slots типов и generation
по полностью вымышленным тестам: permutation invariance, exact keys,
non-participation, оба passes, pair union, oversized atomic skip, complexity
bound, replay/conflicts и blocking coverage.

Новый ADR нужен, если reviewed fictional evidence покажет неприемлемый
blocking miss, появятся проверенные неперсональные canonical поля, потребуется
другая policy version или измеренный limit contract. Пересмотр не может молча
добавить fuzzy/tolerance/AI rule, скрытый all-pairs fallback, partial bucket,
персональный признак, production-recall claim, cluster или merge.
