#!/bin/bash
# A2A-Mesh end-to-end demo
# Scenario: Coder -> Reviewer pipeline with the real loop_until feedback loop (Week 7),
# driven through the actual POST /v1/pipelines/{id}/run endpoint - not manual per-agent
# calls like this script used to do. The orchestrator itself decides whether to retry
# the Coder based on the Reviewer's verdict.
#
# Provider: Ollama (llama3.2, local, free) by default. The Coder runs WITHOUT its real
# tools (file_read/file_write/run_tests/git_diff, Week 6) in this mode - live testing
# showed llama3.2 does not reliably follow the tool-calling schema (it invents tool names
# that don't exist, e.g. "create_test_file" instead of "file_write"). Pass --tools to run
# the Coder with its real built-in tools against Claude instead, which does follow the
# schema correctly - this requires ANTHROPIC_API_KEY and makes real (billed) API calls.
#
# Usage: ./scripts/demo.sh [--tools] [task]
# Default task: "Write a Python function that finds all duplicate values in a list and returns them sorted"

set -e

BASE="http://localhost:8000"

USE_TOOLS=false
POSITIONAL=()
for arg in "$@"; do
  if [ "$arg" = "--tools" ]; then
    USE_TOOLS=true
  else
    POSITIONAL+=("$arg")
  fi
done
TASK="${POSITIONAL[0]:-Write a Python function that finds all duplicate values in a list and returns them sorted}"

if [ "$USE_TOOLS" = true ]; then
  if [ -z "$ANTHROPIC_API_KEY" ] && [ -f .env ]; then
    ANTHROPIC_API_KEY=$(grep -E "^ANTHROPIC_API_KEY=" .env | cut -d= -f2-)
  fi
  if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "✗ --tools requires ANTHROPIC_API_KEY (real tool use needs a model that reliably follows function-calling schemas; llama3.2 does not)."
    exit 1
  fi
  PROVIDER="anthropic"
  MODEL="claude-opus-4-8"
else
  PROVIDER="ollama"
  MODEL="llama3.2"
fi

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

step() { echo -e "\n${BOLD}${CYAN}▶ $1${RESET}"; }
ok()   { echo -e "  ${GREEN}✓ $1${RESET}"; }
info() { echo -e "  ${DIM}$1${RESET}"; }
fail() { echo -e "  ${RED}✗ $1${RESET}"; exit 1; }

check_status() {
  local label="$1" actual="$2" expected="$3"
  if [ "$actual" -ne "$expected" ]; then
    fail "$label — expected HTTP $expected, got $actual"
  fi
}

extract() {
  python3 -c "
import sys, json
try:
    print(json.load(sys.stdin)$1)
except Exception:
    print('')
" 2>/dev/null
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║          A2A-Mesh  —  Live Demo              ║${RESET}"
echo -e "${BOLD}║   Coder → Reviewer  (loop_until feedback)    ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Task:${RESET}     $TASK"
if [ "$USE_TOOLS" = true ]; then
  echo -e "${BOLD}Provider:${RESET} $PROVIDER/$MODEL  ${DIM}(real tools enabled: file_read/file_write/run_tests/git_diff)${RESET}"
else
  echo -e "${BOLD}Provider:${RESET} $PROVIDER/$MODEL  ${DIM}(plain text — pass --tools for real tool use via Claude)${RESET}"
fi

# ── 0. Health ─────────────────────────────────────────────────────────────────
step "0. Health check"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" "$BASE/health")
check_status "GET /health" "$STATUS" 200
DB=$(cat /tmp/demo_resp | extract "['db']")
REDIS=$(cat /tmp/demo_resp | extract "['redis']")
ok "Server is up  (db=$DB  redis=$REDIS)"

# ── 1. Register ───────────────────────────────────────────────────────────────
TS=$(date +%s)
NS="demo${TS}"
EMAIL="admin${TS}@demo.com"

step "1. Register company"
info "namespace=$NS  email=$EMAIL"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Demo Corp\",\"namespace\":\"$NS\",\"email\":\"$EMAIL\",\"password\":\"secret123\"}")
check_status "POST /v1/auth/register" "$STATUS" 201
TOKEN=$(cat /tmp/demo_resp | extract "['access_token']")
ok "Registered  (token=${TOKEN:0:30}...)"

# ── 2. Create agents — real Coder/Reviewer configs, same code the pipeline runs ────────
step "2. Create Coder agent"
CODER_CFG=$(PROVIDER="$PROVIDER" MODEL="$MODEL" USE_TOOLS="$USE_TOOLS" uv run python3 -c "
import json, os
from a2a_mesh.agents.coder import build_coder_config
cfg = build_coder_config(provider=os.environ['PROVIDER'], model=os.environ['MODEL'])
tools = cfg.tools if os.environ['USE_TOOLS'] == 'true' else []
print(json.dumps({
    'name': cfg.name, 'display_name': cfg.display_name, 'description': cfg.description,
    'provider': cfg.provider, 'model': cfg.model, 'system_prompt': cfg.system_prompt,
    'config': {'tools': tools},
}))
")
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d "$CODER_CFG")
check_status "POST /v1/agents (coder)" "$STATUS" 201
CODER_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Coder created  (id=$CODER_ID)"

