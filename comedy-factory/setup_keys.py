#!/usr/bin/env python3
"""
Comedy Factory — Secrets Setup
Prompts for each API key and saves them to ~/.comedy-factory/.env (outside the repo).

Usage:
  python comedy-factory/setup_keys.py
"""

import os
from pathlib import Path

VAULT = Path.home() / ".comedy-factory" / ".env"

KEYS = [
    {
        "key": "NEWS_API_KEY",
        "label": "NewsAPI key",
        "where": "newsapi.org  →  Account  →  API key",
    },
    {
        "key": "ANTHROPIC_API_KEY",
        "label": "Anthropic API key",
        "where": "console.anthropic.com  →  API Keys  →  Create key",
    },
    {
        "key": "ELEVENLABS_API_KEY",
        "label": "ElevenLabs API key",
        "where": "elevenlabs.io  →  Profile (top-right)  →  API Key",
    },
    {
        "key": "RAVEN_VOICE_ID",
        "label": "Raven voice ID",
        "where": "elevenlabs.io  →  Voices  →  create 'Raven'  →  copy the ID",
    },
    {
        "key": "JAX_VOICE_ID",
        "label": "Jax voice ID",
        "where": "elevenlabs.io  →  Voices  →  create 'Jax'  →  copy the ID",
    },
    {
        "key": "LEONARDO_API_KEY",
        "label": "Leonardo.ai API key",
        "where": "app.leonardo.ai  →  User Settings  →  API Access  →  Create key",
    },
    {
        "key": "TIKTOK_ACCESS_TOKEN",
        "label": "TikTok access token",
        "where": "developers.tiktok.com  →  your app  →  Access token  (optional, skip to defer)",
        "optional": True,
    },
    {
        "key": "SLACK_WEBHOOK_URL",
        "label": "Slack webhook URL",
        "where": "api.slack.com/apps  →  your app  →  Incoming Webhooks  (optional, for review gate)",
        "optional": True,
    },
]


def _read_vault():
    """Read existing vault into a dict."""
    values = {}
    if VAULT.exists():
        for line in VAULT.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
    return values


def _write_vault(values: dict):
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Comedy Factory — Secrets Vault", "# ~/.comedy-factory/.env — outside the git repo, never committed.", ""]
    for k, v in values.items():
        lines.append(f"{k}={v}")
    VAULT.write_text("\n".join(lines) + "\n")
    VAULT.chmod(0o600)


def main():
    print("\n=== Comedy Factory — Key Setup ===")
    print(f"Saving to: {VAULT}\n")

    current = _read_vault()
    updated = dict(current)

    for spec in KEYS:
        key = spec["key"]
        label = spec["label"]
        where = spec["where"]
        optional = spec.get("optional", False)

        existing = current.get(key, "")
        masked = f"{existing[:6]}..." if len(existing) > 6 else existing
        prompt_hint = f" [{masked}]" if existing else ""
        optional_tag = " (optional — press Enter to skip)" if optional else ""

        print(f"  {label}{optional_tag}")
        print(f"  Get it at: {where}")
        value = input(f"  Paste value{prompt_hint}: ").strip()

        if value:
            updated[key] = value
        elif existing:
            print(f"  Keeping existing value.")
        else:
            print(f"  Skipped.")

        print()

    # Always include REVIEW_GATE_ENABLED
    if "REVIEW_GATE_ENABLED" not in updated:
        updated["REVIEW_GATE_ENABLED"] = "false"

    _write_vault(updated)

    print(f"Saved to {VAULT}")
    print("\nVerify with:")
    print("  python comedy-factory/run_daily.py --test-config\n")


if __name__ == "__main__":
    main()
