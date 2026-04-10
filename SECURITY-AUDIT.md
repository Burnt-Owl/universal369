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
