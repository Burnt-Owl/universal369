#!/usr/bin/env bash
# sync-linux.sh — Push/pull deployment for universal369.com
# Usage:
#   ./sync-linux.sh push   — deploy local files to VPS
#   ./sync-linux.sh pull   — fetch live files from VPS to local

set -euo pipefail

# ── CONFIGURATION ──────────────────────────────────────────
VPS_HOST="187.77.208.156"          # ← Set your VPS IP here
VPS_PORT="2222"
VPS_USER="root"
VPS_PATH="/home/universal369.com/public_html"
SSH_KEY="${HOME}/.ssh/id_ed25519"
SITE_URL="https://universal369.com"
# ───────────────────────────────────────────────────────────

FILES=(
    "index.html"
    "cosmic-energy-enhanced.mp4"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color helpers (graceful fallback if tput unavailable)
if command -v tput &>/dev/null && tput colors &>/dev/null 2>&1; then
    GREEN=$(tput setaf 2); RED=$(tput setaf 1); RESET=$(tput sgr0); BOLD=$(tput bold)
else
    GREEN=""; RED=""; RESET=""; BOLD=""
fi

ok()   { echo "${GREEN}[OK]${RESET}  $*"; }
fail() { echo "${RED}[FAIL]${RESET} $*" >&2; }
info() { echo "${BOLD}[--]${RESET}  $*"; }

SSH_OPTS=(-i "${SSH_KEY}" -p "${VPS_PORT}" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
SCP_OPTS=(-i "${SSH_KEY}" -P "${VPS_PORT}" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)

check_ssh_key() {
    if [[ ! -f "${SSH_KEY}" ]]; then
        fail "SSH key not found: ${SSH_KEY}"
        exit 1
    fi
}

check_local_files() {
    local missing=0
    for f in "${FILES[@]}"; do
        if [[ ! -f "${SCRIPT_DIR}/${f}" ]]; then
            fail "Local file missing: ${SCRIPT_DIR}/${f}"
            missing=1
        fi
    done
    [[ $missing -eq 0 ]] || exit 1
}

cmd_push() {
    info "=== PUSH: local → VPS (${VPS_HOST}) ==="
    check_ssh_key
    check_local_files

    for f in "${FILES[@]}"; do
        info "Uploading ${f} ..."
        scp "${SCP_OPTS[@]}" "${SCRIPT_DIR}/${f}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/${f}"
        ok "${f} uploaded"
    done

    info "Setting remote permissions ..."
    local chmod_args=""
    for f in "${FILES[@]}"; do
        chmod_args+=" ${VPS_PATH}/${f}"
    done
    ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "chmod 644${chmod_args}"
    ok "Permissions set (644)"

    # Verify live site (soft warning, not a hard failure)
    if command -v curl &>/dev/null; then
        info "Checking live site ..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${SITE_URL}" || echo "000")
        if [[ "${HTTP_CODE}" == "200" ]]; then
            ok "Site live — ${SITE_URL} returned HTTP ${HTTP_CODE}"
        else
            echo "${RED}[WARN]${RESET} ${SITE_URL} returned HTTP ${HTTP_CODE} (may need DNS propagation or SSL setup)"
        fi
    fi

    echo ""
    ok "Push complete."
}

cmd_pull() {
    info "=== PULL: VPS (${VPS_HOST}) → local ==="
    check_ssh_key

    for f in "${FILES[@]}"; do
        info "Downloading ${f} ..."
        scp "${SCP_OPTS[@]}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/${f}" "${SCRIPT_DIR}/${f}"
        ok "${f} → ${SCRIPT_DIR}/${f}"
    done

    echo ""
    ok "Pull complete."
}

usage() {
    echo "Usage: $0 <push|pull>"
    echo ""
    echo "  push  — Upload local files to VPS"
    echo "  pull  — Download VPS files to local"
    echo ""
    echo "Configuration (edit top of this script):"
    echo "  VPS_HOST = ${VPS_HOST}"
    echo "  VPS_PATH = ${VPS_PATH}"
    echo "  SSH_KEY  = ${SSH_KEY}"
}

case "${1:-}" in
    push) cmd_push ;;
    pull) cmd_pull ;;
    *)    usage; exit 1 ;;
esac
