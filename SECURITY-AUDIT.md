# Security Audit Report
**Date:** 2026-04-10
**Scope:** `Burnt-Owl/universal369` repo + local dev environment
**Branch:** `claude/security-audit-VarHi`

---

## ~~CRITICAL~~ RESOLVED — VPS Credentials Purged from Git History

**Severity:** CRITICAL (now RESOLVED)
**Status:** FIXED on 2026-04-10
**Method:** `git filter-repo --replace-text` across all 36 commits

The following values were previously exposed in plain text in `CLAUDE.md` and `HANDOFF.md`
git history. They have now been replaced with placeholder tokens in every commit:

| Item | Replaced With |
|------|---------------|
| VPS IP | `[VPS_IP]` |
| SSH Port | `[SSH_PORT]` |
| Windows IP | `[REDACTED_IP]` |
| fail2ban subnet | `[REDACTED_SUBNET]` |

**Verification:** `git log --all -p` returns zero matches for any of the original values.

**Remaining recommendation:** Even though history is clean, consider rotating the SSH port
on the VPS as a precaution, since the values may have been cached by GitHub or any forks.

---

## HIGH — GitHub Actions Workflow Using Floating Action Tags (Not SHA-Pinned)

**Severity:** HIGH
**File:** `.github/workflows/comedy-factory-daily.yml`

```yaml
uses: actions/checkout@v4          # Not pinned to a SHA
uses: actions/setup-python@v5      # Not pinned to a SHA
uses: actions/upload-artifact@v4   # Not pinned to a SHA
```

A supply-chain compromise of any of these actions (e.g., a tag being moved to malicious code)
would execute inside your workflow with access to all `secrets.*` values, including:
`ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `TIKTOK_ACCESS_TOKEN`, etc.

**Fix:** Pin each action to a specific commit SHA:
```yaml
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683        # v4.2.2
uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2     # v5.3.0
uses: actions/upload-artifact@65c4c4a1ddee5b72f698fdd19549f0f0fb45cf86 # v4.6.0
```

---

## MEDIUM — FFmpeg ASS Subtitle Filter Uses Unescaped Path (video_agent.py)

**Severity:** MEDIUM
**File:** `comedy-factory/agents/video_agent.py` line 349

```python
"-vf", f"ass='{ass_file}'",
```

The file path is embedded directly into an FFmpeg filter string with single-quote wrapping only.
If `run_dir` (and thus `ass_file`) ever contains a single quote, colon, or backslash, FFmpeg will
misparse the filter graph. On Windows paths this would break immediately (`C:\...`).
In a multi-tenant or user-controlled `run_dir` scenario it could be exploited.

**Fix:** Escape the path for FFmpeg filter syntax:
```python
escaped = str(ass_file).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
"-vf", f"ass='{escaped}'",
```

---

## MEDIUM — FFmpeg concat uses `-safe 0` (video_agent.py)

**Severity:** MEDIUM (low immediate risk, bad practice)
**File:** `comedy-factory/agents/video_agent.py` lines 319–324

```python
concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_files))
...
FF, "-y", "-f", "concat", "-safe", "0", ...
```

`-safe 0` disables FFmpeg's path safety restrictions, allowing absolute paths and path traversal
in the concat manifest. Currently `clip_files` is controlled entirely by internal logic, so the
risk is low. But if any future code path allows external input to influence `clip_files`, this
becomes a path traversal vector.

**Fix:** Use `-safe 1` and ensure all clip paths are relative, or validate that all paths resolve
within the expected `tmp_dir` before writing the manifest.

---

## MEDIUM — YouTube OAuth Opens Local HTTP Server in CI (publish_agent.py)

**Severity:** MEDIUM
**File:** `comedy-factory/agents/publish_agent.py` line ~72

```python
flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, scopes)
credentials = flow.run_local_server(port=0)
```

`run_local_server()` is the interactive desktop OAuth flow. In GitHub Actions (CI), this will
hang indefinitely waiting for a browser redirect that will never come. There is no stored-token
refresh mechanism, so every run needs a browser interaction.

**Fix:** Switch to the service-account / refresh-token pattern:
```python
# Store credentials as JSON (token, refresh_token, etc.) in a GitHub secret
# Then load and refresh:
from google.oauth2.credentials import Credentials
creds = Credentials.from_authorized_user_info(json.loads(YOUTUBE_CREDS_JSON))
if creds.expired:
    creds.refresh(Request())
