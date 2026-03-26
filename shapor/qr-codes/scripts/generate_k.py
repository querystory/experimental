#!/usr/bin/env python3
"""Generate 10 artistic QR code variants (K01-K10) for QueryStory."""

import math
import random
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pyzbar.pyzbar import decode as pyzbar_decode

# --- QR Data ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
SIZE = len(matrix)  # 29

# --- Constants ---
SS = 3  # supersample factor
MOD = 36 * SS       # module size in pixels (108)
PAD = 70 * SS       # padding (210)
BLUE = "#2563EB"
DARK_BLUE = "#1d4ed8"
LIGHT_BLUE = "#dbeafe"
WHITE = "#ffffff"
IMG_SIZE = PAD * 2 + SIZE * MOD

# --- S-curve path (as points for drawing) ---
def s_curve_points(ox, oy, scale):
    """Generate S-curve points mapped to image coordinates."""
    # Original SVG: M45,30 C40,30 35,34 37,36 C39,38 44,38 47,41 C50,44 47,48 42,48 C37,48 35,44 37,42
    # Logo grid spans 15-45, so normalize to 0-1 from that range
    def bezier(p0, p1, p2, p3, steps=20):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
            y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
            pts.append((x, y))
        return pts

    def map_pt(sx, sy):
        nx = (sx - 15) / 30
        ny = (sy - 15) / 30
        return (ox + nx * scale, oy + ny * scale)

    all_pts = []
    all_pts += bezier(map_pt(45,30), map_pt(40,30), map_pt(35,34), map_pt(37,36))
    all_pts += bezier(map_pt(37,36), map_pt(39,38), map_pt(44,38), map_pt(47,41))
    all_pts += bezier(map_pt(47,41), map_pt(50,44), map_pt(47,48), map_pt(42,48))
    all_pts += bezier(map_pt(42,48), map_pt(37,48), map_pt(35,44), map_pt(37,42))
    return all_pts


