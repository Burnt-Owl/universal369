"""
Stock Agent — manages Pexels stock video library for Raven & Jax.

Downloads and caches portrait-orientation reaction/talking clips.
Stored in assets/stock/{raven,jax,wide}/ — reused across episodes.

Priority of video sources in video_agent:
  1. Stock clips (this agent) — real people, most natural look
  2. D-ID avatars            — lip-synced AI characters (fallback)
  3. Static frames           — drift-zoom stills (last resort)
"""

import random
import requests
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PEXELS_API_KEY

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"
CLIPS_PER_CHARACTER  = 6
MIN_CLIP_DURATION    = 8  # seconds

# Search queries per character role
CHARACTER_QUERIES = {
    "raven": [
        "woman reacting shocked funny",
        "woman talking excited",
        "woman laughing surprised reaction",
        "woman watching TV shocked",
        "woman vlog reaction close up",
    ],
    "jax": [
        "man reacting shocked funny",
        "man talking excited",
        "man laughing surprised reaction",
        "man watching TV shocked",
        "man vlog reaction close up",
    ],
    "wide": [
        "couple watching TV couch reaction",
        "two people talking couch",
        "friends reaction shocked watching",
    ],
}


def _headers() -> dict:
    return {"Authorization": PEXELS_API_KEY}


def _search(query: str, per_page: int = 5) -> list[dict]:
    resp = requests.get(
        PEXELS_VIDEO_SEARCH,
        headers=_headers(),
        params={"query": query, "per_page": per_page, "orientation": "portrait"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("videos", [])


def _best_file(video: dict) -> dict | None:
    """Pick the best portrait-orientation video file."""
    files = sorted(video.get("video_files", []), key=lambda f: f.get("height", 0), reverse=True)
    # Prefer portrait files >= 1080p
    for f in files:
        w, h = f.get("width", 0), f.get("height", 0)
        if h > w and h >= 1080:
            return f
    # Accept any portrait
    for f in files:
        if f.get("height", 0) > f.get("width", 0):
            return f
    return files[0] if files else None


def _download(url: str, path: Path):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as fh:
        for chunk in resp.iter_content(65536):
            fh.write(chunk)


def ensure_clips(assets_dir: Path, force: bool = False) -> dict[str, list[Path]]:
    """Download Pexels clips for each role if not already cached. Returns {role: [paths]}."""
    stock_dir = assets_dir / "stock"
    result = {}

    for role, queries in CHARACTER_QUERIES.items():
        role_dir = stock_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)

        existing = sorted(role_dir.glob("*.mp4"))
        if len(existing) >= CLIPS_PER_CHARACTER and not force:
            print(f"[stock_agent] {role}: {len(existing)} clips cached, skipping download.")
            result[role] = existing
            continue

        print(f"[stock_agent] {role}: fetching clips from Pexels...")
        clips = []
        seen_ids = set(int(p.stem) for p in existing if p.stem.isdigit())

        for query in queries:
            if len(clips) + len(existing) >= CLIPS_PER_CHARACTER:
                break
            try:
                videos = _search(query, per_page=5)
            except Exception as e:
                print(f"[stock_agent] Search failed for '{query}': {e}")
                continue

            for v in videos:
                if len(clips) + len(existing) >= CLIPS_PER_CHARACTER:
                    break
                vid_id = v["id"]
                if vid_id in seen_ids:
                    continue
                if v.get("duration", 0) < MIN_CLIP_DURATION:
                    continue
                file_info = _best_file(v)
                if not file_info:
                    continue
                out = role_dir / f"{vid_id}.mp4"
                if not out.exists():
                    print(f"[stock_agent] {role}: downloading {vid_id} ({v['duration']}s)...")
                    try:
                        _download(file_info["link"], out)
                    except Exception as e:
                        print(f"[stock_agent] Download failed: {e}")
                        continue
                clips.append(out)
                seen_ids.add(vid_id)

        all_clips = existing + clips
        result[role] = all_clips
        print(f"[stock_agent] {role}: {len(all_clips)} clips ready.")

    return result


def random_clip(role: str, assets_dir: Path) -> Path:
    """Return a random cached clip for this role (raven/jax/wide)."""
    role_dir = assets_dir / "stock" / role.lower()
    clips = sorted(role_dir.glob("*.mp4"))
    if not clips:
        raise FileNotFoundError(
            f"[stock_agent] No clips for role '{role}'. Run stock_agent.run() first."
        )
    return random.choice(clips)


def has_clips(assets_dir: Path) -> bool:
    """True if all three roles have at least one clip cached."""
    for role in ("raven", "jax", "wide"):
        if not list((assets_dir / "stock" / role).glob("*.mp4")):
            return False
    return True


def run(assets_dir: Path = None, force: bool = False) -> dict[str, list[Path]]:
    if assets_dir is None:
        assets_dir = Path(__file__).parent.parent / "assets"
    if not PEXELS_API_KEY:
        raise ValueError("[stock_agent] PEXELS_API_KEY not set in ~/.comedy-factory/.env")
    return ensure_clips(assets_dir, force=force)


if __name__ == "__main__":
    run()
