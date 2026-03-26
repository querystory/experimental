#!/usr/bin/env python3
"""Generate QR code variants C01-C10: Size-modulated and density-modulated dots."""

import math
import qrcode
from PIL import Image, ImageDraw, ImageFilter
from pyzbar.pyzbar import decode as pyzbar_decode

# --- Constants ---
SUPERSAMPLE = 3
MOD = 36 * SUPERSAMPLE
PAD = 70 * SUPERSAMPLE
QS_BLUE = "#2563EB"
QS_BLUE_RGB = (37, 99, 235)
DARK_BLUE_RGB = (20, 50, 120)
NAVY_RGB = (15, 30, 80)
OUT = "qr-variants"

# --- QR Matrix ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)
CENTER = (N - 1) / 2.0
IMG_SIZE = N * MOD + 2 * PAD

# Size range: min_ratio to max_ratio. Wider = more visual drama, but risk scan failure.
# 0.5 to 1.05 is aggressive but with H error correction should work.
MIN_R = 0.5
MAX_R = 1.05


def is_finder(r, c):
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return True
    return False


def px(r, c):
    return PAD + c * MOD, PAD + r * MOD


def center_px(r, c):
    x, y = px(r, c)
    return x + MOD // 2, y + MOD // 2


def draw_etched_finders(draw, inner_color="black"):
    """Standard square finders with QS logo etched in white on 3x3 center."""
    for fr, fc in [(0, 0), (0, N - 7), (N - 7, 0)]:
        x0, y0 = px(fr, fc)
        s = 7 * MOD
        draw.rectangle([x0, y0, x0 + s - 1, y0 + s - 1], fill="black")
        draw.rectangle([x0 + MOD, y0 + MOD, x0 + 6 * MOD - 1, y0 + 6 * MOD - 1], fill="white")
        draw.rectangle([x0 + 2 * MOD, y0 + 2 * MOD, x0 + 5 * MOD - 1, y0 + 5 * MOD - 1], fill=inner_color)
        cx = x0 + 3 * MOD + MOD // 2
        cy = y0 + 3 * MOD + MOD // 2
        draw_qs_logo(draw, cx, cy, int(MOD * 1.8), "white")


