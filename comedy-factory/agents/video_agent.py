"""
Video Agent — assembles final MP4 from audio, frames, and captions.
Output: runs/YYYY-MM-DD/final-YYYY-MM-DD.mp4

Pipeline:
  1. Cross-fade between frame-01 (Raven scene) and frame-02 (Jax scene)
  2. Sequence Raven audio then Jax audio
  3. Burn ASS captions (1080x1920 coords, 32px font, speaker-colored)
"""

import re
import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


def _ffmpeg() -> str:
    import shutil
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

FF = _ffmpeg()


def get_audio_duration(p: Path) -> float:
    from mutagen.mp3 import MP3
    return MP3(str(p)).info.length


def parse_script_lines(script_md: str) -> list[tuple[str, str]]:
    lines = []
    for raw in script_md.split("\n"):
        raw = raw.strip()
        if raw.startswith("RAVEN:"):
            spk, text = "Raven", raw[6:].strip()
        elif raw.startswith("JAX:"):
            spk, text = "Jax", raw[4:].strip()
        else:
            continue
        text = re.sub(r'\*[^*]+\*', '', text).strip()
        text = re.sub(r'\[[^\]]+\]', '', text).strip()
        if text:
            lines.append((spk, text))
    return lines


def write_ass(lines: list[tuple[str, str]], raven_dur: float, jax_dur: float, path: Path):
    """Write an ASS subtitle file at 1080x1920 so FontSize=32 = 32 physical pixels."""
    raven_lines = [(s, t) for s, t in lines if s == "Raven"]
    jax_lines   = [(s, t) for s, t in lines if s == "Jax"]

    entries = []

    def spread(spk_lines, t_start, total):
        if not spk_lines:
            return
        lengths = [max(len(t), 1) for _, t in spk_lines]
        total_c = sum(lengths)
        t = t_start
        for (spk, text), c in zip(spk_lines, lengths):
            dur = max((c / total_c) * (total - 0.3), 1.0)
            # wrap to ≤42 chars
            import textwrap
            wrapped = "\\N".join(textwrap.wrap(text, 42))
            entries.append((t, t + dur - 0.1, spk, wrapped))
            t += dur

    spread(raven_lines, 0.3, raven_dur - 0.3)
    spread(jax_lines, raven_dur + 0.3, jax_dur - 0.3)

    def ts(s):
        h = int(s // 3600); m = int((s % 3600) // 60); s2 = s % 60
        return f"{h}:{m:02}:{s2:05.2f}"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 1\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,"
        "BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginV\n"
        # Colours in ASS are &HAABBGGRR (alpha, blue, green, red)
        "Style: Raven,Arial,32,&H0041D7FF,&H00000000,&H80000000,-1,0,1,2,1,2,60\n"
        "Style: Jax,Arial,32,&H00FFB964,&H00000000,&H80000000,-1,0,1,2,1,2,60\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    dialogues = ""
    for t_in, t_out, spk, text in entries:
        dialogues += f"Dialogue: 0,{ts(t_in)},{ts(t_out)},{spk},,0,0,0,,{text}\n"

    path.write_text(header + dialogues, encoding="utf-8")


def run(run_dir: Path) -> Path:
    script_md  = (run_dir / "script.md").read_text()
    date_str   = run_dir.name
    raven_mp3  = run_dir / "raven-voice.mp3"
    jax_mp3    = run_dir / "jax-voice.mp3"
    assets_dir = run_dir / "assets"
    frames     = sorted(assets_dir.glob("frame-*.png")) if assets_dir.exists() else []
    tmp        = run_dir / "tmp-video.mp4"
    out        = run_dir / f"final-{date_str}.mp4"

    rd = get_audio_duration(raven_mp3)
    jd = get_audio_duration(jax_mp3)
    total = rd + jd + 0.5

    print(f"[video_agent] Raven: {rd:.1f}s  Jax: {jd:.1f}s  Total: {total:.1f}s")

    # Captions
    ass_file = run_dir / "captions.ass"
    write_ass(parse_script_lines(script_md), rd, jd, ass_file)

    W, H, FPS = VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS
    XFADE = 0.8

    # --- Build base video (fast — no zoompan) ---
    if len(frames) >= 2:
        fc = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,fps={FPS}[v1];"
            f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,fps={FPS}[v2];"
            f"[v1][v2]xfade=transition=fade:duration={XFADE}:offset={rd - XFADE/2}[vout];"
            f"[2:a]adelay=0[a0];"
            f"[3:a]adelay={int(rd*1000)}[a1];"
            "[a0][a1]amix=inputs=2:duration=longest[audio]"
        )
        inputs = [
            "-loop","1","-t",str(rd+XFADE),"-i",str(frames[0]),
            "-loop","1","-t",str(jd+XFADE),"-i",str(frames[1]),
            "-i",str(raven_mp3),"-i",str(jax_mp3),
        ]
    elif len(frames) == 1:
        fc = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,fps={FPS}[vout];"
            f"[1:a]adelay=0[a0];"
            f"[2:a]adelay={int(rd*1000)}[a1];"
            "[a0][a1]amix=inputs=2:duration=longest[audio]"
        )
        inputs = [
            "-loop","1","-t",str(total),"-i",str(frames[0]),
            "-i",str(raven_mp3),"-i",str(jax_mp3),
        ]
    else:
        fc = (
            f"color=black:{W}x{H}:r={FPS}[vout];"
            f"[0:a]adelay=0[a0];[1:a]adelay={int(rd*1000)}[a1];"
            "[a0][a1]amix=inputs=2:duration=longest[audio]"
        )
        inputs = ["-i",str(raven_mp3),"-i",str(jax_mp3)]

    r1 = subprocess.run([
        FF,"-y",*inputs,
        "-filter_complex",fc,
        "-map","[vout]","-map","[audio]",
        "-t",str(total),
        "-c:v","libx264","-preset","fast",
        "-c:a","aac","-pix_fmt","yuv420p","-movflags","+faststart",
        str(tmp),
    ], capture_output=True, text=True)

    if r1.returncode != 0:
        raise RuntimeError(f"[video_agent] base render failed:\n{r1.stderr[-1000:]}")

    # --- Burn captions ---
    print("[video_agent] Burning captions...")
    r2 = subprocess.run([
        FF,"-y","-i",str(tmp),
        "-vf",f"ass='{ass_file}'",
        "-c:v","libx264","-preset","fast",
        "-c:a","copy","-pix_fmt","yuv420p",
        str(out),
    ], capture_output=True, text=True)

    tmp.unlink(missing_ok=True)

    if r2.returncode != 0:
        raise RuntimeError(f"[video_agent] caption burn failed:\n{r2.stderr[-500:]}")

    mb = out.stat().st_size / 1_000_000
    print(f"[video_agent] Done → {out.name}  ({mb:.1f}MB)")
    return out


if __name__ == "__main__":
    from datetime import date
    run(Path(__file__).parent.parent / "runs" / date.today().isoformat())
