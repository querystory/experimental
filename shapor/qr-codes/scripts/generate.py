#!/usr/bin/env python3
"""Generate 10 QR code variants with S-curve extending beyond the QR boundary."""

import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import qrcode
from pyzbar.pyzbar import decode as pyzbar_decode

# --- QR Setup ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
size = len(matrix)  # 29

MOD = 20  # pixels per module
PAD = 2 * MOD  # padding on left/top
EXTRA_RIGHT = 5 * MOD  # extra space for S to extend right
EXTRA_BOTTOM = 5 * MOD  # extra space for S to extend bottom

# Canvas size
W = PAD + size * MOD + EXTRA_RIGHT + PAD
H = PAD + size * MOD + EXTRA_BOTTOM + PAD

# QR data area origin
QR_X0 = PAD
QR_Y0 = PAD
QR_SIZE = size * MOD  # 29*20 = 580

# --- S-curve bezier mapping ---
# Logo SVG path: M45,30 C40,30 35,34 37,36 C39,38 44,38 47,41 C50,44 47,48 42,48 C37,48 35,44 37,42
# Logo coord space: 15-45 (30 units)
# We map logo X [15..45] -> pixel [QR_X0 .. QR_X0 + QR_SIZE + 3*MOD]  (extends past QR)
# We map logo Y [15..45] -> pixel [QR_Y0 .. QR_Y0 + QR_SIZE + 3*MOD]  (extends past QR)

def logo_to_pixel(lx, ly, scale_extra=3):
    """Map logo coordinates to pixel coordinates, with extension beyond QR."""
    total = QR_SIZE + scale_extra * MOD
    px = QR_X0 + (lx - 15) / 30.0 * total
    py = QR_Y0 + (ly - 15) / 30.0 * total
    return px, py


def cubic_bezier(p0, p1, p2, p3, t):
    """Evaluate cubic bezier at parameter t."""
    u = 1 - t
    return (u**3 * p0[0] + 3*u**2*t * p1[0] + 3*u*t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3*u**2*t * p1[1] + 3*u*t**2 * p2[1] + t**3 * p3[1])


def get_s_curve_points(scale_extra=3, num_points=200):
    """Get the S-curve as a list of (x, y) pixel points."""
    # The 4 cubic bezier segments from the SVG path
    segments = [
        ((45, 30), (40, 30), (35, 34), (37, 36)),
        ((37, 36), (39, 38), (44, 38), (47, 41)),
        ((47, 41), (50, 44), (47, 48), (42, 48)),
        ((42, 48), (37, 48), (35, 44), (37, 42)),
    ]
    points = []
    for seg in segments:
        p0 = logo_to_pixel(*seg[0], scale_extra)
        p1 = logo_to_pixel(*seg[1], scale_extra)
        p2 = logo_to_pixel(*seg[2], scale_extra)
        p3 = logo_to_pixel(*seg[3], scale_extra)
        for i in range(num_points):
            t = i / num_points
            points.append(cubic_bezier(p0, p1, p2, p3, t))
    # Add final point
    last_seg = segments[-1]
    points.append(logo_to_pixel(*last_seg[3], scale_extra))
    return points


def draw_s_curve(draw, color=(0, 100, 200), width=8, scale_extra=3):
    """Draw the S-curve on the image."""
    pts = get_s_curve_points(scale_extra)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)


def draw_s_curve_fading(draw, color_start=(0, 100, 200), width=8, scale_extra=3):
    """Draw S-curve that fades as it exits the QR boundary."""
    pts = get_s_curve_points(scale_extra)
    qr_right = QR_X0 + QR_SIZE
    qr_bottom = QR_Y0 + QR_SIZE
    for i in range(len(pts) - 1):
        x, y = pts[i]
        # Calculate how far outside QR we are
        dx = max(0, x - qr_right) / (EXTRA_RIGHT)
        dy = max(0, y - qr_bottom) / (EXTRA_BOTTOM)
        fade = max(dx, dy)
        fade = min(1.0, fade)
        alpha = int(255 * (1 - fade))
        c = (*color_start, alpha)
        draw.line([pts[i], pts[i+1]], fill=c, width=width)


def draw_s_curve_with_dots(draw, color=(0, 100, 200), dot_radius=4, spacing=8, scale_extra=3):
    """Draw the S-curve as a series of dots (continuing the QR dot pattern)."""
    pts = get_s_curve_points(scale_extra)
    for i in range(0, len(pts), spacing):
        x, y = pts[i]
        draw.ellipse([x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius], fill=color)


