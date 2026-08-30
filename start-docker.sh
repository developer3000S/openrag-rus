#!/usr/bin/env bash
#
# Запускает полный локальный стек OpenRAG через Docker Compose.
#
# Учитывает особенности этой машины:
#   * Порты 8000, 9000, 9443 заняты контейнером portainer (не OpenRAG),
#     поэтому Backend публикуется на 8001, а порты 9000/9443 не затрагиваются.
#   * Образы пересобраны на Debian, чтобы работать на CPU без x86-64-v3.
#
# Все обязательные переменные окружения подставляются здесь, если они ещё не
# заданы в окружении/в .env. Это нужно, потому что без них контейнеры падают:
#   - OpenSearch    -> отклоняет слабый/похожий на имя пользователя пароль;
#   - LangFlow      -> "Username and password must be set" (нужен суперпользователь);
#   - Backend       -> нужен валидный Fernet-ключ OPENRAG_ENCRYPTION_KEY.
#
# Сгенерированные секреты персистятся в .env (${ENV_FILE}), чтобы быть СТАБИЛЬНЫМИ
# между запусками. Это критично, потому что:
#   - Langflow создаёт суперпользователя ровно один раз — при первой инициализации
#     БД langflow-data/langflow.db. Если на каждый запуск генерировать новый пароль,
#     backend не сможет войти: "Login failed: incorrect password".
#   - OPENRAG_ENCRYPTION_KEY нельзя ротировать при каждом старте — уже
#     зашифрованные этим ключом данные станут нечитаемыми.

set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE="${OPENRAG_ENV_FILE:-.env}"
LANGFLOW_DATA_PATH="${LANGFLOW_DATA_PATH:-./langflow-data}"

# ---------------------------------------------------------------------------
# Хелперы для чтения и записи значений секретов в .env.
# ---------------------------------------------------------------------------
# Читает значение переменной KEY из .env. Возвращает 1 (и пустоту), если
# переменная отсутствует либо равно пустому значению.
env_file_value() {
  local key="$1"
  local file="$ENV_FILE"
  [[ -f "${file}" ]] || return 1
  local line
  line="$(grep -E "^${key}=" "${file}" | tail -n 1 || true)"
  [[ -n "${line:-}" ]] || return 1
  local value="${line#*=}"
  value="${value%$'\r'}"
  value="${value#\"}"; value="${value%\"}"
  value="${value#\'}"; value="${value%\'}"
  [[ -n "${value:-}" ]] || return 1
  printf '%s' "${value}"
}

# Пишет/обновляет значение переменной KEY в .env (без потери остальных строк).
set_env_file() {
  local key="$1" value="$2"
  local file="$ENV_FILE"
  if [[ ! -f "${file}" ]]; then
    printf '%s=%s\n' "${key}" "${value}" > "${file}"
  elif grep -qE "^${key}=" "${file}"; then
    python3 - "${file}" "${key}" "${value}" <<'PY'
import sys

path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
key_eq = key + "="

with open(path, "r", encoding="utf-8") as fh:
    lines = fh.readlines()

out, replaced = [], False
for line in lines:
    if line.startswith(key_eq):
        if not replaced:
            out.append(key_eq + value + "\n")
            replaced = True
    else:
        out.append(line)

if not replaced:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(key_eq + value + "\n")

with open(path, "w", encoding="utf-8") as fh:
    fh.write("".join(out))
PY
  else
    printf '\n%s=%s\n' "${key}" "${value}" >> "${file}"
  fi
  echo ">>> ${file}: ${key}=<сохранён>"
}

# ---------------------------------------------------------------------------
# Порт Backend. 8000 занят portainer, поэтому используем 8001.
# ---------------------------------------------------------------------------
export OPENRAG_BACKEND_PORT="${OPENRAG_BACKEND_PORT:-8001}"

# ---------------------------------------------------------------------------
# Порты остальных сервисов (все свободны на этой машине).
# ---------------------------------------------------------------------------
export OPENSEARCH_PORT="${OPENSEARCH_PORT:-9200}"
export OPENSEARCH_PERF_PORT="${OPENSEARCH_PERF_PORT:-9600}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export LANGFLOW_PORT="${LANGFLOW_PORT:-7860}"
export OPENSEARCH_DASHBOARDS_PORT="${OPENSEARCH_DASHBOARDS_PORT:-5601}"

# ---------------------------------------------------------------------------
# Секреты. Сначала берём уже сохранённые значения из .env; значение
# генерируем и персистим только если его ещё нет ни в окружении, ни в .env.
# ---------------------------------------------------------------------------

# OpenSearch: сильный пароль, не похожий на имя пользователя "admin".
# OpenSearch (opensearch-security demo installer) падает с "Weak password",
# если пароль не проходит zxcvbn-проверку, поэтому слабые значения из .env
# (например "Admin@12345") мы автоматически заменяем на сильные.
password_is_strong() {
  local p="$1"
  [[ "${#p}" -ge 12 ]] || return 1
  [[ "${p}" =~ [a-z] ]] || return 1
  [[ "${p}" =~ [A-Z] ]] || return 1
  [[ "${p}" =~ [0-9] ]] || return 1
  [[ "${p}" =~ [^a-zA-Z0-9] ]] || return 1
  [[ "$(printf '%s' "${p}" | tr '[:upper:]' '[:lower:]')" != admin* ]] || return 1
}

