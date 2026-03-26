#!/usr/bin/env python3
"""Generate B-series QR codes: Connected/flowing dots theme."""

import qrcode
from PIL import Image, ImageDraw, ImageFilter
from pyzbar.pyzbar import decode
import math

# --- Constants ---
SS = 3  # supersample factor
MOD = 36 * SS  # module size in pixels
PAD = 70 * SS  # padding
QS_BLUE = "#2563EB"
DARK_BLUE = "#1E40AF"
NAVY = "#1E3A5F"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F0F4F8"
NEAR_BLACK = "#1A1A2E"

# Generate QR matrix
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)  # 29 for version 3

IMG_SIZE = N * MOD + 2 * PAD


def is_finder(r, c):
    """Check if module is in a finder pattern region."""
    if r < 7 and c < 7:
        return True
    if r < 7 and c >= N - 7:
        return True
    if r >= N - 7 and c < 7:
        return True
    return False


def is_finder_center(r, c):
    """Check if module is in the 3x3 center of a finder."""
    centers = [(3, 3), (3, N - 4), (N - 4, 3)]
    for cr, cc in centers:
        if abs(r - cr) <= 1 and abs(c - cc) <= 1:
            return True
    return False


def draw_standard_finders(draw, color="#000000"):
    """Draw standard square finder patterns."""
    finder_positions = [(0, 0), (0, N - 7), (N - 7, 0)]
    for fr, fc in finder_positions:
        x0 = PAD + fc * MOD
        y0 = PAD + fr * MOD
        # Outer border (7x7)
        draw.rectangle([x0, y0, x0 + 7 * MOD - 1, y0 + 7 * MOD - 1], fill=color)
        # White ring (5x5)
        draw.rectangle([x0 + MOD, y0 + MOD, x0 + 6 * MOD - 1, y0 + 6 * MOD - 1], fill=WHITE)
        # Inner block (3x3)
        draw.rectangle([x0 + 2 * MOD, y0 + 2 * MOD, x0 + 5 * MOD - 1, y0 + 5 * MOD - 1], fill=color)


def draw_rounded_finders(draw, color="#000000", radius_frac=0.3):
    """Draw rounded-rectangle finder patterns."""
    finder_positions = [(0, 0), (0, N - 7), (N - 7, 0)]
    r_outer = int(MOD * radius_frac * 3)
    r_mid = int(MOD * radius_frac * 2)
    r_inner = int(MOD * radius_frac * 1.5)
    for fr, fc in finder_positions:
        x0 = PAD + fc * MOD
        y0 = PAD + fr * MOD
        draw.rounded_rectangle([x0, y0, x0 + 7 * MOD - 1, y0 + 7 * MOD - 1],
                               radius=r_outer, fill=color)
        draw.rounded_rectangle([x0 + MOD, y0 + MOD, x0 + 6 * MOD - 1, y0 + 6 * MOD - 1],
                               radius=r_mid, fill=WHITE)
        draw.rounded_rectangle([x0 + 2 * MOD, y0 + 2 * MOD, x0 + 5 * MOD - 1, y0 + 5 * MOD - 1],
                               radius=r_inner, fill=color)


def draw_logo_on_finders(draw):
    """Draw the QS logo etched in white on finder centers (small, centered)."""
    finder_positions = [(0, 0), (0, N - 7), (N - 7, 0)]
    for fr, fc in finder_positions:
        cx = PAD + (fc + 3.5) * MOD
        cy = PAD + (fr + 3.5) * MOD
        # Keep logo within the center 1 module (not spanning whole 3x3)
        size = MOD * 1.6
        # Draw 2x2 grid dots
        for gi in range(3):
            for gj in range(3):
                dx = cx + (gj - 1) * size * 0.35
                dy = cy + (gi - 1) * size * 0.35
                r = size * 0.05
                draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=WHITE)
        # Grid lines
        lw = max(2, int(size * 0.025))
        for gi in range(3):
            y = cy + (gi - 1) * size * 0.35
            draw.line([cx - size * 0.35, y, cx + size * 0.35, y], fill=WHITE, width=lw)
        for gj in range(3):
            x = cx + (gj - 1) * size * 0.35
            draw.line([x, cy - size * 0.35, x, cy + size * 0.35], fill=WHITE, width=lw)
        # Backwards S-curve
        sw = max(2, int(size * 0.04))
        pts = []
        for t in range(50):
            frac = t / 49.0
            y = cy - size * 0.3 + frac * size * 0.6
            x = cx + math.sin((1 - frac) * math.pi) * size * 0.15
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=WHITE, width=sw)