# --- Finder patterns ---
FINDER_POSITIONS = [(0, 0), (size - 7, 0), (0, size - 7)]


def is_finder_module(r, c):
    """Check if module (r, c) is part of a finder pattern."""
    for fr, fc in FINDER_POSITIONS:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return True
    return False


def is_finder_center(r, c):
    """Check if module is in the 3x3 center of a finder."""
    for fr, fc in FINDER_POSITIONS:
        if fr + 2 <= r <= fr + 4 and fc + 2 <= c <= fc + 4:
            return True
    return False


def draw_standard_finders(draw, fg=(0, 0, 0)):
    """Draw standard 7x7 finder patterns as solid squares."""
    for fr, fc in FINDER_POSITIONS:
        for r in range(7):
            for c in range(7):
                x = QR_X0 + (fc + c) * MOD
                y = QR_Y0 + (fr + r) * MOD
                if matrix[fr + r][fc + c]:
                    draw.rectangle([x, y, x + MOD - 1, y + MOD - 1], fill=fg)


def draw_mini_qs_logo(draw, cx, cy, block_size):
    """Draw a tiny QS logo (grid + dots + S) in white centered at (cx, cy) over block_size x block_size area."""
    # White background for the center
    half = block_size // 2
    # Draw tiny S-curve in white
    # Scale the S to fit in the center block
    mini_segments = [
        ((45, 30), (40, 30), (35, 34), (37, 36)),
        ((37, 36), (39, 38), (44, 38), (47, 41)),
        ((47, 41), (50, 44), (47, 48), (42, 48)),
        ((42, 48), (37, 48), (35, 44), (37, 42)),
    ]
    def mini_map(lx, ly):
        px = cx - half + (lx - 15) / 30.0 * block_size
        py = cy - half + (ly - 15) / 30.0 * block_size
        return px, py

    pts = []
    for seg in mini_segments:
        p0 = mini_map(*seg[0])
        p1 = mini_map(*seg[1])
        p2 = mini_map(*seg[2])
        p3 = mini_map(*seg[3])
        for i in range(30):
            t = i / 30
            pts.append(cubic_bezier(p0, p1, p2, p3, t))
    pts.append(mini_map(*mini_segments[-1][3]))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=(255, 255, 255), width=max(1, block_size // 15))


def draw_etched_finders(draw, fg=(0, 0, 0)):
    """Draw finder patterns with tiny QS logo etched into the 3x3 center."""
    # First draw all finder modules as solid squares
    draw_standard_finders(draw, fg)
    # Then etch mini logo into each finder center
    for fr, fc in FINDER_POSITIONS:
        cx = QR_X0 + (fc + 3) * MOD + MOD // 2
        cy = QR_Y0 + (fr + 3) * MOD + MOD // 2
        draw_mini_qs_logo(draw, cx, cy, 3 * MOD)


def draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=False):
    """Draw data modules as circles."""
    r_px = MOD * 0.42  # slightly smaller than half-module for gaps
    for r in range(size):
        for c in range(size):
            if skip_finders and is_finder_module(r, c):
                continue
            if matrix[r][c]:
                cx = QR_X0 + c * MOD + MOD / 2
                cy = QR_Y0 + r * MOD + MOD / 2
                draw.ellipse([cx - r_px, cy - r_px, cx + r_px, cy + r_px], fill=fg)


def draw_square_modules(draw, fg=(0, 0, 0), skip_finders=False):
    """Draw data modules as squares."""
    for r in range(size):
        for c in range(size):
            if skip_finders and is_finder_module(r, c):
                continue
            if matrix[r][c]:
                x = QR_X0 + c * MOD
                y = QR_Y0 + r * MOD
                draw.rectangle([x, y, x + MOD - 1, y + MOD - 1], fill=fg)


def new_canvas(bg=(255, 255, 255)):
    """Create a fresh RGBA canvas."""
    return Image.new("RGBA", (W, H), (*bg, 255))


def scan_test(img, name):
    """Test if QR scans correctly."""
    # Convert to grayscale for scanning
    gray = img.convert("L")
    results = pyzbar_decode(gray)
    if results and any(r.data.decode() == "https://querystory.ai" for r in results):
        print(f"SCAN  {name}")
        return True
    else:
        print(f"FAIL  {name}")
        return False


def save_and_test(img, name):
    """Save PNG and test scanning."""
    path = f"/home/shapor/src/qs/live-mode/qr-variants/{name}.png"
    # Convert RGBA to RGB for saving
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    rgb.paste(img, mask=img.split()[3])
    rgb.save(path)
    scan_test(rgb, name)