def cell_center(r, c):
    """Get pixel center of module (r, c)."""
    return (PAD + c * MOD + MOD // 2, PAD + r * MOD + MOD // 2)


def is_finder(r, c):
    """Check if module is in a finder pattern area."""
    if r < 7 and c < 7:
        return True
    if r < 7 and c >= SIZE - 7:
        return True
    if r >= SIZE - 7 and c < 7:
        return True
    return False


def draw_etched_finder(draw, top_r, top_c, color_dark, color_light):
    """Draw etched finder pattern (concentric rounded rects)."""
    x0 = PAD + top_c * MOD
    y0 = PAD + top_r * MOD
    s = MOD * 7
    m = MOD

    # Outer ring
    draw.rounded_rectangle([x0, y0, x0 + s, y0 + s], radius=m, fill=color_dark)
    # White ring
    draw.rounded_rectangle([x0 + m, y0 + m, x0 + s - m, y0 + s - m], radius=m//2, fill=color_light)
    # Inner square
    inner_m = int(m * 2)
    draw.rounded_rectangle([x0 + inner_m, y0 + inner_m, x0 + s - inner_m, y0 + s - inner_m],
                           radius=m//2, fill=color_dark)


def draw_etched_finders(draw, color_dark=BLUE, color_light=WHITE):
    """Draw all three finder patterns."""
    draw_etched_finder(draw, 0, 0, color_dark, color_light)
    draw_etched_finder(draw, 0, SIZE - 7, color_dark, color_light)
    draw_etched_finder(draw, SIZE - 7, 0, color_dark, color_light)


def draw_logo_center(draw, img_size, logo_mods=5):
    """Draw the QS logo in the center of the QR code."""
    cx = img_size // 2
    cy = img_size // 2
    logo_size = int(MOD * logo_mods)
    half = logo_size // 2

    # Blue rounded rect background
    draw.rounded_rectangle(
        [cx - half, cy - half, cx + half, cy + half],
        radius=int(logo_size * 0.18),
        fill=BLUE
    )

    # White grid: 2x2 cells, 9 dots at intersections
    grid_pad = int(logo_size * 0.2)
    gx0 = cx - half + grid_pad
    gy0 = cy - half + grid_pad
    gw = logo_size - 2 * grid_pad
    gh = logo_size - 2 * grid_pad

    # Grid lines
    line_w = max(2, int(logo_size * 0.02))
    for i in range(3):
        x = gx0 + int(i * gw / 2)
        draw.line([(x, gy0), (x, gy0 + gh)], fill=WHITE, width=line_w)
        y = gy0 + int(i * gh / 2)
        draw.line([(gx0, y), (gx0 + gw, y)], fill=WHITE, width=line_w)

    # 9 dots at intersections
    dot_r = max(3, int(logo_size * 0.04))
    for i in range(3):
        for j in range(3):
            dx = gx0 + int(j * gw / 2)
            dy = gy0 + int(i * gh / 2)
            draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=WHITE)

    # S-curve
    s_pts = s_curve_points(cx - half + grid_pad, cy - half + grid_pad, gw)
    curve_w = max(3, int(logo_size * 0.05))
    if len(s_pts) > 1:
        draw.line(s_pts, fill=WHITE, width=curve_w, joint="curve")


def is_logo_area(r, c, logo_mods=5):
    """Check if module is in the center logo area."""
    center = SIZE // 2
    half = logo_mods // 2 + 1
    return abs(r - center) <= half and abs(c - center) <= half


def scan_check(img, name):
    """Downsample and scan."""
    small = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    results = pyzbar_decode(small)
    if results and results[0].data == b"https://querystory.ai":
        print(f"  {name}: SCAN")
        return True
    # Try without downsampling
    results = pyzbar_decode(img)
    if results and results[0].data == b"https://querystory.ai":
        print(f"  {name}: SCAN")
        return True
    print(f"  {name}: FAIL")
    return False


# ============================================================
# K01: Pixel Art Style
# ============================================================
def generate_k01():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    sub = 3  # 3x3 sub-pixels per module
    sub_size = MOD // sub

    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            cx, cy = PAD + c * MOD, PAD + r * MOD
            if matrix[r][c]:
                # Fill all sub-pixels for dark modules
                for sr in range(sub):
                    for sc in range(sub):
                        sx = cx + sc * sub_size
                        sy = cy + sr * sub_size
                        gap = 2 * SS
                        draw.rectangle([sx + gap, sy + gap, sx + sub_size - gap, sy + sub_size - gap],
                                       fill=BLUE)
            else:
                # Light module: just a faint center dot
                center_x = cx + MOD // 2
                center_y = cy + MOD // 2
                dr = sub_size // 4
                draw.ellipse([center_x - dr, center_y - dr, center_x + dr, center_y + dr],
                             fill="#e0e7ff")

    draw_etched_finders(draw)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K02: Watercolor / Splatter
# ============================================================
def generate_k02():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    random.seed(42)

    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            # Main dot with slight offset
            ox = random.randint(-MOD//8, MOD//8)
            oy = random.randint(-MOD//8, MOD//8)
            base_r = int(MOD * 0.38)
            size_var = random.uniform(0.85, 1.15)
            radius = int(base_r * size_var)
            # Slight color variation
            blue_val = random.randint(200, 240)
            color = f"#{0x25:02x}{0x63:02x}{blue_val:02x}"
            draw.ellipse([cx + ox - radius, cy + oy - radius, cx + ox + radius, cy + oy + radius],
                         fill=color)
            # Small splatter dots
            for _ in range(random.randint(1, 3)):
                sx = cx + random.randint(-MOD//3, MOD//3)
                sy = cy + random.randint(-MOD//3, MOD//3)
                sr = random.randint(2*SS, 5*SS)
                alpha_blue = random.randint(180, 230)
                sc = f"#{0x25:02x}{0x63:02x}{alpha_blue:02x}"
                draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=sc)

    draw_etched_finders(draw)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K03: Topographic Map
# ============================================================
def generate_k03():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "#f0f7ff")
    draw = ImageDraw.Draw(img)

    # Draw contour-like rings around S-curve center
    cx_logo = IMG_SIZE // 2
    cy_logo = IMG_SIZE // 2

    # Background contour lines
    for ring in range(3, 30, 2):
        r = ring * MOD
        draw.ellipse([cx_logo - r, cy_logo - r, cx_logo + r, cy_logo + r],
                     outline="#c7d7f0", width=1*SS)

    # Data modules as filled contour blobs
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            # Draw concentric rings for each dark module
            for i in range(3, 0, -1):
                radius = int(MOD * 0.4 * i / 3)
                alpha = 80 + (3 - i) * 60
                blue_g = min(255, 0x63 + (3-i)*30)
                color = f"#{0x25:02x}{blue_g:02x}{0xEB:02x}"
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                             outline=color, width=2*SS)
            # Solid center
            cr = int(MOD * 0.15)
            draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=BLUE)

    draw_etched_finders(draw)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K04: Blueprint Style
# ============================================================
def generate_k04():
    bg = WHITE
    line_color = "#bfdbfe"
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), bg)
    draw = ImageDraw.Draw(img)

    # Grid lines across entire image (light blue on white for blueprint feel)
    grid_step = MOD
    for x in range(PAD, PAD + SIZE * MOD + 1, grid_step):
        draw.line([(x, PAD), (x, PAD + SIZE * MOD)], fill=line_color, width=1*SS)
    for y in range(PAD, PAD + SIZE * MOD + 1, grid_step):
        draw.line([(PAD, y), (PAD + SIZE * MOD, y)], fill=line_color, width=1*SS)

    # Dimension markers at top edge
    for c in range(0, SIZE, 5):
        x = PAD + c * MOD + MOD // 2
        draw.line([(x, PAD - 20*SS), (x, PAD - 10*SS)], fill=DARK_BLUE, width=1*SS)

    # Dimension line
    draw.line([(PAD, PAD - 15*SS), (PAD + SIZE*MOD, PAD - 15*SS)], fill=DARK_BLUE, width=1*SS)

    # Data modules as filled rounded squares (dark on white = high contrast)
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            cx, cy = cell_center(r, c)
            if matrix[r][c]:
                half = int(MOD * 0.42)
                draw.rounded_rectangle(
                    [cx - half, cy - half, cx + half, cy + half],
                    radius=half//4, fill=DARK_BLUE
                )
            else:
                # Small crosshair for empty modules
                ch = MOD // 6
                draw.line([(cx - ch, cy), (cx + ch, cy)], fill="#dbeafe", width=1*SS)
                draw.line([(cx, cy - ch), (cx, cy + ch)], fill="#dbeafe", width=1*SS)

    draw_etched_finders(draw, DARK_BLUE, bg)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K05: Neon Glow
