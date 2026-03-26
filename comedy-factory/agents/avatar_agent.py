"""
Avatar Agent — generates D-ID talking head videos for Raven and Jax.

Uses D-ID Talks API:
  1. Upload character portrait → get hosted image URL
  2. Upload ElevenLabs audio   → get hosted audio URL
  3. POST /talks               → submit render job
  4. Poll GET /talks/{id}      → wait for status "done"
  5. Download result_url       → save as raven-avatar.mp4 / jax-avatar.mp4

Output: runs/YYYY-MM-DD/raven-avatar.mp4, jax-avatar.mp4

The resulting videos are lip-synced talking head clips — the character's face
actually moves and speaks. These replace the static-image clips in video_agent.
"""

import time
import requests
from pathlib import Path


DID_API_URL = "https://api.d-id.com"
POLL_INTERVAL = 5   # seconds between status checks
POLL_TIMEOUT  = 300 # max seconds to wait per render


def _auth(api_key: str) -> dict:
    """
    D-ID API key format from dashboard: base64(email):raw_secret
    HTTP Basic auth requires base64(username:password), so we encode the whole key.
    """
    import base64
    encoded = base64.b64encode(api_key.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _upload_image(portrait: Path, api_key: str) -> str:
    """Upload character portrait PNG to D-ID, return hosted URL."""
    with open(portrait, "rb") as f:
        resp = requests.post(
            f"{DID_API_URL}/images",
            headers=_auth(api_key),
            files={"image": (portrait.name, f, "image/png")},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["url"]


def _upload_audio(audio: Path, api_key: str) -> str:
    """Upload MP3 audio to D-ID, return hosted URL."""
    with open(audio, "rb") as f:
        resp = requests.post(
            f"{DID_API_URL}/audios",
            headers=_auth(api_key),
            files={"audio": (audio.name, f, "audio/mpeg")},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["url"]


def _create_talk(image_url: str, audio_url: str, api_key: str) -> str:
    """Submit a D-ID talk render job, return talk_id."""
    headers = {**_auth(api_key), "Content-Type": "application/json"}
    payload = {
        "source_url": image_url,
        "script": {
            "type": "audio",
            "audio_url": audio_url,
        },
        "config": {
            "fluent": True,        # natural head motion
            "pad_audio": 0.0,
            "result_format": "mp4",
        },
    }
    resp = requests.post(f"{DID_API_URL}/talks", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["id"]


def _poll_talk(talk_id: str, api_key: str) -> str:
    """Poll until status == 'done', return result_url."""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{DID_API_URL}/talks/{talk_id}",
            headers=_auth(api_key),
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json()
        status = data.get("status", "")
        if status == "done":
            return data["result_url"]
        if status == "error":
            raise RuntimeError(f"D-ID render error: {data.get('error', data)}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"D-ID talk {talk_id} timed out after {POLL_TIMEOUT}s")


def _download(url: str, out_path: Path):
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)


def generate_avatar(name: str, portrait: Path, audio: Path, out: Path, api_key: str) -> Path:
    """Full D-ID Talks pipeline for one character — portrait + audio → talking video."""
    print(f"[avatar_agent] {name}: uploading portrait...")
    image_url = _upload_image(portrait, api_key)

    print(f"[avatar_agent] {name}: uploading audio...")
    audio_url = _upload_audio(audio, api_key)

    print(f"[avatar_agent] {name}: submitting talk render...")
    talk_id = _create_talk(image_url, audio_url, api_key)

    print(f"[avatar_agent] {name}: waiting for render (id={talk_id})...")
    result_url = _poll_talk(talk_id, api_key)

    print(f"[avatar_agent] {name}: downloading result...")
    _download(result_url, out)

    mb = out.stat().st_size / 1_000_000
    print(f"[avatar_agent] {name} avatar done → {out.name} ({mb:.1f}MB)")
    return out


def run(run_dir: Path) -> tuple[Path, Path]:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import DID_API_KEY

    if not DID_API_KEY:
        raise ValueError("[avatar_agent] DID_API_KEY not set in ~/.comedy-factory/.env")

    chars_dir     = Path(__file__).parent.parent / "assets" / "characters"
    raven_portrait = chars_dir / "raven.png"
    jax_portrait   = chars_dir / "jax.png"

    for p in (raven_portrait, jax_portrait):
        if not p.exists():
            raise FileNotFoundError(f"[avatar_agent] Missing character portrait: {p}")

    raven_audio = run_dir / "raven-voice.mp3"
    jax_audio   = run_dir / "jax-voice.mp3"

    raven_out = run_dir / "raven-avatar.mp4"
    jax_out   = run_dir / "jax-avatar.mp4"

    generate_avatar("Raven", raven_portrait, raven_audio, raven_out, DID_API_KEY)
    generate_avatar("Jax",   jax_portrait,   jax_audio,   jax_out,   DID_API_KEY)

    return raven_out, jax_out


if __name__ == "__main__":
    from datetime import date
    run(Path(__file__).parent.parent / "runs" / date.today().isoformat())
