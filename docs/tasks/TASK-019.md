# TASK-019 — pure duplicate-pair assessment и manual review

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/019-duplicate-pair-assessment`
- Целевая ветка: `main`
- Стартовый SHA: `9fadad132f798cf4133aa615e60a9e19b7cb25f3`

## Цель

Реализовать нейтральные immutable frozen/slots типы доказательной оценки
ровно одной неупорядоченной пары разных source publications, чистую полностью
симметричную оценку по `publication-duplicate-policy@1` и отдельную pure
валидацию immutable ручной проверки по ADR 0006. Автоматический результат
остаётся гипотезой для ручной проверки и не создаёт физический объект, merge
или cluster.

## Включённый объём

- Один небольшой нейтральный core-модуль, повторно использующий существующие
  `PublicationRef`, `ObservationKey`, `AvailableObservation`,
  `PublicationObservation`, canonical field outcomes и полное provenance.
- Валидируемые safe opaque ASCII policy/rule/reason/review codes, canonical
  `PublicationPair`, structural `DuplicateAssessmentIdentity` и стабильные
  assessment/review conflicts.
- `DuplicateFieldSnapshot`, строго ordered `DuplicateEvidenceItem` и
  `RuleNonComparison` с непустыми tuple fields/snapshots и согласованными
  сторонами.
- Immutable `DuplicatePolicy` и константа `publication-duplicate-policy@1` с
  четырьмя rules в точном порядке: total area, rooms, exact location text и
  exact price/currency.
- Pure `assess_publication_pair` с canonical side assignment, полной
  симметрией, `PairNotAssessed` для unavailable side и точной decision table
  ADR 0006 без score, probability или tolerance.
- `CurrentPairContext`, pure current/stale check и immutable
  `AssessmentSupersession` с проверкой одной pair и отличающейся replacement
  identity, без storage append.
- Отдельные manual-review types и pure `create_manual_review` с supplied
  identity/time, exact finding references, revision/supersedes semantics,
  replay и atomic conflicts без hidden state.
- Прямые fully fictional unit-тесты типов, rules, outcomes, symmetry,
  unavailable, identity/current/supersession, manual review revisions,
  immutability, non-transitivity и запрещённой поверхности.
- Узкие package exports и согласование только фактически затронутых проектных
  документов.

## Исключённый объём

- Batch/all-pairs generation, blocking/indexing, clustering, connected
  components и transitive closure.
- `PhysicalProperty`, canonical winner, merge/collapse/hide publications или
  изменение observation histories.
- Assessment/review repository, append history, expected revision, storage,
  database/ORM/migrations и fork detection без переданных records.
- Pydantic, JSON, filesystem boundary, CLI/API/UI и изменение первого
  application flow или `search-result@1`.
- Реальные источники, HTTP, polling, scheduler, retry/rate limits, clocks,
  UUID, I/O или hidden state.
- Изменение normalization/observation contracts TASK-015…TASK-017, fixtures,
  golden, `pyproject.toml`, `uv.lock` или dependencies.
- AI/embeddings/LLM, персональные сигналы, OpenClaw, Telegram, уведомления,
  публикация, удаление worktree/веток и merge в `main`.
- Реализация или начало TASK-020.

## Критерии готовности

- [x] Все новые types/results frozen/slots и tuple-only; opaque codes принимают
  только ограниченный printable ASCII и не содержат произвольный текст.
- [x] `PublicationPair` принимает только разные references и канонически
  назначает стороны; same-reference operation возвращает точный stable
  conflict, same-source и cross-source pairs разрешены.
- [x] Assessment identity точно связывает canonical pair, left/right
  observation keys и policy version; snapshots повторно используют canonical
  outcomes/provenance без raw для `Missing` и сохраняют reason/raw для
  `Unsupported`.
- [x] `publication-duplicate-policy@1` выполняет ровно четыре rules и exact
  decision table ADR 0006 в policy order; missing/unsupported/unavailable,
  location/price/currency mismatch не становятся отрицательным evidence.
- [x] `assess_publication_pair(A, B) == assess_publication_pair(B, A)` по
  полному структурному равенству для всех outcomes и разных provenance;
  supporting и contradicting evidence сохраняются одновременно.
- [x] Exact price alone остаётся insufficient; автоматические outcomes не
  утверждают confirmed physical property и не содержат numeric score,
  probability или tolerance.
- [x] Current/stale helper и supersession invariants зависят только от явно
  переданного context/link и не читают историю или storage.
- [x] Manual review отделена от assessment, проверяет exact evidence/
  non-comparison references, revision/supersedes/time/pair binding, replay и
  conflicts и не изменяет observations или automatic evidence.
- [x] Fully fictional tests покрывают четыре rules, полную decision table,
  unavailable, same/cross-source, identity/policy/current/supersession,
  confirm/reject/inconclusive, revisions/replay/conflicts, immutability и
  non-transitivity.
- [x] Публичная поверхность узкая; модуль не импортирует Pydantic, JSON,
  filesystem, storage, clocks или UUID и не предоставляет merge/cluster API.
- [x] `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и
  `docs/tasks/README.md` отражают только фактический результат TASK-019 и
  называют ровно TASK-020 как следующий малый шаг.
