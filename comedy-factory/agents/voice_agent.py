"""
Voice Agent — generates ElevenLabs audio for Raven and Jax.
Output: runs/YYYY-MM-DD/raven-voice.mp3, jax-voice.mp3
"""

import re
import time
import requests
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ELEVENLABS_API_KEY,
    RAVEN_VOICE_ID,
    JAX_VOICE_ID,
    RAVEN_VOICE_SETTINGS,
    JAX_VOICE_SETTINGS,
    MAX_RETRIES,
    RETRY_DELAYS,
)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def parse_script(script_md: str) -> list[tuple[str, str]]:
    """Parse script.md into list of (speaker, line) tuples."""
    lines = []
    for raw_line in script_md.split("\n"):
        raw_line = raw_line.strip()
        if raw_line.startswith("RAVEN:"):
            text = raw_line[6:].strip()
        elif raw_line.startswith("JAX:"):
            text = raw_line[4:].strip()
        else:
            continue
        # Strip stage directions like *(nodding)* or *[pause]*
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        text = re.sub(r'\[[^\]]+\]', '', text).strip()
        if text:
            speaker = "RAVEN" if raw_line.startswith("RAVEN") else "JAX"
            lines.append((speaker, text))
    return lines


def lines_for_speaker(parsed: list[tuple[str, str]], speaker: str) -> str:
    """Concatenate all lines for a speaker with natural pauses."""
    parts = [line for spk, line in parsed if spk == speaker]
    return "  ...  ".join(parts)  # ElevenLabs reads "..." as a pause


def _gtts_fallback(text: str, slow: bool = False) -> bytes:
    """Generate audio via Google TTS when ElevenLabs is unavailable."""
    import io
    from gtts import gTTS
    tts = gTTS(text, lang="en", slow=slow)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


def generate_audio(text: str, voice_id: str, voice_settings: dict, slow: bool = False) -> bytes:
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": voice_settings,
    }

    for attempt, delay in enumerate(RETRY_DELAYS + [None], 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            if delay is None:
                print(f"[voice_agent] ElevenLabs unavailable, falling back to gTTS.")
                return _gtts_fallback(text, slow=slow)
            print(f"[voice_agent] Attempt {attempt} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)


def run(run_dir: Path) -> tuple[Path, Path]:
    script_file = run_dir / "script.md"
    script_text = script_file.read_text()

    # Scan entire file — parse_script only picks up RAVEN:/JAX: lines
    parsed = parse_script(script_text)
    if not parsed:
        raise ValueError("[voice_agent] No dialogue lines found in script.")

    raven_text = lines_for_speaker(parsed, "RAVEN")
    jax_text = lines_for_speaker(parsed, "JAX")

    if not RAVEN_VOICE_ID or not JAX_VOICE_ID:
        raise ValueError("[voice_agent] RAVEN_VOICE_ID and JAX_VOICE_ID must be set in .env")

    print("[voice_agent] Generating Raven's voice...")
    raven_audio = generate_audio(raven_text, RAVEN_VOICE_ID, RAVEN_VOICE_SETTINGS, slow=False)
    raven_file = run_dir / "raven-voice.mp3"
    raven_file.write_bytes(raven_audio)

    print("[voice_agent] Generating Jax's voice...")
    jax_audio = generate_audio(jax_text, JAX_VOICE_ID, JAX_VOICE_SETTINGS, slow=True)
    jax_file = run_dir / "jax-voice.mp3"
    jax_file.write_bytes(jax_audio)

    print(f"[voice_agent] Audio saved → {raven_file.name}, {jax_file.name}")
    return raven_file, jax_file


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)
