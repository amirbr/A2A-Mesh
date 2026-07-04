#!/bin/bash
# A2A-Mesh end-to-end demo
# Scenario: Coder → Reviewer pipeline backed by real Claude
# Usage: ./scripts/demo.sh [task]
# Default task: "Write a Python function that finds all duplicate values in a list and returns them sorted"

set -e

BASE="http://localhost:8000"
TASK="${1:-Write a Python function that finds all duplicate values in a list and returns them sorted}"

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
pretty()  { python3 -m json.tool 2>/dev/null; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║          A2A-Mesh  —  Live Demo              ║${RESET}"
echo -e "${BOLD}║     Coder → Reviewer pipeline via Claude     ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Task:${RESET} $TASK"

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

# ── 2. Create agents ──────────────────────────────────────────────────────────
step "2. Create Coder agent"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "coder",
    "display_name": "Coder Agent",
    "description": "Writes Python code",
    "provider": "ollama",
    "model": "llama3.2",
    "system_prompt": "You are an expert Python developer. When given a task, write clean, working Python code. Include a brief explanation after the code block. Output only the code and explanation, nothing else."
  }')
check_status "POST /v1/agents (coder)" "$STATUS" 201
CODER_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Coder created  (id=$CODER_ID)"

step "3. Create Reviewer agent"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "reviewer",
    "display_name": "Code Reviewer Agent",
    "description": "Reviews Python code for quality, correctness, and style",
    "provider": "ollama",
    "model": "llama3.2",
    "system_prompt": "You are a senior Python engineer doing a code review. You receive code and a brief explanation. Review it for: correctness, edge cases, readability, and pythonic style. Start with VERDICT: PASS or VERDICT: NEEDS WORK, then give specific bullet-point feedback. Be direct and concrete."
  }')
check_status "POST /v1/agents (reviewer)" "$STATUS" 201
REVIEWER_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Reviewer created  (id=$REVIEWER_ID)"

# ── 3. Deploy ─────────────────────────────────────────────────────────────────
step "4. Deploy agents"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$CODER_ID/deploy" \
  -H "Authorization: Bearer $TOKEN")
check_status "deploy coder" "$STATUS" 200
CODER_URL=$(cat /tmp/demo_resp | extract "['endpoint_url']")
ok "Coder deployed  →  $CODER_URL"

STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$REVIEWER_ID/deploy" \
  -H "Authorization: Bearer $TOKEN")
check_status "deploy reviewer" "$STATUS" 200
REVIEWER_URL=$(cat /tmp/demo_resp | extract "['endpoint_url']")
ok "Reviewer deployed  →  $REVIEWER_URL"

# ── 4. Pipeline ───────────────────────────────────────────────────────────────
step "5. Create pipeline  (Coder → Reviewer)"
STATUS=$(curl -s -o /tmp/demo_resp -w "%{http_code}" -X POST "$BASE/v1/pipelines" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"name\": \"code-review-pipeline\",
    \"description\": \"Coder writes code, Reviewer critiques it\",
    \"steps\": [
      {\"agent_id\": \"$CODER_ID\",    \"name\": \"write-code\"},
      {\"agent_id\": \"$REVIEWER_ID\", \"name\": \"review-code\"}
    ]
  }")
check_status "POST /v1/pipelines" "$STATUS" 201
PIPELINE_ID=$(cat /tmp/demo_resp | extract "['id']")
ok "Pipeline created  (id=$PIPELINE_ID)"

# ── Helper: extract plain text from A2A JSON-RPC response ────────────────────
extract_a2a_text() {
  python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    parts = d.get('result', {}).get('message', {}).get('parts', [])
    print(parts[0].get('text', '') if parts else '')
except Exception:
    print('')
" 2>/dev/null
}

# ── 5. Run step by step ───────────────────────────────────────────────────────
step "6. Step 1 — Coder writes code  (calling Ollama, takes ~20s)"
echo ""

A2A_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
  'jsonrpc': '2.0', 'id': '1', 'method': 'SendMessage',
  'params': {'message': {
    'messageId': 'msg-001', 'role': 'ROLE_USER',
    'parts': [{'text': sys.argv[1]}]
  }}
}))
" "$TASK")

START=$(date +%s)
STATUS=$(curl -s -o /tmp/demo_coder -w "%{http_code}" -X POST \
  "$BASE/a2a/$CODER_ID/" \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d "$A2A_PAYLOAD")
END=$(date +%s)
check_status "POST /a2a/:coder_id/" "$STATUS" 200
CODER_OUTPUT=$(cat /tmp/demo_coder | extract_a2a_text)
ok "Coder finished in $((END - START))s"

echo ""
echo -e "${BOLD}${CYAN}── Coder output ──────────────────────────────${RESET}"
echo ""
echo "$CODER_OUTPUT"
echo ""
echo -e "${BOLD}${CYAN}──────────────────────────────────────────────${RESET}"

step "7. Step 2 — Reviewer critiques the code  (calling Ollama, takes ~20s)"
echo ""

REVIEW_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
  'jsonrpc': '2.0', 'id': '2', 'method': 'SendMessage',
  'params': {'message': {
    'messageId': 'msg-002', 'role': 'ROLE_USER',
    'parts': [{'text': sys.argv[1]}]
  }}
}))
" "$CODER_OUTPUT")

START=$(date +%s)
STATUS=$(curl -s -o /tmp/demo_reviewer -w "%{http_code}" -X POST \
  "$BASE/a2a/$REVIEWER_ID/" \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d "$REVIEW_PAYLOAD")
END=$(date +%s)
check_status "POST /a2a/:reviewer_id/" "$STATUS" 200
REVIEWER_OUTPUT=$(cat /tmp/demo_reviewer | extract_a2a_text)
ok "Reviewer finished in $((END - START))s"

echo ""
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${YELLOW}  Reviewer's verdict${RESET}"
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"
echo ""
echo "$REVIEWER_OUTPUT"
echo ""
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════${RESET}"

# ── 8. Teardown ───────────────────────────────────────────────────────────────
step "8. Stop agents"
curl -s -o /dev/null -X POST "$BASE/v1/agents/$CODER_ID/stop" \
  -H "Authorization: Bearer $TOKEN"
ok "Coder stopped"

curl -s -o /dev/null -X POST "$BASE/v1/agents/$REVIEWER_ID/stop" \
  -H "Authorization: Bearer $TOKEN"
ok "Reviewer stopped"

echo ""
echo -e "${BOLD}${GREEN}Demo complete.${RESET}"
echo ""
echo -e "  Agents:   ${DIM}GET $BASE/v1/agents  (Bearer \$TOKEN)${RESET}"
echo -e "  Pipeline: ${DIM}GET $BASE/v1/pipelines/$PIPELINE_ID${RESET}"
echo -e "  Run:      ${DIM}GET $BASE/v1/pipelines/$PIPELINE_ID/runs/$RUN_ID${RESET}"
echo -e "  API docs: ${DIM}$BASE/docs${RESET}"
echo ""
