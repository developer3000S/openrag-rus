<div align="center">

<img src="./docs/static/img/openrag-logo-dog.svg" alt="" width="120"/>

# OpenRAG

<h3>
  <em>Интеллектуальный поиск по документам на основе агентов</em>
</h3>

<!-- Badges -->

[![Langflow](https://img.shields.io/badge/Langflow-1C1C1E?style=for-the-badge&logo=langflow)](https://github.com/langflow-ai/langflow)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?style=for-the-badge&logo=opensearch&logoColor=white)](https://github.com/opensearch-project/OpenSearch)
[![Docling](https://img.shields.io/badge/Docling-000000?style=for-the-badge)](https://github.com/docling-project/docling)

[![YouTube Channel](https://img.shields.io/youtube/channel/subscribers/UCn2bInQrjdDYKEEmbpwblLQ?label=Subscribe&style=social)](https://www.youtube.com/@OpenRAG/)
[![GitHub stars](https://img.shields.io/github/stars/langflow-ai/openrag?style=social)](https://github.com/langflow-ai/openrag/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/langflow-ai/openrag?style=social)](https://github.com/langflow-ai/openrag/network/members)

[![Documentation](https://img.shields.io/badge/Documentation-773eff)](https://docs.openr.ag) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/langflow-ai/openrag)

</div>

---

OpenRAG — это комплексная платформа генерации с дополнением знаний (Retrieval-Augmented Generation, RAG), которая обеспечивает интеллектуальный поиск по документам и диалоги на основе искусственного интеллекта.

Пользователи могут загружать, обрабатывать и запрашивать документы через чат-интерфейс, работающий на базе больших языковых моделей и возможностей семантического поиска. Система использует Langflow для приёма документов, рабочих процессов извлечения и интеллектуальных подсказок, обеспечивая бесшовный опыт работы с RAG.

Ознакомьтесь с [документацией](https://docs.openr.ag/) или начните с [быстрого старта](https://docs.openr.ag/quickstart).

Создано на основе [FastAPI](https://fastapi.tiangolo.com/) и [Next.js](https://github.com/vercel/next.js).
Работает на базе [OpenSearch](https://github.com/opensearch-project/OpenSearch), [Langflow](https://github.com/langflow-ai/langflow) и [Docling](https://github.com/docling-project/docling).

---

<div align="center">
  <img src="./docs/static/img/openrag_readme_downsized.gif" alt="Демонстрация OpenRAG" width="100%"/>
</div>

## ✨ Ключевые возможности

- **Упакован и готов к запуску** — Все основные инструменты подключены и готовы к работе: просто установите и запустите
- **Агентные RAG-рабочие процессы** — Расширенная оркестрация с реранжированием и координацией нескольких агентов
- **Приём документов** — Обрабатывает сложные реальные данные с интеллектуальным разбором
- **Конструктор рабочих процессов перетаскиванием** — Визуальный интерфейс на базе Langflow для быстрой итерации
- **Модульные корпоративные дополнения** — Расширяйте функциональность по мере необходимости
- **Корпоративный поиск любого масштаба** — На базе OpenSearch для производительности производственного уровня

## 🔄 Как работает OpenRAG

OpenRAG следует упрощённому рабочему процессу, превращая ваши документы в интеллектуальное и доступное для поиска знание:

<div align="center">
  <img src="./docs/static/img/workflow-diagram.svg" alt="Схема рабочего процесса OpenRAG" width="800"/>
</div>

## 🚀 Установка OpenRAG

Чтобы начать работу с OpenRAG, обратитесь к руководствам по установке в документации OpenRAG:

* [Быстрый старт](https://docs.openr.ag/quickstart)
* [Установка Python-пакета OpenRAG](https://docs.openr.ag/install-options)
* [Развёртывание самостоятельно управляемых сервисов с помощью Docker или Podman](https://docs.openr.ag/docker)

### Локальное развёртывание Docker

Для локального развёртывания Docker Compose одной командой запустите вспомогательный скрипт:

```bash
./start-docker.sh
```

Скрипт подставляет значения по умолчанию для обязательных переменных окружения (пароль OpenSearch, `OPENRAG_ENCRYPTION_KEY`, суперпользователь Langflow), публикует бэкенд по адресу `http://localhost:${OPENRAG_BACKEND_PORT}` (по умолчанию `8001`, если порт `8000` уже занят) через переопределение `docker-compose.backend-port.yml`, а также собирает или пере-тегирует локально собранные образы на основе Debian, которые также работают на старых процессорах без набора инструкций `x86-64-v3`.

## ✨ Рабочий процесс быстрого старта

<div align="center">

<img src="./docs/static/img/uv_run_openrag.png" alt="Запуск openrag с помощью uv run" width="300"/>

**1. Запустите OpenRAG**

↓

<img src="./docs/static/img/add_knowledge_openrag.png" alt="Добавьте файлы или папки как базу знаний" width="300"/>

**2. Добавьте базу знаний**

↓

<img src="./docs/static/img/chat_openrag.png" alt="Начните общение со своей базой знаний" width="700"/>

**3. Начните общение**

</div>

## 📦 SDK

Интегрируйте OpenRAG в свои приложения с помощью официальных SDK:

### Python SDK
```bash
pip install openrag-sdk
```

**Краткий пример:**
```python
import asyncio
from openrag_sdk import OpenRAGClient


async def main():
    async with OpenRAGClient() as client:
        response = await client.chat.create(message="What is RAG?")
        print(response.response)


if __name__ == "__main__":
    asyncio.run(main())
```

📖 [Полная документация Python SDK](https://pypi.org/project/openrag-sdk/)

### TypeScript/JavaScript SDK
```bash
npm install openrag-sdk
```

**Краткий пример:**
```typescript
import { OpenRAGClient } from "openrag-sdk";

const client = new OpenRAGClient();
const response = await client.chat.create({ message: "What is RAG?" });
console.log(response.response);
```

📖 [Полная документация TypeScript/JavaScript SDK](https://www.npmjs.com/package/openrag-sdk)

## 🔌 Протокол контекста модели (MCP)

OpenRAG поставляется со встроенным MCP-сервером на **потоковом HTTP** (streamable HTTP), смонтированным на вашем экземпляре по адресу `/mcp`. Подключайте ИИ-ассистентов, таких как Cursor, Claude Desktop и IBM Bob, к вашей базе знаний OpenRAG — без дополнительного процесса и отдельной установки. Аутентифицируйтесь тем же API-ключом OpenRAG, который вы используете для REST API, передавая его в заголовке `X-API-Key`.

> **Важно:** Отдельный PyPI-пакет `openrag-mcp` устарел. Подключайте свой MCP-клиент напрямую к конечной точке `/mcp`.

**Краткий пример (конфигурация Cursor/Claude Desktop):**
```json
{
  "mcpServers": {
    "openrag": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "X-API-Key": "orag_your_api_key_here"
      }
    }
  }
}
```

MCP-сервер предоставляет инструменты для чата с RAG-усилением, семантического поиска, приёма документов, фильтров знаний и управления настройками.

📖 [Полная документация MCP](https://github.com/langflow-ai/openrag/tree/main/sdks/mcp)

## 🛠️ Разработка

Разработчикам, которые хотят [внести вклад в OpenRAG](https://docs.openr.ag/support/contribute) или настроить среду разработки, следует обратиться к файлу [CONTRIBUTING.md](CONTRIBUTING.md).

## 🛟 Устранение неполадок

За помощью по OpenRAG обратитесь к разделу [Устранение неполадок OpenRAG](https://docs.openr.ag/support/troubleshoot) и посетите страницу [Обсуждения](https://github.com/langflow-ai/openrag/discussions).

Чтобы сообщить об ошибке или отправить запрос на новую возможность, посетите страницу [Issues](https://github.com/langflow-ai/openrag/issues).
