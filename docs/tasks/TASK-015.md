# TASK-015 — модель повторных наблюдений и изменений публикации

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/015-observation-change-model`
- Целевая ветка: `main`
- Стартовый SHA: `766a9f3f639bbcaa864cfc8cb431c985c388e38c`

## Цель

Принять минимальный доказательный дизайн нескольких наблюдений одной source
publication, её содержательных изменений, подтверждённой недоступности и
повторного появления. Дизайн должен сохранить `PublicationRef`, канонический
`ObservedAt` и полное provenance, не вводить физический объект недвижимости и
не связывать будущую реализацию с форматом данных или способом хранения.

## Включённый объём

- ADR 0005 с рассмотренными вариантами, решением, последствиями и условиями
  пересмотра.
- Отдельная design-спецификация с точными терминами, инвариантами,
  псевдотипами, таблицей переходов и полностью вымышленными сценариями.
- Структурный ключ наблюдения на основе `PublicationRef + ObservedAt`, правила
  exact replay, равных timestamps, out-of-order поступления и атомарного
  добавления.
- Версионированное детерминированное сравнение полей `source_url`,
  `location_text`, `price_amount`, `currency`, `total_area`, `rooms` с явным
  различием substantive change, source-representation-only change,
  provenance refresh и успешного no-change.
- Доказательная модель подтверждённой недоступности, повторного появления и
  неизвестного результата сетевой/source ошибки без вывода disappearance из
  частичного batch.
- Минимальный будущий pure API и потребительский контракт будущего
  repository/storage port без выбора технологии и без реализации.
- Согласование проектной документации и указание ровно одной следующей малой
  задачи — TASK-016.

## Исключённый объём

- Production Python-код и новые Python-тесты.
- База данных, файловое хранение, ORM, миграции и repository adapter.
- Изменение CLI, `search-result@1`, fixtures, golden или границ TASK-006…TASK-014.
- Реальные источники, HTTP, polling, scheduler, retries и rate limiting.
- Cross-source dedup, сущность физического объекта, сигналы, уведомления, UI,
  API, AI, OpenClaw и Telegram.
- Новые зависимости и изменения `pyproject.toml` или `uv.lock`.
- Реализация или начало TASK-016, слияние в `main`, публикация, удаление ветки
  или worktree.

## Критерии готовности

- [x] ADR 0005 принимает семантику наблюдений, изменений, недоступности и
  reappearance и объясняет отклонённые варианты.
- [x] Design-спецификация однозначно задаёт идентичность потока и наблюдения,
  порядок, exact replay, equal-timestamp conflict, out-of-order policy и
  атомарность.
- [x] `PublicationRef` не смешивается с физическим объектом, а отсутствие в
  batch структурно не является доказательством недоступности.
- [x] Все переходы `Present`/`Missing`/`Unsupported`, причина `Unsupported`,
  canonical before/after и оба provenance определены детерминированно.
- [x] `ChangeSet` версионирован, имеет стабильный порядок полей и различает
  substantive, raw-only, provenance-only и успешный пустой результат.
- [x] Подтверждённая недоступность требует явного source state либо
  conclusive-проверки конкретной `PublicationRef`; timeout, блокировка, network
  error и неполный scan оставляют состояние неизвестным.
- [x] Описаны reappearance, повторная недоступность, идемпотентные повторы,
  future conflict codes и нейтральный repository/storage port.
- [x] Полностью вымышленные сценарии покрывают все назначенные случаи.
- [x] `ROADMAP.md` отмечает TASK-015 завершённой и называет ровно одну следующую
  задачу TASK-016 с утверждёнными узкими границами.
- [x] `uv sync --frozen`, `uv lock --check`, `uv run quality` и
  `git diff --check` успешны.
- [x] `pyproject.toml`, `uv.lock`, `src/`, `tests/fixtures` и golden не изменены;
  полный diff не содержит посторонних изменений.
- [x] Документы состояния обновлены, создан один атомарный documentation
  commit, рабочее дерево после него чистое, ветка не слита.

## Фактически выполненная работа

- Создан ADR 0005 с принятым observation stream одной `PublicationRef`,
  структурным `PublicationRef + ObservedAt` key, exact replay,
  equal-timestamp conflict, out-of-order policy, доказательной unavailable
  semantics и отложенным storage choice.
- Создана отдельная спецификация с immutable pseudotypes available/unavailable
  observations, history, `FieldSnapshot`, `FieldDelta`, `ChangeSet`, append
  results и stable conflict codes.
- Зафиксирована `publication-change-policy@1` и точный порядок шести полей.
  Полная таблица `Present`/`Missing`/`Unsupported` определяет canonical
  before/after, `Unsupported.reason_code`, оба provenance и различие
  substantive, source-representation-only и provenance refresh.
- Определены successful empty `ChangeSet`, первая фиксация, replay,
  out-of-order rejection, атомарность набора и отсутствие partial history.
- Unavailable observation разрешён только при direct source state либо
  conclusive targeted check конкретной publication по versioned rule. Batch
  omission и operational failures структурно оставлены unknown; deleted/expired
  не утверждаются без прямого source claim.
- Определены confirmed unavailable, repeated unavailable, reappearance и
  минимальный consumer-owned repository port с expected revision без выбора
  базы, ORM, filesystem или формата сериализации.
- Добавлена полностью вымышленная decision table всех назначенных сценариев.
- Согласованы `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md`,
  `README.md`, реестр задач и три существующие design docs только ссылками и
  актуальными границами; первый исполняемый срез не изменён.

## Проверки

- `uv sync --frozen` — успешно; создана среда CPython 3.14.7, установлено 18
  зафиксированных packages.
- `uv lock --check` — успешно; lock разрешён без изменения.
- `uv run quality` — успешно: Ruff format-check (`60 files`), Ruff lint,
  strict mypy (`27 source files`), основной pytest (`297 passed`) и fixture
  catalog integrity (`44 passed`).
- Проверка относительных Markdown links во всех изменённых документах —
  успешно.
- `git diff --check` — успешно.
- Проверка списка изменённых путей подтвердила отсутствие изменений
  `pyproject.toml`, `uv.lock`, `src/`, `tests/fixtures` и golden.
- Проверки выполнены на Windows; Linux в этой задаче не запускался.

## Итог

TASK-015 завершена в `task/015-observation-change-model`, готова к отдельному
review/merge и не слита в `main`. Production-код, тесты, dependencies,
fixtures, golden и внешние контракты первого среза не менялись.

## Итоговый коммит

Один атомарный commit находится в истории по сообщению
`docs: define publication observation change model`. Точный SHA подтверждается
Git после создания commit и не дублируется внутри его собственного снимка.

## Следующая рекомендуемая задача

TASK-016 — реализовать neutral frozen/slots observation/change types и чистую
детерминированную операцию сравнения/добавления одного наблюдения по ADR 0005,
без хранилища, JSON, CLI и изменения первого среза. Эта задача здесь не
начинается.
