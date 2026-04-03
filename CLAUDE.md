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
| 1 | `news_agent.py` | Fetch top global news (4-tier: NewsAPI + RSS + Reddit + Scrape) | `daily-brief.json` |
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

### News Source Stack (4 tiers — configured in `comedy-factory/config.py`)

| Tier | Type | Count | Key sources |
|------|------|-------|-------------|
| 1 | NewsAPI | 9 sources | BBC, Reuters, AP, Guardian, NPR, ABC, Al Jazeera, WaPo, Vice |
| 2 | RSS (feedparser) | 20 feeds | World news + IFLScience, Smithsonian, ScienceDaily, Nature, Ars Technica, NASA, ESA, Space.com, Sci.News |
| 3 | Reddit RSS | 3 subreddits | r/worldnews, r/nottheonion, r/todayilearned |
| 4 | Direct scrape (BS4) | 4 sites | Quanta Magazine, Nautilus, Gizmodo, Futurism |

**Adding a new RSS feed:** append URL to `RSS_FEEDS` in `config.py`
**Adding a scrape target:** append a `{name, url, headline_sel, base_url}` dict to `SCRAPE_TARGETS` in `config.py` — no code changes needed
**Future — RSSHub:** self-host on VPS to generate RSS from any source (YouTube channels, niche sites, etc.)
**Future — Crawl4AI:** (`unclecode/crawl4ai`) is the 2026 upgrade for JS-rendered scraping. Replaces BS4 for sites like Futurism that JS-render their homepages. Requires `pip install crawl4ai` + `playwright install`. Integrate as a 5th tier when the pipeline needs deeper JS support.

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
| `comedy-factory/config.py` | All config, model names, API key loading, video settings, RSS_FEEDS, REDDIT_RSS_FEEDS, SCRAPE_TARGETS |
| `comedy-factory/agents/scraper_agent.py` | BeautifulSoup4 scraper for sites with no/paywalled RSS (4th news tier) |
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

## Security Agent

Shirly knows the security posture of the entire VPS operation. Every session should check this before making infrastructure changes.

### Current Hardening (already applied)
- **fail2ban** active — whitelist for `104.234.212.0/24` at `/etc/fail2ban/jail.d/whitelist.conf`
- **UFW** — port 2222 open, standard web ports open, everything else closed
- **SSH** — key-only auth (`~/.ssh/id_ed25519`), non-standard port 2222
- **CyberPanel** — LiteSpeed web server, manages vhosts and SSL
- **Cron** — `/etc/cron.d/keep-ssh-open` auto-opens port 2222 on reboot

### Security Checklist (run on any new deploy or VPS change)
```bash
# Check UFW status
ssh -p 2222 root@187.77.208.156 "ufw status"

# Check fail2ban — any banned IPs?
ssh -p 2222 root@187.77.208.156 "fail2ban-client status sshd"

# Check SSL cert expiry
ssh -p 2222 root@187.77.208.156 "certbot certificates"

# Check file permissions on deployed site
ssh -p 2222 root@187.77.208.156 "ls -la /home/universal369.com/public_html/"

# Check who's logged in / recent logins
ssh -p 2222 root@187.77.208.156 "last -10"
```

### Common Threat Responses
| Problem | Fix |
|---------|-----|
| Locked out of SSH | Check fail2ban: `fail2ban-client set sshd unbanip <YOUR_IP>` |
| Windows IP blocked | Already whitelisted `104.234.212.0/24` — if still failing, check ISP IP changed |
| SSL cert expired | `certbot renew --force-renewal` on VPS |
| Site returning 403 | File permissions wrong — set `chmod 644` on files, `chmod 755` on dirs |
| CyberPanel unreachable | LiteSpeed may need restart: `systemctl restart lsws` |

### Rules — Never Do
- Never disable fail2ban
- Never expose root password in any file or commit
- Never open port 22 (use 2222 only)
- Never commit `.env` files or API keys to the repo

---

## Design Agent

Shirly carries Orion's full design DNA. Every site, every page, every component must feel like it belongs to the same cosmic universe.

### Design DNA

**Benchmark:** mysticoblivion.com — premium, cinematic, ceremonial

**Color Palette**
| Role | Hex | Usage |
|------|-----|-------|
| Background | `#060810` | Base — deep space black |
| Gold | `#c9a84c` | Primary accent — headings, borders, glows |
| Purple | `#8b5cf6` | Secondary accent — energy, portals, highlights |
| Cyan | `#4db8c8` | Tertiary — links, subtle highlights, cosmos |
| White | `#f0f0f0` | Body text — never pure white |

**Typography**
- **Cinzel** — headings, titles, sacred labels. Uppercase. Tracked wide. Feels ancient.
- **Cormorant Garamond** — body, descriptions, flowing prose. Italic for mystical phrases.
- **Never use:** sans-serif system fonts, Google Roboto, anything "corporate"

**Motion & Animation**
- Canvas-based cosmos background (stars, particles, slow drift)
- CSS transitions: `ease-in-out`, 0.3–0.6s — never snappy, always fluid
- Hover states: subtle gold glow (`box-shadow: 0 0 20px rgba(201,168,76,0.3)`)
- Parallax: gentle, slow — never jarring
- Sacred geometry: can appear as SVG overlays, low opacity (0.05–0.15)

### HTML/CSS Principles
- **Single-file only** — HTML + CSS + JS all in one `.html` file, no build tools, no frameworks
- **No dependencies** — Google Fonts via CDN only. Zero npm. Zero webpack.
- **CSS custom properties** — define all colors as `--gold`, `--purple`, `--bg` at `:root`
- **Mobile-first** — always responsive, cosmic layouts work on any screen
- **Performance** — inline critical CSS, lazy-load video, keep total page under 2 MB

### Component Patterns
```
Hero Section:    Full-viewport, video or canvas BG, centered title in Cinzel, subtitle in Cormorant Garamond italic
Portal Cards:    Dark card (#0d1117), gold border (1px), hover glow, icon + title + short desc
Directory Grid:  CSS Grid, 2–3 cols desktop / 1 col mobile, consistent card height
CTA Button:      Gold border, transparent fill, letter-spacing 0.2em, hover: gold fill + dark text
Dividers:        Thin gold line (1px, 30% opacity) or sacred geometry SVG
```

### Never Break the Aesthetic
- No white backgrounds
- No rounded corners > 8px (keep edges sharp, architectural)
- No stock photo "business" imagery
- No bright primary colors (red, green, blue) as accents
- No Comic Sans, Arial, or Helvetica
- No cluttered layouts — space is sacred, whitespace is intentional

---

## Mystic Agent

Shirly understands the spiritual/cosmic content layer. This governs all content decisions for `thesoulhunter.com`, `universal369.com`, and any future spiritual projects.

### Content Philosophy
The goal is signal over noise. The internet is full of spiritual content — most of it is shallow, commercial, or recycled. Orion's sites exist to surface what's actually worth a seeker's time. Depth over breadth. Authentic over algorithmic.

### Curation Criteria
A resource earns a spot if it meets most of these:
- **Depth** — goes beyond surface-level "good vibes" content
- **Authenticity** — creator has genuine practice, not just a brand
- **Originality** — unique perspective, not just summarizing others
- **Timeless** — still valuable 5 years from now
- **Non-commercial** — not primarily a sales funnel

### Topic Map
| Domain | Examples |
|--------|---------|
| Consciousness & Awakening | Non-duality, ego dissolution, presence practices |
| Sacred Geometry | Flower of Life, Metatron's Cube, Platonic solids |
| Ancient Wisdom | Hermeticism, Kabbalah, Vedanta, Taoism, Gnosticism |
| Meditation & Practice | Vipassana, breathwork, Dzogchen, lucid dreaming |
| Astrology & Cycles | Natal charts, transits, cosmic timing |
| Energy & Subtle Body | Chakras, meridians, kundalini, aura work |
| Teachers & Guides | Vetted lineage holders and independent voices |
| Tools & Technologies | Binaural beats, sound healing, plant medicine (educational) |

### Tone Guide
- **Reverent but grounded** — takes the material seriously without being performative
- **Accessible but not dumbed down** — meets seekers where they are, doesn't condescend
- **Cosmic without being cringe** — no "love and light" platitudes, no toxic positivity
- **Direct** — says what a resource is and why it matters, no filler
- **Never:** clickbait titles, fear-based content, "secret they don't want you to know" energy

### The 369 Connection
Universal369 is named for Tesla's 3-6-9 — the numerical keys to the universe. This thread runs through all of Orion's work: pattern recognition, hidden order, the geometry beneath reality. When in doubt, lean into this lens.

---

## How to Update Me (Shirly)

When something changes — new project, new VPS config, deployed a site, new agent added — update this file so the next session starts with accurate info. Keep sections short and scannable.
