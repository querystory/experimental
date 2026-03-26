#!/usr/bin/env python3
"""Generate QR code variants H01-H10: S-curve visible through shape/size/color modulation."""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pyzbar.pyzbar import decode as pyzbar_decode
import qrcode

# --- QR matrix ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
MOD = len(matrix)  # 29

# --- S-curve bezier path ---
# M45,30 C40,30 35,34 37,36 C39,38 44,38 47,41 C50,44 47,48 42,48 C37,48 35,44 37,42
BEZIER_SEGMENTS = [
    [(45, 30), (40, 30), (35, 34), (37, 36)],
    [(37, 36), (39, 38), (44, 38), (47, 41)],
    [(47, 41), (50, 44), (47, 48), (42, 48)],
    [(42, 48), (37, 48), (35, 44), (37, 42)],
]

def cubic_bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3 * p0[0] + 3*u**2*t * p1[0] + 3*u*t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3*u**2*t * p1[1] + 3*u*t**2 * p2[1] + t**3 * p3[1])

# Generate S-curve points in module coordinates
# Logo grid 15-45 maps to module space. Logo center is at pixel (30, 39) in 0-60 space.
# Map: module = (coord - 15) / 30 * 29
def logo_to_mod(x, y):
    return (x - 15) / 30 * MOD, (y - 15) / 30 * MOD

s_points = []
for seg in BEZIER_SEGMENTS:
    for i in range(50):
        t = i / 49.0
        px, py = cubic_bezier(seg[0], seg[1], seg[2], seg[3], t)
        mx, my = logo_to_mod(px, py)
        s_points.append((mx, my))

s_points = np.array(s_points)

def dist_to_s(col, row):
    """Min distance from module center (col, row) to S-curve in module coords."""
    dx = s_points[:, 0] - (col + 0.5)
    dy = s_points[:, 1] - (row + 0.5)
    return float(np.min(np.sqrt(dx**2 + dy**2)))

# Precompute distance map
dist_map = np.zeros((MOD, MOD))
for r in range(MOD):
    for c in range(MOD):
        dist_map[r][c] = dist_to_s(c, r)

max_dist = dist_map.max()

# --- Finder pattern / function pattern detection ---
def is_finder(r, c):
    """Check if module is in finder pattern area (7x7 corners + separators)."""
    in_tl = r < 7 and c < 7
    in_tr = r < 7 and c >= MOD - 7
    in_bl = r >= MOD - 7 and c < 7
    # separators
    sep_tl = (r == 7 and c < 8) or (c == 7 and r < 8)
    sep_tr = (r == 7 and c >= MOD - 8) or (c == MOD - 8 and r < 8)
    sep_bl = (r == MOD - 8 and c < 8) or (c == 7 and r >= MOD - 8)
    return in_tl or in_tr or in_bl or sep_tl or sep_tr or sep_bl

def is_alignment(r, c):
    """Check if in alignment pattern (5x5 at center for version 3: position 22)."""
    ar, ac = 22, 22
    return abs(r - ar) <= 2 and abs(c - ac) <= 2

def is_timing(r, c):
    """Timing patterns."""
    return (r == 6 and 8 <= c <= MOD - 9) or (c == 6 and 8 <= r <= MOD - 9)

def is_function_pattern(r, c):
    return is_finder(r, c) or is_alignment(r, c) or is_timing(r, c)

# --- Drawing helpers ---
PAD = 4  # quiet zone modules
SCALE = 20  # pixels per module

def img_size():
    return (MOD + 2 * PAD) * SCALE

def mod_xy(r, c):
    """Top-left pixel of module (r, c)."""
    x = (PAD + c) * SCALE
    y = (PAD + r) * SCALE
    return x, y

def mod_center(r, c):
    x, y = mod_xy(r, c)
    return x + SCALE // 2, y + SCALE // 2

