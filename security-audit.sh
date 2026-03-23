#!/usr/bin/env bash
# =============================================================================
# VPS Security Audit Script — universal369.com
# =============================================================================
# Usage: ./security-audit.sh [user@host] [port] [key_path]
#
# Environment variable overrides (use instead of args for CI/automation):
#   VPS_HOST   — SSH target, e.g. root@<YOUR_VPS_IP>
#   VPS_PORT   — SSH port (default: 22)
#   VPS_KEY    — path to SSH private key (default: ~/.ssh/id_ed25519)
#   SITE_HOST  — hostname for curl header checks (default: universal369.com)
#   SITE_PATH  — webroot path on server (default: /var/www/html)
#
# This script is READ-ONLY — it makes no changes to the server.
# Output is printed to stdout and saved to vps-audit-TIMESTAMP.txt
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config (args > env vars > defaults)
# ---------------------------------------------------------------------------
VPS_HOST="${1:-${VPS_HOST:-}}"
VPS_PORT="${2:-${VPS_PORT:-22}}"
VPS_KEY="${3:-${VPS_KEY:-$HOME/.ssh/id_ed25519}}"
SITE_HOST="${SITE_HOST:-universal369.com}"
SITE_PATH="${SITE_PATH:-/var/www/html}"
REPORT="vps-audit-$(date +%Y%m%d-%H%M%S).txt"

if [[ -z "$VPS_HOST" ]]; then
  echo "ERROR: No SSH target specified."
  echo "Usage: ./security-audit.sh user@host [port] [key_path]"
  echo "Or set VPS_HOST environment variable."
  exit 1
fi

SSH_OPTS="-p $VPS_PORT -i $VPS_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes"
SSH="ssh $SSH_OPTS $VPS_HOST"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CRITICAL=0; HIGH=0; MEDIUM=0; LOW=0; PASS=0
FINDINGS=()

flag() {
  local level="$1"; shift
  local msg="$*"
  case "$level" in
    CRITICAL) ((CRITICAL++)) ;;
    HIGH)     ((HIGH++))     ;;
    MEDIUM)   ((MEDIUM++))   ;;
    LOW)      ((LOW++))      ;;
    PASS)     ((PASS++))     ;;
  esac
  FINDINGS+=("[$level] $msg")
}

section() { printf '\n\033[1;34m=== %s ===\033[0m\n' "$*"; }
info()    { printf '  \033[0;36m%s\033[0m\n' "$*"; }

remote() { $SSH "$@" 2>/dev/null; }

# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------
echo "============================================================"
echo " VPS Security Audit"
echo " Host: $VPS_HOST | Port: $VPS_PORT"
echo " Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

if ! $SSH "echo 'SSH connection OK'" > /dev/null 2>&1; then
  echo "ERROR: Cannot connect to $VPS_HOST on port $VPS_PORT"
  echo "Check VPS_HOST, VPS_PORT, and VPS_KEY settings."
  exit 2
fi
echo "Connection: OK"

exec > >(tee -a "$REPORT") 2>&1

# ===========================================================================
# SECTION 1: SSH CONFIGURATION
# ===========================================================================
section "1. SSH CONFIGURATION"

SSH_CONFIG=$(remote "sshd -T 2>/dev/null || grep -v '^#' /etc/ssh/sshd_config | grep -v '^$'")
info "Raw sshd effective config (key fields):"
remote "sshd -T 2>/dev/null | grep -iE '(permitrootlogin|passwordauthentication|pubkeyauthentication|port|banner|clientaliveinterval|clientalivecountmax|logingracetime|maxauthtries|permitemptypasswords)'" | sed 's/^/    /' || true

# PermitRootLogin
ROOT_LOGIN=$(remote "sshd -T 2>/dev/null | grep -i 'permitrootlogin'" | awk '{print $2}' | head -1)
if [[ "$ROOT_LOGIN" == "yes" ]]; then
  flag HIGH "PermitRootLogin is 'yes' — root can log in with any auth method. Change to 'prohibit-password'."
