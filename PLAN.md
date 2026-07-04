# A2A Agent Orchestrator — Build Plan

> An API-first, 12-week plan to build the core platform.
> UI comes after the API is solid and working.

---

## 0. Working with Claude Code

This project is built with Claude Code (in Cursor) as the AI pair programmer.

**At the start of every session**, Claude Code should read these files in order:
1. `CLAUDE.md` — coding rules, conventions, what NOT to do
2. `PROGRESS.md` — current week, what's done, what's next
3. `ARCHITECTURE.md` — system design, data models, API surface
4. This file (`PLAN.md`) — when zooming out to weekly deliverables

**At the end of every session**, update `PROGRESS.md` with what was done.

**Project metadata:**
- Repo: https://github.com/amirbr/A2A-Mesh
- Name: A2A-Mesh
- Founder: Amir (solo)

---

## 1. Product Vision

A platform where companies can:

1. **Internally** — build and orchestrate teams of AI agents that handle real workflows (e.g. Coder → Reviewer → Jira).
2. **Externally** — let their agents discover and communicate with agents at *other companies* using the A2A protocol.

The internal use case is the entry point. The cross-company federation is the long-term moat.

---

## 2. Scope of This Plan

- ✅ Backend API only (no UI)
- ✅ Internal multi-agent orchestration
- ✅ Cross-company agent federation foundations
- ✅ One real working pipeline: Coder → Reviewer → Jira
- ❌ No visual builder UI (later phase)
- ❌ No billing system (later phase)
- ❌ No marketplace (later phase)

---

## 3. Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Agent framework | Google ADK + `a2a-sdk` |
| HTTP server | FastAPI + Uvicorn |
| LLM | LiteLLM (multi-provider: Anthropic, Ollama, OpenAI, etc.) |
| Database | PostgreSQL |
| Cache / queue | Redis |
| Auth | JWT + API keys |
| Runtime | Docker, optional Kubernetes |
| Deployment | Railway / Fly.io to start, AWS later |
| Testing | pytest |

---

## 4. System Architecture

```
                  ┌─────────────────────────────┐
                  │       Orchestrator API       │  ← control plane
                  │   (FastAPI / public REST)    │
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
                  │  (where agents actually run) │
                  │                              │
                  │  ┌────────┐  ┌────────┐      │
                  │  │ Coder  │  │Reviewer│  ... │
                  │  └────────┘  └────────┘      │
                  └──────────────┬──────────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  ▼                             ▼
            ┌──────────┐                  ┌──────────┐
            │PostgreSQL│                  │  Redis   │
            └──────────┘                  └──────────┘
```

**Components:**

- **Orchestrator API** — the public-facing REST API users interact with
- **Agent Registry** — stores agent definitions, configs, and capabilities
- **Task Engine** — schedules and executes tasks across agents
- **Federation Layer** — handles cross-company discovery and auth
- **Agent Runtime** — where agents actually execute (managed cloud or self-hosted)
- **Postgres** — persistent storage (agents, pipelines, tasks, audit logs)
- **Redis** — queues, caches, rate limits

---

## 5. Data Models

### Company (tenant)
```json
{
  "id": "co_abc123",
  "name": "Acme Inc",
  "namespace": "acme",
  "domain": "acme.com",
  "plan": "pro",
  "created_at": "2026-06-11T10:00:00Z"
}
```

### User
```json
{
  "id": "usr_xyz789",
  "company_id": "co_abc123",
  "email": "dev@acme.com",
  "role": "admin"
}
```

### Agent
```json
{
  "id": "agt_coder01",
  "company_id": "co_abc123",
  "name": "coder",
  "display_name": "Code Generator",
  "description": "Writes production Python code from task descriptions",
  "version": "1.0.0",
  "status": "running",
  "visibility": "internal",
  "runtime": "managed",
  "config": { /* see Agent Configuration */ },
  "agent_card_url": "https://api.acme.com/agents/agt_coder01/card"
}
```

