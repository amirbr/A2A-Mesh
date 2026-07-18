# A2A-Mesh — Progress Log

> Update this after every coding session. This is the source of truth for "where are we."
> Format: check the boxes as tasks complete. Add a date when a week starts/ends.
> Claude Code should read this at the start of every session to know where we are.

---

## Current Status

- **Current week:** Week 7 (Reviewer Agent + Loop Logic — complete, Sections A/B done)
- **Last session:** 2026-07-18
- **Next session goal:** Week 8 — Jira agent + full 3-agent MVP pipeline (Coder → Reviewer → Jira)
- **Blockers:** None known. Docker daemon must be running locally before integration tests (`docker compose up`).
- **Open questions:** None open for Week 7. Week 8 needs a real Jira instance/credentials to
  test against (see PLAN.md Week 8 goal) — flag before starting if not available yet.
- **Doc note (2026-07-09):** Weeks 1–5 checkboxes below were back-filled from `git log` — this file wasn't updated after Week 2 for a while even though the work kept shipping. Keep it current going forward.

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
- [x] Committed: `28346b0 feat: postgres/redis connection verification and a2a echo sample`

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
- [x] Committed: `9420005 feat: echo agent wired into main app with agent card and json-rpc`

### Section B: Postgres task storage
- [x] `src/a2a_mesh/db/models/task.py` — TaskRecord model (id, context_id, agent_id, state, data as JSON)
- [x] `alembic/script.py.mako` — migration template (was missing)
- [x] `alembic/versions/*_create_tasks_table.py` — migration applied to DB
- [x] `src/a2a_mesh/db/task_store.py` — PostgresTaskStore implementing TaskStore ABC
- [x] `src/a2a_mesh/agents/echo.py` — switched from InMemoryTaskStore to PostgresTaskStore
- [x] `src/a2a_mesh/db/session.py` — NullPool in test mode (fixes cross-event-loop asyncpg issues)
- [x] `tests/conftest.py` — APP_ENV=test set before app import
- [x] 11/11 tests passing
- [x] Committed: `b841cce feat: postgres task store, tasks table migration, echo agent persists tasks`

---

## Week 3 — Base Agent SDK + Orchestrator API Skeleton

Started: 2026-06-29
Finished: 2026-06-30
**Goal:** Reusable BaseAgent class. Control plane API stubs.

### Section A: DB models + migrations
- [x] `core/ids.py` — prefixed ID generators (co_, usr_, agt_, etc.)
- [x] `db/models/company.py`, `user.py`, `agent.py` — SQLAlchemy models
- [x] `db/models/__init__.py` — central model registry (fixes SQLAlchemy relationship resolution)
- [x] Alembic migration: companies, users, agents tables created
- [x] 21/21 tests passing
- [x] Committed: `14cc943 feat: company, user, agent db models and migration`

### Section B: Auth — register, login, JWT, API keys
- [x] `core/errors.py` — typed HTTP exceptions (AuthError, NotFoundError, ConflictError, etc.)
- [x] `core/auth.py` — argon2 password hashing, JWT create/decode, API key generation
- [x] `db/models/api_key.py` — ApiKey model + migration
- [x] `api/v1/auth.py` — POST /v1/auth/register, /login, /api-keys (create/list/revoke)
- [x] `main.py` — custom HTTP exception handler (returns `{"error":...}` directly)
- [x] `conftest.py` — test DB isolation: uses port 5436, truncates tables between tests
- [x] 21/21 tests passing
- [x] Committed: `649a929 feat: auth endpoints — register, login, jwt, api keys`

### Section C: Agent CRUD API
- [x] `api/v1/agents.py` — POST/GET/PATCH/DELETE /v1/agents, scoped to company, auth required
- [x] `tests/test_api/test_agents.py` — 13 tests (create, list, get, update, delete + auth/scope checks)
- [x] 34/34 tests passing
- [x] Committed: `bf5559a feat: agent crud api — create, list, get, update, delete`

