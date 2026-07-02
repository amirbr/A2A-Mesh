# A2A-Mesh — Progress Log

> Update this after every coding session. This is the source of truth for "where are we."
> Format: check the boxes as tasks complete. Add a date when a week starts/ends.
> Claude Code should read this at the start of every session to know where we are.

---

## Current Status

- **Current week:** Week 1 (setup & A2A fundamentals)
- **Last session:** 2026-06-26
- **Next session goal:** Week 2 — Echo Agent (Agent Card, message/send, message/stream, tasks/get)
- **Blockers:** Docker Desktop not installed — need it to run Postgres + Redis for integration tests
- **Open questions:** None

---

## Week 0 — Project Setup (before Week 1)

Started: 2026-06-26
Finished: 2026-06-26

### Section A: Repo + docs
- [x] Create GitHub repo `A2A-Mesh`, clone to local
- [x] Drop in all docs (CLAUDE.md, PLAN.md, PROGRESS.md, ARCHITECTURE.md, FINANCIAL_PROJECTION.md, README.md)
- [x] Committed: `chore: initial project setup`

### Section B: Python project + deps + folder structure
- [x] `.gitignore` created
- [x] `pyproject.toml` — uv 0.11.24, Python 3.11.15, 79 packages installed
- [x] `.env.example` created
- [x] Full folder structure per CLAUDE.md §4 — all dirs + `__init__.py` stubs
- [x] Skeleton files: `main.py`, `config.py`, `logging.py`, `tests/conftest.py`
- [x] Tests passing: `GET /health → 200`
- [ ] Get Anthropic API key, add to local `.env` ← **you do this**
- [x] Committed: `chore(week-0/python-setup): pyproject.toml, deps, folder structure, health endpoint`

---

## Week 1 — Setup & A2A Fundamentals

Started: 2026-06-26
Finished: 2026-06-26
**Goal:** Working dev environment. FastAPI + Postgres + Redis all connected and tested.

### Section A: docker-compose + DB + Redis
- [x] `docker-compose.yml` — Postgres 15 (port 5435), Redis 7 (port 6379), test DB (port 5436)
- [x] `db/base.py` — SQLAlchemy DeclarativeBase with `id`/`created_at`/`updated_at`
- [x] `db/session.py` — async session factory + `get_db` FastAPI dependency
- [x] `core/redis.py` — async Redis client singleton with shutdown hook
- [x] `/health` endpoint — returns `{status, db, redis}` with live checks
- [x] Tests passing: 3/3 including integration (DB + Redis confirmed live)
- [x] Committed: `feat(week-1/infra): docker-compose, db session, redis client, /health endpoint`

### Section B: Alembic + A2A spec notes
- [x] `alembic.ini` + `alembic/env.py` — async Alembic wired to `config.settings`
- [x] `docs/a2a-notes.md` — Agent Card format, JSON-RPC 2.0, Task lifecycle, all 4 methods, Part types
- [x] Committed: `docs(week-1/a2a-spec): alembic setup and a2a protocol notes`

### Section C: Connection verification + Google A2A sample
- [x] Postgres confirmed from Python — PostgreSQL 15.18 on port 5435
- [x] Redis confirmed from Python — Redis 7.4.9 on port 6379
- [x] `scripts/run_echo_sample.py` — working A2A agent using `a2a-sdk` v1.1
  - `GET /.well-known/agent-card.json` — AgentCard with skills served
  - `POST /` with `SendMessage` (JSON-RPC, `A2A-Version: 1.0` header) — echoes back text
  - Key learnings: method is `SendMessage` not `message/send`; agent card at `/.well-known/agent-card.json`; `Message` response for immediate replies
- [x] Tests: 3/3 passing
- [ ] Commit: `feat: postgres/redis connection verification and a2a echo sample`

- **Ports note:** System has pgAdmin Postgres 16/18 on 5432/5433 — our containers use 5435/5436/6379
- **Demo:** `uv run pytest tests/ -v` → 3/3; `uv run python scripts/run_echo_sample.py` → live A2A agent

---

## Week 2 — First A2A Agent (Echo Agent)

Started: 2026-06-26
Finished: ____
**Goal:** An A2A-compliant Echo Agent that any A2A client can talk to.

### Section A: Echo Agent in main app
- [x] `src/a2a_mesh/agents/echo.py` — EchoAgentExecutor + build_echo_routes()
- [x] `src/a2a_mesh/main.py` — mount agent card + JSON-RPC routes via a2a-sdk
- [x] `GET /.well-known/agent-card.json` — AgentCard with skills
- [x] `POST /a2a/echo/` — SendMessage (JSON-RPC, A2A-Version: 1.0)
- [x] `tests/test_api/test_echo_agent.py` — 8 tests (agent card + send message happy/error paths)
- [x] 11/11 tests passing
- [ ] Commit: `feat: echo agent wired into main app with agent card and json-rpc`