def draw_etched_finder(draw, top_r, top_c):
    """Draw finder with QS logo etched in 3x3 center."""
    for dr in range(7):
        for dc in range(7):
            r, c = top_r + dr, top_c + dc
            x, y = mod_xy(r, c)
            # Standard finder: outer ring dark, then white, then 3x3 center dark
            if dr == 0 or dr == 6 or dc == 0 or dc == 6:
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="#1a1a2e")
            elif dr == 1 or dr == 5 or dc == 1 or dc == 5:
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="white")
            else:
                # 3x3 center - dark with white "QS" mark
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="#1a1a2e")
    # Etch: white pixels in center 3x3 to suggest logo
    # Simple "S" shape in the 3x3:  top-right, middle-center, bottom-left
    cx, cy = mod_xy(top_r + 3, top_c + 3)
    s = SCALE
    # White S-curve hint in center
    draw.rectangle([cx + s//3, cy + 1, cx + s - 2, cy + s//3], fill="white")  # top bar
    draw.rectangle([cx + s//3, cy + s//3, cx + 2*s//3, cy + 2*s//3], fill="white")  # mid
    draw.rectangle([cx + 1, cy + 2*s//3, cx + 2*s//3, cy + s - 2], fill="white")  # bottom bar

def draw_finders(draw):
    """Draw all three finder patterns with etched logo."""
    draw_etched_finder(draw, 0, 0)
    draw_etched_finder(draw, 0, MOD - 7)
    draw_etched_finder(draw, MOD - 7, 0)
    # Separators (white) - already white background, but ensure
    for i in range(8):
        for r, c in [(7, i), (i, 7), (7, MOD - 8 + i), (i, MOD - 8),
                      (MOD - 8, i), (MOD - 8 + i, 7)]:
            if 0 <= r < MOD and 0 <= c < MOD:
                x, y = mod_xy(r, c)
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="white")

def draw_alignment(draw):
    """Draw alignment pattern at (22,22)."""
    ar, ac = 22, 22
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            r, c = ar + dr, ac + dc
            x, y = mod_xy(r, c)
            if abs(dr) == 2 or abs(dc) == 2:
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="#1a1a2e")
            elif abs(dr) == 1 or abs(dc) == 1:
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="white")
            else:
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="#1a1a2e")

def draw_timing(draw):
    """Draw timing patterns."""
    for i in range(8, MOD - 8):
        x, y = mod_xy(6, i)
        col = "#1a1a2e" if i % 2 == 0 else "white"
        draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill=col)
        x, y = mod_xy(i, 6)
        draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill=col)

def new_image():
    sz = img_size()
    img = Image.new("RGB", (sz, sz), "white")
    return img, ImageDraw.Draw(img)

def draw_base(draw):
    """Draw finders, alignment, timing."""
    draw_finders(draw)
    draw_alignment(draw)
    draw_timing(draw)

def scan_ok(img):
    results = pyzbar_decode(img)
    for r in results:
        if r.data == b"https://querystory.ai":
            return True
    return False

def save_and_check(img, name):
    path = f"/home/shapor/src/qs/live-mode/qr-variants/{name}.png"
    img.save(path, "PNG")
    ok = scan_ok(img)
    print(f"{name}: {'SCAN' if ok else 'FAIL'}")
    return ok