### Section D: BaseAgent class
- [x] `agents/base.py` — BaseAgent(AgentExecutor, ABC) with AgentConfig, SkillConfig, lifecycle hooks (on_start/on_stop/on_error), build_agent_card(), build_routes()
- [x] `agents/echo.py` — refactored to extend BaseAgent, process() as single override
- [x] 34/34 tests passing
- [x] Committed: `e14ed0d feat: baseagent class with lifecycle hooks and config`

---

## Week 4 — Agent Runtime + Deployment

Started: 2026-06-30
Finished: 2026-07-02
**Goal:** Agents can be deployed and run dynamically.
**Decision:** In-process registry (not Docker per agent). Same API surface; Docker-per-agent is post-MVP when we have real workload isolation requirements.

### Section A: Registry + deploy/stop/status/logs endpoints
- [x] `orchestrator/registry.py` — in-memory agent registry (register/unregister/get/list)
- [x] `agents/generic.py` — GenericAgent driven by system_prompt config (stub, LLM in Week 5)
- [x] `api/v1/runtime.py` — POST /v1/agents/{id}/deploy, /stop, GET /status, /logs
- [x] `main.py` — runtime router registered
- [x] `tests/test_api/test_runtime.py` — 9 tests covering deploy, stop, status, logs
- [x] 43/43 tests passing
- [x] Committed: `dada1c2 feat: agent runtime and dynamic a2a dispatch`

### Section B: Dynamic A2A routing + smoke test update
- [x] `api/a2a/dispatch.py` — POST /a2a/{agent_id}/ (JSON-RPC dispatch), GET /a2a/{agent_id}/.well-known/agent-card.json
- [x] Route ordering fixed: echo's static routes registered before dynamic dispatch so /a2a/echo/ isn't shadowed
- [x] `tests/test_api/test_dispatch.py` — 5 tests (not deployed 404, deployed response, unsupported method, agent card)
- [x] `scripts/smoke_test.sh` — extended with deploy/stop/status/logs/dispatch/agent-card checks
- [x] 48/48 tests passing
- [x] Committed: `dada1c2 feat: agent runtime and dynamic a2a dispatch` (same commit as Section A)

### Section C: Health check endpoint
- [x] `GET /v1/agents/{id}/health` — pings agent's process(), returns healthy/unhealthy + latency_ms
- [x] Not-deployed agents return healthy=false, latency_ms=null
- [x] Failed health check marks agent status as "error" in DB
- [x] Tests: health not deployed, health deployed
- [x] Committed: `8414dd2 feat: week 4 agent runtime — deploy, stop, health, restart, dynamic a2a dispatch`

### Section D: Crash recovery — restart endpoint + on_error DB marking
- [x] `GenericAgent.on_error()` — marks agent status="error" in DB and unregisters from registry on crash
- [x] `POST /v1/agents/{id}/restart` — stops existing instance (if any), redeploys fresh instance
- [x] `agent_db_id` threaded through `_build_agent_instance` → `GenericAgent.__init__`
- [x] Tests: restart stopped agent, restart running agent replaces instance
- [x] 52/52 tests passing
- [x] Committed: `8414dd2 feat: week 4 agent runtime — deploy, stop, health, restart, dynamic a2a dispatch` (same commit as Section C)

---

## Week 5 — LLM Integration + Pipeline Engine

Started: 2026-07-02
Finished: 2026-07-04
**Goal:** Agents use an LLM to think. Pipelines run.

### Section A: Claude API wrapper + GenericAgent wired to Claude
- [x] `llm/claude.py` — async Anthropic wrapper: complete(system_prompt, user_message, model, ...) → str
- [x] `agents/generic.py` — process() now calls claude.complete() instead of stub
- [x] `tests/conftest.py` — global `mock_claude` autouse fixture (no test ever hits real API)
- [x] `tests/test_agents/test_generic_agent.py` — 4 tests (calls claude, empty message, error propagation, system prompt used)
- [x] 56/56 tests passing
- [x] Committed as part of `4cabbbf` (see Section D — superseded same day, see note below)

