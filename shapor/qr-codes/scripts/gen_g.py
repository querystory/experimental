#!/usr/bin/env python3
"""Generate QR variants G01-G10: Connected traces with visible S-curve."""

import math
import qrcode
from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode as pyzbar_decode

# --- QR matrix ---
qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data("https://querystory.ai")
qr.make(fit=True)
matrix = qr.get_matrix()
SIZE = len(matrix)  # 29

# --- S-curve bezier (QS logo) ---
# M45,30 C40,30 35,34 37,36 C39,38 44,38 47,41 C50,44 47,48 42,48 C37,48 35,44 37,42
# Logo grid 15-45, map to QR module coords in center region

def bezier_cubic(p0, p1, p2, p3, n=50):
    """Generate n points along cubic bezier."""
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def logo_to_qr(lx, ly, pad, mod, img_size):
    """Convert logo coords (15-45 range) to pixel coords."""
    qr_x = pad + (lx - 15) / 30 * SIZE * mod
    qr_y = pad + (ly - 15) / 30 * SIZE * mod
    return (qr_x, qr_y)


def get_scurve_points(pad, mod, img_size, n_per_seg=50):
    """Get S-curve points in pixel coords."""
    # Four cubic bezier segments
    segs = [
        ((45, 30), (40, 30), (35, 34), (37, 36)),
        ((37, 36), (39, 38), (44, 38), (47, 41)),
        ((47, 41), (50, 44), (47, 48), (42, 48)),
        ((42, 48), (37, 48), (35, 44), (37, 42)),
    ]
    pts = []
    for p0, p1, p2, p3 in segs:
        p0p = logo_to_qr(*p0, pad, mod, img_size)
        p1p = logo_to_qr(*p1, pad, mod, img_size)
        p2p = logo_to_qr(*p2, pad, mod, img_size)
        p3p = logo_to_qr(*p3, pad, mod, img_size)
        pts.extend(bezier_cubic(p0p, p1p, p2p, p3p, n_per_seg))
    return pts


def min_dist_to_curve(px, py, curve_pts):
    """Min distance from pixel to S-curve."""
    return min(math.hypot(px - cx, py - cy) for cx, cy in curve_pts)


def is_finder(r, c):
    """Check if module is in finder pattern area."""
    # Top-left, top-right, bottom-left finder patterns (7x7 each)
    if r < 7 and c < 7:
        return True
    if r < 7 and c >= SIZE - 7:
        return True
    if r >= SIZE - 7 and c < 7:
        return True
    return False


def draw_finder_standard(draw, r, c, pad, mod):
    """Draw standard finder pattern at given corner."""
    x0 = pad + c * mod
    y0 = pad + r * mod
    # Outer black
    draw.rectangle([x0, y0, x0 + 7 * mod - 1, y0 + 7 * mod - 1], fill="black")
    # Inner white
    draw.rectangle([x0 + mod, y0 + mod, x0 + 6 * mod - 1, y0 + 6 * mod - 1], fill="white")
    # Center black
    draw.rectangle([x0 + 2 * mod, y0 + 2 * mod, x0 + 5 * mod - 1, y0 + 5 * mod - 1], fill="black")


def draw_finder_with_qs(draw, r, c, pad, mod):
    """Draw finder with QS logo etched in center 3x3."""
    draw_finder_standard(draw, r, c, pad, mod)
    # Draw small "Q" shape in white on the 3x3 center - small enough to not break finder
    cx = pad + (c + 3.5) * mod
    cy = pad + (r + 3.5) * mod
    radius = mod * 0.7
    lw = max(1, mod // 6)
    # Circle
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline="white", width=lw)
    # Small tail for Q
    draw.line([cx + radius * 0.3, cy + radius * 0.3, cx + radius * 0.8, cy + radius * 0.8], fill="white", width=lw)


def draw_finders(draw, pad, mod, etched=False):
    """Draw all three finder patterns."""
    fn = draw_finder_with_qs if etched else draw_finder_standard
    fn(draw, 0, 0, pad, mod)
    fn(draw, 0, SIZE - 7, pad, mod)
    fn(draw, SIZE - 7, 0, pad, mod)


def get_adjacent_dark(r, c):
    """Get adjacent dark modules (4-connected)."""
    adj = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < SIZE and 0 <= nc < SIZE and matrix[nr][nc] and not is_finder(nr, nc):
            adj.append((nr, nc))
    return adj


def module_center(r, c, pad, mod):
    """Get pixel center of module."""
    return (pad + c * mod + mod / 2, pad + r * mod + mod / 2)


