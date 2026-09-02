# TASK-018 — доказательная модель возможных дублей публикаций

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/018-duplicate-evidence-model`
- Целевая ветка: `main`
- Стартовый SHA: `a3bde301a6f172631c0583f04d9e05164b0f9980`

## Цель

Принять доказательную, симметричную и версионируемую модель оценки двух
разных source publications как возможных дублей. Автоматическая оценка должна
сохранять объяснимые supporting и contradicting evidence, отдельно допускать
immutable ручную проверку и никогда не превращаться в установленный факт
физического объекта, merge исходных публикаций или транзитивный cluster.

## Включённый объём

- ADR 0006 с рассмотренными вариантами, решением, последствиями и условиями
  пересмотра.
- Отдельная design-спецификация pair identity, symmetry, policy/observation
  binding, evidence, categorical decision table, replay, stale/supersession,
  conflicts, manual review и non-transitivity.
- Первая консервативная duplicate policy только на доступных полях
  `NormalizedListing` первого среза и с явными ограничениями этих данных.
- Минимальные будущие pure pseudotypes/API одной pair assessment и отдельной
  human review record без выбора storage или внешнего формата.
- Полностью вымышленные сценарии всех утверждённых переходов и границ.
- Согласование проектной документации и указание ровно одной следующей малой
  задачи — TASK-019.

## Исключённый объём

- Production Python-код, Python-тесты, fixtures/golden, `pyproject.toml` и
  `uv.lock`.
- `PhysicalProperty`, canonical merged listing, winner, merge/collapse,
  clustering, connected components и транзитивность.
- Batch candidate generation, blocking/indexing, large-scale matching и
  performance optimization.
- Storage/repository adapter, expected revision implementation, база данных,
  ORM, migrations, JSON/Pydantic/filesystem boundary, CLI/API/UI.
- Реальные источники, HTTP, polling, scheduler, retries/rate limits.
- Изменение нормализации, observation contracts TASK-015…TASK-017, первого
  среза, dependencies или внешних документов.
- Нестандартные персональные сигналы, AI/embeddings/LLM, OpenClaw, Telegram и
  уведомления.
- Реализация или начало TASK-019, слияние в `main`, публикация и удаление
  ветки/worktree.

## Критерии готовности

- [x] ADR 0006 и design spec однозначно задают unordered pair identity,
  symmetry, observation/policy binding, evidence/review separation,
  stale/replay/conflict semantics и non-transitivity.
- [x] `Missing`, `Unsupported` и unavailable/operational absence не становятся
  отрицательным duplicate evidence; автоматический outcome не подтверждает
  физический объект.
- [x] Первая policy и categorical decision table достаточно точны для
  следующей pure implementation task без numeric score или probability.
- [x] Supporting и contradicting evidence сохраняются одновременно и имеют
  стабильные rules, порядок, snapshots, provenance и безопасные reason codes.
- [x] Immutable manual review record объясним, версионируем, имеет явную
  supersession semantics и не меняет automatic evidence или source streams.
- [x] Полностью вымышленные сценарии покрывают symmetry, exact replay, новую
  observation, provenance, missing/unsupported, mixed evidence, insufficient
  input, same-source/cross-source, unavailable, все review outcomes,
  supersession и non-transitivity.
- [x] `ROADMAP.md` отмечает TASK-018 завершённой и называет ровно TASK-019 как
  следующий малый шаг с утверждёнными узкими границами.
- [x] `uv sync --frozen`, `uv lock --check`, `uv run quality`, проверка
  Markdown links и `git diff --check` успешны.
- [x] `src/`, `tests/`, `tests/fixtures`, `fixtures/golden`, `pyproject.toml` и
  `uv.lock` не изменены; diff не содержит посторонних изменений.
- [x] Создан один атомарный documentation commit, дерево чистое, task-ветка не
  слита.

## Фактически выполненная работа

- Создан ADR 0006. Он сравнивает и отклоняет immediate `PhysicalProperty`
  merge, numeric score, отрицание из missing/text mismatch, pairwise evidence
  с separate review и transitive clusters; принят только четвёртый вариант.
- Создана отдельная спецификация canonical unordered pair identity, точной
  assessment identity по двум available observation keys и версии policy,
  symmetry, full equality, replay, stale/current и explicit supersession.
- Определены структурные `DuplicateEvidenceItem` с rule id/version, polarity,
  policy-defined categorical strength, field snapshots, provenance обеих
  сторон и safe reason code, а также отдельный `RuleNonComparison` для
  missing/unsupported и намеренно нейтральных различий.
- Принята `publication-duplicate-policy@1` со стабильным порядком area, rooms,
  exact location text и exact price/currency. Точная categorical decision
  table требует exact area плюс rooms либо location, сохраняет mixed evidence
  и не использует score/probability.
- Unavailable side и operational uncertainty структурно возвращают
  `PairNotAssessed`, не assessment и не отрицательное evidence. Same-source и
  cross-source pairs разрешены, identical `PublicationRef` запрещена.
- Определена отдельная immutable manual review с supplied time,
  reviewer/reference codes, confirm/reject/inconclusive, rationale/evidence
  references, exact replay и строгой revision/supersedes/conflict semantics.
- Зафиксированы non-transitivity, запрет cluster/merge/canonical winner,
  сохранение исходных publications и privacy boundary без выводов о людях.
- Добавлена полностью вымышленная матрица всех назначенных сценариев и
  минимальные будущие pure APIs без storage или внешнего формата.
- Согласованы `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md`,
  `README.md`, реестр задач и две непосредственно связанные существующие
  design specifications. Production contracts и первый срез не менялись.

## Проверки

- `uv sync --frozen` — успешно; создана среда CPython 3.14.7 и установлены 18
  зафиксированных packages без изменения lock.
- `uv lock --check` — успешно; разрешены 18 packages без изменения `uv.lock`.
- `uv run quality` — успешно: Ruff format-check (`69 files`), Ruff lint,
  strict mypy (`31 source files`), основной pytest (`386 passed`) и fixture
  catalog integrity (`44 passed`).
- Относительные Markdown links во всех 11 изменённых документах — успешно:
  проверено 58 локальных ссылок, broken links нет.
- `git diff --check` — успешно; сообщения Git о будущем LF→CRLF checkout не
  являются whitespace errors.
- Проверка changed paths подтвердила отсутствие изменений `src/`, `tests/`,
  `tests/fixtures`, `fixtures/golden`, `pyproject.toml` и `uv.lock`.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-018 завершена только в ветке `task/018-duplicate-evidence-model`, готова к
отдельному review/merge и намеренно не слита в `main`. Создана только
design-only модель; Python implementation, tests, storage, external boundaries,
batch/clustering и TASK-019 не начинались.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`docs: define publication duplicate evidence model`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

После завершения TASK-018 — ровно TASK-019: реализовать neutral frozen/slots
duplicate-pair assessment, evidence и manual-review types и чистую
симметричную оценку одной пары по ADR 0006, без batch/clustering, storage,
JSON, CLI и изменений первого среза. TASK-019 здесь не начинается.