- [x] `uv sync --frozen`, `uv lock --check`, новый test-module,
  `uv run quality` и `git diff --check` успешны.
- [x] `pyproject.toml`, `uv.lock`, `tests/fixtures` и golden не изменены; diff
  не содержит посторонних путей.
- [x] Создан один атомарный commit, рабочее дерево чистое, ветка не слита.

## Фактически выполненная работа

- Добавлен один нейтральный модуль `publication_duplicate_assessments.py`,
  напрямую повторно использующий `PublicationRef`, `ObservationKey`,
  `AvailableObservation`, `PublicationObservation`, canonical outcomes и
  provenance существующих normalization/observation contracts.
- Реализованы safe opaque policy/rule/reason/review codes, canonical unordered
  `PublicationPair`, exact `DuplicateAssessmentIdentity`, полные
  `DuplicateFieldSnapshot` и atomic result/conflict types. Mutable containers,
  пустые обязательные tuples и несогласованные side/field bindings отклоняются.
- Добавлена immutable `PUBLICATION_DUPLICATE_POLICY_V1` с точными четырьмя
  rules, versions, fields и policy order из ADR 0006. Supporting,
  contradicting и neutral findings сохраняются раздельно и не преобразуются в
  score, probability или tolerance.
- `assess_publication_pair` канонизирует observations целиком вместе со
  сторонами, возвращает stable same-reference conflict, отдельный
  `PairNotAssessed/side_not_available` либо complete assessment. Четыре rules и
  decision table реализованы буквально; полное структурное equality не зависит
  от порядка входа.
- Snapshots сохраняют существующие `PresentValue`/`MissingValue`/
  `UnsupportedValue` и полный provenance. Missing не получает raw,
  Unsupported сохраняет reason и raw, а location/price/currency mismatch
  остаются non-comparison.
- Добавлены `CurrentPairContext`, pure current/stale helpers и explicit
  `AssessmentSupersession` с one-pair/different-identity invariants, без
  repository или неявного вывода из времени.
- Реализованы separate manual-review draft/record/result types и
  `create_manual_review`: exact evidence/non-comparison references, supplied
  UTC time/identity, confirm/reject/inconclusive, revision 1/next revision,
  replacement assessment той же pair, replay и stable atomic conflicts.
  `review_revision_fork` сохранён как future stable code, но hidden state и fork
  detection не добавлялись.
- Добавлены 93 прямых fully fictional unit-теста rules, decision table,
  provenance, symmetry, unavailable, identity/current/supersession, all review
  outcomes/revisions/conflicts, immutability, non-transitivity и отсутствия
  I/O/merge/cluster API. Публичные символы осознанно экспортированы из пакета.

## Проверки

- `uv sync --frozen` — успешно; проверены 18 зафиксированных packages без
  изменения lock.
- `uv lock --check` — успешно; разрешены 18 packages без изменения `uv.lock`.
- `uv run pytest -q tests/test_publication_duplicate_assessments.py` — успешно,
  `93 passed`.
- `uv run quality` — успешно: Ruff format-check (`72 files`), Ruff lint,
  strict mypy (`33 source files`), основной pytest (`479 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно; предупреждения Git о будущем LF→CRLF checkout
  не являются whitespace errors.
- Проверка changed paths подтвердила отсутствие изменений `pyproject.toml`,
  `uv.lock`, `tests/fixtures`, golden и любых посторонних файлов.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-019 завершена в `task/019-duplicate-pair-assessment`, готова к отдельному
review/merge и намеренно не слита в `main`. Реализована только pure оценка
одной явно переданной пары и отдельная manual review; batch generation,
storage, external boundaries, physical property/merge/clustering и TASK-020 не
начинались.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`feat: implement duplicate pair assessment core`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-020 — принять контракт полностью вымышленного reviewed control set и
реализовать pure метрики качества duplicate policy: coverage, candidate/review
load и precision/recall только при достаточных labels, без real data, storage,
JSON, CLI или изменения policy. Эта задача здесь не начинается.