# ========== VARIANT GENERATORS ==========

def gen_g01():
    """Thick S-curve trace over connected dots. Connections as thin lines, S-curve as thick colored overlay."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    base_width = mod * 0.35
    thick_width = mod * 0.7

    # Draw connections between adjacent dark modules
    drawn_connections = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn_connections:
                    continue
                drawn_connections.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                draw.line([(cx, cy), (nx, ny)], fill="#333333", width=int(base_width))

    # Draw dots at dark modules
    dot_r = mod * 0.25
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill="#333333")

    # Draw S-curve as thick colored trace
    for i in range(len(curve_pts) - 1):
        x1, y1 = curve_pts[i]
        x2, y2 = curve_pts[i + 1]
        draw.line([(x1, y1), (x2, y2)], fill="#2563EB", width=int(thick_width))

    draw_finders(draw, pad, mod, etched=False)
    return img


def gen_g02():
    """Connections colored by distance to S-curve: blue near, dark gray far."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    max_dist = mod * 8  # normalize distance

    # Draw connections
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                mx, my = (cx + nx) / 2, (cy + ny) / 2
                d = min_dist_to_curve(mx, my, curve_pts)
                t = min(d / max_dist, 1.0)
                # Blue (37,99,235) -> dark gray (51,51,51)
                cr = int(37 + t * (51 - 37))
                cg = int(99 + t * (51 - 99))
                cb = int(235 + t * (51 - 235))
                w = int(mod * (0.5 - 0.2 * t))
                draw.line([(cx, cy), (nx, ny)], fill=(cr, cg, cb), width=w)

    # Dots
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            d = min_dist_to_curve(cx, cy, curve_pts)
            t = min(d / max_dist, 1.0)
            cr = int(37 + t * (51 - 37))
            cg = int(99 + t * (51 - 99))
            cb = int(235 + t * (51 - 235))
            dot_r = mod * (0.3 - 0.1 * t)
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=(cr, cg, cb))

    draw_finders(draw, pad, mod)
    return img


def gen_g03():
    """S-curve as gap/channel: don't connect modules that the curve crosses between."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    gap_threshold = mod * 1.5

    # Draw connections, skip if midpoint is too close to curve
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                mx, my = (cx + nx) / 2, (cy + ny) / 2
                d = min_dist_to_curve(mx, my, curve_pts)
                if d < gap_threshold:
                    continue  # skip - creates gap along curve
                draw.line([(cx, cy), (nx, ny)], fill="#1a1a1a", width=int(mod * 0.35))

    # Dots - all dark modules
    dot_r = mod * 0.28
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            d = min_dist_to_curve(cx, cy, curve_pts)
            color = "#2563EB" if d < gap_threshold else "#1a1a1a"
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=color)

    # Draw S-curve as thin blue line for visibility
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#93C5FD", width=int(mod * 0.15))

    draw_finders(draw, pad, mod)
    return img


def gen_g04():
    """Metro map style: straight connections everywhere, S-curve drawn as thick colored line on top."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    conn_w = int(mod * 0.4)

    # Draw all connections
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                draw.line([(cx, cy), (nx, ny)], fill="#374151", width=conn_w)

    # Square dots at junctions
    sq = mod * 0.25
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            draw.rectangle([cx - sq, cy - sq, cx + sq, cy + sq], fill="#374151")

    # S-curve: blue line (metro line) - keep thin enough to not destroy modules
    w_line = int(mod * 0.35)
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#2563EB", width=w_line)

    # Small dots along the S-curve like metro stations
    for i in range(0, len(curve_pts), 25):
        sx, sy = curve_pts[i]
        draw.ellipse([sx - mod * 0.22, sy - mod * 0.22, sx + mod * 0.22, sy + mod * 0.22], fill="white", outline="#2563EB", width=2)

    draw_finders(draw, pad, mod, etched=True)
    return img


