# Windows Security Checklist — Orion's Machine

Quick reference for keeping the dev machine secure without breaking VPS workflows.

---

## SSH Key Security

Your SSH key (`~/.ssh/id_ed25519`) is the only thing standing between anyone
and root access on your VPS. Protect it.

```powershell
# Verify key permissions are restrictive (Windows PowerShell)
icacls $env:USERPROFILE\.ssh\id_ed25519

# Should show only your user with full control.
# If it shows "Everyone" or other accounts:
icacls $env:USERPROFILE\.ssh\id_ed25519 /inheritance:r /grant:r "$env:USERNAME:(F)"
```

**Never:**
- Copy `id_ed25519` to cloud storage (OneDrive, Google Drive, Dropbox)
- Email it or paste it anywhere
- Store it in a repo (even private)

**Recommended:** Add a passphrase to the key if it doesn't have one:
```bash
ssh-keygen -p -f ~/.ssh/id_ed25519
```
Then use `ssh-agent` to avoid typing it every time.

---

## Windows Firewall

Windows Defender Firewall should be ON for all profiles.

```powershell
# Check status
Get-NetFirewallProfile | Select Name, Enabled

# Enable all profiles if off
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

You don't need to open any inbound ports — you're always initiating connections
outbound to the VPS, not the other way around.

---

## Windows Defender / Antivirus

```powershell
# Check real-time protection is on
Get-MpComputerStatus | Select RealTimeProtectionEnabled, AntivirusEnabled

# Run a quick scan
Start-MpScan -ScanType QuickScan
```

Keep definitions up to date. Settings → Windows Security → Virus & threat protection
→ Check for updates.

---

## ProtonVPN Setup (see protonvpn-split-tunnel.md)

Key settings for your workflow:
- Split tunnel: **ON**, exclude `187.77.208.156`
- Kill switch: **App mode** (not permanent) — or off during VPS sessions
- DNS leak protection: **ON**
- Auto-connect on startup: your choice, but ensure split tunnel is active first

---

## Browser Security

Since you're managing a live VPS and site:
- Use a separate browser profile for hPanel / CyberPanel admin work
- Enable 2FA on your Hostinger account (hpanel.hostinger.com)
- Never save hPanel passwords in the browser — use a password manager

---

## Git / Secrets Hygiene

Your `.gitignore` should always exclude:
```
.env
*.env
comedy-factory/.env
~/.comedy-factory/
```

Before pushing any commit:
```bash
git diff --cached --name-only  # See what's staged
git log --oneline -5           # Quick review
```

Never commit API keys. If you accidentally do:
1. Rotate the key immediately (Anthropic dashboard, ElevenLabs, etc.)
2. Use `git filter-branch` or BFG Repo Cleaner to remove from history
3. Force push to overwrite the remote

---

## Two-Factor Authentication — Enable Everywhere

| Service | 2FA Status |
|---------|-----------|
| Hostinger / hPanel | Enable at hpanel.hostinger.com → Security |
| GitHub (Burnt-Owl) | Enable at github.com → Settings → Security |
| Anthropic Console | Enable at console.anthropic.com |
| ElevenLabs | Enable in account settings |
| ProtonVPN | Already uses ProtonMail 2FA |

---

## Quick Health Check (run periodically)

```powershell
# Windows PowerShell (as Administrator)

# 1. Firewall on?
Get-NetFirewallProfile | Select Name, Enabled

# 2. Windows up to date?
(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0").Updates.Count

# 3. No unexpected listening ports?
netstat -ano | findstr LISTENING

# 4. SSH key permissions OK?
icacls $env:USERPROFILE\.ssh\id_ed25519
```

---

## VPS Quick Test (run any time to verify VPS is healthy)

```bash
# From your terminal (VPN split-tunnel configured):
ssh -p 2222 root@187.77.208.156 "ufw status && fail2ban-client status sshd && last -5"
```
