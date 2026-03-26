#!/usr/bin/env python3
"""Generate QR code variants E01-E10: Mixed module shapes and novel textures."""

import math
import random
import qrcode
from PIL import Image, ImageDraw, ImageFilter
from pyzbar.pyzbar import decode as pyzbar_decode

# --- Config ---
SUPERSAMPLE = 3
MOD = 36 * SUPERSAMPLE      # module size in pixels
PAD = 70 * SUPERSAMPLE      # padding
QS_BLUE = "#2563EB"
OUT_DIR = "qr-variants"

random.seed(42)

# --- Generate QR matrix ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)

# --- Helpers ---
def is_finder(r, c):
    """Check if (r,c) is within a finder pattern (7x7 corners)."""
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return True
    return False

def finder_origin(r, c):
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return (fr, fc)
    return None

def make_canvas():
    size = N * MOD + 2 * PAD
    img = Image.new("RGB", (size, size), "white")
    return img, ImageDraw.Draw(img)

def px(r, c):
    """Top-left pixel for module (r, c)."""
    return PAD + c * MOD, PAD + r * MOD

def center_px(r, c):
    x, y = px(r, c)
    return x + MOD // 2, y + MOD // 2

def draw_etched_finders(draw):
    """Draw standard square finders with QS logo etched in white on 3x3 center."""
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        x0, y0 = px(fr, fc)
        s = 7 * MOD
        # Outer black square
        draw.rectangle([x0, y0, x0 + s - 1, y0 + s - 1], fill="black")
        # White ring
        draw.rectangle([x0 + MOD, y0 + MOD, x0 + 6 * MOD - 1, y0 + 6 * MOD - 1], fill="white")
        # Inner black square
        draw.rectangle([x0 + 2 * MOD, y0 + 2 * MOD, x0 + 5 * MOD - 1, y0 + 5 * MOD - 1], fill="black")
        # Etch QS logo in white on the 3x3 center
        cx = x0 + 3 * MOD + MOD // 2
        cy = y0 + 3 * MOD + MOD // 2
        logo_size = int(MOD * 1.8)
        draw_qs_logo(draw, cx, cy, logo_size, "white")