def gen_g05():
    """PCB traces with S-curve as highlighted signal path. Connections near curve are copper/gold."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    # Light background for scannability
    img = Image.new("RGB", (img_size, img_size), "#E8F5E9")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    highlight_dist = mod * 3

    # Traces
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                mx, my = (cx + nx) / 2, (cy + ny) / 2
                d = min_dist_to_curve(mx, my, curve_pts)
                if d < highlight_dist:
                    color = "#8B6914"  # dark gold
                    w = int(mod * 0.45)
                else:
                    color = "#2D5016"  # dark green
                    w = int(mod * 0.3)
                draw.line([(cx, cy), (nx, ny)], fill=color, width=w)

    # Pads
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            d = min_dist_to_curve(cx, cy, curve_pts)
            if d < highlight_dist:
                color = "#8B6914"
                pr = mod * 0.3
            else:
                color = "#2D5016"
                pr = mod * 0.22
            draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=color)

    # S-curve as dark gold trace
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#6B4F10", width=int(mod * 0.35))

    # Finder patterns - need white bg first
    for (fr, fc) in [(0, 0), (0, SIZE - 7), (SIZE - 7, 0)]:
        x0, y0 = pad + fc * mod, pad + fr * mod
        draw.rectangle([x0 - 2, y0 - 2, x0 + 7 * mod + 1, y0 + 7 * mod + 1], fill="white")
    draw_finders(draw, pad, mod)
    return img


def gen_g06():
    """Rounded connections with S-curve highlighted via thicker + blue connections."""
    mod = 22
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    near_dist = mod * 2.5

    # All connections
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                mx, my = (cx + nx) / 2, (cy + ny) / 2
                d = min_dist_to_curve(mx, my, curve_pts)
                if d < near_dist:
                    draw.line([(cx, cy), (nx, ny)], fill="#2563EB", width=int(mod * 0.5))
                else:
                    draw.line([(cx, cy), (nx, ny)], fill="#1F2937", width=int(mod * 0.3))

    # Dots
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            d = min_dist_to_curve(cx, cy, curve_pts)
            if d < near_dist:
                dr = mod * 0.32
                draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill="#2563EB")
            else:
                dr = mod * 0.22
                draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill="#1F2937")

    draw_finders(draw, pad, mod)
    return img


def gen_g07():
    """S-curve as background glow behind connected modules."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)

    # Draw glow behind S-curve
    for width, alpha_color in [(int(mod * 3), "#E0EDFF"), (int(mod * 2), "#BFDBFE"), (int(mod * 1.2), "#93C5FD")]:
        for i in range(len(curve_pts) - 1):
            draw.line([curve_pts[i], curve_pts[i + 1]], fill=alpha_color, width=width)

    # Connections
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                draw.line([(cx, cy), (nx, ny)], fill="#1E293B", width=int(mod * 0.35))

    # Dots
    dot_r = mod * 0.25
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill="#1E293B")

    # Crisp S-curve line on top
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#2563EB", width=int(mod * 0.5))

    # White bg for finders
    for (fr, fc) in [(0, 0), (0, SIZE - 7), (SIZE - 7, 0)]:
        x0, y0 = pad + fc * mod, pad + fr * mod
        draw.rectangle([x0 - 2, y0 - 2, x0 + 7 * mod + 1, y0 + 7 * mod + 1], fill="white")
    draw_finders(draw, pad, mod)
    return img


def gen_g08():
    """Dual color scheme: modules on one side of S-curve are blue, other side dark. Curve is the boundary."""
    mod = 20
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)

    # Determine which side of curve each point is on using cross product with nearest segment
    def side_of_curve(px, py):
        min_d = float("inf")
        best_cross = 0
        for i in range(len(curve_pts) - 1):
            ax, ay = curve_pts[i]
            bx, by = curve_pts[i + 1]
            d = math.hypot(px - (ax + bx) / 2, py - (ay + by) / 2)
            if d < min_d:
                min_d = d
                # Cross product determines side
                best_cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        return best_cross > 0

    # Connections
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            side = side_of_curve(cx, cy)
            color = "#2563EB" if side else "#1F2937"
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                n_side = side_of_curve(nx, ny)
                if side == n_side:
                    draw.line([(cx, cy), (nx, ny)], fill=color, width=int(mod * 0.35))
                else:
                    # Cross-boundary: don't connect (creates gap along S-curve)
                    pass

    # Dots
    dot_r = mod * 0.25
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            side = side_of_curve(cx, cy)
            color = "#2563EB" if side else "#1F2937"
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=color)

    draw_finders(draw, pad, mod)
    return img


