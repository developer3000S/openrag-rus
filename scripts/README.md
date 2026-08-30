# Скрипты OpenRAG

## Массовая загрузка (`openrag_bulk.py`)

`openrag_bulk.py` — автономный клиент для загрузки каталога или набора
файлов через публичный API приёма OpenRAG. Он группирует файлы в серверные
задачи, поддерживает ограниченное число задач в процессе выполнения, опрашивает их
до завершения и по мере выполнения записывает атомарную запись `summary.json`.

Семейства команд намеренно разделены:

- `bulk upload` загружает файлы или каталоги, предоставленные пользователем.
- `bench arxiv` получает воспроизводимый набор данных arXiv, а затем делегирует свой этап
  загрузки тому же массовому загрузчику.

Скрипт содержит встроенные метаданные зависимостей `uv` и не импортирует приложение
OpenRAG или SDK, поэтому его также можно скопировать и запускать вне этого репозитория.

Задайте URL фронтенда OpenRAG и API-ключ с разрешениями `knowledge:upload` и
`knowledge:read:own`:

```bash
export OPENRAG_URL=http://localhost:3000
export OPENRAG_API_KEY=orag_your_api_key

uv run scripts/openrag_bulk.py bulk upload ./documents \
  --include '*.pdf' \
  --exclude 'archive/*' \
  --batch-size 10 \
  --max-inflight 4 \
  --max-submit 2
```

`--batch-size` определяет, сколько файлов отправляется в каждом multipart-запросе.
`--max-inflight` ограничивает число отправленных задач OpenRAG, включая задачи,
находящиеся на этапе загрузки или опроса. `--max-submit` может установить более низкий предел для одновременных
multipart-запросов, что полезно, когда файлы большие.

Полезные параметры загрузки включают:

| Параметр | Назначение |
| --- | --- |
| `--sort path\|size-asc\|size-desc` | Выбирает порядок, в котором файлы группируются в пакеты. |
| `--include GLOB`, `--exclude GLOB` | Фильтрует относительные пути или имена файлов; повторите любой из параметров. |
| `--no-recursive` | Читать только файлы непосредственно внутри указанных каталогов. |
| `--settings-json JSON_OR_@FILE` | Передаёт настройки приёма знаний для каждого запуска. |
| `--tweaks-json JSON_OR_@FILE` | Передаёт настройки приёма Langflow (tweaks). |
| `--no-replace-duplicates` | Сохраняет существующие документы с дублирующимися именами файлов. |
| `--task-timeout SECONDS` | Ограничивает ожидание каждой отправленной серверной задачи. |
| `--runs-dir DIR`, `--output-dir DIR`, `--run-id ID` | Управляют локальными записями о запусках. |

При подключении напрямую к бэкенду, а не через прокси фронтенда,
выберите его префикс маршрута явно:

```bash
uv run scripts/openrag_bulk.py bulk upload ./documents \
  --base-url http://localhost:8000 \
  --api-prefix /v1
```

Запуски по умолчанию сохраняются в `~/.openrag/bulk/runs`. Их можно просмотреть
без работающего сервера или API-ключа:

```bash
uv run scripts/openrag_bulk.py bulk list
uv run scripts/openrag_bulk.py bulk summary
uv run scripts/openrag_bulk.py bulk summary --detail latest
```

Команда загрузки завершается с кодом состояния `0`, когда каждый пакет завершается успешно, `1`, когда
один или несколько пакетов/файлов завершаются с ошибкой, и `2` при недопустимых входных данных или конфигурации.

### Бенчмарк arXiv и загрузчик PDF

Тот же автономный клиент включает бенчмарк arXiv из `openrag-lite`.
Он может подготовить PDF-файлы без сервера или передать подготовленные PDF-файлы напрямую в
приведённый выше массовый загрузчик.

По умолчанию бенчмарк копирует оплачиваемый запрашивающим (requester-pays) tarball PDF arXiv с S3,
кэширует tarball, извлекает выбранные PDF-файлы и загружает их в OpenRAG:

```bash
export OPENRAG_URL=http://localhost:3000
export OPENRAG_API_KEY=orag_your_api_key

uv run scripts/openrag_bulk.py bench arxiv \
  --max-results 100 \
  --batch-size 10 \
  --max-inflight 4
```

Путь S3 требует AWS CLI и учётные данные, которые могут читать
оплачиваемый запрашивающим бакет `s3://arxiv`. Переопределите `--s3-uri`, чтобы использовать другой tarball;
обычные локальные пути и URL `file://` также поддерживаются.

Чтобы вместо этого запросить Atom API arXiv и загрузить PDF-файлы по отдельности, выберите
источник Atom. Клиент по умолчанию применяет трёхсекундную задержку вежливости между
запросами arXiv:

```bash
uv run scripts/openrag_bulk.py bench arxiv \
  --source atom \
  --category cs.AI \
  --date-from 2025-01-01 \
  --date-to 2025-01-31 \
  --max-results 25
```

`--query` принимает необработанный поисковый запрос arXiv и переопределяет запрос категории/даты.
`--start`, `--sort-by` и `--sort-order` управляют выбором источника.

Загружайте и кэшируйте PDF-файлы без подключения к OpenRAG, передав
`--download-only`; API-ключ не требуется:

```bash
uv run scripts/openrag_bulk.py bench arxiv \
  --source atom \
  --query 'cat:cs.CL' \
  --max-results 10 \
  --download-only
```

Кэш PDF по умолчанию находится в `~/.openrag/benchmarks/arxiv/pdfs`. Существующие PDF-файлы и
tarball S3 повторно используются по умолчанию. Сбои загрузки Atom запоминаются в
`_failed_downloads.json`; передайте `--retry-failed-downloads`, чтобы повторить их, или
`--no-skip-existing`, чтобы создать свежие PDF-файлы.

