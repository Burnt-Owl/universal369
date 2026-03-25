#!/usr/bin/env python3
"""
Comedy Factory — Voice Setup
Finds and assigns the best ElevenLabs voices for Raven & Jax.

On a free ElevenLabs plan: auto-selects from built-in library voices.
On a paid plan: creates custom voices via Voice Design API.

Usage:
  python comedy-factory/setup_voices.py           # auto-select from library
  python comedy-factory/setup_voices.py --custom  # create via Voice Design (paid)
  python comedy-factory/setup_voices.py --list    # show all available voices
"""

import sys
import json
import argparse
import requests
from pathlib import Path

VAULT = Path.home() / ".comedy-factory" / ".env"
ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# Best library voice matches for each character
# Keyed by voice_id → description used for matching
LIBRARY_PICKS = {
    "raven": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Sarah",
        "reason": "Young American female, confident and clear — matches Raven's sharp delivery",
    },
    "jax": {
        "voice_id": "CwhRBWXzGAHq8TQ4Fs17",
        "name": "Roger",
        "reason": "Laid-back, casual, resonant American male — matches Jax's warm, unhurried energy",
    },
}

# Voice Design prompts for paid plan custom creation
CUSTOM_DESIGNS = {
    "raven": {
        "name": "Raven",
        "description": "Raven from the Raven & Jax comedy series",
        "voice_description": (
            "A woman in her early 30s with a sharp, dry, confident American voice. "
            "Fast-paced and witty, slightly skeptical tone, clear diction."
        ),
        "text": (
            "So apparently this was all planned six months ago. "
            "I literally told you this would happen. There are no coincidences, Jax."
        ),
    },
    "jax": {
        "name": "Jax",
        "description": "Jax from the Raven & Jax comedy series",
        "voice_description": (
            "A man in his early 30s with a warm, casual, slightly husky American voice. "
            "Laid-back and slow-paced, conversational and friendly."
        ),
        "text": (
            "Wait — who's that again? Okay but like... is that bad? "
            "That's wild. You want another beer?"
        ),
    },
}


def _load_vault() -> dict:
    values = {}
    if VAULT.exists():
        for line in VAULT.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
    return values


def _write_vault(updates: dict):
    current = _load_vault()
    current.update(updates)
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Comedy Factory — Secrets Vault",
             "# ~/.comedy-factory/.env — outside the git repo, never committed.", ""]
    for k, v in current.items():
        lines.append(f"{k}={v}")
    VAULT.write_text("\n".join(lines) + "\n")
    VAULT.chmod(0o600)


def get_api_key() -> str:
    key = _load_vault().get("ELEVENLABS_API_KEY", "")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY not found in ~/.comedy-factory/.env")
        print("Run: python comedy-factory/setup_keys.py")
        sys.exit(1)
    return key


def list_voices(api_key: str) -> list:
    resp = requests.get(
        f"{ELEVENLABS_BASE}/voices",
        headers={"xi-api-key": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("voices", [])


def use_library_voices(api_key: str) -> dict:
    """Select best library matches for Raven & Jax."""
    voices = list_voices(api_key)
    available_ids = {v["voice_id"] for v in voices}

    result = {}
    for char, pick in LIBRARY_PICKS.items():
        if pick["voice_id"] in available_ids:
            print(f"  {char.capitalize()}: {pick['name']} ({pick['voice_id']})")
            print(f"           {pick['reason']}")
            result[char] = pick["voice_id"]
        else:
            # Voice not in account — find closest by gender/age/accent
            print(f"  {char.capitalize()}: {pick['name']} not in account, finding alternative...")
            gender = "female" if char == "raven" else "male"
            accent = "american"
            candidates = [
                v for v in voices
                if v.get("labels", {}).get("gender") == gender
                and v.get("labels", {}).get("accent") == accent
            ]
            if candidates:
                v = candidates[0]
                print(f"           Using {v['name']} ({v['voice_id']}) instead")
                result[char] = v["voice_id"]
            else:
                print(f"  WARNING: No suitable voice found for {char}")
                result[char] = None
    return result


def create_custom_voices(api_key: str) -> dict:
    """Create Raven & Jax via ElevenLabs Voice Design API (paid plans only)."""
    result = {}
    for char, spec in CUSTOM_DESIGNS.items():
        print(f"\n  Creating {spec['name']} via Voice Design...")

        # Step 1: Generate preview
        design_resp = requests.post(
            f"{ELEVENLABS_BASE}/text-to-voice/design",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "voice_description": spec["voice_description"],
                "text": spec["text"],
                "auto_enhance": True,
            },
            timeout=60,
        )
        if design_resp.status_code == 422:
            print("  ERROR: Voice Design requires a paid ElevenLabs plan.")
            print("  Run without --custom to use library voices instead.")
            sys.exit(1)
        design_resp.raise_for_status()
        previews = design_resp.json().get("previews", [])
        if not previews:
            raise RuntimeError(f"No previews returned for {char}")
        generated_voice_id = previews[0]["generated_voice_id"]

        # Step 2: Save voice
        create_resp = requests.post(
            f"{ELEVENLABS_BASE}/text-to-voice/create",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "name": spec["name"],
                "description": spec["description"],
                "generated_voice_id": generated_voice_id,
            },
            timeout=30,
        )
        create_resp.raise_for_status()
        voice_id = create_resp.json()["voice_id"]
        print(f"  {spec['name']} created → voice_id: {voice_id}")
        result[char] = voice_id

    return result


def main():
    parser = argparse.ArgumentParser(description="Comedy Factory voice setup")
    parser.add_argument("--custom", action="store_true",
                        help="Create custom voices via Voice Design (paid ElevenLabs plan required)")
    parser.add_argument("--list", action="store_true",
                        help="List all available voices in your ElevenLabs account")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.list:
        voices = list_voices(api_key)
        print(f"\nAvailable voices ({len(voices)}):\n")
        for v in voices:
            labels = v.get("labels", {})
            print(f"  {v['name']:<25} {v['voice_id']}  "
                  f"{labels.get('gender','')}/{labels.get('age','')}/{labels.get('accent','')}")
        return

    print("\n=== Comedy Factory — Voice Setup ===\n")

    if args.custom:
        print("Mode: Custom Voice Design (paid)\n")
        ids = create_custom_voices(api_key)
    else:
        print("Mode: Library voices (free)\n")
        ids = use_library_voices(api_key)

    # Save to vault
    updates = {}
    if ids.get("raven"):
        updates["RAVEN_VOICE_ID"] = ids["raven"]
    if ids.get("jax"):
        updates["JAX_VOICE_ID"] = ids["jax"]

    if updates:
        _write_vault(updates)
        print(f"\nSaved to {VAULT}")
        for k, v in updates.items():
            print(f"  {k}={v}")
    else:
        print("\nNo voice IDs saved — check errors above.")

    print("\nNext: python comedy-factory/run_daily.py --test-config\n")


if __name__ == "__main__":
    main()
