#!/usr/bin/env bash
# =============================================================================
# VPS Security Hardening Script — universal369.com
# =============================================================================
# REVIEW ALL COMMANDS BEFORE RUNNING. This script makes changes to the server.
#
# Usage: ./security-harden.sh [user@host] [port] [key_path]
#
# Environment variable overrides:
#   VPS_HOST      — SSH target, e.g. root@<YOUR_VPS_IP>
#   VPS_PORT      — SSH port (default: 22)
#   VPS_KEY       — path to SSH private key (default: ~/.ssh/id_ed25519)
#   SITE_PATH     — webroot path on server (default: /var/www/html)
#   TRUSTED_IP    — your trusted IP for CyberPanel access restriction
#   AUTO_APPLY=1  — skip per-section confirmation prompts (use with caution)
#
# Run sections individually by setting SECTIONS="1 3 5" etc. (default: all)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VPS_HOST="${1:-${VPS_HOST:-}}"
VPS_PORT="${2:-${VPS_PORT:-22}}"
VPS_KEY="${3:-${VPS_KEY:-$HOME/.ssh/id_ed25519}}"
SITE_PATH="${SITE_PATH:-/var/www/html}"
TRUSTED_IP="${TRUSTED_IP:-}"
AUTO_APPLY="${AUTO_APPLY:-0}"
SECTIONS="${SECTIONS:-1 2 3 4 5 6 7 8}"

if [[ -z "$VPS_HOST" ]]; then
  echo "ERROR: No SSH target specified."
  echo "Usage: ./security-harden.sh user@host [port] [key_path]"
  echo "Or set VPS_HOST environment variable."
  exit 1
fi

SSH_OPTS="-p $VPS_PORT -i $VPS_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
SSH="ssh $SSH_OPTS $VPS_HOST"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
remote() { $SSH "$@"; }

section() {
  printf '\n\033[1;34m=== HARDENING SECTION %s ===\033[0m\n' "$*"
}

