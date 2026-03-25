#!/usr/bin/env python3
"""
Comedy Factory — Onboarding
Runs all one-time setup tasks in sequence.

Usage:
  python comedy-factory/onboarding.py              # full onboarding flow
  python comedy-factory/onboarding.py --voices     # voices only
  python comedy-factory/onboarding.py --keys       # keys only
  python comedy-factory/onboarding.py --characters # generate character images only
  python comedy-factory/onboarding.py --verify     # verify config only
"""

import sys
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent


def run_step(label: str, cmd: list[str], critical: bool = True) -> bool:
    print(f"\n{'='*52}")
    print(f"  {label}")
    print(f"{'='*52}")
    result = subprocess.run(cmd, cwd=BASE_DIR.parent)
    if result.returncode != 0:
        print(f"\n  [FAILED] {label}")
        if critical:
            print("  Stopping — fix the error above and re-run.\n")
            sys.exit(1)
        return False
    print(f"\n  [OK] {label}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Comedy Factory onboarding wizard")
    parser.add_argument("--voices", action="store_true", help="Set up ElevenLabs voices only")
    parser.add_argument("--keys", action="store_true", help="Run interactive key setup only")
    parser.add_argument("--characters", action="store_true",
                        help="Generate Raven & Jax character images only (requires LEONARDO_API_KEY)")
    parser.add_argument("--verify", action="store_true", help="Verify config only")
    args = parser.parse_args()

    run_all = not any([args.voices, args.keys, args.characters, args.verify])

    print("\n🎬 Comedy Factory — Onboarding\n")

    # Step 1: Voices
    if run_all or args.voices:
        run_step(
            "Step 1/4 — ElevenLabs Voices",
            [sys.executable, str(BASE_DIR / "setup_voices.py")],
        )

    # Step 2: Remaining keys (interactive)
    if run_all or args.keys:
        run_step(
            "Step 2/4 — API Keys",
            [sys.executable, str(BASE_DIR / "setup_keys.py")],
        )

    # Step 3: Verify config
    if run_all or args.verify:
        run_step(
            "Step 3/4 — Config Verification",
            [sys.executable, str(BASE_DIR / "run_daily.py"), "--test-config"],
        )

    # Step 4: Generate character images
    if run_all or args.characters:
        run_step(
            "Step 4/4 — Generate Raven & Jax Character Images",
            [sys.executable, str(BASE_DIR / "run_daily.py"),
             "--regen-characters", "--skip-publish", "--dry-run"],
            critical=False,  # skip gracefully if LEONARDO_API_KEY not set yet
        )

    print("\n✅ Onboarding complete!")
    print("   Run your first episode:")
    print("   python comedy-factory/run_daily.py --dry-run\n")


if __name__ == "__main__":
    main()
