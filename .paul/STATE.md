# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-03-18)

**Core value:** Seekers can discover the best spiritual websites, teachers, and creators in one curated place.
**Current focus:** Site built — ready to deploy

## Current Position

Milestone: v0.1 Initial Release
Phase: Build complete
Plan: Site built — 8 categories, 40 curated links
Status: Ready to deploy to VPS
Last activity: 2026-04-02 — Full site built

Progress:
- Milestone: [████████░░] 80%

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ○     [Ready to deploy]
```

## What Was Built

`thesoulhunter/index.html` — single-file HTML site, same design DNA as universal369.com.

### 8 Categories (40 total curated links)
1. **Teachers & Guides** — Rupert Spira, Adyashanti, Ram Dass, Tara Brach, Mooji
2. **Consciousness & Awakening** — SAND, Nonduality.com, Conscious TV, Batgap, Actualized.org
3. **Ancient Wisdom** — Hermetic Library, Gnosis Archive, Theosophical Society, Vedanta, Sacred Texts
4. **Meditation & Practice** — Dhamma.org, Wim Hof, Tricycle, Insight Timer, Soma Breath
5. **Sacred Geometry & Cosmos** — Geometry Code, Joe Dispenza, Gregg Braden, HeartMath, Gaia
6. **Astrology & Cycles** — Astro.com, The Astrology Podcast, Chani Nicholas, Cafe Astrology, Astrology King
7. **Sound & Frequency** — Brain.fm, MyNoise, Acoustic Brainwave, Healing Frequencies, Music for Programming
8. **Creators & Channels** — Alan Watts Org, Koi Fresco, Nonduality TV, Michael Sealey, Joe Rogan consciousness eps

## Accumulated Context

### Decisions
- Single-file HTML, no framework, same CSS/JS as universal369.com
- No video background (no asset exists) — canvas cosmos + stronger purple glow hero overlay
- Hero: "THE SOUL HUNTER / THE PATH · THE PRACTICE · THE TRUTH"
- 8 categories chosen from CLAUDE.md Mystic Agent topic map
- Curation criteria: depth, authenticity, non-commercial, timeless

### Deferred Issues
- VPS directory `/home/thesoulhunter.com/public_html/` needs to be created in CyberPanel before deploy

### Deploy Command (when ready)
```bash
scp -P 2222 thesoulhunter/index.html root@187.77.208.156:/home/thesoulhunter.com/public_html/
ssh -p 2222 root@187.77.208.156 "chmod 644 /home/thesoulhunter.com/public_html/index.html"
curl -s -o /dev/null -w "%{http_code}" https://thesoulhunter.com
```

## Session Continuity

Last session: 2026-04-02
Stopped at: Site built, needs deploy to VPS
Next action: Create thesoulhunter.com vhost in CyberPanel, then deploy
Resume file: .paul/STATE.md (this file)

---
*STATE.md — Updated after every significant action*
