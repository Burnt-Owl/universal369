"""
Video Agent — assembles final MP4 from audio, frames, and captions.
Output: runs/YYYY-MM-DD/final-YYYY-MM-DD.mp4

Pipeline:
  1. Parse script → map dialogue lines to frame types (raven/jax/wide)
  2. Split audio proportionally across lines → timed clip list
  3. Per clip: subtle drift zoom (crop shift) for motion feel
  4. Concatenate clips + audio
  5. Burn bold ASS captions (TikTok style: large, centered, speaker-colored)
"""

import re
import json
import subprocess
import textwrap
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


def _assign_timings(lines: list[tuple[str, str]], raven_dur: float, jax_dur: float):
    """
    Returns list of (speaker, text, t_start, t_end) with proportional timing.
    Raven lines span [0, raven_dur], Jax lines span [raven_dur, total].
    """
    raven_lines = [(s, t) for s, t in lines if s == "Raven"]
    jax_lines   = [(s, t) for s, t in lines if s == "Jax"]

    result = []

    def spread(spk_lines, t_offset, total_dur):
        if not spk_lines:
            return
        lengths = [max(len(t), 1) for _, t in spk_lines]
        total_c = sum(lengths)
        t = t_offset + 0.3
        for (spk, text), c in zip(spk_lines, lengths):
            dur = max((c / total_c) * (total_dur - 0.4), 1.2)
            result.append((spk, text, t, t + dur - 0.1))
            t += dur

    spread(raven_lines, 0.0, raven_dur)
    spread(jax_lines, raven_dur, jax_dur)
    return result