### Section B: Postgres task storage
- [x] `src/a2a_mesh/db/models/task.py` — TaskRecord model (id, context_id, agent_id, state, data as JSON)
- [x] `alembic/script.py.mako` — migration template (was missing)
- [x] `alembic/versions/*_create_tasks_table.py` — migration applied to DB
- [x] `src/a2a_mesh/db/task_store.py` — PostgresTaskStore implementing TaskStore ABC
- [x] `src/a2a_mesh/agents/echo.py` — switched from InMemoryTaskStore to PostgresTaskStore
- [x] `src/a2a_mesh/db/session.py` — NullPool in test mode (fixes cross-event-loop asyncpg issues)
- [x] `tests/conftest.py` — APP_ENV=test set before app import
- [x] 11/11 tests passing
- [ ] Commit: `feat: postgres task store, tasks table migration, echo agent persists tasks`

---

## Week 3 — Base Agent SDK + Orchestrator API Skeleton

Started: 2026-06-29
Finished: ____
**Goal:** Reusable BaseAgent class. Control plane API stubs.

### Section A: DB models + migrations
- [x] `core/ids.py` — prefixed ID generators (co_, usr_, agt_, etc.)
- [x] `db/models/company.py`, `user.py`, `agent.py` — SQLAlchemy models
- [x] `db/models/__init__.py` — central model registry (fixes SQLAlchemy relationship resolution)
- [x] Alembic migration: companies, users, agents tables created
- [x] 21/21 tests passing
- [ ] Commit: `feat: company, user, agent db models and migration`

### Section B: Auth — register, login, JWT, API keys
- [x] `core/errors.py` — typed HTTP exceptions (AuthError, NotFoundError, ConflictError, etc.)
- [x] `core/auth.py` — argon2 password hashing, JWT create/decode, API key generation
- [x] `db/models/api_key.py` — ApiKey model + migration
- [x] `api/v1/auth.py` — POST /v1/auth/register, /login, /api-keys (create/list/revoke)
- [x] `main.py` — custom HTTP exception handler (returns `{"error":...}` directly)
- [x] `conftest.py` — test DB isolation: uses port 5436, truncates tables between tests
- [x] 21/21 tests passing
- [ ] Commit: `feat: auth endpoints — register, login, jwt, api keys`

### Section C: Agent CRUD API
- [x] `api/v1/agents.py` — POST/GET/PATCH/DELETE /v1/agents, scoped to company, auth required
- [x] `tests/test_api/test_agents.py` — 13 tests (create, list, get, update, delete + auth/scope checks)
- [x] 34/34 tests passing
- [ ] Commit: `feat: agent crud api — create, list, get, update, delete`

### Section D: BaseAgent class
- [x] `agents/base.py` — BaseAgent(AgentExecutor, ABC) with AgentConfig, SkillConfig, lifecycle hooks (on_start/on_stop/on_error), build_agent_card(), build_routes()
- [x] `agents/echo.py` — refactored to extend BaseAgent, process() as single override
- [x] 34/34 tests passing
- [ ] Commit: `feat: baseagent class with lifecycle hooks and config`

---

## Week 4 — Agent Runtime + Deployment

Started: 2026-06-30
Finished: ____
**Goal:** Agents can be deployed and run dynamically.
**Decision:** In-process registry (not Docker per agent). Same API surface; Docker-per-agent is post-MVP when we have real workload isolation requirements.

### Section A: Registry + deploy/stop/status/logs endpoints
- [x] `orchestrator/registry.py` — in-memory agent registry (register/unregister/get/list)
- [x] `agents/generic.py` — GenericAgent driven by system_prompt config (stub, LLM in Week 5)
- [x] `api/v1/runtime.py` — POST /v1/agents/{id}/deploy, /stop, GET /status, /logs
- [x] `main.py` — runtime router registered
- [x] `tests/test_api/test_runtime.py` — 9 tests covering deploy, stop, status, logs
- [x] 43/43 tests passing
- [ ] Commit: `feat: agent runtime — deploy, stop, status endpoints and in-process registry`

### Section B: Dynamic A2A routing + smoke test update
- [x] `api/a2a/dispatch.py` — POST /a2a/{agent_id}/ (JSON-RPC dispatch), GET /a2a/{agent_id}/.well-known/agent-card.json
- [x] Route ordering fixed: echo's static routes registered before dynamic dispatch so /a2a/echo/ isn't shadowed
- [x] `tests/test_api/test_dispatch.py` — 5 tests (not deployed 404, deployed response, unsupported method, agent card)
- [x] `scripts/smoke_test.sh` — extended with deploy/stop/status/logs/dispatch/agent-card checks
- [x] 48/48 tests passing
- [ ] Commit: `feat: dynamic a2a dispatch — deployed agents callable at /a2a/{id}/`

---

## Week 5 — Claude Integration + Pipeline Engine

Started: ____
Finished: ____
**Goal:** Agents use Claude to think. Pipelines run.

