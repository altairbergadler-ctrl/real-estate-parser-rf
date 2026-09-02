# 0010. Consumer-owned persistence и replay boundary публикаций

- Статус: принято
- Дата: 2026-09-02
- Задача: TASK-026

## Контекст

TASK-016 и TASK-017 реализовали immutable observation histories и атомарный
pure append. TASK-019, TASK-022, TASK-023 и TASK-025 добавили manual-review
revisions, bounded candidate generation, blocking coverage и atomic assessment
batch. Их structural identities, exact replay и equal-identity/different-
content conflicts уже определены, но всё существует только в памяти процесса.

Будущий side-effecting слой должен загружать исходное состояние, вызывать
готовые pure operations и фиксировать результат без partial writes и скрытого
last-write-wins. При этом преждевременный выбор SQL/NoSQL/filesystem или одной
универсальной repository abstraction связал бы предметные контракты с
неизмеренной инфраструктурой. Также нельзя объявить все вычисленные artifacts
новыми фактами: candidate, assessment и metrics зависят от exact input и
versioned policy, тогда как observation и supplied human decision имеют иной
источник авторитетности.

## Рассмотренные варианты

### Только observation histories как source of truth

Сохранять immutable observations, а candidates, assessments, batch results,
manual-review context и quality artifacts пересчитывать по запросу.

Преимущество — минимальный объём хранения и одна очевидная предметная основа.
Недостатки — потеря доказательства, какой exact generation result и assessment
были реально предъявлены человеку или использованы downstream; повторный
расчёт требует старого кода и полной policy configuration; дорогой batch будет
выполняться снова; human revision может ссылаться на уже недоступный artifact.
Вариант недостаточен для доказательного аудита.

### Все histories и derived artifacts как самостоятельные authoritative records

Считать observations, candidates, assessments, batches, control metrics и
проекции равноправным authoritative state и обновлять каждый вид независимо.

Преимущество — быстрые reads без recompute. Недостатки — несколько
конкурирующих истин, риск рассогласования, сложный write coordination и
неясная семантика исправления deterministic artifact. Идемпотентность
превращается в синхронизацию множества mutable copies, а новые policy versions
рискуют переписать старое объяснение. Вариант ухудшает модульность и
доказательность.

### Гибрид: authoritative histories и human decisions плюс version-bound audit

Считать immutable observations и supplied human assertions authoritative в
своих узких смыслах. Deterministic candidates, assessments и batch artifacts
остаются derived, но их committed экземпляр сохраняется immutable как audit
record, если он участвовал в side-effecting workflow. Current views, heads,
indexes, current/stale и quality metrics являются rebuildable projections.
Recompute создаёт тот же exact content для той же identity либо новый artifact
под новой input/policy identity; он не заменяет старую запись молча.

Преимущества — сохраняются evidence и точный фактический workflow, replay
дешёв и проверяем, пересчёт разрешён без превращения derived output в новую
истину, а порты остаются узкими и принадлежат consumers. Цена — необходимо
хранить version/lineage coordinates и некоторые вычислимые artifacts дольше,
чем требуется только для online read.

### Сравнение по критериям решения

| Критерий | Только histories | Всё authoritative | Гибрид |
| --- | --- | --- | --- |
| Доказательность | исходные observations сохранены, но фактически использованный derived workflow теряется | artifacts сохранены, но вычисление ошибочно повышено до самостоятельного факта | source/human authority отделена от immutable audit вычислений |
| Воспроизводимость | зависит от доступности старого кода/policy и может быть дорогой | сохранённый output доступен, но независимые mutable records могут расходиться | exact inputs/policies retained; same identity проверяется structural equality |
| Стоимость пересчёта | максимальная: candidates/assessments строятся снова | минимальная online, но высока стоимость синхронизации copies | audit read дешёв; disposable projections пересчитываются по необходимости |
| Модульность | простой history store, но downstream audit требует обходных связей | generic store/координация проникают во многие модули | каждый application consumer владеет узким typed port |
| Идемпотентность | history replay определён, downstream side effects не доказаны | несколько mutable winners осложняют replay | identity/content replay и expected revision имеют единый явный порядок |
| Будущая эксплуатация | слабая диагностика исторического workflow | много согласуемого state и риск last-write-wins | atomic units, receipts, typed conflicts и rebuild projections разделены |

## Решение

Принят **гибридный вариант**.

- Authoritative publication state — неизменяемая последовательность
  `AvailableObservation | UnavailableObservation` каждой `PublicationRef`.
  `PublicationObservationHistory` является canonical snapshot этой
  последовательности на конкретной revision. Никакой derived duplicate
  artifact не меняет observation history.
- Authoritative human state — supplied immutable
  `DuplicatePairManualReview` revisions и independently supplied control
  labels только в пределах exact assessment/control population. Они являются
  human assertions, а не physical-property fact.
- `ChangeSet`, `DuplicateCandidateGenerationResult`, pair assessments,
  `DuplicateCandidateAssessmentBatch`, explicit supersession links и
  зафиксированные control inputs являются derived или relational artifacts.
  Committed экземпляр, который использован для review, публикации результата
  или иной side effect, сохраняется immutable как audit record вместе с exact
  inputs, policy/configuration и lineage.
