# CLAUDE.md — Standing Instructions for Claude Code

> **READ THIS FIRST every session.** This file is the contract for how we build A2A-Mesh.
> If anything in this file conflicts with a user request, ask for clarification before proceeding.

---

## 1. Project Identity

**Name:** A2A-Mesh
**Repo:** https://github.com/amirbr/A2A-Mesh
**One-liner:** A vertical SaaS platform that lets companies build, orchestrate, and federate AI agents using the A2A protocol — internally and across organizations.
**Founder:** Amir (solo, building MVP)
**Current phase:** Pre-MVP. API-first. No UI yet.

---

## 2. Mandatory Reading Order at Session Start

When you (Claude Code) open this repo, read these files in order before doing anything:

1. **CLAUDE.md** — this file (project rules)
2. **PROGRESS.md** — what week and day we're on, what's done, what's next
3. **PLAN.md** — the 12-week build plan with weekly deliverables
4. **ARCHITECTURE.md** — system design, data models, API surface

If the user asks about money, valuation, or business: read **FINANCIAL_PROJECTION.md**.

---

## 3. Core Principles (Non-Negotiable)

These rules override defaults. Follow them strictly.

### 3.1 Scope discipline
- We're building **API only** until Week 12. No UI work. No React. No HTML.
- One use case until it works end-to-end: **Coder → Reviewer → Jira** dev pipeline.
- The moat is **cross-company federation**. Design for it from Day 1, even if not used yet.

### 3.2 Stack rules — do not deviate without asking
- **Language:** Python 3.11+ only. No Node, no Go.
- **Web framework:** FastAPI. Not Flask, not Django.
- **DB:** PostgreSQL only. No MongoDB, no SQLite (except in tests).
- **Cache/queue:** Redis only.
- **ORM:** SQLAlchemy 2.0 (async).
- **Migrations:** Alembic.
- **LLM:** Anthropic Claude API. Default model `claude-opus-4-7`.
- **Agent SDK:** Google ADK + `a2a-sdk`. We do NOT reimplement A2A from scratch.
- **Testing:** pytest + httpx for API tests.
- **Package manager:** `uv` (preferred) or `pip`.
- **Format/lint:** `ruff` for both. No `black`, no `flake8`, no `isort` separately.
- **Type checking:** `mypy` in strict mode.

### 3.3 Infrastructure rules
- NO Kafka, NO RabbitMQ in the MVP. Use Postgres + Redis for queues.
- NO Kubernetes for MVP. Docker Compose locally, single VM/container in cloud.
- NO microservices proliferation. Start as a modular monolith. Split later if pain demands it.

### 3.4 Code style — strict
- **Type hints required** on every function signature (parameters AND return types).
- **Async/await** for all I/O (DB, HTTP, LLM calls).
- **No bare `except:`** — always catch specific exceptions.
- **No print statements** in code — use `logging` module with structured JSON logs.
- **Constants in UPPER_SNAKE_CASE.**
- **Private functions/methods** prefixed with `_`.
- **Docstrings** required on every public function and class (Google style).
- **Line length:** 100 characters max.
- **Imports:** standard lib → third-party → local, separated by blank lines.

### 3.5 API design rules
- All routes versioned: `/v1/...`.
- All A2A protocol endpoints under `/a2a/...`.
- All responses are JSON.
- All errors use HTTP status codes correctly AND return a JSON body with `{ "error": { "code": ..., "message": ..., "details": ... } }`.
- All entity IDs are prefixed strings: `agt_xxxx` (agent), `usr_xxxx` (user), `co_xxxx` (company), `tsk_xxxx` (task), `pip_xxxx` (pipeline), `run_xxxx` (run).
- ID format: `prefix_` + 12 char lowercase alphanumeric.
- All timestamps are ISO 8601 UTC with `Z` suffix.
- All endpoints that change data require auth (JWT or API key).

### 3.6 Database rules
- All tables have: `id` (string PK), `created_at`, `updated_at` (UTC).
- All foreign keys named `<table>_id`.
- Use Alembic for every schema change. NEVER edit the DB schema by hand.
- Index foreign keys and any column used in WHERE clauses.
- Use UUIDs internally if needed, but expose prefixed string IDs externally.

### 3.7 Testing rules
- Every API endpoint has at least one happy-path test.
- Every API endpoint has at least one error-case test.
- Tests use pytest + httpx AsyncClient.
- Test DB is separate from dev DB (use `TEST_DATABASE_URL`).
- Aim for 70%+ coverage. Don't obsess over 100%.
- Run `pytest` before declaring any task done.

### 3.8 Security rules
- NEVER commit secrets, API keys, or `.env` files.
- All secrets read from environment variables via `pydantic-settings`.
- Passwords hashed with `argon2` (use `argon2-cffi`).
- JWT tokens signed with HS256, 1-hour expiry default.
- API keys hashed in DB (store hash, not plaintext).
- All cross-company A2A calls signed with JWT (federation auth).
- Rate limit every public endpoint.

### 3.9 Git rules
- Commit messages: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Small commits. One logical change per commit.
- Branch naming: `week-N/feature-name` (e.g. `week-2/echo-agent`).
- NEVER commit directly to `main` once we have CI. PRs only.

---

## 4. Folder Structure (canonical)