```

---

## LOW — API Keys Sourced Correctly but Empty-String Defaults Mask Missing Keys

**Severity:** LOW
**File:** `comedy-factory/config.py` lines 13–23

```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
```

Empty string defaults mean a misconfigured environment will silently pass key validation and
only fail at API call time. This makes debugging harder and could cause partial pipeline runs
that waste credits.

**Fix:** For required keys, raise early:
```python
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]   # KeyError = fast fail
NEWS_API_KEY      = os.environ["NEWS_API_KEY"]
```
Optional keys can keep the `os.getenv("KEY", "")` pattern.

---

## LOW — `comedy-factory/.gitignore` Missing `youtube-client-secrets.json` Parent-Level Protection

**Severity:** LOW
**File:** `comedy-factory/.gitignore`

The `.gitignore` correctly lists `youtube-client-secrets.json`, but there is no root-level
`.gitignore` entry. If the file is accidentally placed at the repo root or in a subdirectory
outside `comedy-factory/`, it will not be ignored and could be committed.

**Fix:** Add to the root `.gitignore` (create one if missing):
```
# OAuth / credential files — never commit
youtube-client-secrets.json
*.pem
*.key
.env
.env.*
!.env.example
```

---

## INFORMATIONAL — No `shell=True` in subprocess Calls

All `subprocess.run()` calls in `video_agent.py` and `effects_agent.py` correctly use list
arguments (no string interpolation + `shell=True`). This is good — no command injection risk
through the FFmpeg pipeline.

---

## INFORMATIONAL — All API Keys Loaded via Environment (config.py)

No API keys are hardcoded in committed Python files. All keys are sourced from `os.getenv()`.
The `.env` file is gitignored. This is correct.

---

## Summary Table

| # | Severity | Finding |
|---|----------|---------|
| 1 | ~~CRITICAL~~ RESOLVED | VPS IP + SSH port purged from git history |
| 2 | HIGH | GitHub Actions not SHA-pinned (supply chain risk) |
| 3 | MEDIUM | FFmpeg ASS filter path unescaped |
| 4 | MEDIUM | FFmpeg concat uses `-safe 0` |
| 5 | MEDIUM | YouTube OAuth flow incompatible with CI |
| 6 | LOW | Empty-string API key defaults mask misconfiguration |
| 7 | LOW | `youtube-client-secrets.json` only ignored in subdirectory |

---

## Immediate Actions (Priority Order)

1. ~~**Today:** Purge git history to remove the real VPS IP/port.~~ DONE (2026-04-10)
2. **Recommended:** Rotate SSH port on VPS as a precaution.
3. **Today:** Pin GitHub Actions to SHA hashes.
4. **This week:** Fix YouTube OAuth to use stored refresh tokens.
5. **This week:** Escape the FFmpeg ASS filter path.
6. **Ongoing:** Tighten required-key validation in `config.py`.

---

# System & Network Deep Sweep
**Date:** 2026-07-08
**Scope:** Full container environment — processes, network, files, auth, integrity

---

## Rootkit & Backdoor Scan

### SUID Binaries — CLEAN
All SUID binaries are standard system utilities:
`chfn`, `chsh`, `gpasswd`, `mount`, `newgrp`, `passwd`, `su`, `sudo`, `umount`,
`dbus-daemon-launch-helper`, `polkit-agent-helper-1`

No unexpected or rogue SUID binaries found.

### Hidden Processes — CLEAN
Cross-referenced `/proc/` PIDs against `ps` output. The only delta is kernel threads
(PIDs 1–20), which is normal. No userspace processes hiding from `ps`.

### LD_PRELOAD Hijack — CLEAN
- `/etc/ld.so.preload` is empty (no library injection)
- No `LD_PRELOAD` or `LD_LIBRARY_PATH` in environment
- No rogue shared libraries in linker paths

### Git Hooks — CLEAN
All hooks in `.git/hooks/` are `.sample` files (inactive). No active hooks that could
execute code on commit/push/checkout.

### Shell Profiles — CLEAN
Checked `/etc/profile`, `/etc/bash.bashrc`, `/root/.bashrc`, `/root/.profile`.
Only standard `lesspipe` and `dircolors` eval calls found — both are default Ubuntu.
No injected `curl`, `wget`, `python`, `nc`, or reverse shell commands.

### Kernel Modules — CLEAN
No loaded kernel modules (`lsmod` returns empty). Container runs on host kernel.

---

## Network Analysis

### Listening Ports
| Port | Binding | Purpose |
|------|---------|---------|
| 2024 | `0.0.0.0` | process_api (container control plane) |
| 2025 | `0.0.0.0` | Container management |
| 41729 | `127.0.0.1` | Git proxy (local only) |
| 35135 | `127.0.0.1` | MCP server (local only) |

Ports 2024/2025 are bound to all interfaces — this is expected for the Claude Code
container orchestrator. Ports 41729/35135 are localhost-only (safe).

### Active Connections — CLEAN
All established connections go to two IPs over HTTPS (port 443):
- `160.79.104.10` — Anthropic API infrastructure (~30 connections, expected)
- `34.149.66.137` — Google Cloud (likely MCP or CDN, 1 connection)

No connections to unknown IPs, no connections on suspicious ports (IRC 6667,
C2 common ports 4444/8080/1337, crypto mining pools 3333/5555).

### DNS — CLEAN
`/etc/resolv.conf` points to `8.8.8.8` (Google DNS). No rogue nameservers.

### /etc/hosts — CLEAN
Only `127.0.0.1 localhost` and `127.0.0.1 vm`. No DNS hijacking entries.

---

## Authentication & Access

### User Accounts with Shell Access
| User | UID | Shell | Assessment |
|------|-----|-------|------------|
| `root` | 0 | `/bin/bash` | Expected |
| `sync` | 4 | `/bin/sync` | System account, harmless |
| `ubuntu` | 1000 | `/bin/bash` | Default Ubuntu user |
| `postgres` | 102 | `/bin/bash` | PostgreSQL admin (has shell — note below) |
| `claude` | 999 | `/bin/bash` | Claude Code agent user |

**Note:** `postgres` has a login shell (`/bin/bash`). In production environments, database
service accounts should use `/usr/sbin/nologin` to prevent interactive login.

### SSH Keys — CLEAN
No `authorized_keys` files found for any user. No SSH identity keys in `/home/` or `/root/.ssh/`.

### Sudoers — FINDING
```
claude ALL=(ALL) NOPASSWD: ALL
```
The `claude` user has **passwordless root** via sudo. This is expected for the Claude Code
container environment but would be a critical finding on a production server.

### Cron Jobs — CLEAN
Only standard system crons found:
- `e2scrub_all` — filesystem scrub (standard)
- `php` sessionclean — PHP session garbage collection (standard)

No user crontabs. No suspicious scheduled tasks.

---

## Malware & Trojan Scan

### Crypto Miners — CLEAN
Scanned for: `xmrig`, `minerd`, `cryptonight`, mining pool connections.
Zero matches in processes.

### Reverse Shells — CLEAN
Scanned for: `nc -l`, `bash -i`, `/dev/tcp`, `socat`, `mkfifo`, `nc -e`.
Zero matches in processes or codebase.

### Tunneling Tools — CLEAN
Scanned for: `ngrok`, `chisel`, `frp`, `rathole`, `serveo`.
Zero matches.

### Obfuscated Payloads — CLEAN
Scanned all `.py`, `.js`, `.html` files for:
- `eval()` + `base64` decode chains — none found
- `exec()` with dynamic input — none found
- Suspicious URLs (pastebin, transfer.sh, paste.ee) — none found

The only `base64` usage is legitimate:
- `avatar_agent.py` — D-ID API Basic auth encoding
- `visual_agent.py` — decoding Gemini Imagen API response data

### Injected Scripts in HTML — CLEAN
`index.html` contains no `<iframe>` tags and no external `<script src=...>` tags.

---

## File Integrity

### Recently Modified System Binaries — CLEAN
No files in `/usr/bin/` or `/usr/sbin/` modified in the last 7 days.

### World-Writable Files — CLEAN
No world-writable files found in the repository.

### Suspicious Temp Files — LOW RISK
```
/tmp/147.0.7727.24/chromedriver/chromedriver-linux64/chromedriver
```
This is a Chromedriver binary, likely from a Puppeteer/Selenium installation. Not malicious,
but should be cleaned up if unused.

### Hidden Files in Repo — CLEAN
Only `.env.example` found (expected). No hidden backdoor scripts.

### PAM Modules — CLEAN
PAM modules show as "UNPACKAGED" because `dpkg` database isn't fully available in the container,
but the modules themselves (`pam_deny.so`, `pam_permit.so`, `pam_systemd.so`, etc.) are all
standard Ubuntu/Debian PAM modules. No rogue authentication modules.

### Systemd Services — CLEAN
Services found: `docker`, `redis-server`, `postgresql`, `containerd`, `ssl-cert`, `getty`.
All are standard infrastructure services. No suspicious ExecStart commands.

---

## Summary

| Category | Status | Details |
|----------|--------|---------|
| Rootkits | CLEAN | No hidden processes, no LD_PRELOAD, no kernel modules |
| Network | CLEAN | Only Anthropic + Google Cloud connections on port 443 |
| Malware | CLEAN | No miners, reverse shells, or obfuscated payloads |
| Auth | CLEAN | No unauthorized SSH keys, no rogue users |
| File Integrity | CLEAN | No modified system binaries, no world-writable files |
| Git Hooks | CLEAN | No active hooks (all .sample) |
| Cron/Scheduled | CLEAN | Only standard system crons |
| DNS/Hosts | CLEAN | Google DNS, no hijacking |

### Informational Notes (not vulnerabilities)
1. `postgres` user has a login shell — consider changing to `/usr/sbin/nologin` on prod
2. `claude` user has passwordless sudo — expected in this container, not for prod
3. Chromedriver binary in `/tmp/` — clean up if unused
4. Ports 2024/2025 bound to `0.0.0.0` — expected for container orchestration
