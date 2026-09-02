# TASK-020 — reviewed control set и pure duplicate-policy quality metrics

- Статус: завершено в task-ветке, готово к review
- Рабочая ветка: `task/020-reviewed-control-metrics`
- Целевая ветка: `main`
- Стартовый SHA: `1c360159028a37da77c59b0041b8036b0f1bb331`

## Цель

Принять и реализовать небольшой neutral immutable контракт полностью
вымышленного reviewed control set и чистые детерминированные метрики качества
publication duplicate policy: assessment coverage, categorical review load и
exact precision/recall только при достаточных independently supplied labels.
Human label остаётся pair-bound assertion, а не physical-property fact или
безусловная истина.

## Включённый объём

- ADR 0007 и согласованная design-спецификация с явным сравнением fully labeled
  population и denominator-specific label sufficiency.
- Отдельный узкий `DuplicateControlLabel` для canonical pair с outcomes
  confirm/reject/inconclusive, независимый от automatic outcome и manual-review
  revision binding TASK-019.
- Atomic `DuplicatePolicyControlCase`, связывающий canonical pair, exact
  `PairAssessmentSuccess | PairNotAssessed`, explicit policy version и label.
- Непустой tuple-only `DuplicatePolicyControlSet` одной policy version, не
  более одного case на pair и canonical order независимо от перестановки.
- Typed stable contract errors для unsupported result, pair/label/policy
  mismatch, duplicate pair и invalid set без partial metrics.
- Exact counts всех automatic outcomes, `PairNotAssessed`, assessed и общего
  review-required набора.
- `ExactRatio` для coverage и population review-load rate без float, rounding
  или presentation formatting.
- Exact precision/recall либо typed unavailable reason по утверждённым
  denominator-specific условиям.
- Одна pure операция `evaluate_duplicate_policy_quality`, узкие package exports
  и новый fully fictional unit-test module.

## Исключённый объём

- Изменение ADR 0006, `publication-duplicate-policy@1`, automatic assessment,
  supporting/contradicting evidence, observations или manual reviews.
- Batch candidate generation, blocking/indexing, quadratic all-pairs scan,
  missed-pair risk implementation, merge, clustering и transitive relation.
- Physical property, canonical winner, collapse/hide publications и изменение
  histories.
- Repository append, storage/database, Pydantic, JSON, filesystem, CLI/API/UI,
  HTTP, часы, UUID, случайность и hidden state.
- Float, Decimal, percent string, score, threshold, F1 и accuracy.
- Real data, fixtures/golden, реальные sources, AI, OpenClaw, Telegram,
  notifications, dependencies, `pyproject.toml` и `uv.lock`.
- Merge в `main`, push, удаление веток/worktree и начало TASK-021.

## Критерии готовности

- [x] ADR 0007 сравнивает fully labeled population и denominator-specific
  sufficiency и фиксирует точные denominators и unavailable reasons.
- [x] Control label independently supplied, pair-bound и не выводится из
  automatic outcome; `INCONCLUSIVE` означает недостаточную разметку.
- [x] Case exact связывает pair, policy version, success/not-assessed result и
  label; failure/unsupported result отклоняется без partial metrics.
- [x] Control set непустой, frozen/slots, tuple-only, unique by pair, one-policy
  и canonical независимо от input permutation.
- [x] Coverage и population review load используют exact integer ratios;
  counts всех трёх outcomes, not-assessed и review-required сохранены отдельно.
- [x] Precision доступна только при ненулевом полностью conclusively labeled
  review-required denominator; иначе возвращает утверждённый typed reason.
- [x] Recall доступна только при fully conclusive population и ненулевом
  confirmed denominator; insufficient/not-assessed могут быть false negatives.
- [x] Evaluation не мутирует и не пересчитывает automatic assessment,
  observations, evidence, non-comparisons или reviews.
- [x] Новый fully fictional test module покрывает valid/invalid cases,
  permutations, immutability, counts, ratios, precision/recall sufficiency,
  label independence и запрещённую surface.
- [x] Новый модуль не импортирует I/O/storage/clock/UUID/Pydantic/JSON и не
  предоставляет score/threshold/F1/accuracy/merge/cluster API.
- [x] Проектные документы отражают только фактический результат TASK-020 и
  называют ровно TASK-021 как следующий шаг без его начала.
- [x] `pyproject.toml`, `uv.lock`, fixtures и golden не изменены.
- [x] Создан ровно один атомарный commit; ветка не слита и не опубликована.

## Фактически выполненная работа

- Добавлен neutral pure-модуль `publication_duplicate_quality.py` с отдельным
  pair-bound label type, atomic case/set contracts, stable typed errors,
  exact-ratio и metric-unavailable records.
- `DuplicatePolicyControlCase` повторно использует contracts TASK-019,
  проверяет exact pair/result/policy/label binding и явно сохраняет policy
  version для `PairNotAssessed`.
- `DuplicatePolicyControlSet` проверяет непустоту, tuple-only форму, единую
  policy version и pair uniqueness, затем канонически сортирует cases по
  structural coordinates обеих references.
- `evaluate_duplicate_policy_quality` одной полной pure-операцией считает
  automatic outcome/not-assessed/review-required counts, assessment coverage,
  population review load и denominator-safe precision/recall.
- Precision использует только review-required denominator; recall требует
  conclusive labels всей population и считает confirmed insufficient и
  not-assessed cases false negatives.
- Добавлены ADR 0007, детальная design-спецификация, узкие package exports и 24
  fully fictional unit-теста.

## Проверки

- `uv sync --frozen` — успешно.
- `uv lock --check` — успешно.
- `uv run pytest -q tests/test_publication_duplicate_quality.py` — успешно,
  `24 passed`.
- `uv run quality` — успешно: Ruff format-check (`77 files`), Ruff lint,
  strict mypy (`35 source files`), основной pytest (`503 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Changed paths проверены: `pyproject.toml`, `uv.lock`, `tests/fixtures` и
  golden не изменены; посторонних файлов нет.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-020 завершена в `task/020-reviewed-control-metrics` и намеренно не слита в
`main`. Реализованы только reviewed control contract и pure exact metrics;
candidate generation, blocking/indexing, storage, physical-property semantics
и TASK-021 не начинались.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`feat: add reviewed duplicate policy metrics`. Точный SHA подтверждается Git
после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-021 — принять design-only контракт детерминированного формирования ограниченного набора duplicate candidate pairs из available observations с явными blocking keys и измеримым риском пропуска, без реализации, quadratic all-pairs scan, storage, clustering, JSON, CLI или real data
