# universal369.com — Deployment Handoff
**Date**: 2026-03-19
**Status**: Files ready, SSH blocked from Windows machine

---

## The Goal
Deploy universal369.com to the VPS. Two files ready to go:
- `index.html` (21KB) — the site
- `cosmic-energy-enhanced.mp4` (576KB) — background video

## VPS Details
- **IP**: [VPS_IP]
- **SSH**: `ssh hostinger-vps`
- **Key**: `~/.ssh/id_ed25519`
- **Site path**: `/home/universal369.com/public_html/`
- **SSH alias**: `hostinger-vps` (in ~/.ssh/config)

## Current Blocker
SSH from Windows (IP [REDACTED_IP]) is dropping at banner exchange.
- UFW: ✅ port [SSH_PORT] open
- fail2ban: ✅ 0 banned IPs
- sshd: ✅ running fine
- Root cause: Likely Hostinger network-level block on that IP

## What to try from Linux
```bash
# 1. Test SSH first
ssh -v -p [SSH_PORT] root@[VPS_IP] "echo connected"

# 2. If it works, deploy:
scp -P [SSH_PORT] index.html root@[VPS_IP]:/home/universal369.com/public_html/
scp -P [SSH_PORT] cosmic-energy-enhanced.mp4 root@[VPS_IP]:/home/universal369.com/public_html/

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
- fail2ban whitelist: `/etc/fail2ban/jail.d/whitelist.conf` — whitelists [REDACTED_SUBNET]
- Reboot cron: `/etc/cron.d/keep-ssh-open` — auto-opens port [SSH_PORT] on reboot

## Files location (Windows)
`C:\Users\Orion\universal369\`

## If SSH still fails from Linux
Upload via hPanel File Manager:
1. hpanel.hostinger.com → VPS → File Manager
2. Navigate to `/home/universal369.com/public_html/`
3. Upload both files directly

