"""
Video Agent — assembles final MP4 from audio, images, and captions using ffmpeg.
Output: runs/YYYY-MM-DD/final-YYYY-MM-DD.mp4

Features:
- Ken Burns slow zoom on each scene frame
- Cross-fade transition between Scene 1 (Raven) and Scene 2 (Jax)
- Captions burned in from script, timed to audio durations
- Audio: Raven then Jax in sequence
"""

import re
import json
import subprocess
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


def _find_ffmpeg() -> str:
    import shutil
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("ffmpeg not found. Run: pip install imageio-ffmpeg")

FFMPEG = _find_ffmpeg()


def get_audio_duration(audio_file: Path) -> float:
    from mutagen.mp3 import MP3
    return MP3(str(audio_file)).info.length


def parse_script_lines(script_md: str) -> list[tuple[str, str]]:
    """Return [(speaker, line), ...] stripping stage directions."""
    lines = []
    for raw in script_md.split("\n"):
        raw = raw.strip()
        if raw.startswith("RAVEN:"):
            text = raw[6:].strip()
            spk = "Raven"
        elif raw.startswith("JAX:"):
            text = raw[4:].strip()
            spk = "Jax"
        else:
            continue
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        text = re.sub(r'\[[^\]]+\]', '', text).strip()
        if text:
            lines.append((spk, text))
    return lines


def _split_caption(text: str, max_chars: int = 42) -> list[str]:
    """Split long lines into ≤max_chars chunks at word/sentence boundaries."""
    import textwrap
    return textwrap.wrap(text, width=max_chars, break_long_words=False)


