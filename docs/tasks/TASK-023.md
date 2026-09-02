# TASK-023 — pure exact duplicate-candidate blocking coverage

- Статус: завершено в task-ветке, не слито в `main`
- Рабочая ветка: `task/023-duplicate-blocking-coverage`
- Целевая ветка: `main`
- Стартовый SHA: `769503b1acddfdbad3d8260b142dc2ab00c1a526`

## Цель

Реализовать отдельный neutral frozen/slots pure-модуль exact blocking-coverage
evaluation по ADR 0008 поверх уже валидных `DuplicatePolicyControlSet` и
`DuplicateCandidateGenerationResult`. Evaluation измеряет только покрытие
conclusively confirmed cases конкретного полностью вымышленного control set в
exact generation context и не перезапускает generation либо assessment.

## Включённый объём

- Узкий модуль `publication_duplicate_candidate_coverage.py`, зависящий только
  от публичных contracts TASK-019/020/022.
- Typed unavailable contract с ровно двумя причинами:
  `inconclusive_control_labels` и `no_eligible_confirmed_relationships`.
- Полный immutable coverage record с раздельными candidate/assessment policy
  versions, exact generation identity, population и всеми disjoint counts ADR
  0008.
- Exact unsimplified `ExactRatio` либо typed unavailable с утверждённым
  precedence.
- Structural conflict subject exact `PublicationPair` и left/right
  `ObservationKey`, stable
  `DUPLICATE_CANDIDATE_COVERAGE_CONFLICT/generation_result_inconsistent` и
  canonical atomic success/failure outcome без partial metrics.
- Pure `evaluate_duplicate_candidate_blocking_coverage(control_set,
  generation_result)` и узкие package-root exports.
- Один новый direct fully fictional unit-test module.
- Согласование PROJECT/ARCHITECTURE/ROADMAP/CHECKPOINT/task registry только по
  фактически реализованному результату.

## Исключённый объём

- Изменение `PUBLICATION_DUPLICATE_POLICY_V1`,
  `PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1`, `assess_publication_pair`,
  `generate_duplicate_candidates`, quality metrics TASK-020, labels или
  evidence.
- Выполнение generation/assessment, вывод human label из automatic outcome и
  hidden all-pairs scan.
- Storage/repository/index/database, Pydantic/JSON/filesystem, CLI/API/UI,
  часы, UUID, randomness, HTTP или real data.
- Physical property, canonical winner, merge/collapse/hide, clustering,
  transitive closure, score, probability или tolerance.
- Dependencies, `pyproject.toml`, `uv.lock`, fixtures/golden,
  `tests/fixtures`, push, merge в `main`, удаление ветки/worktree или начало
  TASK-024.

## Критерии готовности

- [x] Coverage contracts frozen/slots, immutable, tuple-only где применимо и
  публично экспортированы.
- [x] Population и PairNotAssessed/label/confirmed eligibility/miss counts
  соответствуют точным disjoint invariants ADR 0008.
- [x] Confirmed cases классифицируются в порядке PairNotAssessed, outside input,
  stale/mismatched exact keys, eligible.
- [x] Eligible case covered только exact candidate identity; отсутствие общего
  exact v1 key и whole-oversized skip различаются.
- [x] Один oversized route не мешает coverage через другой действительно
  materialized route.
- [x] Общий non-oversized key без exact candidate даёт только stable atomic
  `generation_result_inconsistent` failure без partial coverage.
- [x] Metric precedence сначала учитывает любой inconclusive label, затем
  нулевой eligible-confirmed denominator; доступный ratio не сокращается и не
  использует float/percent/rounding.
- [x] Assessment policy, candidate policy и exact generation identity
  сохраняются раздельно.
- [x] Evaluation только читает exact assessment snapshots и public generation
  outcomes, не мутирует inputs и не вызывает assessment/generation.
- [x] Fully fictional tests покрывают exact `2/4`, оба routes,
  oversized alternate route, same/cross-source, все eligibility classes,
  label/PairNotAssessed counts, unavailable precedence, constructors,
  exports, permutations и conflict ordering.
- [x] Модуль не имеет I/O/storage/clock/UUID/JSON/Pydantic/merge/cluster
  surface; реальные данные отсутствуют.
- [x] `pyproject.toml`, `uv.lock`, fixtures/golden и `tests/fixtures` не
  изменены.
- [x] Создан ровно один атомарный commit; ветка не слита и не опубликована.

## Фактически выполненная работа

- Добавлен neutral pure-модуль
  `src/real_estate_parser/publication_duplicate_candidate_coverage.py` с exact
  unavailable, metric, conflict subject, canonical conflict и atomic
  success/failure contracts.
- Coverage constructor защищает все count equations, разные policy bindings,
  non-empty population и точное соответствие metric precedence фактическим
  counts.
- Evaluation использует canonical generation input keys и exact identity
  candidates; общие v1 blocking keys восстанавливаются только из сохранённых
  canonical field snapshots готовой assessment.
- Whole oversized miss признаётся только когда каждый общий key присутствует в
  соответствующем `OversizedBucket` с обеими exact member keys. Иной общий key
  без candidate создаёт canonical atomic conflict.
- Package root экспортирует новые contracts и operation.
- Добавлен `tests/test_publication_duplicate_candidate_coverage.py` с 18
  fully fictional tests; existing generation/assessment functions используются
  только при подготовке валидных test inputs, но не вызываются evaluation.

## Проверки

- `uv sync --frozen` — успешно: проверены 18 зафиксированных packages,
  зависимости не изменены.
- `uv lock --check` — успешно: разрешены 18 packages, lock соответствует
  project metadata.
- `uv run pytest -q tests/test_publication_duplicate_candidate_coverage.py` —
  успешно: `18 passed`.
- `uv run quality` — успешно: Ruff format-check (`86 files`), Ruff lint,
  strict mypy (`39 source files`), основной pytest (`570 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Все 41 изменённые относительные Markdown links — успешно; broken links
  отсутствуют.
- Changed paths проверены: `pyproject.toml`, `uv.lock`, `tests/fixtures` и
  `fixtures/golden` не изменены; посторонних файлов нет.
- Full diff review подтвердил отсутствие assessment/generation calls, real
  data, hidden all-pairs, I/O и scope creep.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-023 завершена только в `task/023-duplicate-blocking-coverage` и намеренно
не слита в `main`. Реализован только pure exact blocking-coverage evaluator;
batch assessment composition, storage, external boundaries и TASK-024 не
начинались.

## Итоговый коммит

Один атомарный commit находится в истории ветки по сообщению
`feat: add exact duplicate candidate blocking coverage`. Точный SHA
подтверждается Git после создания commit и не дублируется внутри его
собственного снимка.

## Следующая рекомендуемая задача

TASK-024 — спроектировать pure atomic batch composition от DuplicateCandidateGenerationResult и exact current AvailableObservation к assess_publication_pair с explicit binding/conflict semantics, без storage, JSON, CLI, real data или изменения candidate/assessment policies