### Pipeline
```json
{
  "id": "pip_devflow",
  "company_id": "co_abc123",
  "name": "dev-pipeline",
  "steps": [
    { "agent_id": "agt_coder01", "input_from": "user" },
    { "agent_id": "agt_reviewer01", "input_from": "previous", "loop_until": "approved" },
    { "agent_id": "agt_jira01", "input_from": "previous" }
  ]
}
```

### Task
```json
{
  "id": "tsk_001",
  "agent_id": "agt_coder01",
  "pipeline_run_id": "run_555",
  "status": "completed",
  "input": { "prompt": "Add a /login endpoint" },
  "output": { "code": "..." },
  "started_at": "...",
  "completed_at": "...",
  "tokens_used": 4521,
  "cost_usd": 0.07
}
```

### Trust Relationship (for federation)
```json
{
  "id": "trust_001",
  "from_company_id": "co_abc123",
  "to_company_id": "co_partner456",
  "allowed_agents": ["agt_partner_inventory"],
  "rate_limit": "100/hour",
  "created_at": "..."
}
```

---

## 6. Complete API Reference

> All endpoints are prefixed with `/v1`. Auth header: `Authorization: Bearer <token>` or `X-API-Key: <key>`.

### 6.1 Authentication

#### `POST /v1/auth/register` — Register a new company
```json
// Request
{
  "company_name": "Acme Inc",
  "email": "admin@acme.com",
  "password": "secret123"
}

// Response
{
  "company_id": "co_abc123",
  "user_id": "usr_xyz789",
  "access_token": "eyJhbGc...",
  "api_key": "ak_live_..."
}
```

#### `POST /v1/auth/login`
```json
// Request
{ "email": "admin@acme.com", "password": "secret123" }

// Response
{ "access_token": "eyJhbGc...", "expires_in": 3600 }
```

#### `POST /v1/auth/api-keys` — Generate a new API key
#### `GET /v1/auth/api-keys` — List keys
#### `DELETE /v1/auth/api-keys/{id}` — Revoke a key

---

### 6.2 Companies

#### `GET /v1/companies/me` — My company details
#### `PATCH /v1/companies/me` — Update company settings
#### `GET /v1/companies/{namespace}` — Public profile (for federation)

---

### 6.3 Agents (CRUD)

#### `POST /v1/agents` — **Create a new agent**
```json
// Request
{
  "name": "coder",
  "display_name": "Code Generator",
  "description": "Writes production Python code",
  "config": {
    "model": "claude-opus-4-8",
    "temperature": 0.2,
    "max_tokens": 4096,
    "system_prompt": "You are a senior Python engineer...",
    "tools": ["file_read", "file_write", "run_tests"],
    "mcp_servers": ["https://github-mcp.acme.com"],
    "memory": { "type": "session" },
    "rate_limit": "60/minute",
    "cost_limit_usd": 5.00
  },
  "visibility": "internal",
  "runtime": "managed"
}

// Response
{
  "id": "agt_coder01",
  "status": "creating",
  "agent_card_url": "https://api.acme.com/agents/agt_coder01/card"
}
```

#### `GET /v1/agents` — List all agents in company
#### `GET /v1/agents/{id}` — Get one agent
#### `PATCH /v1/agents/{id}` — **Update agent settings**
```json
// Request — change anything
{
  "config": {
    "system_prompt": "Updated prompt...",
    "temperature": 0.5
  }
}
```
#### `DELETE /v1/agents/{id}` — Delete an agent

#### `GET /v1/agents/{id}/card` — Returns the public A2A Agent Card
```json
{
  "name": "coder",
  "description": "Writes production Python code",
  "url": "https://api.acme.com/a2a/agt_coder01",
  "version": "1.0.0",
  "capabilities": { "streaming": true, "pushNotifications": false },
  "skills": [
    {
      "id": "write_code",
      "name": "Write code",
      "description": "Generate code from a task description"
    }
  ]
}
```

---