step "3. Create Reviewer agent"
REVIEWER_CFG=$(PROVIDER="$PROVIDER" MODEL="$MODEL" uv run python3 -c "
import json, os
from a2a_mesh.agents.reviewer import build_reviewer_config
cfg = build_reviewer_config(provider=os.environ['PROVIDER'], model=os.environ['MODEL'])
print(json.dumps({
    'name': cfg.name, 'display_name': cfg.display_name, 'description': cfg.description,
    'provider': cfg.provider, 'model': cfg.model, 'system_prompt': cfg.system_prompt,
}))
")
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d "$REVIEWER_CFG")
check_status "POST /v1/agents (reviewer)" "$STATUS" 201
REVIEWER_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Reviewer created  (id=$REVIEWER_ID)"

# ── 4. Deploy ─────────────────────────────────────────────────────────────────
step "4. Deploy agents"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$CODER_ID/deploy" -H "Authorization: Bearer $TOKEN")
check_status "deploy coder" "$STATUS" 200
ok "Coder deployed"

STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$REVIEWER_ID/deploy" -H "Authorization: Bearer $TOKEN")
check_status "deploy reviewer" "$STATUS" 200
ok "Reviewer deployed"

# ── 5. Pipeline with loop_until (Week 7) ────────────────────────────────────────────────
step "5. Create pipeline  (Coder → Reviewer, loop_until approved, max 3 attempts)"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/pipelines" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"name\": \"code-review-pipeline\",
    \"description\": \"Coder writes code, Reviewer approves or sends it back for revision\",
    \"steps\": [
      {\"agent_id\": \"$CODER_ID\", \"name\": \"write-code\"},
      {\"agent_id\": \"$REVIEWER_ID\", \"name\": \"review-code\",
       \"loop_until\": {\"field\": \"approved\", \"equals\": true}, \"max_iterations\": 3}
    ]
  }")
check_status "POST /v1/pipelines" "$STATUS" 201
PIPELINE_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Pipeline created  (id=$PIPELINE_ID)"

# ── 6. Run it — the orchestrator owns the Coder ↔ Reviewer loop internally ─────────────
step "6. Run pipeline  (orchestrator retries the Coder on rejection, up to max_iterations)"
info "waiting on $PROVIDER/$MODEL — can take a while, longer if it loops"

RUN_PAYLOAD=$(python3 -c "import json, sys; print(json.dumps({'input': sys.argv[1]}))" "$TASK")
START=$(date +%s)
STATUS=$(curl -s -o /tmp/demo_run -w "%{http_code}" -X POST \
  "$BASE/v1/pipelines/$PIPELINE_ID/run" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d "$RUN_PAYLOAD" --max-time 300)
END=$(date +%s)
check_status "POST /v1/pipelines/:id/run" "$STATUS" 200

RUN_ID=$(cat /tmp/demo_run | extract "['id']")
RUN_STATUS=$(cat /tmp/demo_run | extract "['status']")
ok "Pipeline run finished in $((END - START))s  →  status=$RUN_STATUS"

echo ""
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"
if [ "$RUN_STATUS" = "completed" ]; then
  echo -e "${BOLD}${YELLOW}  Reviewer's final verdict${RESET}"
  echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"
  echo ""
  python3 -c "
import json
with open('/tmp/demo_run') as f:
    run = json.load(f)
text = json.loads(run['output'])['text']
try:
    print(json.dumps(json.loads(text), indent=2))
except json.JSONDecodeError:
    print(text)
"
  echo ""
  info "This is the Reviewer's own JSON output — loop_until parses this exact object to decide"
  info "whether to loop back to the Coder. Per-step output isn't stored yet (only the final"
  info "text is), so the Coder's approved code isn't visible here — Week 8 will thread it"
  info "through to the Jira step."
else
  echo -e "${BOLD}${RED}  Pipeline failed${RESET}"
  echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"
  echo ""
  cat /tmp/demo_run | extract "['error']"
fi
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"

# ── 7. Teardown ───────────────────────────────────────────────────────────────
step "7. Stop agents"
curl -s -o /dev/null -X POST "$BASE/v1/agents/$CODER_ID/stop" -H "Authorization: Bearer $TOKEN"
ok "Coder stopped"

curl -s -o /dev/null -X POST "$BASE/v1/agents/$REVIEWER_ID/stop" -H "Authorization: Bearer $TOKEN"
ok "Reviewer stopped"

echo ""
echo -e "${BOLD}${GREEN}Demo complete.${RESET}"
echo ""
echo -e "  Agents:   ${DIM}GET $BASE/v1/agents  (Bearer \$TOKEN)${RESET}"
echo -e "  Pipeline: ${DIM}GET $BASE/v1/pipelines/$PIPELINE_ID${RESET}"
echo -e "  Run:      ${DIM}GET $BASE/v1/pipelines/$PIPELINE_ID/runs/$RUN_ID${RESET}"
echo -e "  API docs: ${DIM}$BASE/docs${RESET}"
echo ""
