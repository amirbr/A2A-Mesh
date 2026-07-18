# A2A-Mesh — Architecture Reference

> The technical source of truth. When Claude Code or a developer needs to make a design decision, it should match what's here.
> See **PLAN.md** for the weekly build schedule and **CLAUDE.md** for coding rules.

---

## 1. System Architecture

```
                  ┌─────────────────────────────┐
                  │       Orchestrator API       │  ← control plane (FastAPI)
                  │       /v1/* + /a2a/*         │
                  └──────────────┬──────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│Agent Registry│         │ Task Engine  │         │  Federation  │
│   (catalog)  │         │  (executor)  │         │    Layer     │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
                  ┌─────────────────────────────┐
                  │      Agent Runtime Pool      │
                  │  (Docker containers)         │
                  └──────────────┬──────────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  ▼                             ▼
            ┌──────────┐                  ┌──────────┐
            │PostgreSQL│                  │  Redis   │
            └──────────┘                  └──────────┘
```

**Components:**

| Component | Responsibility |
|---|---|
| Orchestrator API | Public REST API. Handles auth, CRUD, pipeline execution requests |
| Agent Registry | Internal database of agents and their metadata |
| Task Engine | Schedules and tracks task execution |
| Federation Layer | Cross-company discovery, trust, JWT signing/verification |
| Agent Runtime | Where agents actually run (Docker containers in MVP) |
| Postgres | Persistent storage for all data |
| Redis | Cache, task queue, rate limits |

---

## 2. Tech Stack (Locked)

| Concern | Tool | Version |
|---|---|---|
| Language | Python | 3.11+ |
| Web framework | FastAPI | latest |
| ASGI server | Uvicorn | latest |
| ORM | SQLAlchemy (async) | 2.0+ |
| Migrations | Alembic | latest |
| DB driver | asyncpg | latest |
| Database | PostgreSQL | 15+ |
| Cache / Queue | Redis | 7+ |
| Validation | Pydantic | v2 |
| Settings | pydantic-settings | latest |
| LLM | LiteLLM | multi-provider (claude-opus-4-8 default, Ollama, OpenAI) |
| Agent SDK | a2a-sdk, google-adk | latest |
| Auth | python-jose (JWT), argon2-cffi (passwords) | latest |
| Testing | pytest, pytest-asyncio, httpx | latest |
| Format / lint | ruff | latest |
| Type checking | mypy (strict) | latest |
| Container | Docker, docker-compose | latest |
| Deployment | Railway or Fly.io (MVP) | — |

---

## 3. Data Models

### 3.1 Company
```python
class Company:
    id: str              # "co_" + 12char
    name: str
    namespace: str       # url-safe (e.g. "acme")
    domain: str | None   # for federation
    plan: str            # "free" | "pro" | "business" | "enterprise"
    created_at: datetime
    updated_at: datetime
```

### 3.2 User
```python
class User:
    id: str              # "usr_" + 12char
    company_id: str      # FK -> Company
    email: str           # unique
    password_hash: str   # argon2
    role: str            # "admin" | "member"
    created_at: datetime
    updated_at: datetime
```

### 3.3 Agent
```python
class Agent:
    id: str              # "agt_" + 12char
    company_id: str      # FK -> Company
    name: str            # url-safe slug
    display_name: str
    description: str
    version: str         # semver
    status: str          # "creating" | "running" | "stopped" | "error"
    visibility: str      # "private" | "internal" | "partners" | "public"
    runtime: str         # "managed" | "byo"
    config: dict         # see Agent Configuration below
    endpoint_url: str | None  # internal URL where agent runs
    created_at: datetime
    updated_at: datetime
```

### 3.4 Pipeline
```python
class Pipeline:
    id: str              # "pip_" + 12char
    company_id: str      # FK -> Company
    name: str
    description: str
    steps: list[dict]    # ordered list of step configs
    created_at: datetime
    updated_at: datetime
```

### 3.5 Task
```python
class Task:
    id: str              # "tsk_" + 12char
    agent_id: str        # FK -> Agent
    pipeline_run_id: str | None  # FK -> PipelineRun (if part of a pipeline)
    caller_id: str       # who initiated (user_id or agent_id)
    status: str          # "pending" | "running" | "completed" | "failed" | "cancelled"
    input: dict          # JSON
    output: dict | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime
```

### 3.6 PipelineRun
```python
class PipelineRun:
    id: str              # "run_" + 12char
    pipeline_id: str     # FK -> Pipeline
    status: str          # "running" | "completed" | "failed"
    input: dict
    output: dict | None
    started_at: datetime
    completed_at: datetime | None
```

### 3.7 ApiKey
```python
class ApiKey:
    id: str              # "key_" + 12char
    company_id: str      # FK -> Company
    key_hash: str        # hash of the actual key
    prefix: str          # first 8 chars, displayed in UI
    name: str
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked: bool
    created_at: datetime
```

