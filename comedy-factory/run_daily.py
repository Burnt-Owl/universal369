#!/usr/bin/env python3
"""
Comedy Factory — Daily Orchestrator
Runs the full Raven & Jax video production pipeline.

Usage:
  python run_daily.py                    # Full run including publish
  python run_daily.py --dry-run          # Script only, no API calls for media
  python run_daily.py --skip-publish     # Full pipeline, skip YouTube/TikTok upload
  python run_daily.py --skip-visuals     # Skip Leonardo.ai image generation
  python run_daily.py --date 2026-03-25  # Run for a specific date
  python run_daily.py --test-config      # Validate all env vars are set (no API calls)
"""

import sys
import json
import argparse
import traceback
from datetime import date
from pathlib import Path

# Add comedy-factory root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import RUNS_DIR
from agents import (
    news_agent,
    brief_agent,
    script_agent,
    voice_agent,
    visual_agent,
    video_agent,
    publish_agent,
)


REQUIRED_VARS = [
    ("NEWS_API_KEY", "newsapi.org"),
    ("ANTHROPIC_API_KEY", "console.anthropic.com"),
    ("ELEVENLABS_API_KEY", "elevenlabs.io"),
    ("RAVEN_VOICE_ID", "ElevenLabs voice ID for Raven"),
    ("JAX_VOICE_ID", "ElevenLabs voice ID for Jax"),
    ("LEONARDO_API_KEY", "app.leonardo.ai"),
]

OPTIONAL_VARS = [
    ("TIKTOK_ACCESS_TOKEN", "developers.tiktok.com"),
    ("YOUTUBE_CLIENT_SECRETS", "Google Cloud Console"),
    ("SLACK_WEBHOOK_URL", "Slack app webhook (for review gate)"),
]


def _test_config():
    import os
    print("\n--- Comedy Factory Config Check ---\n")
    all_ok = True
    for var, source in REQUIRED_VARS:
        val = os.getenv(var, "")
        status = "OK" if val else "MISSING"
        if not val:
            all_ok = False
        print(f"  [{status}] {var:<30} ({source})")

    print()
    for var, source in OPTIONAL_VARS:
        val = os.getenv(var, "")
        status = "SET" if val else "not set"
        print(f"  [{status}] {var:<30} ({source})")

    print()
    if all_ok:
        print("All required vars are set. Ready to run.")
    else:
        print("Some required vars are missing. Fill in comedy-factory/.env")
    print()


def step(name: str, fn, *args, **kwargs):
    print(f"\n{'='*50}")
    print(f"  STEP: {name}")
    print(f"{'='*50}")
    try:
        result = fn(*args, **kwargs)
        print(f"  [OK] {name} complete.")
        return result
    except Exception as e:
        print(f"  [FAILED] {name}: {e}")
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(description="Comedy Factory daily runner")
    parser.add_argument("--dry-run", action="store_true", help="Script only, no media generation")
    parser.add_argument("--skip-publish", action="store_true", help="Skip YouTube/TikTok upload")
    parser.add_argument("--skip-visuals", action="store_true", help="Skip Leonardo.ai image generation")
    parser.add_argument("--date", default=date.today().isoformat(), help="Run date (YYYY-MM-DD)")
    parser.add_argument("--test-config", action="store_true", help="Validate all env vars, no API calls")
    args = parser.parse_args()

    if args.test_config:
        _test_config()
        return

    run_dir = RUNS_DIR / args.date
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 COMEDY FACTORY — {args.date}")
    print(f"   Run dir: {run_dir}")
    if args.dry_run:
        print("   Mode: DRY RUN (script only)")
    elif args.skip_publish:
        print("   Mode: SKIP PUBLISH")

    # 1. Fetch news
    step("News Agent", news_agent.run, run_dir)

    # 2. Select best story
    step("Brief Agent", brief_agent.run, run_dir)

    # 3. Write script
    step("Script Agent", script_agent.run, run_dir)

    if args.dry_run:
        print("\n✅ DRY RUN complete. Check script at:")
        print(f"   {run_dir / 'script.md'}")
        return

    # 4. Generate voices
    step("Voice Agent", voice_agent.run, run_dir)

    # 5. Generate visuals (optional)
    if not args.skip_visuals:
        step("Visual Agent", visual_agent.run, run_dir)
    else:
        print("\n[SKIPPED] Visual Agent")

    # 6. Assemble video
    step("Video Agent", video_agent.run, run_dir)

    # 7. Publish
    if not args.skip_publish:
        step("Publish Agent", publish_agent.run, run_dir, dry_run=False)
    else:
        print("\n[SKIPPED] Publish Agent")

    print(f"\n✅ Comedy Factory run complete for {args.date}")
    video_files = list(run_dir.glob("final-*.mp4"))
    if video_files:
        print(f"   Video: {video_files[0]}")

    log_file = RUNS_DIR / "publish-log.json"
    if log_file.exists():
        log = json.loads(log_file.read_text())
        latest = next((e for e in reversed(log) if e["date"] == args.date), None)
        if latest:
            if latest.get("youtube_url"):
                print(f"   YouTube: {latest['youtube_url']}")
            if latest.get("tiktok_url"):
                print(f"   TikTok: {latest['tiktok_url']}")


if __name__ == "__main__":
    main()
