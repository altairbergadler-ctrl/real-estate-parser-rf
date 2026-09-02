# 0009. Атомарная композиция assessment для готовых duplicate candidates

- Статус: принято
- Дата: 2026-09-02
- Задача: TASK-024

## Контекст

TASK-022 формирует bounded `DuplicateCandidateGenerationResult`, а TASK-019
чисто оценивает одну явно переданную пару через `assess_publication_pair`.
Между ними отсутствует контракт, который доказывает, что готовые candidates
относятся к тому же полному current context, и атомарно оценивает только эти
pairs. Простого цикла недостаточно: generation result хранит exact keys, но не
полное содержимое observations; assessment требует именно полные
`AvailableObservation`; candidate и assessment policies имеют разные
identities; downstream union допускает `PairNotAssessed` и failure.

Композиция должна оставаться pure. Она не может повторять generation,
добавлять all-pairs fallback, трактовать blocking matches как evidence,
сохранять partial success либо вводить storage, I/O или физический объект.

## Рассмотренные варианты

### Повторно запустить candidate generation из current observations

Отклонено. Это смешало бы selection и assessment, могло бы получить иной
result при другой configuration и скрыло бы binding к caller-supplied
`DuplicateCandidateGenerationResult`.

### Доверять только references кандидата и брать любые current observations

Отклонено. Новая observation той же `PublicationRef` могла бы быть оценена под
устаревшей candidate identity. Требуется exact equality всех generation keys и
current available keys, включая отдельное различение missing, extra и
same-reference/new-key context.

### Останавливать batch на первом конфликте или первом downstream failure

Отклонено. Preflight может собрать все независимо доказуемые structural
conflicts без вызова assessment. После начала pure pass downstream operation не
имеет side effects, поэтому оставшиеся candidates можно проверить ровно один
раз и вернуть полный детерминированный conflict set.

### Возвращать partial successful assessments рядом с failure

Отклонено. Такой результат зависел бы от места первого сбоя и позволял бы
consumer принять неполный batch. Failure не содержит item outcomes.

### Отдельная pure atomic batch composition

Принято. Она связывает exact generation result, canonical current available
context и явно переданную assessment policy, затем вызывает существующую
single-pair operation ровно по materialized candidates.

## Решение

- Batch run имеет отдельную identity из exact
  `DuplicateCandidateGenerationIdentity` и явно переданной
  `DuplicatePolicyVersion`. Candidate policy и assessment policy остаются
  разными identities; assessment version не выводится из candidate policy.
- Поддерживаются только полный
  `PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1` в generation result и полный
  `PUBLICATION_DUPLICATE_POLICY_V1` как assessment policy. Совпадения одной
  version string недостаточно при изменённых rules.
- Current input принимается только как tuple, должен быть непустым и содержать
  только `AvailableObservation`. После атомарной проверки он канонизируется и
  содержит ровно одно observation на `PublicationRef`. Equal key с иным
  полным содержимым и repeated reference — разные structural conflicts.
- Canonical current keys обязаны точно совпасть с
  `generation_identity.canonical_input_keys`. Отсутствующий generation key,
  лишняя current reference и новый key той же reference различаются typed
  mismatch kind и не схлопываются в свободный текст.
- Full observation content существует только в current input и передаётся в
  assessment. Snapshots, blocking keys, candidate metadata и generation
  identity не заменяют observation.
- Каждый candidate обязан быть связан с exact generation policy, canonical
  pair и exact left/right current keys. Композиция не создаёт pairs и не
  оценивает references вне `generation_result.candidates`.
- Blocking matches остаются routing metadata готового generation result. Они
  не передаются как evidence, не влияют на assessment outcome и не
  переоцениваются скрытым regeneration pass.
- Все независимо доказуемые preflight conflicts собираются в unique canonical
  tuple до первого assessment call. При любом preflight conflict число вызовов
  `assess_publication_pair` равно нулю.
- Empty candidates после успешного preflight дают успешный batch с пустым
  tuple item outcomes и нулём assessment calls.
- Для каждого candidate в canonical generation order существующая
  `assess_publication_pair` вызывается ровно один раз с exact left/right
  `AvailableObservation` в canonical candidate order и с явно переданной
  assessment policy. Same-source и cross-source pairs допустимы; self-pair
  исключена `PublicationPair` и binding invariants.
- Для корректно связанного v1 input ожидается только `PairAssessmentSuccess`.
  Его pair, keys, policy, полные side observations и identity проверяются
  повторно перед созданием item outcome.
- `PairNotAssessed` для двух available sides становится typed
  `unexpected_pair_not_assessed`; `PairAssessmentFailure` и malformed success
  становятся typed `downstream_assessment_conflict`. Они не выбрасываются как
  operational exception и не создают partial success.
- После первого downstream conflict pure pass продолжается по всем оставшимся
  candidates. Каждый всё равно вызывается ровно один раз; все downstream
  conflicts канонизируются. Итог — atomic batch failure без item outcomes,
  даже если часть calls вернула success.
- Success сохраняет batch identity, полный exact generation result как
  configuration/content binding, полный assessment policy и ordered tuple
  item outcomes. Item identity содержит batch identity и исходную candidate
  identity; outcome содержит exact candidate и exact `PairAssessmentSuccess`.
- Одинаковые полные inputs и policies дают structurally equal result. Equal
  item identity с иным content — `item_identity_content_conflict`; equal batch
  identity с иным full content — `batch_identity_content_conflict`. Future
  consumer не выбирает winner и не выполняет overwrite.
- Lookup/composition выполняет `O(N + C)` работы плюс стоимость ровно `C`
  pair assessments, где `N` — current observations, `C` — materialized
  candidates. Допустима линейная canonical validation уже ordered contracts;
  all-pairs scan, regeneration, transitive closure и hidden fallback
  запрещены.
- Assessment остаётся pairwise hypothesis. Batch не подтверждает physical
  property, не объединяет histories, не создаёт winner/cluster и не делает
  relation транзитивной.

Точные pseudotypes, constructor invariants, conflict taxonomy, call order,
replay semantics, complexity proof и fictional scenarios заданы в
[PUBLICATION-DUPLICATE-ASSESSMENT-BATCH.md](../design/PUBLICATION-DUPLICATE-ASSESSMENT-BATCH.md).

## Последствия

- TASK-025 сможет реализовать узкую composition поверх существующих public
  contracts без изменения candidate или assessment policies.
- Caller обязан передать полный exact current context отдельно от generation
  result; хранить только keys или snapshots недостаточно.
- Downstream failure может потребовать оставшиеся pure calls, поэтому failure
  стоимостью не меньше успешного полного pass, но conflict set не зависит от
  места первого сбоя.
- Полная generation result в success делает replay/content conflicts
  проверяемыми без repository design, ценой структурного повторного reference
  в batch result.
- Контракт ничего не решает о persistence, concurrency, external formats,
  production throughput или качестве blocking/assessment.

## Проверка и условия пересмотра

Решение проверяется TASK-025 neutral frozen/slots contracts и fully fictional
unit tests на exact context binding, zero-call preflight failure, empty batch,
one-call-per-candidate, downstream atomicity, permutations, replay и
non-transitivity. Новый ADR нужен, если изменятся supported policy versions,
single-pair result union, candidate result contract либо появится доказанная
потребность в side-effecting execution. Пересмотр не может молча разрешить
partial success, regeneration, all-pairs fallback, storage semantics,
physical-property merge или cluster.
