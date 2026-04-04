#!/usr/bin/env python3
"""
Vinyl Records Intro Video Generator
Creates a cinematic intro video featuring a spinning vinyl record
with cosmic aesthetic matching the universal369 design DNA.

Output: 1080x1920 vertical video (9:16), 8 seconds, 30fps
"""

import math
import os
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# === Config ===
WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 8  # seconds
TOTAL_FRAMES = FPS * DURATION

# Colors (cosmic palette)
BG_COLOR = (6, 8, 16)           # #060810
GOLD = (201, 168, 76)           # #c9a84c
GOLD_DIM = (140, 117, 53)
PURPLE = (139, 92, 246)         # #8b5cf6
CYAN = (77, 184, 200)           # #4db8c8
WHITE = (240, 240, 240)         # #f0f0f0
VINYL_BLACK = (15, 15, 20)
VINYL_GROOVE = (25, 25, 35)
LABEL_RED = (140, 30, 30)
LABEL_DARK = (90, 20, 20)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "vinyl-intro.mp4")

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"


def ease_in_out(t):
    """Smooth ease-in-out curve."""
    return t * t * (3 - 2 * t)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def draw_vinyl_record(img, cx, cy, radius, angle, scale=1.0, alpha=255):
    """Draw a vinyl record with grooves, label, and spindle hole."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    r = int(radius * scale)
    if r < 10:
        return img

    # Outer disc (black vinyl)
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(*VINYL_BLACK, alpha)
    )

    # Grooves - concentric rings with slight variation
    for i in range(12, r - 30, 3):
        groove_alpha = int(alpha * 0.3)
        # Subtle variation based on angle to simulate light reflection
        brightness_mod = int(8 * math.sin(angle + i * 0.1))
        c = max(0, min(255, VINYL_GROOVE[0] + brightness_mod))
        draw.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            outline=(c, c, c + 5, groove_alpha),
            width=1
        )

    # Light reflection arc (the shiny streak on vinyl)
    ref_angle = angle * 0.5
    for j in range(3):
        ref_r = r - 40 - j * 60
        if ref_r < 30:
            break
        arc_start = math.degrees(ref_angle) - 20
        arc_end = arc_start + 40
        draw.arc(
            [cx - ref_r, cy - ref_r, cx + ref_r, cy + ref_r],
            start=arc_start, end=arc_end,
            fill=(60, 60, 70, int(alpha * 0.4)),
            width=2
        )

    # Outer rim highlight
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(*GOLD_DIM, int(alpha * 0.3)),
        width=2
    )

    # Center label
    label_r = int(r * 0.28)
    # Label gradient (dark red center)
    draw.ellipse(
        [cx - label_r, cy - label_r, cx + label_r, cy + label_r],
        fill=(*LABEL_RED, alpha)
    )
    # Inner ring on label
    inner_r = int(label_r * 0.7)
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(*LABEL_DARK, alpha)
    )

    # Label text (rotates with record)
    if scale > 0.5:
        try:
            label_font = ImageFont.truetype(FONT_BOLD, max(10, int(14 * scale)))
            small_font = ImageFont.truetype(FONT_ITALIC, max(8, int(10 * scale)))
        except:
            label_font = ImageFont.load_default()
            small_font = label_font

        # Draw rotated label text
        label_img = Image.new("RGBA", (label_r * 2, label_r * 2), (0, 0, 0, 0))
        label_draw = ImageDraw.Draw(label_img)

        # Title on label
        text = "VINYLE"
        bbox = label_draw.textbbox((0, 0), text, font=label_font)
        tw = bbox[2] - bbox[0]
        label_draw.text(
            (label_r - tw // 2, label_r - 20),
            text, fill=(*GOLD, alpha), font=label_font
        )
        text2 = "RECORDS"
        bbox2 = label_draw.textbbox((0, 0), text2, font=small_font)
        tw2 = bbox2[2] - bbox2[0]
        label_draw.text(
            (label_r - tw2 // 2, label_r),
            text2, fill=(*WHITE, int(alpha * 0.8)), font=small_font
        )

        # Rotate label with record
        rotated_label = label_img.rotate(
            -math.degrees(angle), resample=Image.BICUBIC, center=(label_r, label_r)
        )
        overlay.paste(
            rotated_label,
            (cx - label_r, cy - label_r),
            rotated_label
        )

    # Spindle hole
    hole_r = max(2, int(r * 0.025))
    draw.ellipse(
        [cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r],
        fill=(0, 0, 0, alpha)
    )

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    return img


def draw_starfield(img, frame, total_frames):
    """Draw subtle animated star particles."""
    draw = ImageDraw.Draw(img)
    import random
    random.seed(42)  # Consistent star positions

    for _ in range(80):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        base_bright = random.randint(40, 120)
        # Twinkle
        twinkle = math.sin(frame * 0.05 + random.random() * 10) * 30
        bright = max(0, min(255, int(base_bright + twinkle)))
        size = random.choice([1, 1, 1, 2])
        draw.ellipse([x, y, x + size, y + size], fill=(bright, bright, bright + 10, bright))

    return img


def draw_dust_particles(img, frame):
    """Floating golden dust particles."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    import random
    random.seed(99)

    for i in range(30):
        speed = random.uniform(0.3, 1.2)
        x = (random.randint(0, WIDTH) + int(frame * speed * 2)) % WIDTH
        base_y = random.randint(0, HEIGHT)
        y = base_y + int(math.sin(frame * 0.03 + i) * 20)

        progress = frame / TOTAL_FRAMES
        particle_alpha = int(80 * min(1.0, progress * 3) * (0.5 + 0.5 * math.sin(frame * 0.08 + i)))

        size = random.choice([1, 2, 2, 3])
        color = (*GOLD, particle_alpha) if i % 3 != 0 else (*PURPLE, particle_alpha)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=color)

    return Image.alpha_composite(img, overlay)


