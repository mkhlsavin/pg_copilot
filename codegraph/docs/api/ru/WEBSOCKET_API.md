# Справочная документация по WebSocket API

В этом документе описывается WebSocket API для работы с CodeGraph в режиме реального времени.

## Содержание

- [Обзор](#overview)
- [Аутентификация](#authentication)
- [Ошибки соединения](#connection-errors)
- [Точки доступа (Endpoints)](#endpoints)
- [Потоковая передача чата](#chat-streaming)
- [Статус задачи](#job-status)
- [Уведомления](#notifications)
- [Типы сообщений](#message-types)
- [Клиент → Сервер](#client-server)
- [Сервер → Клиент](#server-client)
- [Формат сообщений](#message-format)
- [Поддержание соединения (Keep-Alive)](#keep-alive)
- [Обработка ошибок](#error-handling)
- [Формат сообщения об ошибке](#error-message-format)
- [Распространённые ошибки](#common-errors)
- [Пример клиента на Python](#python-client-example)
- [Пример клиента на JavaScript](#javascript-client-example)
- [Ограничения по частоте запросов (Rate Limits)](#rate-limits)
- [См. также](#see-also)

## Обзор {#overview}

WebSocket API предоставляет:
- **Потоковую передачу ответов чата** — потоковую передачу ответов ИИ в реальном времени
- **Обновления хода выполнения задач** — уведомления о состоянии фоновых задач
- **Push-уведомления** — системные оповещения и уведомления

Базовый URL: `ws://localhost:8000/ws/v1`

---

## Аутентификация {#authentication}

Все соединения WebSocket требуют JWT-токен, передаваемый в качестве параметра запроса.

```
ws://localhost:8000/ws/v1/chat?token=<JWT_TOKEN>
```

### Ошибки соединения {#connection-errors}

| Код | Причина | Описание |
| --- | --- | --- |
| 4001 | Недействительный токен | Токен отсутствует, просрочен или недействителен |
| 4003 | Доступ запрещён | У пользователя недостаточно прав |
| 1008 | Нарушение политики | Ошибка политики соединения |

---

## Конечные точки

### Потоковый чат

**Конечная точка:** `ws://localhost:8000/ws/v1/chat`

Общение в реальном времени с потоковой передачей ответов.

#### Подключение

```
const ws = new WebSocket('ws://localhost:8000/ws/v1/chat?token=' + token);

ws.onopen = () => {
  console.log('Подключено к чату');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Получено:', message.type, message.payload);
};

ws.onerror = (error) => {
  console.error('Ошибка WebSocket:', error);
};

ws.onclose = (event) => {
  console.log('Отключено:', event.code, event.reason);
};
```

#### Отправка запроса в чат

```
ws.send(JSON.stringify({
  type: 'chat.query',
  payload: {
    query: 'Найти все уязвимости к SQL-инъекциям',
    session_id: 'необязательный-id-сессии',
    scenario_id: 'необязательный-id-сценария',
    language: 'en'
  },
  request_id: 'уникальный-id-запроса'
}));
```

#### Получение потокового ответа

Сообщения приходят последовательно:

1. **Выбор сценария** (необязательно)

```
{
  "type": "chat.scenario",
  "payload": { "scenario_id": "security_audit" },
  "timestamp": "2025-12-14T10:30:00Z",
  "request_id": "unique-request-id"
}
```

1. **Фрагменты ответа** (несколько)

```
{
  "type": "chat.chunk",
  "payload": { "content": "Найдено 3 потенциальные ", "is_final": false },
  "timestamp": "2025-12-14T10:30:01Z",
  "request_id": "unique-request-id"
}
```

1. **Завершение**

```
{
  "type": "chat.done",
  "payload": {},
  "timestamp": "2025-12-14T10:30:05Z",
  "request_id": "unique-request-id"
}
```

---

### Статус задачи {#job-status}

**Конечная точка:** `ws://localhost:8000/ws/v1/jobs/{job_id}`

Подписка на обновления хода выполнения фоновой задачи.

#### Подключение

```
const jobId = 'abc123';
const ws = new WebSocket(`ws://localhost:8000/ws/v1/jobs/${jobId}?token=${token}`);
```

#### Сообщения {#error-message-format}

**Задача запущена**

```
{
  "type": "job.started",
  "payload": {
    "job_id": "abc123",
    "status": "subscribed"
  },
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Ход выполнения задачи**

```
{
  "type": "job.progress",
  "payload": {
    "job_id": "abc123",
    "status": "running",
    "progress": 45,
    "message": "Обработка файлов..."
  },
  "timestamp": "2025-12-14T10:31:00Z"
}
```

**Задача завершена**

```
{
  "type": "job.completed",
  "payload": {
    "job_id": "abc123",
    "status": "completed",
    "progress": 100,
    "result": {
      "files_processed": 150,
      "vulnerabilities_found": 3
    }
  },
  "timestamp": "2025-12-14T10:35:00Z"
}
```

**Задача завершилась с ошибкой**

```
{
  "type": "job.failed",
  "payload": {
    "job_id": "abc123",
    "status": "failed",
    "error": "Таймаут соединения",
    "details": "Не удалось подключиться к серверу Joern"
  },
  "timestamp": "2025-12-14T10:35:00Z"
}
```

---

### Уведомления {#notifications}

**Конечная точка:** `ws://localhost:8000/ws/v1/notifications`

Получение push-уведомлений о системных событиях.

#### Подключение

```
const ws = new WebSocket('ws://localhost:8000/ws/v1/notifications?token=' + token);
```

#### Сообщения

**Уведомление**

```
{
  "type": "notification",
  "payload": {
    "title": "Импорт завершён",
    "message": "Проект 'myapp' успешно импортирован",
    "level": "success",
    "action_url": "/projects/abc123"
  },
  "timestamp": "2025-12-14T10:35:00Z"
}
```

Уровни уведомлений: `info`, `success`, `warning`, `error`

---

## Типы сообщений {#message-types}

### Клиент → Сервер {#client-server}

| Тип | Описание | Полезная нагрузка |
| --- | --- | --- |
| chat.query | Отправить запрос в чат | query,session_id?,scenario_id?,language? |
| ping | Поддержание соединения | Нет |

### Сервер → Клиент {#server-client}

| Тип | Описание | Полезная нагрузка |
| --- | --- | --- |
| chat.scenario | Выбор сценария | scenario_id |
| chat.chunk | Фрагмент ответа | content,is_final |
| chat.done | Ответ завершён | Нет |
| chat.error | Ошибка чата | error,details? |
| job.started | Задача подписана | job_id,status |
| job.progress | Ход выполнения задачи | job_id,status,progress,message? |
| job.completed | Задача завершена | job_id,result |
| job.failed | Задача не удалась | job_id,error,details? |
| notification | Уведомление | title,message,level,action_url? |
| error | Общая ошибка | error,details? |
| pong | Ответ на ping | Нет |

---

## Формат сообщения

Все сообщения имеют следующую структуру:

```
interface WSMessage {
  type: string;           // Тип сообщения (например, 'chat.query')
  payload: object;        // Данные, специфичные для сообщения
  timestamp?: string;     // Временная метка в формате ISO 8601
  request_id?: string;    // Для сопоставления запросов и ответов
}
```

---

## Сохранение соединения

Отправляйте периодические ping-сообщения, чтобы предотвратить таймаут соединения:

```
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping', payload: {} }));
  }
}, 30000); // Каждые 30 секунд
```

---

## Обработка ошибок {#error-handling}

### Формат сообщения об ошибке

```
{
  "type": "error",
  "payload": {
    "error": "Описание ошибки",
    "details": "Дополнительные сведения"
  },
  "request_id": "original-request-id"
}
```

### Распространённые ошибки {#common-errors}

| Ошибка | Причина | Решение |
| --- | --- | --- |
| Неверный формат сообщения | Некорректный JSON | Проверьте структуру сообщения |
| Требуется запрос | Пустой запрос | Укажите текст запроса |
| Неизвестный тип сообщения | Неподдерживаемый тип | Используйте типы, описанные в документации |
| Задача не найдена | Неверный идентификатор задачи | Убедитесь, что задача существует |

## Пример клиента на Python {#python-client-example}

```
import asyncio
import json
import websockets

async def chat_client(token: str, query: str):
    uri = f"ws://localhost:8000/ws/v1/chat?token={token}"

    async with websockets.connect(uri) as ws:
        # Отправка запроса
        await ws.send(json.dumps({
            "type": "chat.query",
            "payload": {"query": query},
            "request_id": "req-001"
        }))

        # Получение потокового ответа
        full_response = ""
        async for message in ws:
            data = json.loads(message)

            if data["type"] == "chat.chunk":
                content = data["payload"]["content"]
                full_response += content
                print(content, end="", flush=True)

            elif data["type"] == "chat.done":
                print("\n--- Ответ завершён ---")
                break

            elif data["type"] == "error":
                print(f"Ошибка: {data['payload']['error']}")
                break

        return full_response

# Использование {#usage}
asyncio.run(chat_client("your-jwt-token", "Найди переполнения буфера"))
```

## Пример JavaScript-клиента

```
class ChatClient {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.handlers = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(
        `ws://localhost:8000/ws/v1/chat?token=${this.token}`
      );

      this.ws.onopen = () => resolve(this);
      this.ws.onerror = (error) => reject(error);

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        const handler = this.handlers.get(message.request_id);
        if (handler) {
          handler(message);
        }
      };
    });
  }

  async query(text, onChunk) {
    const requestId = `req-${Date.now()}`;

    return new Promise((resolve, reject) => {
      let fullResponse = '';

      this.handlers.set(requestId, (message) => {
        switch (message.type) {
          case 'chat.chunk':
            fullResponse += message.payload.content;
            onChunk?.(message.payload.content);
            break;
          case 'chat.done':
            this.handlers.delete(requestId);
            resolve(fullResponse);
            break;
          case 'error':
            this.handlers.delete(requestId);
            reject(new Error(message.payload.error));
            break;
        }
      });

      this.ws.send(JSON.stringify({
        type: 'chat.query',
        payload: { query: text },
        request_id: requestId
      }));
    });
  }

  close() {
    this.ws?.close();
  }
}

// Использование
const client = await new ChatClient('jwt-token').connect();
const response = await client.query(
  'Найти SQL-инъекции',
  (chunk) => process.stdout.write(chunk)
);
console.log('\nПолный ответ:', response);
client.close();
```

---

## Ограничения по скорости

| Ограничение | Значение | Описание |
| --- | --- | --- |
| Макс. количество соединений на пользователя | 5 | Одновременные WebSocket-соединения |
| Макс. размер сообщения | 64 КБ | Полезная нагрузка одного сообщения |
| Сообщений в секунду | 10 | Ограничение скорости на одно соединение |
| Интервал ping | 30 сек | Рекомендуемый интервал для поддержания соединения |
| Таймаут соединения | 5 мин | Таймаут неактивного соединения |

## Смотрите также

- [Справочник по REST API](./REST_API.md) — документация по HTTP API
- [Руководство по аутентификации](../development/AUTHENTICATION_UPDATE.md) — работа с JWT-токенами
- [Служба чата](../development/ARCHITECTURE.md#chat-service) — архитектура чата