def gen_g09():
    """Dense connections with S-curve etched as white gap through the pattern."""
    mod = 18
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)

    # Draw filled rectangles for dark modules (dense, like standard QR but rounded)
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            x0 = pad + c * mod
            y0 = pad + r * mod
            margin = mod * 0.08
            draw.rounded_rectangle(
                [x0 + margin, y0 + margin, x0 + mod - margin, y0 + mod - margin],
                radius=mod * 0.2,
                fill="#1F2937",
            )

    # Connect adjacent dark modules (fill gaps)
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            # Right neighbor
            if c + 1 < SIZE and matrix[r][c + 1] and not is_finder(r, c + 1):
                x0 = pad + c * mod + mod * 0.3
                y0 = pad + r * mod + mod * 0.08
                draw.rectangle([x0, y0, x0 + mod * 0.4, y0 + mod * 0.84], fill="#1F2937")
            # Bottom neighbor
            if r + 1 < SIZE and matrix[r + 1][c] and not is_finder(r + 1, c):
                x0 = pad + c * mod + mod * 0.08
                y0 = pad + r * mod + mod * 0.3
                draw.rectangle([x0, y0, x0 + mod * 0.84, y0 + mod * 0.4], fill="#1F2937")

    # Etch S-curve as thin white line through the pattern
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="white", width=int(mod * 0.35))
    # Blue outline on both sides
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#2563EB", width=int(mod * 0.12))

    draw_finders(draw, pad, mod, etched=True)
    return img


def gen_g10():
    """Combined: connected traces + gradient coloring + S-curve overlay with glow + etched finders."""
    mod = 22
    pad = mod * 4
    img_size = SIZE * mod + 2 * pad
    img = Image.new("RGB", (img_size, img_size), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    curve_pts = get_scurve_points(pad, mod, img_size)
    max_dist = mod * 7

    # Subtle glow
    for width, color in [(int(mod * 2.5), "#EFF6FF"), (int(mod * 1.5), "#DBEAFE")]:
        for i in range(len(curve_pts) - 1):
            draw.line([curve_pts[i], curve_pts[i + 1]], fill=color, width=width)

    # Connections with gradient
    drawn = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            for nr, nc in get_adjacent_dark(r, c):
                if is_finder(nr, nc):
                    continue
                key = (min(r, nr), min(c, nc), max(r, nr), max(c, nc))
                if key in drawn:
                    continue
                drawn.add(key)
                nx, ny = module_center(nr, nc, pad, mod)
                mx, my = (cx + nx) / 2, (cy + ny) / 2
                d = min_dist_to_curve(mx, my, curve_pts)
                t = min(d / max_dist, 1.0)
                # Near: blue #2563EB, Far: slate #334155
                cr = int(37 + t * (51 - 37))
                cg = int(99 + t * (85 - 99))
                cb = int(235 + t * (85 - 235))
                w = int(mod * (0.45 - 0.15 * t))
                draw.line([(cx, cy), (nx, ny)], fill=(cr, cg, cb), width=w)

    # Dots
    for r in range(SIZE):
        for c in range(SIZE):
            if not matrix[r][c] or is_finder(r, c):
                continue
            cx, cy = module_center(r, c, pad, mod)
            d = min_dist_to_curve(cx, cy, curve_pts)
            t = min(d / max_dist, 1.0)
            cr = int(37 + t * (51 - 37))
            cg = int(99 + t * (85 - 99))
            cb = int(235 + t * (85 - 235))
            dr = mod * (0.28 - 0.08 * t)
            draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=(cr, cg, cb))

    # S-curve - thinner to preserve scannability
    for i in range(len(curve_pts) - 1):
        draw.line([curve_pts[i], curve_pts[i + 1]], fill="#1D4ED8", width=int(mod * 0.35))

    # White bg for finders
    for (fr, fc) in [(0, 0), (0, SIZE - 7), (SIZE - 7, 0)]:
        x0, y0 = pad + fc * mod, pad + fr * mod
        draw.rectangle([x0 - 2, y0 - 2, x0 + 7 * mod + 1, y0 + 7 * mod + 1], fill="#F8FAFC")
    draw_finders(draw, pad, mod, etched=True)
    return img


# ========== MAIN ==========

generators = [
    ("G01", "Thick S-curve trace overlay", gen_g01),
    ("G02", "Distance-gradient coloring", gen_g02),
    ("G03", "S-curve gap/channel", gen_g03),
    ("G04", "Metro map + S-curve line", gen_g04),
    ("G05", "PCB gold signal path", gen_g05),
    ("G06", "Blue highlight near curve", gen_g06),
    ("G07", "Background glow + overlay", gen_g07),
    ("G08", "Dual color split by curve", gen_g08),
    ("G09", "Dense modules, etched S-curve", gen_g09),
    ("G10", "Combined gradient + glow + etched", gen_g10),
]

outdir = "/home/shapor/src/qs/live-mode/qr-variants"

for name, desc, gen_fn in generators:
    img = gen_fn()
    path = f"{outdir}/{name}.png"
    img.save(path, "PNG")
    # Scan
    results = pyzbar_decode(img)
    status = "SCAN" if any(r.data == b"https://querystory.ai" for r in results) else "FAIL"
    print(f"{name}: {status} - {desc}")