# ============================================================
# H01: Circles near S, squares far away
# ============================================================
def gen_h01():
    img, draw = new_image()
    draw_base(draw)
    threshold = 3.0  # modules within this distance get circles
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            x, y = mod_xy(r, c)
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            s = SCALE - 2
            if d < threshold:
                # Circle
                draw.ellipse([cx - s//2, cy - s//2, cx + s//2, cy + s//2], fill="#1a1a2e")
            else:
                # Square
                draw.rectangle([x + 1, y + 1, x + SCALE - 2, y + SCALE - 2], fill="#1a1a2e")
    save_and_check(img, "H01")

# ============================================================
# H02: Size modulation - larger near S, smaller far
# ============================================================
def gen_h02():
    img, draw = new_image()
    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            # Size: 0.95 at d=0, 0.45 at d=max_dist
            frac = 0.95 - 0.5 * min(d / 8.0, 1.0)
            half = int(SCALE * frac / 2)
            draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H02")

# ============================================================
# H03: Color gradient - bright blue near S, dark navy far
# ============================================================
def gen_h03():
    img, draw = new_image()
    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            t = min(d / 8.0, 1.0)
            # Near S: bright blue (70, 130, 255), far: dark navy (20, 20, 50)
            r_c = int(70 * (1 - t) + 20 * t)
            g_c = int(130 * (1 - t) + 20 * t)
            b_c = int(255 * (1 - t) + 50 * t)
            s = SCALE - 2
            draw.ellipse([cx - s//2, cy - s//2, cx + s//2, cy + s//2], fill=(r_c, g_c, b_c))
    save_and_check(img, "H03")

# ============================================================
# H04: Combined - large bright circles near S, small dark squares far
# ============================================================
def gen_h04():
    img, draw = new_image()
    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            t = min(d / 7.0, 1.0)
            # Size
            frac = 0.95 - 0.45 * t
            half = int(SCALE * frac / 2)
            # Color
            r_c = int(50 * (1 - t) + 26 * t)
            g_c = int(120 * (1 - t) + 26 * t)
            b_c = int(240 * (1 - t) + 46 * t)
            color = (r_c, g_c, b_c)
            if t < 0.4:
                draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill=color)
            else:
                draw.rectangle([cx - half, cy - half, cx + half, cy + half], fill=color)
    save_and_check(img, "H04")

# ============================================================
# H05: S-curve line behind + size modulation reinforcing
# ============================================================
def gen_h05():
    img, draw = new_image()
    # Draw subtle S-curve line first
    pts = []
    for seg in BEZIER_SEGMENTS:
        for i in range(50):
            t = i / 49.0
            px, py = cubic_bezier(seg[0], seg[1], seg[2], seg[3], t)
            mx, my = logo_to_mod(px, py)
            pts.append(((PAD + mx) * SCALE, (PAD + my) * SCALE))
    # Draw S as subtle wide line
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=(200, 210, 240), width=int(SCALE * 0.8))
    # White background for non-dark modules
    for r in range(MOD):
        for c in range(MOD):
            if not matrix[r][c] and not is_function_pattern(r, c):
                x, y = mod_xy(r, c)
                draw.rectangle([x, y, x + SCALE - 1, y + SCALE - 1], fill="white")
    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            frac = 0.92 - 0.4 * min(d / 7.0, 1.0)
            half = int(SCALE * frac / 2)
            draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H05")

# ============================================================
# H06: Diamonds on S-curve, circles elsewhere
# ============================================================
def gen_h06():
    img, draw = new_image()
    draw_base(draw)
    threshold = 2.5
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            s = SCALE - 2
            half = s // 2
            if d < threshold:
                # Diamond
                draw.polygon([(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)],
                             fill="#2a4494")
            else:
                draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H06")

# ============================================================
# H07: Stars near S-curve, plain circles elsewhere
# ============================================================
def gen_h07():
    img, draw = new_image()
    draw_base(draw)
    threshold = 3.0

    def star_points(cx, cy, outer, inner, n=5):
        pts = []
        for i in range(2 * n):
            angle = math.pi / 2 + i * math.pi / n
            rad = outer if i % 2 == 0 else inner
            pts.append((cx + rad * math.cos(angle), cy - rad * math.sin(angle)))
        return pts

    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            half = (SCALE - 2) // 2
            if d < threshold:
                pts = star_points(cx, cy, half, half * 0.4, 5)
                draw.polygon(pts, fill="#3355aa")
            else:
                draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H07")

# ============================================================
# H08: Inverted size - smaller near S creating a channel/gap
# ============================================================
def gen_h08():
    img, draw = new_image()
    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            # Inverted: small near S, large far
            t = min(d / 5.0, 1.0)
            frac = 0.40 + 0.55 * t  # 0.40 near, 0.95 far
            half = int(SCALE * frac / 2)
            draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H08")

# ============================================================
# H09: Grid lines visible + S-curve through size - both logo elements
# ============================================================
def gen_h09():
    img, draw = new_image()
    # Draw faint grid lines at logo boundaries (module ~14.5 = row/col between 14 and 15)
    # The logo grid spans 15-45 in logo coords, mapping to ~0-29 in modules
    # Grid cross at center: row 14.5, col 14.5 (center of 29x29)
    grid_r, grid_c = 14, 14  # approximate
    # Draw subtle grid lines
    for i in range(MOD + 2 * PAD):
        px = (PAD + grid_c) * SCALE + SCALE // 2
        py = i * SCALE + SCALE // 2
        # Vertical line at col 14.5
        draw.line([(px + SCALE//2, 0), (px + SCALE//2, img_size())], fill=(230, 230, 240), width=2)
        # Horizontal line at row 14.5
        draw.line([(0, px + SCALE//2), (img_size(), px + SCALE//2)], fill=(230, 230, 240), width=2)

    draw_base(draw)
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            # Also consider distance to grid lines
            grid_dist = min(abs(r - 14.5), abs(c - 14.5))
            combined = min(d, grid_dist * 1.5)
            t = min(combined / 6.0, 1.0)
            frac = 0.95 - 0.45 * t
            half = int(SCALE * frac / 2)
            r_c = int(60 * (1 - t) + 26 * t)
            g_c = int(100 * (1 - t) + 26 * t)
            b_c = int(220 * (1 - t) + 46 * t)
            draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill=(r_c, g_c, b_c))
    save_and_check(img, "H09")

# ============================================================
# H10: Donut/ring shapes near S, solid circles far
# ============================================================
def gen_h10():
    img, draw = new_image()
    draw_base(draw)
    threshold = 3.0
    for r in range(MOD):
        for c in range(MOD):
            if is_function_pattern(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = mod_center(r, c)
            d = dist_map[r][c]
            half = (SCALE - 2) // 2
            if d < threshold:
                # Donut: outer circle dark, small inner hole
                draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#2a4494")
                inner = int(half * 0.3)
                draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill="white")
            else:
                draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill="#1a1a2e")
    save_and_check(img, "H10")

# --- Generate all ---
if __name__ == "__main__":
    gen_h01()
    gen_h02()
    gen_h03()
    gen_h04()
    gen_h05()
    gen_h06()
    gen_h07()
    gen_h08()
    gen_h09()
    gen_h10()
    print("Done!")
