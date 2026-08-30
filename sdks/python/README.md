# Python SDK OpenRAG

Официальный Python SDK для API [OpenRAG](https://openr.ag).

## Установка

```bash
pip install openrag-sdk
```

## Быстрый старт

```python
import asyncio
from openrag_sdk import OpenRAGClient

async def main():
    # Клиент автоматически находит OPENRAG_API_KEY и OPENRAG_URL из окружения
    async with OpenRAGClient() as client:
        # Простой чат
        response = await client.chat.create(message="What is RAG?")
        print(response.response)
        print(f"Chat ID: {response.chat_id}")

asyncio.run(main())
```

## Конфигурация

SDK можно настроить через переменные окружения или аргументы конструктора:

| Переменная окружения | Аргумент конструктора | Описание |
|---------------------|---------------------|-------------|
| `OPENRAG_API_KEY` | `api_key` | API-ключ для аутентификации (обязательный) |
| `OPENRAG_URL` | `base_url` | Базовый URL фронтенда OpenRAG (по умолчанию: `http://localhost:3000`) |

```python
# Использование переменных окружения
client = OpenRAGClient()

# Использование явных аргументов
client = OpenRAGClient(
    api_key="orag_...",
    base_url="https://api.example.com"
)
```

## Чат

### Без потоковой передачи

```python
response = await client.chat.create(message="What is RAG?")
print(response.response)
print(f"Chat ID: {response.chat_id}")

# Продолжение беседы
followup = await client.chat.create(
    message="Tell me more",
    chat_id=response.chat_id
)
```

### Потоковая передача с `create(stream=True)`

Возвращает асинхронный итератор напрямую:

```python
chat_id = None
async for event in await client.chat.create(message="Explain RAG", stream=True):
    if event.type == "content":
        print(event.delta, end="", flush=True)
    elif event.type == "sources":
        for source in event.sources:
            page_info = f" (page {source.page})" if source.page else ""
            print(f"\nSource: {source.filename}{page_info}")
    elif event.type == "done":
        chat_id = event.chat_id
```

### Потоковая передача с контекстным менеджером `stream()`

Предоставляет дополнительные помощники для удобства:

```python
# Полный перебор событий
async with client.chat.stream(message="Explain RAG") as stream:
    async for event in stream:
        if event.type == "content":
            print(event.delta, end="", flush=True)

    # Доступ к агрегированным данным после перебора
    print(f"\nChat ID: {stream.chat_id}")
    print(f"Full text: {stream.text}")
    print(f"Sources: {stream.sources}")

# Только текстовые фрагменты
async with client.chat.stream(message="Explain RAG") as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)

# Получить итоговый текст напрямую
async with client.chat.stream(message="Explain RAG") as stream:
    text = await stream.final_text()
    print(text)
```

### История бесед

```python
# Список всех бесед
conversations = await client.chat.list()
for conv in conversations.conversations:
    print(f"{conv.chat_id}: {conv.title}")

# Получение конкретной беседы с сообщениями
conversation = await client.chat.get(chat_id)
for msg in conversation.messages:
    print(f"{msg.role}: {msg.content}")

# Удаление беседы
await client.chat.delete(chat_id)
```

## Поиск

```python
# Базовый поиск
results = await client.search.query("document processing")
for result in results.results:
    print(f"{result.filename} (score: {result.score})")
    print(f"  {result.text[:100]}...")

# Поиск с фильтрами
from openrag_sdk import SearchFilters

results = await client.search.query(
    "API documentation",
    filters=SearchFilters(
        data_sources=["api-docs.pdf"],
        document_types=["application/pdf"]
    ),
    limit=5,
    score_threshold=0.5
)
```

## Документы

```python
# Приём файла (по умолчанию ожидает завершения)
result = await client.documents.ingest(file_path="./report.pdf")
print(f"Status: {result.status}")
print(f"Successful files: {result.successful_files}")

# Приём без ожидания (возвращается немедленно с task_id)
result = await client.documents.ingest(file_path="./report.pdf", wait=False)
print(f"Task ID: {result.task_id}")

# Ручной опрос до завершения
final_status = await client.documents.wait_for_task(result.task_id)
print(f"Status: {final_status.status}")
print(f"Successful files: {final_status.successful_files}")

# Приём из файлового объекта
with open("./report.pdf", "rb") as f:
    result = await client.documents.ingest(file=f, filename="report.pdf")

# Удаление документа
result = await client.documents.delete("report.pdf")
print(f"Success: {result.success}")
```

## Список файлов

`client.documents.list_files()` инвентаризирует всё содержимое базы знаний и
возвращает метаданные, необходимые для управления фильтрами знаний и поиском.

```python
import json

# Список первой страницы файлов
page = await client.documents.list_files(page_size=50)
for f in page.files:
    print(f"{f.filename}  ({f.mimetype}, {f.chunk_count} chunks)")

# Курсорная постраничная навигация по всем файлам
after_key = None
while True:
    page = await client.documents.list_files(page_size=100, after_key=after_key)
    for f in page.files:
        print(f.filename)
    if page.after_key is None:
        break
    after_key = json.dumps(page.after_key)

# Фильтрация и сортировка
page = await client.documents.list_files(
    connector_type="sharepoint",
    sort_by="indexed_time",
    sort_order="desc",
)

# Рабочий процесс «список → создание фильтра знаний»
page = await client.documents.list_files(connector_type="sharepoint")
filenames = [f.filename for f in page.files]
result = await client.knowledge_filters.create({
    "name": "SharePoint docs",
    "queryData": {"filters": {"data_sources": filenames}},
})
filter_id = result.id

# Использование фильтра в поиске и чате
results = await client.search.query("quarterly report", filter_id=filter_id)
response = await client.chat.create(message="Summarise Q3", filter_id=filter_id)
```

Для разового получения списка без управления курсором `client.documents.get_all_files()`
возвращает все файлы одним вызовом — параметры не требуются.

> **Примечание:** `get_all_files()` возвращает не более **500 файлов**. Если ваша база
> знаний содержит более 500 файлов, используйте `list_files()` с курсорной пагинацией
> (`after_key`), чтобы пролистать полный набор.

```python
# Получить все файлы одним вызовом (не нужно отслеживать курсор)
page = await client.documents.get_all_files()
for f in page.files:
    print(f.filename)
```

## Настройки

```python
# Получить настройки
settings = await client.settings.get()
print(f"LLM Provider: {settings.agent.llm_provider}")
print(f"LLM Model: {settings.agent.llm_model}")
print(f"Embedding Model: {settings.knowledge.embedding_model}")

# Обновить настройки
await client.settings.update({
    "chunk_size": 1000,
    "chunk_overlap": 200,
})
```

## Фильтры знаний

Фильтры знаний — это многократно используемые именованные конфигурации фильтров, которые можно применять к операциям чата и поиска.

```python
# Создать фильтр знаний
result = await client.knowledge_filters.create({
    "name": "Technical Docs",
    "description": "Filter for technical documentation",
    "queryData": {
        "query": "technical",
        "filters": {
            "document_types": ["application/pdf"],
        },
        "limit": 10,
        "scoreThreshold": 0.5,
    },
})
filter_id = result.id

# Поиск фильтров
filters = await client.knowledge_filters.search("Technical")
for f in filters:
    print(f"{f.name}: {f.description}")

# Получить конкретный фильтр
filter_obj = await client.knowledge_filters.get(filter_id)

# Обновить фильтр
await client.knowledge_filters.update(filter_id, {
    "description": "Updated description",
})

# Удалить фильтр
await client.knowledge_filters.delete(filter_id)

# Использовать фильтр в чате
response = await client.chat.create(
    message="Explain the API",
    filter_id=filter_id,
)

# Использовать фильтр в поиске
results = await client.search.query("API endpoints", filter_id=filter_id)
```

## Обработка ошибок

```python
from openrag_sdk import (
    OpenRAGError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
)

try:
    response = await client.chat.create(message="Hello")
except AuthenticationError as e:
    print(f"Invalid API key: {e.message}")
except NotFoundError as e:
    print(f"Resource not found: {e.message}")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
except ServerError as e:
    print(f"Server error: {e.message}")
except OpenRAGError as e:
    print(f"API error: {e.message} (status: {e.status_code})")
```

## Лицензия

MIT
