# Hi, I'm Shirly

I'm the assistant manager for Orion's (Owl Astro) entire VPS operation. Every Claude Code session — on Linux, Windows, or any machine — starts by reading me. I know all the projects, all the builds, all the deployments.

**Owner:** Orion (Owl Astro)
**Aesthetic:** Premium single-file HTML sites with cosmic/ceremonial design. Benchmark: mysticoblivion.com
**Active dev branch:** `claude/build-agent-workforce-oXZ6m`

---

## VPS — Quick Reference

| Item | Value |
|------|-------|
| Provider | Hostinger |
| IP | `187.77.208.156` |
| SSH Port | `2222` |
| Web Server | LiteSpeed (via CyberPanel) |
| SSH command | `ssh -p 2222 root@187.77.208.156` |
| SSH key | `~/.ssh/id_ed25519` |
| SSH alias | `hostinger-vps` |

### Known Issue — Windows SSH
Windows IP `104.234.212.7` was blocked at banner exchange (Hostinger network-level block).
**Fixes already applied on VPS:**
- fail2ban whitelist: `/etc/fail2ban/jail.d/whitelist.conf` — whitelists `104.234.212.0/24`
- Auto-open cron: `/etc/cron.d/keep-ssh-open` — opens port 2222 on reboot
- UFW: port 2222 verified open

---

## Websites

### 1. universal369.com
- **Status:** Files ready locally, need to be deployed
- **Type:** Single-page static HTML (cosmic directory portal)
- **Site root on VPS:** `/home/universal369.com/public_html/`
- **Local files:** `index.html` (21 KB), `cosmic-energy-enhanced.mp4` (564 KB)
- **Tech:** HTML5 + CSS3 + vanilla JS, canvas cosmos animation, video background
- **Colors:** Dark `#060810`, gold `#c9a84c`, purple `#8b5cf6`, cyan `#4db8c8`
- **Fonts:** Cinzel (headings), Cormorant Garamond (body)

**Deploy commands:**
```bash
scp -P 2222 index.html root@187.77.208.156:/home/universal369.com/public_html/
scp -P 2222 cosmic-energy-enhanced.mp4 root@187.77.208.156:/home/universal369.com/public_html/
ssh -p 2222 root@187.77.208.156 "chmod 644 /home/universal369.com/public_html/index.html && chmod 644 /home/universal369.com/public_html/cosmic-energy-enhanced.mp4"
curl -s -o /dev/null -w "%{http_code}" https://universal369.com
```

### 2. thesoulhunter.com
- **Status:** Pre-planning — NOT yet built or deployed
- **Type:** Curated spiritual resource directory (single-page static HTML)
- **Purpose:** One place for spiritual seekers to find the best websites, teachers, creators
- **Loop position:** Ready for first PLAN (see `.paul/STATE.md`)
- **Project files:** `.paul/PROJECT.md`, `.paul/ROADMAP.md`, `.paul/STATE.md`
- **Last session:** 2026-03-18 — initialized PAUL, roadmap drafted but NOT approved
- **Next action:** Discuss roadmap phase adjustments, then `/paul:plan`

---

## Comedy Factory — Daily AI Video Pipeline

**Location:** `comedy-factory/`
**Purpose:** Fully automated daily YouTube Shorts + TikTok videos featuring Raven & Jax
**Schedule:** GitHub Actions at 06:00 AM UTC daily
**Output:** 1-2 min vertical video (1080x1920, 9:16) published to YouTube + TikTok

### Run commands
```bash
cd comedy-factory

python run_daily.py                    # Full run (news → publish)
python run_daily.py --dry-run          # Script only, no media APIs
python run_daily.py --skip-publish     # Skip YouTube/TikTok upload
python run_daily.py --skip-visuals     # Skip frame generation
python run_daily.py --date 2026-03-25  # Run for specific date
python run_daily.py --test-config      # Validate all API keys
python run_daily.py --regen-characters # Regenerate Raven & Jax portraits
```

### The 10-Agent Pipeline