# ============================================================
def generate_k05():
    # White background with dark blue modules + blue glow halos around them
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    glow_color = (191, 219, 254)  # light blue glow
    dark = (21, 40, 80)  # very dark blue for modules

    # First pass: glow halos
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            gr = int(MOD * 0.6)
            draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=glow_color)

    # Second pass: sharp dark modules on top
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            radius = int(MOD * 0.38)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=dark)

    draw_etched_finders(draw, dark, WHITE)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K06: Mosaic / Tile
# ============================================================
def generate_k06():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "#f8fafc")
    draw = ImageDraw.Draw(img)

    random.seed(99)
    gap = 3 * SS
    tile_size = MOD - gap * 2
    corner_r = int(tile_size * 0.2)

    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            x0 = PAD + c * MOD + gap
            y0 = PAD + r * MOD + gap
            if matrix[r][c]:
                # Slight rotation effect via offset corners
                ox = random.randint(-2*SS, 2*SS)
                oy = random.randint(-2*SS, 2*SS)
                # Vary blue slightly
                b = random.randint(220, 240)
                color = f"#{0x25:02x}{0x63:02x}{b:02x}"
                draw.rounded_rectangle(
                    [x0 + ox, y0 + oy, x0 + tile_size + ox, y0 + tile_size + oy],
                    radius=corner_r, fill=color
                )
            else:
                # Faint tile outline
                draw.rounded_rectangle(
                    [x0, y0, x0 + tile_size, y0 + tile_size],
                    radius=corner_r, outline="#e2e8f0", width=1*SS
                )

    draw_etched_finders(draw)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K07: DNA / Helix
# ============================================================
def generate_k07():
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), WHITE)
    draw = ImageDraw.Draw(img)

    # Draw data modules as dots
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            radius = int(MOD * 0.35)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=BLUE)

    # Double helix S-curve overlay
    logo_cx = IMG_SIZE // 2
    logo_cy = IMG_SIZE // 2
    logo_size = MOD * 5
    half = logo_size // 2
    gx0 = logo_cx - half + int(logo_size * 0.2)
    gy0 = logo_cy - half + int(logo_size * 0.2)
    gw = logo_size - 2 * int(logo_size * 0.2)

    s_pts = s_curve_points(gx0, gy0, gw)
    # Draw helix strands offset from S-curve
    offset = 8 * SS
    for dx, dy in [(offset, 0), (-offset, 0)]:
        helix_pts = [(x + dx, y + dy) for x, y in s_pts]
        if len(helix_pts) > 1:
            draw.line(helix_pts, fill=BLUE, width=3*SS, joint="curve")

    # Rungs connecting the two strands
    for i in range(0, len(s_pts), 5):
        x, y = s_pts[i]
        draw.line([(x - offset, y), (x + offset, y)], fill="#93c5fd", width=2*SS)

    draw_etched_finders(draw)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K08: Constellation / Scatter
# ============================================================
def generate_k08():
    # White bg, dark dots connected by faint lines like a star chart
    bg = WHITE
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), bg)
    draw = ImageDraw.Draw(img)

    line_color = "#bfdbfe"  # very faint blue lines
    dot_color = BLUE

    # Faint connecting lines between neighboring dark modules
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < SIZE and 0 <= nc < SIZE and matrix[nr][nc]:
                    if is_finder(nr, nc) or is_logo_area(nr, nc):
                        continue
                    nx, ny = cell_center(nr, nc)
                    draw.line([(cx, cy), (nx, ny)], fill=line_color, width=1*SS)

    # Dark dots
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            radius = int(MOD * 0.35)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=dot_color)
            # Bright core
            cr = int(MOD * 0.12)
            draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=DARK_BLUE)

    draw_etched_finders(draw, BLUE, bg)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K09: Emboss / 3D
