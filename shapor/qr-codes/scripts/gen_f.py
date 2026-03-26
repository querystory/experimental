#!/usr/bin/env python3
"""Generate QR code variants with S-curve extending beyond QR boundary."""

import qrcode
from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode as pyzbar_decode
import os

OUT_DIR = "/home/shapor/src/qs/live-mode/qr-variants"
os.makedirs(OUT_DIR, exist_ok=True)

SUPERSAMPLE = 3
MODULE_SIZE = 36 * SUPERSAMPLE
PADDING = 70 * SUPERSAMPLE

QS_BLUE = "#2563EB"
QS_BLUE_RGB = (37, 99, 235)
WHITE = "#FFFFFF"
BLACK = "#000000"

# Generate QR matrix
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)  # 29 for version 3


def cubic_bezier(p0, p1, p2, p3, steps=50):
    """Evaluate cubic bezier curve, return list of (x,y) points."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def draw_modules(draw, ms, pad, color=BLACK, rounded=False):
    """Draw all QR data modules."""
    draw_modules_xy(draw, ms, pad, pad, color, rounded)


def draw_modules_xy(draw, ms, pad_x, pad_y, color=BLACK, rounded=False):
    """Draw all QR data modules with separate x/y padding."""
    for r in range(N):
        for c in range(N):
            if matrix[r][c]:
                x = pad_x + c * ms
                y = pad_y + r * ms
                if rounded:
                    rr = ms * 0.3
                    draw.rounded_rectangle([x, y, x + ms, y + ms], radius=rr, fill=color)
                else:
                    draw.rectangle([x, y, x + ms, y + ms], fill=color)


def draw_thick_curve(draw, pts, width, color):
    """Draw a curve from a list of points with given width."""
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=width)


def draw_tapered_curve(draw, pts, start_width, end_width, color):
    """Draw a curve that tapers from start_width to end_width."""
    n = len(pts)
    for i in range(n - 1):
        t = i / max(1, n - 2)
        w = int(start_width + (end_width - start_width) * t)
        draw.line([pts[i], pts[i + 1]], fill=color, width=max(1, w))


def draw_fading_curve(draw, pts, width, base_color, start_alpha=255, end_alpha=0):
    """Draw curve with fading alpha (on RGBA image)."""
    n = len(pts)
    for i in range(n - 1):
        t = i / max(1, n - 2)
        alpha = int(start_alpha + (end_alpha - start_alpha) * t)
        w = max(1, int(width * (1.0 - t * 0.5)))
        color = (*base_color, alpha)
        draw.line([pts[i], pts[i + 1]], fill=color, width=w)


def scan_qr(img_path):
    """Scan QR with pyzbar, return decoded text or None."""
    img = Image.open(img_path)
    results = pyzbar_decode(img)
    if results:
        return results[0].data.decode("utf-8")
    return None


def finalize(img, path, label):
    """Downsample 3x and save, then scan."""
    w, h = img.size
    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    final = img.resize((w // SUPERSAMPLE, h // SUPERSAMPLE), Image.LANCZOS)
    final.save(path)
    result = scan_qr(path)
    status = "SCAN" if result == "https://querystory.ai" else "FAIL"
    print(f"{label}: {status} ({result})")
    return status


# ==============================================================================
# Variant A01: S-curve flowing out from bottom-right corner, tapering
# ==============================================================================
def gen_a01():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(8 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + extra

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    # S-curve BEHIND QR, from inside bottom-right flowing out
    qr_r = pad + qr_size
    qr_b = pad + qr_size
    start_x = qr_r - 6 * ms
    start_y = qr_b - 6 * ms

    pts = []
    pts.extend(cubic_bezier(
        (start_x, start_y),
        (start_x + 5 * ms, start_y - 2 * ms),
        (qr_r - 2 * ms, qr_b + ms),
        (qr_r + ms, qr_b + ms),
        80
    ))
    pts.extend(cubic_bezier(
        (qr_r + ms, qr_b + ms),
        (qr_r + 4 * ms, qr_b + ms),
        (qr_r + 3 * ms, qr_b + 5 * ms),
        (qr_r + 6 * ms, qr_b + 6 * ms),
        80
    ))

    sw = int(ms * 1.3)
    draw_tapered_curve(draw, pts, sw, int(sw * 0.2), QS_BLUE)

    # QR on top
    draw_modules(draw, ms, pad, BLACK, rounded=True)

    return finalize(img, os.path.join(OUT_DIR, "A01_scurve_breakout_br.png"), "A01")


# ==============================================================================
# Variant A02: S-curve wrapping around right edge
# ==============================================================================
def gen_a02():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(7 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    qr_r = pad + qr_size
    mid_y = pad + qr_size // 2

    # S wrapping along right edge
    pts = []
    pts.extend(cubic_bezier(
        (qr_r - 3 * ms, pad + 3 * ms),
        (qr_r + 4 * ms, pad - ms),
        (qr_r + 5 * ms, mid_y - 2 * ms),
        (qr_r + 2 * ms, mid_y),
        80
    ))
    pts.extend(cubic_bezier(
        (qr_r + 2 * ms, mid_y),
        (qr_r - ms, mid_y + 2 * ms),
        (qr_r + 5 * ms, pad + qr_size - 3 * ms),
        (qr_r - 3 * ms, pad + qr_size - 2 * ms),
        80
    ))

    sw = int(ms * 1.0)
    draw_thick_curve(draw, pts, sw, QS_BLUE)

    draw_modules(draw, ms, pad)

    return finalize(img, os.path.join(OUT_DIR, "A02_scurve_wrap_right.png"), "A02")


# ==============================================================================
# Variant A03: QR sits inside a large decorative S-curve
# ==============================================================================
def gen_a03():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    border = int(10 * ms)
    total = qr_size + 2 * pad + 2 * border
    qr_pad = pad + border

    img = Image.new("RGB", (total, total), WHITE)
    draw = ImageDraw.Draw(img)

    # Large decorative S that the QR sits within
    pts = []
    pts.extend(cubic_bezier(
        (border * 0.3, border * 0.2),
        (total * 0.7, -border * 0.3),
        (total * 0.9, total * 0.35),
        (total * 0.5, total * 0.5),
        100
    ))
    pts.extend(cubic_bezier(
        (total * 0.5, total * 0.5),
        (total * 0.1, total * 0.65),
        (total * 0.3, total * 1.05),
        (total * 0.9, total * 0.85),
        100
    ))

    # Draw wide soft band
    sw = int(ms * 3.0)
    draw_thick_curve(draw, pts, sw, "#DBEAFE")  # blue-100
    draw_thick_curve(draw, pts, int(sw * 0.15), QS_BLUE)

    # QR on top
    draw_modules(draw, ms, qr_pad)

    return finalize(img, os.path.join(OUT_DIR, "A03_scurve_decorative_bg.png"), "A03")


# ==============================================================================
# Variant A04: Elegant thin S-curve exiting right side
# ==============================================================================
def gen_a04():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(10 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + int(4 * ms)

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    qr_r = pad + qr_size
    qr_cy = pad + qr_size // 2

    pts = cubic_bezier(
        (qr_r - 4 * ms, qr_cy + 3 * ms),
        (qr_r + 3 * ms, qr_cy - ms),
        (qr_r + 6 * ms, qr_cy + 5 * ms),
        (qr_r + 8 * ms, qr_cy + 2 * ms),
        120
    )

    sw = int(ms * 0.5)
    draw_tapered_curve(draw, pts, sw, int(sw * 0.1), QS_BLUE)

    draw_modules(draw, ms, pad, rounded=True)

    return finalize(img, os.path.join(OUT_DIR, "A04_scurve_elegant_exit.png"), "A04")


# ==============================================================================
# Variant A05: Double S-curves exiting right and bottom
# ==============================================================================
def gen_a05():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(7 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + extra

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    qr_r = pad + qr_size
    qr_b = pad + qr_size

    # S-curve exiting right
    pts1 = cubic_bezier(
        (qr_r - 5 * ms, pad + 8 * ms),
        (qr_r + 3 * ms, pad + 5 * ms),
        (qr_r + 5 * ms, pad + 11 * ms),
        (qr_r + 4 * ms, pad + 15 * ms),
        80
    )
    sw = int(ms * 0.8)
    draw_thick_curve(draw, pts1, sw, QS_BLUE)

    # S-curve exiting bottom
    pts2 = cubic_bezier(
        (pad + 10 * ms, qr_b - 5 * ms),
        (pad + 6 * ms, qr_b + 3 * ms),
        (pad + 15 * ms, qr_b + 4 * ms),
        (pad + 20 * ms, qr_b + 5 * ms),
        80
    )
    draw_thick_curve(draw, pts2, sw, "#3B82F6")

    draw_modules(draw, ms, pad)

    return finalize(img, os.path.join(OUT_DIR, "A05_double_scurve_exit.png"), "A05")


# ==============================================================================
# Variant A06: Bold S-curve with fading opacity
# ==============================================================================
def gen_a06():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(9 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + extra

    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    qr_br_x = pad + qr_size
    qr_br_y = pad + qr_size

    pts = []
    pts.extend(cubic_bezier(
        (qr_br_x - 7 * ms, qr_br_y - 9 * ms),
        (qr_br_x + 3 * ms, qr_br_y - 9 * ms),
        (qr_br_x - 3 * ms, qr_br_y + 2 * ms),
        (qr_br_x + 2 * ms, qr_br_y + 2 * ms),
        80
    ))
    pts.extend(cubic_bezier(
        (qr_br_x + 2 * ms, qr_br_y + 2 * ms),
        (qr_br_x + 7 * ms, qr_br_y + 2 * ms),
        (qr_br_x + 5 * ms, qr_br_y + 7 * ms),
        (qr_br_x + 7 * ms, qr_br_y + 7 * ms),
        80
    ))

    sw = int(ms * 1.5)
    draw_fading_curve(draw, pts, sw, QS_BLUE_RGB, 255, 40)

    # QR modules (black on RGBA)
    draw_modules(draw, ms, pad, BLACK)

    return finalize(img, os.path.join(OUT_DIR, "A06_bold_scurve_fade.png"), "A06")


# ==============================================================================
# Variant A07: S-curve as thick band behind QR, extending both sides
# ==============================================================================
def gen_a07():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra_lr = int(8 * ms)
    w = qr_size + 2 * pad + 2 * extra_lr
    h = qr_size + 2 * pad

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    # S-curve band spanning full width
    cy = h // 2
    pts = []
    pts.extend(cubic_bezier(
        (0, cy - 4 * ms),
        (w * 0.25, cy - 7 * ms),
        (w * 0.35, cy + 5 * ms),
        (w * 0.5, cy + 2 * ms),
        80
    ))
    pts.extend(cubic_bezier(
        (w * 0.5, cy + 2 * ms),
        (w * 0.65, cy - ms),
        (w * 0.75, cy + 7 * ms),
        (w, cy + 3 * ms),
        80
    ))

    band_w = int(ms * 3)
    draw_thick_curve(draw, pts, band_w, "#DBEAFE")
    draw_thick_curve(draw, pts, int(band_w * 0.12), QS_BLUE)

    # QR centered: x offset for extra width, y uses normal padding
    draw_modules_xy(draw, ms, pad + extra_lr, pad)

    return finalize(img, os.path.join(OUT_DIR, "A07_scurve_band_behind.png"), "A07")


# ==============================================================================
# Variant A08: S-curve flowing down from QR bottom center with dot terminus
# ==============================================================================
def gen_a08():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra_bottom = int(10 * ms)
    w = qr_size + 2 * pad
    h = qr_size + 2 * pad + extra_bottom

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    cx = pad + qr_size // 2
    qr_b = pad + qr_size

    pts = cubic_bezier(
        (cx, qr_b - 2 * ms),
        (cx + 7 * ms, qr_b),
        (cx - 7 * ms, qr_b + 7 * ms),
        (cx, qr_b + extra_bottom - 2 * ms),
        120
    )

    sw = int(ms * 1.0)
    draw_tapered_curve(draw, pts, sw, int(sw * 0.3), QS_BLUE)

    # Dot at end
    ex, ey = pts[-1]
    r = int(ms * 0.7)
    draw.ellipse([ex - r, ey - r, ex + r, ey + r], fill=QS_BLUE)

    draw_modules(draw, ms, pad, rounded=True)

    return finalize(img, os.path.join(OUT_DIR, "A08_scurve_flow_down.png"), "A08")


# ==============================================================================
# Variant A09: S-curve arcing from bottom-left area out to bottom-right
# ==============================================================================
def gen_a09():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(8 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + extra

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    qr_r = pad + qr_size
    qr_b = pad + qr_size

    pts = cubic_bezier(
        (pad + 4 * ms, qr_b - 3 * ms),
        (pad + 15 * ms, qr_b + 4 * ms),
        (qr_r + 3 * ms, qr_b - 4 * ms),
        (qr_r + 6 * ms, qr_b + 6 * ms),
        100
    )

    sw = int(ms * 0.9)
    draw_tapered_curve(draw, pts, sw, int(sw * 0.15), QS_BLUE)

    draw_modules(draw, ms, pad)

    return finalize(img, os.path.join(OUT_DIR, "A09_scurve_arc_out.png"), "A09")


# ==============================================================================
# Variant A10: Multi-segment S weaving through and beyond, with glow
# ==============================================================================
def gen_a10():
    ms = MODULE_SIZE
    pad = PADDING
    qr_size = N * ms
    extra = int(8 * ms)
    w = qr_size + 2 * pad + extra
    h = qr_size + 2 * pad + extra

    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    # Multi-segment S behind QR
    pts = []
    pts.extend(cubic_bezier(
        (pad - 2 * ms, pad - 3 * ms),
        (pad + 10 * ms, pad - 2 * ms),
        (pad + 4 * ms, pad + 10 * ms),
        (pad + 15 * ms, pad + 13 * ms),
        60
    ))
    pts.extend(cubic_bezier(
        (pad + 15 * ms, pad + 13 * ms),
        (pad + 26 * ms, pad + 16 * ms),
        (pad + 8 * ms, pad + 23 * ms),
        (pad + 22 * ms, pad + 26 * ms),
        60
    ))
    qr_r = pad + qr_size
    qr_b = pad + qr_size
    pts.extend(cubic_bezier(
        (pad + 22 * ms, pad + 26 * ms),
        (pad + 32 * ms, pad + 28 * ms),
        (qr_r + 3 * ms, qr_b + 3 * ms),
        (qr_r + 6 * ms, qr_b + 6 * ms),
        60
    ))

    # Glow
    sw = int(ms * 0.7)
    draw_thick_curve(draw, pts, int(sw * 3), "#DBEAFE")
    draw_thick_curve(draw, pts, int(sw * 1.5), "#93C5FD")
    draw_thick_curve(draw, pts, sw, QS_BLUE)

    draw_modules(draw, ms, pad, rounded=True)

    return finalize(img, os.path.join(OUT_DIR, "A10_scurve_weave_glow.png"), "A10")


# ==============================================================================
# Generate all
# ==============================================================================
print(f"QR matrix size: {N}x{N}")
print(f"Module size: {MODULE_SIZE}px (supersample {SUPERSAMPLE}x)")
print(f"Output directory: {OUT_DIR}")
print()

results = {}
for name, fn in [
    ("A01", gen_a01), ("A02", gen_a02), ("A03", gen_a03), ("A04", gen_a04),
    ("A05", gen_a05), ("A06", gen_a06), ("A07", gen_a07), ("A08", gen_a08),
    ("A09", gen_a09), ("A10", gen_a10),
]:
    try:
        results[name] = fn()
    except Exception as e:
        print(f"{name}: ERROR - {e}")
        import traceback
        traceback.print_exc()
        results[name] = "ERROR"

print()
print("=" * 40)
print("SUMMARY")
print("=" * 40)
for name, status in results.items():
    print(f"  {name}: {status}")