elif [[ "$ROOT_LOGIN" == "prohibit-password" || "$ROOT_LOGIN" == "without-password" ]]; then
  flag PASS "PermitRootLogin is '$ROOT_LOGIN' — password root login blocked, key auth allowed."
elif [[ "$ROOT_LOGIN" == "no" ]]; then
  flag PASS "PermitRootLogin is 'no' — root login fully disabled."
else
  flag MEDIUM "PermitRootLogin value unclear ('$ROOT_LOGIN') — verify manually."
fi

# PasswordAuthentication
PASSWD_AUTH=$(remote "sshd -T 2>/dev/null | grep -i '^passwordauthentication'" | awk '{print $2}' | head -1)
if [[ "$PASSWD_AUTH" == "yes" ]]; then
  flag HIGH "PasswordAuthentication is 'yes' — brute-force attacks possible. Disable it."
else
  flag PASS "PasswordAuthentication is disabled — key-only auth enforced."
fi

# PubkeyAuthentication
PUBKEY=$(remote "sshd -T 2>/dev/null | grep -i '^pubkeyauthentication'" | awk '{print $2}' | head -1)
if [[ "$PUBKEY" != "yes" ]]; then
  flag HIGH "PubkeyAuthentication is not 'yes' — key-based login may be broken."
else
  flag PASS "PubkeyAuthentication is enabled."
fi

# ClientAliveInterval
CLIENT_INTERVAL=$(remote "sshd -T 2>/dev/null | grep -i '^clientaliveinterval'" | awk '{print $2}' | head -1)
if [[ -z "$CLIENT_INTERVAL" || "$CLIENT_INTERVAL" == "0" ]]; then
  flag MEDIUM "No ClientAliveInterval set — idle sessions never time out."
else
  flag PASS "ClientAliveInterval is $CLIENT_INTERVAL seconds."
fi

# MaxAuthTries
MAX_TRIES=$(remote "sshd -T 2>/dev/null | grep -i '^maxauthtries'" | awk '{print $2}' | head -1)
if [[ -n "$MAX_TRIES" && "$MAX_TRIES" -gt 5 ]]; then
  flag MEDIUM "MaxAuthTries is $MAX_TRIES — consider reducing to 3."
elif [[ -n "$MAX_TRIES" ]]; then
  flag PASS "MaxAuthTries is $MAX_TRIES."
else
  flag LOW "MaxAuthTries not explicitly set — using system default (6)."
fi

# LoginGraceTime
GRACE=$(remote "sshd -T 2>/dev/null | grep -i '^logingracetime'" | awk '{print $2}' | head -1)
if [[ -n "$GRACE" && "$GRACE" -gt 60 ]]; then
  flag LOW "LoginGraceTime is ${GRACE}s — consider reducing to 30s."
elif [[ -n "$GRACE" ]]; then
  flag PASS "LoginGraceTime is ${GRACE}s."
fi

# Banner
BANNER=$(remote "sshd -T 2>/dev/null | grep -i '^banner'" | awk '{print $2}' | head -1)
if [[ -z "$BANNER" || "$BANNER" == "none" ]]; then
  flag LOW "No SSH banner configured — consider adding a legal warning notice."
else
  flag PASS "SSH banner configured: $BANNER"
fi

# ===========================================================================
# SECTION 2: UFW FIREWALL
# ===========================================================================
section "2. UFW FIREWALL"

UFW_STATUS=$(remote "ufw status verbose 2>/dev/null || echo 'UFW not available'")
info "UFW status:"
echo "$UFW_STATUS" | sed 's/^/    /'

if echo "$UFW_STATUS" | grep -qi "inactive\|not available"; then
  flag HIGH "UFW is inactive or not installed — no firewall protection."
else
  flag PASS "UFW is active."
fi

# Check CyberPanel port 8090 exposed to world
if echo "$UFW_STATUS" | grep -qE '8090.*Anywhere|8090.*0\.0\.0\.0'; then
  flag HIGH "Port 8090 (CyberPanel admin) is open to 0.0.0.0/0 — restrict to your trusted IP."
elif echo "$UFW_STATUS" | grep -q "8090"; then
  flag PASS "Port 8090 (CyberPanel) has restricted access."
