# TASK-022 — pure bounded duplicate candidate generation

- Статус: завершено в task-ветке, не слито в `main`
- Рабочая ветка: `task/022-duplicate-candidate-core`
- Целевая ветка: `main`
- Стартовый SHA: `e5423f0550b1469308ee1e254844c0d21bed638f`

## Цель

Реализовать neutral frozen/slots blocking/candidate contracts и одну pure
deterministic generation operation по ADR 0008 для явно переданного непустого
tuple current observations. Результат должен формировать bounded union exact
candidate pairs, полностью объяснять Missing/Unsupported non-participation и
whole-bucket oversized outcomes и не выполнять pair assessment либо blocking
coverage evaluation.

## Включённый объём

- Один neutral-модуль `publication_duplicate_candidates.py`, зависящий только
  от готовых normalization/observation contracts и `PublicationPair`.
- Отдельная immutable `publication-duplicate-candidate-policy@1` с двумя exact
  passes в порядке ADR 0008: `total_area + rooms` и
  `total_area + location_text`.
- Safe opaque candidate policy/rule/reason codes, typed exact blocking keys,
  positive exact caller-supplied `BucketPairLimit` и полная immutable
  configuration.
- Frozen/slots component/rule non-participation, logical bucket,
  `OversizedBucket`, candidate/generation identities, result, success, failure
  и stable generation/future-consumer conflict contracts.
- Pure `generate_duplicate_candidates` с атомарной validation,
  canonicalization, whole-bucket size decision, bounded pair materialization и
  policy-ordered union matches.
- Public package exports и один новый fully fictional direct unit-test module.
- Согласование PROJECT/ARCHITECTURE/ROADMAP/CHECKPOINT/task registry только по
  фактически реализованному результату.

## Исключённый объём

- Blocking coverage pseudotypes/evaluator TASK-023 и любые изменения quality
  metrics TASK-020.
- Вызов `assess_publication_pair`, batch assessment, duplicate evidence,
  manual review или изменение ADR 0006/0007/0008 и их policies.
- Global all-pairs fallback, partial first-N bucket, default limit,
  fuzzy/tolerance/geocoding/coordinates/photo/AI/LLM rules.
- Physical property, canonical winner, merge/collapse/hide, clustering и
  transitive closure.
- Pydantic, JSON, filesystem, CLI/API/UI, storage/repository/index/database,
  clocks, UUID, randomness, HTTP или real data.
- Dependencies, `pyproject.toml`, `uv.lock`, fixtures/golden, push,
  publication, merge в `main`, удаление ветки/worktree или начало TASK-023.

## Критерии готовности

- [x] Candidate policy имеет отдельную exact version и ровно два ordered rules
  ADR 0008; arbitrary/changed rules дают stable unsupported-policy failure.
- [x] Blocking keys используют только typed canonical values и structural
  equality; float/hash/digest/locale identity отсутствует.
- [x] Bucket limit принимает только positive exact int и не имеет default.
- [x] Missing/Unsupported полностью и в component order объясняются typed
  non-participation; alternate pass остаётся доступным.
- [x] Input tuple атомарно проверяется на shape/non-empty, availability,
  supported object, same-key content conflict и one-observation-per-reference.
- [x] Любой validation conflict выдаёт только unique canonical conflicts без
  partial input/candidates/non-participations/buckets.
- [x] Каждый bucket сначала получает exact prospective count; oversized bucket
  целиком пропускается, exact-limit bucket полностью materializes, singleton
  успешен без pair.
- [x] Same-source/cross-source pairs разрешены, self-pair невозможна, union
  сохраняет все и только materialized matches в policy order.
- [x] Result хранит полную policy/configuration, canonical input keys,
  candidates, non-participations и oversized buckets; empty candidates —
  success.
- [x] Full valid input invariant к permutations, новая observation key меняет
  generation/candidate identity, pair attempts удовлетворяют bound ADR 0008.
- [x] Модуль не импортирует/не вызывает assessment, не реализует coverage и не
  содержит I/O/storage/clock/UUID/Pydantic/JSON surface.
- [x] Все назначенные проверки успешны, запрещённые пути не изменены, создан
  один атомарный commit и worktree оставлен чистым.

## Фактически выполненная работа

- Добавлен neutral frozen/slots-модуль
  `src/real_estate_parser/publication_duplicate_candidates.py` с safe typed
  policy/rule/reason codes, exact policy v1, двумя typed blocking keys,
  non-participation, bucket/candidate/generation contracts и stable conflicts.
- Реализована pure `generate_duplicate_candidates`: она собирает все
  независимо доказуемые validation conflicts до projection, канонизирует
  current available observations, создаёт максимум две memberships на
  observation и применяет exact whole-bucket limit до pair loops.
- Non-oversized buckets полностью разворачиваются в canonical unordered pairs;
  union дедуплицирует candidate identity и сохраняет ordered matches. Skipped
  oversized key не становится match, но alternate non-oversized key может
  сформировать ту же pair.
- `DuplicateCandidateGenerationResult` сохраняет exact policy, limit и
  canonical input identity, tuple-only outputs и полную конфигурацию без
  assessment/evidence semantics.
- Публичные types/function экспортированы из package root.
- Добавлен `tests/test_publication_duplicate_candidates.py` с 49 полностью
  вымышленными direct tests на contracts, conflicts, passes, union,
  non-participation, same/cross-source, limits, oversized outcomes,
  permutation/replay identity, immutability, bound и static forbidden surface.

## Проверки

- `uv sync --frozen` — успешно; зафиксированные зависимости не изменены.
- `uv lock --check` — успешно.
- `uv run pytest tests/test_publication_duplicate_candidates.py -q` — успешно:
  `49 passed`.
- `uv run quality` — успешно: Ruff format-check (`83 files`), Ruff lint,
  strict mypy (`37 source files`), основной pytest (`552 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-022 завершена только в `task/022-duplicate-candidate-core` и намеренно не
слита в `main`. Pure candidate generation реализована; blocking coverage,
assessment batch, storage, внешние boundaries и TASK-023 не начинались.

## Итоговый коммит

Один атомарный commit находится в истории ветки по сообщению
`feat: add bounded duplicate candidate generation`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-023 — реализовать pure exact blocking-coverage evaluation по ADR 0008 поверх DuplicatePolicyControlSet и DuplicateCandidateGenerationResult с typed unavailable/conflict outcomes, без storage, JSON, CLI, real data или изменения generation/assessment policies
