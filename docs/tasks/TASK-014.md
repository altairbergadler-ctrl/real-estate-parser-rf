# TASK-014 — CLI и итоговый сквозной тест первого локального среза

- Статус: завершено в task-ветке, готово к review/merge
- Рабочая ветка: `task/014-cli-e2e`
- Целевая ветка: `main`

## Цель

Завершить первый детерминированный локальный срез: связать уже готовые
границы TASK-006…TASK-013 в один минимальный path-level application flow,
добавить пользовательскую команду
`uv run real-estate-parser search --listings <listings.json> --criteria <criteria.json>`
и доказать subprocess E2E-тестами байтовый контракт stdout, безопасный stderr,
exit codes, атомарность и повторяемость.

## Публичный application API

- `run_local_search(listings_path: Path, criteria_path: Path) -> LocalSearchResult`
- `LocalSearchSuccess(json_bytes: bytes)`
- `LocalSearchFailure(issues: tuple[ContractIssue, ...])`
- `LocalSearchResult = LocalSearchSuccess | LocalSearchFailure`

Result-типы минимальные, frozen/slots. Успех содержит только полные
канонические bytes, failure — только непустой tuple упорядоченных issues.
Операционные ошибки чтения файла и UTF-8 остаются исключениями внешней
границы и безопасно преобразуются только CLI-адаптером.

## Включённый объём

- Отдельный application orchestrator, независимо загружающий listings и
  criteria, объединяющий их content issues в глобальном контрактном порядке и
  прекращающий поток до адаптации при любой такой issue.
- Последовательная композиция существующих операций адаптации, атомарной
  коллекции, поиска, mapping и output serialization без новых предметных правил.
- Тонкий CLI на `argparse` с одним subcommand `search`, обязательными
  `--listings`/`--criteria`, console script и `python -m real_estate_parser`.
- Exit `0`: stdout byte-for-byte равен полным canonical `json_bytes`, stderr
  пуст; bytes пишутся через binary stdout без повторной сериализации и newline
  conversion.
- Exit `1`: stdout пуст, stderr содержит только отсортированные строки
  `CATEGORY/CODE/JSON_PATH`, по одной на LF, без traceback, входных значений,
  абсолютных путей и частичного JSON.
- Exit `2`: usage errors и безопасно обработанные file/UTF-8 failures;
  stdout пуст, а operational stderr называет только роль `listings` либо
  `criteria` и общую безопасную причину.
- Отдельные application composition tests и subprocess CLI E2E для всех
  утверждённых success/golden, partial semantics, syntax, multiple schema
  errors, normalization atomicity, duplicate publication, independent criteria
  failure, global ordering, usage/operational failures и repeated bytes.
- Только запись console script в `pyproject.toml`; механическое изменение
  `uv.lock` допустимо лишь если его требует metadata корневого проекта.
- Обновление согласованной документации состояния и завершения первого среза.

## Исключённый объём

- Новые правила входа, source adaptation, нормализации, collection, поиска,
  mapping, output schema или serialization.
- Запись result JSON в файл.
- Изменение или регенерация `tests/fixtures/v1`, expected/golden и `MANIFEST.md`.
- Новые зависимости.
- API, сервер, UI, база, HTTP/HTML, реальные площадки, сеть, Docker/CI,
  фоновые задачи, AI, OpenClaw, Telegram и публикация.
- Этап 3, физические объекты, дедупликация, история наблюдений и сигналы.
- Слияние в `main`, удаление ветки/worktree и начало следующей задачи.

## Решения задачи

- Новый ADR не создаётся: composition и локальный CLI уже приняты ADR 0002,
  а точный порядок диагностик и canonical bytes — ADR 0003/0004.
- `argparse` остаётся только внешним адаптером; application orchestrator не
  зависит от argparse, а ядро не получает зависимостей на CLI или Pydantic.

## Критерии готовности

- [x] Application flow атомарно возвращает полные canonical bytes либо
  непустой глобально упорядоченный tuple `ContractIssue`.
- [x] Оба входных документа загружаются независимо, поэтому content failures
  listings и criteria доказуемо объединяются; operational failures не
  маскируются под `INPUT_*`.
