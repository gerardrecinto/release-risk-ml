#!/usr/bin/env bash
# Smoke test against a running instance of the service.
# Usage: scripts/smoke_test.sh [base_url]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "== healthz =="
curl -sf "$BASE_URL/healthz"
echo

echo "== predict: rule-resolved high risk (low test pass rate) =="
curl -sf -X POST "$BASE_URL/predict" -H 'Content-Type: application/json' -d '{
  "lines_changed": 500, "files_changed": 10, "test_pass_rate": 0.5,
  "code_review_approvals": 2, "is_hotfix": false, "deploy_hour_utc": 14,
  "time_since_last_deploy_hours": 48.0, "author_past_rollback_rate": 0.1,
  "change_failure_history_30d": 0, "service_criticality": "low"
}'
echo

echo "== predict: rule-resolved low risk (small, reviewed, clean history) =="
curl -sf -X POST "$BASE_URL/predict" -H 'Content-Type: application/json' -d '{
  "lines_changed": 10, "files_changed": 2, "test_pass_rate": 1.0,
  "code_review_approvals": 2, "is_hotfix": false, "deploy_hour_utc": 14,
  "time_since_last_deploy_hours": 48.0, "author_past_rollback_rate": 0.1,
  "change_failure_history_30d": 0, "service_criticality": "low"
}'
echo

echo "== predict: ambiguous case, routed to model =="
curl -sf -X POST "$BASE_URL/predict" -H 'Content-Type: application/json' -d '{
  "lines_changed": 300, "files_changed": 4, "test_pass_rate": 0.9,
  "code_review_approvals": 1, "is_hotfix": false, "deploy_hour_utc": 14,
  "time_since_last_deploy_hours": 20.0, "author_past_rollback_rate": 0.3,
  "change_failure_history_30d": 1, "service_criticality": "medium"
}'
echo

echo "== predict: invalid input rejected =="
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/predict" -H 'Content-Type: application/json' -d '{"lines_changed": -1}')
if [ "$STATUS" != "422" ]; then
  echo "expected 422 for invalid input, got $STATUS"
  exit 1
fi
echo "422 as expected"

echo "smoke test passed"