- Quality metrics, blocking coverage, current/stale status, current review
  head, lookup indexes и materialized current views — disposable projections.
  Их можно удалить и построить снова из retained authoritative/audit records.
- `SourcePublicationSnapshot` и boundary batches не становятся автоматически
  authoritative state этой границы. Если legal/audit policy потребует raw
  capture, он хранится отдельным immutable upstream record по будущему
  consumer-owned контракту; текущие persistence ports его не изобретают.
- Контракты принадлежат consuming application boundaries, а infrastructure
  adapters реализуют их снаружи. Принимаются отдельные
  `ObservationHistoryPort`, `DuplicateGenerationArtifactPort`,
  `DuplicateAssessmentArtifactPort`, `ManualReviewRevisionPort` и
  `DuplicateQualityAuditPort`. Единого `Repository[T]`, dynamic plugin loader и
  storage-owned domain interface нет.
- Common revision — opaque concurrency token конкретного stream/artifact slot
  или review head. Она не входит в domain identity, не является timestamp и не
  сравнивается по величине. Ожидание задаётся явно как `ABSENT` либо exact
  ранее загруженная revision.
- Commit сначала разрешает structural identity. Equal identity и equal full
  content дают `REPLAYED` без изменения revision. Equal identity и different
  content дают typed content conflict. Только для ещё не сохранённой identity
  проверяется expected revision; mismatch даёт conflict, а не overwrite.
- Multi-history observation append фиксирует как одну atomic unit все и только
  затронутые streams, immutable commit receipt и их post-revisions. Один
  conflict оставляет все streams и receipt неизменными.
- Один generation result является atomic artifact. Assessment-batch commit
  атомарно проверяет либо сохраняет embedded exact generation result и полный
  batch; generation без batch допустима, batch без exact generation binding —
  нет.
- Одна manual-review revision, её `supersedes` и новый head фиксируются как
  одна atomic unit. Previous revisions не изменяются. Fork или stale expected
  head не выбирает winner.
- Exact retry после success является no-op. После неизвестного исхода
  interrupted commit consumer обязан загрузить запись по той же structural
  identity: exact content означает replay, different content — conflict,
  absence разрешает повтор той же команды. Partial state запрещён при любом
  исходе.
- Stale read приводит к `expected_revision_mismatch`; consumer загружает новое
  состояние и заново выполняет pure operation. Adapter не применяет
  last-write-wins и не объединяет competing results.
- Recompute при тех же full inputs и policy обязан дать structurally equal
  content. Иной content под той же identity является conflict. Новые
  observation keys, bucket limit или policy version создают новую identity;
  предыдущий artifact сохраняется, а supersession добавляется только явно.
- Normal observation append не принимает out-of-order backfill и не
  переписывает history, как требует ADR 0005. Историческая материализация
  отсутствующего derived artifact допустима по его exact identity. Изменение
  authoritative observation timeline требует отдельного ADR и workflow.
- Никакая routine retention или recompute operation не удаляет и не
  переписывает observations, manual-review revisions, committed audit
  artifacts, commit receipts или supersession links. Projection можно
  пересоздать. Физическое архивирование/удаление и legal retention требуют
  отдельной policy.

Точные pseudotypes, owners, atomic units, reads, conflicts, ordering, retention
и fictional scenarios заданы в
[PUBLICATION-PERSISTENCE-AND-REPLAY.md](../design/PUBLICATION-PERSISTENCE-AND-REPLAY.md).

## Последствия

- Future executor может быть тонкой side-effecting composition:
  load → pure operation → compare-and-commit. Его scheduling, retry budget и
  orchestration здесь не проектируются.
- Exact replay не зависит от случайного request id, JSON bytes, storage clock
  или revision. Для observation multi-stream commit нужен retained structural
  receipt, иначе crash-after-commit нельзя надёжно отличить от нового запроса.
- Derived audit занимает место, но сохраняет exact explanation и не требует
  старого runtime для ответа «что было реально использовано».
- Projection loss не является потерей evidence; projection corruption
  исправляется rebuild из retained records.
- Concurrent writers получают deterministic replay/content/revision outcomes;
  ни arrival order, ни максимальный timestamp не выбирают winner.
- Один infrastructure adapter может реализовать несколько портов общей
  транзакцией, но domain/application modules не зависят от его технологии и не
  объединяются generic repository.
- TASK-027 сможет реализовать только neutral Python port contracts и
  deterministic in-memory reference adapter. Выбор durable storage остаётся
  отдельным решением после измерения объёма, запросов, retention и concurrency.

## Проверка и условия пересмотра

Решение проверяется TASK-027 in-memory adapter tests на first commit, exact
retry, identity/content conflict, expected-revision conflict, concurrent
writers и отсутствие partial state во всех atomic units. Полностью вымышленные
сценарии design-спецификации задают ожидаемые outcomes до implementation.

Новый ADR нужен, если measured workload требует distributed coordination,
если legal retention требует raw capture или deletion workflow, если обычный
append должен поддержать out-of-order correction, если quality controls
получат отдельную revision model, либо если durable technology меняет atomic
guarantees. Пересмотр не может молча ослабить immutable evidence, exact replay,
expected revisions, no-partial-write или no-last-write-wins semantics.
