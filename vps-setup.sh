#!/usr/bin/env bash
# vps-setup.sh — One-time VPS setup for universal369.com
# Usage: ssh -p 2222 root@187.77.208.156 "bash -s" < vps-setup.sh

set -euo pipefail

SITE_ROOT="/home/universal369.com/public_html"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "========================================="
echo " universal369.com VPS Setup"
echo " ${TIMESTAMP}"
echo "========================================="

# 1. Create site directory
echo "[1/4] Creating site root: ${SITE_ROOT}"
mkdir -p "${SITE_ROOT}"
chmod 755 "${SITE_ROOT}"
echo "      OK — directory exists and is world-readable"

# 2. Set ownership
echo "[2/4] Setting ownership"
chown -R root:root "${SITE_ROOT}"
echo "      OK — owned by root:root"

# 3. Check UFW for port 2222 (idempotent)
echo "[3/4] Checking UFW for port 2222"
if command -v ufw &>/dev/null; then
    if ufw status | grep -q "2222"; then
        echo "      OK — port 2222 already open in UFW"
    else
        ufw allow 2222/tcp
        echo "      OK — port 2222 added to UFW"
    fi
else
    echo "      SKIP — ufw not found (OK on some Hostinger images)"
fi

# 4. Write placeholder only if directory is empty
echo "[4/4] Checking for existing content"
if [ -z "$(ls -A "${SITE_ROOT}" 2>/dev/null)" ]; then
    cat > "${SITE_ROOT}/index.html" <<'PLACEHOLDER'
<!DOCTYPE html>
<html><head><title>universal369.com</title></head>
<body><p>Site coming soon.</p></body></html>
PLACEHOLDER
    chmod 644 "${SITE_ROOT}/index.html"
    echo "      OK — placeholder index.html written"
else
    echo "      OK — directory already has content, skipping placeholder"
fi

echo ""
echo "========================================="
echo " Setup complete. Ready to deploy."
echo "========================================="
echo " Site root : ${SITE_ROOT}"
echo " Next step : ./sync-linux.sh push"
echo "========================================="
