# Дорожная карта

## Правила выполнения

- Одна задача даёт один небольшой, проверяемый результат.
- Одна задача выполняется в одной короткоживущей ветке `task/<номер>-<краткое-название>`.
- Задача начинается с явных границ и критериев готовности и заканчивается проверками, обновлением собственного файла и `CHECKPOINT.md`.
- Завершённая задача сливается в `main`; следующая задача не начинается автоматически.
- Порядок после ближайшей задачи предварительный и уточняется по результатам предыдущих задач.

## Этап 0. Фундамент

- **TASK-001 — первоначальный фундамент проекта.** Git-история, проектные принципы, правила работы, дорожная карта и контрольная точка. Завершено.

## Этап 1. Проектирование минимального среза

- **TASK-002 — технологический стек и минимальный сквозной срез.** Сравнить варианты по требованиям проекта, выбрать минимально достаточный стек и описать один сквозной сценарий от тестового входа до результата поиска. Завершено.
- **TASK-003 — предметная модель и границы контрактов.** Минимальные сущности, происхождение данных, состояния неопределённости и контракты между модулями для выбранного среза. Завершено.
- **TASK-004 — стратегия проверок и фикстур.** Уровни тестирования, точные внешние документы v1, полностью вымышленные данные, негативная матрица и байтовые эталоны. Завершено.

## Этап 2. Первый детерминированный сквозной сценарий

- **TASK-005 — программный каркас и команды качества.** Минимальный `src`-layout, зафиксированные зависимости и одна воспроизводимая команда Ruff/mypy/pytest/fixture checks. Завершено; предметный поток не начат.
- **TASK-006 — граничная загрузка локального пакета публикаций v1.** Строгая Pydantic-граница `fixture-source-batch@1`, чтение локального JSON и явно типизированный выход для будущего source adapter без адаптации, нормализации или поиска. Завершено.
- **TASK-007 — фиктивный source adapter.** Адаптировать проверенный пакет через контракт фиктивного источника, проверить source, publication id и URL без нормализации. Завершено.
- **TASK-008 — детерминированная нормализация одного снимка.** Нормализовать один `SourcePublicationSnapshot` в `NormalizedListing` с точными преобразованиями, происхождением и состояниями `Present`/`Missing`/`Unsupported`, без коллекции и поиска. Завершено.
- **TASK-009 — атомарная нормализация пакета и immutable collection.** Нормализовать все snapshots полного `SourceBatch`, собрать ошибки и только при полном успехе построить `CollectionSnapshot` с уникальными `PublicationRef`, без поиска и output mapping. Завершено.
- **TASK-010 — строгая граница `search-criteria@1` и канонический `SearchCriteria`.** Прочитать один локальный criteria JSON, строго валидировать Pydantic boundary и преобразовать его в neutral immutable criteria без выполнения поиска. Завершено.
- **TASK-011 — чистая операция стандартного поиска.** Принять `CollectionSnapshot + SearchCriteria`, применить критерии конъюнктивно и вернуть детерминированный результат без output mapping и CLI. Завершено.
- **TASK-012 — чистое каноническое отображение результата.** Преобразовать `SearchResult` в immutable `SearchResultDocument` со всеми состояниями и provenance, без Pydantic output validation, JSON serialization и CLI. Завершено.
- **TASK-013 — строгая output boundary и детерминированная JSON-сериализация.** Проверить `SearchResultDocument` строгой Pydantic-моделью и сериализовать в детерминированный UTF-8 JSON с byte-exact проверкой существующих golden, без CLI и path-level orchestration. Завершено.
- **TASK-014 — CLI и итоговый сквозной тест первого среза.** Связать уже готовые границы в один path-level поток, добавить пользовательскую команду и проверить stdout/stderr, exit codes, атомарность и golden bytes. Завершено и слито в `main`; первый локальный сквозной срез завершён.

Каждый пункт перед началом оформляется отдельной задачей; реализация этапа не объединяется в одну крупную ветку.

## Этап 3. Качество данных

- **TASK-015 — модель повторных наблюдений и изменений публикации.** Принять
  доказательную семантику observation stream одной `PublicationRef`,
  substantive/raw-only/provenance изменений, подтверждённой недоступности,
  reappearance, replay и конфликтов без реализации и выбора storage. Завершено
  и слито в `main`.