### Section B: Pipeline DB model + CRUD API
- [x] `db/models/pipeline.py` — Pipeline + PipelineRun models
- [x] `db/models/__init__.py` — Pipeline + PipelineRun registered
- [x] Alembic migration: pipelines + pipeline_runs tables created
- [x] `api/v1/pipelines.py` — POST/GET/PATCH/DELETE /v1/pipelines, scoped to company
- [x] Tests: create, list, get, update, delete, auth required
- [x] Committed as part of `4cabbbf`

### Section C: Pipeline executor
- [x] `orchestrator/engine.py` — run_pipeline(): sequential steps, pipes output to next agent
- [x] `POST /v1/pipelines/{id}/run` — executes pipeline, returns completed/failed run
- [x] `GET /v1/pipelines/{id}/runs/{run_id}` — fetch run status and output
- [x] Tests: success, agent not deployed → failed run, no steps → 422, two-step pipeline, get run status
- [x] 68/68 tests passing
- [x] Committed as part of `4cabbbf`

### Section D: LiteLLM multi-provider dispatch (replaces Section A's Claude-only wrapper)
- [x] `llm/dispatch.py` — replaces `llm/claude.py`; unified `complete()` over LiteLLM
- [x] Supports `provider: "anthropic" | "ollama" | "openai"` — any LiteLLM-supported provider works by passing the right `provider`/`model` string, no code changes needed
- [x] `agents/generic.py` — now calls `dispatch.complete()` instead of `claude.complete()`
- [x] Tests updated to mock `litellm.acompletion`
- [x] Committed: `4cabbbf feat: litellm multi-provider dispatch replacing claude and ollama wrappers`

**Not done in Week 5 (still open, not yet scheduled):** tool-calling support and token usage / cost tracking per task. Tool-calling is being pulled into Week 6 below (see MCP note). Cost tracking is still unscheduled — flag before Week 9 federation work, since `cost_limit_usd` and usage billing depend on it.

---

## Week 6 — Coder Agent + Tool Use (built-in tools + MCP)

Started: 2026-07-13
Finished: 2026-07-15
**Goal:** A real agent that writes code from prompts, and a tool-calling loop any agent can use —
including calling out to external MCP servers (e.g. Jira).

**Why MCP got added here (2026-07-09):** `mcp_servers` has been in the documented `AgentConfig`
schema since Week 0 (`ARCHITECTURE.md` §5, `PLAN.md` §7) but was never on the week-by-week plan
and isn't wired to anything in code — `AgentConfig` (`agents/base.py`) has no `tools` or
`mcp_servers` field, and `llm/dispatch.complete()` does single-shot completion only, no
function-calling loop. Built-in tools (`file_read`, etc.) and MCP-provided tools need the same
underlying mechanism, so build the loop once here and support both.

### Section A: Tool-calling loop in the LLM dispatch layer
- [x] `llm/dispatch.run_with_tools()` — new function alongside `complete()`; loops on LiteLLM's
      function-calling interface (tool_choice="auto") until the model returns a final text
      answer, executing each tool call via a caller-supplied async `tool_executor(name, args)`
      and feeding the result back as a `role: tool` message; raises `RuntimeError` past
      `max_iterations` (default 5) with no final answer
- [x] `AgentConfig` (`agents/base.py`) gains `tools: list[str] = []` and
      `mcp_servers: list[str] = []` — data only, not wired to GenericAgent yet (Section B/C)
- [x] `tests/test_llm/test_dispatch.py` — 4 tests: `complete()` sends no `tools` kwarg and is
      unaffected (no regression), `run_with_tools()` returns immediately with no tool calls,
      round-trips a tool call → tool result → final answer, raises past `max_iterations`
- [x] 73/73 tests passing
- [x] Committed: `9cab7f1 feat: tool-calling loop in llm dispatch, tools/mcp_servers config fields`

### Section B: Built-in tools
- [x] `agents/tools.py` — `Workspace` (sandboxed dir, rejects path-escape reads/writes) +
      `file_read`, `file_write`, `run_tests` (real `pytest` subprocess via `sys.executable -m
      pytest`, 30s timeout), `git_diff`; `execute_builtin_tool()` dispatcher never raises —
      returns `"Error: ..."` strings so the model can see and react to tool failures