if [[ -z "${OPENSEARCH_PASSWORD:-}" ]]; then
  OPENSEARCH_PASSWORD="$(env_file_value OPENSEARCH_PASSWORD || true)"
fi
if [[ -z "${OPENSEARCH_PASSWORD:-}" ]]; then
  OPENSEARCH_PASSWORD="Core#Thr0ught!77Xx"
  set_env_file OPENSEARCH_PASSWORD "${OPENSEARCH_PASSWORD}"
elif ! password_is_strong "${OPENSEARCH_PASSWORD}"; then
  echo ">>> ВНИМАНИЕ: OPENSEARCH_PASSWORD из .env слишком слабый — заменяю на сильный."
  OPENSEARCH_PASSWORD="Core#Thr0ught!77Xx"
  set_env_file OPENSEARCH_PASSWORD "${OPENSEARCH_PASSWORD}"
fi
export OPENSEARCH_PASSWORD

# Backend: валидный Fernet-ключ OPENRAG_ENCRYPTION_KEY.
if [[ -z "${OPENRAG_ENCRYPTION_KEY:-}" ]]; then
  OPENRAG_ENCRYPTION_KEY="$(env_file_value OPENRAG_ENCRYPTION_KEY || true)"
fi
if [[ -z "${OPENRAG_ENCRYPTION_KEY:-}" ]]; then
  OPENRAG_ENCRYPTION_KEY="$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || true)"
  if [[ -z "${OPENRAG_ENCRYPTION_KEY}" ]]; then
    # Запасной вариант: стабильный ключ из hashlib (BASE64-URL, 44 символа).
    OPENRAG_ENCRYPTION_KEY="$(python3 -c "import base64,hashlib; print(base64.urlsafe_b64encode(hashlib.sha256(b'openrag-dev-key-0000000000').digest()).decode())" 2>/dev/null || echo "b3BlbnJhZy1kZXYta2V5LTAwMDAwMDAwMDAwMDAwMDAwMDAtMDAw")"
  fi
  set_env_file OPENRAG_ENCRYPTION_KEY "${OPENRAG_ENCRYPTION_KEY}"
fi
export OPENRAG_ENCRYPTION_KEY

# LangFlow: суперпользователь, секрет и ключи Langfuse.
LANGFLOW_SUPERUSER="$(env_file_value LANGFLOW_SUPERUSER || true)"
LANGFLOW_SUPERUSER="${LANGFLOW_SUPERUSER:-langflow}"
export LANGFLOW_SUPERUSER

# LANGFLOW_SUPERUSER_PASSWORD. Флаг *_GENERATED помечает, что мы только что
# создали новый пароль — ниже по нему сработает авто-восстановление БД.
LANGFLOW_SUPERUSER_PASSWORD="$(env_file_value LANGFLOW_SUPERUSER_PASSWORD || true)"
LANGFLOW_SUPERUSER_PASSWORD_GENERATED=""
if [[ -z "${LANGFLOW_SUPERUSER_PASSWORD:-}" ]]; then
  # Случайный 18-символьный пароль (цифры+буквы), не похож на имя пользователя.
  LANGFLOW_SUPERUSER_PASSWORD="$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(18)))" 2>/dev/null || echo "Langflow#Passw0rd78")"
  LANGFLOW_SUPERUSER_PASSWORD_GENERATED="1"
  set_env_file LANGFLOW_SUPERUSER_PASSWORD "${LANGFLOW_SUPERUSER_PASSWORD}"
fi
export LANGFLOW_SUPERUSER_PASSWORD

if [[ -z "${LANGFLOW_SECRET_KEY:-}" ]]; then
  LANGFLOW_SECRET_KEY="$(env_file_value LANGFLOW_SECRET_KEY || true)"
fi
if [[ -z "${LANGFLOW_SECRET_KEY:-}" ]]; then
  LANGFLOW_SECRET_KEY="$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-langflow-secret-key-__placeholder")"
  set_env_file LANGFLOW_SECRET_KEY "${LANGFLOW_SECRET_KEY}"
fi
export LANGFLOW_SECRET_KEY

export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"

# ---------------------------------------------------------------------------
# Авто-восстановление LangFlow-БД.
#
# Langflow создаёт суперпользователя ровно один раз — при первой инициализации
# langflow-data/langflow.db. Если пароль «разошёлся» с БД (например, .env был
# пуст, пароль сгенерирован заново, а в БД остался хэш старого), backend
# зацикливается на "Login failed: incorrect password". В этом случае переносим
# старую БД (langflow.db ± langflow.db-wal/-shm) в langflow-data/backup-<ts>/,
# чтобы Langflow пересоздал её и завёл суперпользователя с паролем из .env.
# Обратите внимание: встроенные флоу backend пересоздаст сам (из flows/), а
# пользовательские правки флоу останутся в перенесённой БД-бэкапе.
# ---------------------------------------------------------------------------
if [[ -n "${LANGFLOW_SUPERUSER_PASSWORD_GENERATED}" ]]; then
  langflow_db="${LANGFLOW_DATA_PATH}/langflow.db"
  if [[ -f "${langflow_db}" ]]; then
    has_superuser="$(python3 - "${langflow_db}" "${LANGFLOW_SUPERUSER}" <<'PY' 2>/dev/null || echo "0"
