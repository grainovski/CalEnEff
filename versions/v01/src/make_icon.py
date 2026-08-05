"""
Generate Ra226_Calibration.ico  —  multi-size app icon
Design: dark background, radiation trefoil (international ionising-radiation
symbol) drawn in the app's green accent colour, with a small "γ" superimposed.

Run once:   python make_icon.py
Output:     Ra226_Calibration.ico  (16, 32, 48, 64, 128, 256 px frames)
"""
import math
from PIL import Image, ImageDraw, ImageFont

# ── palette (matches _DARK theme) ────────────────────────────────────────────
BG      = (30,  30,  46,  255)   # #1e1e2e  — deep navy
FG      = (166, 227, 161, 255)   # #a6e3a1  — green accent (EFF_C)
FG2     = (137, 180, 250, 255)   # #89b4fa  — blue accent  (ACCENT)
DARK2   = (42,  42,  62,  0)     # transparent placeholder

def draw_icon(size: int) -> Image.Image:
    """Draw a single square frame at *size* × *size* pixels."""
    img  = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    cx = cy = size / 2
    r_outer = size * 0.42       # outer radius of each sector
    r_inner = size * 0.13       # inner disc radius (hole in trefoil)
    r_centre = size * 0.09      # central solid disc radius

    # ── trefoil: 3 sectors, 60° each, separated by 60° gaps ──────────────
    for k in range(3):
        base_angle = 90 + k * 120          # start at top, rotate 120° each
        a_start    = base_angle - 30        # sector spans ±30° → 60° wide
        a_end      = base_angle + 30
        # draw a filled "doughnut sector": full disc minus inner disc
        # PIL arc draws the outline; we fill using a pie then mask

        # outer pie slice (full sector)
        draw.pieslice(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            start=a_start, end=a_end, fill=FG,
        )

    # punch out inner circle (the hole that makes it a doughnut-sector trefoil)
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        fill=BG,
    )

    # ── gap lines: 3 thin wedges that separate the sectors ────────────────
    gap_half = 8  # degrees half-width of each gap line
    for k in range(3):
        angle_deg = 90 + k * 120
        for sign in (+1, -1):
            theta = math.radians(angle_deg + sign * (30 - gap_half / 2))
            x_end = cx + r_outer * 1.1 * math.cos(theta)
            y_end = cy + r_outer * 1.1 * math.sin(theta)
            lw    = max(1, int(size * 0.025))
            draw.line([cx, cy, x_end, y_end], fill=BG, width=lw)

    # ── central solid disc ────────────────────────────────────────────────
    draw.ellipse(
        [cx - r_centre, cy - r_centre, cx + r_centre, cy + r_centre],
        fill=FG,
    )

    # ── "γ" text centred (only legible at larger sizes) ───────────────────
    if size >= 48:
        fs = max(8, int(size * 0.22))
        try:
            font = ImageFont.truetype("segoeuib.ttf", fs)
        except OSError:
            try:
                font = ImageFont.truetype("arial.ttf", fs)
            except OSError:
                font = ImageFont.load_default()

        txt = "γ"
        bbox = draw.textbbox((0, 0), txt, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
        # draw with BG colour so it contrasts against the green central disc
        draw.text((tx, ty), txt, font=font, fill=BG)

    return img


# ── generate all sizes and save as ICO ───────────────────────────────────────
# PIL's ICO writer downscales the SOURCE image to each requested size.
# Use the largest frame (256×256) as the source so every size is a
# high-quality downscale, not an upscale.
SIZES = [16, 32, 48, 64, 128, 256]

src = draw_icon(256)   # single high-res master

out_path = "Ra226_Calibration.ico"
src.save(
    out_path,
    format="ICO",
    sizes=[(s, s) for s in SIZES],
)

# Verify
from PIL import IcoImagePlugin
with open(out_path, "rb") as f:
    _ico = IcoImagePlugin.IcoFile(f)
    actual = sorted(_ico.sizes())
print(f"Saved {out_path}  frames: {actual}")
