# Reviewed control set и pure quality metrics duplicate policy

## Назначение и границы

Документ уточняет [ADR 0007](../decisions/0007-reviewed-duplicate-control-metrics.md)
до формы реализованного neutral pure-контракта TASK-020. Он оценивает только
явно переданную полностью вымышленную population pair cases и не определяет,
как pairs были найдены, отобраны, сохранены или размечены.

Контракт напрямую повторно использует `PublicationPair`,
`DuplicatePolicyVersion`, `PairAssessmentSuccess`, `PairNotAssessed` и
`DuplicateAutomaticOutcome` TASK-019. Семантика
`publication-duplicate-policy@1`, evidence, observations и manual reviews не
изменяется.

Вне scope остаются Pydantic, JSON, filesystem, CLI/API/UI, storage, clocks,
UUID, real data, sampling, candidate generation, blocking/indexing,
all-pairs scan, merge, clustering и transitive relation.

## Независимый pair-bound label

Control label не переиспользует `ManualReviewOutcome`, потому что manual review
привязана к assessment identity, findings и revision chain, а control case
должен также представлять `PairNotAssessed`.

```text
DuplicateControlLabelOutcome =
  CONFIRMED_RELATIONSHIP
  | REJECTED_RELATIONSHIP
  | INCONCLUSIVE

DuplicateControlLabel(
  pair: PublicationPair,
  outcome: DuplicateControlLabelOutcome
)
```

Label всегда supplied независимо. Automatic outcome не является входом для
его построения и не может определить его значение. `INCONCLUSIVE` означает
недостаточную разметку, а не rejected relationship. Даже confirmed label —
human assertion exact pair, не physical-object fact и не transitive edge.

## Atomic control case

```text
MeasurablePairAssessmentResult = PairAssessmentSuccess | PairNotAssessed

DuplicatePolicyControlCase(
  pair: PublicationPair,
  policy_version: DuplicatePolicyVersion,
  result: MeasurablePairAssessmentResult,
  label: DuplicateControlLabel
)
```

Инварианты:

- `pair` уже canonical и совпадает с `label.pair`;
- для `PairAssessmentSuccess` exact `assessment.identity.pair == pair` и
  `assessment.identity.policy_version == policy_version`;
- для `PairNotAssessed` exact `result.pair == pair`, а policy version хранится
  явно в case;
- `PairAssessmentFailure` и любой иной object не измеряются и дают typed
  `unsupported_result` contract error;
- case не изменяет и не копирует observations, evidence, non-comparisons,
  automatic outcome или manual reviews.

## Control population

```text
DuplicatePolicyControlSet(
  policy_version: DuplicatePolicyVersion,
  cases: non-empty tuple[DuplicatePolicyControlCase, ...]
)
```

Control set:

- принимает только tuple;
- содержит не более одного case на canonical `PublicationPair`;
- требует одну declared policy version для всех cases;
- канонически хранит cases по
  `(left.source, left.publication, right.source, right.publication)`;
- структурно равен для любой перестановки одинаковых cases.

Невалидный case или set отклоняется до evaluation одной typed
`DuplicateControlContractError` со stable code. Partial counts или metrics при
этом не существуют.

## Классификация result

| Result | Класс prediction | Отдельный count |
| --- | --- | --- |
| `CANDIDATE_REQUIRES_MANUAL_REVIEW` | review-required / predicted positive | candidate count |
| `CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW` | review-required / predicted positive | conflicting count |
| `INSUFFICIENT_EVIDENCE_NO_CANDIDATE` | predicted negative | insufficient count |
| `PairNotAssessed` | predicted negative для quality denominator, но не automatic outcome/evidence | not-assessed count |

`assessed_pair_count` равен сумме трёх automatic outcome counts.
`review_required_count` равен candidate + conflicting. `population_count`
равен assessed + not-assessed.

## Exact ratios

```text
ExactRatio(
  numerator: integer, 0 <= numerator <= denominator,
  denominator: positive integer
)
```

Ratio не предоставляет float, Decimal, rounded percent или formatting.
Сокращение дроби не выполняется: `2/4` сохраняет фактические counts выбранного
denominator.

### Assessment coverage

```text
assessed_pair_count / population_count
```

Label sufficiency не влияет на coverage. Непустота control set гарантирует
положительный denominator.

### Population review-load rate

```text
review_required_count / population_count
```

