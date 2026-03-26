#!/usr/bin/env python3
"""Generate 10 bold color treatment QR code variants for QueryStory."""

import math
import qrcode
from PIL import Image, ImageDraw, ImageFilter
from pyzbar.pyzbar import decode as pyzbar_decode

# --- Config ---
SCALE = 3
MOD = 36 * SCALE       # module pixel size
PAD = 70 * SCALE       # padding
OUT_DIR = "/home/shapor/src/qs/live-mode/qr-variants"

# Colors
QS_BLUE = (37, 99, 235)        # #2563EB
DARK_NAVY = (15, 23, 42)       # #0f172a
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Generate QR matrix
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)

# Image dimensions
IMG_W = N * MOD + 2 * PAD
IMG_H = N * MOD + 2 * PAD

# Finder pattern positions (top-left corners of 7x7 finder patterns)
FINDERS = [(0, 0), (0, N - 7), (N - 7, 0)]

def is_finder(r, c):
    for fr, fc in FINDERS:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return True
    return False

def is_finder_center(r, c):
    """Check if module is in the 3x3 center of a finder pattern."""
    for fr, fc in FINDERS:
        if fr + 2 <= r <= fr + 4 and fc + 2 <= c <= fc + 4:
            return True
    return False

def module_center(r, c):
    """Get pixel center of module (r, c)."""
    x = PAD + c * MOD + MOD // 2
    y = PAD + r * MOD + MOD // 2
    return x, y

def qr_center():
    return PAD + N * MOD // 2, PAD + N * MOD // 2

def lerp_color(c1, c2, t):
    t = max(0, min(1, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def draw_rounded_rect(draw, bbox, radius, fill):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)

def draw_module(draw, r, c, color, round_ratio=0.3):
    x = PAD + c * MOD
    y = PAD + r * MOD
    margin = int(MOD * 0.08)
    radius = int(MOD * round_ratio)
    draw_rounded_rect(draw, (x + margin, y + margin, x + MOD - margin, y + MOD - margin), radius, color)

def draw_standard_finder(draw, fr, fc, outer_color=BLACK, inner_color=BLACK):
    """Draw a standard 7x7 finder pattern."""
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    r = int(MOD * 0.3)
    # Outer 7x7
    draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), r * 2, outer_color)
    # White 5x5
    off1 = MOD
    draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), r * 2, WHITE)
    # Inner 3x3
    off2 = 2 * MOD
    draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), r * 2, inner_color)

def draw_standard_finder_bg(draw, fr, fc, outer_color=BLACK, inner_color=BLACK, bg_color=WHITE):
    """Draw a standard 7x7 finder pattern with custom bg color for the ring."""
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    r = int(MOD * 0.3)
    draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), r * 2, outer_color)
    off1 = MOD
    draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), r * 2, bg_color)
    off2 = 2 * MOD
    draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), r * 2, inner_color)

def draw_etched_finder(draw, fr, fc, outer_color=BLACK, logo_color=WHITE):
    """Draw finder with logo etched in white on the 3x3 center."""
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    r = int(MOD * 0.3)
    # Outer 7x7
    draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), r * 2, outer_color)
    # White ring
    off1 = MOD
    draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), r * 2, WHITE)
    # Inner 3x3 solid
    off2 = 2 * MOD
    draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), r * 2, outer_color)
    # Draw logo elements in the 3x3 center
    cx = x0 + 3.5 * MOD
    cy = y0 + 3.5 * MOD
    s = MOD * 1.2  # scale for logo in center
    draw_mini_logo(draw, cx, cy, s, logo_color)

def draw_etched_finder_bg(draw, fr, fc, outer_color=BLACK, logo_color=WHITE, bg_color=WHITE):
    """Draw finder with logo etched, custom bg for ring."""
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    r = int(MOD * 0.3)
    draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), r * 2, outer_color)
    off1 = MOD
    draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), r * 2, bg_color)
    off2 = 2 * MOD
    draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), r * 2, outer_color)
    cx = x0 + 3.5 * MOD
    cy = y0 + 3.5 * MOD
    s = MOD * 1.2
    draw_mini_logo(draw, cx, cy, s, logo_color)

