# universal369.com — Deployment Handoff
**Date**: 2026-03-19
**Status**: Files ready, SSH blocked from Windows machine

---

## The Goal
Deploy universal369.com to the VPS. Two files ready to go:
- `index.html` (21KB) — the site
- `cosmic-energy-enhanced.mp4` (576KB) — background video

## VPS Details
Connection details are stored locally in `~/.ssh/config` — not committed to this repo.
- **SSH**: `ssh hostinger-vps` (alias defined in `~/.ssh/config`)
- **Site path**: `/home/universal369.com/public_html/`

To set up the SSH alias locally if needed:
```
Host hostinger-vps
  HostName <VPS_IP>
  User root
  Port <SSH_PORT>
  IdentityFile <SSH_KEY_PATH>
```

## Current Blocker
SSH from Windows was dropping at banner exchange.
- UFW: ✅ SSH port open
- fail2ban: ✅ 0 banned IPs
- sshd: ✅ running fine
- Root cause: Likely Hostinger network-level block on that IP

## What to try from Linux
```bash
# 1. Test SSH first
ssh -v hostinger-vps "echo connected"

# 2. If it works, deploy:
scp index.html hostinger-vps:/home/universal369.com/public_html/
scp cosmic-energy-enhanced.mp4 hostinger-vps:/home/universal369.com/public_html/

# 3. Set permissions
ssh hostinger-vps "chmod 644 /home/universal369.com/public_html/index.html && chmod 644 /home/universal369.com/public_html/cosmic-energy-enhanced.mp4"

# 4. Confirm live
curl -s -o /dev/null -w "%{http_code}" https://universal369.com
```

## If the domain/directory doesn't exist yet on VPS
Run this in hPanel browser terminal first:
```bash
ls /home/universal369.com/public_html/
# If missing, create it:
mkdir -p /home/universal369.com/public_html
chmod 755 /home/universal369.com/public_html
```
(Domain must also be added in CyberPanel if not already there)

## Fixes already applied to VPS
- fail2ban whitelist added for operator IP range (see `/etc/fail2ban/jail.d/whitelist.conf` on the server)
- Reboot cron added to keep SSH port open (see `/etc/cron.d/keep-ssh-open` on the server — review with security-audit.sh)

## Security Tools (this repo)
- `security-audit.sh` — run this first to check the current security posture
- `security-harden.sh` — review and apply fixes found by the audit

```bash
# Set your connection details, then run the audit:
export VPS_HOST="root@<VPS_IP>"
export VPS_PORT="<SSH_PORT>"
export VPS_KEY="<SSH_KEY_PATH>"
export SITE_PATH="/home/universal369.com/public_html"
./security-audit.sh
```

## If SSH still fails from Linux
Upload via hPanel File Manager:
1. hpanel.hostinger.com → VPS → File Manager
2. Navigate to `/home/universal369.com/public_html/`
3. Upload both files directly
