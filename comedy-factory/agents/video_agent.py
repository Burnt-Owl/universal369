"""
Video Agent — assembles final MP4 from audio, stock footage, and captions.
Output: runs/YYYY-MM-DD/final-YYYY-MM-DD.mp4

Video source priority (highest to lowest):
  1. Pexels stock clips  — real people reacting/talking (best look)
  2. D-ID avatar videos  — lip-synced AI characters
  3. Static frames       — drift-zoom stills (fallback)

Pipeline:
  1. Parse script → timed dialogue lines
  2. Build clip plan (speaker cuts every ~8s)
  3. Render each clip from best available source
  4. Concat clips → mix Raven + Jax audio → burn ASS captions
"""

import re
import random
import subprocess
import textwrap
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

LOADING_SCREEN_DURATION = 1.8  # seconds per loading screen transition


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


def _video_duration(p: Path) -> float:
    r = subprocess.run([
        FF, "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(p)
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


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
        name_color = "{\\c&H0041D7FF&}" if spk == "Raven" else "{\\c&H0064B9FF&}"
        dialogues += f"Dialogue: 1,{ts(t_in)},{ts(t_out)},Label,,0,0,0,,{name_color}{spk.upper()}\n"

    path.write_text(header + dialogues, encoding="utf-8")


# ── Clip renderers ─────────────────────────────────────────────────────────────

def _clip_from_stock(stock_clip: Path, duration: float, clip_path: Path,
                     W: int, H: int, fps: int):
    """Extract a random segment from a Pexels stock clip, scaled to portrait."""
    total = _video_duration(stock_clip)
    max_start = max(0.0, total - duration - 0.5)
    t_start = random.uniform(0, max_start) if max_start > 0 else 0.0

    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps={fps}"
    )
    r = subprocess.run([
        FF, "-y",
        "-ss", f"{t_start:.3f}", "-i", str(stock_clip),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(clip_path),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Stock clip extract failed:\n{r.stderr[-600:]}")


def _clip_from_avatar(avatar: Path, t_start: float, duration: float,
                      clip_path: Path, W: int, H: int, fps: int):
    """Extract a timed segment from a D-ID talking-head video."""
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps={fps}"
    )
    r = subprocess.run([
        FF, "-y",
        "-ss", f"{max(t_start,0):.3f}", "-i", str(avatar),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(clip_path),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Avatar clip extract failed:\n{r.stderr[-600:]}")


def _make_loading_clip(clip_path: Path, W: int, H: int, fps: int):
    """Insert a game-style loading screen transition between speaker switches."""
    from agents.effects_agent import make_loading_screen
    make_loading_screen(clip_path, LOADING_SCREEN_DURATION, W, H, fps)


def _make_clip(frame: Path, duration: float, clip_path: Path,
               W: int, H: int, fps: int, zoom_in: bool = True):
    """Render a still image with drift-zoom (last-resort fallback)."""
    SW, SH = int(W * 1.10), int(H * 1.10)
    dx, dy = SW - W, SH - H
    if zoom_in:
        x_expr = f"{dx//2}-({dx//2})*t/{duration:.2f}"
        y_expr = f"{dy//2}-({dy//2})*t/{duration:.2f}"
    else:
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
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(clip_path),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Static clip render failed:\n{r.stderr[-600:]}")


# ── Main ───────────────────────────────────────────────────────────────────────

def run(run_dir: Path) -> Path:
    script_md  = (run_dir / "script.md").read_text()
    date_str   = run_dir.name
    raven_mp3  = run_dir / "raven-voice.mp3"
    jax_mp3    = run_dir / "jax-voice.mp3"
    assets_dir = Path(__file__).parent.parent / "assets"
    frames_dir = run_dir / "assets"
    tmp_dir    = run_dir / "tmp_clips"
    tmp_dir.mkdir(exist_ok=True)
    out        = run_dir / f"final-{date_str}.mp4"

    rd = get_audio_duration(raven_mp3)
    jd = get_audio_duration(jax_mp3)
    total = rd + jd + 0.5
    print(f"[video_agent] Raven: {rd:.1f}s  Jax: {jd:.1f}s  Total: {total:.1f}s")

    # Detect available video sources
    from agents import stock_agent
    use_stock   = stock_agent.has_clips(assets_dir)
    raven_avatar = run_dir / "raven-avatar.mp4"
    jax_avatar   = run_dir / "jax-avatar.mp4"
    use_avatars  = raven_avatar.exists() and jax_avatar.exists()

    if use_stock:
        print("[video_agent] Using Pexels stock footage.")
    elif use_avatars:
        print("[video_agent] Using D-ID talking-head avatars.")
    else:
        print("[video_agent] Using static frames with drift zoom.")

    # Static frame fallbacks
    frame_wide  = frames_dir / "frame-wide.png"
    frame_raven = frames_dir / "frame-raven.png"
    frame_jax   = frames_dir / "frame-jax.png"
    if not frame_raven.exists():
        old = sorted(frames_dir.glob("frame-*.png"))
        frame_raven = old[0] if old else frame_wide
        frame_jax   = old[1] if len(old) > 1 else frame_wide
        frame_wide  = old[0] if old else frame_wide

    W, H, FPS = VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

    lines = parse_script_lines(script_md)
    timed = _assign_timings(lines, rd, jd)

    ass_file = run_dir / "captions.ass"
    write_ass(timed, ass_file)

    # Build clip plan: (t_start, t_end, speaker_or_None, zoom_in, is_loading)
    # is_loading=True → generate a game loading screen instead of video/frame
    CUT_INTERVAL = 8.0
    clips_plan   = []   # (t_start, t_end, speaker, zoom_in, is_loading)
    zoom_toggle  = True
    current_seg_start = 0.0
    current_speaker   = None
    last_cut_t        = 0.0
    loading_offset    = 0.0   # accumulated loading screen time shifts audio timing

    for i, (spk, text, t_in, t_out) in enumerate(timed):
        prev_spk = timed[i-1][0] if i > 0 else None
        speaker_changed = (prev_spk is not None and spk != prev_spk)
        time_since_cut  = t_in - last_cut_t

        if speaker_changed or time_since_cut >= CUT_INTERVAL:
            if t_in > current_seg_start:
                clips_plan.append((current_seg_start, t_in, current_speaker, zoom_toggle, False))
                zoom_toggle = not zoom_toggle
                last_cut_t = t_in

            if speaker_changed:
                # Insert game loading screen instead of plain wide reaction shot
                clips_plan.append((t_in, t_in + LOADING_SCREEN_DURATION, None, zoom_toggle, True))
                zoom_toggle = not zoom_toggle
                current_speaker = spk
                current_seg_start = t_in + LOADING_SCREEN_DURATION
            else:
                current_speaker   = spk if current_speaker is None else None
                current_seg_start = t_in

    if timed:
        clips_plan.append((current_seg_start, timed[-1][3] + 0.3, current_speaker, zoom_toggle, False))

    # Render clips
    clip_files = []
    for idx, (t_start, t_end, speaker, zi, is_loading) in enumerate(clips_plan):
        dur = max(t_end - t_start, 0.5)
        clip_path = tmp_dir / f"clip_{idx:02d}.mp4"

        if is_loading:
            print(f"[video_agent] Clip {idx+1}/{len(clips_plan)}: [LOADING SCREEN] ({LOADING_SCREEN_DURATION}s)...")
            _make_loading_clip(clip_path, W, H, FPS)

        elif use_stock:
            role = speaker.lower() if speaker else "wide"
            stock_clip = stock_agent.random_clip(role, assets_dir)
            print(f"[video_agent] Clip {idx+1}/{len(clips_plan)}: stock/{role} ({dur:.1f}s)...")
            _clip_from_stock(stock_clip, dur, clip_path, W, H, FPS)

        elif use_avatars and speaker is not None:
            avatar = raven_avatar if speaker == "Raven" else jax_avatar
            av_start = t_start if speaker == "Raven" else max(t_start - rd, 0)
            print(f"[video_agent] Clip {idx+1}/{len(clips_plan)}: {speaker} avatar ({dur:.1f}s)...")
            _clip_from_avatar(avatar, av_start, dur, clip_path, W, H, FPS)

        else:
            frame = frame_raven if speaker == "Raven" else (frame_jax if speaker == "Jax" else frame_wide)
            print(f"[video_agent] Clip {idx+1}/{len(clips_plan)}: {frame.name} ({dur:.1f}s)...")
            _make_clip(frame, dur, clip_path, W, H, FPS, zoom_in=zi)

        clip_files.append(clip_path)

    # Concat clips → silent video
    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_files))

    silent_video = run_dir / "tmp-silent.mp4"
    r = subprocess.run([
        FF, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-t", str(total), str(silent_video),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{r.stderr[-600:]}")

    # Mix audio: Raven first, Jax after
    tmp_video_audio = run_dir / "tmp-video-audio.mp4"
    r = subprocess.run([
        FF, "-y",
        "-i", str(silent_video), "-i", str(raven_mp3), "-i", str(jax_mp3),
        "-filter_complex",
        f"[1:a]adelay=0[a0];[2:a]adelay={int(rd*1000)}[a1];[a0][a1]amix=inputs=2:duration=longest[audio]",
        "-map", "0:v", "-map", "[audio]",
        "-c:v", "copy", "-c:a", "aac", "-t", str(total),
        str(tmp_video_audio),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Audio mix failed:\n{r.stderr[-600:]}")

    # Burn captions
    print("[video_agent] Burning captions...")
    r = subprocess.run([
        FF, "-y", "-i", str(tmp_video_audio),
        "-vf", f"ass='{ass_file}'",
        "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", "-pix_fmt", "yuv420p",
        str(out),
    ], capture_output=True, text=True)

    silent_video.unlink(missing_ok=True)
    tmp_video_audio.unlink(missing_ok=True)

    if r.returncode != 0:
        raise RuntimeError(f"Caption burn failed:\n{r.stderr[-500:]}")

    mb = out.stat().st_size / 1_000_000
    print(f"[video_agent] Done → {out.name}  ({mb:.1f}MB)")

    # Apply gaming UI overlays (quest marker, loading screens already inserted,
    # Objective Failed notification)
    try:
        from agents import effects_agent
        effects_agent.run(run_dir, raven_dur=rd, total_dur=total)
    except Exception as e:
        print(f"[video_agent] Effects overlay skipped: {e}")

    return out


if __name__ == "__main__":
    from datetime import date
    run(Path(__file__).parent.parent / "runs" / date.today().isoformat())