def write_srt(lines: list[tuple[str, str]], raven_dur: float, jax_dur: float, path: Path):
    """
    Write a .srt subtitle file, one entry per dialogue line, split to ≤2 display lines.
    Raven lines fill raven_dur seconds, Jax lines fill jax_dur seconds.
    """
    raven_lines = [(s, t) for s, t in lines if s == "Raven"]
    jax_lines   = [(s, t) for s, t in lines if s == "Jax"]

    entries = []

    def spread(speaker_lines, start_time, total_dur):
        n = len(speaker_lines)
        if not n:
            return
        # Weight time by character count so longer lines get more screen time
        lengths = [max(len(t), 1) for _, t in speaker_lines]
        total_chars = sum(lengths)
        t = start_time
        for (spk, text), chars in zip(speaker_lines, lengths):
            dur = (chars / total_chars) * (total_dur - 0.3)
            display = "\n".join(_split_caption(text))
            entries.append((t, t + dur - 0.1, spk, display))
            t += dur

    spread(raven_lines, 0.3, raven_dur - 0.3)
    spread(jax_lines,   raven_dur + 0.3, jax_dur - 0.3)

    def fmt(secs):
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        ms = int((secs % 1) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    srt = ""
    for idx, (t_in, t_out, spk, text) in enumerate(entries, 1):
        color = "#FFD741" if spk == "Raven" else "#64B9FF"
        label = f"<font color='{color}'><b>{spk}</b></font>"
        srt += f"{idx}\n{fmt(t_in)} --> {fmt(t_out)}\n{label}\n{text}\n\n"

    path.write_text(srt, encoding="utf-8")


def run(run_dir: Path) -> Path:
    script_md   = (run_dir / "script.md").read_text()
    event_data  = json.loads((run_dir / "selected-event.json").read_text())
    date_str    = run_dir.name

    raven_audio = run_dir / "raven-voice.mp3"
    jax_audio   = run_dir / "jax-voice.mp3"
    assets_dir  = run_dir / "assets"
    frames      = sorted(assets_dir.glob("frame-*.png")) if assets_dir.exists() else []
    out_file    = run_dir / f"final-{date_str}.mp4"

    raven_dur = get_audio_duration(raven_audio)
    jax_dur   = get_audio_duration(jax_audio)
    total_dur = raven_dur + jax_dur + 0.5

    print(f"[video_agent] Raven: {raven_dur:.1f}s  Jax: {jax_dur:.1f}s  Total: {total_dur:.1f}s")

    # Write subtitles
    script_lines = parse_script_lines(script_md)
    srt_file = run_dir / "captions.srt"
    write_srt(script_lines, raven_dur, jax_dur, srt_file)

    W, H, FPS = VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS
    XFADE_DUR = 0.8   # cross-fade duration in seconds
    XFADE_AT  = raven_dur - XFADE_DUR / 2

    if len(frames) >= 2:
        # Two frames: Ken Burns on each + cross-fade transition
        f1_frames = int(raven_dur * FPS) + int(XFADE_DUR * FPS)
        f2_frames = int(jax_dur   * FPS) + int(XFADE_DUR * FPS)

        # Ken Burns: slow zoom-in on scene 1, slow zoom-out on scene 2
        kb1 = (
            f"[0:v]scale=8000:-1,zoompan=z='min(zoom+0.0006,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={f1_frames}:s={W}x{H}:fps={FPS},setsar=1[v1]"
        )
        kb2 = (
            f"[1:v]scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.08,max(zoom-0.0006,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={f2_frames}:s={W}x{H}:fps={FPS},setsar=1[v2]"
        )
        xfade = f"[v1][v2]xfade=transition=fade:duration={XFADE_DUR}:offset={XFADE_AT}[vout]"

        video_filter = f"{kb1};{kb2};{xfade}"
        video_inputs = ["-i", str(frames[0]), "-i", str(frames[1])]
        video_map    = "[vout]"
        audio_idx    = 2

    elif len(frames) == 1:
        # Single frame with Ken Burns
        total_frames = int(total_dur * FPS)
        kb = (
            f"[0:v]scale=8000:-1,zoompan=z='min(zoom+0.0004,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={W}x{H}:fps={FPS},setsar=1[vout]"
        )
        video_filter = kb
        video_inputs = ["-i", str(frames[0])]
        video_map    = "[vout]"
        audio_idx    = 1

    else:
        # No frames — black background
        video_filter = f"color=black:{W}x{H}:r={FPS}[vout]"
        video_inputs = []
        video_map    = "[vout]"
        audio_idx    = 0

    # Audio: sequence Raven then Jax
    audio_filter = (
        f"[{audio_idx}:a]adelay=0[a0];"
        f"[{audio_idx+1}:a]adelay={int(raven_dur*1000)}[a1];"
        "[a0][a1]amix=inputs=2:duration=longest[audio]"
    )

    filter_complex = video_filter + ";" + audio_filter

    cmd = [
        FFMPEG, "-y",
        *video_inputs,
        "-i", str(raven_audio),
        "-i", str(jax_audio),
        "-filter_complex", filter_complex,
        "-map", video_map,
        "-map", "[audio]",
        "-t", str(total_dur),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_file),
    ]

    print("[video_agent] Assembling video with Ken Burns + cross-fade...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")

    # Burn captions into video
    captioned = run_dir / f"final-{date_str}-captioned.mp4"
    cap_cmd = [
        FFMPEG, "-y",
        "-i", str(out_file),
        "-vf", (
            f"subtitles='{srt_file}':force_style='"
            "FontName=DejaVu Sans Bold,FontSize=13,"
            "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
            "Outline=2,Shadow=1,Alignment=2,MarginV=40'"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(captioned),
    ]
    cap_result = subprocess.run(cap_cmd, capture_output=True, text=True)
    if cap_result.returncode == 0:
        out_file.unlink()          # remove un-captioned version
        captioned.rename(out_file) # promote captioned to final
        print(f"[video_agent] Captions burned in ✓")
    else:
        print(f"[video_agent] Caption burn failed (keeping uncaptioned): {cap_result.stderr[-200:]}")

    size_mb = out_file.stat().st_size / 1_000_000
    print(f"[video_agent] Video saved → {out_file.name}  ({size_mb:.1f}MB)")
    return out_file


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)
