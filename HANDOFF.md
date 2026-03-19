# universal369.com — Deployment Handoff
**Date**: 2026-03-19
**Status**: Files ready, SSH blocked from Windows machine

---

## The Goal
Deploy universal369.com to the VPS. Two files ready to go:
- `index.html` (21KB) — the site
- `cosmic-energy-enhanced.mp4` (576KB) — background video

## VPS Details
- **IP**: 187.77.208.156
- **SSH**: `ssh -p 2222 root@187.77.208.156`
- **Key**: `~/.ssh/id_ed25519`
- **Site path**: `/home/universal369.com/public_html/`
- **SSH alias**: `hostinger-vps` (in ~/.ssh/config)

## Current Blocker
SSH from Windows (IP 104.234.212.7) is dropping at banner exchange.
- UFW: ✅ port 2222 open
- fail2ban: ✅ 0 banned IPs
- sshd: ✅ running fine
- Root cause: Likely Hostinger network-level block on that IP

## What to try from Linux
```bash
# 1. Test SSH first
ssh -v -p 2222 root@187.77.208.156 "echo connected"

# 2. If it works, deploy:
scp -P 2222 index.html root@187.77.208.156:/home/universal369.com/public_html/
scp -P 2222 cosmic-energy-enhanced.mp4 root@187.77.208.156:/home/universal369.com/public_html/

# 3. Set permissions
ssh -p 2222 root@187.77.208.156 "chmod 644 /home/universal369.com/public_html/index.html && chmod 644 /home/universal369.com/public_html/cosmic-energy-enhanced.mp4"

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
- fail2ban whitelist: `/etc/fail2ban/jail.d/whitelist.conf` — whitelists 104.234.212.0/24
- Reboot cron: `/etc/cron.d/keep-ssh-open` — auto-opens port 2222 on reboot

## Files location (Windows)
`C:\Users\Orion\universal369\`

## If SSH still fails from Linux
Upload via hPanel File Manager:
1. hpanel.hostinger.com → VPS → File Manager
2. Navigate to `/home/universal369.com/public_html/`
3. Upload both files directly