### 6.4 Agent Runtime (where it lives)

#### `POST /v1/agents/{id}/deploy` — Deploy / start the agent
```json
// Request
{ "runtime": "managed", "region": "us-east-1" }

// Response
{ "status": "running", "endpoint": "https://api.acme.com/a2a/agt_coder01" }
```

#### `POST /v1/agents/{id}/stop` — Stop the agent
#### `GET /v1/agents/{id}/status` — Health check
#### `GET /v1/agents/{id}/logs?since=...` — Stream logs
#### `GET /v1/agents/{id}/metrics` — CPU, memory, tasks/sec

---

### 6.5 Agent Communication (A2A Protocol Endpoints)

> These are the standard A2A endpoints each agent exposes. Anyone with the right auth can call them.

#### `GET /.well-known/agent.json` — Standard A2A discovery endpoint
#### `POST /a2a/{agent_id}/message/send` — Send a task to the agent
```json
// Request (JSON-RPC 2.0)
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "Add a /login endpoint" }]
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "taskId": "tsk_001",
    "status": "running"
  }
}
```

#### `POST /a2a/{agent_id}/message/stream` — Stream responses via SSE
#### `GET /a2a/{agent_id}/tasks/{taskId}` — Get task status
#### `POST /a2a/{agent_id}/tasks/{taskId}/cancel` — Cancel a task

---

### 6.6 Pipelines

#### `POST /v1/pipelines` — Create a pipeline
```json
// Request
{
  "name": "dev-flow",
  "description": "Code → Review → Jira",
  "steps": [
    { "agent": "agt_coder01" },
    { "agent": "agt_reviewer01", "loop_until": { "field": "approved", "equals": true }, "max_iterations": 3 },
    { "agent": "agt_jira01" }
  ]
}
```

#### `GET /v1/pipelines` — List pipelines
#### `GET /v1/pipelines/{id}` — Get one
#### `PATCH /v1/pipelines/{id}` — Update
#### `DELETE /v1/pipelines/{id}` — Delete
#### `POST /v1/pipelines/{id}/run` — Execute a pipeline
```json
// Request
{ "input": { "task": "Add a login endpoint to the Flask app" } }

// Response
{ "run_id": "run_555", "status": "running" }
```

#### `GET /v1/pipelines/{id}/runs/{run_id}` — Get run status, all tasks, logs

---

### 6.7 Tasks

#### `GET /v1/tasks` — List all tasks (filterable)
#### `GET /v1/tasks/{id}` — Get one task
#### `POST /v1/tasks/{id}/cancel` — Cancel running task

---

### 6.8 Federation (Cross-Company)

#### `GET /v1/federation/discover?capability=code-review` — Search agents at other companies
```json
// Response
{
  "results": [
    {
      "company": "partner.com",
      "agent_id": "agt_review_x",
      "agent_card_url": "https://api.partner.com/agents/agt_review_x/card",
      "skills": ["code-review"]
    }
  ]
}
```

#### `POST /v1/federation/invite` — Invite another company to trust you
#### `POST /v1/federation/trust` — Accept a trust relationship
```json
// Request
{
  "company": "partner.com",
  "allowed_agents": ["agt_review_x"],
  "rate_limit": "100/hour"
}
```

#### `GET /v1/federation/partners` — List trusted companies
#### `DELETE /v1/federation/trust/{id}` — Revoke trust

---

### 6.9 Observability

#### `GET /v1/metrics` — Prometheus-format metrics
#### `GET /v1/audit-log?since=...` — Audit log of all cross-company calls
#### `GET /v1/usage?period=month` — Usage and cost report

---

## 7. Agent Configuration Reference

Every agent has a `config` object. Full schema:

```json
{
  "model": "claude-opus-4-8",         // which LLM
  "temperature": 0.2,                  // 0.0 = deterministic, 1.0 = creative
  "max_tokens": 4096,                  // max output length
  "system_prompt": "You are...",       // role/instructions
  "tools": ["file_read", "git_diff"],  // built-in tools the agent can use
  "mcp_servers": [                     // external tool servers
    "https://github-mcp.acme.com",
    "https://jira-mcp.acme.com"
  ],
  "memory": {
    "type": "session" | "persistent" | "none",
    "max_size_mb": 50
  },
  "rate_limit": "60/minute",           // calls per period
  "cost_limit_usd": 5.00,              // max $ per task
  "timeout_seconds": 300,              // max time per task
  "retry": {
    "max_attempts": 3,
    "backoff": "exponential"
  },
  "auth": {
    "required": true,                  // must caller be authenticated?
    "allowed_companies": ["partner.com"]
  }
}
```

### Visibility Levels

| Visibility | Who can call this agent? |
|---|---|
| `private` | Only this agent's owner (single user) |
| `internal` | Anyone in the same company |
| `partners` | Companies in the trust list |
| `public` | Anyone on the federation network |

---

## 8. Where Agents Can Run (Runtime Options)

The platform supports four runtime modes:

### 8.1 Managed Cloud (default, easiest)
You host the agent for the customer.
- Customer creates an agent → we deploy it to our cloud
- Auto-scaling, monitoring, logs all handled
- Pay-per-use or subscription pricing
- Best for: most customers, fastest start

```json
{ "runtime": "managed", "region": "us-east-1" }
```

### 8.2 Self-Hosted Docker
Customer runs the agent themselves in a Docker container.
- We give them an image: `acmecorp/agent-runtime:latest`
- They run `docker run` with config env vars
- Agent calls home to our orchestrator
- Best for: privacy-sensitive customers

```bash
docker run \
  -e A2A_AGENT_ID=agt_coder01 \
  -e A2A_API_KEY=ak_live_... \
  acmecorp/agent-runtime:latest
```

### 8.3 Self-Hosted Kubernetes
For enterprises with K8s already.
- We provide Helm chart
- Multi-replica, auto-scaling
- Best for: large enterprises

### 8.4 Bring Your Own (BYO)
Customer has an existing service. They register it as an A2A agent.
- They expose `/a2a/...` endpoints themselves
- We just route to them
- Best for: companies who already built agents

```json
{
  "runtime": "byo",
  "endpoint": "https://internal-agent.acme.com/a2a/coder"
}
```

---

## 9. Communication Flows (Step-by-Step)

### Flow 1 — User creates an agent

```
1. User → POST /v1/auth/login                           → access_token
2. User → POST /v1/agents (with config)                 → agent_id
3. Orchestrator → spin up agent in runtime              (managed cloud)
4. Orchestrator → publishes Agent Card at /.well-known  
5. User → GET /v1/agents/{id}/status                    → "running"
```

### Flow 2 — User runs a single agent task

```
1. User → POST /a2a/agt_coder01/message/send
         { "params": { "message": "Add /login endpoint" } }
2. Agent → calls Claude API with system prompt + input
3. Agent → uses tools (file_read, file_write)
4. Agent → returns result via JSON-RPC
5. Result stored in tasks table
```

### Flow 3 — User runs a pipeline (Coder → Reviewer → Jira)

```
1. User → POST /v1/pipelines/{id}/run                   → run_id
2. Orchestrator → calls agt_coder01                     (Task 1)
3. agt_coder01 → returns code                           
4. Orchestrator → calls agt_reviewer01 with code        (Task 2)
5. agt_reviewer01 → returns "needs changes"
6. Orchestrator → loops back to agt_coder01             (Task 3)
7. agt_coder01 → returns updated code
8. agt_reviewer01 → returns "approved"
9. Orchestrator → calls agt_jira01 with summary         (Task 4)
10. agt_jira01 → creates Jira ticket
11. Orchestrator → marks run complete
```

### Flow 4 — Internal agent-to-agent call (within same company)