- [x] `agents/generic.py` — `GenericAgent._process_with_tools()`: when `config.tools` is
      non-empty, creates a fresh temp-dir `Workspace` per call, runs
      `dispatch.run_with_tools()` against it, and always cleans up the dir in `finally`; empty
      `config.tools` still goes through the original `dispatch.complete()` path unchanged
- [x] `agents/coder.py` — `CODER_SYSTEM_PROMPT` + `build_coder_config()`; the Coder is a
      `GenericAgent` configured with the four built-in tools, not a separate class — matches
      how the runtime already deploys every agent generically
- [x] `api/v1/runtime.py::_build_agent_instance` — now reads `tools`/`mcp_servers` out of the
      DB-stored config JSON, so `POST /v1/agents` with `config: {"tools": [...]}` actually
      reaches the deployed agent
- [x] `tests/test_agents/test_tools.py` — 13 tests: workspace path-escape rejection (relative
      and absolute), file_read/file_write round trip incl. parent-dir creation, missing-file
      error string, run_tests against a real passing and a real failing test, git_diff on a
      non-repo dir, unknown-tool/missing-arg/path-escape dispatch errors
- [x] `tests/test_agents/test_generic_agent.py` — 2 new tests: no-tools agent never touches
      `run_with_tools` (regression guard), tools-configured agent calls `run_with_tools` with
      the right schemas/executor and always calls `shutil.rmtree`
- [x] `tests/test_agents/test_coder_agent.py` — end-to-end test: scripted "add a Flask login
      endpoint" tool-call sequence (file_write ×2, run_tests, final answer) against **real**
      tool execution — a real subprocess `pytest` run confirms "2 passed" in the tool result
      fed back to the model; only the LLM boundary (`litellm.acompletion`) is mocked
- [x] 89/89 tests passing
- [x] Committed: `0dc2539 feat: built-in tools, coder agent config, workspace-isolated tool loop`

### Section C: MCP client support
- [x] **Decided (2026-07-15, user sign-off):** official `mcp` Python SDK, not hand-rolled —
      added `mcp>=1.28.1` to `pyproject.toml` via `uv add mcp`
- [x] `agents/mcp_client.py` — `discover_tools()`/`call_tool()` over the SDK's Streamable HTTP
      transport (`streamable_http_client`, not the deprecated `streamablehttp_client`);
      `discover_tools` raises `McpServerError` on an unreachable/broken server, `call_tool`
      never raises — connection failures come back as `"Error: ..."` text, same pattern as
      `execute_builtin_tool`
- [x] `agents/generic.py::_process_with_tools` — now resolves `config.mcp_servers` into tool
      schemas alongside `config.tools`, in the same flat list the model sees; routes each tool
      call to the built-in dispatcher or the right MCP server transparently
- [x] `api/v1/runtime.py` — `_validate_mcp_servers()` called on `/deploy` and `/restart`;
      unreachable server → `422 validation_error` before the agent ever registers, not a
      silent failure on the agent's first real message
- [x] `tests/conftest.py` — `mock_mcp_server` fixture: a real local MCP server (`FastMCP` +
      `uvicorn`, one `get_weather` tool) bound to a free port, for end-to-end tests
- [x] `tests/test_agents/test_mcp_client.py` — 4 tests: discover real tool schema, call real
      tool and get the real result, unknown-tool error string, unreachable-server raises
      `McpServerError`
- [x] `tests/test_agents/test_generic_agent.py` — end-to-end: agent configured with only
      `mcp_servers` (no built-in tools) calls the real local MCP server's `get_weather` tool
      and the real result reaches the model's final answer (LLM boundary mocked, MCP call is
      real)
- [x] `tests/test_api/test_runtime.py` — deploy rejects an unreachable `mcp_servers` URL
      (422) and accepts a reachable one (200, against the real mock server)
- [x] 96/96 tests passing
- [x] Committed: `c607f25 feat: mcp client integration, deploy-time server validation`
- **Demo at end of week:** Coder generates real code for a real task (Section B), *and* a
  separate agent calls a tool on a local mock MCP server end to end (Section C) — proves the
  Jira case will work once a real Jira MCP server + trust config point at it, no
  Jira-specific code needed