# ============================================================
def generate_k09():
    bg = "#e2e8f0"
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), bg)
    draw = ImageDraw.Draw(img)

    highlight = "#f8fafc"
    shadow = "#94a3b8"
    offset = 3 * SS

    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            cx, cy = cell_center(r, c)
            half = int(MOD * 0.4)
            if matrix[r][c]:
                # Shadow (bottom-right)
                draw.rounded_rectangle(
                    [cx - half + offset, cy - half + offset, cx + half + offset, cy + half + offset],
                    radius=half//3, fill=shadow
                )
                # Highlight (top-left edge implicit via main shape)
                draw.rounded_rectangle(
                    [cx - half - offset//2, cy - half - offset//2, cx + half - offset//2, cy + half - offset//2],
                    radius=half//3, fill=highlight
                )
                # Main module
                draw.rounded_rectangle(
                    [cx - half, cy - half, cx + half, cy + half],
                    radius=half//3, fill=BLUE
                )

    draw_etched_finders(draw, BLUE, bg)
    draw_logo_center(draw, IMG_SIZE)
    return img


# ============================================================
# K10: Stamp / Seal
# ============================================================
def generate_k10():
    bg = "#fef2f2"
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), bg)
    draw = ImageDraw.Draw(img)

    crimson = "#b91c1c"
    dark_red = "#991b1b"
    light_red = "#fecaca"

    # Circular border
    cx_img = IMG_SIZE // 2
    cy_img = IMG_SIZE // 2
    border_r = int((SIZE * MOD) // 2 + PAD * 0.4)
    draw.ellipse([cx_img - border_r, cy_img - border_r, cx_img + border_r, cy_img + border_r],
                 outline=crimson, width=6*SS)
    # Inner ring
    inner_r = border_r - 12*SS
    draw.ellipse([cx_img - inner_r, cy_img - inner_r, cx_img + inner_r, cy_img + inner_r],
                 outline=crimson, width=3*SS)

    # Data modules as square stamps
    for r in range(SIZE):
        for c in range(SIZE):
            if is_finder(r, c) or is_logo_area(r, c):
                continue
            if not matrix[r][c]:
                continue
            cx, cy = cell_center(r, c)
            half = int(MOD * 0.4)
            draw.rectangle([cx - half, cy - half, cx + half, cy + half], fill=crimson)

    draw_etched_finders(draw, crimson, bg)

    # Override logo with red version
    logo_size = MOD * 5
    half_l = logo_size // 2
    draw.rounded_rectangle(
        [cx_img - half_l, cy_img - half_l, cx_img + half_l, cy_img + half_l],
        radius=int(logo_size * 0.18), fill=crimson
    )
    # White grid
    grid_pad = int(logo_size * 0.2)
    gx0 = cx_img - half_l + grid_pad
    gy0 = cy_img - half_l + grid_pad
    gw = logo_size - 2 * grid_pad
    gh = gw
    line_w = max(2, int(logo_size * 0.02))
    for i in range(3):
        x = gx0 + int(i * gw / 2)
        draw.line([(x, gy0), (x, gy0 + gh)], fill=WHITE, width=line_w)
        y = gy0 + int(i * gh / 2)
        draw.line([(gx0, y), (gx0 + gw, y)], fill=WHITE, width=line_w)
    dot_r = max(3, int(logo_size * 0.04))
    for i in range(3):
        for j in range(3):
            dx = gx0 + int(j * gw / 2)
            dy = gy0 + int(i * gh / 2)
            draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=WHITE)
    s_pts = s_curve_points(gx0, gy0, gw)
    curve_w = max(3, int(logo_size * 0.05))
    if len(s_pts) > 1:
        draw.line(s_pts, fill=WHITE, width=curve_w, joint="curve")

    return img


# ============================================================
# Generate all
# ============================================================
generators = [
    ("K01", "Pixel Art", generate_k01),
    ("K02", "Watercolor", generate_k02),
    ("K03", "Topographic", generate_k03),
    ("K04", "Blueprint", generate_k04),
    ("K05", "Neon Glow", generate_k05),
    ("K06", "Mosaic Tile", generate_k06),
    ("K07", "DNA Helix", generate_k07),
    ("K08", "Constellation", generate_k08),
    ("K09", "Emboss 3D", generate_k09),
    ("K10", "Stamp Seal", generate_k10),
]

out_dir = "/home/shapor/src/qs/live-mode/qr-variants"
for name, desc, gen_fn in generators:
    print(f"Generating {name} ({desc})...")
    img = gen_fn()
    path = f"{out_dir}/{name}.png"
    img.save(path)
    scan_check(img, name)
    print()

print("Done!")
