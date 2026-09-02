# Задачи проекта

Каждая задача — небольшой проверяемый результат с явными границами. Её файл является переносимым отчётом для будущих сессий, а не заменой истории Git.

## Жизненный цикл

1. Создать `TASK-NNN.md` с целью, включённым и исключённым объёмом и критериями готовности.
2. Создать короткоживущую ветку `task/NNN-краткое-название` от актуальной `main`.
3. Выполнить только заявленный объём и подходящие проверки.
4. Записать фактическую работу и результаты проверок в файл задачи.
5. Обновить `CHECKPOINT.md`.
6. Слить завершённую ветку в `main` понятным merge-коммитом, если задача не предписывает иной безопасный способ.
7. Убедиться, что активна `main`, рабочее дерево чистое, и остановиться до отдельного указания на следующую задачу.

## Обязательные разделы задачи

- цель;
- включённый объём;
- исключённый объём;
- критерии готовности;
- фактически выполненная работа;
- проверки;
- итоговый коммит или однозначный способ найти его в истории;
- следующая рекомендуемая задача.

## Реестр

- [TASK-001](TASK-001.md) — первоначальный фундамент проекта; завершено.
- [TASK-002](TASK-002.md) — технологический стек и минимальный сквозной срез; завершено.
- [TASK-003](TASK-003.md) — предметная модель и границы контрактов; завершено.
- [TASK-004](TASK-004.md) — стратегия проверок и фикстур; завершено.
- [TASK-005](TASK-005.md) — программный каркас и единая команда качества; завершено.
- [TASK-006](TASK-006.md) — граничная загрузка локального пакета публикаций v1; завершено.
- [TASK-007](TASK-007.md) — фиктивный source adapter без нормализации; завершено.
- [TASK-008](TASK-008.md) — детерминированная нормализация одного снимка; завершено.
- [TASK-009](TASK-009.md) — атомарная нормализация пакета и immutable
  collection; завершено.
- [TASK-010](TASK-010.md) — строгая граница `search-criteria@1` и
  канонический `SearchCriteria`; завершено.
- [TASK-011](TASK-011.md) — чистая операция стандартного поиска по
  `CollectionSnapshot + SearchCriteria` без output mapping и CLI; завершено.
- [TASK-012](TASK-012.md) — чистое каноническое отображение `SearchResult` в
  immutable `SearchResultDocument` без Pydantic output validation, JSON
  serialization и CLI; завершено.
- [TASK-013](TASK-013.md) — строгая Pydantic output boundary и
  детерминированная UTF-8 JSON serialization `SearchResultDocument` с
  byte-exact проверкой существующих golden, без CLI и path-level
  orchestration; завершено.
- [TASK-014](TASK-014.md) — CLI, path-level application flow и итоговый
  subprocess E2E первого локального среза; завершено и слито в `main`.
- [TASK-015](TASK-015.md) — доказательная модель повторных observation,
  изменений, подтверждённой недоступности и reappearance одной
  `PublicationRef`; завершено и слито в `main`.
- [TASK-016](TASK-016.md) — neutral frozen/slots observation/change types и
  чистое детерминированное сравнение/добавление одного observation одной
  `PublicationRef`; завершено и слито в `main`.
- [TASK-017](TASK-017.md) — чистая атомарная batch-композиция observations в
  несколько histories с каноническими outcomes и глобальными conflicts без
  partial state или storage; завершено и слито в `main`.
- [TASK-018](TASK-018.md) — доказательная симметричная модель pairwise
  duplicate assessment, supporting/contradicting evidence и отдельной manual
  review без physical-property merge, storage или AI; завершено и слито в
  `main`.
- [TASK-019](TASK-019.md) — neutral frozen/slots duplicate-pair assessment,
  policy-ordered evidence/non-comparison и отдельная pure manual review с
  revision semantics без batch/clustering, storage или external boundary;
  завершено в task-ветке, готово к review/merge.