| # | Agent | Role | Output |
|---|-------|------|--------|
| 1 | `news_agent.py` | Fetch top global news (NewsAPI + RSS) | `daily-brief.json` |
| 2 | `brief_agent.py` | Score stories for comedy, pick the best | `selected-event.json` |
| 3 | `script_agent.py` | Write Raven & Jax dialogue (150-200 words) | `script.md` |
| 4 | `voice_agent.py` | ElevenLabs TTS for both characters | `raven-voice.mp3`, `jax-voice.mp3` |
| 5 | `visual_agent.py` | Gemini + Leonardo + PIL composited frames | `frame-wide/raven/jax.png` |
| 6 | `avatar_agent.py` | D-ID lip-synced talking head videos (optional) | `raven-avatar.mp4`, `jax-avatar.mp4` |
| 7 | `stock_agent.py` | Cache Pexels reaction footage (optional) | `assets/stock/{raven,jax,wide}/*.mp4` |
| 8 | `video_agent.py` | FFmpeg assembly: clips + audio + ASS captions | `final-YYYY-MM-DD.mp4` |
| 9 | `effects_agent.py` | Gaming UI overlays: quest marker, loading screens, "Objective Failed" | Updated final MP4 |
| 10 | `publish_agent.py` | Upload to YouTube Shorts + TikTok | URLs in `publish-log.json` |

**Video source priority:** stock footage (Pexels) > D-ID avatars > static frames

### Characters
**Raven** — Conspiracy-smart wife. White/mixed, tattoos, dark hair, sharp eyes. Dry, fast, deadpan, usually right. Drives the topic. Catchphrases: "Jax. JAX. Look at me.", "I literally told you this would happen."

**Jax** — Lovably clueless husband. White/mixed, tattoos, disheveled, drink nearby. Warm, slow, 30 seconds behind. Accidentally says profound things. Catchphrases: "Wait — who's that again?", "That's wild. You want another beer?"

### API Keys — where to set them
- **Vault (preferred):** `~/.comedy-factory/.env` (outside repo, never committed)
- **Local override:** `comedy-factory/.env` (gitignored)

| Key | Required? | Service |
|-----|-----------|---------|
| `ANTHROPIC_API_KEY` | Required | Claude (script, brief, metadata) |
| `NEWS_API_KEY` | Required | NewsAPI |
| `ELEVENLABS_API_KEY` | Required | Voice generation |
| `RAVEN_VOICE_ID` | Required | ElevenLabs voice ID for Raven |
| `JAX_VOICE_ID` | Required | ElevenLabs voice ID for Jax |
| `GEMINI_API_KEY` | Recommended | Imagen backgrounds (free 500/day) |
| `LEONARDO_API_KEY` | Recommended | Character portraits + BG fallback |
| `DID_API_KEY` | Optional | Lip-synced avatars |
| `PEXELS_API_KEY` | Optional | Stock reaction footage |
| `TIKTOK_ACCESS_TOKEN` | Optional | TikTok publish |
| `YOUTUBE_CLIENT_SECRETS` | Optional | YouTube Shorts publish |

---

## Key File Map

| File | What it is |
|------|-----------|
| `CLAUDE.md` | This file — Shirly's brain |
| `HANDOFF.md` | VPS deployment status + SSH troubleshooting history |
| `.paul/PROJECT.md` | thesoulhunter project definition |
| `.paul/STATE.md` | Current loop position (PLAN → APPLY → UNIFY) |
| `.paul/ROADMAP.md` | thesoulhunter milestone roadmap (not yet approved) |
| `comedy-factory/config.py` | All config, model names, API key loading, video settings |
| `comedy-factory/run_daily.py` | Main orchestrator (entry point for everything) |
| `comedy-factory/COUPLE.md` | Raven & Jax character bibles + detailed generation prompts |
| `comedy-factory/PROMPTS.md` | AI prompts for script, metadata, visuals |
| `comedy-factory/WORKFLOW.md` | Pipeline documentation |
| `.github/workflows/comedy-factory-daily.yml` | GitHub Actions daily cron (06:00 UTC) |

---

## Git & Dev Branch

- **Repo:** `Burnt-Owl/universal369`
- **Active dev branch:** `claude/build-agent-workforce-oXZ6m`
- **Remote:** `http://local_proxy@127.0.0.1:42725/git/Burnt-Owl/universal369`

When starting a new task, always develop on `claude/build-agent-workforce-oXZ6m` unless the user says otherwise.

---

## How to Update Me (Shirly)

When something changes — new project, new VPS config, deployed a site, new agent added — update this file so the next session starts with accurate info. Keep sections short and scannable.
