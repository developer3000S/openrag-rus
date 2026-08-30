---
name: openrag_sdk
description: Помощь разработчикам в интеграции SDK OpenRAG в приложения с примерами кода, конфигурацией и лучшими практиками
---

Когда пользователь просит интегрировать SDK OpenRAG или использовать OpenRAG в своём приложении, следуйте этому рабочему процессу.

## Этап первоначальной оценки
Перед началом интеграции SDK:
1. Определите экземпляр OpenRAG:
   - Определите базовый URL (например, `http://localhost:3000`, `https://api.example.com`)
   - Проверьте, требуется ли аутентификация (API-ключ)
   - Проверьте доступность API: `curl <base_url>` или `curl <base_url>/health`
2. Определите целевое приложение:
   - Язык программирования (Python, JavaScript/TypeScript)
   - Фреймворк (если есть): FastAPI, Flask, Express, React, Next.js и т. д.
   - Структуру проекта и существующие зависимости
3. Определите требования к интеграции:
   - Функциональность RAG-чата (потоковая или без потоковой передачи)
   - Семантический поиск
   - Приём и управление документами
   - Фильтры знаний
   - Управление историей бесед
   - Управление настройками

## Основные цели
- Установить соответствующий пакет SDK для целевого языка
- Настроить аутентификацию и параметры подключения
- Реализовать основные функции с работающими примерами кода
- Добавить надлежащую обработку ошибок
- Протестировать интеграцию локально
- Задокументировать интеграцию для удобства сопровождения

## Установка SDK

