# TypeScript SDK OpenRAG

Официальный TypeScript/JavaScript SDK для API [OpenRAG](https://openr.ag).

## Установка

```bash
npm install openrag-sdk
# или
yarn add openrag-sdk
# или
pnpm add openrag-sdk
```

## Быстрый старт

```typescript
import { OpenRAGClient } from "openrag-sdk";

// Клиент автоматически находит OPENRAG_API_KEY и OPENRAG_URL из окружения
const client = new OpenRAGClient();

// Простой чат
const response = await client.chat.create({ message: "What is RAG?" });
console.log(response.response);
console.log(`Chat ID: ${response.chatId}`);
```

## Конфигурация

SDK можно настроить через переменные окружения или аргументы конструктора:

| Переменная окружения | Вариант конструктора | Описание |
|---------------------|-------------------|-------------|
| `OPENRAG_API_KEY` | `apiKey` | API-ключ для аутентификации (обязательный) |
| `OPENRAG_URL` | `baseUrl` | Базовый URL фронтенда OpenRAG (по умолчанию: `http://localhost:3000`) |

```typescript
// Использование переменных окружения
const client = new OpenRAGClient();

// Использование явных аргументов
const client = new OpenRAGClient({
  apiKey: "orag_...",
  baseUrl: "https://api.example.com",
});
```

## Чат

### Без потоковой передачи

```typescript
const response = await client.chat.create({ message: "What is RAG?" });
console.log(response.response);
console.log(`Chat ID: ${response.chatId}`);

// Продолжение беседы
const followup = await client.chat.create({
  message: "Tell me more",
  chatId: response.chatId,
});
```

### Потоковая передача с `create({ stream: true })`

Возвращает асинхронный итератор напрямую:

```typescript
let chatId: string | null = null;
for await (const event of await client.chat.create({
  message: "Explain RAG",
  stream: true,
})) {
  if (event.type === "content") {
    process.stdout.write(event.delta);
  } else if (event.type === "sources") {
    for (const source of event.sources) {
      const pageInfo = source.page ? ` (page ${source.page})` : "";
      console.log(`\nSource: ${source.filename}${pageInfo}`);
    }
  } else if (event.type === "done") {
    chatId = event.chatId;
  }
}
```

### Потоковая передача с `stream()`

Предоставляет дополнительные помощники для удобства:

```typescript
// Полный перебор событий
const stream = await client.chat.stream({ message: "Explain RAG" });
try {
  for await (const event of stream) {
    if (event.type === "content") {
      process.stdout.write(event.delta);
    }
  }

  // Доступ к агрегированным данным после перебора
  console.log(`\nChat ID: ${stream.chatId}`);
  console.log(`Full text: ${stream.text}`);
  console.log(`Sources: ${stream.sources}`);
} finally {
  stream.close();
}

// Только текстовые фрагменты
const stream = await client.chat.stream({ message: "Explain RAG" });
try {
  for await (const text of stream.textStream) {
    process.stdout.write(text);
  }
} finally {
  stream.close();
}

// Получить итоговый текст напрямую
const stream = await client.chat.stream({ message: "Explain RAG" });
try {
  const text = await stream.finalText();
  console.log(text);
} finally {
  stream.close();
}
```

### История бесед

```typescript
// Список всех бесед
const conversations = await client.chat.list();
for (const conv of conversations.conversations) {
  console.log(`${conv.chatId}: ${conv.title}`);
}

// Получение конкретной беседы с сообщениями
const conversation = await client.chat.get(chatId);
for (const msg of conversation.messages) {
  console.log(`${msg.role}: ${msg.content}`);
}

// Удаление беседы
await client.chat.delete(chatId);
```

## Поиск

```typescript
// Базовый поиск
const results = await client.search.query("document processing");
for (const result of results.results) {
  console.log(`${result.filename} (score: ${result.score})`);
  console.log(`  ${result.text.slice(0, 100)}...`);
}

// Поиск с фильтрами
const results = await client.search.query("API documentation", {
  filters: {
    data_sources: ["api-docs.pdf"],
    document_types: ["application/pdf"],
  },
  limit: 5,
  scoreThreshold: 0.5,
});
```

## Документы

```typescript
// Приём файла (по умолчанию ожидает завершения)
const result = await client.documents.ingest({
  filePath: "./report.pdf",
});
console.log(`Status: ${result.status}`);
console.log(`Successful files: ${result.successful_files}`);

// Приём без ожидания (возвращается немедленно с task_id)
const result = await client.documents.ingest({
  filePath: "./report.pdf",
  wait: false,
});
console.log(`Task ID: ${result.task_id}`);

// Ручной опрос до завершения
const finalStatus = await client.documents.waitForTask(result.task_id);
console.log(`Status: ${finalStatus.status}`);
console.log(`Successful files: ${finalStatus.successful_files}`);

// Приём из объекта File (браузер)
const file = new File([...], "report.pdf");
const result = await client.documents.ingest({
  file,
  filename: "report.pdf",
});

// Удаление документа
const result = await client.documents.delete("report.pdf");
console.log(`Success: ${result.success}`);
```

## Список файлов

`client.documents.listFiles()` инвентаризирует всё содержимое базы знаний и
возвращает метаданные, необходимые для управления фильтрами знаний и поиском.

```typescript
// Список первой страницы файлов
const firstPage = await client.documents.listFiles({ page_size: 50 });
for (const f of firstPage.files) {
  console.log(`${f.filename}  (${f.mimetype}, ${f.chunk_count} chunks)`);
}

// Курсорная постраничная навигация по всем файлам
let afterKey: string | undefined;
do {
  const page = await client.documents.listFiles({ page_size: 100, after_key: afterKey });
  for (const f of page.files) console.log(f.filename);
  afterKey = page.after_key ? JSON.stringify(page.after_key) : undefined;
} while (afterKey);

// Фильтрация и сортировка
const sortedPage = await client.documents.listFiles({
  connector_type: "sharepoint",
  sort_by: "indexed_time",
  sort_order: "desc",
});

// Рабочий процесс «список → создание фильтра знаний»
const sharepointPage = await client.documents.listFiles({ connector_type: "sharepoint" });
const filenames = sharepointPage.files.map(f => f.filename);
const { id: filterId } = await client.knowledgeFilters.create({
  name: "SharePoint docs",
  queryData: { filters: { data_sources: filenames } },
});

// Использование фильтра в поиске и чате
const results = await client.search.query("quarterly report", { filterId });
const response = await client.chat.create({ message: "Summarise Q3", filterId });
```

Для разового получения списка без управления курсором `client.documents.getAllFiles()`
возвращает все файлы одним вызовом — параметры не требуются.

> **Примечание:** `getAllFiles()` возвращает не более **500 файлов**. Если ваша база
> знаний содержит более 500 файлов, используйте `listFiles()` с курсорной пагинацией
> (`after_key`), чтобы пролистать полный набор.

```typescript
// Получить все файлы одним вызовом (не нужно отслеживать курсор)
const page = await client.documents.getAllFiles();
for (const f of page.files) console.log(f.filename);
```

## Настройки

```typescript
// Получить настройки
const settings = await client.settings.get();
console.log(`LLM Provider: ${settings.agent.llm_provider}`);
console.log(`LLM Model: ${settings.agent.llm_model}`);
console.log(`Embedding Model: ${settings.knowledge.embedding_model}`);

// Обновить настройки
await client.settings.update({
  chunk_size: 1000,
  chunk_overlap: 200,
});
```

## Фильтры знаний

Фильтры знаний — это многократно используемые именованные конфигурации фильтров, которые можно применять к операциям чата и поиска.

```typescript
// Создать фильтр знаний
const result = await client.knowledgeFilters.create({
  name: "Technical Docs",
  description: "Filter for technical documentation",
  queryData: {
    query: "technical",
    filters: {
      document_types: ["application/pdf"],
    },
    limit: 10,
    scoreThreshold: 0.5,
  },
});
const filterId = result.id;

// Поиск фильтров
const filters = await client.knowledgeFilters.search("Technical");
for (const filter of filters) {
  console.log(`${filter.name}: ${filter.description}`);
}

// Получить конкретный фильтр
const filter = await client.knowledgeFilters.get(filterId);

// Обновить фильтр
await client.knowledgeFilters.update(filterId, {
  description: "Updated description",
});

// Удалить фильтр
await client.knowledgeFilters.delete(filterId);

// Использовать фильтр в чате
const response = await client.chat.create({
  message: "Explain the API",
  filterId,
});

// Использовать фильтр в поиске
const results = await client.search.query("API endpoints", { filterId });
```

## Обработка ошибок

```typescript
import {
  OpenRAGError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  ServerError,
} from "openrag-sdk";

try {
  const response = await client.chat.create({ message: "Hello" });
} catch (e) {
  if (e instanceof AuthenticationError) {
    console.log(`Invalid API key: ${e.message}`);
  } else if (e instanceof NotFoundError) {
    console.log(`Resource not found: ${e.message}`);
  } else if (e instanceof ValidationError) {
    console.log(`Invalid request: ${e.message}`);
  } else if (e instanceof RateLimitError) {
    console.log(`Rate limited: ${e.message}`);
  } else if (e instanceof ServerError) {
    console.log(`Server error: ${e.message}`);
  } else if (e instanceof OpenRAGError) {
    console.log(`API error: ${e.message} (status: ${e.statusCode})`);
  }
}
```

## Поддержка браузеров

Этот SDK работает как в средах Node.js, так и в браузерах. Основное различие — приём файлов:

- **Node.js**: используйте параметр `filePath`
- **Браузер**: используйте параметр `file` с объектом `File` или `Blob`

## TypeScript

Этот SDK написан на TypeScript и предоставляет полные определения типов. Все типы экспортируются из главного модуля:

```typescript
import type {
  ChatResponse,
  StreamEvent,
  SearchResponse,
  IngestResponse,
  SettingsResponse,
} from "openrag-sdk";
```

## Лицензия

MIT