def draw_mini_logo(draw, cx, cy, scale, color):
    """Draw simplified QS logo: 2x2 grid + dots."""
    s = scale
    gap = s * 0.12
    box_s = (s - gap) / 2
    # 2x2 grid dots
    for gr in range(2):
        for gc in range(2):
            dx = cx + (gc - 0.5) * (box_s + gap)
            dy = cy + (gr - 0.5) * (box_s + gap)
            r = box_s * 0.35
            draw.ellipse((dx - r, dy - r, dx + r, dy + r), fill=color)

def s_curve_side(x, y):
    """Return which side of the S-curve a point is on. Approximate using the center of QR.
    Maps pixel coords to the SVG coordinate space (45,30)-(42,48) range,
    then checks side. Returns -1 or +1."""
    cx, cy = qr_center()
    # Normalize to -1..1 range relative to QR center
    half = N * MOD / 2
    nx = (x - cx) / half  # -1 to 1
    ny = (y - cy) / half
    # S-curve goes roughly from top-center to bottom-center with horizontal wiggle
    # Approximate as a sine wave
    curve_x = 0.15 * math.sin(ny * math.pi)
    return 1 if nx > curve_x else -1

def dist_to_s_curve(x, y):
    """Approximate distance to S-curve center line, normalized 0-1."""
    cx, cy = qr_center()
    half = N * MOD / 2
    nx = (x - cx) / half
    ny = (y - cy) / half
    curve_x = 0.15 * math.sin(ny * math.pi)
    return min(abs(nx - curve_x) / 1.0, 1.0)

def save_and_scan(img, filename, label, dark_mode=False):
    # Downsample 3x to final size
    final_w = IMG_W // SCALE
    final_h = IMG_H // SCALE
    final = img.resize((final_w, final_h), Image.LANCZOS)
    path = f"{OUT_DIR}/{filename}"
    final.save(path, "PNG")
    # Scan - for dark mode, try both normal and inverted
    results = pyzbar_decode(final)
    if not results and dark_mode:
        from PIL import ImageOps
        inverted = ImageOps.invert(final)
        results = pyzbar_decode(inverted)
    status = "PASS" if results and results[0].data.decode() == "https://querystory.ai" else "FAIL"
    decoded = results[0].data.decode() if results else "NO DECODE"
    print(f"{filename}: {status} ({decoded}) - {label}")
    return status


# ============================================================
# D01: Radial gradient - dark blue center -> light blue edge
# ============================================================
def gen_d01():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    cx, cy = qr_center()
    max_dist = math.sqrt((N * MOD / 2) ** 2 * 2)
    DARK = (20, 50, 160)
    LIGHT = (100, 180, 255)
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            d = math.sqrt((mx - cx) ** 2 + (my - cy) ** 2) / max_dist
            color = lerp_color(DARK, LIGHT, d)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        draw_standard_finder(draw, fr, fc, DARK, DARK)
    return save_and_scan(img, "D01_radial_gradient.png", "Radial gradient dark->light blue")


# ============================================================
# D02: Angular/sweep gradient in blue-indigo-teal range
# ============================================================
def gen_d02():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    cx, cy = qr_center()
    # Color stops around the circle: blue -> indigo -> teal -> blue
    def angle_color(angle):
        # angle in radians, 0 to 2pi
        t = angle / (2 * math.pi)  # 0 to 1
        colors = [
            (37, 99, 235),    # blue
            (79, 70, 229),    # indigo
            (20, 184, 166),   # teal
            (37, 99, 235),    # blue (wrap)
        ]
        idx = t * (len(colors) - 1)
        i = int(idx)
        f = idx - i
        i = min(i, len(colors) - 2)
        return lerp_color(colors[i], colors[i + 1], f)

    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            angle = math.atan2(my - cy, mx - cx) + math.pi  # 0 to 2pi
            color = angle_color(angle)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        draw_etched_finder(draw, fr, fc, QS_BLUE, WHITE)
    return save_and_scan(img, "D02_angular_sweep.png", "Angular sweep blue/indigo/teal")


