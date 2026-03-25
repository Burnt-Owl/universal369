"""
Video Agent — assembles final MP4 from audio, images, and captions using ffmpeg.
Output: runs/YYYY-MM-DD/final-YYYY-MM-DD.mp4
"""

import re
import json
import subprocess
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


def parse_script_lines(script_md: str) -> list[tuple[str, str]]:
    lines = []
    match = re.search(r"---\n\n(.*?)\n\n---", script_md, re.DOTALL)
    dialogue = match.group(1) if match else script_md
    for raw in dialogue.split("\n"):
        raw = raw.strip()
        if raw.startswith("RAVEN:"):
            lines.append(("RAVEN", raw[6:].strip()))
        elif raw.startswith("JAX:"):
            lines.append(("JAX", raw[4:].strip()))
    return lines


def get_audio_duration(audio_file: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def run(run_dir: Path) -> Path:
    script_md = (run_dir / "script.md").read_text()
    event_data = json.loads((run_dir / "selected-event.json").read_text())
    headline = event_data["selected"]["headline"]
    date_str = run_dir.name

    raven_audio = run_dir / "raven-voice.mp3"
    jax_audio = run_dir / "jax-voice.mp3"
    assets_dir = run_dir / "assets"
    if assets_dir.exists():
        # Prefer composited frames (background + characters + text) over raw backgrounds
        frames = sorted(assets_dir.glob("frame-*.png"))
        backgrounds = frames if frames else sorted(assets_dir.glob("background-*.png"))
    else:
        backgrounds = []

    out_file = run_dir / f"final-{date_str}.mp4"

    raven_dur = get_audio_duration(raven_audio)
    jax_dur = get_audio_duration(jax_audio)
    total_dur = raven_dur + jax_dur + 1.0  # 1s buffer

    print(f"[video_agent] Raven: {raven_dur:.1f}s, Jax: {jax_dur:.1f}s, Total: {total_dur:.1f}s")

    # Build background: use first background image if available, else black
    if backgrounds:
        bg_input = ["-loop", "1", "-i", str(backgrounds[0])]
        bg_filter = (
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={VIDEO_FPS}[bg];"
        )
        input_count = 1
    else:
        bg_input = []
        bg_filter = (
            f"color=black:{VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={VIDEO_FPS}[bg];"
        )
        input_count = 0

    # Title card text (top of video)
    title_safe = headline.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")[:60]
    title_filter = (
        f"[bg]drawtext=text='{title_safe}':fontcolor=white:fontsize=36:"
        f"x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.5:boxborderw=10[titled];"
        f"[titled]drawtext=text='Raven \\& Jax':fontcolor=white:fontsize=28:"
        f"x=(w-text_w)/2:y=h-120:box=1:boxcolor=black@0.5:boxborderw=8[out]"
    )

    # Merge audio: raven then jax in sequence
    audio_filter = (
        f"[{input_count}:a]adelay=0[a0];"
        f"[{input_count + 1}:a]adelay={int(raven_dur * 1000)}[a1];"
        "[a0][a1]amix=inputs=2:duration=longest[audio]"
    )

    filter_complex = bg_filter + title_filter + ";" + audio_filter

    cmd = [
        "ffmpeg", "-y",
        *bg_input,
        "-i", str(raven_audio),
        "-i", str(jax_audio),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "[audio]",
        "-t", str(total_dur),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_file),
    ]

    print(f"[video_agent] Assembling video...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")

    print(f"[video_agent] Video saved → {out_file}")
    return out_file


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)
