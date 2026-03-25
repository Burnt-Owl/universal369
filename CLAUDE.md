# CLAUDE.md — Universal 369

## Project Overview

**Universal 369** (universal369.com) is a curated cosmic directory — a single-page static website that catalogs the internet's best resources for expanding consciousness, knowledge, and understanding. It features six curated categories of links spanning knowledge archives, learning platforms, science, philosophy, and creative inspiration.

A sibling project, **thesoulhunter** (thesoulhunter.com), is planned as a spiritual resource directory (see `.paul/PROJECT.md`).

**Author**: Lucretious (lucretious@mailfence.com)
**Design benchmark**: mysticoblivion.com

## Repository Structure

```
universal369/
├── index.html                    # The entire site — HTML, CSS, and JS in one file (~726 lines)
├── cosmic-energy-enhanced.mp4    # Background video asset (576KB)
├── HANDOFF.md                    # VPS deployment instructions
├── CLAUDE.md                     # This file
└── .paul/                        # PAUL project management system
    ├── PROJECT.md                # Project definition and requirements
    ├── ROADMAP.md                # Planned development phases
    ├── STATE.md                  # Current project readiness state
    └── HANDOFF-2026-03-18-init.md
```

## Tech Stack

This is a **zero-dependency, single-file website** — no build system, no package.json, no frameworks.

- **HTML5** — semantic structure (`<section>`, `<header>`, `<footer>`)
- **CSS3** — embedded in `<style>`, uses custom properties (variables), Flexbox, Grid, animations, media queries
- **Vanilla JavaScript** — embedded in `<script>`, strict mode, ES6+
- **Google Fonts** — Cinzel (headings), Cormorant Garamond (body)
- **Canvas API** — animated starfield background
- **IntersectionObserver** — scroll-reveal animations

## Design System

### Color Palette (CSS custom properties in `:root`)
| Variable       | Value     | Usage              |
|----------------|-----------|--------------------|
| `--bg`         | `#060810` | Page background    |
| `--gold`       | `#c9a84c` | Accents, headings  |
| `--purple`     | `#8b5cf6` | Links, highlights  |
| `--cyan`       | `#4db8c8` | Secondary accents  |
| `--text`       | `#cdc8d8` | Body text          |
| `--text-bright`| `#f0eef5` | Emphasized text    |

### Typography
- **Headers**: Cinzel (serif, uppercase, gold)
- **Body**: Cormorant Garamond (serif, light weight 300)
- **Base size**: 18px, line-height 1.7

### Aesthetic
Dark cosmic/esoteric theme. Smooth hover transitions, subtle glow effects, twinkling star canvas. The look should remain elegant and mystical — avoid anything that feels modern/corporate.

## Code Conventions

### Comment Style
Use Unicode box-drawing section dividers:
```css
/* ═══════════════════════════════════════════════
   SECTION NAME · DESCRIPTION
═══════════════════════════════════════════════ */
/* ── Subsection ── */
```

### CSS
- Use CSS custom properties from `:root` — never hardcode colors
- Hyphenated class names (e.g., `.category-card`, `.hero-section`)
- Mobile breakpoint at `max-width: 600px`
- Organize by page section: hero, categories, footer, then responsive overrides

### JavaScript
- Always `'use strict'`
- Functional style with named functions (e.g., `initCosmos()`, `initReveal()`)
- Use modern APIs: IntersectionObserver, requestAnimationFrame, Canvas
- No external libraries — keep everything vanilla

### HTML
- Semantic elements (`<section>`, `<header>`, `<footer>`)
- All content in a single `index.html` file — this is intentional, not a shortcut

## Deployment

**Platform**: CyberPanel + LiteSpeed on Hostinger VPS

| Detail     | Value                                            |
|------------|--------------------------------------------------|
| VPS IP     | 187.77.208.156                                   |
| SSH        | `ssh -p 2222 root@187.77.208.156`                |
| Site path  | `/home/universal369.com/public_html/`            |
| Files      | `index.html` + `cosmic-energy-enhanced.mp4`      |

Deploy via SCP:
```bash
scp -P 2222 index.html root@187.77.208.156:/home/universal369.com/public_html/
scp -P 2222 cosmic-energy-enhanced.mp4 root@187.77.208.156:/home/universal369.com/public_html/
```

See `HANDOFF.md` for full deployment details and troubleshooting.

## Testing

No automated tests. This is a static single-file site — QA is manual:
- Open `index.html` in a browser
- Check responsive layout at mobile (≤600px) and desktop widths
- Verify canvas starfield animation renders
- Confirm scroll-reveal animations trigger on scroll
- Test all external links in directory listings

## Key Guidelines for AI Assistants

1. **Keep it single-file** — all HTML, CSS, and JS belong in `index.html`. Do not split into separate files unless explicitly asked.
2. **Preserve the aesthetic** — dark cosmic theme, gold/purple/cyan palette, mystical serif fonts. Changes should feel cohesive with the existing design.
3. **No frameworks or build tools** — this is vanilla by design. Do not introduce npm, webpack, React, Tailwind, or similar.
4. **Use CSS variables** — reference `--gold`, `--purple`, etc. from `:root`. Never hardcode color values.
5. **Respect the comment style** — use the Unicode box-drawing dividers for new sections.
6. **Performance matters** — the site loads fast because it's minimal. Keep assets small, avoid heavy libraries.
7. **PAUL system** — project planning lives in `.paul/`. Respect that structure for roadmap and state tracking.
8. **Git branch**: `master` is the main branch.