def draw_qs_logo(draw, cx, cy, size, color):
    gap = size // 3
    dot_r = max(size // 12, 2)
    lw = max(size // 18, 1)
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            draw.ellipse([cx + dx * gap - dot_r, cy + dy * gap - dot_r,
                         cx + dx * gap + dot_r, cy + dy * gap + dot_r], fill=color)
    draw.line([cx - gap, cy - gap, cx + gap, cy - gap], fill=color, width=lw)
    draw.line([cx - gap, cy + gap, cx + gap, cy + gap], fill=color, width=lw)
    draw.line([cx - gap, cy - gap, cx - gap, cy + gap], fill=color, width=lw)
    draw.line([cx + gap, cy - gap, cx + gap, cy + gap], fill=color, width=lw)
    pts = []
    for t in range(20):
        frac = t / 19.0
        sx = cx - gap + frac * 2 * gap
        sy = cy + math.sin(frac * math.pi * 2 - math.pi / 2) * gap * 0.4
        pts.append((sx, sy))
    draw.line(pts, fill=color, width=lw)


def make_canvas():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "white")
    return img, ImageDraw.Draw(img)


def draw_sized_circle(draw, r, c, ratio, color="black"):
    """Draw circular module scaled by ratio. ratio=1.0 means full module minus small gap."""
    cx_px, cy_px = center_px(r, c)
    base_radius = (MOD - 2 * SUPERSAMPLE) / 2
    radius = base_radius * ratio
    if radius < 3:
        radius = 3
    draw.ellipse([cx_px - radius, cy_px - radius, cx_px + radius, cy_px + radius], fill=color)


def dist_to_center(r, c):
    return math.sqrt((r - CENTER) ** 2 + (c - CENTER) ** 2)


def s_curve_points(n=200):
    """S-curve points in module coordinate space."""
    pts_raw = [
        (45, 30), (40, 30), (35, 34), (37, 36),
        (37, 36), (39, 38), (44, 38), (47, 41),
        (47, 41), (50, 44), (47, 48), (42, 48),
        (42, 48), (37, 48), (35, 44), (37, 42),
    ]
    scale = N / 80.0
    points = []
    for seg in range(4):
        p0 = pts_raw[seg * 4]
        p1 = pts_raw[seg * 4 + 1]
        p2 = pts_raw[seg * 4 + 2]
        p3 = pts_raw[seg * 4 + 3]
        for t_i in range(n // 4):
            t = t_i / (n // 4 - 1)
            mt = 1 - t
            x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
            y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
            points.append((x * scale, y * scale))
    return points


def dist_to_s_curve(r, c, curve_pts):
    return min(math.sqrt((c - px_) ** 2 + (r - py) ** 2) for px_, py in curve_pts)


def dist_to_grid_lines(r, c):
    """Distance to nearest QS grid line (rows/cols at 0, N/2, N-1)."""
    min_d = float('inf')
    for i in range(3):
        line_pos = i * (N - 1) / 2.0
        min_d = min(min_d, abs(r - line_pos), abs(c - line_pos))
    return min_d


def lerp_ratio(t):
    """Map t in [0,1] to size ratio range."""
    return MIN_R + (MAX_R - MIN_R) * t


def blend_color(c1, c2, t):
    """Blend two RGB tuples. t=1 -> c1, t=0 -> c2."""
    return tuple(int(c1[i] * t + c2[i] * (1 - t)) for i in range(3))


def finish(img, name):
    """Downsample, save, scan."""
    final = IMG_SIZE // SUPERSAMPLE
    out = img.resize((final, final), Image.LANCZOS)
    path = f"{OUT}/{name}.png"
    out.save(path)
    results = pyzbar_decode(Image.open(path))
    status = "PASS" if any(r.data == b"https://querystory.ai" for r in results) else "FAIL"
    decoded = [r.data.decode() for r in results] if results else ["none"]
    print(f"  {name}: {status} (decoded: {decoded})")
    return status


# ============================================================
# C01: Radial gradient - larger in center, smaller at edges
# ============================================================
def gen_C01():
    print("C01: Radial center-large dots")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    max_dist = dist_to_center(0, 0)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_center(r, c)
                t = 1.0 - d / max_dist  # 1 at center, 0 at edge
                draw_sized_circle(draw, r, c, lerp_ratio(t), "black")
    return finish(img, "C01_radial_center_large")


# ============================================================
# C02: Inverse radial - larger at edges, smaller in center. Blue.
# ============================================================
def gen_C02():
    print("C02: Radial edge-large blue")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    max_dist = dist_to_center(0, 0)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_center(r, c)
                t = d / max_dist  # 0 at center, 1 at edge
                draw_sized_circle(draw, r, c, lerp_ratio(t), QS_BLUE)
    return finish(img, "C02_radial_edge_large")


# ============================================================
# C03: S-curve emerges from size modulation - near curve = bigger dots
# ============================================================
def gen_C03():
    print("C03: S-curve size emergence")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    curve_pts = s_curve_points()
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_s_curve(r, c, curve_pts)
                t = math.exp(-d * 0.25)  # 1 near curve, 0 far
                draw_sized_circle(draw, r, c, lerp_ratio(t), "black")
    return finish(img, "C03_scurve_size")


# ============================================================
# C04: S-curve size + color. Near S = large blue, far = smaller black
# ============================================================
def gen_C04():
    print("C04: S-curve size+color")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    curve_pts = s_curve_points()
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_s_curve(r, c, curve_pts)
                t = math.exp(-d * 0.25)
                color = blend_color(QS_BLUE_RGB, (0, 0, 0), t)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C04_scurve_size_color")


# ============================================================
# C05: Grid pattern emerges from size modulation
# ============================================================
def gen_C05():
    print("C05: Grid lines emergence")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_grid_lines(r, c)
                t = math.exp(-d * 0.35)
                color = blend_color(QS_BLUE_RGB, (0, 0, 0), t)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C05_grid_emergence")


# ============================================================
# C06: Horizontal sine waves modulate dot size
# ============================================================
def gen_C06():
    print("C06: Horizontal sine waves")
    img, draw = make_canvas()
    draw_etched_finders(draw)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                t = 0.5 + 0.5 * math.sin(2 * math.pi * r / 7)
                draw_sized_circle(draw, r, c, lerp_ratio(t), "black")
    return finish(img, "C06_horiz_sine")


# ============================================================
# C07: Diagonal wave with blue gradient
# ============================================================
def gen_C07():
    print("C07: Diagonal waves blue gradient")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                t = 0.5 + 0.5 * math.sin(2 * math.pi * (r + c) / 10)
                pos_t = (r + c) / (2 * (N - 1))
                color = blend_color(QS_BLUE_RGB, DARK_BLUE_RGB, pos_t)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C07_diag_wave_blue")


# ============================================================
# C08: S-curve + radial combined - two visual layers
# ============================================================
def gen_C08():
    print("C08: S-curve + radial combined")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    curve_pts = s_curve_points()
    max_dist = dist_to_center(0, 0)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d_s = dist_to_s_curve(r, c, curve_pts)
                d_c = dist_to_center(r, c)
                s_t = math.exp(-d_s * 0.25)
                c_t = 1.0 - d_c / max_dist
                t = 0.6 * s_t + 0.4 * c_t  # weighted blend
                color = blend_color(QS_BLUE_RGB, (0, 0, 0), s_t)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C08_scurve_radial")


# ============================================================
# C09: Concentric rings - dot size oscillates with distance
# ============================================================
def gen_C09():
    print("C09: Concentric rings")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d = dist_to_center(r, c)
                t = 0.5 + 0.5 * math.sin(2 * math.pi * d / 5)
                color = blend_color(QS_BLUE_RGB, NAVY_RGB, t)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C09_concentric_rings")


# ============================================================
# C10: S-curve + grid dual modulation - both logo elements emerge
# ============================================================
def gen_C10():
    print("C10: S-curve + grid dual modulation")
    img, draw = make_canvas()
    draw_etched_finders(draw, inner_color=QS_BLUE)
    curve_pts = s_curve_points()
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if matrix[r][c]:
                d_s = dist_to_s_curve(r, c, curve_pts)
                d_g = dist_to_grid_lines(r, c)
                s_t = math.exp(-d_s * 0.25)
                g_t = math.exp(-d_g * 0.3)
                t = max(s_t, g_t)  # either feature enlarges dots
                if s_t > g_t:
                    color = QS_BLUE
                else:
                    color = blend_color(QS_BLUE_RGB, DARK_BLUE_RGB, 0.5)
                draw_sized_circle(draw, r, c, lerp_ratio(t), color)
    return finish(img, "C10_scurve_grid_dual")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print(f"QR: {N}x{N}, MOD={MOD}px, size range={MIN_R:.2f}-{MAX_R:.2f}\n")
    results = []
    for gen in [gen_C01, gen_C02, gen_C03, gen_C04, gen_C05,
                gen_C06, gen_C07, gen_C08, gen_C09, gen_C10]:
        results.append(gen())
    passes = results.count("PASS")
    fails = results.count("FAIL")
    print(f"\nResults: {passes} PASS, {fails} FAIL")
