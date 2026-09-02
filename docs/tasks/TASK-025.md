# TASK-025 — pure duplicate-candidate assessment batch core

- Статус: завершено и слито в `main`
- Рабочая ветка: `task/025-duplicate-assessment-batch-core`
- Целевая ветка: `main`
- Стартовый SHA: `3c6674603230b878067fe573328fe73caf16392a`

## Цель

Реализовать neutral frozen/slots contracts и pure deterministic atomic
composition по ADR 0009 для exact binding готового
`DuplicateCandidateGenerationResult`, полного caller-supplied current context
из `AvailableObservation` и явной assessment policy.

## Включённый объём

- Отдельный neutral core-модуль
  `publication_duplicate_assessment_batches.py`.
- Validated input/configuration, batch/item identities, item outcome, complete
  batch, atomic success/failure union и typed conflict subjects.
- Поддержка только полного
  `PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1` и полного
  `PUBLICATION_DUPLICATE_POLICY_V1`.
- Exact generation/current binding с раздельными unavailable/unsupported,
  same-key content, duplicate reference, missing, extra и same-reference
  current-key mismatch semantics.
- Полный zero-call preflight, defensive candidate binding и existing
  `assess_publication_pair` ровно один раз на materialized candidate.
- Full downstream pure pass с typed conversion `PairNotAssessed`,
  `PairAssessmentFailure`, malformed success и unsupported result; failure не
  содержит partial item outcomes.
- Package-root exports и один direct fully fictional unit-test module.
- Согласование task registry и project state documents только по фактически
  реализованному результату.

## Исключённый объём

- Изменение candidate/assessment policies или поведения
  `generate_duplicate_candidates`/`assess_publication_pair`.
- Storage/repository/index/database/ORM/migrations, transaction/revision,
  idempotency side effects, retry и persistence.
- JSON/Pydantic/filesystem, CLI/API/UI, real data, HTTP, scraping и внешние
  сервисы.
- AI/fuzzy/tolerance, physical property, winner, merge/collapse/hide,
  clustering, connected components и transitive closure.
- Новые dependencies, `pyproject.toml`, `uv.lock`, fixtures/golden, merge в
  `main`, push/publication, удаление worktree/ветки или начало следующей задачи.

## Критерии готовности

- [x] Все новые record contracts frozen/slots, tuple-only где применимо,
  runtime-validated и публично экспортированы.
- [x] Batch identity отдельно хранит exact generation identity и explicit
  assessment policy version; candidate и assessment policy types не смешаны.
- [x] Full exact supported policies проверяются независимо до assessment.
- [x] Current input валидируется атомарно; все назначенные конфликтные формы
  имеют независимые typed subjects и stable canonical order.
- [x] Full current keys exact связаны с generation keys; same-reference new key
  даёт один `CURRENT_KEY_MISMATCH`, а не missing+extra.
- [x] Candidate binding проверяет policy, pair/keys, membership coordinates,
  uniqueness и canonical order без regeneration и без использования blocking
  matches как evidence.
- [x] Любой preflight conflict даёт ровно zero assessment calls.
- [x] Valid empty candidates дают complete success, empty item tuple и zero
  calls.
- [x] Каждый valid candidate вызывает existing pair operation ровно один раз в
  canonical order с exact full current sides и explicit assessment policy.
- [x] Downstream conflicts не останавливают pure pass; итоговый failure
  атомарен и не раскрывает provisional successful items.
- [x] Success сохраняет full generation result, full assessment policy и exact
  ordered bound item outcomes.
- [x] Fully fictional tests покрывают constructors, policies, all preflight
  forms, binding, call counts/order, empty/multiple/same/cross-source,
  permutation, downstream full pass, replay/immutability, non-transitivity и
  forbidden surface.
- [x] Нет all-pairs, regeneration, retries, transitive work, I/O, storage или
  external surface; lookup/composition boundary остаётся `O(N + C)` плюс ровно
  `C` pair calls.
- [x] Документация отражает только реализованный scope; TASK-024 отмечена как
  интегрированная в `main`.
- [x] Все финальные проверки успешны; создаётся один атомарный implementation
  commit, дерево оставляется чистым и ветка не сливается в `main`.

## Фактически выполненная работа

- Добавлен neutral pure-модуль с validated configuration/input, exact
  batch/item identities, full item/batch records, atomic outcome union,
  category/code taxonomy и structural subjects ADR 0009.
- Реализован phase-gated preflight: current shape/content, full policies,
  generation/current reference-key binding и candidate binding полностью
  завершаются до первого downstream call.
- Composition канонизирует valid current permutations, строит linear
  reference lookup и передаёт existing assessment operation только exact full
  left/right observations и explicit assessment policy.
- Downstream values преобразуются в batch conflicts; pass продолжается по всем
  candidates, а provisional items сохраняются только при полном success.
- Добавлены package-root exports и
  `tests/test_publication_duplicate_assessment_batches.py` с 33 прямыми fully
  fictional tests.
- Существующие candidate/assessment modules, policies и operations не
  изменялись.

## Проверки

- `uv run pytest tests/test_publication_duplicate_assessment_batches.py -q` —
  успешно: `33 passed`.
- `uv sync --frozen` — успешно: проверены 18 зафиксированных packages,
  зависимости и lock не изменены.
- `uv lock --check` — успешно: разрешены 18 packages, lock соответствует
  project metadata.
- `uv run quality` — успешно: Ruff format-check (`92 files`), Ruff lint,
  strict mypy (`41 source files`), основной pytest (`603 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Все 47 относительных Markdown links в 7 изменённых документах — успешно;
  broken links отсутствуют.
- Changed-path audit — успешно: `pyproject.toml`, `uv.lock`, `tests/fixtures` и
  `fixtures/golden` не изменены; новые dependencies отсутствуют.
- Public forbidden-surface audit — успешно: новый модуль не вызывает и не
  экспортирует generation operation, storage/external/physical-property/
  transitive API.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-025 реализует только pure in-memory batch composition по ADR 0009 и слита
в `main` merge-коммитом `c43642b`. Storage, external boundaries, side effects,
real data, physical-property и transitive semantics намеренно отсутствуют.

## Итоговый коммит

Один атомарный implementation commit будет создан после полного successful
quality/documentation audit. Точный SHA подтверждается Git после commit и не
дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

После TASK-025 действующий план не задаёт единственную однозначную малую
следующую задачу. Выбор между side-effecting execution contract, persistence
boundary и иным продолжением остаётся открытым архитектурным вопросом и не
принимается молча в рамках TASK-025.