- [x] Console script и `python -m real_estate_parser` реализуют точные exit/stdout/
  stderr контракты без утечки абсолютных путей, exception text и traceback.
- [x] E2E-ALL-001, E2E-NONE-001 и E2E-EMPTY-001 совпадают с existing golden
  byte-for-byte; SEARCH-PARTIAL-001 сохраняет утверждённую семантику.
- [x] SYN-001, MULTI-001, NRM-006 и COL-001 дают точные diagnostics без
  частичного JSON; доказаны отдельная criteria issue и глобальный порядок двух
  независимо невалидных документов.
- [x] Usage, missing/non-UTF-8 input и повторный subprocess run проверены.
- [x] `uv lock --check`, `uv sync --frozen`, точечные tests, `uv run quality`,
  help/manual byte comparison, публичный импорт API, `git diff --check` успешны.
- [x] Dependencies и `tests/fixtures/v1` не изменены; полный diff не содержит
  посторонних изменений.
- [x] Документы состояния обновлены, создан один атомарный содержательный
  commit, рабочее дерево после него чистое, ветка не слита.

## Фактически выполненная работа

- Добавлен `real_estate_parser.application` с отдельным path-level
  `run_local_search`, минимальными frozen/slots success/failure и глобальной
  сортировкой issues двух независимо загруженных документов.
- Готовые операции TASK-006…TASK-013 скомпонованы строго последовательно;
  downstream stage запускается только после полного успеха предыдущей границы,
  а partial collection/result bytes наружу не выдаются.
- Operational file/UTF-8 failures сохранены отдельным role-aware exception с
  двумя безопасными reason codes; они не превращаются в `ContractIssue`.
- Добавлен тонкий `argparse` adapter, console script и `__main__.py`.
  Успешные bytes пишутся напрямую через binary stdout, issue/operational
  diagnostics — через binary stderr.
- Добавлены 12 application composition tests и 14 subprocess CLI E2E tests:
  три existing golden, partial-area, SYN-001, MULTI-001, NRM-006, COL-001,
  criteria failure, два независимо невалидных документа, usage, operational
  failures, repeatability и установленный console script.
- Публичный application API экспортирован из package root; CLI helpers там не
  экспортируются.
- Согласованы PROJECT, ARCHITECTURE, ROADMAP, CHECKPOINT, README, design docs и
  реестр задач. Новый ADR не потребовался.

## Проверки

- `uv lock --check` — успешно; `uv.lock` не изменён.
- `uv sync --frozen` — успешно, проверено 18 packages.
- `uv run pytest tests/test_application.py -q` — `12 passed`.
- `uv run pytest tests/test_cli_e2e.py -q` — `14 passed`.
- `uv run quality` — успешно: Ruff format-check (`57 files`), Ruff lint,
  strict mypy (`27 source files`), обычный pytest (`297 passed`) и fixture
  catalog integrity (`44 passed`).
- `uv run real-estate-parser --help` — exit `0`, показывает единственный
  subcommand `search`.
- Ручной запуск console script для comprehensive + all-three — exit `0`,
  stderr `0 bytes`, stdout `5429 bytes` и byte-for-byte равен
  `expected/search-all-three.json`.
- Публичный импорт `run_local_search`, `LocalSearchResult`,
  `LocalSearchSuccess`, `LocalSearchFailure` — успешно.
- `git diff --check`, полный просмотр diff, отсутствие изменений
  `tests/fixtures/v1`/`uv.lock` и отсутствие новых dependencies — успешно.
- Проверки выполнены на Windows; Linux в текущей среде не проверялся.

## Итоговый коммит

Атомарный содержательный коммит находится в истории по сообщению
`feat: complete first local CLI slice`. Точный SHA подтверждается Git после
создания коммита и не дублируется внутри его собственного снимка.

## Следующий рекомендуемый шаг

После review и отдельной интеграции TASK-014 в `main` остановиться и запросить
у пользователя отдельный выбор и декомпозицию следующего малого шага этапа 3.
TASK-015 этой задачей не определяется и не начинается.
