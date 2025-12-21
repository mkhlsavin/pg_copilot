# WebSocket API Reference

This document describes the WebSocket API for real-time communication with CodeGraph.

## Overview

The WebSocket API provides:
- **Streaming chat responses** - Real-time AI response streaming
- **Job progress updates** - Background job status notifications
- **Push notifications** - System alerts and notifications

Base URL: `ws://localhost:8000/ws/v1`

---

## Authentication

All WebSocket connections require a JWT token passed as a query parameter.

```
ws://localhost:8000/ws/v1/chat?token=<JWT_TOKEN>
```

### Connection Errors

| Code | Reason | Description |
|------|--------|-------------|
| 4001 | Invalid token | Token is missing, expired, or invalid |
| 4003 | Forbidden | User lacks permission |
| 1008 | Policy violation | Connection policy error |

---

## Endpoints

### Chat Streaming

**Endpoint:** `ws://localhost:8000/ws/v1/chat`

Real-time chat with streaming responses.

#### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v1/chat?token=' + token);

ws.onopen = () => {
  console.log('Connected to chat');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message.type, message.payload);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log('Disconnected:', event.code, event.reason);
};
```

#### Send Chat Query

```javascript
ws.send(JSON.stringify({
  type: 'chat.query',
  payload: {
    query: 'Find all SQL injection vulnerabilities',
    session_id: 'optional-session-id',
    scenario_id: 'optional-scenario-id',
    language: 'en'
  },
  request_id: 'unique-request-id'
}));
```

#### Receive Streaming Response

Messages arrive in sequence:

1. **Scenario Selection** (optional)
```json
{
  "type": "chat.scenario",
  "payload": { "scenario_id": "security_audit" },
  "timestamp": "2025-12-14T10:30:00Z",
  "request_id": "unique-request-id"
}
```

2. **Response Chunks** (multiple)
```json
{
  "type": "chat.chunk",
  "payload": { "content": "Found 3 potential ", "is_final": false },
  "timestamp": "2025-12-14T10:30:01Z",
  "request_id": "unique-request-id"
}
```

3. **Completion**
```json
{
  "type": "chat.done",
  "payload": {},
  "timestamp": "2025-12-14T10:30:05Z",
  "request_id": "unique-request-id"
}
```

---

### Job Status

**Endpoint:** `ws://localhost:8000/ws/v1/jobs/{job_id}`

Subscribe to background job progress updates.

#### Connection

```javascript
const jobId = 'abc123';
const ws = new WebSocket(`ws://localhost:8000/ws/v1/jobs/${jobId}?token=${token}`);
```

#### Messages

**Job Started**
```json
{
  "type": "job.started",
  "payload": {
    "job_id": "abc123",
    "status": "subscribed"
  },
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Job Progress**
```json
{
  "type": "job.progress",
  "payload": {
    "job_id": "abc123",
    "status": "running",
    "progress": 45,
    "message": "Processing files..."
  },
  "timestamp": "2025-12-14T10:31:00Z"
}
```

**Job Completed**
```json
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

**Job Failed**
```json
{
  "type": "job.failed",
  "payload": {
    "job_id": "abc123",
    "status": "failed",
    "error": "Connection timeout",
    "details": "Could not connect to Joern server"
  },
  "timestamp": "2025-12-14T10:35:00Z"
}
```

---

### Notifications

**Endpoint:** `ws://localhost:8000/ws/v1/notifications`

Receive push notifications for system events.

#### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v1/notifications?token=' + token);
```

#### Messages

**Notification**
```json
{
  "type": "notification",
  "payload": {
    "title": "Import Complete",
    "message": "Project 'myapp' has been imported successfully",
    "level": "success",
    "action_url": "/projects/abc123"
  },
  "timestamp": "2025-12-14T10:35:00Z"
}
```

Notification levels: `info`, `success`, `warning`, `error`

---

## Message Types

### Client → Server

| Type | Description | Payload |
|------|-------------|---------|
| `chat.query` | Send chat query | `query`, `session_id?`, `scenario_id?`, `language?` |
| `ping` | Keep connection alive | None |

### Server → Client

| Type | Description | Payload |
|------|-------------|---------|
| `chat.scenario` | Scenario selection | `scenario_id` |
| `chat.chunk` | Response chunk | `content`, `is_final` |
| `chat.done` | Response complete | None |
| `chat.error` | Chat error | `error`, `details?` |
| `job.started` | Job subscribed | `job_id`, `status` |
| `job.progress` | Job progress | `job_id`, `status`, `progress`, `message?` |
| `job.completed` | Job finished | `job_id`, `result` |
| `job.failed` | Job failed | `job_id`, `error`, `details?` |
| `notification` | Push notification | `title`, `message`, `level`, `action_url?` |
| `error` | General error | `error`, `details?` |
| `pong` | Ping response | None |

---

## Message Format

All messages follow this structure:

```typescript
interface WSMessage {
  type: string;           // Message type (e.g., 'chat.query')
  payload: object;        // Message-specific data
  timestamp?: string;     // ISO 8601 timestamp
  request_id?: string;    // For correlating requests/responses
}
```

---

## Keep-Alive

Send periodic ping messages to prevent connection timeout:

```javascript
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping', payload: {} }));
  }
}, 30000); // Every 30 seconds
```

---

## Error Handling

### Error Message Format

```json
{
  "type": "error",
  "payload": {
    "error": "Error description",
    "details": "Additional details"
  },
  "request_id": "original-request-id"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid message format | Malformed JSON | Check message structure |
| Query is required | Empty query | Provide query text |
| Unknown message type | Unsupported type | Use documented types |
| Job not found | Invalid job ID | Verify job exists |

---

## Python Client Example

```python
import asyncio
import json
import websockets

async def chat_client(token: str, query: str):
    uri = f"ws://localhost:8000/ws/v1/chat?token={token}"

    async with websockets.connect(uri) as ws:
        # Send query
        await ws.send(json.dumps({
            "type": "chat.query",
            "payload": {"query": query},
            "request_id": "req-001"
        }))

        # Receive streaming response
        full_response = ""
        async for message in ws:
            data = json.loads(message)

            if data["type"] == "chat.chunk":
                content = data["payload"]["content"]
                full_response += content
                print(content, end="", flush=True)

            elif data["type"] == "chat.done":
                print("\n--- Response complete ---")
                break

            elif data["type"] == "error":
                print(f"Error: {data['payload']['error']}")
                break

        return full_response

# Usage
asyncio.run(chat_client("your-jwt-token", "Find buffer overflows"))
```

---

## JavaScript Client Example

```javascript
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

// Usage
const client = await new ChatClient('jwt-token').connect();
const response = await client.query(
  'Find SQL injections',
  (chunk) => process.stdout.write(chunk)
);
console.log('\nFull response:', response);
client.close();
```

---

## Rate Limits

| Limit | Value | Description |
|-------|-------|-------------|
| Max connections per user | 5 | Concurrent WebSocket connections |
| Max message size | 64 KB | Single message payload |
| Messages per second | 10 | Rate limit per connection |
| Ping interval | 30 sec | Recommended keep-alive interval |
| Connection timeout | 5 min | Idle connection timeout |

---

## See Also

- [REST API Reference](./REST_API.md) - HTTP API documentation
- [Authentication Guide](../development/AUTHENTICATION_UPDATE.md) - JWT token handling
- [Chat Service](../development/ARCHITECTURE.md#chat-service) - Chat architecture