def draw_connected_modules(draw, color, connect_h=True, connect_v=True,
                           line_width_frac=0.55, end_cap_round=True,
                           vary_thickness=False, grid_center=14.5):
    """Draw dark modules as connected traces."""
    lw = int(MOD * line_width_frac)
    half = lw // 2

    for r in range(N):
        for c in range(N):
            if not matrix[r][c]:
                continue
            if is_finder(r, c):
                continue

            cx = PAD + c * MOD + MOD // 2
            cy = PAD + r * MOD + MOD // 2

            thickness = lw
            if vary_thickness:
                # Thicker near the grid center lines
                dist_to_center_r = abs(r - grid_center)
                dist_to_center_c = abs(c - grid_center)
                min_dist = min(dist_to_center_r, dist_to_center_c)
                if min_dist < 2:
                    thickness = int(lw * 1.3)
                elif min_dist < 4:
                    thickness = int(lw * 1.1)

            th = thickness // 2

            # Draw the module itself as a rounded rect or circle
            if end_cap_round:
                draw.ellipse([cx - th, cy - th, cx + th, cy + th], fill=color)
            else:
                draw.rectangle([cx - th, cy - th, cx + th, cy + th], fill=color)

            # Connect to right neighbor
            if connect_h and c + 1 < N and matrix[r][c + 1] and not is_finder(r, c + 1):
                nx = PAD + (c + 1) * MOD + MOD // 2
                draw.rectangle([cx, cy - th, nx, cy + th], fill=color)
                if end_cap_round:
                    draw.ellipse([nx - th, cy - th, nx + th, cy + th], fill=color)

            # Connect to bottom neighbor
            if connect_v and r + 1 < N and matrix[r + 1][c] and not is_finder(r + 1, c):
                ny = PAD + (r + 1) * MOD + MOD // 2
                draw.rectangle([cx - th, cy, cx + th, ny], fill=color)
                if end_cap_round:
                    draw.ellipse([cx - th, ny - th, cx + th, ny + th], fill=color)


def finalize(img, name):
    """Downsample and save."""
    final_size = IMG_SIZE // SS
    out = img.resize((final_size, final_size), Image.LANCZOS)
    path = f"/home/shapor/src/qs/live-mode/qr-variants/{name}"
    out.save(path)
    # Scan
    results = decode(Image.open(path))
    status = "PASS" if any(r.data == b"https://querystory.ai" for r in results) else "FAIL"
    decoded = [r.data.decode() for r in results] if results else ["none"]
    print(f"{name}: {status} (decoded: {decoded})")
    return status


# ============================================================
# B01: Horizontal connections only, black, round caps, standard finders
# ============================================================
def gen_b01():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, "#000000", connect_h=True, connect_v=False,
                           line_width_frac=0.5, end_cap_round=True)
    draw_standard_finders(draw, "#000000")
    finalize(img, "B01_horiz_connections.png")


# B02: H+V connections, black, round caps, standard finders
def gen_b02():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, "#000000", connect_h=True, connect_v=True,
                           line_width_frac=0.5, end_cap_round=True)
    draw_standard_finders(draw, "#000000")
    finalize(img, "B02_hv_connections.png")


