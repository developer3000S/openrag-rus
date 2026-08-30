# OpenRAG MCP

> **Python-пакет `openrag-mcp` устарел и больше не обновляется. Используйте встроенную конечную точку потокового HTTP (streamable HTTP).**

OpenRAG поставляется со встроенным сервером [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) через **потоковый HTTP**, смонтированным на вашем экземпляре OpenRAG по адресу `/mcp`. Эта конечная точка является частью вашего развёртывания OpenRAG; при локальном подключении ничто не покидает вашу сеть.

Любой MCP-клиент, поддерживающий URL-настройки сервера, такой как [Cursor](https://docs.cursor.com/context/model-context-protocol), [Claude Desktop](https://modelcontextprotocol.io/quickstart/user) и MCP SDK, может подключиться напрямую к этой конечной точке.

Нет необходимости запускать дополнительный процесс и ничего устанавливать дополнительно. Ваш клиент подключается по HTTP, используя тот же API-ключ OpenRAG, который вы используете для REST API. Приём документов, отслеживание задач и инструменты фильтров знаний доступны напрямую.

## Предварительные требования

Помимо работающего экземпляра OpenRAG, вам нужен API-ключ OpenRAG и URL конечной точки MCP вашего OpenRAG.

### Аутентификация

Вам нужен API-ключ OpenRAG (с префиксом `orag_`). Вы можете создать API-ключ OpenRAG в **Настройки → API-ключи**.

Передавайте свой API-ключ OpenRAG в каждом запросе с помощью заголовков `X-API-Key` или `Authorization: Bearer`.

Один и тот же ключ работает и для REST API, и для MCP, и прозрачно перенаправляется на нижележащие конечные точки.

### URL конечной точки

Конечная точка MCP находится по адресу `/mcp` на вашем экземпляре OpenRAG. Хост и порт зависят от того, как развёрнут OpenRAG:

| Развёртывание | URL MCP |
|:-----------|:--------|
| Развёртывание Docker по умолчанию | `http://localhost:3000/mcp` |
| Бэкенд, запущенный напрямую (разработка, вне Docker) | `http://localhost:8000/mcp` |
| Удалённый / развёрнутый экземпляр | `https://your-openrag-instance.com/mcp` |

В развёртывании Docker по умолчанию порт бэкенда (`8000`) не публикуется на хост. Фронтенд OpenRAG на порту `3000` проксирует `/mcp` на бэкенд и перенаправляет ваши заголовки аутентификации. Поэтому **`http://localhost:3000/mcp`** — правильный локальный URL для стандартной установки.

Используйте `http://localhost:8000/mcp` только тогда, когда вы запускаете бэкенд напрямую без фронтенда.

Следующие примеры используют локальный URL Docker; замените этот URL на собственный хост, если вам нужно подключиться к удалённому экземпляру.

## Cursor

Файл конфигурации: `~/.cursor/mcp.json`

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

Перезапустите Cursor после сохранения файла конфигурации.

## Claude Desktop

Файл конфигурации:

* macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
* Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

Перезапустите Claude Desktop после изменения файла конфигурации.

## IBM Bob

Добавьте сервер в конфигурацию MCP IBM Bob, установив `type` в `streamable-http`:

```json
{
  "mcpServers": {
    "openrag": {
      "type": "streamable-http",
      "url": "http://localhost:3000/mcp",
      "headers": {
        "x-api-key": "orag_your_api_key_here"
      }
    }
  }
}
```

Дополнительные сведения см. в разделе [Интеграция MCP с IBM Bob](https://www.ibm.com/think/tutorials/mcp-integration-ibm-bob).

## Доступные инструменты

Все инструменты автоматически предоставляются из API `/v1/` и доступны сразу после подключения:

| Инструмент | Описание |
| ---- | ----------- |
| `openrag_chat` | Отправить сообщение и получить ответ с RAG-усилением. Поддерживает `chat_id` и `filter_id`. |
| `openrag_list_chats` | Список всех чат-бесед. |
| `openrag_get_chat` | Получить конкретную чат-беседу по ID. |
| `openrag_delete_chat` | Удалить чат-беседу по ID. |
| `openrag_search` | Семантический поиск по базе знаний. Поддерживает фильтры, порог оценки, источники данных. |
| `openrag_ingest` | Принять документы (файлы, URL, текст) в базу знаний. Возвращает `task_id`. |
| `openrag_get_task_status` | Проверить статус задачи приёма по `task_id`. |
| `openrag_delete_document` | Удалить документ из базы знаний по имени файла. |
| `openrag_get_settings` | Получить текущую конфигурацию OpenRAG (LLM, встраивания, настройки фрагментации, системный промпт). |
| `openrag_update_settings` | Обновить конфигурацию OpenRAG. Все поля необязательны. |
| `openrag_list_models` | Список доступных моделей для провайдера (`openai`, `ollama`, `omniroute`). |
| `openrag_create_knowledge_filter` | Создать фильтр знаний для ограничения поиска и чатов. |
| `openrag_search_knowledge_filters` | Поиск фильтров знаний по имени или критериям. |
| `openrag_get_knowledge_filter` | Получить фильтр знаний по ID. |
| `openrag_update_knowledge_filter` | Обновить существующий фильтр знаний. |
| `openrag_delete_knowledge_filter` | Удалить фильтр знаний по ID. |

## Лицензия

Apache 2.0 — подробности см. в [LICENSE](../../LICENSE).