else
  info "Port 8090 not visible in UFW rules — may be blocked or CyberPanel not present."
fi

# List all listening ports
info "All listening ports (ss -tlnp):"
remote "ss -tlnp" | sed 's/^/    /'

# SSH rate limiting
if echo "$UFW_STATUS" | grep -qiE "(limit.*$VPS_PORT|$VPS_PORT.*limit)"; then
  flag PASS "SSH port $VPS_PORT has UFW rate limiting."
else
  flag MEDIUM "SSH port $VPS_PORT is not rate-limited in UFW — consider 'ufw limit $VPS_PORT/tcp'."
fi

# ===========================================================================
# SECTION 3: FAIL2BAN
# ===========================================================================
section "3. FAIL2BAN"

F2B_STATUS=$(remote "fail2ban-client status 2>/dev/null || echo 'fail2ban not running'")
info "fail2ban status:"
echo "$F2B_STATUS" | sed 's/^/    /'

if echo "$F2B_STATUS" | grep -qi "not running\|command not found"; then
  flag HIGH "fail2ban is not running — no automated IP banning in place."
else
  flag PASS "fail2ban is running."

  # SSH jail
  if remote "fail2ban-client status sshd" > /dev/null 2>&1; then
    flag PASS "fail2ban sshd jail is active."
    info "fail2ban sshd jail details:"
    remote "fail2ban-client status sshd 2>/dev/null" | sed 's/^/    /'
  else
    flag HIGH "fail2ban sshd jail is NOT active — SSH brute-force not protected."
  fi

  # LiteSpeed jail
  if remote "fail2ban-client status litespeed" > /dev/null 2>&1; then
    flag PASS "fail2ban litespeed jail is active."
  else
    flag MEDIUM "fail2ban litespeed jail not found — web server attacks not blocked."
  fi

  # CyberPanel jail
  if remote "fail2ban-client status cyberpanel" > /dev/null 2>&1; then
    flag PASS "fail2ban cyberpanel jail is active."
  else
    flag MEDIUM "fail2ban cyberpanel jail not found — admin panel brute-force not blocked."
  fi
fi

# Ban time check
info "fail2ban timing config:"
remote "grep -hE '^(bantime|findtime|maxretry)' /etc/fail2ban/jail.local /etc/fail2ban/jail.conf 2>/dev/null | head -10" | sed 's/^/    /' || true

BANTIME=$(remote "grep -hE '^bantime\s*=' /etc/fail2ban/jail.local /etc/fail2ban/jail.conf 2>/dev/null | head -1 | grep -oE '[0-9]+'")
if [[ -n "$BANTIME" && "$BANTIME" -lt 3600 ]]; then
  flag MEDIUM "fail2ban bantime is ${BANTIME}s — consider increasing to 3600+ seconds."
elif [[ -n "$BANTIME" ]]; then
  flag PASS "fail2ban bantime is ${BANTIME}s."
fi

MAXRETRY=$(remote "grep -hE '^maxretry\s*=' /etc/fail2ban/jail.local /etc/fail2ban/jail.conf 2>/dev/null | head -1 | grep -oE '[0-9]+'")
if [[ -n "$MAXRETRY" && "$MAXRETRY" -gt 5 ]]; then
  flag MEDIUM "fail2ban maxretry is $MAXRETRY — consider reducing to 5 or less."
elif [[ -n "$MAXRETRY" ]]; then
  flag PASS "fail2ban maxretry is $MAXRETRY."
fi

# Whitelist review
info "fail2ban whitelist (review for stale entries):"
remote "cat /etc/fail2ban/jail.d/whitelist.conf 2>/dev/null || echo '  (no whitelist.conf found)'" | sed 's/^/    /'
flag LOW "Review fail2ban whitelist: ensure whitelisted CIDRs are still necessary and correctly scoped."

# ===========================================================================
# SECTION 4: CRON JOBS REVIEW
# ===========================================================================
section "4. CRON JOBS"