### 3.8 TrustRelationship
```python
class TrustRelationship:
    id: str              # "trust_" + 12char
    from_company_id: str
    to_company_id: str
    allowed_agents: list[str]  # agent ids that can be called
    rate_limit: str            # "100/hour" etc
    active: bool
    created_at: datetime
```

### 3.9 AuditLog (federation calls)
```python
class AuditLog:
    id: str              # "log_" + 12char
    caller_company_id: str
    caller_agent_id: str
    target_company_id: str
    target_agent_id: str
    task_id: str
    input_hash: str
    output_hash: str | None
    status: str
    cost_usd: float
    created_at: datetime
```

---

## 4. API Surface

### 4.1 Authentication (`/v1/auth/*`)
- `POST /v1/auth/register` — register company + admin user
- `POST /v1/auth/login` — issue JWT
- `POST /v1/auth/api-keys` — generate API key
- `GET /v1/auth/api-keys` — list keys
- `DELETE /v1/auth/api-keys/{id}` — revoke

### 4.2 Companies (`/v1/companies/*`)
- `GET /v1/companies/me`
- `PATCH /v1/companies/me`
- `GET /v1/companies/{namespace}` — public profile for federation

### 4.3 Agents (`/v1/agents/*`)
- `POST /v1/agents` — create
- `GET /v1/agents` — list
- `GET /v1/agents/{id}` — get one
- `PATCH /v1/agents/{id}` — update
- `DELETE /v1/agents/{id}` — delete
- `GET /v1/agents/{id}/card` — public A2A Agent Card

### 4.4 Agent Runtime (`/v1/agents/{id}/*`)
- `POST /v1/agents/{id}/deploy`
- `POST /v1/agents/{id}/stop`
- `GET /v1/agents/{id}/status`
- `GET /v1/agents/{id}/logs`
- `GET /v1/agents/{id}/metrics`

### 4.5 A2A Protocol (`/a2a/*`)
- `GET /.well-known/agent.json` — standard A2A discovery
- `POST /a2a/{agent_id}/message/send` — JSON-RPC
- `POST /a2a/{agent_id}/message/stream` — SSE streaming
- `GET /a2a/{agent_id}/tasks/{task_id}` — task status
- `POST /a2a/{agent_id}/tasks/{task_id}/cancel`

### 4.6 Pipelines (`/v1/pipelines/*`)
- `POST /v1/pipelines` — create
- `GET /v1/pipelines` — list
- `GET /v1/pipelines/{id}`
- `PATCH /v1/pipelines/{id}`
- `DELETE /v1/pipelines/{id}`
- `POST /v1/pipelines/{id}/run` — execute
- `GET /v1/pipelines/{id}/runs/{run_id}` — run status

### 4.7 Tasks (`/v1/tasks/*`)
- `GET /v1/tasks` — list (filterable)
- `GET /v1/tasks/{id}`
- `POST /v1/tasks/{id}/cancel`

### 4.8 Federation (`/v1/federation/*`)
- `GET /v1/federation/discover?capability=...`
- `POST /v1/federation/invite`
- `POST /v1/federation/trust`
- `GET /v1/federation/partners`
- `DELETE /v1/federation/trust/{id}`

### 4.9 Observability (`/v1/*`)
- `GET /v1/metrics` — Prometheus format
- `GET /v1/audit-log`
- `GET /v1/usage`

---

## 5. Agent Configuration Schema

```python
class AgentConfig(BaseModel):
    provider: str = "anthropic"    # "anthropic" | "ollama" | "openai"
    model: str = "claude-opus-4-8"
    temperature: float = 0.2
    max_tokens: int = 4096
    system_prompt: str
    tools: list[str] = []                  # built-in tool names
    mcp_servers: list[str] = []            # external MCP server URLs
    memory: MemoryConfig
    rate_limit: str = "60/minute"
    cost_limit_usd: float = 5.00
    timeout_seconds: int = 300
    retry: RetryConfig
    auth: AuthConfig

class MemoryConfig(BaseModel):
    type: Literal["none", "session", "persistent"] = "session"
    max_size_mb: int = 50

class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff: Literal["linear", "exponential"] = "exponential"

class AuthConfig(BaseModel):
    required: bool = True
    allowed_companies: list[str] = []      # company namespaces
```

---

## 6. Visibility Levels

| Visibility | Who can call this agent |
|---|---|
| `private` | Only the owning user |
| `internal` | Anyone in the same company |
| `partners` | Companies in the trust list |
| `public` | Anyone on the federation network |

Visibility is checked on every call, before any other logic.

---

## 7. Runtime Modes

