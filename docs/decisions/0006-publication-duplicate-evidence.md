# 0006. Доказательная оценка возможных дублей source publications

- Статус: принято
- Дата: 2026-09-02
- Задача: TASK-018

## Контекст

После TASK-015…TASK-017 приложение умеет хранить независимые histories
повторных observations ровно одной `PublicationRef`. Следующий предметный шаг
должен оценивать, могут ли две разные source publications описывать один
физический объект, но доступные данные первого среза ограничены свободным
`location_text`, точной ценой, валютой, общей площадью и числом комнат. В них
нет подтверждённого адреса, координат, идентификатора объекта, фото-хэшей или
данных собственника.

Ошибочное объединение уничтожило бы различие source identity и истории, а
одно число сходства скрыло бы основания и неопределённость. `Missing`,
`Unsupported`, недоступность публикации и операционные ошибки также нельзя
выдавать за несовпадение физических объектов. Нужна минимальная модель,
которая остаётся полезной для ручной проверки и не утверждает больше, чем
доказывают исходные observations.

## Рассмотренные варианты

### Немедленно создавать или сливать `PhysicalProperty`

Отклонено. Данные первого среза не устанавливают физическую identity. Merge
сделал бы гипотезу необратимым фактом, смешал бы `PublicationRef`, provenance и
histories, потребовал бы canonical winner и правил разрешения конфликтов,
которых сейчас нет.

### Хранить только numeric similarity score или probability

Отклонено. Число без структурных оснований не объясняет, какие поля были
сравнимы, где находились данные и почему результат изменился. Доступного
контрольного набора нет и вероятность невозможно честно откалибровать; порог
создал бы псевдоточность и скрыл бы одновременно существующие supporting и
contradicting evidence.

### Считать `Missing`, `Unsupported` или text mismatch отрицательным evidence

Отклонено. Отсутствующее или неподдерживаемое поле означает недостаток
сравнимого ввода. Различие свободного `location_text`, цены или времени
наблюдения/публикации может возникнуть у повторной публикации того же объекта и
само по себе не доказывает разные объекты. Такое правило систематически
превращало бы неопределённость и особенности источника в отрицательный факт.

### Pairwise evidence assessment и отдельная ручная проверка

Принято. Автоматическая оценка относится к неупорядоченной паре двух разных
`PublicationRef`, точным `AvailableObservation` обеих сторон и версии policy.
Она хранит структурные supporting и contradicting evidence, отдельные
not-comparable результаты и один объяснимый categorical outcome. Ручная
проверка является новым immutable human assertion поверх точной assessment и
не переписывает автоматические evidence или histories.

### Сразу строить transitive clusters или connected components

Отклонено. Pairwise relation не транзитивна: независимые основания `A~B` и
`B~C` ничего не доказывают о `A~C`. Автоматический cluster распространил бы
ошибку одной связи, скрыл бы исходные публикации и фактически ввёл бы merge до
проверки качества каждой пары.

## Решение

- До и после оценки существуют независимые `PublicationRef` и их observation
  histories. `PhysicalProperty`, merged listing и canonical winner не
  создаются.
- Допустима только пара разных `PublicationRef`; разные публикации одного
  источника и публикации разных источников обрабатываются одинаково.
- Пара неупорядоченная. Стороны канонически назначаются сравнением
  `SourceId.value`, затем `PublicationId.value`; перестановка входов не меняет
  identity, evidence, outcome или порядок.
- Автоматическая assessment привязана к полным точным `AvailableObservation`
  обеих сторон и `DuplicatePolicyVersion`. `UnavailableObservation`, batch
  omission, timeout и иная операционная неопределённость assessment не
  создают.
- Identity assessment структурно состоит из канонической pair identity, двух
  соответствующих `ObservationKey` и версии policy. Exact replay равного
  полного результата является no-op; та же identity с иным содержимым —
  конфликт, а не overwrite.
- Новое observation любой стороны или новая версия policy создаёт другую
  assessment. Старая остаётся исторически объяснимой, но является stale для
  текущего решения и не переиспользуется молча.
- Evidence хранит стабильные rule id/version, polarity, policy-defined
  categorical strength, сравниваемые field names, полные canonical snapshots
  и provenance обеих сторон и короткий безопасный reason code. Голого score
  или probability нет.
- `Missing` и `Unsupported` дают отдельный not-comparable результат правила,
  не contradicting evidence. Free-text location mismatch, price mismatch и
  разные observation timestamps также не являются отрицательным evidence.
- Первая policy использует только `total_area`, `rooms`, точное совпадение
  `location_text` и дополнительное точное совпадение полной цены. `source_url`
  и `PublicationRef` остаются publication identity; `ObservedAt` — координата
  observation. Валюта участвует только в проверке сравнимости цены.
- Aggregate имеет только три outcomes:
  `CANDIDATE_REQUIRES_MANUAL_REVIEW`,
  `CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW` и
  `INSUFFICIENT_EVIDENCE_NO_CANDIDATE`. Ни один outcome не называется и не
  означает confirmed same property.
- Supporting и contradicting evidence сохраняются одновременно. Ни одно
  противоречие не удаляет support, и support не удаляет противоречие.
- Manual review — отдельная immutable revision с переданными вызывающей
  стороной временем, reviewer/reference codes, одним из outcomes
  `CONFIRMED_RELATIONSHIP`, `REJECTED_RELATIONSHIP`, `INCONCLUSIVE`, rationale
  codes, ссылками на evidence и явным supersedes. Даже confirmed является
  human assertion, не merge и не физическим фактом системы.
- Ни автоматическая, ни ручная pairwise relation не транзитивна. Clustering,
  connected components, автоматический merge/collapse и скрытие публикаций
  запрещены.
- Модель не делает выводов о личности собственника, местонахождении человека
  или иных чувствительных признаках. Reason/rationale codes не содержат
  произвольный персональный текст.

Точные псевдотипы, первая policy, decision table, replay/stale/conflict и
review semantics заданы в
[PUBLICATION-DUPLICATE-EVIDENCE.md](../design/PUBLICATION-DUPLICATE-EVIDENCE.md).

## Последствия

- Следующая реализация сможет быть чистой, симметричной и тестируемой без
  storage, JSON, часов, случайности и инфраструктуры.
- Результат останется объяснимым при смене observation или policy: старые
  evidence не переписываются и не теряются.
- Ограниченные поля первого среза будут давать много conservative
  `INSUFFICIENT_EVIDENCE_NO_CANDIDATE`; это честнее вымышленной уверенности.
- Ручная работа нужна для каждого кандидата и конфликта; подтверждение одной
  пары не распространяется на соседние пары.
- Поиск кандидатов среди большого набора, хранение, API/UI и измерение качества
  остаются отдельными задачами и не определяются этим решением.

## Проверка и условия пересмотра

Решение проверяется следующей чистой реализацией frozen/slots типов и функции
оценки одной пары, exhaustive fully fictional tests на symmetry, decision
table, replay/conflicts, stale inputs и manual review revisions. Пересмотр
нужен, если появятся проверенные структурные адреса/координаты или другие
неперсональные признаки, контрольный набор позволит откалибровать иной
aggregate, либо доказанный workflow потребует сущность физического объекта.
Такой пересмотр обязан сохранить исходные `PublicationRef`, observations и
provenance и оформляется новым ADR; он не может молча превратить историческую
assessment в факт или транзитивный merge.
