"""
Visual Agent — generates scene images via Leonardo.ai API.
Output: runs/YYYY-MM-DD/assets/background-01.png, background-02.png, etc.
"""

import json
import time
import requests
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LEONARDO_API_KEY, MAX_RETRIES, RETRY_DELAYS

LEONARDO_BASE = "https://cloud.leonardo.ai/api/rest/v1"

# Raven & Jax couch scene prompts
SCENE_PROMPTS = [
    # Wide couch shot — both characters implied
    (
        "A modern living room at night, cozy couch with throw pillows, coffee table with "
        "beer cans and an open laptop, warm TV glow, low ambient lighting, slightly messy "
        "but lived-in, empty couch for characters. Cinematic 9:16 vertical, photorealistic, "
        "8k, shot on 35mm, no people."
    ),
    # Close-up reaction shot environment
    (
        "Close-up of a coffee table in a dim living room, beer cans, TV remote, phone screen lit, "
        "warm glow from TV off-camera. Cinematic, 9:16 vertical, photorealistic, bokeh background."
    ),
]

# Model ID for Leonardo's photorealistic model (Phoenix / Alchemy)
# Update this to the current best model in your Leonardo account
LEONARDO_MODEL_ID = "aa77f04e-3eec-4034-9c07-d0f619684628"  # Leonardo Phoenix


def generate_image(prompt: str, width: int = 1080, height: int = 1920) -> bytes:
    headers = {
        "authorization": f"Bearer {LEONARDO_API_KEY}",
        "content-type": "application/json",
    }

    # Step 1: Kick off generation
    payload = {
        "prompt": prompt,
        "modelId": LEONARDO_MODEL_ID,
        "width": width,
        "height": height,
        "num_images": 1,
        "photoReal": True,
        "alchemy": True,
        "highResolution": False,
    }

    for attempt, delay in enumerate(RETRY_DELAYS + [None], 1):
        try:
            resp = requests.post(
                f"{LEONARDO_BASE}/generations",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            gen_id = resp.json()["sdGenerationJob"]["generationId"]
            break
        except Exception as e:
            if delay is None:
                raise RuntimeError(f"Leonardo generation request failed: {e}")
            print(f"[visual_agent] Request attempt {attempt} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)

    # Step 2: Poll for completion
    print(f"[visual_agent] Waiting for generation {gen_id}...")
    for _ in range(30):
        time.sleep(4)
        poll = requests.get(
            f"{LEONARDO_BASE}/generations/{gen_id}",
            headers=headers,
            timeout=15,
        )
        poll.raise_for_status()
        data = poll.json().get("generations_by_pk", {})
        status = data.get("status")
        if status == "COMPLETE":
            image_url = data["generated_images"][0]["url"]
            img_resp = requests.get(image_url, timeout=30)
            img_resp.raise_for_status()
            return img_resp.content
        elif status == "FAILED":
            raise RuntimeError(f"Leonardo generation failed: {data}")

    raise TimeoutError(f"Leonardo generation {gen_id} timed out after 2 minutes")


def run(run_dir: Path) -> list[Path]:
    assets_dir = run_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    if not LEONARDO_API_KEY:
        raise ValueError("[visual_agent] LEONARDO_API_KEY must be set in .env")

    saved = []
    for i, prompt in enumerate(SCENE_PROMPTS, 1):
        print(f"[visual_agent] Generating background-0{i}...")
        image_bytes = generate_image(prompt)
        out_file = assets_dir / f"background-0{i}.png"
        out_file.write_bytes(image_bytes)
        saved.append(out_file)
        print(f"[visual_agent] Saved → {out_file.name}")

    return saved


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)