confirm() {
  local prompt="$1"
  if [[ "$AUTO_APPLY" == "1" ]]; then
    echo "  [AUTO] $prompt → applying"
    return 0
  fi
  printf '\033[0;33m  Apply: %s\033[0m [y/N] ' "$prompt"
  read -r ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

skip_section() {
  local num="$1"
  if [[ "$SECTIONS" != *"$num"* ]]; then
    echo "  (skipping section $num — not in SECTIONS='$SECTIONS')"
    return 0
  fi
  return 1
}

warn() { printf '\033[0;33m  WARN: %s\033[0m\n' "$*"; }
ok()   { printf '\033[0;32m  OK:   %s\033[0m\n' "$*"; }
info() { printf '  INFO: %s\n' "$*"; }

# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------
echo "============================================================"
echo " VPS Security Hardening Script"
echo " Host: $VPS_HOST | Port: $VPS_PORT"
echo " Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""
echo "  IMPORTANT: Keep your current SSH session open."
echo "  Test all SSH changes in a SEPARATE terminal before closing this one."
echo ""

if ! $SSH "echo 'SSH connection OK'" > /dev/null 2>&1; then
  echo "ERROR: Cannot connect to $VPS_HOST on port $VPS_PORT"
  exit 2
fi
echo "  Connection: OK"

# ===========================================================================
# SECTION 1: SSH HARDENING
# ===========================================================================
skip_section 1 && true || {
section "1: SSH HARDENING"
info "Current sshd settings:"
remote "sshd -T 2>/dev/null | grep -iE '(permitrootlogin|passwordauthentication|logingracetime|clientaliveinterval|maxauthtries|banner)'" | sed 's/^/    /' || true

# 1a — Backup sshd_config
if confirm "Backup /etc/ssh/sshd_config"; then
  remote "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.\$(date +%Y%m%d-%H%M%S)"
  ok "sshd_config backed up."
fi

# 1b — PermitRootLogin prohibit-password
warn "Changing PermitRootLogin to 'prohibit-password' (keeps key auth, blocks password login)."
warn "If you use key auth, this is safe. If you ever used password auth to root, test first."
if confirm "Set PermitRootLogin to 'prohibit-password'"; then
  remote "sed -i 's/^PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && \
    grep -q '^PermitRootLogin' /etc/ssh/sshd_config || echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config"
  ok "PermitRootLogin set to prohibit-password."
fi

# 1c — PasswordAuthentication no
if confirm "Ensure PasswordAuthentication is 'no'"; then
  remote "sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    grep -q '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config"
  ok "PasswordAuthentication disabled."
fi

# 1d — ClientAliveInterval and ClientAliveCountMax
if confirm "Set ClientAliveInterval 300 / ClientAliveCountMax 2 (5-minute idle timeout)"; then
  remote "grep -q '^ClientAliveInterval' /etc/ssh/sshd_config && \
    sed -i 's/^ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config || \
    echo 'ClientAliveInterval 300' >> /etc/ssh/sshd_config
  grep -q '^ClientAliveCountMax' /etc/ssh/sshd_config && \
    sed -i 's/^ClientAliveCountMax.*/ClientAliveCountMax 2/' /etc/ssh/sshd_config || \
    echo 'ClientAliveCountMax 2' >> /etc/ssh/sshd_config"
  ok "Idle timeout set: 300s interval, 2 max count (10-minute max idle)."
fi

# 1e — MaxAuthTries
if confirm "Set MaxAuthTries 3"; then
  remote "grep -q '^MaxAuthTries' /etc/ssh/sshd_config && \
    sed -i 's/^MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config || \
    echo 'MaxAuthTries 3' >> /etc/ssh/sshd_config"
  ok "MaxAuthTries set to 3."
fi

# 1f — LoginGraceTime
if confirm "Set LoginGraceTime 30 (was likely 120s)"; then
  remote "grep -q '^LoginGraceTime' /etc/ssh/sshd_config && \
    sed -i 's/^LoginGraceTime.*/LoginGraceTime 30/' /etc/ssh/sshd_config || \
    echo 'LoginGraceTime 30' >> /etc/ssh/sshd_config"
  ok "LoginGraceTime set to 30 seconds."
fi

# 1g — Warning banner
if confirm "Add SSH login warning banner (/etc/ssh/sshd_banner)"; then
  remote "cat > /etc/ssh/sshd_banner << 'BANNER'
*******************************************************************
AUTHORIZED ACCESS ONLY. All connections are monitored and logged.
Unauthorized access is strictly prohibited and will be prosecuted.
*******************************************************************
BANNER
  grep -q '^Banner' /etc/ssh/sshd_config && \
    sed -i 's|^Banner.*|Banner /etc/ssh/sshd_banner|' /etc/ssh/sshd_config || \
    echo 'Banner /etc/ssh/sshd_banner' >> /etc/ssh/sshd_config"
  ok "SSH banner configured."
fi

# 1h — Reload sshd
warn "About to reload sshd. Keep this SSH session open and test in a second terminal."
if confirm "Reload sshd to apply changes (test in another terminal first!)"; then
  remote "sshd -t && systemctl reload sshd && echo 'sshd reloaded successfully'"
  ok "sshd reloaded."
fi
}

# ===========================================================================
# SECTION 2: FIREWALL (UFW)
# ===========================================================================
skip_section 2 && true || {
section "2: FIREWALL (UFW)"
info "Current UFW rules:"
remote "ufw status verbose 2>/dev/null" | sed 's/^/    /'

# 2a — Rate-limit SSH port
if confirm "Replace plain 'allow $VPS_PORT/tcp' with rate-limited 'limit $VPS_PORT/tcp'"; then
  remote "ufw delete allow $VPS_PORT/tcp 2>/dev/null || true
    ufw limit $VPS_PORT/tcp comment 'SSH rate-limited'
    ufw reload"
  ok "SSH port $VPS_PORT is now rate-limited."
fi

# 2b — Restrict CyberPanel port 8090
CURRENT_8090=$(remote "ufw status | grep 8090 | head -1" 2>/dev/null || echo "")
if echo "$CURRENT_8090" | grep -qE 'Anywhere|0\.0\.0\.0'; then
  warn "Port 8090 (CyberPanel admin) is open to the world."
  if [[ -z "$TRUSTED_IP" ]]; then
    printf '  Enter your trusted IP for CyberPanel access (or leave blank to skip): '
    read -r TRUSTED_IP
  fi
  if [[ -n "$TRUSTED_IP" ]]; then
    if confirm "Restrict port 8090 to $TRUSTED_IP only"; then
      remote "ufw delete allow 8090/tcp 2>/dev/null || true
        ufw delete allow 8090 2>/dev/null || true
        ufw allow from $TRUSTED_IP to any port 8090 proto tcp comment 'CyberPanel trusted IP only'
        ufw reload"
      ok "Port 8090 restricted to $TRUSTED_IP."
    fi
  else
    warn "Skipping port 8090 restriction — no trusted IP provided. Do this manually!"
  fi
else
  ok "Port 8090 already restricted (not open to world)."
fi

# 2c — Enable UFW logging
if confirm "Enable UFW logging (low verbosity)"; then
  remote "ufw logging low"
  ok "UFW logging enabled."
fi

info "Updated UFW rules:"
remote "ufw status verbose 2>/dev/null" | sed 's/^/    /'
}

# ===========================================================================
# SECTION 3: FAIL2BAN HARDENING
# ===========================================================================
skip_section 3 && true || {
section "3: FAIL2BAN"
info "Current fail2ban status:"
remote "fail2ban-client status 2>/dev/null" | sed 's/^/    /' || echo "  (fail2ban not running)"

# 3a — Write hardened jail config
if confirm "Write /etc/fail2ban/jail.d/hardened.conf (sshd jail on port $VPS_PORT, bantime=3600, maxretry=5)"; then
  remote "cat > /etc/fail2ban/jail.d/hardened.conf << EOF
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled  = true
port     = $VPS_PORT
logpath  = %(sshd_log)s
backend  = %(sshd_backend)s
maxretry = 3
EOF"
  ok "Hardened fail2ban config written."
fi

# 3b — Whitelist review
info "Current whitelist (/etc/fail2ban/jail.d/whitelist.conf):"
remote "cat /etc/fail2ban/jail.d/whitelist.conf 2>/dev/null || echo '  (not found)'" | sed 's/^/    /'
warn "Review the whitelist above. If the whitelisted CIDR is no longer needed, remove it."
if confirm "Remove the fail2ban whitelist file (only if you no longer need it)"; then
  remote "rm -f /etc/fail2ban/jail.d/whitelist.conf"
  ok "Whitelist removed."
fi

# 3c — Restart fail2ban
if confirm "Restart fail2ban to apply config changes"; then
  remote "systemctl restart fail2ban && sleep 2 && fail2ban-client status"
  ok "fail2ban restarted."
fi
}

# ===========================================================================
# SECTION 4: CRON REVIEW
# ===========================================================================
skip_section 4 && true || {
section "4: CRON JOBS"
info "Content of /etc/cron.d/keep-ssh-open:"
CRON_CONTENT=$(remote "cat /etc/cron.d/keep-ssh-open 2>/dev/null || echo '(not found)'")
echo "$CRON_CONTENT" | sed 's/^/    /'

# Detect suspicious patterns
if echo "$CRON_CONTENT" | grep -qE '(curl|wget|bash\s+-c|/dev/tcp)'; then
  warn "SUSPICIOUS: cron contains network fetch commands. Removing is strongly recommended."
  if confirm "Remove /etc/cron.d/keep-ssh-open (SUSPICIOUS — contains network commands)"; then
    remote "rm -f /etc/cron.d/keep-ssh-open"
    ok "Suspicious cron removed."
  fi
elif echo "$CRON_CONTENT" | grep -q "not found"; then
  ok "No keep-ssh-open cron found."
else
  info "The cron content looks benign. UFW rules persist across reboots by default."
  info "This cron is likely a leftover from debugging. Consider removing it."
  if confirm "Remove /etc/cron.d/keep-ssh-open (appears safe but probably unnecessary)"; then
    remote "rm -f /etc/cron.d/keep-ssh-open && systemctl enable ufw"
    ok "Cron removed. UFW auto-start confirmed."
  fi
fi
}

# ===========================================================================
# SECTION 5: OS & PACKAGE UPDATES
# ===========================================================================
skip_section 5 && true || {
section "5: OS & PACKAGE UPDATES"
info "Pending upgrades:"
remote "apt-get update -qq 2>/dev/null && apt list --upgradable 2>/dev/null | tail -n +2" | sed 's/^/    /' || true

if confirm "Run 'apt-get upgrade -y' to apply all pending updates"; then
  remote "DEBIAN_FRONTEND=noninteractive apt-get upgrade -y 2>&1 | tail -20"
  ok "Packages upgraded."
fi

if confirm "Enable unattended security updates (auto-apply security patches)"; then
  remote "DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades 2>&1 | tail -5
    dpkg-reconfigure -plow unattended-upgrades"
  ok "Unattended upgrades configured."
fi
}

# ===========================================================================
# SECTION 6: FILE PERMISSIONS
# ===========================================================================
skip_section 6 && true || {
section "6: FILE PERMISSIONS (webroot: $SITE_PATH)"
info "Current webroot permissions:"
remote "ls -la $SITE_PATH 2>/dev/null || echo '(path not found — set SITE_PATH env var)'" | sed 's/^/    /'

if confirm "Set all files in $SITE_PATH to 644 and directories to 755"; then
  remote "find $SITE_PATH -type f -exec chmod 644 {} \;
    find $SITE_PATH -type d -exec chmod 755 {} \;"
  ok "Permissions corrected: files=644, dirs=755."
fi

# Remove world-writable
WORLD_WRITABLE=$(remote "find $SITE_PATH -perm -o+w -ls 2>/dev/null || true")
if [[ -n "$WORLD_WRITABLE" ]]; then
  warn "World-writable files found:"
  echo "$WORLD_WRITABLE" | sed 's/^/    /'
  if confirm "Remove world-write permission from all files/dirs in $SITE_PATH"; then
    remote "chmod -R o-w $SITE_PATH"
    ok "World-write permission removed."
  fi
else
  ok "No world-writable files in webroot."
fi
}

# ===========================================================================
# SECTION 7: WEB SECURITY HEADERS
# ===========================================================================
skip_section 7 && true || {
section "7: WEB SECURITY HEADERS"
info "Checking current headers via localhost curl:"
remote "curl -sI https://localhost/ -H 'Host: universal369.com' -k 2>/dev/null | grep -iE '(x-frame|x-content|strict-transport|content-security|x-xss|referrer)' || echo '  (no security headers found)'" | sed 's/^/    /'

HTACCESS_PATH="$SITE_PATH/.htaccess"

if confirm "Write security headers to $HTACCESS_PATH (LiteSpeed/Apache compatible)"; then
  remote "cat > $HTACCESS_PATH << 'HTACCESS'
# Security Headers
<IfModule mod_headers.c>
    Header always set X-Frame-Options \"SAMEORIGIN\"
    Header always set X-Content-Type-Options \"nosniff\"
    Header always set X-XSS-Protection \"1; mode=block\"
    Header always set Referrer-Policy \"strict-origin-when-cross-origin\"
    Header always set Permissions-Policy \"camera=(), microphone=(), geolocation=()\"
    Header always set Strict-Transport-Security \"max-age=31536000; includeSubDomains\"
</IfModule>

# Force HTTPS
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>
HTACCESS"
  ok "Security headers written to $HTACCESS_PATH"
  info "Verify with: curl -sI https://universal369.com | grep -i x-frame"
fi
}

# ===========================================================================
# SECTION 8: CREATE NON-ROOT DEPLOY USER (OPTIONAL)
# ===========================================================================
skip_section 8 && true || {
section "8: NON-ROOT DEPLOY USER (optional but recommended)"
info "Currently the server only has root access. Creating a deploy user with sudo"
info "allows you to set PermitRootLogin no for full root SSH lockdown."
info ""
info "Steps that would be applied:"
info "  1. Create user 'deploy' with bash shell"
info "  2. Add to sudo group"
info "  3. Copy /root/.ssh/authorized_keys to /home/deploy/.ssh/"
info "  4. You then test: ssh -p $VPS_PORT deploy@<vps-ip>"
info "  5. After confirming deploy login works: set PermitRootLogin no"
info ""
warn "Only proceed if you understand the implications. TEST before locking out root."

if confirm "Create non-root 'deploy' user with sudo and copy SSH keys"; then
  remote "id deploy &>/dev/null && echo 'User deploy already exists' || {
    useradd -m -s /bin/bash deploy
    usermod -aG sudo deploy
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys
    echo 'User deploy created successfully.'
  }"
  ok "deploy user created. TEST login now before changing PermitRootLogin."
  info "Test: ssh -p $VPS_PORT -i $VPS_KEY deploy@<YOUR_VPS_IP>"
  info "After confirming login: re-run section 1 with PermitRootLogin set to 'no'."
fi
}

# ===========================================================================
# SUMMARY
# ===========================================================================
printf '\n\033[1;32m============================================================\033[0m\n'
printf '\033[1;32m Hardening script complete.\033[0m\n'
printf '\033[1;32m============================================================\033[0m\n'
printf '\n'
printf '  Next steps:\n'
printf '  1. Run ./security-audit.sh to verify the fixes took effect\n'
printf '  2. Check UFW status: ssh %s "ufw status verbose"\n' "$VPS_HOST"
printf '  3. Test SSH login in a NEW terminal before closing this session\n'
printf '  4. Verify security headers: curl -sI https://universal369.com\n'
printf '\n'