# ============================================================
# D03: S-curve color boundary - two blues
# ============================================================
def gen_d03():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    BLUE_A = (30, 64, 175)    # darker blue
    BLUE_B = (96, 165, 250)   # lighter blue
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            side = s_curve_side(mx, my)
            color = BLUE_A if side < 0 else BLUE_B
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        draw_standard_finder(draw, fr, fc, BLUE_A, BLUE_A)
    return save_and_scan(img, "D03_scurve_boundary.png", "S-curve color boundary two-tone")


# ============================================================
# D04: Diagonal gradient (top-left dark -> bottom-right light)
# ============================================================
def gen_d04():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    DARK = (30, 58, 138)      # blue-900
    LIGHT = (147, 197, 253)   # blue-300
    max_diag = N * MOD * math.sqrt(2)
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            px = mx - PAD
            py = my - PAD
            d = (px + py) / max_diag
            color = lerp_color(DARK, LIGHT, d)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        # Color finders by position
        mx, my = module_center(fr + 3, fc + 3)
        d = ((mx - PAD) + (my - PAD)) / max_diag
        fc_color = lerp_color(DARK, LIGHT, d)
        draw_etched_finder(draw, fr, fc, fc_color, WHITE)
    return save_and_scan(img, "D04_diagonal_gradient.png", "Diagonal gradient dark->light")


# ============================================================
# D05: Quadrant colors with smooth blending (2x2 grid inspired)
# ============================================================
def gen_d05():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    # Four quadrant colors
    TL = (30, 64, 175)      # blue-800
    TR = (79, 70, 229)      # indigo-600
    BL = (14, 116, 144)     # cyan-700
    BR = (37, 99, 235)      # blue-600
    cx, cy = qr_center()
    half = N * MOD / 2
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            # Bilinear interpolation
            tx = max(0, min(1, (mx - PAD) / (N * MOD)))
            ty = max(0, min(1, (my - PAD) / (N * MOD)))
            top = lerp_color(TL, TR, tx)
            bot = lerp_color(BL, BR, tx)
            color = lerp_color(top, bot, ty)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        mx, my = module_center(fr + 3, fc + 3)
        tx = max(0, min(1, (mx - PAD) / (N * MOD)))
        ty = max(0, min(1, (my - PAD) / (N * MOD)))
        top = lerp_color(TL, TR, tx)
        bot = lerp_color(BL, BR, tx)
        fc_color = lerp_color(top, bot, ty)
        draw_standard_finder(draw, fr, fc, fc_color, fc_color)
    return save_and_scan(img, "D05_quadrant_blend.png", "Quadrant color blend (2x2 grid)")


# ============================================================
# D06: Distance from S-curve - lighter near curve, darker away
# ============================================================
def gen_d06():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    NEAR = (96, 165, 250)     # light blue near curve
    FAR = (30, 27, 75)        # dark indigo far from curve
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            d = dist_to_s_curve(mx, my)
            color = lerp_color(NEAR, FAR, d)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        draw_etched_finder(draw, fr, fc, FAR, (96, 165, 250))
    return save_and_scan(img, "D06_scurve_distance.png", "Color by distance from S-curve")


# ============================================================
# D07: Dark mode - navy bg, bright blue dots
# ============================================================
def gen_d07():
    img = Image.new("RGB", (IMG_W, IMG_H), DARK_NAVY)
    draw = ImageDraw.Draw(img)
    BRIGHT = (96, 165, 250)   # blue-400
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            draw_module(draw, r, c, BRIGHT)
    for fr, fc in FINDERS:
        # Custom finder for dark bg
        x0 = PAD + fc * MOD
        y0 = PAD + fr * MOD
        m = int(MOD * 0.08)
        rad = int(MOD * 0.3) * 2
        draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), rad, BRIGHT)
        off1 = MOD
        draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), rad, DARK_NAVY)
        off2 = 2 * MOD
        draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), rad, BRIGHT)
    return save_and_scan(img, "D07_dark_mode.png", "Dark mode navy bg + bright blue", dark_mode=True)


