# A2A Protocol v1.0 — Implementation Notes

> Reference: https://google.github.io/A2A  
> These notes focus on what A2A-Mesh needs to implement.

---

## 1. Core Concepts

| Concept | Description |
|---|---|
| **Agent Card** | JSON document that describes an agent's identity, capabilities, and endpoints |
| **Task** | A unit of work with a lifecycle: submitted → working → completed/failed |
| **Message** | Input or output exchanged between caller and agent (user or agent role) |
| **Part** | Atomic content unit inside a message: TextPart, FilePart, or DataPart |
| **Artifact** | Output produced by an agent (code, text, data) attached to a completed Task |

---

## 2. Agent Card Format

Served at `GET /.well-known/agent.json` (platform-level) and optionally per agent.

```json
{
  "name": "coder",
  "description": "Writes production Python code from task descriptions",
  "url": "https://api.acme.com/a2a/agt_abc123def456",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "write_code",
      "name": "Write Code",
      "description": "Generate working Python code from a task description",
      "tags": ["python", "codegen"],
      "examples": ["Add a /login endpoint to this Flask app"],
      "inputModes": ["text/plain"],
      "outputModes": ["text/plain"]
    }
  ],
  "authentication": {
    "schemes": ["Bearer"]
  }
}
```

**Key fields:**
- `url` — base URL for A2A protocol calls to this agent
- `capabilities.streaming` — whether `/message/stream` SSE is supported
- `skills` — what the agent can do (used for federation discovery)
- `authentication.schemes` — how callers must authenticate

---

## 3. JSON-RPC 2.0 Message Format

All A2A calls use JSON-RPC 2.0 over HTTP POST.

### Request envelope
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "message/send",
  "params": { ... }
}
```

### Response envelope
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": { ... }
}
```

### Error envelope
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": { ... }
  }
}
```

**Standard JSON-RPC error codes:**
| Code | Meaning |
|---|---|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

---

## 4. Methods We Must Implement

### 4.1 `message/send`
**Endpoint:** `POST /a2a/{agent_id}/message/send`

Send a message to an agent and get back a task result synchronously.

**Request params:**
```json
{
  "message": {
    "role": "user",
    "parts": [
      { "type": "text", "text": "Add a /login endpoint" }
    ],
    "messageId": "msg-uuid"
  },
  "configuration": {
    "acceptedOutputModes": ["text/plain"]
  }
}
```

**Result:**
```json
{
  "id": "tsk_abc123def456",
  "status": {
    "state": "completed",
    "timestamp": "2026-06-26T10:00:00Z"
  },
  "artifacts": [
    {
      "artifactId": "art-1",
      "parts": [
        { "type": "text", "text": "def login(): ..." }
      ]
    }
  ]
}
```

### 4.2 `message/stream`
**Endpoint:** `POST /a2a/{agent_id}/message/stream`

Same params as `message/send` but responds with Server-Sent Events (SSE).

Each SSE event is a JSON-RPC response fragment with partial task state:
```
data: {"jsonrpc":"2.0","id":"req-1","result":{"id":"tsk_...","status":{"state":"working"}}}

data: {"jsonrpc":"2.0","id":"req-1","result":{"id":"tsk_...","status":{"state":"completed"},"artifacts":[...]}}
```

The stream ends when `status.state` is terminal (completed/failed/canceled).

### 4.3 `tasks/get`
**Endpoint:** `GET /a2a/{agent_id}/tasks/{task_id}` (or JSON-RPC `tasks/get`)

Returns current task state.

### 4.4 `tasks/cancel`
**Endpoint:** `POST /a2a/{agent_id}/tasks/{task_id}/cancel`

Attempts to cancel a running task. Sets state to `canceled` if successful.

---

## 5. Task Lifecycle

```
submitted → working → completed
                    ↘ failed
                    ↘ canceled
                    ↘ input-required  (agent needs clarification)
```

- `submitted` — task received, not yet started
- `working` — agent actively processing
- `input-required` — agent paused, waiting for user response
- `completed` — final artifacts available
- `failed` — terminal error
- `canceled` — caller or agent cancelled it

---

## 6. Part Types

```json
{ "type": "text", "text": "Hello world" }

{ "type": "file", "file": { "name": "main.py", "mimeType": "text/x-python", "bytes": "<base64>" } }

{ "type": "data", "data": { "approved": true, "feedback": "LGTM" } }
```

`DataPart` is the key type for structured agent outputs (e.g. Reviewer → `{ "approved": bool, "feedback": str }`).

---

## 7. What the `/.well-known/agent.json` Endpoint Must Return

This is the platform-level discovery endpoint. In our case it describes the platform itself, not individual agents. Individual agents serve their cards at `/v1/agents/{id}/card` and `/a2a/{agent_id}/.well-known/agent.json`.

---

## 8. Implementation Order (for A2A-Mesh)

1. **Week 2** — Echo Agent: `message/send`, `message/stream`, `tasks/get`
2. **Week 3** — Persistent task storage, BaseAgent class
3. **Week 5** — Claude-powered agents via `BaseAgent`
4. **Week 9** — Federation: Agent Card discovery across companies, signed JWT calls