```
A2A-Mesh/
├── CLAUDE.md
├── README.md
├── PLAN.md
├── PROGRESS.md
├── ARCHITECTURE.md
├── FINANCIAL_PROJECTION.md
├── .claudeignore
├── .gitignore
├── .env.example
├── pyproject.toml
├── docker-compose.yml
├── alembic.ini
├── src/
│   └── a2a_mesh/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app entrypoint
│       ├── config.py               # Settings (pydantic-settings)
│       ├── logging.py              # Structured logging setup
│       ├── api/
│       │   ├── __init__.py
│       │   ├── v1/                 # /v1/* routes
│       │   │   ├── auth.py
│       │   │   ├── agents.py
│       │   │   ├── pipelines.py
│       │   │   ├── tasks.py
│       │   │   ├── federation.py
│       │   │   └── companies.py
│       │   └── a2a/                # /a2a/* protocol endpoints
│       │       ├── well_known.py
│       │       ├── messages.py
│       │       └── tasks.py
│       ├── core/
│       │   ├── auth.py             # JWT, API keys, password hashing
│       │   ├── ids.py              # ID generation
│       │   └── errors.py           # Custom exceptions
│       ├── db/
│       │   ├── __init__.py
│       │   ├── session.py          # Async session factory
│       │   ├── base.py             # Declarative base
│       │   └── models/
│       │       ├── company.py
│       │       ├── user.py
│       │       ├── agent.py
│       │       ├── pipeline.py
│       │       ├── task.py
│       │       └── trust.py
│       ├── agents/
│       │   ├── base.py             # BaseAgent class
│       │   ├── coder.py
│       │   ├── reviewer.py
│       │   └── jira_agent.py
│       ├── orchestrator/
│       │   ├── engine.py           # Pipeline execution engine
│       │   └── registry.py         # Internal agent registry
│       ├── federation/
│       │   ├── discovery.py
│       │   ├── trust.py
│       │   └── jwt.py              # Federation JWT signing
│       └── llm/
│           └── claude.py           # Anthropic API wrapper
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_agents/
│   └── test_federation/
├── alembic/
│   └── versions/
└── scripts/
    └── seed_dev_data.py
```

**Rules:**
- Never create files outside this structure without asking.
- Never put business logic in `api/` route files — that's only request/response handling. Logic lives in `core/`, `agents/`, `orchestrator/`, `federation/`.

---

## 5. What NOT to Do

These are common LLM-coding mistakes. Avoid all of them.

- ❌ Do not add features that aren't in the current week's plan.
- ❌ Do not add libraries without checking if they're already in `pyproject.toml`.
- ❌ Do not write a UI, HTML template, or React component. We're API only.
- ❌ Do not "improve" existing code unless the user asked for refactoring.
- ❌ Do not write 500-line files. Split when files exceed ~300 lines.
- ❌ Do not bypass type hints with `Any` to make errors go away.
- ❌ Do not add `# type: ignore` without explaining why in a comment.
- ❌ Do not create new database tables without an Alembic migration.
- ❌ Do not add print statements for debugging — use logger.
- ❌ Do not write code without tests.
- ❌ Do not generate code longer than what's actually needed.

---

## 6. Workflow Expectations

Each week is broken into named **sections** (e.g. "Section A: docker-compose + DB session", "Section B: alembic setup"). Each section ends with a test run and a commit. Never bundle multiple sections into one commit.

### Per-section loop (repeat for every section in the week):

1. **Confirm understanding.** State what section you're doing and list files to create/modify (3–5 bullets).
2. **Check PROGRESS.md.** Know what week/section we're on and what was last completed.
3. **Implement.** Write the code.
4. **Test.** Run `uv run pytest` (and `uv run pytest -m integration` if services are up). All tests must pass before committing.
5. **Update PROGRESS.md.** Check off the section's tasks.
6. **Commit.** Suggest a conventional commit message scoped to this section only. Wait for user to commit or do it.
7. **Move to next section.** Do not start it until the user says go.

### Commit message format
```
<type>(week-N/<section-slug>): <what changed>
```
Examples:
- `feat(week-1/docker-compose): add postgres + redis containers`
- `feat(week-1/db-session): async sqlalchemy session factory and base model`
- `test(week-1/health): integration test for /health with live DB and Redis`

### Week structure in PROGRESS.md
Each week lists its sections explicitly. Each section has:
- [ ] Implementation tasks
- [ ] Tests passing
- [ ] Committed

If user says "do X", and X spans multiple sections, **break it into sections and confirm before each.**

---

## 7. Context Recovery (when memory is missing)

If you (Claude Code) feel uncertain about a decision:

1. First check this file (CLAUDE.md).
2. Then check ARCHITECTURE.md for technical decisions.
3. Then check PROGRESS.md for what's been built.
4. Then check the actual code in `src/`.
5. Only if all above are silent — ask the user.

NEVER guess at a decision the user already made. NEVER invent project conventions. Stick to what's documented.

---

## 8. Communication Style

- Be direct. No unnecessary preamble or apology.
- Show code, then explain it — not the other way around.
- When suggesting a non-trivial choice, give 2 options with trade-offs.
- If user proposes something that violates this CLAUDE.md, push back and explain why.
- Use plain English. No "leveraging synergies" garbage.

---

## 9. End of Every Session

When a session ends or the user says "let's wrap up":

1. Summarize what got done in 3 bullet points.
2. Update PROGRESS.md with today's checkmarks.
3. Suggest the next 1–3 tasks for next session.
4. Suggest the commit message(s).

---

*Last updated: Week 0 (project setup). Update this file when conventions change — but never relax it without good reason.*
