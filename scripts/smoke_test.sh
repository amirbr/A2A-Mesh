#!/bin/bash
# Smoke test — runs all API features end to end.
# Usage: ./scripts/smoke_test.sh

BASE="http://localhost:8000"
PASS=0
FAIL=0
TS=$(date +%s)
NS="acme${TS}"
EMAIL="admin${TS}@acme.com"

check() {
  local label="$1"
  local status="$2"
  local expected="$3"
  if [ "$status" -eq "$expected" ]; then
    echo "  ✓ $label (HTTP $status)"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $label (expected $expected, got $status)"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== Health ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/health")
check "GET /health" "$STATUS" 200
cat /tmp/a2a_resp | python3 -m json.tool 2>/dev/null

echo ""
echo "=== Auth: Register ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Acme\",\"namespace\":\"$NS\",\"email\":\"$EMAIL\",\"password\":\"secret123\"}")
check "POST /v1/auth/register" "$STATUS" 201
TOKEN=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
echo "  Token: ${TOKEN:0:40}..."

echo ""
echo "=== Auth: Login ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"secret123\"}")
check "POST /v1/auth/login" "$STATUS" 200

echo ""
echo "=== Auth: Wrong password ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"wrongpassword\"}")
check "POST /v1/auth/login (wrong password)" "$STATUS" 401

echo ""
echo "=== API Keys ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/auth/api-keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"ci-key"}')
check "POST /v1/auth/api-keys" "$STATUS" 201
KEY_ID=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/auth/api-keys" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/auth/api-keys" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X DELETE "$BASE/v1/auth/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $TOKEN")
check "DELETE /v1/auth/api-keys/:id" "$STATUS" 204

echo ""
echo "=== Agents ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"my-coder","display_name":"My Coder","description":"A coding agent"}')
check "POST /v1/agents" "$STATUS" 201
AGENT_ID=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo "  Agent ID: $AGENT_ID"

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/agents" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/agents" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/agents/:id" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X PATCH "$BASE/v1/agents/$AGENT_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"display_name":"Updated Coder","visibility":"internal"}')
check "PATCH /v1/agents/:id" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X DELETE "$BASE/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN")
check "DELETE /v1/agents/:id" "$STATUS" 204

echo ""
echo "=== Agent Runtime ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"runtime-agent","display_name":"Runtime Agent","description":"Deploy test"}')
check "POST /v1/agents (for runtime test)" "$STATUS" 201
RUNTIME_AGENT_ID=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" \
  "$BASE/v1/agents/$RUNTIME_AGENT_ID/status" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/agents/:id/status (before deploy)" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$RUNTIME_AGENT_ID/deploy" \
  -H "Authorization: Bearer $TOKEN")
check "POST /v1/agents/:id/deploy" "$STATUS" 200
echo "  Endpoint: $(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['endpoint_url'])" 2>/dev/null)"

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" \
  "$BASE/v1/agents/$RUNTIME_AGENT_ID/status" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/agents/:id/status (running)" "$STATUS" 200

# Call the deployed agent via A2A
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST \
  "$BASE/a2a/$RUNTIME_AGENT_ID/" \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"msg-001","role":"ROLE_USER","parts":[{"text":"hello dynamic agent"}]}}}')
check "POST /a2a/:id/ (dynamic dispatch)" "$STATUS" 200
echo "  Response: $(cat /tmp/a2a_resp | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['message']['parts'][0]['text'])" 2>/dev/null)"

# Agent card for deployed agent
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" \
  "$BASE/a2a/$RUNTIME_AGENT_ID/.well-known/agent-card.json")
check "GET /a2a/:id/.well-known/agent-card.json" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/agents/$RUNTIME_AGENT_ID/logs" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/agents/:id/logs" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$RUNTIME_AGENT_ID/stop" \
  -H "Authorization: Bearer $TOKEN")
check "POST /v1/agents/:id/stop" "$STATUS" 200

echo ""
echo "=== Pipelines ==="
# Re-deploy runtime agent for pipeline use
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"pipeline-agent","display_name":"Pipeline Agent","description":"Used in pipeline"}')
check "POST /v1/agents (pipeline step)" "$STATUS" 201
PIP_AGENT_ID=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/pipelines" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"test-pipeline\",\"description\":\"Smoke test pipeline\",\"steps\":[{\"agent_id\":\"$PIP_AGENT_ID\",\"name\":\"step-one\"}]}")
check "POST /v1/pipelines" "$STATUS" 201
PIPELINE_ID=$(cat /tmp/a2a_resp | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo "  Pipeline ID: $PIPELINE_ID"

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/pipelines" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/pipelines" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/v1/pipelines/$PIPELINE_ID" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/pipelines/:id" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X PATCH "$BASE/v1/pipelines/$PIPELINE_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"updated-pipeline"}')
check "PATCH /v1/pipelines/:id" "$STATUS" 200

# Deploy agent then run pipeline
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST \
  "$BASE/v1/agents/$PIP_AGENT_ID/deploy" \
  -H "Authorization: Bearer $TOKEN")
check "POST /v1/agents/:id/deploy (for pipeline)" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/v1/pipelines/$PIPELINE_ID/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"input":"write a hello world function in Python"}')
check "POST /v1/pipelines/:id/run" "$STATUS" 200
RUN_DATA=$(cat /tmp/a2a_resp)
RUN_STATUS=$(echo "$RUN_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
RUN_ID=$(echo "$RUN_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo "  Run status: $RUN_STATUS, Run ID: $RUN_ID"

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" \
  "$BASE/v1/pipelines/$PIPELINE_ID/runs/$RUN_ID" \
  -H "Authorization: Bearer $TOKEN")
check "GET /v1/pipelines/:id/runs/:run_id" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X DELETE "$BASE/v1/pipelines/$PIPELINE_ID" \
  -H "Authorization: Bearer $TOKEN")
check "DELETE /v1/pipelines/:id" "$STATUS" 204

echo ""
echo "=== Echo Agent (A2A Protocol) ==="
STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" "$BASE/.well-known/agent-card.json")
check "GET /.well-known/agent-card.json" "$STATUS" 200

STATUS=$(curl -s -o /tmp/a2a_resp -w "%{http_code}" -X POST "$BASE/a2a/echo/" \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"msg-001","role":"ROLE_USER","parts":[{"text":"hello from smoke test"}]}}}')
check "POST /a2a/echo/ (SendMessage)" "$STATUS" 200
ECHO_TEXT=$(cat /tmp/a2a_resp | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['message']['parts'][0]['text'])" 2>/dev/null)
echo "  Response: $ECHO_TEXT"

echo ""
echo "==========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "==========================================="
echo ""