def draw_glow(img, cx, cy, radius, color, intensity):
    """Draw a soft radial glow."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for r in range(radius, 0, -2):
        alpha = int(intensity * (1 - r / radius) ** 2)
        alpha = max(0, min(255, alpha))
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, alpha)
        )

    return Image.alpha_composite(img, overlay)


def generate_frame(frame_num):
    """Generate a single frame of the intro video."""
    t = frame_num / TOTAL_FRAMES  # 0.0 to 1.0

    img = Image.new("RGBA", (WIDTH, HEIGHT), (*BG_COLOR, 255))

    # Star background
    img = draw_starfield(img, frame_num, TOTAL_FRAMES)

    # === Animation phases ===
    # Phase 1 (0-2s): Record enters from bottom with rotation, scales up
    # Phase 2 (2-5s): Record centered, spinning, title fades in
    # Phase 3 (5-7s): Full display with glow effects
    # Phase 4 (7-8s): Subtle zoom and fade to ready state

    cx = WIDTH // 2
    record_radius = 320

    # Record position and scale animation
    if t < 0.25:  # Phase 1: Enter
        phase_t = ease_out_cubic(t / 0.25)
        cy = int(HEIGHT + 400 - (HEIGHT + 400 - HEIGHT * 0.42) * phase_t)
        scale = 0.3 + 0.7 * phase_t
        record_alpha = int(255 * min(1.0, phase_t * 1.5))
    elif t < 0.625:  # Phase 2: Settle
        cy = int(HEIGHT * 0.42)
        scale = 1.0
        record_alpha = 255
    elif t < 0.875:  # Phase 3: Full display
        cy = int(HEIGHT * 0.42)
        scale = 1.0 + 0.02 * math.sin(t * 8)  # Subtle pulse
        record_alpha = 255
    else:  # Phase 4: Settle
        cy = int(HEIGHT * 0.42)
        scale = 1.0
        record_alpha = 255

    # Spin angle (accelerates then constant)
    if t < 0.25:
        spin_speed = ease_in_out(t / 0.25) * 4
    else:
        spin_speed = 4
    angle = frame_num * 0.08 * (spin_speed / 4 + 0.2)

    # Background glow behind record
    glow_intensity = int(40 * min(1.0, t * 4))
    img = draw_glow(img, cx, cy, int(record_radius * 1.8 * scale), PURPLE, glow_intensity)
    img = draw_glow(img, cx, cy, int(record_radius * 1.3 * scale), GOLD, glow_intensity // 2)

    # Draw the vinyl record
    img = draw_vinyl_record(img, cx, cy, record_radius, angle, scale, record_alpha)

    # Dust particles
    img = draw_dust_particles(img, frame_num)

    # === Text overlays ===
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        title_font = ImageFont.truetype(FONT_BOLD, 72)
        subtitle_font = ImageFont.truetype(FONT_ITALIC, 32)
        tagline_font = ImageFont.truetype(FONT_REGULAR, 24)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = title_font
        tagline_font = title_font

    # Title: "VINYLE RECORDS" - fades in during phase 2
    if t > 0.25:
        text_t = min(1.0, (t - 0.25) / 0.2)
        text_alpha = int(255 * ease_in_out(text_t))

        # Title
        title = "VINYLE RECORDS"
        bbox = draw.textbbox((0, 0), title, font=title_font)
        tw = bbox[2] - bbox[0]
        title_y = int(HEIGHT * 0.72)

        # Gold glow behind text
        for offset in range(3, 0, -1):
            glow_a = int(text_alpha * 0.15)
            draw.text(
                (cx - tw // 2 - offset, title_y - offset),
                title, fill=(*GOLD, glow_a), font=title_font
            )

        draw.text(
            (cx - tw // 2, title_y),
            title, fill=(*GOLD, text_alpha), font=title_font
        )

        # Decorative line under title
        line_w = int(tw * 0.6 * ease_in_out(min(1.0, (t - 0.3) / 0.15)))
        line_y = title_y + 85
        if line_w > 0:
            draw.line(
                [cx - line_w // 2, line_y, cx + line_w // 2, line_y],
                fill=(*GOLD, int(text_alpha * 0.5)),
                width=1
            )
            # Diamond at center of line
            d = 4
            draw.polygon(
                [(cx, line_y - d), (cx + d, line_y), (cx, line_y + d), (cx - d, line_y)],
                fill=(*GOLD, int(text_alpha * 0.7))
            )

    # Subtitle - fades in slightly later
    if t > 0.35:
        sub_t = min(1.0, (t - 0.35) / 0.2)
        sub_alpha = int(255 * ease_in_out(sub_t))

        subtitle = "Curated Sound  ·  Timeless Wax"
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = bbox[2] - bbox[0]
        sub_y = int(HEIGHT * 0.72) + 105

        draw.text(
            (cx - sw // 2, sub_y),
            subtitle, fill=(*WHITE, int(sub_alpha * 0.7)), font=subtitle_font
        )

    # Bottom tagline - last to appear
    if t > 0.55:
        tag_t = min(1.0, (t - 0.55) / 0.2)
        tag_alpha = int(255 * ease_in_out(tag_t))

        tagline = "E S T .   2 0 2 5"
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tgw = bbox[2] - bbox[0]
        tag_y = int(HEIGHT * 0.85)

        draw.text(
            (cx - tgw // 2, tag_y),
            tagline, fill=(*CYAN, int(tag_alpha * 0.6)), font=tagline_font
        )

    img = Image.alpha_composite(img, overlay)

    # Convert to RGB for video output
    return img.convert("RGB")


def main():
    print("Generating Vinyle Records intro video...")
    print(f"  Resolution: {WIDTH}x{HEIGHT}")
    print(f"  Duration: {DURATION}s @ {FPS}fps = {TOTAL_FRAMES} frames")

    # Create temp directory for frames
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate all frames
        for i in range(TOTAL_FRAMES):
            frame = generate_frame(i)
            frame_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
            frame.save(frame_path)

            if (i + 1) % 30 == 0 or i == 0:
                print(f"  Frame {i + 1}/{TOTAL_FRAMES}")

        print("  Encoding video with FFmpeg...")

        # Assemble with FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(tmpdir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-crf", "18",  # High quality
            "-movflags", "+faststart",
            OUTPUT_FILE
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False

        file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
        print(f"\n  Output: {OUTPUT_FILE}")
        print(f"  Size: {file_size:.1f} MB")
        print("  Done!")
        return True


if __name__ == "__main__":
    main()