```
Agent A wants to call Agent B (both at Acme Inc)

1. Agent A → POST https://internal/a2a/agt_b/message/send
            Headers: X-Company: acme, X-Caller-Agent: agt_a
2. Orchestrator → validates A and B in same company
3. Orchestrator → routes to Agent B
4. Agent B → processes, returns result
5. Audit log entry: { from: agt_a, to: agt_b, status: ok }
```

### Flow 5 — Cross-Company Agent Call (the key feature)

```
Agent A at Acme wants to call Agent B at Partner Inc

1. Agent A's owner (Acme) → POST /v1/federation/invite (to Partner)
2. Partner accepts → POST /v1/federation/trust         → trust_id
3. Agent A → GET /v1/federation/discover?capability=...
4. Discovery returns Partner's public Agent B card
5. Agent A → POST https://api.partner.com/a2a/agt_b/message/send
            Authorization: Bearer <signed JWT>
            JWT claims: { iss: "acme.com", sub: "agt_a", aud: "partner.com" }
6. Partner's orchestrator verifies JWT signature
7. Partner checks trust relationship is active
8. Partner checks Agent B's allowed_companies list
9. Agent B → processes task, returns result
10. Both sides log the cross-company call to audit log
```

### Flow 6 — Agent Discovery Across Companies

```
1. User at Acme → GET /v1/federation/discover?capability=code-review
2. Orchestrator queries federation registry
3. Returns all public agents matching capability
4. User picks one → adds to their pipeline as external step
```

---

## 10. Cross-Company Federation Protocol (Detailed)

This is what makes the product defensible. Each step matters.

### Trust Establishment
- Companies must explicitly trust each other before agents can communicate
- Trust is configurable: which of my agents can be called by you, rate limits, allowed times
- Either side can revoke trust instantly

### Agent Identity
- Every agent has a cryptographic identity (key pair)
- Public key included in the Agent Card
- All cross-company calls are signed with the caller's private key

### Authentication
- JWT-based with short-lived tokens (5 min default)
- Token includes: `iss` (caller company), `sub` (caller agent), `aud` (target company), `exp`
- Receiver verifies signature using the federation registry's published keys

### Audit Log
- Every cross-company call is logged on both sides
- Includes: timestamp, caller agent, target agent, input hash, output hash, cost
- Visible to both companies' admins (provides accountability)

### Rate Limits & Cost
- Each trust relationship has a rate limit
- Caller pays for the LLM cost on their side
- Optional: caller can be billed by the callee for specialized agent usage

---

## 11. Authentication & Security

| Auth Type | When Used |
|---|---|
| **JWT (user)** | User logs into the platform |
| **API Key** | Programmatic access (CI, scripts) |
| **Agent JWT** | Agent-to-agent calls within company |
| **Federation JWT** | Cross-company agent calls (signed) |
| **mTLS (optional)** | High-security partners |

All endpoints require auth. All cross-company traffic is encrypted in transit. Sensitive config (API keys, secrets) is encrypted at rest using AES-256.

---

## 12. Week-by-Week Plan

### Week 1 — Setup & A2A Fundamentals
**Deliverable:** Working dev env. A sample A2A agent running on `localhost:8000`.
- Read full A2A v1.0 spec
- Set up monorepo structure
- Install Python 3.11, `a2a-sdk`, `google-adk`, FastAPI
- Run Google's official A2A samples
- Stand up Postgres + Redis via Docker Compose

### Week 2 — Your First A2A Agent
**Deliverable:** An "Echo Agent" any A2A client can talk to.
- Implement `/.well-known/agent.json`
- Implement `/a2a/{id}/message/send` (JSON-RPC)
- Implement `/a2a/{id}/message/stream` (SSE)
- Basic task storage in Postgres

### Week 3 — Base Agent SDK + Orchestrator API skeleton
**Deliverable:** `BaseAgent` Python class + control plane API stubs.
- `BaseAgent` class with lifecycle hooks
- Build `POST /v1/agents`, `GET /v1/agents`, etc. (CRUD)
- Auth: register, login, JWT issuance
- API key management

