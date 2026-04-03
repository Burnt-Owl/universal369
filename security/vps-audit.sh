#!/usr/bin/env bash
# VPS Security Audit + Hardening Script
# Run: ssh -p 2222 root@187.77.208.156 "bash -s" < vps-audit.sh
# Or:  ssh -p 2222 root@187.77.208.156 < vps-audit.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}[OK]${RESET} $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
fail() { echo -e "${RED}[FAIL]${RESET} $*"; }
info() { echo -e "${CYAN}[INFO]${RESET} $*"; }

echo ""
echo "================================================"
echo "  VPS Security Audit — 187.77.208.156"
echo "  $(date)"
echo "================================================"
echo ""

# ── 1. UFW ─────────────────────────────────────────
echo "── Firewall (UFW) ──────────────────────────────"
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        ok "UFW active"
        ufw status numbered
    else
        fail "UFW is INACTIVE — enabling now..."
        ufw --force enable
        ok "UFW enabled"
    fi
else
    fail "UFW not installed"
fi
echo ""

# ── 2. Open ports sanity check ──────────────────────
echo "── Open Ports ──────────────────────────────────"
ss -tlnp | grep LISTEN
echo ""
UNEXPECTED=$(ss -tlnp | grep LISTEN | grep -v -E ':(22|80|443|2222|8090)\s' || true)
if [ -n "$UNEXPECTED" ]; then
    warn "Unexpected listening ports detected:"
    echo "$UNEXPECTED"
else
    ok "Only expected ports are open (22/80/443/2222/8090)"
fi
echo ""

# ── 3. fail2ban ─────────────────────────────────────
echo "── fail2ban ────────────────────────────────────"
if systemctl is-active --quiet fail2ban; then
    ok "fail2ban is running"
    fail2ban-client status sshd 2>/dev/null || warn "sshd jail not configured"
    BANNED=$(fail2ban-client status sshd 2>/dev/null | grep "Banned IP" | awk -F: '{print $2}' | xargs)
    if [ -z "$BANNED" ]; then
        ok "No currently banned IPs"
    else
        warn "Banned IPs: $BANNED"
    fi
else
    fail "fail2ban is NOT running — starting..."
    systemctl start fail2ban
    systemctl enable fail2ban
    ok "fail2ban started and enabled"
fi
echo ""

# ── 4. fail2ban whitelist ───────────────────────────
echo "── fail2ban Whitelist ──────────────────────────"
WHITELIST_FILE="/etc/fail2ban/jail.d/whitelist.conf"
if [ -f "$WHITELIST_FILE" ]; then
    ok "Whitelist exists: $WHITELIST_FILE"
    cat "$WHITELIST_FILE"
else
    warn "Whitelist missing — creating for 104.234.212.0/24 (Windows IP range)..."
    cat > "$WHITELIST_FILE" << 'EOF'
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 104.234.212.0/24
EOF
    ok "Whitelist created"
fi
echo ""

# ── 5. SSH hardening ────────────────────────────────
echo "── SSH Config ──────────────────────────────────"
SSHD_CONFIG="/etc/ssh/sshd_config"

check_ssh_setting() {
    local key="$1" expected="$2"
    local val
    val=$(grep -i "^${key}" "$SSHD_CONFIG" 2>/dev/null | awk '{print $2}' | tail -1)
    if [ "$val" = "$expected" ]; then
        ok "$key = $val"
    else
        warn "$key = '${val:-unset}' (expected: $expected)"
    fi
}

check_ssh_setting "PermitRootLogin" "prohibit-password"
check_ssh_setting "PasswordAuthentication" "no"
check_ssh_setting "PubkeyAuthentication" "yes"
check_ssh_setting "PermitEmptyPasswords" "no"
check_ssh_setting "X11Forwarding" "no"
check_ssh_setting "MaxAuthTries" "3"

# Ensure PasswordAuthentication is off
if grep -q "^PasswordAuthentication yes" "$SSHD_CONFIG"; then
    warn "PasswordAuthentication is YES — disabling..."
    sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' "$SSHD_CONFIG"
    systemctl reload sshd
    ok "PasswordAuthentication disabled"
fi

# Ensure MaxAuthTries is set
if ! grep -q "^MaxAuthTries" "$SSHD_CONFIG"; then
    warn "MaxAuthTries not set — setting to 3..."
    echo "MaxAuthTries 3" >> "$SSHD_CONFIG"
    systemctl reload sshd
    ok "MaxAuthTries set to 3"
fi
echo ""

# ── 6. SSL certs ────────────────────────────────────
echo "── SSL Certificates ────────────────────────────"
if command -v certbot &>/dev/null; then
    certbot certificates 2>/dev/null || warn "certbot returned error"
else
    info "certbot not in PATH — SSL managed by CyberPanel/LiteSpeed"
fi
echo ""

# ── 7. File permissions ─────────────────────────────
echo "── Site File Permissions ───────────────────────"
SITE_DIR="/home/universal369.com/public_html"
if [ -d "$SITE_DIR" ]; then
    ls -la "$SITE_DIR"
    # Fix permissions if wrong
    find "$SITE_DIR" -type f -not -perm 644 -exec chmod 644 {} \; 2>/dev/null && ok "All files set to 644"
    find "$SITE_DIR" -type d -not -perm 755 -exec chmod 755 {} \; 2>/dev/null && ok "All dirs set to 755"
else
    warn "Site directory not found: $SITE_DIR"
fi
echo ""

# ── 8. Recent logins ────────────────────────────────
echo "── Recent Logins ───────────────────────────────"
last -15
echo ""

# ── 9. Suspicious processes ─────────────────────────
echo "── Process Check ───────────────────────────────"
SUSPICIOUS=$(ps aux | grep -E "(miner|cryptonight|xmrig|monero|stratum)" | grep -v grep || true)
if [ -n "$SUSPICIOUS" ]; then
    fail "SUSPICIOUS PROCESSES FOUND:"
    echo "$SUSPICIOUS"
else
    ok "No suspicious processes detected"
fi
echo ""

# ── 10. Cron integrity ──────────────────────────────
echo "── Cron Jobs ───────────────────────────────────"
info "Root crontab:"
crontab -l 2>/dev/null || echo "(empty)"
info "System crons in /etc/cron.d/:"
ls -la /etc/cron.d/ 2>/dev/null
if [ -f /etc/cron.d/keep-ssh-open ]; then
    ok "keep-ssh-open cron present:"
    cat /etc/cron.d/keep-ssh-open
fi
echo ""

# ── 11. Unattended upgrades ─────────────────────────
echo "── Auto Security Updates ───────────────────────"
if dpkg -l | grep -q unattended-upgrades 2>/dev/null; then
    ok "unattended-upgrades installed"
    systemctl is-active unattended-upgrades && ok "Service is active" || warn "Service not active"
else
    warn "unattended-upgrades not installed — installing..."
    apt-get install -y unattended-upgrades -qq
    systemctl enable unattended-upgrades
    systemctl start unattended-upgrades
    ok "unattended-upgrades installed and enabled"
fi
echo ""

echo "================================================"
echo "  Audit complete"
echo "================================================"