info "Content of /etc/cron.d/keep-ssh-open:"
CRON_CONTENT=$(remote "cat /etc/cron.d/keep-ssh-open 2>/dev/null || echo '(file not found)'")
echo "$CRON_CONTENT" | sed 's/^/    /'

# Flag dangerous patterns in cron
if echo "$CRON_CONTENT" | grep -qE '(curl|wget|bash\s+-c|python\s+-c|perl\s+-e|nc\s+|/dev/tcp)'; then
  flag HIGH "keep-ssh-open cron contains network fetch commands (curl/wget/bash -c) — potential persistence/C2 mechanism. Inspect immediately."
elif echo "$CRON_CONTENT" | grep -q "file not found"; then
  flag PASS "/etc/cron.d/keep-ssh-open not found — no special SSH cron present."
else
  flag LOW "/etc/cron.d/keep-ssh-open exists — verify it is still needed and contains only benign UFW/iptables commands."
fi

info "All cron.d files:"
remote "ls -la /etc/cron.d/ 2>/dev/null" | sed 's/^/    /'

info "Root crontab:"
remote "crontab -l 2>/dev/null || echo '  (empty)'" | sed 's/^/    /'

info "System crontab (/etc/crontab):"
remote "cat /etc/crontab 2>/dev/null" | sed 's/^/    /'

# ===========================================================================
# SECTION 5: CYBERPANEL & WEB SERVER
# ===========================================================================
section "5. CYBERPANEL & LITESPEED"

info "CyberPanel version:"
remote "cat /usr/local/CyberCP/version.txt 2>/dev/null || \
        /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py version 2>/dev/null || \
        echo '(could not determine version)'" | sed 's/^/    /'

info "LiteSpeed / lscpd service status:"
remote "systemctl is-active lscpd 2>/dev/null && systemctl status lscpd --no-pager -l 2>/dev/null | head -5 || \
        systemctl is-active lsws 2>/dev/null && systemctl status lsws --no-pager -l 2>/dev/null | head -5 || \
        echo '(lscpd/lsws not found via systemctl)'" | sed 's/^/    /'

info "Port 8090 binding:"
PORT_8090=$(remote "ss -tlnp 2>/dev/null | grep ':8090'")
echo "$PORT_8090" | sed 's/^/    /'
if echo "$PORT_8090" | grep -qE '0\.0\.0\.0:8090|\*:8090'; then
  flag HIGH "CyberPanel port 8090 is bound to 0.0.0.0 — accessible from any IP if UFW allows it. Restrict via UFW to your trusted IP."
elif [[ -n "$PORT_8090" ]]; then
  flag PASS "Port 8090 is not world-bound (likely localhost only)."
else
  flag LOW "Port 8090 not detected — CyberPanel may not be running or uses a different port."
fi

# ===========================================================================
# SECTION 6: OS & PACKAGE UPDATES
# ===========================================================================
section "6. OS & PACKAGE UPDATES"

info "OS version:"
remote "lsb_release -a 2>/dev/null || cat /etc/os-release 2>/dev/null | head -5" | sed 's/^/    /'

info "Kernel:"
remote "uname -r" | sed 's/^/    /'

info "Pending security updates:"
SECURITY_UPDATES=$(remote "apt-get -s upgrade 2>/dev/null | grep -cE '^Inst' || echo 0")
if [[ "$SECURITY_UPDATES" -gt 0 ]]; then
  flag HIGH "$SECURITY_UPDATES package(s) have available upgrades — run 'apt-get upgrade' to apply."
  remote "apt list --upgradable 2>/dev/null | grep -i security | head -10" | sed 's/^/    /'
else
  flag PASS "No pending upgrades detected (or apt unavailable)."
fi

info "Recent successful logins (last 10):"
remote "last -n 10 2>/dev/null" | sed 's/^/    /'

info "Recent failed login attempts (last 10):"
remote "lastb -n 10 2>/dev/null | head -11 || echo '  (lastb not available or no failures)'" | sed 's/^/    /'

# ===========================================================================
# SECTION 7: FILE PERMISSIONS
# ===========================================================================
section "7. FILE PERMISSIONS (webroot: $SITE_PATH)"