def draw_qs_logo(draw, cx, cy, size, color):
    """Draw simplified QS logo: 2x2 grid with dots and S-curve."""
    r = size // 2
    gap = size // 3
    # 2x2 grid dots
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            dot_r = max(size // 12, 2)
            draw.ellipse([cx + dx * gap - dot_r, cy + dy * gap - dot_r,
                         cx + dx * gap + dot_r, cy + dy * gap + dot_r], fill=color)
    # Connecting lines
    lw = max(size // 18, 1)
    draw.line([cx - gap, cy - gap, cx + gap, cy - gap], fill=color, width=lw)
    draw.line([cx - gap, cy + gap, cx + gap, cy + gap], fill=color, width=lw)
    draw.line([cx - gap, cy - gap, cx - gap, cy + gap], fill=color, width=lw)
    draw.line([cx + gap, cy - gap, cx + gap, cy + gap], fill=color, width=lw)
    # S-curve (simplified as a sine wave)
    pts = []
    for t in range(20):
        frac = t / 19.0
        sx = cx - gap + frac * 2 * gap
        sy = cy + math.sin(frac * math.pi * 2 - math.pi / 2) * gap * 0.4
        pts.append((sx, sy))
    draw.line(pts, fill=color, width=lw)

def draw_module_square(draw, r, c, color="black", shrink=0):
    x, y = px(r, c)
    s = shrink
    draw.rectangle([x + s, y + s, x + MOD - 1 - s, y + MOD - 1 - s], fill=color)

def draw_module_circle(draw, r, c, color="black", shrink=2):
    x, y = px(r, c)
    s = shrink * SUPERSAMPLE
    draw.ellipse([x + s, y + s, x + MOD - 1 - s, y + MOD - 1 - s], fill=color)

def draw_module_diamond(draw, r, c, color="black", shrink=2):
    cx, cy = center_px(r, c)
    s = shrink * SUPERSAMPLE
    half = MOD // 2 - s
    draw.polygon([(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)], fill=color)

def draw_module_cross(draw, r, c, color="black"):
    x, y = px(r, c)
    arm = MOD // 4
    draw.rectangle([x + arm, y, x + MOD - 1 - arm, y + MOD - 1], fill=color)
    draw.rectangle([x, y + arm, x + MOD - 1, y + MOD - 1 - arm], fill=color)

def draw_module_triangle(draw, r, c, direction, color="black"):
    x, y = px(r, c)
    s = 2 * SUPERSAMPLE
    if direction == "up":
        draw.polygon([(x + MOD // 2, y + s), (x + MOD - 1 - s, y + MOD - 1 - s), (x + s, y + MOD - 1 - s)], fill=color)
    elif direction == "down":
        draw.polygon([(x + s, y + s), (x + MOD - 1 - s, y + s), (x + MOD // 2, y + MOD - 1 - s)], fill=color)
    elif direction == "left":
        draw.polygon([(x + MOD - 1 - s, y + s), (x + MOD - 1 - s, y + MOD - 1 - s), (x + s, y + MOD // 2)], fill=color)
    else:  # right
        draw.polygon([(x + s, y + s), (x + s, y + MOD - 1 - s), (x + MOD - 1 - s, y + MOD // 2)], fill=color)

def draw_module_hexagon(draw, r, c, color="black"):
    cx, cy = center_px(r, c)
    s = 2 * SUPERSAMPLE
    half = MOD // 2 - s
    pts = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        pts.append((cx + half * math.cos(angle), cy + half * math.sin(angle)))
    draw.polygon(pts, fill=color)

def draw_module_star(draw, r, c, color="black", points=4):
    cx, cy = center_px(r, c)
    s = 2 * SUPERSAMPLE
    outer = MOD // 2 - s
    inner = outer * 0.4
    pts = []
    for i in range(points * 2):
        angle = i * math.pi / points - math.pi / 2
        rad = outer if i % 2 == 0 else inner
        pts.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
    draw.polygon(pts, fill=color)

def draw_radial_line(draw, r, c, center_r, center_c, color="black"):
    """Draw a short line pointing toward (center_r, center_c)."""
    cx, cy = center_px(r, c)
    gcx, gcy = center_px(center_r, center_c)
    dx, dy = gcx - cx, gcy - cy
    dist = math.sqrt(dx * dx + dy * dy) or 1
    dx, dy = dx / dist, dy / dist
    half = MOD // 2 - 2 * SUPERSAMPLE
    lw = max(MOD // 4, 2)
    draw.line([cx - dx * half, cy - dy * half, cx + dx * half, cy + dy * half],
              fill=color, width=lw)

def finalize(img, name):
    """Downsample and save."""
    final_size = (N * 36 + 2 * 70)
    out = img.resize((final_size, final_size), Image.LANCZOS)
    path = f"{OUT_DIR}/{name}.png"
    out.save(path)
    # Scan
    results = pyzbar_decode(Image.open(path))
    status = "PASS" if any(r.data == b"https://querystory.ai" for r in results) else "FAIL"
    decoded = [r.data.decode() for r in results] if results else ["none"]
    print(f"  {name}: {status} (decoded: {decoded})")
    return status


# ============================================================
# E01: Horizontal barcode lines
# ============================================================
def gen_e01():
    print("E01: Horizontal barcode lines")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    line_h = max(MOD * 2 // 3, 2)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                x, y = px(r, c)
                # Draw horizontal line spanning the module width
                cy = y + MOD // 2
                draw.rectangle([x, cy - line_h // 2, x + MOD - 1, cy + line_h // 2], fill="black")
    finalize(img, "E01_barcode_lines")


# ============================================================
# E02: Quadrant shapes - circles, squares, diamonds, hexagons
# ============================================================
def gen_e02():
    print("E02: Quadrant mixed shapes")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N // 2, N // 2
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            if r < mid_r and c < mid_c:
                draw_module_circle(draw, r, c)
            elif r < mid_r and c >= mid_c:
                draw_module_square(draw, r, c, shrink=2 * SUPERSAMPLE)
            elif r >= mid_r and c < mid_c:
                draw_module_hexagon(draw, r, c)
            else:
                draw_module_diamond(draw, r, c)
    finalize(img, "E02_quadrant_shapes")


# ============================================================
# E03: Concentric rings from center
# ============================================================
def gen_e03():
    print("E03: Concentric rings")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N / 2.0, N / 2.0
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            dist = math.sqrt((r - mid_r) ** 2 + (c - mid_c) ** 2)
            ring = int(dist) % 3
            if ring == 0:
                draw_module_circle(draw, r, c)
            elif ring == 1:
                draw_module_diamond(draw, r, c)
            else:
                draw_module_square(draw, r, c, shrink=3 * SUPERSAMPLE)
    finalize(img, "E03_concentric_rings")


# ============================================================
# E04: Random rotation - squares and diamonds mixed
# ============================================================
def gen_e04():
    print("E04: Random rotation squares/diamonds")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    random.seed(42)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            if random.random() < 0.4:
                draw_module_diamond(draw, r, c)
            else:
                draw_module_square(draw, r, c, shrink=2 * SUPERSAMPLE)
    finalize(img, "E04_random_rotation")


# ============================================================
# E05: Starburst/radial lines pointing to center
# ============================================================
def gen_e05():
    print("E05: Starburst radial")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N // 2, N // 2
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            draw_radial_line(draw, r, c, mid_r, mid_c)
    finalize(img, "E05_starburst_radial")


# ============================================================
# E06: Checkerboard overlay with dual colors
# ============================================================
def gen_e06():
    print("E06: Checkerboard overlay")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            on_checker = (r + c) % 2 == 0
            color = "#1a1a1a" if on_checker else "#444444"
            if on_checker:
                draw_module_circle(draw, r, c, color=color)
            else:
                draw_module_square(draw, r, c, shrink=3 * SUPERSAMPLE)
                # Add a lighter inner
                x, y = px(r, c)
                s = MOD // 4
                draw.rectangle([x + s, y + s, x + MOD - 1 - s, y + MOD - 1 - s], fill=color)
    finalize(img, "E06_checkerboard_overlay")


# ============================================================
# E07: Distance gradient - circles near center, squares at edges
# ============================================================
def gen_e07():
    print("E07: Distance gradient shapes")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N / 2.0, N / 2.0
    max_dist = math.sqrt(mid_r ** 2 + mid_c ** 2)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            dist = math.sqrt((r - mid_r) ** 2 + (c - mid_c) ** 2)
            frac = dist / max_dist
            if frac < 0.3:
                draw_module_circle(draw, r, c, shrink=1)
            elif frac < 0.6:
                # Rounded squares (circles with less shrink)
                draw_module_diamond(draw, r, c)
            else:
                draw_module_square(draw, r, c, shrink=2 * SUPERSAMPLE)
    finalize(img, "E07_distance_gradient")


# ============================================================
# E08: Cross shapes on grid lines, circles elsewhere
# ============================================================
def gen_e08():
    print("E08: Cross on grid, circles elsewhere")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N // 2, N // 2
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            # "Grid lines" = every 4th row/col
            on_grid = (r % 4 == 0) or (c % 4 == 0)
            if on_grid:
                draw_module_cross(draw, r, c)
            else:
                draw_module_circle(draw, r, c)
    finalize(img, "E08_cross_grid_circles")


# ============================================================
# E09: Triangles pointing in different directions based on position
# ============================================================
def gen_e09():
    print("E09: Directional triangles")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N / 2.0, N / 2.0
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            # Direction based on quadrant relative to center
            dr = r - mid_r
            dc = c - mid_c
            if abs(dr) > abs(dc):
                direction = "down" if dr > 0 else "up"
            else:
                direction = "right" if dc > 0 else "left"
            draw_module_triangle(draw, r, c, direction)
    finalize(img, "E09_directional_triangles")


# ============================================================
# E10: Stars + radial + checkerboard combo
# ============================================================
def gen_e10():
    print("E10: Stars + radial + hexagons combo")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    mid_r, mid_c = N / 2.0, N / 2.0
    max_dist = math.sqrt(mid_r ** 2 + mid_c ** 2)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c) or not matrix[r][c]:
                continue
            dist = math.sqrt((r - mid_r) ** 2 + (c - mid_c) ** 2)
            frac = dist / max_dist
            on_checker = (r + c) % 2 == 0
            if frac < 0.25:
                draw_module_star(draw, r, c, points=4)
            elif frac < 0.5:
                if on_checker:
                    draw_module_hexagon(draw, r, c)
                else:
                    draw_module_diamond(draw, r, c)
            elif frac < 0.75:
                draw_radial_line(draw, r, c, int(mid_r), int(mid_c), color="black")
            else:
                if on_checker:
                    draw_module_cross(draw, r, c)
                else:
                    draw_module_circle(draw, r, c)
    finalize(img, "E10_stars_radial_hex_combo")


# --- Run all ---
if __name__ == "__main__":
    gen_e01()
    gen_e02()
    gen_e03()
    gen_e04()
    gen_e05()
    gen_e06()
    gen_e07()
    gen_e08()
    gen_e09()
    gen_e10()
    print("\nDone! All variants saved to qr-variants/")