### Week 4 — Agent Runtime + Deployment
**Deliverable:** Agents can be deployed and run dynamically.
- `POST /v1/agents/{id}/deploy` spins up an agent process
- Managed runtime: Docker containers per agent
- Health checks, logs, restart on crash
- Status endpoint reports actual state

### Week 5 — LLM Integration + Pipeline Engine
**Deliverable:** Agents call LLMs to think. Pipelines run.
- LiteLLM multi-provider client (Anthropic, Ollama, OpenAI)
- Per-agent `provider` + `model` config
- System prompt config
- `POST /v1/pipelines` + `POST /v1/pipelines/{id}/run`
- Sequential pipeline executor

### Week 6 — Coder Agent
**Deliverable:** A real agent that writes code from prompts.
- Coder system prompt
- Tools: `file_read`, `file_write`, `run_tests`, `git_diff`
- Test on real task: "add a Flask login endpoint"

### Week 7 — Reviewer Agent + Loop Logic
**Deliverable:** 2-agent pipeline with feedback loop.
- Reviewer system prompt + scoring output
- Pipeline `loop_until` logic
- End-to-end test: Coder → Reviewer → approved code

### Week 8 — Jira Agent + Full MVP Pipeline
**Deliverable:** Full 3-agent dev pipeline working end-to-end.
- Jira API integration
- Jira agent: create/update tickets
- Run pipeline against a real Jira instance

### Week 9 — Cross-Company Federation Foundations
**Deliverable:** Agent A at Company 1 can call Agent B at Company 2.
- Federation registry service
- Public agent card hosting
- `GET /v1/federation/discover`
- Cross-company call routing

### Week 10 — Auth, Trust & Security
**Deliverable:** Secure federation, ready for real partners.
- Trust relationship CRUD
- JWT signing/verification across companies
- Rate limits per trust pair
- Audit log of all federation calls

### Week 11 — Persistence, Observability & Reliability
**Deliverable:** Production-grade infrastructure.
- All entities persisted to Postgres
- Redis-based task queue
- Structured logging
- Prometheus metrics
- OpenTelemetry traces

### Week 12 — Deployment & Testing
**Deliverable:** Live, deployed, demoable API.
- Dockerize all services
- Deploy to Railway / Fly.io
- Public demo endpoint
- Full integration test suite
- Auto-generated API docs (FastAPI → OpenAPI)
- README + quickstart guide

---

## 13. Success Criteria (end of Week 12)

- [ ] 3-agent dev pipeline runs end-to-end on a real Jira board
- [ ] Two separate test "companies" can discover each other's agents and exchange tasks
- [ ] API is deployed publicly with full OpenAPI documentation
- [ ] A new developer can build their own agent in under an hour following the docs
- [ ] At least 2 real design partners (dev teams) testing the system

---

## 14. After Week 12 (Next Phase Preview)

- Visual UI for building agents and pipelines (drag-and-drop)
- Pre-built agent marketplace (templates)
- Billing + multi-tenant accounts + Stripe integration
- More agents: Designer, QA, DevOps, Sales, Support
- More integrations: Slack, GitHub, Linear, Notion
- Industry-specific agent templates
- Mobile app for monitoring pipelines

---

## 15. Open Questions (Decide Along the Way)

- Monorepo or polyrepo?
- Self-hosted only, or also offer hosted version from day 1?
- Should agents persist memory across runs? (probably yes)
- How do we handle long-running tasks (hours/days)?
- Pricing model — per agent run? Per seat? Per company?
- Open-source the SDK, keep the orchestrator closed?

---

## 16. Notes

- **Don't get stuck on perfection.** Each week's deliverable should work, not be pretty.
- **Demo every week.** Record a 2-minute video. Builds momentum and proof.
- **Talk to 1 dev team per week** while building. Cheapest validation possible.
- **Cross-company federation is the moat.** Don't deprioritize it.
- **The API is the product.** Design it as if devs will read it.