info "Webroot listing:"
remote "ls -la $SITE_PATH 2>/dev/null || echo '(path not found — set SITE_PATH env var)'" | sed 's/^/    /'

info "Files with incorrect permissions (should be 644):"
BAD_FILES=$(remote "find $SITE_PATH -type f ! -perm 644 -ls 2>/dev/null || true")
if [[ -n "$BAD_FILES" ]]; then
  echo "$BAD_FILES" | sed 's/^/    /'
  flag MEDIUM "Files found with non-644 permissions in webroot — run security-harden.sh to fix."
else
  flag PASS "All files in webroot have 644 permissions."
fi

info "Directories with incorrect permissions (should be 755):"
BAD_DIRS=$(remote "find $SITE_PATH -type d ! -perm 755 -ls 2>/dev/null || true")
if [[ -n "$BAD_DIRS" ]]; then
  echo "$BAD_DIRS" | sed 's/^/    /'
  flag MEDIUM "Directories found with non-755 permissions in webroot."
else
  flag PASS "All directories in webroot have 755 permissions."
fi

info "World-writable files (HIGH risk):"
WORLD_WRITABLE=$(remote "find $SITE_PATH -perm -o+w -ls 2>/dev/null || true")
if [[ -n "$WORLD_WRITABLE" ]]; then
  echo "$WORLD_WRITABLE" | sed 's/^/    /'
  flag HIGH "World-writable files found in webroot — fix immediately."
else
  flag PASS "No world-writable files in webroot."
fi

# ===========================================================================
# SECTION 8: WEB SECURITY HEADERS
# ===========================================================================
section "8. WEB SECURITY HEADERS"

info "HTTP response headers (via localhost curl):"
HEADERS=$(remote "curl -sI http://localhost/ -H 'Host: $SITE_HOST' 2>/dev/null || echo '(curl unavailable)'")
echo "$HEADERS" | sed 's/^/    /'

info "HTTPS response headers (via localhost curl):"
HTTPS_HEADERS=$(remote "curl -sI https://localhost/ -H 'Host: $SITE_HOST' -k 2>/dev/null || echo '(curl unavailable)'")
echo "$HTTPS_HEADERS" | sed 's/^/    /'

# Check each header (check HTTPS first, fall back to HTTP)
COMBINED_HEADERS="$HTTPS_HEADERS
$HEADERS"

if echo "$COMBINED_HEADERS" | grep -qi "^x-frame-options"; then
  flag PASS "X-Frame-Options header present."
else
  flag MEDIUM "X-Frame-Options header missing — add 'X-Frame-Options: SAMEORIGIN'."
fi

if echo "$COMBINED_HEADERS" | grep -qi "^x-content-type-options"; then
  flag PASS "X-Content-Type-Options header present."
else
  flag MEDIUM "X-Content-Type-Options header missing — add 'X-Content-Type-Options: nosniff'."
fi

if echo "$COMBINED_HEADERS" | grep -qi "^strict-transport-security"; then
  flag PASS "Strict-Transport-Security (HSTS) header present."
else
  flag HIGH "HSTS header missing — add 'Strict-Transport-Security: max-age=31536000; includeSubDomains'."
fi

if echo "$COMBINED_HEADERS" | grep -qi "^content-security-policy"; then
  flag PASS "Content-Security-Policy header present."
else
  flag MEDIUM "Content-Security-Policy header missing."
fi

# HTTP → HTTPS redirect
HTTP_LOCATION=$(remote "curl -sI http://localhost/ -H 'Host: $SITE_HOST' 2>/dev/null | grep -i '^location'" || true)
if echo "$HTTP_LOCATION" | grep -qi "https://"; then
  flag PASS "HTTP redirects to HTTPS."
else
  flag HIGH "HTTP does not redirect to HTTPS — enforce HTTPS redirect."
fi

# .htaccess check
info ".htaccess in webroot:"
remote "cat $SITE_PATH/.htaccess 2>/dev/null || echo '  (no .htaccess found)'" | sed 's/^/    /'

# ===========================================================================
# SECTION 9: SSL/TLS CERTIFICATE
# ===========================================================================
section "9. SSL/TLS CERTIFICATE"

