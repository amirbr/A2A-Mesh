# A2A-Mesh

> A vertical SaaS platform for building, orchestrating, and federating AI agents using the A2A protocol — internally and across organizations.

🚧 **Status: Pre-MVP.** Currently in active development. See [PROGRESS.md](./PROGRESS.md).

---

## What is A2A-Mesh?

A2A-Mesh lets companies:

1. **Build internal AI agent teams** — connect specialized agents in pipelines (e.g., Coder → Reviewer → Jira) that handle real workflows.
2. **Federate across companies** — your agents can discover and securely communicate with agents at other companies, with full authentication and audit trails.

Built on Google's [Agent2Agent (A2A) protocol](https://github.com/google/a2a) and Anthropic's Claude.

---

## Why A2A-Mesh exists

The A2A protocol is open — but using it in production requires solving hard problems:

- **Discovery** — who has what agent?
- **Trust** — how do you authenticate strangers?
- **Reliability** — what happens when an agent goes down?
- **Billing & audit** — who pays, who can prove what happened?

A2A-Mesh solves these. The protocol is HTTP-like; A2A-Mesh is what makes it production-grade.

---

## Quickstart

> Coming when MVP ships (Week 12). For now, see [PLAN.md](./PLAN.md) for the build roadmap.

```bash
# planned developer experience
git clone https://github.com/amirbr/A2A-Mesh.git
cd A2A-Mesh
cp .env.example .env  # add your Anthropic API key
docker compose up
uv run a2a-mesh serve
```

---

## Repository Map

| File | Purpose |
|---|---|
| [CLAUDE.md](./CLAUDE.md) | Standing instructions for Claude Code (read first if you're an AI) |
| [PLAN.md](./PLAN.md) | 12-week build plan |
| [PROGRESS.md](./PROGRESS.md) | Weekly progress tracker |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Technical reference (data models, APIs, flows) |
| [FINANCIAL_PROJECTION.md](./FINANCIAL_PROJECTION.md) | 5-year business projection |
| `src/a2a_mesh/` | Source code |
| `tests/` | Test suite |
| `docs/` | Additional documentation |

---

## Tech Stack

- **Language:** Python 3.11+
- **API:** FastAPI + Uvicorn
- **Database:** PostgreSQL 15+
- **Cache / Queue:** Redis 7+
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **LLM:** Anthropic Claude API
- **Agent framework:** Google ADK + a2a-sdk
- **Container:** Docker + docker-compose
- **Deployment:** Railway / Fly.io (MVP)

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full breakdown.

---

## Local Development (planned)

```bash
# Install dependencies
uv sync

# Start Postgres + Redis
docker compose up -d

# Run migrations
uv run alembic upgrade head

# Run the API
uv run uvicorn a2a_mesh.main:app --reload

# Run tests
uv run pytest

# Lint and format
uv run ruff check --fix .
uv run mypy src/
```

---

## Project Phases

| Phase | Status | Goal |
|---|---|---|
| Week 0 | 🟡 In progress | Project setup, docs |
| Week 1 | ⏳ Upcoming | A2A fundamentals, dev env |
| Week 2 | ⏳ Upcoming | First A2A agent (Echo) |
| Week 3 | ⏳ Upcoming | Base Agent SDK, CRUD APIs |
| Week 4 | ⏳ Upcoming | Agent runtime + deployment |
| Week 5 | ⏳ Upcoming | Claude integration + pipelines |
| Week 6 | ⏳ Upcoming | Coder agent |
| Week 7 | ⏳ Upcoming | Reviewer agent + loops |
| Week 8 | ⏳ Upcoming | Jira agent + full MVP pipeline |
| Week 9 | ⏳ Upcoming | Cross-company federation |
| Week 10 | ⏳ Upcoming | Auth, trust, security |
| Week 11 | ⏳ Upcoming | Persistence + observability |
| Week 12 | ⏳ Upcoming | Deployment + public demo |

---

## License

TBD.

---

## Contact

Built by Amir. Currently a solo project.
