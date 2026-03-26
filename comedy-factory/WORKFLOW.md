# Comedy Factory: Daily Production Workflow

## Overview

**Output:** 1 x 1-2 min funny short film per day
**Characters:** Raven & Jax (see COUPLE.md)
**Format:** 9:16 vertical — YouTube Shorts + TikTok
**Theme:** Modern couple on the couch reacting to one global daily event

---

## Daily Pipeline

```
06:00 AM ──▶ [1. NEWS AGENT]     Scrape top global event of the day
     ──▶ [2. BRIEF AGENT]    Select & frame the event for comedy
     ──▶ [3. SCRIPT AGENT]   Write Raven & Jax dialogue (1-2 min)
     ──▶ [4. REVIEW GATE]    Human review / approve script (optional)
     ──▶ [5. VOICE AGENT]    Generate ElevenLabs audio for both characters
     ──▶ [6. VISUAL AGENT]   Generate character visuals via Leonardo.ai
     ──▶ [7. VIDEO AGENT]    Assemble: audio + visuals + captions + b-roll
     ──▶ [8. PUBLISH AGENT]  Post to YouTube Shorts + TikTok
12:00 PM ──▶ Video live
```

---

## Agent Specs

### 1. News Agent
- **Input:** None (triggers at 6am daily)
- **Task:** Fetch top 5-10 global news stories from the past 24 hours
- **Sources:** RSS feeds, NewsAPI, Reddit r/worldnews
- **Output:** `daily-brief.json` — list of events with headline, summary, source

### 2. Brief Agent
- **Input:** `daily-brief.json`
- **Task:** Score each event for comedy potential. Select the best one.
  - Score criteria: Absurdity level, relatability, couple-reaction potential
- **Output:** `selected-event.json` — chosen event + comedy angle

### 3. Script Agent
- **Input:** `selected-event.json` + `COUPLE.md` (character bible)
- **Task:** Write a 1-2 minute dialogue script
  - Format: Screenplay style — Raven line, Jax line, back and forth
  - Tone: Natural conversation, real couple energy, punchy jokes
  - Length: ~150-200 words (1-2 min when spoken)
- **Output:** `script.md`

### 4. Review Gate (Optional Human Step)
- Script gets sent to Slack/email for quick approval
- 30-min window — auto-approves if no response
- Can override the selected event or edit lines

### 5. Voice Agent
- **Input:** `script.md`
- **Task:** Generate ElevenLabs audio for Raven + Jax separately
  - Use locked voice IDs for consistency
  - Export: `raven-voice.mp3`, `jax-voice.mp3`
- **Output:** Two audio files

### 6. Visual Agent
- **Input:** Character style prompts (from `PROMPTS.md`)
- **Task:** Generate scene images via Leonardo.ai
  - 2-3 background/couch shots
  - Character reference images (consistent look)
- **Output:** Image assets in `assets/[date]/`

### 7. Video Agent
- **Input:** Audio files + images + script
- **Task:** Assemble final video
  - Sync audio to character visuals (lip sync if using HeyGen)
  - Add auto-captions (burnt-in subtitles)
  - Add title card: the event headline, styled
  - Export: 9:16, 1080x1920, MP4
- **Output:** `final-[date].mp4`

### 8. Publish Agent
- **Input:** `final-[date].mp4` + auto-generated title/description
- **Task:** Upload to:
  - YouTube Shorts (via YouTube Data API)
  - TikTok (via TikTok API or manual)
- **Output:** Published URLs logged to `publish-log.json`

---

## File Structure Per Day

```
comedy-factory/
├── runs/
│   └── 2026-03-25/
│       ├── daily-brief.json
│       ├── selected-event.json
│       ├── script.md
│       ├── assets/
│       │   ├── background-01.png
│       │   └── background-02.png
│       ├── raven-voice.mp3
│       ├── jax-voice.mp3
│       └── final-2026-03-25.mp4
├── publish-log.json
```

---

## Error Handling

| Failure Point | Recovery |
|---------------|----------|
| No good news story found | Pull from backup topics list (culture, sports, viral moments) |
| Script too long | Auto-trim to 200 words max |
| Voice generation fails | Retry x3, then flag for manual |
| Video export fails | Alert and hold — do not publish partial |
| Publish fails | Retry x3, log error, alert human |

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| NewsAPI / RSS | News sourcing |
| Claude API | Brief selection + script writing |
| ElevenLabs API | Voice generation (Raven & Jax) |
| Leonardo.ai API | Character / scene image generation |
| Midjourney (manual) | Character reference images (one-time setup) |
| ffmpeg | Video assembly + captioning |
| YouTube Data API | Publishing to YouTube Shorts |
| TikTok API | Publishing to TikTok |
| Python / n8n | Workflow orchestration |
| Cron / GitHub Actions | Daily scheduling |

---

*Created: 2026-03-25 | Comedy Factory v0.1*