- [ ] Implement `llm/claude.py` — Anthropic API wrapper
- [ ] Add Claude client to `BaseAgent` (system prompt, model config)
- [ ] Add tool calling support
- [ ] Token usage + cost tracking per task
- [ ] Implement `POST /v1/pipelines` (CRUD)
- [ ] Implement `POST /v1/pipelines/{id}/run`
- [ ] Sequential pipeline executor (Coder → Reviewer mock for now)
- [ ] Tests
- **Demo at end of week:** Pipeline runs 2 LLM-powered agents in sequence

---

## Week 6 — Coder Agent

Started: ____
Finished: ____
**Goal:** A real agent that writes code from prompts.

- [ ] Coder agent system prompt
- [ ] Tools: `file_read`, `file_write`, `run_tests`, `git_diff`
- [ ] Workspace isolation (sandbox per task)
- [ ] Tests for each tool
- [ ] End-to-end test: "add a Flask login endpoint" → working code
- **Demo at end of week:** Coder generates real code for a real task

---

## Week 7 — Reviewer Agent + Loop Logic

Started: ____
Finished: ____
**Goal:** 2-agent pipeline with feedback loop.

- [ ] Reviewer agent system prompt
- [ ] Reviewer scoring output schema (`approved: bool`, `feedback: str`)
- [ ] Pipeline `loop_until` logic + `max_iterations` cap
- [ ] End-to-end test: Coder ↔ Reviewer until approved
- **Demo at end of week:** Full Coder ↔ Reviewer loop produces approved code

---

## Week 8 — Jira Agent + Full MVP Pipeline

Started: ____
Finished: ____
**Goal:** Full 3-agent dev pipeline working end-to-end.

- [ ] Jira API integration (auth, create issue, update issue, transition)
- [ ] Jira agent system prompt + tools
- [ ] Full pipeline: Coder → Reviewer → Jira
- [ ] Test against a real Jira instance
- **Demo at end of week:** Real task → code → review → Jira ticket created. MVP complete.

---

## Week 9 — Cross-Company Federation Foundations

Started: ____
Finished: ____
**Goal:** Agent A at Company 1 can call Agent B at Company 2.

- [ ] Federation registry service
- [ ] Public Agent Card hosting per company namespace
- [ ] Implement `GET /v1/federation/discover`
- [ ] Cross-company call routing logic
- [ ] Test with two local "companies"
- **Demo at end of week:** Two test companies discover each other's agents

---

## Week 10 — Auth, Trust & Security

Started: ____
Finished: ____
**Goal:** Secure federation, ready for real partners.

- [ ] Trust relationship CRUD (`POST/GET/DELETE /v1/federation/trust`)
- [ ] Federation JWT signing (per-company key pairs)
- [ ] Federation JWT verification on receiving agent
- [ ] Rate limits per trust pair
- [ ] Audit log of every cross-company call
- [ ] `allowed_companies` enforcement on agents
- **Demo at end of week:** Cross-company call works with full auth + audit

---

## Week 11 — Persistence, Observability & Reliability

Started: ____
Finished: ____
**Goal:** Production-grade infrastructure.

- [ ] All entities persisted to Postgres (no in-memory state)
- [ ] Redis-based task queue (Celery)
- [ ] Structured JSON logging
- [ ] Prometheus metrics endpoint
- [ ] OpenTelemetry traces across agent calls
- [ ] Retry + dead-letter queue
- **Demo at end of week:** System survives restart, debuggable in production

---

## Week 12 — Deployment & Testing

Started: ____
Finished: ____
**Goal:** Live, deployed, demoable API.

- [ ] Dockerize all services
- [ ] Deploy to Railway or Fly.io
- [ ] Public demo endpoint live
- [ ] Full integration test suite
- [ ] Auto-generated API docs via FastAPI
- [ ] Update README with quickstart
- [ ] Record 5-minute demo video
- **Demo at end of week:** A stranger can use the API following just the README.

---

## Session Log

> Add a brief entry after every session. Keeps history visible.

| Date | Week.Day | What got done | Next |
|---|---|---|---|
| 2026-06-26 | W0.D1 | .gitignore, pyproject.toml, uv+Python 3.11, all deps, folder structure, main.py/config.py/logging.py, first test passing | Week 1 |
| 2026-06-26 | W1.D1 | docker-compose.yml, alembic setup, db/session.py, db/base.py, core/redis.py, /health with DB+Redis check, docs/a2a-notes.md, 2 tests passing | Install Docker Desktop, then Week 2 (Echo Agent) |

---

## Decisions Log

> Document non-obvious technical decisions here so we don't second-guess them later.

| Date | Decision | Why |
|---|---|---|
| _yyyy-mm-dd_ | Modular monolith, not microservices | Speed of iteration; split later if pain demands |
| _yyyy-mm-dd_ | Postgres for queues, not Kafka | MVP scale; add Kafka post-Series A |
|  |  |  |

---

## Customer Conversations Log

> Talk to 1 dev team per week. Track every conversation here. This is more important than code.

| Date | Company / person | Insight | Action |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |
