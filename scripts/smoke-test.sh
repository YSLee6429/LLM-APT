#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://localhost:8000}"
web_url="${2:-http://localhost:3000}"

echo "[1/5] 检查 API 存活状态"
curl --noproxy '*' --fail --silent --show-error "${base_url}/health/live" | grep --quiet '"status":"ok"'

echo "[2/5] 检查 API 就绪状态"
curl --noproxy '*' --fail --silent --show-error "${base_url}/health/ready" | grep --quiet '"status":"ready"'

echo "[3/5] 创建短时游客会话"
guest_json="$(curl --noproxy '*' --fail --silent --show-error --request POST "${base_url}/api/v1/auth/guest")"
guest_token="$(printf '%s' "${guest_json}" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')"
test -n "${guest_token}"
curl --noproxy '*' --fail --silent --show-error \
  --header "Authorization: Bearer ${guest_token}" \
  "${base_url}/api/v1/auth/me" | grep --quiet '"role":"guest"'

echo "[4/5] 验证游客不能调用外部模型"
status_code="$(curl --noproxy '*' --silent --output /dev/null --write-out '%{http_code}' \
  --request POST \
  --header "Authorization: Bearer ${guest_token}" \
  --header 'Content-Type: application/json' \
  --data '{"provider_key":"mock","prompt":"smoke test","language":"cpp"}' \
  "${base_url}/api/v1/providers/generate")"
test "${status_code}" = "403"

echo "[5/5] 检查 Web 入口"
curl --noproxy '*' --fail --silent --show-error --output /dev/null "${web_url}"

echo "LLM-APT 冒烟校验通过：API 就绪、游客会话有效、受限接口返回 403、Web 可访问。"