### Python SDK
**Пакет:** [`openrag-sdk`](https://pypi.org/project/openrag-sdk/)

Установка:
```bash
pip install openrag-sdk
```

Или с помощью uv:
```bash
uv add openrag-sdk
```

### TypeScript/JavaScript SDK
**Пакет:** [`openrag-sdk`](https://libraries.io/npm/openrag-sdk)

Установка:
```bash
npm install openrag-sdk
```

Или с помощью других менеджеров пакетов:
```bash
yarn add openrag-sdk
pnpm add openrag-sdk
bun add openrag-sdk
```

### MCP-сервер
**Пакет:** [`openrag-mcp`](https://pypi.org/project/openrag-mcp/)

Для интеграции MCP (Model Context Protocol):
```bash
pip install openrag-mcp
```

Или с помощью uvx:
```bash
uvx openrag-mcp
```

## Конфигурация

### Конфигурация Python SDK
SDK можно настроить через переменные окружения или аргументы конструктора:

**Переменные окружения:**
```bash
OPENRAG_API_KEY=your-api-key  # Обязательно, если включена аутентификация
OPENRAG_URL=http://localhost:3000  # Необязательно, по умолчанию localhost:3000
```

**Аргументы конструктора:**
```python
from openrag_sdk import OpenRAGClient

# Использование переменных окружения (автоматически находит OPENRAG_API_KEY и OPENRAG_URL)
client = OpenRAGClient()

# Использование явных аргументов
client = OpenRAGClient(
    api_key="orag_...",
    base_url="https://api.example.com"
)
```

### Конфигурация TypeScript SDK
Аналогичные варианты конфигурации для TypeScript:

```typescript
import { OpenRAGClient } from 'openrag-sdk';

// Использование переменных окружения
const client = new OpenRAGClient();

// Использование явной конфигурации
const client = new OpenRAGClient({
  apiKey: 'orag_...',
  baseUrl: 'https://api.example.com'
});
```

## Примеры основных функций

### 1. Чат (без потоковой передачи)

**Python:**
```python
import asyncio
from openrag_sdk import OpenRAGClient

async def main():
    # Client auto-discovers OPENRAG_API_KEY and OPENRAG_URL from environment
    async with OpenRAGClient() as client:
        # Simple chat
        response = await client.chat.create(message="What is RAG?")
        print(response.response)
        print(f"Chat ID: {response.chat_id}")
        
        # Continue conversation
        followup = await client.chat.create(
            message="Tell me more",
            chat_id=response.chat_id
        )
        print(followup.response)

asyncio.run(main())
```

**TypeScript:**
```typescript
import { OpenRAGClient } from 'openrag-sdk';

async function main() {
  const client = new OpenRAGClient();
  
  // Simple chat
  const response = await client.chat.create({
    message: "What is RAG?"
  });
  console.log(response.response);
  console.log(`Chat ID: ${response.chatId}`);
  
  // Continue conversation
  const followup = await client.chat.create({
    message: "Tell me more",
    chatId: response.chatId
  });
  console.log(followup.response);
}

main();
```

### 2. Чат (потоковая передача)

**Python:**
```python
async def streaming_chat():
    chat_id = None
    async with OpenRAGClient() as client:
        # Stream responses
        async for event in await client.chat.create(
            message="Explain RAG", 
            stream=True
        ):
            if event.type == "content":
                print(event.delta, end="", flush=True)
            elif event.type == "sources":
                for source in event.sources:
                    print(f"\nSource: {source.filename}")
            elif event.type == "done":
                chat_id = event.chat_id

asyncio.run(streaming_chat())
```

**Python с контекстным менеджером stream():**
```python
async def streaming_with_context():
    async with OpenRAGClient() as client:
        # Full event iteration
        async with client.chat.stream(message="Explain RAG") as stream:
            async for event in stream:
                if event.type == "content":
                    print(event.delta, end="", flush=True)
        
        # Access aggregated data after iteration
        print(f"\nChat ID: {stream.chat_id}")
        
        # Get final text directly
        async with client.chat.stream(message="Explain RAG") as stream:
            text = await stream.final_text()
            print(text)

asyncio.run(streaming_with_context())
```

**TypeScript:**
```typescript
async function streamingChat() {
  const client = new OpenRAGClient();
  
  const stream = await client.chat.create({
    message: "Explain RAG",
    stream: true
  });
  
  for await (const event of stream) {
    if (event.type === 'content') {
      process.stdout.write(event.delta);
    } else if (event.type === 'sources') {
      for (const source of event.sources) {
        console.log(`\nSource: ${source.filename}`);
      }
    } else if (event.type === 'done') {
      console.log(`\nChat ID: ${event.chatId}`);
    }
  }
}
```

### 3. История бесед

**Python:**
```python
async def manage_conversations():
    async with OpenRAGClient() as client:
        # List all conversations
        conversations = await client.chat.list()
        for conv in conversations.conversations:
            print(f"{conv.chat_id}: {conv.title}")
        
        if not conversations.conversations:
            print("No conversations found")
            return
        
        chat_id = conversations.conversations[0].chat_id
        
        # Get specific conversation with messages
        conversation = await client.chat.get(chat_id)
        for msg in conversation.messages:
            print(f"{msg.role}: {msg.content}")
        
        # Delete conversation
        await client.chat.delete(chat_id)

asyncio.run(manage_conversations())
```

**TypeScript:**
```typescript
async function manageConversations() {
  const client = new OpenRAGClient();
  
  // List all conversations
  const conversations = await client.chat.list();
  for (const conv of conversations.conversations) {
    console.log(`${conv.chatId}: ${conv.title}`);
  }
  
  if (!conversations.conversations.length) {
    console.log("No conversations found");
    return;
  }
  
  const chatId = conversations.conversations[0].chatId;
  
  // Get specific conversation
  const conversation = await client.chat.get(chatId);
  for (const msg of conversation.messages) {
    console.log(`${msg.role}: ${msg.content}`);
  }
  
  // Delete conversation
  await client.chat.delete(chatId);
}
```

### 4. Поиск

**Python:**
```python
async def search_knowledge():
    async with OpenRAGClient() as client:
        # Basic search
        results = await client.search.query("document processing")
        for result in results.results:
            print(f"{result.filename} (score: {result.score})")
            print(f"{result.text[:100]}...")
        
        # Search with filters
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

asyncio.run(search_knowledge())
```

**TypeScript:**
```typescript
async function searchKnowledge() {
  const client = new OpenRAGClient();
  
  // Basic search
  const results = await client.search.query("document processing");
  
  for (const result of results.results) {
    console.log(`${result.filename} (score: ${result.score})`);
    console.log(`${result.text.substring(0, 100)}...`);
  }
  
  // Search with filters
  const filtered = await client.search.query("API documentation", {
    filters: {
      data_sources: ["api-docs.pdf"],
      document_types: ["application/pdf"]
    },
    limit: 5,
    scoreThreshold: 0.5
  });
}
```

### 5. Управление документами

**Python:**
```python
async def manage_documents():
    async with OpenRAGClient() as client:
        # Ingest a file (waits for completion by default)
        result = await client.documents.ingest(file_path="./report.pdf")
        print(f"Status: {result.status}")
        
        # Ingest from file object
        with open("./report.pdf", "rb") as f:
            result = await client.documents.ingest(file=f, filename="report.pdf")
        
        # Poll for completion manually
        final_status = await client.documents.wait_for_task(result.task_id)
        print(f"Status: {final_status.status}")
        print(f"Successful files: {final_status.successful_files}")
        
        # Delete a document
        result = await client.documents.delete("report.pdf")
        print(f"Success: {result.success}")

asyncio.run(manage_documents())
```

**TypeScript:**
```typescript
async function manageDocuments() {
  const client = new OpenRAGClient();
  
  // Ingest a file
  const result = await client.documents.ingest({
    filePath: "./report.pdf"
  });
  console.log(`Status: ${result.status}`);
  
  // Poll for completion
  const finalStatus = await client.documents.waitForTask(result.task_id);
  console.log(`Status: ${finalStatus.status}`);
  console.log(`Successful files: ${finalStatus.successful_files}`);
  
  // Delete a document
  const deleteResult = await client.documents.delete("report.pdf");
  console.log(`Success: ${deleteResult.success}`);
}
```

### 6. Управление настройками

**Python:**
```python
async def manage_settings():
    async with OpenRAGClient() as client:
        # Get settings
        settings = await client.settings.get()
        print(f"LLM Provider: {settings.agent.llm_provider}")
        print(f"LLM Model: {settings.agent.llm_model}")
        print(f"Embedding Model: {settings.knowledge.embedding_model}")
        
        # Update settings
        await client.settings.update({
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small"
        })

asyncio.run(manage_settings())
```

**TypeScript:**
```typescript
async function manageSettings() {
  const client = new OpenRAGClient();
  
  // Get settings
  const settings = await client.settings.get();
  console.log(`LLM Provider: ${settings.agent.llmProvider}`);
  console.log(`LLM Model: ${settings.agent.llmModel}`);
  
  // Update settings
  await client.settings.update({
    llm_provider: "openai",
    llm_model: "gpt-4o-mini",
    embedding_provider: "openai",
    embedding_model: "text-embedding-3-small"
  });
}
```

### 7. Фильтры знаний

**Python:**
```python
async def use_knowledge_filters():
    async with OpenRAGClient() as client:
        # Create a knowledge filter
        result = await client.knowledge_filters.create({
            "name": "Technical Docs",
            "description": "Filter for technical documentation",
            "queryData": {
                "query": "technical",
                "filters": {
                    "document_types": ["application/pdf"]
                },
                "limit": 10,
                "scoreThreshold": 0.5
            }
        })
        filter_id = result.id
        
        # Search for filters
        filters = await client.knowledge_filters.search("Technical")
        for f in filters:
            print(f"{f.name}: {f.description}")
        
        # Update a filter
        await client.knowledge_filters.update(filter_id, {
            "description": "Updated description"
        })
        
        # Delete a filter
        await client.knowledge_filters.delete(filter_id)
        
        # Use filter in chat
        response = await client.chat.create(
            message="Explain the API",
            filter_id=filter_id
        )
        
        # Use filter in search
        results = await client.search.query(
            "API endpoints",
            filter_id=filter_id
        )

asyncio.run(use_knowledge_filters())
```

**TypeScript:**
```typescript
async function useKnowledgeFilters() {
  const client = new OpenRAGClient();
  
  // Create a knowledge filter
  const result = await client.knowledgeFilters.create({
    name: "Technical Docs",
    description: "Filter for technical documentation",
    queryData: {
      query: "technical",
      filters: {
        documentTypes: ["application/pdf"]
      },
      limit: 10,
      scoreThreshold: 0.5
    }
  });
  const filterId = result.id;
  
  // Use filter in chat
  const response = await client.chat.create({
    message: "Explain the API",
    filterId: filterId
  });
  
  // Use filter in search
  const results = await client.search.query({
    query: "API endpoints",
    filterId: filterId
  });
}
```

## Обработка ошибок

### Обработка ошибок в Python
```python
from openrag_sdk import (
    OpenRAGError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError
)

async def handle_errors():
    try:
        async with OpenRAGClient() as client:
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
        print(f"Server error: {e.message} (status: {e.status_code})")
    except OpenRAGError as e:
        print(f"API error: {e.message} (status: {e.status_code})")
```

### Обработка ошибок в TypeScript
```typescript
import {
  OpenRAGClient,
  OpenRAGError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  ServerError
} from 'openrag-sdk';

async function handleErrors() {
  try {
    const client = new OpenRAGClient();
    const response = await client.chat.create({ message: "Hello" });
  } catch (error) {
    if (error instanceof AuthenticationError) {
      console.error(`Invalid API key: ${error.message}`);
    } else if (error instanceof NotFoundError) {
      console.error(`Resource not found: ${error.message}`);
    } else if (error instanceof ValidationError) {
      console.error(`Invalid request: ${error.message}`);
    } else if (error instanceof RateLimitError) {
      console.error(`Rate limited: ${error.message}`);
    } else if (error instanceof ServerError) {
      console.error(`Server error: ${error.message}`);
    } else if (error instanceof OpenRAGError) {
      console.error(`API error: ${error.message}`);
    }
  }
}
```

## Паттерны интеграции

### Паттерн 1: бэкенд FastAPI
```python
from fastapi import FastAPI, HTTPException
from openrag_sdk import OpenRAGClient
from pydantic import BaseModel

app = FastAPI()
client = OpenRAGClient()

class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        response = await client.chat.create(
            message=request.message,
            chat_id=request.chat_id
        )
        return {
            "answer": response.response,
            "sources": [{"filename": s.filename, "score": s.score} for s in response.sources],
            "chat_id": response.chat_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search(query: str, limit: int = 10):
    try:
        results = await client.search.query(query, limit=limit)
        return {
            "results": [
                {
                    "filename": r.filename,
                    "text": r.text,
                    "score": r.score
                }
                for r in results.results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Паттерн 2: бэкенд Express.js
```typescript
import express from 'express';
import { OpenRAGClient } from 'openrag-sdk';

const app = express();
const client = new OpenRAGClient();

app.use(express.json());

app.post('/api/chat', async (req, res) => {
  try {
    const { message, chatId } = req.body;
    const response = await client.chat.create({
      message,
      chatId
    });
    
    res.json({
      answer: response.response,
      sources: response.sources.map(s => ({
        filename: s.filename,
        score: s.score
      })),
      chatId: response.chatId
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/search', async (req, res) => {
  try {
    const { query, limit = 10 } = req.query;
    const results = await client.search.query({
      query: query as string,
      limit: Number(limit)
    });
    
    res.json({
      results: results.results.map(r => ({
        filename: r.filename,
        text: r.text,
        score: r.score
      }))
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3001, () => {
  console.log('Server running on port 3001');
});
```

### Паттерн 3: фронтенд React
```typescript
import { useState } from 'react';
import { OpenRAGClient } from 'openrag-sdk';

// Note: In production, proxy API calls through your backend
// to avoid exposing API keys in the browser
const client = new OpenRAGClient({
  baseUrl: process.env.REACT_APP_OPENRAG_URL
});

function ChatComponent() {
  const [message, setMessage] = useState('');
  const [chatId, setChatId] = useState<string | null>(null);
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const result = await client.chat.create({
        message,
        chatId,
        limit: 5
      });
      
      setResponse(result.response);
      setChatId(result.chatId);
      setMessage('');
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
      {response && (
        <div className="response">
          {response}
        </div>
      )}
    </div>
  );
}
```

### Паттерн 4: потоковая передача в React
```typescript
import { useState } from 'react';
import { OpenRAGClient } from 'openrag-sdk';

function StreamingChat() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [streaming, setStreaming] = useState(false);
  const client = new OpenRAGClient();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStreaming(true);
    setResponse('');
    
    try {
      const stream = await client.chat.create({
        message,
        stream: true
      });
      
      for await (const event of stream) {
        if (event.type === 'content') {
          setResponse(prev => prev + event.delta);
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
    } finally {
      setStreaming(false);
      setMessage('');
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={streaming}
        />
        <button type="submit" disabled={streaming}>
          {streaming ? 'Streaming...' : 'Send'}
        </button>
      </form>
      <div className="response">
        {response}
        {streaming && <span className="cursor">▊</span>}
      </div>
    </div>
  );
}
```

## Лучшие практики безопасности

1. **Никогда не раскрывайте API-ключи в клиентском коде**
   - Всегда проксируйте запросы через свой бэкенд
   - Используйте переменные окружения для API-ключей
   - Реализуйте надлежащую аутентификацию в своём бэкенде

2. **Используйте HTTPS в производстве**
   - Всегда используйте HTTPS для производственных развёртываний
   - Настраивайте корректные сертификаты SSL/TLS

3. **Проверяйте и санируйте входные данные**
   - Проверяйте пользовательский ввод перед отправкой в OpenRAG
   - Санируйте вывод перед отображением пользователям
   - Реализуйте ограничение скорости (rate limiting) на своих конечных точках

4. **Реализуйте надлежащую обработку ошибок**
   - Не раскрывайте конфиденциальную информацию в сообщениях об ошибках
   - Безопасно регистрируйте ошибки для отладки
   - Предоставляйте понятные пользователю сообщения об ошибках

5. **Следуйте рекомендациям OWASP**
   - Реализуйте надлежащую аутентификацию и авторизацию
   - Защищайтесь от распространённых уязвимостей (XSS, CSRF и т. д.)
   - Поддерживайте зависимости в актуальном состоянии

## Стратегии тестирования

### Тестирование в Python
```python
import pytest
from openrag_sdk import OpenRAGClient

@pytest.fixture
async def client():
    async with OpenRAGClient() as client:
        yield client

@pytest.mark.asyncio
async def test_chat_basic(client):
    response = await client.chat.create(message="Hello")
    assert response.response is not None
    assert isinstance(response.sources, list)
    assert response.chat_id is not None

@pytest.mark.asyncio
async def test_search_with_filters(client):
    results = await client.search.query(
        "test",
        filters={"document_types": ["application/pdf"]}
    )
    assert isinstance(results.results, list)
```

### Тестирование в TypeScript
```typescript
import { describe, it, expect } from 'vitest';
import { OpenRAGClient } from 'openrag-sdk';

describe('OpenRAG SDK', () => {
  const client = new OpenRAGClient();

  it('should chat successfully', async () => {
    const response = await client.chat.create({
      message: 'Hello'
    });
    
    expect(response.response).toBeDefined();
    expect(response.sources).toBeInstanceOf(Array);
    expect(response.chatId).toBeDefined();
  });

  it('should search with filters', async () => {
    const results = await client.search.query({
      query: 'test',
      filters: {
        documentTypes: ['application/pdf']
      }
    });
    
    expect(results.results).toBeInstanceOf(Array);
  });
});
```

## Устранение неполадок

### Проблемы с подключением
- Проверьте правильность базового URL (например, `http://localhost:3000` или `https://api.example.com`)
- Проверьте связь: `curl <base_url>` или `curl <base_url>/health`
- Проверьте сетевую связность, если OpenRAG находится на удалённом сервере
- Убедитесь, что брандмауэр или сетевые политики не блокируют соединение
- Проверьте разрешение DNS при использовании доменного имени

### Ошибки аутентификации
- Проверьте правильность API-ключа, если включена аутентификация
- Проверьте, что API-ключ правильно задан в переменных окружения
- Убедитесь, что API-ключ имеет необходимые разрешения

### Оптимизация производительности
- Используйте подходящие значения `limit` (не запрашивайте источников больше, чем нужно)
- Задавайте разумный `score_threshold` для фильтрации низкокачественных результатов
- Реализуйте кэширование для часто задаваемых вопросов
- Используйте пул соединений для приложений с высокой нагрузкой
- Рассмотрите использование потоковой передачи для лучшего пользовательского опыта

### Проблемы с качеством ответов
- Настраивайте `score_threshold` для фильтрации нерелевантных результатов
- Просматривайте и обновляйте системный промпт для лучших ответов
- Убедитесь, что база знаний содержит релевантные документы
- Рассмотрите использование фильтров знаний для доменно-специфичных запросов

## Соображения о развёртывании

1. **Конфигурация окружения**
   - Используйте разные конфигурации для dev/staging/prod
   - Храните конфиденциальные данные в переменных окружения или менеджере секретов
   - Используйте файлы конфигурации для нечувствительных настроек

2. **Проверки работоспособности**
   - Реализуйте конечные точки проверки работоспособности в своём приложении
   - Отслеживайте доступность сервиса OpenRAG
   - Настройте оповещения о сбоях

3. **Мониторинг и журналирование**
   - Добавьте журналирование вызовов SDK
   - Отслеживайте метрики (время ответа, уровень ошибок и т. д.)
   - Используйте структурированное журналирование для лучшего анализа

4. **Обработка отката**
   - Реализуйте корректную деградацию, если OpenRAG недоступен
   - Предоставляйте кэшированные ответы, когда это возможно
   - Показывайте пользователям соответствующие сообщения об ошибках

5. **Масштабирование**
   - Рассмотрите балансировку нагрузки для сценариев с высокой нагрузкой
   - Реализуйте постановку запросов в очередь при необходимости
   - Отслеживайте использование ресурсов и масштабируйтесь соответственно

## Требования к документации

После интеграции задокументируйте:
- Шаги настройки и конфигурации SDK
- Доступные конечные точки и их использование
- Примеры запросов и ответов
- Коды ошибок и стратегии обработки
- Характеристики производительности и ограничения
- Процедуры обслуживания и устранение неполадок

## Контрольный список проверки

Перед тем как считать интеграцию завершённой:
- [ ] Пакет SDK успешно установлен
- [ ] Клиент успешно подключается к OpenRAG
- [ ] Функциональность чата работает (и потоковая, и без потоковой передачи)
- [ ] Поиск возвращает релевантные результаты
- [ ] Приём документов работает
- [ ] Настройки можно получать и обновлять
- [ ] Фильтры знаний можно создавать и использовать
- [ ] Обработка ошибок реализована
- [ ] Тесты проходят
- [ ] Документация полная
- [ ] Лучшие практики безопасности соблюдены
- [ ] Производительность приемлема для сценария использования

## Дополнительные ресурсы

- **Python SDK:** https://pypi.org/project/openrag-sdk/
- **TypeScript SDK:** https://libraries.io/npm/openrag-sdk
- **MCP-сервер:** https://pypi.org/project/openrag-mcp/
- **Репозиторий GitHub:** https://github.com/langflow-ai/openrag/tree/main/sdks
- **Официальная документация:** https://docs.openr.ag

## Стиль совместной работы

- Предоставляйте работающие примеры кода на основе официальной документации SDK
- Тестируйте шаги интеграции перед их представлением
- Объясняйте компромиссы между разными подходами
- Выявляйте потенциальные проблемы заранее (производительность, безопасность и т. д.)
- Держите примеры сфокусированными на основных функциях
- Предоставляйте как минимальные, так и готовые к производству примеры
- Явно указывайте, что требует запущенного OpenRAG
- Ссылайтесь на официальные репозитории пакетов для установки
