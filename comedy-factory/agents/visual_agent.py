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


def generate_backgrounds_leonardo(headline: str) -> list[bytes]:
    """Generates 2 background images via Leonardo.ai (fallback when Gemini unavailable)."""
    if not LEONARDO_API_KEY:
        raise ValueError("[visual_agent] Neither GEMINI_API_KEY nor LEONARDO_API_KEY is set.")

    results = []
    for i, prompt in enumerate(_build_scene_prompts(headline), 1):
        print(f"[visual_agent] Generating background-0{i} via Leonardo...")
        results.append(_generate_character_leonardo(f"background-0{i}", prompt))
    return results


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
        "width": 1024,
        "height": 1536,
        "num_images": 1,
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


def _tint(img: Image.Image, color: tuple, strength: float = 0.18) -> Image.Image:
    """Overlay a color tint on an RGBA image."""
    overlay = Image.new("RGBA", img.size, color + (int(255 * strength),))
    return Image.alpha_composite(img, overlay)


def _build_base(bg_bytes: bytes, W: int, H: int, darkness: int = 70) -> Image.Image:
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA").resize((W, H), Image.LANCZOS)
    return Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, darkness)))


def _add_headline(frame: Image.Image, headline: str, W: int) -> Image.Image:
    draw = ImageDraw.Draw(frame)
    font = _load_font(38)
    lines = _wrap_text(headline, font, W - 60, draw)
    line_h = 50
    box_h = len(lines) * line_h + 32
    draw.rectangle([(0, 0), (W, box_h + 10)], fill=(0, 0, 0, 180))
    for j, line in enumerate(lines):
        draw.text((W // 2, 20 + j * line_h), line, fill="white", font=font, anchor="mt")
    return frame


def _add_branding(frame: Image.Image, W: int, H: int) -> Image.Image:
    draw = ImageDraw.Draw(frame)
    draw.rectangle([(0, H - 56), (W, H)], fill=(0, 0, 0, 220))
    draw.text((W // 2, H - 28), "RAVEN & JAX", fill="white", font=_load_font(26), anchor="mm")
    return frame


def composite_frames(
    bg_images: list[bytes],
    characters: dict,
    headline: str,
    assets_dir: Path,
) -> list[Path]:
    """
    Creates 3 distinct frame types for dynamic cutting:
      frame-wide.png   — both characters equal, establishing shot
      frame-raven.png  — Raven dominant (left, large), cool blue tint
      frame-jax.png    — Jax dominant (right, large), warm amber tint
    """
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT
    saved = []

    raven_img = Image.open(characters["raven"]).convert("RGBA") if characters.get("raven") else None
    jax_img   = Image.open(characters["jax"]).convert("RGBA")   if characters.get("jax")   else None

    bg0 = bg_images[0]
    bg1 = bg_images[1] if len(bg_images) > 1 else bg_images[0]

    # ── Frame 1: Wide shot — both characters equal ──────────────────────────
    base = _build_base(bg0, W, H, darkness=60)
    CHAR_H_WIDE = int(H * 0.54)
    BOTTOM = H - 56
    if raven_img:
        rw = int(CHAR_H_WIDE * raven_img.width / raven_img.height)
        r = raven_img.resize((rw, CHAR_H_WIDE), Image.LANCZOS)
        base.paste(r, (0, BOTTOM - CHAR_H_WIDE), r)
    if jax_img:
        jw = int(CHAR_H_WIDE * jax_img.width / jax_img.height)
        j = jax_img.resize((jw, CHAR_H_WIDE), Image.LANCZOS)
        base.paste(j, (W - jw, BOTTOM - CHAR_H_WIDE), j)
    frame = base.convert("RGB")
    _add_headline(frame, headline, W)
    _add_branding(frame, W, H)
    out = assets_dir / "frame-wide.png"
    frame.save(out, "PNG")
    saved.append(out)
    print("[visual_agent] Saved → frame-wide.png")

    # ── Frame 2: Raven focus — Raven large, cool tint ──────────────────────
    base = _build_base(bg0, W, H, darkness=80)
    base = _tint(base, (30, 60, 120), 0.20)   # cool blue
    CHAR_H_BIG  = int(H * 0.70)
    CHAR_H_SMALL = int(H * 0.38)
    if raven_img:
        rw = int(CHAR_H_BIG * raven_img.width / raven_img.height)
        r = raven_img.resize((rw, CHAR_H_BIG), Image.LANCZOS)
        # Center Raven horizontally
        x = (W - rw) // 2 - 60
        base.paste(r, (max(0, x), BOTTOM - CHAR_H_BIG), r)
    if jax_img:
        jw = int(CHAR_H_SMALL * jax_img.width / jax_img.height)
        j = jax_img.resize((jw, CHAR_H_SMALL), Image.LANCZOS)
        # Jax small in corner, slightly faded
        fade = Image.new("RGBA", j.size, (0, 0, 0, 100))
        jf = Image.alpha_composite(j, fade)
        base.paste(jf, (W - jw - 10, BOTTOM - CHAR_H_SMALL), jf)
    frame = base.convert("RGB")
    _add_headline(frame, headline, W)
    _add_branding(frame, W, H)
    out = assets_dir / "frame-raven.png"
    frame.save(out, "PNG")
    saved.append(out)
    print("[visual_agent] Saved → frame-raven.png")

    # ── Frame 3: Jax focus — Jax large, warm amber tint ────────────────────
    base = _build_base(bg1, W, H, darkness=80)
    base = _tint(base, (120, 60, 0), 0.20)    # warm amber
    if jax_img:
        jw = int(CHAR_H_BIG * jax_img.width / jax_img.height)
        j = jax_img.resize((jw, CHAR_H_BIG), Image.LANCZOS)
        x = (W - jw) // 2 + 60
        base.paste(j, (min(W - jw, x), BOTTOM - CHAR_H_BIG), j)
    if raven_img:
        rw = int(CHAR_H_SMALL * raven_img.width / raven_img.height)
        r = raven_img.resize((rw, CHAR_H_SMALL), Image.LANCZOS)
        fade = Image.new("RGBA", r.size, (0, 0, 0, 100))
        rf = Image.alpha_composite(r, fade)
        base.paste(rf, (10, BOTTOM - CHAR_H_SMALL), rf)
    frame = base.convert("RGB")
    _add_headline(frame, headline, W)
    _add_branding(frame, W, H)
    out = assets_dir / "frame-jax.png"
    frame.save(out, "PNG")
    saved.append(out)
    print("[visual_agent] Saved → frame-jax.png")

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

    # Layer 2: Backgrounds — Gemini if available, Leonardo as fallback
    if GEMINI_API_KEY:
        bg_images = generate_backgrounds_imagen(headline)
    elif LEONARDO_API_KEY:
        print("[visual_agent] GEMINI_API_KEY not set — using Leonardo for backgrounds.")
        bg_images = generate_backgrounds_leonardo(headline)
    else:
        raise ValueError(
            "[visual_agent] Set GEMINI_API_KEY (free) or LEONARDO_API_KEY to generate backgrounds."
        )

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
