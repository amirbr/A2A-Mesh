# A2A-Mesh — Progress Log

> Update this after every coding session. This is the source of truth for "where are we."
> Format: check the boxes as tasks complete. Add a date when a week starts/ends.
> Claude Code should read this at the start of every session to know where we are.

---

## Current Status

- **Current week:** Week 0 (project setup)
- **Last session:** —
- **Next session goal:** Set up repo, install deps, run first FastAPI hello world
- **Blockers:** None
- **Open questions:** None

---

## Week 0 — Project Setup (before Week 1)

Started: ____
Finished: ____

- [ ] Create GitHub repo `A2A-Mesh`
- [ ] Clone to local machine
- [ ] Drop in all docs (CLAUDE.md, PLAN.md, PROGRESS.md, ARCHITECTURE.md, FINANCIAL_PROJECTION.md, README.md)
- [ ] Initialize Python project with `uv init` or `pyproject.toml`
- [ ] Install core deps: fastapi, uvicorn, sqlalchemy, asyncpg, pydantic, anthropic, a2a-sdk
- [ ] Create `.env.example` and `.gitignore`
- [ ] Create folder structure per CLAUDE.md Section 4
- [ ] Get Anthropic API key, add to local `.env`
- [ ] First commit: `chore: initial project setup`

---

## Week 1 — Setup & A2A Fundamentals

Started: ____
Finished: ____
**Goal:** Working dev environment. Sample A2A agent running on localhost.

- [ ] Read full A2A v1.0 spec, take notes in `docs/a2a-notes.md`
- [ ] Clone and run Google's official A2A sample agents
- [ ] Inspect Agent Card JSON format and JSON-RPC message format
- [ ] Set up `docker-compose.yml` with Postgres + Redis
- [ ] Confirm Postgres connection from Python
- [ ] Confirm Redis connection from Python
- [ ] Write a "hello world" FastAPI app that returns `{"status": "ok"}`
- [ ] Set up `ruff`, `mypy`, `pytest` configs in `pyproject.toml`
- [ ] Run first test
- **Demo at end of week:** Sample A2A agent running, FastAPI serving on :8000

---

## Week 2 — First A2A Agent (Echo Agent)

Started: ____
Finished: ____
**Goal:** An A2A-compliant Echo Agent that any A2A client can talk to.

- [ ] Define Agent Card spec for Echo Agent
- [ ] Implement `GET /.well-known/agent.json`
- [ ] Implement `POST /a2a/{agent_id}/message/send` (JSON-RPC)
- [ ] Implement `POST /a2a/{agent_id}/message/stream` (SSE streaming)
- [ ] Implement `GET /a2a/{agent_id}/tasks/{task_id}`
- [ ] Basic in-memory task storage
- [ ] Test with Google's reference A2A client
- [ ] Write tests for each endpoint
- **Demo at end of week:** External client sends "hello", agent echoes back

---

## Week 3 — Base Agent SDK + Orchestrator API Skeleton

Started: ____
Finished: ____
**Goal:** Reusable BaseAgent class. Control plane API stubs.

- [ ] Set up Postgres tables: companies, users, agents (Alembic migrations)
- [ ] Implement `BaseAgent` class with lifecycle hooks
- [ ] Move task storage from memory to Postgres
- [ ] Implement `POST /v1/auth/register`
- [ ] Implement `POST /v1/auth/login` (JWT issuance)
- [ ] Implement `POST /v1/auth/api-keys` (create/list/revoke)
- [ ] Implement `POST /v1/agents` (CRUD)
- [ ] Implement `GET /v1/agents`
- [ ] Implement `GET /v1/agents/{id}`
- [ ] Implement `PATCH /v1/agents/{id}`
- [ ] Implement `DELETE /v1/agents/{id}`
- [ ] Tests for all of the above
- **Demo at end of week:** Can register a company, create an agent via API

---

## Week 4 — Agent Runtime + Deployment

Started: ____
Finished: ____
**Goal:** Agents can be deployed and run dynamically.

- [ ] Implement `POST /v1/agents/{id}/deploy`
- [ ] Spin up agents as Docker containers (managed runtime)
- [ ] Implement `POST /v1/agents/{id}/stop`
- [ ] Implement `GET /v1/agents/{id}/status` (real health check)
- [ ] Implement `GET /v1/agents/{id}/logs`
- [ ] Health check loop / supervisor
- [ ] Restart on crash
- [ ] Tests
- **Demo at end of week:** Deploy Echo Agent dynamically via API, then stop it

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
| _yyyy-mm-dd_ | W0.D1 | _example: created repo, dropped in docs_ | _Install deps_ |
|  |  |  |  |
|  |  |  |  |

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
