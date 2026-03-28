# CLAUDE.md — Orion / Owl Astro
*Context file for Claude Code. Read this at the start of any session.*

---

## Who I Am

**Orion (Owl Astro)** — I build premium single-file HTML sites with dark, cosmic,
ceremonial aesthetics. Reference benchmark: **mysticoblivion.com**.

Workflow: single HTML file, all CSS + JS inline, no framework, no build step.
Deploy via `scp` to Hostinger VPS. Done.

---

## Design DNA — The Mysticoblivion Aesthetic

### Color Palette
```css
--bg:          #060810   /* deep space black */
--surface:     #0a0d14
--surface2:    #0f1219
--border:      #1a1d2e
--gold:        #c9a84c   /* primary accent */
--gold-dim:    #8a7535
--purple:      #8b5cf6   /* secondary accent */
--purple-dim:  #6b4cc6
--cyan:        #4db8c8   /* tertiary accent */
--text:        #cdc8d8
--text-dim:    #6a6578
--text-bright: #f0eef5
```

### Typography
- **Headings**: `Cinzel` (400 / 600 / 700 / 900) — Google Fonts
- **Body**: `Cormorant Garamond` (light 300, regular 400, semibold 600, italic variants)
- **Fallbacks**: Georgia, serif

### Atmosphere
- `<canvas id="cosmos">` — animated starfield, fixed background, `opacity: 0.6`
- Video hero: `<video class="hero-video">` looping, muted, `opacity: 0.5`, `object-fit: cover`
- Deep dark backgrounds with subtle border separators (`--border`)
- Layered z-index: canvas (z:0) → page content (z:1)

### Layout Principles
- Full-viewport hero (`min-height: 100vh`, centered flex)
- `scroll-behavior: smooth`
- No framework — raw CSS custom properties + vanilla JS
- Everything inline in one `.html` file

---

## VPS — Hostinger (187.77.208.156)

### Connect
```bash
ssh -p 2222 root@187.77.208.156
# Key: ~/.ssh/id_ed25519  (no password — key already authorized)
# Alias in ~/.ssh/config: hostinger-vps
```
If key not loaded: `ssh-add ~/.ssh/id_ed25519`

### Deploy a Site
```bash
# Upload files
scp -P 2222 index.html root@187.77.208.156:/home/DOMAIN.com/public_html/
scp -P 2222 cosmic-energy-enhanced.mp4 root@187.77.208.156:/home/DOMAIN.com/public_html/

# Set permissions
ssh -p 2222 root@187.77.208.156 "chmod 644 /home/DOMAIN.com/public_html/*"

# Verify
curl -s -o /dev/null -w "%{http_code}" https://DOMAIN.com
```

### Site Paths
| Domain | Path |
|--------|------|
| universal369.com | `/home/universal369.com/public_html/` |
| thesoulhunter.com | `/home/thesoulhunter.com/public_html/` |

### Panel
- Hostinger hPanel: hpanel.hostinger.com → VPS
- CyberPanel for domain management
- hPanel File Manager as fallback if SSH is blocked

### VPS Configs
- UFW: port 2222 open
- fail2ban: active, whitelist at `/etc/fail2ban/jail.d/whitelist.conf`
- Reboot cron: `/etc/cron.d/keep-ssh-open` — auto-opens port 2222 on reboot

---

## Network — Multi-Machine Setup

### Architecture
```
Machine 1 ──────┐
Machine 2 ──────┤──► VPS 187.77.208.156:2222  (always-on Syncthing hub)
Machine 3 ──────┤         ~/orion/  ←  28 synced folders
192.168.8.146 ──┘
```

### Syncthing
- **28 folders** synced, all under `~/orion/`
- VPS is the always-on relay device (get device ID from dashboard)
- To add a new machine: get its Syncthing device ID → add on VPS → accept folders

### Machines
| IP | Status |
|----|--------|
| VPS: 187.77.208.156 | Hostinger VPS, always on |
| 192.168.8.146 | Local network machine — identity TBD |

### Adding a New Machine to the Network
```bash
# 1. Copy its SSH public key to VPS
ssh-copy-id -p 2222 -i ~/.ssh/id_ed25519.pub root@187.77.208.156
# or manually append to ~/.ssh/authorized_keys on VPS

# 2. Install Syncthing on new machine, add VPS device ID
# 3. Accept shared ~/orion/ folders on VPS dashboard
```

### Multi-Machine Claude Workflow
Every machine has Claude Code and this `CLAUDE.md`. Workflow:
1. Sit at any machine
2. `git pull` — get latest code
3. Syncthing has already synced `~/orion/` assets
4. Claude reads `CLAUDE.md` → instant full context
5. Deploy from any machine via `scp` to VPS

---

## Active Projects

### universal369.com (this repo)
Curated cosmic knowledge directory. Single-page HTML portal.
- **Repo**: `~/orion/universal369/` or `~/universal369/`
- **Deploy**: `scp -P 2222 index.html root@187.77.208.156:/home/universal369.com/public_html/`

### thesoulhunter.com
Curated spiritual resource directory — "hunting down the best resources so seekers don't have to."
- **Workflow**: `.paul/` project management (PROJECT.md, ROADMAP.md, STATE.md)
- **Status**: Design phase, roadmap pending finalization

### comedy-factory/
AI comedy production pipeline — daily Raven & Jax episodes.
- **Characters**: Raven (conspiracy-smart wife) + Jax (lovably clueless husband)
- **Pipeline**: 8-step daily workflow, 6am news scrape → 12pm publish
- **Stack**: Claude API (scripts) + ElevenLabs (voice) + D-ID (talking heads) + Pexels (stock)
- **Docs**: `comedy-factory/WORKFLOW.md`, `comedy-factory/COUPLE.md`

---

## Key Conventions

- Single-file HTML. No `npm install`. No build step.
- All fonts via Google Fonts CDN link in `<head>`
- Canvas starfield + video hero = standard atmosphere setup
- Git for code, Syncthing for assets/large files
- New domain on VPS: create `/home/DOMAIN.com/public_html/` + add in CyberPanel