def write_ass(timed: list[tuple], path: Path):
    """TikTok-style captions: large bold centered text, speaker-colored name label."""
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT

    def ts(s):
        h = int(s // 3600); m = int((s % 3600) // 60); s2 = s % 60
        return f"{h}:{m:02}:{s2:05.2f}"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\n"
        f"PlayResY: {H}\n"
        "WrapStyle: 1\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,"
        "BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginV\n"
        # Large bold centered captions — Raven gold, Jax blue
        "Style: Raven,Arial,52,&H0041D7FF,&H00000000,&HAA000000,-1,0,1,3,1,2,220\n"
        "Style: Jax,Arial,52,&H0064B9FF,&H00000000,&HAA000000,-1,0,1,3,1,2,220\n"
        "Style: Label,Arial,38,&H00FFFFFF,&H00000000,&H00000000,-1,0,1,2,0,2,290\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )

    dialogues = ""
    for spk, text, t_in, t_out in timed:
        wrapped = "\\N".join(textwrap.wrap(text, 32))
        dialogues += f"Dialogue: 0,{ts(t_in)},{ts(t_out)},{spk},,0,0,0,,{wrapped}\n"
        # Speaker name label above caption
        name_color = "{\\c&H0041D7FF&}" if spk == "Raven" else "{\\c&H0064B9FF&}"
        dialogues += f"Dialogue: 1,{ts(t_in)},{ts(t_out)},Label,,0,0,0,,{name_color}{spk.upper()}\n"

    path.write_text(header + dialogues, encoding="utf-8")


def _make_clip(frame: Path, duration: float, clip_path: Path, W: int, H: int, fps: int,
               zoom_in: bool = True):
    """
    Renders a single video clip from a still image with subtle drift zoom.
    Uses crop-shift trick (fast): scale image 10% larger, drift the crop window.
    """
    # Scale 10% larger for drift room
    SW = int(W * 1.10)
    SH = int(H * 1.10)
    dx = SW - W  # total horizontal drift budget
    dy = SH - H

    if zoom_in:
        # Start wide (crop from center), drift inward (zoom in feel)
        x_expr = f"{dx//2}-({dx//2})*t/{duration:.2f}"
        y_expr = f"{dy//2}-({dy//2})*t/{duration:.2f}"
    else:
        # Start tight, drift outward (zoom out feel)
        x_expr = f"({dx//2})*t/{duration:.2f}"
        y_expr = f"({dy//2})*t/{duration:.2f}"

    vf = (
        f"scale={SW}:{SH}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H}:x='{x_expr}':y='{y_expr}',"
        f"setsar=1,fps={fps}"
    )

    r = subprocess.run([
        FF, "-y",
        "-loop", "1", "-t", str(duration + 0.1), "-i", str(frame),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an",
        str(clip_path),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        raise RuntimeError(f"Clip render failed for {frame.name}:\n{r.stderr[-600:]}")


def run(run_dir: Path) -> Path:
    script_md  = (run_dir / "script.md").read_text()
    date_str   = run_dir.name
    raven_mp3  = run_dir / "raven-voice.mp3"
    jax_mp3    = run_dir / "jax-voice.mp3"
    assets_dir = run_dir / "assets"
    tmp_dir    = run_dir / "tmp_clips"
    tmp_dir.mkdir(exist_ok=True)
    out        = run_dir / f"final-{date_str}.mp4"

    rd = get_audio_duration(raven_mp3)
    jd = get_audio_duration(jax_mp3)
    total = rd + jd + 0.5

    print(f"[video_agent] Raven: {rd:.1f}s  Jax: {jd:.1f}s  Total: {total:.1f}s")

    # Load frames
    frame_wide  = assets_dir / "frame-wide.png"
    frame_raven = assets_dir / "frame-raven.png"
    frame_jax   = assets_dir / "frame-jax.png"

    # Fall back to old naming if new frames don't exist yet
    if not frame_raven.exists():
        old = sorted(assets_dir.glob("frame-*.png"))
        frame_raven = old[0] if old else frame_wide
        frame_jax   = old[1] if len(old) > 1 else frame_wide
        frame_wide  = old[0] if old else frame_wide

    W, H, FPS = VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

    # Parse script → timed lines
    lines = parse_script_lines(script_md)
    timed = _assign_timings(lines, rd, jd)

    # Write captions
    ass_file = run_dir / "captions.ass"
    write_ass(timed, ass_file)

    # Build clip list: cut on every speaker change AND every ~8s within same speaker
    # Pattern: wide → raven_focus → wide → raven_focus → ... → jax_focus → wide → jax_focus
    CUT_INTERVAL = 8.0  # max seconds before inserting a variety cut
    clips_plan = []  # (frame_path, t_start, t_end, zoom_in)

    zoom_toggle = True
    current_seg_start = 0.0
    current_frame = frame_wide
    last_cut_t = 0.0

    for i, (spk, text, t_in, t_out) in enumerate(timed):
        focus = frame_raven if spk == "Raven" else frame_jax
        prev_spk = timed[i-1][0] if i > 0 else None

        speaker_changed = (prev_spk is not None and spk != prev_spk)
        time_since_cut = t_in - last_cut_t

        if speaker_changed or time_since_cut >= CUT_INTERVAL:
            # Close current segment
            if t_in > current_seg_start:
                clips_plan.append((current_frame, current_seg_start, t_in, zoom_toggle))
                zoom_toggle = not zoom_toggle
                last_cut_t = t_in

            # Decide next frame: alternate focus/wide for variety
            if speaker_changed:
                # Brief wide reaction cut (1.5s) then focus
                wide_end = min(t_in + 1.5, t_out)
                clips_plan.append((frame_wide, t_in, wide_end, zoom_toggle))
                zoom_toggle = not zoom_toggle
                current_frame = focus
                current_seg_start = wide_end
            else:
                # Within same speaker: toggle between focus and wide
                is_focus = (current_frame != frame_wide)
                current_frame = frame_wide if is_focus else focus
                current_seg_start = t_in

    # Close final segment
    if timed:
        last_t_out = timed[-1][3] + 0.3
        clips_plan.append((current_frame, current_seg_start, last_t_out, zoom_toggle))

    # Render each clip
    clip_files = []
    for idx, (frame_path, t_start, t_end, zi) in enumerate(clips_plan):
        dur = max(t_end - t_start, 0.5)
        clip_path = tmp_dir / f"clip_{idx:02d}.mp4"
        print(f"[video_agent] Clip {idx+1}/{len(clips_plan)}: {frame_path.name} ({dur:.1f}s)...")
        _make_clip(frame_path, dur, clip_path, W, H, FPS, zoom_in=zi)
        clip_files.append(clip_path)

    # Write concat list
    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_files))

    # Concat clips → silent video
    silent_video = run_dir / "tmp-silent.mp4"
    r = subprocess.run([
        FF, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-t", str(total),
        str(silent_video),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{r.stderr[-600:]}")

    # Mix audio: Raven first then Jax
    tmp_video_audio = run_dir / "tmp-video-audio.mp4"
    r = subprocess.run([
        FF, "-y",
        "-i", str(silent_video),
        "-i", str(raven_mp3),
        "-i", str(jax_mp3),
        "-filter_complex",
        f"[1:a]adelay=0[a0];[2:a]adelay={int(rd*1000)}[a1];[a0][a1]amix=inputs=2:duration=longest[audio]",
        "-map", "0:v", "-map", "[audio]",
        "-c:v", "copy", "-c:a", "aac",
        "-t", str(total),
        str(tmp_video_audio),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Audio mix failed:\n{r.stderr[-600:]}")

    # Burn captions
    print("[video_agent] Burning captions...")
    r = subprocess.run([
        FF, "-y", "-i", str(tmp_video_audio),
        "-vf", f"ass='{ass_file}'",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        str(out),
    ], capture_output=True, text=True)

    # Cleanup temp files
    silent_video.unlink(missing_ok=True)
    tmp_video_audio.unlink(missing_ok=True)

    if r.returncode != 0:
        raise RuntimeError(f"Caption burn failed:\n{r.stderr[-500:]}")

    mb = out.stat().st_size / 1_000_000
    print(f"[video_agent] Done → {out.name}  ({mb:.1f}MB)")
    return out


if __name__ == "__main__":
    from datetime import date
    run(Path(__file__).parent.parent / "runs" / date.today().isoformat())