---

## Week 7 — Reviewer Agent + Loop Logic

Started: 2026-07-18
Finished: 2026-07-18
**Goal:** 2-agent pipeline with feedback loop.

### Section A: Reviewer agent
- [x] `agents/reviewer.py` — `REVIEWER_SYSTEM_PROMPT` + `build_reviewer_config()`, same
      `GenericAgent`-config pattern as the Coder (`agents/coder.py`); no tools — it only reads
      the text the pipeline hands it. Prompt requires a JSON-only reply: `{"approved": bool,
      "feedback": str}`, matching the schema decided in the Week 6 progress note and
      `PLAN.md`'s `loop_until: {"field": "approved", "equals": true}` example.
- [x] `agents/coder.py` — system prompt tweak: the Coder's tool workspace is deleted after
      each call (Week 6 design), so its old final answer ("Done. Added login()...") gave the
      Reviewer nothing to review. Prompt now requires the final answer to include the full
      contents of every changed file, labeled by filename.
- [x] `tests/test_agents/test_reviewer_agent.py` — 3 tests: approves valid code, rejects with
      feedback, confirms no tools/mcp_servers configured. Uses the autouse `mock_llm` fixture
      (patches `dispatch.complete` directly) rather than `litellm.acompletion`, since the
      Reviewer has no tools and never enters the tool-calling loop.
- [x] 99/99 tests passing
- [x] Committed: `1861c4c feat: reviewer agent with structured approve/feedback output`

### Section B: Pipeline `loop_until` logic + end-to-end test
- [x] `orchestrator/engine.py` — `run_pipeline` switched from a `for` loop to an index-based
      `while` loop so a step can jump backward. A step with `loop_until: {"field": ...,
      "equals": ...}` parses its own JSON output after running; if the field doesn't match,
      the engine rebuilds the input as `{original task} + reviewer feedback` and re-runs the
      *previous* step, repeating until the condition is met or `max_iterations` (default 3,
      per-step) is exhausted, at which point the run fails with a clear error. First step
      can't have `loop_until` (nothing to loop back to) — raises `ValidationError`.
- [x] `orchestrator/engine.py::_loop_condition_met()` — new helper; raises `ValidationError`
      if the step's output isn't a JSON object, rather than silently treating unparseable
      output as "not approved."
- [x] `api/v1/pipelines.py::StepConfig` — **bug found while testing:** this Pydantic model
      only declared `agent_id`/`name`, so `loop_until`/`max_iterations` sent in
      `POST /v1/pipelines` were silently dropped before ever reaching the engine. Added both
      fields as optional. Also fixed a related bug this exposed: `model_dump()` always
      includes `max_iterations` (as `None` when unset), so `step.get("max_iterations", 3)`
      never fell back to the default — changed to `step.get("max_iterations") or 3`.
- [x] `tests/test_api/test_pipelines.py` — 2 new end-to-end tests: Coder writes plaintext-
      password code → Reviewer rejects with feedback → Coder revises to hashed comparison →
      Reviewer approves → run completes (full loop, both agents deployed for real, only the
      LLM boundary mocked); and a second test confirming the run fails cleanly once
      `max_iterations` is exhausted with no approval.
- [x] 101/101 tests passing
- [x] Committed: `192aa5f feat: pipeline loop_until logic, Coder-Reviewer feedback loop`
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
| 2026-07-15 | Official `mcp` Python SDK, not hand-rolled JSON-RPC | Spec-compliant handshake/transports now, correct as MCP evolves; we only write the schema/result adapter |
| 2026-07-15 | Coder is a `GenericAgent` config (system prompt + tools), not a new agent class | Runtime already deploys every agent generically via `AgentConfig` from DB JSON; a separate class would be unreachable through `/deploy` without extra dispatch logic |

---

## Customer Conversations Log

> Talk to 1 dev team per week. Track every conversation here. This is more important than code.

| Date | Company / person | Insight | Action |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |
