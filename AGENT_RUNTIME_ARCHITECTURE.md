# Agent Runtime & Hosting Architecture

> Deep-dive on where deployed agents actually execute, how tenants are isolated from each
> other, and how customers can choose managed vs. self-hosted (BYO cloud). Referenced from
> **ARCHITECTURE.md §7 (Runtime Modes)** — that section stays the summary, this file is the
> detail.
>
> Status: design only, nothing here is built yet. See §8 for the week mapping.

---

## 1. The problem

`ARCHITECTURE.md`'s system diagram has always shown an "Agent Runtime Pool (Docker
containers)" between the orchestrator and the database. That was never built. What exists
today (as of Week 6) is `src/a2a_mesh/orchestrator/registry.py`:

```python
_registry: dict[str, BaseAgent] = {}
```

A module-level Python dict, inside the one FastAPI process. `POST /v1/agents/{id}/deploy`
doesn't provision anything — it instantiates a `GenericAgent` object and drops it in this
dict. This was an explicit, documented tradeoff (`PROGRESS.md` Week 4: *"In-process registry
... Docker-per-agent is post-MVP when we have real workload isolation requirements"*), correct
for getting the API surface built fast. It is not correct for hosting real customer agents.

Concretely, today, if company X deploys 10 agents:

- All 10 run as Python objects sharing one process, one event loop, one CPU/memory pool —
  with every other company's agents too. No isolation beyond `company_id` checks in the API
  layer and the per-task `Workspace` sandbox (Week 6) for tool-using agents.
- A process restart loses all of them. The DB still says `status: "running"`; nothing is
  actually there until someone calls `/restart`.
- Horizontal scaling is impossible — a second API process has an empty registry, so you
  can't run two instances behind a load balancer today.

## 2. Why this is more urgent than "someday, post-MVP"

Week 6 shipped `agents/tools.py`: `file_write` + `run_tests` let a deployed agent write an
arbitrary file into its workspace and then execute it via a real `pytest` subprocess. The
`Workspace.resolve()` path-escape check stops the agent from writing *outside* its workspace,
but it does **nothing** to stop the content of a file written *inside* the workspace from
being arbitrary Python — `run_tests` will happily import and execute it. That subprocess runs
with the same OS user, same filesystem visibility, and same network access as the API server
itself, because there is no container boundary.

Today this is low-risk because the only thing driving these tool calls is our own mocked
tests and (eventually) our own LLM calls under our own system prompts. It stops being
low-risk the moment a real user's free-text task description reaches a Coder agent — prompt
injection or a simply buggy generated test becomes arbitrary code execution in the platform's
own process. **This is a stronger, nearer-term argument for containment than multi-tenant
hosting is.** See §8 for how this splits into a fast, cheap fix now vs. the full runtime
rebuild later.

## 3. Design goals

1. **Real isolation** between agents (crash containment, resource limits) and between
   companies (one tenant can't see or starve another).
2. **Stay inside CLAUDE.md's stack rules** while it's a solo/small team: no Kubernetes, no
   microservices proliferation, modular monolith, single VM/container in cloud, until there's
   a real operational reason to leave that model.
3. **Don't rewrite the control plane to change the data plane.** The orchestrator, DB schema,
   and API contract (`POST /v1/agents/{id}/deploy` etc.) should not need to change shape
   between "in-process," "Docker on a shared host," and "customer's own AWS account." Only
   *where the agent executor lives* changes.
4. **Offer customer choice without operating N different systems.** "Managed" and "customer's
   own cloud" need to be the same abstraction with a different executor target, not two
   separately-maintained platforms.
5. **Every step must be justified by an actual trigger** (a resource ceiling hit, a customer
   contractually requiring it) — not built speculatively ahead of need. This mirrors the
   modular-monolith philosophy already in CLAUDE.md §3.3.

## 4. Deployment tiers

Three tiers, all reachable through the same `Agent.runtime` field that already exists in the
DB schema (`"managed"` / `"byo"`, `agents/agent.py` — just needs a third value added):

| Tier | `Agent.runtime` | Who operates the compute | Isolation unit | Who it's for |
|---|---|---|---|---|
| Shared managed | `managed` | A2A-Mesh | Container per agent, shared host(s) | Default — everyone starts here |
| Dedicated managed | `managed_dedicated` | A2A-Mesh | Host (or host pool) per company | Enterprise / compliance-sensitive, paid tier |
| Customer BYO | `byo` | Customer's own cloud account | Whatever the customer's infra provides | Data-residency / "never leaves our AWS" requirements |

This directly answers "should each company get one Docker" — **not for the default tier.**
One host per company from day one means provisioning real infrastructure (a VM, at minimum)
*at signup*, before that company has proven it'll ever deploy a single agent. At pre-revenue
stage that's cost and ops burden with no matching revenue. Dedicated-per-company hosting
becomes tier 2 — sold, not given away, once a customer's usage or compliance needs justify
the dedicated cost. This is also exactly the shape Stripe/Twilio/Cloudflare-style platforms
use: shared multi-tenant infra by default, dedicated infra as a paid upsell.

## 5. Phase 1 (recommended next build) — container-per-agent, shared host, plain Docker

Replace `orchestrator/registry.py`'s in-memory dict with real containers, still on a single
host, still no Kubernetes — this satisfies CLAUDE.md's "single VM/container in cloud" rule
while closing the actual isolation gap.

**Mechanics:**

- The orchestrator talks to the local Docker daemon via the Docker Engine API (`docker`
  Python SDK, or raw calls to the Unix socket — a new dependency, needs the same sign-off
  process Section C's `mcp` SDK went through).
- Each deployed agent = one container, built from a single generic `a2a-mesh-agent` image
  (not one image per agent — the same `GenericAgent` code runs inside every container; what
  differs is the `AgentConfig` JSON injected as an environment variable or mounted file, same
  as `_build_agent_instance` does today, just crossing a process boundary instead of an
  in-process call).
- Container naming/labels: `company_id`, `agent_id`, `agent_name` — so `docker ps
  --filter label=company_id=co_xxx` gives you a company's whole fleet, and cleanup/billing
  can be driven off labels instead of a separate tracking table.
- Resource limits per container: `--memory`, `--cpus`, and (for tool-executing agents like
  the Coder) `--network none` or a locked-down network so `run_tests`/`file_write` can't reach
  the internet or other containers — this is the fix for the §2 sandbox-escape gap, and it's
  the same mechanism as the isolation fix, not a separate piece of work.
- One Docker network per company (`docker network create co_xxx`) — containers in different
  companies' networks can't reach each other even if something inside one is compromised.
- `/deploy`, `/stop`, `/restart`, `/health` (already-built Week 4 endpoints) change their
  implementation from `registry.register()`/Python method calls to `docker run` / `docker
  stop` / HTTP calls to the container's exposed A2A port — **the API contract to the customer
  does not change**, only what's behind `_build_agent_instance`.
- Agent-to-agent calls (pipelines, Week 5's `orchestrator/engine.py`) switch from direct
  Python function calls to real HTTP calls against `http://<container>:<port>/a2a/...` — this
  is actually a *smaller* change than it sounds, since the A2A protocol layer already speaks
  JSON-RPC over HTTP; today it's just being called in-process. This also means Week 5's
  pipeline executor already exercises the exact call shape Phase 1 will use for real.

**What this buys immediately:** every agent survives an API-process restart (the container
keeps running, the orchestrator just needs to reconnect and resync state), resource limits
stop a runaway agent from starving others, and the tool-execution sandbox-escape from §2 is
closed.

**What it doesn't solve:** all containers are still on one host — company X's 10 agents and
company Y's 10 agents compete for the same physical CPU/memory ceiling. That's fine until a
single host's capacity is the actual bottleneck (§6), not before.

## 6. Phase 2 — multi-host, and where Kubernetes actually fits

Triggered by an actual ceiling, not a calendar date: when total deployed-agent count or
resource usage approaches what one host can hold. Two paths, deliberately kept open by
Phase 1's design (Docker Engine API + label-based tracking translates to either):

- **Small fleet, hand-rolled scheduler.** A handful of Docker hosts, a simple placement
  rule (e.g. least-loaded host, or shard by `company_id` hash), tracked in a new `hosts`
  table. Lower operational complexity than Kubernetes, appropriate for "a few dozen hosts,"
  and still consistent with "no microservices proliferation."
- **Kubernetes.** The right tool once you're managing enough hosts that hand-rolled
  scheduling, health-checking, and rolling restarts become the actual pain — i.e. exactly
  the "split later if pain demands it" condition CLAUDE.md already states as the exit
  criterion for the modular monolith. Namespace-per-company gives the same network isolation
  Phase 1 gets from `docker network create`, just fleet-wide. This requires real operational
  investment (cluster upgrades, RBAC, ingress, secrets management) that isn't worth taking on
  solo pre-revenue — it's the right call once there's either enough scale to need it or a
  team member whose job is operating it.

Because Phase 1 already models each agent as "a container with labels, reachable over HTTP,"
migrating the scheduler backend to Kubernetes later is swapping what decides *where* a
container runs — not a rewrite of the orchestrator, the DB schema, or the API. That
portability is the actual reason to build Phase 1 the way §5 describes instead of anything
more bespoke.

## 7. Phase 3 — customer BYO cloud account

`ARCHITECTURE.md` §7 already names this ("customer hosts; they expose A2A endpoints; we just
route") but the mechanism as written — customer exposes an inbound endpoint to us — is a hard
sell to any security team: it means opening inbound firewall rules to an external SaaS.
Recommended refinement:

**The Runner pattern** (same shape as GitHub Actions self-hosted runners, or the Datadog
agent): we ship a small container image (`a2a-mesh-runner`) the customer deploys into their
own AWS/GCP/Azure account — one `docker run` or a Terraform module, their choice. The Runner:

1. Opens an **outbound-only** authenticated connection to A2A-Mesh's control plane (no
   inbound ports on the customer's side, no customer cloud credentials ever touch our infra).
2. Pulls its assigned `AgentConfig`s over that connection.
3. Runs the same `GenericAgent` code Phase 1's containers run — the actual agent logic is
   identical across all three tiers; only where it executes and who pays the compute bill
   differs.
4. Reports task results back over the same connection.

This is why §3's goal 3 (control plane doesn't change shape) matters: the Runner is just
another executor target the orchestrator dispatches to, alongside "container on our Docker
host" and "container on a dedicated host." `Agent.runtime = "byo"` plus a `runner_id`
foreign key is enough to route a deploy call to the right place.

## 8. Data model changes needed (all phases)

- `Agent.runtime`: extend the existing string field's allowed values from `managed`/`byo` to
  `managed` / `managed_dedicated` / `byo`.
- New `hosts` table (Phase 1+): `id`, `label` (`shared-pool` / `co_xxx-dedicated`),
  `docker_endpoint`, `capacity_cpu`, `capacity_mem_mb`, `status`, heartbeat timestamp.
- New `runners` table (Phase 3): `id`, `company_id`, `last_seen_at`, `status`
  (`pending`/`connected`/`stale`), auth token hash (same pattern as `ApiKey` — store hash,
  not plaintext, per CLAUDE.md §3.8).
- `Agent` gains `host_id` (nullable, managed tiers) or `runner_id` (nullable, BYO tier) —
  exactly one of the two set, matching `runtime`.
- No changes needed to `Pipeline`, `PipelineRun`, or the public API request/response shapes —
  this is entirely a data-plane change per §3 goal 3.

## 9. Rollout plan and week mapping

Two different urgency levels, not one:

1. **Fast-follow, before real (non-founder) users touch the Coder agent — not a full
   week.** Harden `agents/tools.py::run_tests` so `file_write` + `run_tests` can't become
   arbitrary unsandboxed code execution: run the subprocess with a restricted environment
   (empty `PATH` additions, no network-capable env vars) at minimum, and disable outbound
   networking for that subprocess if the platform allows it without a container (e.g.
   `unshare --net` on Linux, or accept the gap and prioritize Phase 1 sooner). This is cheap
   and closes the most acute exposure without waiting for the full runtime rebuild.
2. **Week 13 (new, first post-MVP week) — "Agent Runtime: Container-per-Agent."** Build
   §5 (Phase 1) in full: Docker Engine API integration, generic agent image, per-company
   networks, resource limits, `/deploy`/`/stop`/`/restart`/`/health` re-pointed at containers,
   pipeline engine switched from in-process calls to real HTTP. This is *not* squeezed into
   the existing Week 11 ("Persistence, Observability & Reliability") — that week is about the
   control plane's own reliability (DB-backed state, Celery queue, tracing); this is a
   distinct data-plane project and deserves its own week rather than diluting either scope.
3. **Week 14+, trigger-based, not calendar-based.** Phase 2 (multi-host, §6) once a single
   host's capacity is the actual bottleneck. Phase 3 (BYO Runner, §7) once a real prospect
   asks for it, or a design partner's compliance team requires it. Building either before
   there's a concrete trigger would be exactly the kind of speculative infrastructure CLAUDE.md
   §3.3 already warns against.

## 10. Open questions

- Where does Phase 1's Docker host itself run — a single cloud VM we already control, or
  does this fold into whatever Week 12 picks for deploying the platform (Railway/Fly.io)? Both
  of those are container platforms themselves, which may mean "our Docker host" is really
  "containers-in-a-platform-that-manages-containers" — worth resolving when Week 12 is
  reached, not now.
- Billing/metering per container (CPU-seconds, memory) isn't designed yet — needed before
  Phase 1 ships if usage-based pricing is part of the plan (see `FINANCIAL_PROJECTION.md`).
- Runner auth (§7) needs the same signed-JWT federation pattern Week 10 builds for
  cross-company trust — likely the same mechanism, reused rather than reinvented.
