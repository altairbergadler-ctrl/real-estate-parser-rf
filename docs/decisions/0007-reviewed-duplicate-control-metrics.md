# 0007. Reviewed control set и exact метрики duplicate policy

- Статус: принято
- Дата: 2026-09-02
- Задача: TASK-020

## Контекст

TASK-019 реализовала pure pair assessment по
`publication-duplicate-policy@1`, но наличие categorical outcome ещё не
показывает coverage, нагрузку ручной проверки или качество policy. Для
измерения нужен небольшой полностью вымышленный control set с независимо
supplied human labels. При этом human assertion не является доказанной
identity физического объекта, а `INCONCLUSIVE` не может молча становиться
отрицательным label.

`PairNotAssessed` не содержит policy version, `PairAssessmentFailure` не
является измеримым результатом, а float/rounded показатели скрыли бы точные
знаменатели. Нужен нейтральный immutable контракт без Pydantic, JSON,
filesystem, storage, часов, UUID или real data.

## Рассмотренные варианты

### Требовать полностью conclusive labels всей population для любых метрик

Отклонено как единое глобальное условие. Оно делает precision недоступной из-за
`INCONCLUSIVE` case, который не входит в predicted-positive denominator, хотя
все review-required cases могут быть независимо и conclusively размечены.
Coverage и review load вообще не используют human labels.

Полная conclusive разметка всей population всё же обязательна именно для
recall: иначе `PairNotAssessed` или insufficient case с неизвестным label
может скрывать false negative и positive-label denominator неизвестен.

### Использовать denominator-specific label sufficiency

Принято. Каждая метрика объявляет собственный denominator и отдельные условия
доступности:

- coverage: assessed pairs / вся control population;
- population review load: review-required pairs / вся control population;
- precision: confirmed labels среди review-required / все review-required,
  только когда denominator ненулевой и все его labels conclusive;
- recall: review-required среди confirmed / все confirmed, только когда вся
  population conclusive и positive-label denominator ненулевой.

Недоступность возвращается typed reason, а не ноль, исключение, float или
неявно изменённый denominator.

### Переиспользовать `ManualReviewOutcome` как control label

Отклонено. Manual review TASK-019 привязана к exact assessment identity,
finding references и revision chain и не покрывает естественно
`PairNotAssessed`. Переиспользование создало бы ложную binding и смешало бы
операционную review record с независимо supplied pair label.

Принят отдельный узкий `DuplicateControlLabel`, привязанный только к canonical
`PublicationPair` и outcome `CONFIRMED_RELATIONSHIP`,
`REJECTED_RELATIONSHIP` либо `INCONCLUSIVE`.

### Хранить float, проценты, score, F1 или accuracy

Отклонено. Для малого control set точная дробь важнее округлённого
представления. F1 и accuracy вводят новые агрегаты и интерпретацию, которые не
нужны для проверки текущих гипотез policy.

## Решение

- Один `DuplicatePolicyControlCase` атомарно связывает canonical pair, exact
  `PairAssessmentSuccess` либо `PairNotAssessed`, явно сохранённую
  `DuplicatePolicyVersion` и independently supplied pair-bound label.
- `PairAssessmentSuccess` обязан быть связан с той же pair и policy version.
  `PairNotAssessed` обязан быть связан с той же pair; policy version хранится в
  case, потому что существующий result её намеренно не содержит.
- `PairAssessmentFailure` и любой unsupported result отклоняются стабильной
  `unsupported_result` contract error до вычисления метрик.
- `DuplicatePolicyControlSet` непустой, tuple-only, содержит не более одного
  case на pair, относится к одной policy version и канонически сортирует cases
  по обеим references пары независимо от входной перестановки.
- Predicted positive/review-required — только
  `CANDIDATE_REQUIRES_MANUAL_REVIEW` и
  `CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW`. Predicted negative —
  `INSUFFICIENT_EVIDENCE_NO_CANDIDATE` и `PairNotAssessed`.
- Метрики сохраняют counts каждого из трёх automatic outcomes,
  `PairNotAssessed`, assessed pairs и общего review-required набора.
- Coverage и review load имеют population denominator. Дополнительный
  assessed-only review-load denominator не вводится.
- Все ratios представлены только `ExactRatio(numerator, denominator)` с
  integer values и положительным denominator; float, Decimal, rounding и
  presentation percent отсутствуют.
- Precision недоступна как `no_predicted_positive`, когда review-required
  denominator пуст, или как `incomplete_predicted_positive_labels`, когда
  хотя бы один case этого denominator имеет `INCONCLUSIVE` label.
- Recall недоступна как `incomplete_population_labels`, когда хотя бы один
  case population имеет `INCONCLUSIVE`, или как
  `no_confirmed_relationship_labels`, когда вся population conclusive, но
  confirmed denominator пуст.
- При доступности precision равна confirmed среди review-required / все
  review-required, а recall — review-required среди confirmed / все confirmed.
- Label остаётся human assertion exact pair и не создаёт `PhysicalProperty`,
  merge, cluster, transitive relation или безусловную истину.
- Evaluation не изменяет result, observations, evidence, non-comparisons или
  manual reviews и не пересчитывает automatic assessment.

Точная форма типов и сценариев задана в
[PUBLICATION-DUPLICATE-QUALITY.md](../design/PUBLICATION-DUPLICATE-QUALITY.md).

## Последствия

- Policy можно сравнивать с независимо supplied labels, сохраняя точные
  знаменатели и честную недоступность метрик.
- Precision может быть доступна при неполной разметке вне predicted-positive
  denominator; recall сознательно остаётся недоступной до полной conclusive
  разметки population.
- `PairNotAssessed` и insufficient cases могут быть явными false negatives
  recall, но не превращаются в automatic evidence или отрицательные human
  labels.
- Контракт измеряет только переданную control population. Он не заявляет её
  репрезентативность и не определяет candidate generation, blocking или
  production monitoring.

## Условия пересмотра

Решение пересматривается новым ADR, если понадобится sampling contract,
стратификация, confidence interval, comparison нескольких policy versions или
доказанная необходимость иных quality metrics. Такой пересмотр не может молча
вывести labels из automatic outcomes, ослабить pair/policy binding или
превратить human assertion в physical-property identity.