Записи о запусках бенчмарка по умолчанию находятся в `~/.openrag/benchmarks/arxiv/runs`:

```bash
uv run scripts/openrag_bulk.py bench arxiv list
uv run scripts/openrag_bulk.py bench arxiv summary
uv run scripts/openrag_bulk.py bench arxiv summary --detail latest
```

## Синхронизация ролей пользователей по умолчанию (`sync_default_user_roles.py`)

Вспомогательный скрипт только для разработки для RBAC в **режиме OSS** (`OPENRAG_RUN_MODE=oss`): обновляет
существующих пользователей в SQL-базе данных, когда изменяется `OPENRAG_DEFAULT_ROLE`. Требуется:

```env
OPENRAG_RUN_MODE=oss
OPENRAG_SYNC_DEFAULT_ROLE=true
OPENRAG_DEFAULT_ROLE=admin   # целевая роль: admin | developer | user | viewer
```

Игнорируется в режимах `saas` и `on_prem` — эти режимы назначают роли из JWT-claims.

Использует базу данных SQLite по умолчанию в `data/openrag.db`, если не задан `DATABASE_URL`.

### Повышение всех ролей `user` до `OPENRAG_DEFAULT_ROLE`

Используйте это, когда у пользователей всё ещё есть роль `user`, но вы хотите назначить им ту роль,
которая задана в `OPENRAG_DEFAULT_ROLE` (например, `admin`):

```bash
OPENRAG_SYNC_DEFAULT_ROLE=true \
OPENRAG_DEFAULT_ROLE=admin \
uv run python scripts/sync_default_user_roles.py --from-role user
```

### Явное «из → в» (игнорирует целевую переменную окружения)

Когда обе роли указаны в CLI, целевая роль берётся из `--to-role`, а не
из `OPENRAG_DEFAULT_ROLE`:

```bash
OPENRAG_SYNC_DEFAULT_ROLE=true \
uv run python scripts/sync_default_user_roles.py --from-role admin --to-role user
```

Переносит каждого пользователя, чья **единственная** роль — `admin`, в роль `user`, независимо от
того, что задано в `OPENRAG_DEFAULT_ROLE`.

Что он делает:

- Находит каждого пользователя, чья **единственная** роль — `user`
- Назначает ему роль из `OPENRAG_DEFAULT_ROLE` (здесь: `admin`)
- Пропускает пользователей с несколькими ролями или другой единственной ролью
- Обновляет сохранённый базовый уровень в `workspace_config.meta`

Предварительный просмотр без записи:

```bash
OPENRAG_SYNC_DEFAULT_ROLE=true \
OPENRAG_DEFAULT_ROLE=admin \
uv run python scripts/sync_default_user_roles.py --from-role user --dry-run
```

Замените `user` на любую исходную роль и задайте `OPENRAG_DEFAULT_ROLE` на целевую
роль, которую вы хотите.

### Другие команды

| Команда | Назначение |
| --- | --- |
| `uv run python scripts/sync_default_user_roles.py` | Синхронизация, когда значение по умолчанию из окружения изменилось с момента последней записанной базовой линии |
| `--dry-run` | Показать изменения без записи в БД |
| `--from-role ROLE` | Исходная роль для этого запуска (переопределяет сохранённую базовую линию) |
| `--to-role ROLE` | Целевая роль (переопределяет `OPENRAG_DEFAULT_ROLE`; требует `--from-role`) |
| `--from-noauth-role ROLE` | Исходная роль для анонимного пользователя |
| `--to-noauth-role ROLE` | Целевая роль для анонимного пользователя (переопределяет `OPENRAG_NOAUTH_ROLE`) |
| `--record-baseline` | Сохранить текущие значения по умолчанию из окружения; не изменять ни одного пользователя |

### После выполнения

Перезапустите бэкенд (или дождитесь `OPENRAG_PERM_CACHE_TTL`, по умолчанию 60 с), чтобы
проверки разрешений подхватили новые роли. Проверьте с помощью:

```bash
curl -b "auth_token=..." http://localhost:8000/users/me
```

### Примечания

- Предназначен для локальных рабочих процессов разработки OSS, а не для управления ролями в производстве.
- Если скрипт сообщает об устаревших пользователях, но не обновляет ни одного, используйте `--from-role` с
  той ролью, которая есть у этих пользователей в настоящее время.

## Сброс онбординга (`reset_onboarding.py`)

Повторно запускает мастер онбординга, сбрасывая конфигурацию рабочего пространства в БД
(`OPENRAG_STORAGE_MODE=db` по умолчанию):

```bash
uv run python scripts/reset_onboarding.py
```

Что он делает:

- Устанавливает `workspace_config.meta.edited` в `false` (`GET /api/onboarding-status` → `onboarded: false`)
- Очищает `workspace_config.onboarding` (включая `current_step` → `0`)
- В режимах `hybrid` / `files` также обновляет `config.yaml`

Необязательные флаги:

| Флаг | Назначение |
| --- | --- |
| `--dry-run` | Предварительный просмотр без записи |
| `--reset-models` | Также очистить выбранные модели LLM и встраивания |

Пример — полный сброс мастера, включая выбор моделей:

```bash
uv run python scripts/reset_onboarding.py --reset-models
```

После выполнения **перезапустите бэкенд** и перезагрузите приложение.

Этот скрипт **не** удаляет принятые документы, фильтры знаний, Langflow-процессы
или беседы. Для полного удаления используйте аутентифицированную конечную точку API
`POST /settings/rollback-onboarding`.