| Mode | Description | Use case |
|---|---|---|
| `managed` | We host, shared container pool | Default for most customers |
| `managed_dedicated` | We host, isolated host(s) per company | Paid tier, compliance-sensitive |
| `byo` | Customer runs an outbound-only "Runner" in their own cloud account; we never touch their credentials or expose inbound ports | Data-residency requirements |

Not built yet — as of Week 6 all agents still run in-process (`orchestrator/registry.py`, an
in-memory dict), not in Docker. **See `AGENT_RUNTIME_ARCHITECTURE.md` for the full design,
phased rollout plan, and why Kubernetes is deliberately deferred, not rejected.**

---

## 8. Communication Flows

### 8.1 User creates an agent
```
User → POST /v1/agents (with config) → orchestrator
orchestrator → DB: insert agent row (status: creating)
orchestrator → runtime: spin up container
runtime → reports ready
orchestrator → DB: update status to running
orchestrator → publishes Agent Card at /a2a/{agent_id}/card
Response → { id, status, agent_card_url }
```

### 8.2 Single agent task
```
Caller → POST /a2a/{agent_id}/message/send
agent → calls Claude with system prompt + input + tools
agent → executes tool calls if any
agent → returns final response via JSON-RPC
orchestrator → logs task in DB (input, output, tokens, cost)
```

### 8.3 Pipeline execution
```
User → POST /v1/pipelines/{id}/run
orchestrator → creates PipelineRun
orchestrator → for each step:
   call agent via internal A2A
   pipe output to next step
   handle loop_until logic if specified
orchestrator → marks run completed
```

### 8.4 Internal agent-to-agent call (same company)
```
Agent A → POST /a2a/agent_b/message/send (with internal auth header)
orchestrator → validates both agents in same company
orchestrator → routes to Agent B
Agent B → processes, returns
audit log entry written
```

### 8.5 Cross-company agent call
```
Agent A (Acme) wants to call Agent B (Partner)

1. Acme admin → POST /v1/federation/invite (to Partner)
2. Partner admin → POST /v1/federation/trust → trust_id
3. Agent A → GET /v1/federation/discover?capability=X
4. discovery returns Partner's public Agent B card
5. Agent A → POST https://partner.com/a2a/agent_b/message/send
   Authorization: Bearer <signed federation JWT>
   JWT claims: { iss: "acme", sub: "agt_a", aud: "partner", exp: ... }
6. Partner orchestrator verifies JWT signature
7. Partner checks trust active + Agent B's allowed_companies
8. Agent B processes, returns
9. Both sides log to audit_log
```

---

## 9. Authentication Layers

| Layer | Mechanism | Used for |
|---|---|---|
| User auth | JWT (HS256, 1hr expiry) | Logged-in users hitting `/v1/*` |
| API key | Random key, hashed in DB | Programmatic access |
| Internal agent auth | JWT (short-lived) | Same-company agent calls |
| Federation auth | JWT signed with company's private key | Cross-company agent calls |
| Optional mTLS | Certificates | High-security partners |

All endpoints require auth except `/.well-known/*` and `/v1/auth/login`.

---

## 10. Error Response Format

All errors return:
```json
{
  "error": {
    "code": "string_code",
    "message": "Human readable explanation",
    "details": { "...": "..." }
  }
}
```

Common codes:
- `auth_required` (401)
- `forbidden` (403)
- `not_found` (404)
- `validation_error` (422)
- `rate_limited` (429)
- `agent_unavailable` (503)
- `federation_trust_denied` (403)
- `internal_error` (500)

---

## 11. ID Format

| Entity | Prefix | Example |
|---|---|---|
| Company | `co_` | `co_a1b2c3d4e5f6` |
| User | `usr_` | `usr_a1b2c3d4e5f6` |
| Agent | `agt_` | `agt_a1b2c3d4e5f6` |
| Pipeline | `pip_` | `pip_a1b2c3d4e5f6` |
| Pipeline Run | `run_` | `run_a1b2c3d4e5f6` |
| Task | `tsk_` | `tsk_a1b2c3d4e5f6` |
| API Key | `key_` | `key_a1b2c3d4e5f6` |
| Trust | `trust_` | `trust_a1b2c3d4e5f6` |
| Audit Log | `log_` | `log_a1b2c3d4e5f6` |

ID format: `prefix_` + 12 lowercase alphanumeric chars. Generated with `secrets.token_hex(6)`.

---

## 12. Non-Goals (explicit, for MVP)

- No UI / frontend
- No billing system (Stripe later)
- No marketplace / public discovery UI
- No mobile app
- No agent marketplace or templates beyond Coder/Reviewer/Jira
- No Kubernetes
- No Kafka, no SQS, no message broker beyond Redis
- No multi-region deployment
- No advanced observability (Datadog comes later)
- No SOC2 / compliance certifications (post-product-market-fit)

If any of these come up during a session, push back and reference this section.
