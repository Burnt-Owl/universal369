"""
Visual Agent — generates scene frames for Raven & Jax episodes.

Pipeline:
  1. Gemini Imagen  — 2 episode-specific background images (free, per-episode)
  2. Leonardo.ai    — Raven & Jax character shots (paid, cached globally)
  3. PIL/Pillow     — composites backgrounds + characters + text into frame-*.png
  4. Canva          — optional thumbnail (skipped if CANVA_ACCESS_TOKEN not set)

Output: runs/YYYY-MM-DD/assets/frame-01.png, frame-02.png
        runs/YYYY-MM-DD/assets/thumbnail.png  (optional)
"""

import base64
import io
import json
import time
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    GEMINI_API_KEY, LEONARDO_API_KEY, CANVA_ACCESS_TOKEN,
    BASE_DIR, MAX_RETRIES, RETRY_DELAYS,
    VIDEO_WIDTH, VIDEO_HEIGHT,
)

# ── Gemini Imagen ─────────────────────────────────────────────────────────────
GEMINI_IMAGEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "imagen-3.0-generate-002:predict"
)

# ── Leonardo ──────────────────────────────────────────────────────────────────
LEONARDO_BASE = "https://cloud.leonardo.ai/api/rest/v1"
LEONARDO_MODEL_ID = "aa77f04e-3eec-4034-9c07-d0f619684628"  # Leonardo Phoenix

# ── Canva ─────────────────────────────────────────────────────────────────────
CANVA_API_BASE = "https://api.canva.com/rest/v1"

# ── Character cache — shared across all episodes ──────────────────────────────
CHARACTERS_DIR = BASE_DIR / "assets" / "characters"

# ── Character prompts (from COUPLE.md / PROMPTS.md) ──────────────────────────
CHARACTER_PROMPTS = {
    "raven": (
        "Photorealistic portrait of a woman in her early 30s, white and mixed-race, "
        "dark hair, multiple tattoos on arms and neck, sharp observant eyes, slightly "
        "skeptical expression, wearing casual everyday clothes (hoodie or band tee), "
        "sitting on a couch in a dimly lit living room, TV glow in background, coffee "
        "mug nearby. Cinematic lighting, 8k, ultra-detailed skin texture, shot on 35mm, "
        "natural ambient light. No makeup or minimal makeup. 9:16 vertical portrait."
    ),
    "jax": (
        "Photorealistic portrait of a man in his early-to-mid 30s, white and mixed-race, "
        "tattoos on arms and chest visible, slightly disheveled hair, relaxed warm "
        "expression with a hint of confusion, holding a beer can or glass, wearing casual "
        "clothes (t-shirt, open flannel), sitting on a couch in a dimly lit living room, "
        "TV glow in background. Cinematic lighting, 8k, ultra-detailed, shot on 35mm, "
        "natural ambient light. Scruffy stubble. 9:16 vertical portrait."
    ),
}


# ═════════════════════════════════════════════════════════════════════════════
# Layer 1 — Gemini Imagen backgrounds (per-episode, free)
# ═════════════════════════════════════════════════════════════════════════════

def _build_scene_prompts(headline: str) -> list[str]:
    short = headline[:80]
    return [
        (
            f"A modern living room at night, cozy couch with throw pillows, coffee table "
            f"with beer cans and an open laptop showing news about '{short}', "
            f"warm TV glow, low ambient lighting, slightly messy but lived-in, no people. "
            f"Cinematic 9:16 vertical, photorealistic, 8k, shot on 35mm."
        ),
        (
            f"Close-up of a coffee table in a dim living room, beer cans, TV remote, phone "
            f"screen lit with news about '{headline[:60]}', warm glow from TV off-camera. "
            f"Cinematic, 9:16 vertical, photorealistic, bokeh background."
        ),
    ]