Название `review_required_population_rate` фиксирует denominator. Отдельная
доля только среди assessed pairs не вычисляется и не подменяет population
load.

## Precision

Denominator — все review-required cases, независимо от того, candidate это или
conflicting outcome.

Порядок решения:

1. Если review-required cases нет, вернуть
   `QualityMetricUnavailable(no_predicted_positive)`.
2. Если хотя бы один review-required case имеет `INCONCLUSIVE`, вернуть
   `QualityMetricUnavailable(incomplete_predicted_positive_labels)`.
3. Иначе вернуть exact:

```text
confirmed labels среди review-required / все review-required
```

`INCONCLUSIVE` вне этого denominator не мешает precision и не считается false
positive либо true negative.

## Recall

Recall должна учитывать confirmed relationships, пропущенные как insufficient
или not-assessed. Поэтому сначала требуется conclusive label всей population.

Порядок решения:

1. Если хотя бы один case имеет `INCONCLUSIVE`, вернуть
   `QualityMetricUnavailable(incomplete_population_labels)`.
2. Если confirmed labels нет, вернуть
   `QualityMetricUnavailable(no_confirmed_relationship_labels)`.
3. Иначе вернуть exact:

```text
review-required cases среди confirmed / все confirmed
```

Confirmed `INSUFFICIENT_EVIDENCE_NO_CANDIDATE` и confirmed `PairNotAssessed`
оба входят в denominator и увеличивают число false negatives.

## Почему sufficiency зависит от denominator

Полностью размеченная population была бы достаточна для всех label-based
metrics, но является избыточным условием для precision. Например, confirmed и
rejected labels всех review-required cases дают точную precision, даже если
отдельный not-assessed case пока inconclusive.

Для recall та же неполнота недопустима: inconclusive predicted-negative case
может оказаться confirmed relationship, поэтому и numerator, и denominator
recall ещё не установлены. Выбранная схема сохраняет максимум честно доступной
информации, не заменяя неизвестность нулём.

## Pure operation

```text
evaluate_duplicate_policy_quality(
  control_set: DuplicatePolicyControlSet
) -> DuplicatePolicyQualityMetrics
```

Результат содержит policy version, семь exact counts, coverage, population
review load, precision и recall. Precision/recall имеют union форму
`ExactRatio | QualityMetricUnavailable`.

Operation только читает immutable cases, не выполняет assessment заново и не
меняет labels, observations, evidence, reviews или policy. В ней нет I/O,
storage lookup, часов, UUID, случайности или hidden state.

## Полностью вымышленные сценарии

| Сценарий | Ожидаемый результат |
| --- | --- |
| Mixed population из четырёх unique pairs | exact counts всех outcomes, coverage `3/4`, population review load `2/4` |
| Все pairs assessed | coverage `N/N` |
| Все pairs not assessed | coverage `0/N`, review load `0/N` |
| Перестановка cases | тот же canonical set и полностью равные metrics |
| Duplicate pair | `duplicate_pair`, metrics отсутствуют |
| Result другой pair | `pair_binding_mismatch`, metrics отсутствуют |
| Mixed policy versions | `policy_version_mismatch`, metrics отсутствуют |
| `PairAssessmentFailure` | `unsupported_result`, metrics отсутствуют |
| Review-required labels confirmed/rejected | exact precision |
| Нет review-required | precision `no_predicted_positive` |
| Review-required inconclusive | precision `incomplete_predicted_positive_labels` |
| Fully conclusive с confirmed labels | exact recall |
| Нет confirmed labels | recall `no_confirmed_relationship_labels` |
| Любой population label inconclusive | recall `incomplete_population_labels` |
| Confirmed insufficient и not-assessed | оба являются false negatives recall |
| Один automatic result с разными supplied labels | разные quality metrics при неизменном assessment/evidence |

Все scenario publications используют только вымышленные source ids и
`.example`; реальные объекты и люди отсутствуют.

## Намеренно отложено

- формирование candidate pairs, blocking keys, indexing и missed-pair risk;
- sampling и доказательство репрезентативности control population;
- хранение, repository append, JSON/Pydantic boundary и CLI/API/UI;
- comparison нескольких policy versions, confidence intervals, F1, accuracy,
  score, threshold и dashboard formatting;
- physical property, merge/collapse, cluster и transitive closure;
- real data, sources, AI, OpenClaw, Telegram и notifications.
