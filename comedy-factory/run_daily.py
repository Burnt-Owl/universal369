#!/usr/bin/env python3
"""
Comedy Factory — Daily Orchestrator
Runs the full Raven & Jax video production pipeline.

Usage:
  python run_daily.py                    # Full run including publish
  python run_daily.py --dry-run          # Script only, no API calls for media
  python run_daily.py --skip-publish     # Full pipeline, skip YouTube/TikTok upload
  python run_daily.py --skip-visuals     # Skip visual frame generation
  python run_daily.py --regen-characters # Re-generate Raven & Jax shots via Leonardo
  python run_daily.py --gen-characters   # Generate characters only (no news/script needed)
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
    avatar_agent,
    stock_agent,
    video_agent,
    publish_agent,
)


REQUIRED_VARS = [
    ("NEWS_API_KEY", "newsapi.org"),
    ("ANTHROPIC_API_KEY", "console.anthropic.com"),
    ("ELEVENLABS_API_KEY", "elevenlabs.io"),
    ("RAVEN_VOICE_ID", "ElevenLabs voice ID for Raven"),
    ("JAX_VOICE_ID", "ElevenLabs voice ID for Jax"),
]

OPTIONAL_VARS = [
    ("GEMINI_API_KEY", "aistudio.google.com (backgrounds — free 500/day, preferred)"),
    ("LEONARDO_API_KEY", "app.leonardo.ai (backgrounds fallback + --regen-characters)"),
    ("DID_API_KEY", "d-id.com — talking head animation (Raven & Jax lip-sync)"),
    ("PEXELS_API_KEY", "pexels.com/api — stock video footage (real people reacting)"),
    ("CANVA_ACCESS_TOKEN", "canva.com (episode thumbnail)"),
    ("TIKTOK_ACCESS_TOKEN", "developers.tiktok.com"),
    ("YOUTUBE_CLIENT_SECRETS", "Google Cloud Console"),
    ("SLACK_WEBHOOK_URL", "Slack app webhook (for review gate)"),
]

# At least one image provider must be set for visual generation
IMAGE_PROVIDER_VARS = ("GEMINI_API_KEY", "LEONARDO_API_KEY")


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

    # Check image provider
    has_image_provider = any(os.getenv(v, "") for v in IMAGE_PROVIDER_VARS)
    if has_image_provider:
        print("  [OK ] Image provider: set")
    else:
        all_ok = False
        print("  [MISSING] Image provider: set GEMINI_API_KEY or LEONARDO_API_KEY")

    print()
    if all_ok:
        print("All required vars are set. Ready to run.")
    else:
        print("Some required vars are missing. Fill in ~/.comedy-factory/.env")
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
    parser.add_argument("--skip-visuals", action="store_true", help="Skip visual frame generation")
    parser.add_argument("--skip-avatars", action="store_true", help="Skip D-ID avatar generation (use static frames)")
    parser.add_argument("--regen-characters", action="store_true", help="Force re-generation of Raven & Jax character PNGs via Leonardo")
    parser.add_argument("--gen-characters", action="store_true", help="Generate characters only — skips news/script steps")
    parser.add_argument("--date", default=date.today().isoformat(), help="Run date (YYYY-MM-DD)")
    parser.add_argument("--test-config", action="store_true", help="Validate all env vars, no API calls")
    args = parser.parse_args()

    if args.test_config:
        _test_config()
        return

    if args.gen_characters:
        print("\n🎨 Generating Raven & Jax character images via Leonardo...\n")
        chars = visual_agent.ensure_characters(regen=True)
        for name, path in chars.items():
            if path and path.exists():
                print(f"  ✅ {name}: {path}")
            else:
                print(f"  ❌ {name}: generation failed")
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

    # 5. Download stock video clips (cached after first run)
    import os
    if os.getenv("PEXELS_API_KEY", ""):
        assets_dir = Path(__file__).parent / "assets"
        step("Stock Agent", stock_agent.run, assets_dir)
    else:
        print("\n[SKIPPED] Stock Agent (PEXELS_API_KEY not set)")

    # 6. Generate D-ID talking-head avatars (optional — skipped if DID_API_KEY not set)
    if not args.skip_avatars and os.getenv("DID_API_KEY", ""):
        step("Avatar Agent", avatar_agent.run, run_dir)
    else:
        reason = "--skip-avatars flag" if args.skip_avatars else "DID_API_KEY not set"
        print(f"\n[SKIPPED] Avatar Agent ({reason})")

    # 7. Generate visuals (optional)
    if not args.skip_visuals:
        step("Visual Agent", visual_agent.run, run_dir,
             regen_characters=args.regen_characters)
    else:
        print("\n[SKIPPED] Visual Agent")

    # 7. Assemble video
    step("Video Agent", video_agent.run, run_dir)

    # 8. Publish (optional)
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