# B03: H+V connections, QS blue, round caps, etched logo finders
def gen_b03():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, QS_BLUE, connect_h=True, connect_v=True,
                           line_width_frac=0.5, end_cap_round=True)
    draw_standard_finders(draw, QS_BLUE)
    draw_logo_on_finders(draw)
    finalize(img, "B03_blue_hv_etched.png")


# B04: PCB traces - H+V, dark blue, square ends, thicker lines
def gen_b04():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, DARK_BLUE, connect_h=True, connect_v=True,
                           line_width_frac=0.6, end_cap_round=False)
    draw_standard_finders(draw, DARK_BLUE)
    finalize(img, "B04_pcb_square.png")


# B05: PCB traces with rounded caps, dark blue, varying thickness near grid center
def gen_b05():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, DARK_BLUE, connect_h=True, connect_v=True,
                           line_width_frac=0.5, end_cap_round=True,
                           vary_thickness=True)
    draw_standard_finders(draw, DARK_BLUE)
    draw_logo_on_finders(draw)
    finalize(img, "B05_pcb_vary_thick.png")


# B06: Metro map - H only, QS blue, thick rounded, rounded finders
def gen_b06():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, QS_BLUE, connect_h=True, connect_v=False,
                           line_width_frac=0.6, end_cap_round=True)
    draw_rounded_finders(draw, QS_BLUE, radius_frac=0.35)
    finalize(img, "B06_metro_horiz.png")


# B07: Metro map - H+V, QS blue, thick rounded, rounded finders + etched logo
def gen_b07():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, QS_BLUE, connect_h=True, connect_v=True,
                           line_width_frac=0.55, end_cap_round=True)
    draw_rounded_finders(draw, QS_BLUE, radius_frac=0.35)
    draw_logo_on_finders(draw)
    finalize(img, "B07_metro_hv_etched.png")


# B08: Navy on light gray bg, H+V, round caps, grid emphasis
def gen_b08():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    # Light gray background only inside QR area
    draw.rectangle([PAD - MOD, PAD - MOD, PAD + N * MOD + MOD, PAD + N * MOD + MOD],
                   fill=LIGHT_GRAY)
    # Draw subtle grid lines at center
    grid_lw = max(2, MOD // 8)
    grid_color = "#D0D8E4"
    cx_grid = PAD + 14.5 * MOD
    cy_grid = PAD + 14.5 * MOD
    draw.line([cx_grid, PAD, cx_grid, PAD + N * MOD], fill=grid_color, width=grid_lw)
    draw.line([PAD, cy_grid, PAD + N * MOD, cy_grid], fill=grid_color, width=grid_lw)
    draw_connected_modules(draw, NAVY, connect_h=True, connect_v=True,
                           line_width_frac=0.5, end_cap_round=True,
                           vary_thickness=True)
    draw_standard_finders(draw, NAVY)
    draw_logo_on_finders(draw)
    finalize(img, "B08_navy_grid_emphasis.png")


# B09: Organic flowing - thin connections, near-black, white bg, etched finders
def gen_b09():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, NEAR_BLACK, connect_h=True, connect_v=True,
                           line_width_frac=0.45, end_cap_round=True)
    draw_standard_finders(draw, NEAR_BLACK)
    draw_logo_on_finders(draw)
    finalize(img, "B09_organic_thin.png")


# B10: Bold network - QS blue, thick H+V, rounded finders, etched logo, light blue bg
def gen_b10():
    bg = "#EFF6FF"
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), bg)
    draw = ImageDraw.Draw(img)
    draw_connected_modules(draw, QS_BLUE, connect_h=True, connect_v=True,
                           line_width_frac=0.65, end_cap_round=True)
    draw_rounded_finders(draw, QS_BLUE, radius_frac=0.35)
    draw_logo_on_finders(draw)
    finalize(img, "B10_bold_network.png")


if __name__ == "__main__":
    gen_b01()
    gen_b02()
    gen_b03()
    gen_b04()
    gen_b05()
    gen_b06()
    gen_b07()
    gen_b08()
    gen_b09()
    gen_b10()
