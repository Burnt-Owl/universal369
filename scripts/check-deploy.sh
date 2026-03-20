#!/usr/bin/env bash
# scripts/check-deploy.sh — Pre/post deployment health check for universal369.com
# Usage: ./scripts/check-deploy.sh

set -euo pipefail

VPS_HOST="187.77.208.156"
VPS_PORT="2222"
VPS_USER="root"
VPS_PATH="/home/universal369.com/public_html"
SSH_KEY="${HOME}/.ssh/id_ed25519"
SITE_URL="https://universal369.com"

FILES=("index.html" "cosmic-energy-enhanced.mp4")

PASS=0; FAIL=0

ok()   { echo "[PASS] $*"; ((PASS++)); }
fail() { echo "[FAIL] $*"; ((FAIL++)); }

echo "=== Deployment Health Check: universal369.com ==="
echo ""

# 1. SSH key present
echo "[1] SSH key"
if [[ -f "${SSH_KEY}" ]]; then
    ok "Key found: ${SSH_KEY}"
else
    fail "Key missing: ${SSH_KEY}"
fi

# 2. SSH connectivity
echo "[2] SSH connectivity to ${VPS_HOST}:${VPS_PORT}"
if ssh -i "${SSH_KEY}" -p "${VPS_PORT}" \
       -o StrictHostKeyChecking=accept-new \
       -o ConnectTimeout=8 \
       -o BatchMode=yes \
       "${VPS_USER}@${VPS_HOST}" "echo ok" &>/dev/null; then
    ok "SSH connection successful"
else
    fail "SSH connection failed — check key and network"
fi

# 3. Remote files (show size if present)
echo "[3] Remote files on VPS"
for f in "${FILES[@]}"; do
    REMOTE_FILE="${VPS_PATH}/${f}"
    SIZE=$(ssh -i "${SSH_KEY}" -p "${VPS_PORT}" \
               -o StrictHostKeyChecking=accept-new \
               -o ConnectTimeout=8 \
               -o BatchMode=yes \
               "${VPS_USER}@${VPS_HOST}" \
               "stat -c '%s' '${REMOTE_FILE}' 2>/dev/null || echo missing" 2>/dev/null || echo "missing")
    if [[ "${SIZE}" != "missing" ]]; then
        ok "${f} — ${SIZE} bytes"
    else
        fail "${f} NOT found at ${REMOTE_FILE}"
    fi
done

# 4. Live HTTP status
echo "[4] Live site"
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${SITE_URL}" || echo "000")
    if [[ "${HTTP_CODE}" == "200" ]]; then
        ok "${SITE_URL} → HTTP ${HTTP_CODE}"
    else
        fail "${SITE_URL} → HTTP ${HTTP_CODE}"
    fi
else
    echo "[SKIP] curl not installed — skipping HTTP check"
fi

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
