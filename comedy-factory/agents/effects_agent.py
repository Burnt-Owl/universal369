"""
Effects Agent — applies cinematic gaming UI overlays to the assembled video.

Effects:
  1. Quest Marker    — "[OPTIONAL] Listen to Raven's frantic theories"
                       top-left during Raven's sections
  2. Loading Screens — game-style black transitions with ironic TIP: text
                       (inserted as clips in video_agent's clip plan)
  3. Objective Failed— red notification box during the final 5 seconds

All overlays are PIL-generated PNGs composited via FFmpeg overlay filter
(no drawtext / libfreetype required).
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

GAMER_TIPS = [
    "In the event of nuclear winter, fire-resistance\npotions are ineffective against direct hits.",
    "Relationship XP decreases when you ignore\nyour partner's apocalypse warnings.",
    "A laminated survival plan grants +15 Preparedness\nbut -20 Chill.",
    "Beans have infinite shelf life.\nYour excuses do not.",
    "Declaring 'I'm training' is a valid response\nto any crisis.  Source: Jax.",
]

_tip_index = 0


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _next_tip() -> str:
    global _tip_index
    tip = GAMER_TIPS[_tip_index % len(GAMER_TIPS)]
    _tip_index += 1
    return tip


def _ffmpeg() -> str:
    import shutil
    return shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


# ── Loading screen ─────────────────────────────────────────────────────────────

def make_loading_screen(out_path: Path, duration: float,
                        W: int = VIDEO_WIDTH, H: int = VIDEO_HEIGHT,
                        fps: int = VIDEO_FPS):
    """Generate a full-frame game loading screen as a silent video clip."""
    tip = _next_tip()
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    f_spinner = _font(FONT_BOLD, 72)
    f_loading = _font(FONT_BOLD, 44)
    f_tip_hdr = _font(FONT_BOLD, 30)
    f_tip_txt = _font(FONT_MONO, 28)

    cx = W // 2
    mid = H // 2

    # Spinner
    draw.text((cx, mid - 140), "◌", font=f_spinner, fill=(160, 160, 160), anchor="mm")
    # LOADING...
    draw.text((cx, mid - 40), "LOADING...", font=f_loading, fill=(255, 255, 255), anchor="mm")
    # Divider
    draw.line([(100, mid + 30), (W - 100, mid + 30)], fill=(45, 45, 45), width=2)
    # TIP header
    draw.text((cx, mid + 80), "▸  GAME TIP", font=f_tip_hdr, fill=(255, 215, 0), anchor="mm")
    # Tip body
    for i, line in enumerate(tip.split("\n")):
        draw.text((cx, mid + 130 + i * 42), line.strip(), font=f_tip_txt,
                  fill=(190, 190, 190), anchor="mm")

    frame_png = out_path.with_suffix(".png")
    img.save(frame_png)

    r = subprocess.run([
        _ffmpeg(), "-y",
        "-loop", "1", "-t", str(duration + 0.05), "-i", str(frame_png),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(out_path),
    ], capture_output=True, text=True)

    frame_png.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"Loading screen render failed:\n{r.stderr[-400:]}")
    return out_path


# ── Overlay PNG generators ─────────────────────────────────────────────────────

def _make_quest_marker_png(out: Path, W: int, H: int):
    """Quest marker badge — transparent RGBA PNG."""
    text  = "[OPTIONAL] Listen to Raven's frantic theories"
    f     = _font(FONT_BOLD, 30)
    pad   = 14
    bbox  = f.getbbox(text)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    iw    = tw + pad * 2
    ih    = th + pad * 2 + 32   # extra room for diamond marker above

    img  = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Yellow background box
    draw.rounded_rectangle([0, 28, iw, ih], radius=8,
                           fill=(255, 215, 0, 235), outline=(200, 160, 0, 255), width=2)
    # Diamond marker
    f_dia = _font(FONT_BOLD, 26)
    draw.text((iw // 2, 14), "◆", font=f_dia, fill=(255, 215, 0, 255), anchor="mm")
    # Text
    draw.text((pad, 28 + pad), text, font=f, fill=(0, 0, 0, 255))

    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full.paste(img, (40, 55))
    full.save(out)


def _make_obj_failed_png(out: Path, W: int, H: int):
    """Objective Failed notification — centered top, red, transparent RGBA PNG."""
    text  = "✕  OBJECTIVE FAILED:  Global Stability"
    f     = _font(FONT_BOLD, 36)
    pad   = 18
    bbox  = f.getbbox(text)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    iw    = tw + pad * 2
    ih    = th + pad * 2

    img  = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, iw, ih], radius=10,
                           fill=(180, 0, 0, 230), outline=(255, 80, 80, 255), width=3)
    draw.text((pad, pad), text, font=f, fill=(255, 255, 255, 255))

    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x    = (W - iw) // 2
    full.paste(img, (x, 70))
    full.save(out)


# ── Apply overlays via FFmpeg overlay filter ───────────────────────────────────

def apply_overlays(video_in: Path, video_out: Path,
                   raven_dur: float, total_dur: float, tmp_dir: Path):
    """Composite quest marker + objective failed PNGs onto the video."""
    ff = _ffmpeg()
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT

    quest_png = tmp_dir / "overlay_quest.png"
    obj_png   = tmp_dir / "overlay_objfail.png"

    _make_quest_marker_png(quest_png, W, H)
    _make_obj_failed_png(obj_png, W, H)

    notif_start = max(0.0, total_dur - 5.5)

    # FFmpeg complex filter:
    # [0] base video
    # [1] quest marker PNG  — overlay during t ∈ [0, raven_dur]
    # [2] obj failed PNG    — overlay during t ∈ [notif_start, total_dur]
    filter_complex = (
        f"[0:v][1:v]overlay=0:0:enable='between(t,0,{raven_dur:.2f})'[v1];"
        f"[v1][2:v]overlay=0:0:enable='between(t,{notif_start:.2f},{total_dur:.2f})'[vout]"
    )

    r = subprocess.run([
        ff, "-y",
        "-i", str(video_in),
        "-i", str(quest_png),
        "-i", str(obj_png),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(video_out),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        raise RuntimeError(f"Overlay composite failed:\n{r.stderr[-600:]}")

    mb = video_out.stat().st_size / 1_000_000
    print(f"[effects_agent] Overlays applied → {video_out.name} ({mb:.1f}MB)")
    return video_out


def run(run_dir: Path, raven_dur: float, total_dur: float) -> Path:
    date_str  = run_dir.name
    video_in  = run_dir / f"final-{date_str}.mp4"
    video_out = run_dir / f"final-{date_str}-fx.mp4"
    tmp_dir   = run_dir / "tmp_clips"
    tmp_dir.mkdir(exist_ok=True)

    print("[effects_agent] Applying gaming UI overlays...")
    apply_overlays(video_in, video_out, raven_dur, total_dur, tmp_dir)

    video_in.unlink()
    video_out.rename(video_in)
    print(f"[effects_agent] Done → {video_in.name}")
    return video_in