# ============================================================
# D08: Dark mode with radial glow from center
# ============================================================
def gen_d08():
    img = Image.new("RGB", (IMG_W, IMG_H), DARK_NAVY)
    draw = ImageDraw.Draw(img)
    cx, cy = qr_center()
    max_dist = math.sqrt((N * MOD / 2) ** 2 * 2)
    BRIGHT = (147, 197, 253)  # blue-300
    MID = (59, 130, 246)      # blue-500
    DIM = (30, 64, 175)       # blue-800
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            d = math.sqrt((mx - cx) ** 2 + (my - cy) ** 2) / max_dist
            if d < 0.5:
                color = lerp_color(BRIGHT, MID, d * 2)
            else:
                color = lerp_color(MID, DIM, (d - 0.5) * 2)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        x0 = PAD + fc * MOD
        y0 = PAD + fr * MOD
        m = int(MOD * 0.08)
        rad = int(MOD * 0.3) * 2
        draw_rounded_rect(draw, (x0 + m, y0 + m, x0 + 7 * MOD - m, y0 + 7 * MOD - m), rad, DIM)
        off1 = MOD
        draw_rounded_rect(draw, (x0 + off1, y0 + off1, x0 + 6 * MOD, y0 + 6 * MOD), rad, DARK_NAVY)
        off2 = 2 * MOD
        draw_rounded_rect(draw, (x0 + off2 + m, y0 + off2 + m, x0 + 5 * MOD - m, y0 + 5 * MOD - m), rad, DIM)
    return save_and_scan(img, "D08_dark_radial_glow.png", "Dark mode with radial glow", dark_mode=True)


# ============================================================
# D09: Background gradient (light blue -> white) with QS blue dots
# ============================================================
def gen_d09():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    # Draw background gradient
    BG_TOP = (219, 234, 254)    # blue-100
    BG_BOT = (255, 255, 255)    # white
    for y in range(IMG_H):
        t = y / IMG_H
        c = lerp_color(BG_TOP, BG_BOT, t)
        draw.line([(0, y), (IMG_W, y)], fill=c)
    # Dots in solid blue
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            draw_module(draw, r, c, QS_BLUE)
    for fr, fc in FINDERS:
        draw_etched_finder(draw, fr, fc, QS_BLUE, WHITE)
    return save_and_scan(img, "D09_bg_gradient.png", "Background gradient + solid blue dots")


# ============================================================
# D10: Chrome-style - radial + angular combo, etched finders, bold
# ============================================================
def gen_d10():
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    cx, cy = qr_center()
    max_dist = math.sqrt((N * MOD / 2) ** 2 * 2)
    # Three color sectors like Chrome but in blue spectrum
    SECTOR_COLORS = [
        (37, 99, 235),     # blue
        (79, 70, 229),     # indigo
        (6, 182, 212),     # cyan
    ]
    for r in range(N):
        for c in range(N):
            if not matrix[r][c] or is_finder(r, c):
                continue
            mx, my = module_center(r, c)
            angle = math.atan2(my - cy, mx - cx) + math.pi
            sector = int(angle / (2 * math.pi) * 3) % 3
            next_sector = (sector + 1) % 3
            # Blend within sector
            sector_start = sector * (2 * math.pi / 3)
            t_in_sector = (angle - sector_start) / (2 * math.pi / 3)
            base_color = lerp_color(SECTOR_COLORS[sector], SECTOR_COLORS[next_sector], t_in_sector)
            # Add radial darkening toward edges
            d = math.sqrt((mx - cx) ** 2 + (my - cy) ** 2) / max_dist
            color = lerp_color(base_color, tuple(max(0, v - 40) for v in base_color), d * 0.5)
            draw_module(draw, r, c, color)
    for fr, fc in FINDERS:
        # Each finder gets its sector color
        mx, my = module_center(fr + 3, fc + 3)
        angle = math.atan2(my - cy, mx - cx) + math.pi
        sector = int(angle / (2 * math.pi) * 3) % 3
        draw_etched_finder(draw, fr, fc, SECTOR_COLORS[sector], WHITE)
    return save_and_scan(img, "D10_chrome_sectors.png", "Chrome-style sector colors")


# ============================================================
# Run all
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Generating bold color QR variants...")
    print("=" * 60)
    results = []
    for fn in [gen_d01, gen_d02, gen_d03, gen_d04, gen_d05,
               gen_d06, gen_d07, gen_d08, gen_d09, gen_d10]:
        results.append(fn())
    print("=" * 60)
    passed = sum(1 for r in results if r == "PASS")
    print(f"Results: {passed}/10 passed scanning")