def generate_backgrounds_imagen(headline: str) -> list[bytes]:
    """Calls Gemini Imagen 3 to generate 2 episode-specific background images."""
    if not GEMINI_API_KEY:
        raise ValueError("[visual_agent] GEMINI_API_KEY must be set in .env")

    url = f"{GEMINI_IMAGEN_URL}?key={GEMINI_API_KEY}"
    results = []

    for i, prompt in enumerate(_build_scene_prompts(headline), 1):
        print(f"[visual_agent] Generating background-0{i} via Gemini Imagen...")
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"aspectRatio": "9:16", "sampleCount": 1},
        }
        for attempt, delay in enumerate(RETRY_DELAYS + [None], 1):
            try:
                resp = requests.post(url, json=payload, timeout=60)
                resp.raise_for_status()
                b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
                results.append(base64.b64decode(b64))
                break
            except Exception as e:
                if delay is None:
                    raise RuntimeError(f"Imagen scene {i} failed after {attempt} attempts: {e}")
                print(f"[visual_agent] Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    return results


# ═════════════════════════════════════════════════════════════════════════════
# Layer 2 — Leonardo character shots (one-time, cached)
# ═════════════════════════════════════════════════════════════════════════════

def _generate_character_leonardo(name: str, prompt: str) -> bytes:
    if not LEONARDO_API_KEY:
        raise ValueError(
            f"[visual_agent] LEONARDO_API_KEY required to generate '{name}'. "
            "Add it to .env and run with --regen-characters."
        )

    headers = {
        "authorization": f"Bearer {LEONARDO_API_KEY}",
        "content-type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "modelId": LEONARDO_MODEL_ID,
        "width": 1080,
        "height": 1920,
        "num_images": 1,
        "photoReal": True,
        "alchemy": True,
    }

    gen_id = None
    for attempt, delay in enumerate(RETRY_DELAYS + [None], 1):
        try:
            resp = requests.post(
                f"{LEONARDO_BASE}/generations",
                json=payload, headers=headers, timeout=30,
            )
            resp.raise_for_status()
            gen_id = resp.json()["sdGenerationJob"]["generationId"]
            break
        except Exception as e:
            if delay is None:
                raise RuntimeError(f"Leonardo request failed for '{name}': {e}")
            print(f"[visual_agent/leonardo] Attempt {attempt} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)

    print(f"[visual_agent] Waiting for Leonardo generation {gen_id}...")
    for _ in range(30):
        time.sleep(4)
        poll = requests.get(
            f"{LEONARDO_BASE}/generations/{gen_id}",
            headers=headers, timeout=15,
        )
        poll.raise_for_status()
        data = poll.json().get("generations_by_pk", {})
        if data.get("status") == "COMPLETE":
            img_url = data["generated_images"][0]["url"]
            return requests.get(img_url, timeout=30).content
        elif data.get("status") == "FAILED":
            raise RuntimeError(f"Leonardo generation failed for '{name}': {data}")

    raise TimeoutError(f"Leonardo generation timed out for '{name}'")


def ensure_characters(regen: bool = False) -> dict:
    """
    Returns {name: Path} for Raven and Jax character PNGs.
    Generates via Leonardo only when cache is missing or regen=True.
    Values are None if generation was skipped and no cache exists.
    """
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    result = {}

    for name, prompt in CHARACTER_PROMPTS.items():
        cache_path = CHARACTERS_DIR / f"{name}.png"

        if cache_path.exists() and not regen:
            print(f"[visual_agent] Using cached character: {name}")
            result[name] = cache_path
        else:
            reason = "forced regen" if regen else "not cached"
            try:
                print(f"[visual_agent] Generating '{name}' via Leonardo ({reason})...")
                img_bytes = _generate_character_leonardo(name, prompt)
                cache_path.write_bytes(img_bytes)
                print(f"[visual_agent] Cached → {cache_path}")
                result[name] = cache_path
            except (ValueError, RuntimeError, TimeoutError) as e:
                print(f"[visual_agent] Warning: skipping '{name}' character: {e}")
                result[name] = cache_path if cache_path.exists() else None

    return result


# ═════════════════════════════════════════════════════════════════════════════
# Layer 3 — PIL compositing
# ═════════════════════════════════════════════════════════════════════════════

def _load_font(size: int):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw) -> list[str]:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def composite_frames(
    bg_images: list[bytes],
    characters: dict,
    headline: str,
    assets_dir: Path,
) -> list[Path]:
    """
    Composites background + character shots + text overlays into frame-*.png.

    Layout (1080x1920):
      - Background: full frame, slightly darkened
      - Raven: bottom-left, 52% frame height
      - Jax:   bottom-right, 52% frame height
      - Headline: top bar, white text on semi-transparent black
      - Branding: bottom bar, "RAVEN & JAX"
    """
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT
    CHAR_H = int(H * 0.52)
    BOTTOM_ANCHOR = H - 60  # above branding bar

    saved = []
    for i, bg_bytes in enumerate(bg_images, 1):
        bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA").resize((W, H), Image.LANCZOS)

        # Subtle darkening for text contrast
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 65)))

        # Paste Raven (left)
        raven_path = characters.get("raven")
        if raven_path:
            raven = Image.open(raven_path).convert("RGBA")
            rw = int(CHAR_H * raven.width / raven.height)
            raven = raven.resize((rw, CHAR_H), Image.LANCZOS)
            bg.paste(raven, (0, BOTTOM_ANCHOR - CHAR_H), raven)

        # Paste Jax (right)
        jax_path = characters.get("jax")
        if jax_path:
            jax = Image.open(jax_path).convert("RGBA")
            jw = int(CHAR_H * jax.width / jax.height)
            jax = jax.resize((jw, CHAR_H), Image.LANCZOS)
            bg.paste(jax, (W - jw, BOTTOM_ANCHOR - CHAR_H), jax)

        frame = bg.convert("RGB")
        draw = ImageDraw.Draw(frame)

        # Headline bar
        font_hl = _load_font(36)
        lines = _wrap_text(headline, font_hl, W - 40, draw)
        line_h = 46
        box_h = len(lines) * line_h + 28
        draw.rectangle([(0, 55), (W, 55 + box_h)], fill=(0, 0, 0, 155))
        for j, line in enumerate(lines):
            draw.text((W // 2, 70 + j * line_h), line,
                      fill="white", font=font_hl, anchor="mt")

        # Branding bar
        draw.rectangle([(0, H - 60), (W, H)], fill=(0, 0, 0, 215))
        draw.text((W // 2, H - 30), "RAVEN & JAX",
                  fill="white", font=_load_font(28), anchor="mm")

        out = assets_dir / f"frame-0{i}.png"
        frame.save(out, "PNG")
        saved.append(out)
        print(f"[visual_agent] Saved → {out.name}")

    return saved


# ═════════════════════════════════════════════════════════════════════════════
# Layer 4 — Canva thumbnail (optional)
# ═════════════════════════════════════════════════════════════════════════════

def create_canva_thumbnail(frame_path: Path, headline: str):
    """
    Uploads episode frame to Canva as an asset.
    Returns thumbnail path on success, None if skipped or failed.
    Canva step is fully optional — never blocks the pipeline.
    """
    if not CANVA_ACCESS_TOKEN:
        return None

    try:
        headers = {"Authorization": f"Bearer {CANVA_ACCESS_TOKEN}"}
        img_bytes = frame_path.read_bytes()
        name_b64 = base64.b64encode(
            f"Raven & Jax — {headline[:50]}".encode()
        ).decode()

        # Upload asset to Canva
        upload_resp = requests.post(
            f"{CANVA_API_BASE}/asset-uploads",
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
                "Asset-Upload-Metadata": json.dumps({"name_base64": name_b64}),
            },
            data=img_bytes,
            timeout=30,
        )
        upload_resp.raise_for_status()
        job_id = upload_resp.json()["job"]["id"]

        # Poll for asset upload completion
        asset_id = None
        for _ in range(20):
            time.sleep(2)
            poll = requests.get(
                f"{CANVA_API_BASE}/asset-uploads/{job_id}",
                headers=headers, timeout=15,
            )
            poll.raise_for_status()
            job = poll.json()["job"]
            if job["status"] == "success":
                asset_id = job["asset"]["id"]
                break
            elif job["status"] == "failed":
                raise RuntimeError("Canva asset upload failed")

        if not asset_id:
            raise TimeoutError("Canva asset upload timed out")

        # Save the frame as the thumbnail (asset is now in Canva for manual editing too)
        thumbnail_path = frame_path.parent / "thumbnail.png"
        thumbnail_path.write_bytes(img_bytes)
        print(f"[visual_agent] Canva asset uploaded (id={asset_id}). Thumbnail → thumbnail.png")
        return thumbnail_path

    except Exception as e:
        print(f"[visual_agent] Canva thumbnail skipped: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═════════════════════════════════════════════════════════════════════════════

def run(run_dir: Path, regen_characters: bool = False) -> list[Path]:
    """
    Runs the full visual pipeline for today's episode.
    Reads headline from run_dir/selected-event.json.

    Returns:
        List of composited frame Paths written to run_dir/assets/
    """
    assets_dir = run_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    event_file = run_dir / "selected-event.json"
    if event_file.exists():
        headline = json.loads(event_file.read_text()).get("selected", {}).get("headline", "")
    else:
        headline = "Breaking News"
        print("[visual_agent] Warning: selected-event.json not found, using generic prompts")

    # Layer 1: Characters (Leonardo, cached globally)
    characters = ensure_characters(regen=regen_characters)

    # Layer 2: Backgrounds (Gemini Imagen, per-episode)
    bg_images = generate_backgrounds_imagen(headline)

    # Layer 3: Composite frames (PIL)
    frames = composite_frames(bg_images, characters, headline, assets_dir)

    # Layer 4: Canva thumbnail (optional)
    if frames:
        create_canva_thumbnail(frames[0], headline)

    return frames


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)