info "Certificate details:"
CERT_INFO=$(remote "echo | openssl s_client -connect localhost:443 -servername $SITE_HOST 2>/dev/null | openssl x509 -noout -dates -subject -issuer 2>/dev/null || echo '(openssl check failed)'")
echo "$CERT_INFO" | sed 's/^/    /'

# Check expiry
CERT_END=$(remote "echo | openssl s_client -connect localhost:443 -servername $SITE_HOST 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2" || true)
if [[ -n "$CERT_END" ]]; then
  CERT_EPOCH=$(date -d "$CERT_END" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$CERT_END" +%s 2>/dev/null || echo 0)
  NOW_EPOCH=$(date +%s)
  DAYS_LEFT=$(( (CERT_EPOCH - NOW_EPOCH) / 86400 ))

  if [[ "$DAYS_LEFT" -le 0 ]]; then
    flag CRITICAL "SSL certificate has EXPIRED — site will show security errors."
  elif [[ "$DAYS_LEFT" -le 14 ]]; then
    flag HIGH "SSL certificate expires in $DAYS_LEFT days — renew immediately."
  elif [[ "$DAYS_LEFT" -le 30 ]]; then
    flag MEDIUM "SSL certificate expires in $DAYS_LEFT days — plan renewal soon."
  else
    flag PASS "SSL certificate valid for $DAYS_LEFT more days."
  fi
else
  flag MEDIUM "Could not verify SSL certificate expiry — check manually."
fi

# Let's Encrypt / certbot
info "Certbot certificates:"
remote "certbot certificates 2>/dev/null | head -20 || echo '  (certbot not found)'" | sed 's/^/    /'

# ===========================================================================
# SECTION 10: RUNNING SERVICES
# ===========================================================================
section "10. RUNNING SERVICES"

info "Active services:"
SERVICES=$(remote "systemctl list-units --type=service --state=running --no-pager --plain 2>/dev/null | awk '{print \$1}'")
echo "$SERVICES" | sed 's/^/    /'

EXPECTED="sshd|ssh|lscpd|lsws|litespeed|fail2ban|ufw|cron|crond|rsyslog|systemd|dbus|networkd|resolved|journald|logind|getty|cyberpanel|mysql|mariadb|php"
UNEXPECTED=$(echo "$SERVICES" | grep -vE "$EXPECTED" | grep -v "^$" | grep -v "^UNIT" || true)
if [[ -n "$UNEXPECTED" ]]; then
  echo "  Unexpected services (review these):"
  echo "$UNEXPECTED" | sed 's/^/    /'
  flag MEDIUM "Unexpected services running — review list above and disable anything unnecessary."
else
  flag PASS "No obviously unexpected services detected."
fi

# ===========================================================================
# SUMMARY
# ===========================================================================
printf '\n\033[1;33m============================================================\033[0m\n'
printf '\033[1;33m AUDIT SUMMARY\033[0m\n'
printf '\033[1;33m============================================================\033[0m\n'

for f in "${FINDINGS[@]}"; do
  case "$f" in
    "[CRITICAL]"*) printf '\033[1;31m  %s\033[0m\n' "$f" ;;
    "[HIGH]"*)     printf '\033[0;31m  %s\033[0m\n' "$f" ;;
    "[MEDIUM]"*)   printf '\033[0;33m  %s\033[0m\n' "$f" ;;
    "[LOW]"*)      printf '\033[0;36m  %s\033[0m\n' "$f" ;;
    "[PASS]"*)     printf '\033[0;32m  %s\033[0m\n' "$f" ;;
  esac
done

printf '\n'
printf '  CRITICAL: %d\n' "$CRITICAL"
printf '  HIGH:     %d\n' "$HIGH"
printf '  MEDIUM:   %d\n' "$MEDIUM"
printf '  LOW:      %d\n' "$LOW"
printf '  PASS:     %d\n' "$PASS"
printf '\n'
printf '  Full report saved to: %s\n' "$REPORT"
printf '\033[1;33m============================================================\033[0m\n'