import sqlite3, sys

db, username = sys.argv[1], sys.argv[2]
try:
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT 1 FROM user WHERE username = ? AND is_superuser = 1 LIMIT 1",
        (username,),
    ).fetchone()
    conn.close()
    print("1" if row else "0")
except Exception:
    print("0")
PY
)"
    if [[ "${has_superuser}" == "1" ]]; then
      backup_dir="${LANGFLOW_DATA_PATH}/backup-$(date +%Y%m%d-%H%M%S)"
      mkdir -p "${backup_dir}"
      docker compose -f docker-compose.yml -f docker-compose.backend-port.yml stop langflow >/dev/null 2>&1 || true
      for f in langflow.db langflow.db-wal langflow.db-shm; do
        if [[ -f "${LANGFLOW_DATA_PATH}/${f}" ]]; then
          mv "${LANGFLOW_DATA_PATH}/${f}" "${backup_dir}/"
        fi
      done
      echo ""
      echo ">>> ВНИМАНИЕ: сброшена БД LangFlow — логин суперпользователя был рассинхронизирован."
      echo ">>> Старая БД сохранена в: ${backup_dir}"
      echo ">>> Langflow пересоздаст суперпользователя с паролем из .env, backend заново импортирует встроенные флоу."
      echo ""
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Сборка/подготовка локальных образов.
#
# Этот CPU поддерживает максимум x86-64-v2 (нет AVX2), поэтому образы из
# реестра langflowai/*:latest (на базе UBI/Red Hat) падают с ошибкой
# "Fatal glibc error: CPU does not support x86-64-v3" — их glibc собран на
# x86-64-v3 и не умеет fallback-диспатча. Рабочие локальные сборки на базе
# Debian помечены тегом :debian-fix. Ниже мы либо перетегируем их на :latest
# (быстро), либо, если их нет, собираем заново, чтобы `docker compose up`
# использовал именно Debian-образы, а не сломанные из реестра.
# ---------------------------------------------------------------------------
build_or_retag_image() {
  local image="$1"   # полное имя образа без тега (например langflowai/openrag-backend)
  local dockerfile="$2"

  if docker image inspect "${image}:debian-fix" >/dev/null 2>&1; then
    echo ">>> Использую готовый Debian-образ ${image}:debian-fix -> ${image}:latest"
    docker tag "${image}:debian-fix" "${image}:latest"
  else
    echo ">>> Собираю Debian-образ ${image}:latest (${dockerfile})..."
    docker build -t "${image}:latest" -f "${dockerfile}" .
  fi
}

build_or_retag_image "docker.io/langflowai/openrag-opensearch" "Dockerfile"
build_or_retag_image "docker.io/langflowai/openrag-backend"   "Dockerfile.backend"
build_or_retag_image "docker.io/langflowai/openrag-frontend"  "Dockerfile.frontend"
build_or_retag_image "docker.io/langflowai/openrag-langflow"  "Dockerfile.langflow"

# ---------------------------------------------------------------------------
# Запуск всех контейнеров OpenRAG (включая dashboards).
#
# Базовый docker-compose.yml не публикует порт backend-а наружу (в штатной
# схеме фронтенд ходит в него по внутренней сети compose). На этой машине мы
# хотим прямой доступ к backend-у через http://localhost:${OPENRAG_BACKEND_PORT},
# поэтому подключаем override docker-compose.backend-port.yml с привязкой порта.
# ---------------------------------------------------------------------------
echo ">>> Запуск контейнеров OpenRAG (Backend -> :${OPENRAG_BACKEND_PORT})..."
docker compose -f docker-compose.yml -f docker-compose.backend-port.yml up -d

echo ">>> Статус контейнеров:"
docker compose -f docker-compose.yml -f docker-compose.backend-port.yml ps

echo ""
echo "Сервисы OpenRAG:"
echo "Название контейнера	Адрес по умолчанию	Цель"
echo "OpenRAG Backend		http://localhost:${OPENRAG_BACKEND_PORT}	Сервер FastAPI и основные функциональные возможности."
echo "OpenRAG Frontend	http://localhost:${FRONTEND_PORT}	Веб-интерфейс React для взаимодействия с пользователем."
echo "LangFlow		http://localhost:${LANGFLOW_PORT}	Механизм управления рабочими процессами на основе ИИ."
echo "OpenSearch		http://localhost:${OPENSEARCH_PORT}	Хранилище данных для знаний."
echo "OpenSearch Dashboards	http://localhost:${OPENSEARCH_DASHBOARDS_PORT}	Интерфейс администрирования базы данных OpenSearch."