- **TASK-016 — нейтральные observation/change types и pure append одного
  наблюдения.** Реализовать frozen/slots types и чистую детерминированную
  операцию сравнения/добавления одного observation по ADR 0005, без хранилища,
  JSON, CLI и изменения первого среза. Завершено и слито в `main`.
- **TASK-017 — атомарное добавление набора observations в несколько histories.**
  Реализовать чистую атомарную операцию добавления набора observations в
  несколько независимых publication histories с глобально детерминированными
  conflicts и без storage, JSON, CLI и изменений первого среза. Завершено и
  слито в `main`.
- **TASK-018 — доказательная модель возможных дублей публикаций.** Принять
  объяснимые положительные и отрицательные основания возможного совпадения,
  статус ручной проверки и границы неопределённости без программной
  реализации, physical-property merge, storage или AI. Завершено и слито в
  `main`.
- **TASK-019 — pure duplicate-pair assessment и manual-review types.**
  Реализовать neutral frozen/slots duplicate-pair assessment, evidence и
  manual-review types и чистую симметричную оценку одной пары по ADR 0006, без
  batch/clustering, storage, JSON, CLI и изменений первого среза. Завершено и
  слито в `main`.
- **TASK-020 — reviewed control set и pure duplicate-policy quality metrics.**
  Принять контракт полностью вымышленного reviewed control set и реализовать
  pure метрики coverage, candidate/review load и precision/recall только при
  достаточных labels, без real data, storage, JSON, CLI или изменения policy.
  Завершено и слито в `main`.
- **TASK-021 — deterministic bounded duplicate candidate generation design.**
  Принять отдельную candidate policy из двух exact blocking passes, whole-bucket
  oversized outcome, stable union/replay/conflicts и exact missed-pair coverage
  на fully fictional control population без реализации, all-pairs scan,
  storage, clustering, JSON, CLI или real data. Завершено и слито в `main`.
- **TASK-022 — neutral frozen/slots blocking/candidate types и pure bounded
  generation.** Реализовать exact two-pass policy, atomic current-input
  validation, whole-bucket oversized outcomes и deterministic candidate union
  без assessment, coverage, storage или external boundaries. Завершено и слито
  в `main`.
- **TASK-023 — pure exact duplicate-candidate blocking coverage.** Реализовать
  frozen/slots counts, exact ratio/typed unavailable и atomic inconsistent-result
  conflict поверх готовых control set и generation result без повторного
  assessment/generation, storage или external boundaries. Завершено и слито в
  `main`.
- **TASK-024 — design pure atomic duplicate-candidate assessment batch.**
  Принять exact generation/current binding, separate policy identities,
  zero-call preflight, one-call-per-candidate composition и atomic downstream
  conflicts без partial outcomes, storage, external boundaries или
  physical-property semantics. Завершено в
  `task/024-duplicate-assessment-batch-design`, не слито в `main`.
- TASK-025 — реализовать neutral frozen/slots batch-assessment contracts и pure deterministic composition по ADR 0009 для exact DuplicateCandidateGenerationResult/current AvailableObservation binding, без storage, JSON, CLI, real data или изменения candidate/assessment policies. Следующая рекомендуемая малая задача; не начата.

- Добавить версионируемые правила нормализации.
- Позднее сохранить и использовать историю наблюдений через отдельно выбранный
  infrastructure adapter.

## Этап 4. Источники и эксплуатационный контур

- Определить юридические, этические и технические ограничения для первого реального источника.
- Реализовать первый адаптер источника без проникновения его особенностей в ядро.
- Добавить ограничение частоты, повторные попытки, контроль ошибок и наблюдаемость.
- Добавлять следующие источники по одному, подтверждая совместимость контрактов.

## Этап 5. Доказательные сигналы

- Реализовать детерминированные сигналы и представление доказательств.
- Ввести калибровку уверенности и процесс ручной проверки.
- Оценить экономику и качество на контрольном наборе.
- Только отдельной задачей решить, нужен ли необязательный ИИ-модуль для предварительно отобранных объявлений.

## Этап 6. Уведомления и интеграции

- Спроектировать независимые события и предпочтения уведомлений.
- Реализовать первый нейтральный канал доставки.
- Подключать Telegram и OpenClaw только внешними адаптерами, отдельными задачами и без зависимости ядра от них.

## Этап 7. Пользовательский опыт и масштабирование

- Спроектировать интерфейс на основании проверенных сценариев.
- Оптимизировать производительность по измерениям.
- Рассматривать разделение монолита только при наличии подтверждённого эксплуатационного ограничения.