# ============================================================
# F01: Basic S-curve behind, circle dots, standard finders
# ============================================================
def gen_f01():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(0, 120, 220, 80), width=12, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_standard_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F01")

# ============================================================
# F02: Thick S-curve, circle dots, etched finders
# ============================================================
def gen_f02():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(0, 100, 200, 60), width=20, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_etched_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F02")

# ============================================================
# F03: S-curve with glow/shadow effect
# ============================================================
def gen_f03():
    img = new_canvas()
    # Draw glow layer
    glow_layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    draw_s_curve(glow_draw, color=(0, 120, 255, 40), width=30, scale_extra=4)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, glow_layer)
    # Draw S again sharper on top
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(0, 100, 200, 100), width=10, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_standard_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F03")

# ============================================================
# F04: Fading S-curve that fades as it exits QR boundary
# ============================================================
def gen_f04():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve_fading(draw, color_start=(0, 100, 200), width=12, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_standard_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F04")

# ============================================================
# F05: S-curve in teal/green, circle dots, etched finders
# ============================================================
def gen_f05():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(0, 180, 140, 80), width=14, scale_extra=4)
    draw_circle_modules(draw, fg=(20, 20, 20), skip_finders=True)
    draw_etched_finders(draw, fg=(20, 20, 20))
    save_and_test(img, "F05")

# ============================================================
# F06: S as dotted pattern (continuing QR dot style)
# ============================================================
def gen_f06():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve_with_dots(draw, color=(0, 100, 200, 180), dot_radius=MOD * 0.42, spacing=5, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_standard_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F06")

# ============================================================
# F07: Thin elegant S-curve in purple, etched finders
# ============================================================
def gen_f07():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(100, 40, 180, 90), width=6, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_etched_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F07")

# ============================================================
# F08: Double S-curve (S + shadow offset), circle dots
# ============================================================
def gen_f08():
    img = new_canvas()
    # Shadow S (offset)
    shadow_layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    # Shift shadow by drawing with offset
    pts = get_s_curve_points(scale_extra=4)
    offset = 6
    for i in range(len(pts) - 1):
        shadow_draw.line([(pts[i][0] + offset, pts[i][1] + offset),
                          (pts[i+1][0] + offset, pts[i+1][1] + offset)],
                         fill=(0, 0, 0, 30), width=14)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, shadow_layer)
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(0, 100, 200, 100), width=10, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_standard_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F08")

# ============================================================
# F09: S-curve in warm orange/red, thick, with glow, etched finders
# ============================================================
def gen_f09():
    img = new_canvas()
    glow_layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    draw_s_curve(glow_draw, color=(220, 80, 20, 40), width=28, scale_extra=4)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)
    draw_s_curve(draw, color=(200, 60, 10, 110), width=12, scale_extra=4)
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_etched_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F09")

# ============================================================
# F10: S-curve gradient (blue to teal), fading out, dot S beyond QR, etched finders
# ============================================================
def gen_f10():
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    pts = get_s_curve_points(scale_extra=4)
    n = len(pts)
    qr_right = QR_X0 + QR_SIZE
    qr_bottom = QR_Y0 + QR_SIZE
    for i in range(n - 1):
        t = i / n
        # Color gradient: blue -> teal
        r_c = int(0 * (1 - t) + 0 * t)
        g_c = int(80 * (1 - t) + 180 * t)
        b_c = int(220 * (1 - t) + 150 * t)
        # Fade outside QR
        x, y = pts[i]
        dx = max(0, x - qr_right) / EXTRA_RIGHT
        dy = max(0, y - qr_bottom) / EXTRA_BOTTOM
        fade = min(1.0, max(dx, dy))
        alpha = int(120 * (1 - fade))
        draw.line([pts[i], pts[i+1]], fill=(r_c, g_c, b_c, alpha), width=10)
    # Dot pattern along S outside QR boundary
    for i in range(0, n, 6):
        x, y = pts[i]
        if x > qr_right or y > qr_bottom:
            dr = MOD * 0.35
            draw.ellipse([x - dr, y - dr, x + dr, y + dr], fill=(0, 140, 160, 150))
    draw_circle_modules(draw, fg=(0, 0, 0), skip_finders=True)
    draw_etched_finders(draw, fg=(0, 0, 0))
    save_and_test(img, "F10")


# --- Generate all ---
if __name__ == "__main__":
    gen_f01()
    gen_f02()
    gen_f03()
    gen_f04()
    gen_f05()
    gen_f06()
    gen_f07()
    gen_f08()
    gen_f09()
    gen_f10()
