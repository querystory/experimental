#!/usr/bin/env python3
"""Generate 15 QR code design variants (L01-L15) with readable QS letters."""

import os
import math
import qrcode
from PIL import Image, ImageDraw, ImageFont
from pyzbar.pyzbar import decode as pyzbar_decode

OUT_DIR = "/home/shapor/src/qs/live-mode/qr-variants"
os.makedirs(OUT_DIR, exist_ok=True)

BRAND_BLUE = (37, 99, 235)
DARK_BLUE = (20, 60, 160)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

URL = "https://querystory.ai"
SUPERSAMPLE = 3
MOD = 36 * SUPERSAMPLE
PAD = 70 * SUPERSAMPLE
BOLD_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

qr = qrcode.QRCode(version=3, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=1, border=0)
qr.add_data(URL)
qr.make(fit=True)
matrix = qr.get_matrix()
N = len(matrix)  # 29

IMG_W = N * MOD + 2 * PAD
IMG_H = IMG_W

FINDERS = [(0, 0), (0, N - 7), (N - 7, 0)]

def is_finder(r, c):
    for fr, fc in FINDERS:
        if fr <= r < fr + 7 and fc <= c < fc + 7:
            return True
    return False

def mod_center(r, c):
    return PAD + c * MOD + MOD // 2, PAD + r * MOD + MOD // 2

def qr_center():
    return PAD + N * MOD // 2, PAD + N * MOD // 2

def draw_rounded_rect(draw, bbox, radius, fill):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)

def draw_module(draw, r, c, color=BLACK, round_ratio=0.3):
    """Draw standard rounded-rect module."""
    x = PAD + c * MOD
    y = PAD + r * MOD
    m = int(MOD * 0.08)
    rad = int(MOD * round_ratio)
    draw_rounded_rect(draw, (x+m, y+m, x+MOD-m, y+MOD-m), rad, color)

def draw_circle_module(draw, r, c, color=BLACK, size=0.85):
    cx, cy = mod_center(r, c)
    half = int(MOD * size / 2)
    draw.ellipse([cx-half, cy-half, cx+half, cy+half], fill=color)

def draw_diamond_module(draw, r, c, color=BLACK, size=0.85):
    cx, cy = mod_center(r, c)
    half = int(MOD * size / 2)
    draw.polygon([(cx, cy-half), (cx+half, cy), (cx, cy+half), (cx-half, cy)], fill=color)

def draw_square_module(draw, r, c, color=BLACK, size=0.85):
    cx, cy = mod_center(r, c)
    half = int(MOD * size / 2)
    draw.rectangle([cx-half, cy-half, cx+half, cy+half], fill=color)

def draw_standard_finder(draw, fr, fc, color=BLACK):
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    rad = int(MOD * 0.3)
    draw_rounded_rect(draw, (x0+m, y0+m, x0+7*MOD-m, y0+7*MOD-m), rad*2, color)
    draw_rounded_rect(draw, (x0+MOD, y0+MOD, x0+6*MOD, y0+6*MOD), rad*2, WHITE)
    draw_rounded_rect(draw, (x0+2*MOD+m, y0+2*MOD+m, x0+5*MOD-m, y0+5*MOD-m), rad*2, color)

def draw_mini_logo(draw, cx, cy, scale, color):
    """Draw simplified QS logo dots (2x2 grid) from working code."""
    s = scale
    gap = s * 0.12
    box_s = (s - gap) / 2
    for gr in range(2):
        for gc in range(2):
            dx = cx + (gc - 0.5) * (box_s + gap)
            dy = cy + (gr - 0.5) * (box_s + gap)
            r = box_s * 0.35
            draw.ellipse((dx-r, dy-r, dx+r, dy+r), fill=color)

def draw_etched_finder(draw, fr, fc, color=BLACK, logo_color=WHITE):
    """Finder with mini logo etched in white on 3x3 center (proven scannable)."""
    x0 = PAD + fc * MOD
    y0 = PAD + fr * MOD
    m = int(MOD * 0.08)
    rad = int(MOD * 0.3)
    draw_rounded_rect(draw, (x0+m, y0+m, x0+7*MOD-m, y0+7*MOD-m), rad*2, color)
    draw_rounded_rect(draw, (x0+MOD, y0+MOD, x0+6*MOD, y0+6*MOD), rad*2, WHITE)
    draw_rounded_rect(draw, (x0+2*MOD+m, y0+2*MOD+m, x0+5*MOD-m, y0+5*MOD-m), rad*2, color)
    cx = x0 + 3.5 * MOD
    cy = y0 + 3.5 * MOD
    draw_mini_logo(draw, cx, cy, MOD * 1.2, logo_color)

def draw_all_finders(draw, etched=True, color=BLACK):
    for fr, fc in FINDERS:
        if etched:
            draw_etched_finder(draw, fr, fc, color)
        else:
            draw_standard_finder(draw, fr, fc, color)

def draw_data(draw, skip_fn=None, color_fn=None, shape="rounded", size_fn=None, force_on=None):
    """Draw non-finder data modules."""
    for r in range(N):
        for c in range(N):
            if is_finder(r, c):
                continue
            if skip_fn and skip_fn(r, c):
                continue
            on = matrix[r][c]
            if force_on and (r, c) in force_on:
                on = True
            if not on:
                continue
            color = color_fn(r, c) if color_fn else BLACK

            # Per-module shape override
            sh = shape(r, c) if callable(shape) else shape
            sz = size_fn(r, c) if size_fn else 0.85

            if sh == "circle":
                draw_circle_module(draw, r, c, color, sz)
            elif sh == "diamond":
                draw_diamond_module(draw, r, c, color, sz)
            elif sh == "square":
                draw_square_module(draw, r, c, color, sz)
            else:  # rounded
                draw_module(draw, r, c, color)

def get_letter_mask(letter, font_size_modules, offset_r=0, offset_c=0):
    font = ImageFont.truetype(BOLD_FONT, font_size_modules * 10)
    canvas = N * 10
    img = Image.new("L", (canvas, canvas), 0)
    d = ImageDraw.Draw(img)
    bbox = font.getbbox(letter)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x = (canvas - tw)//2 + offset_c*10 - bbox[0]
    y = (canvas - th)//2 + offset_r*10 - bbox[1]
    d.text((x, y), letter, fill=255, font=font)
    mask = set()
    for r in range(N):
        for c in range(N):
            px, py = c*10+5, r*10+5
            if 0 <= px < canvas and 0 <= py < canvas and img.getpixel((px, py)) > 128:
                mask.add((r, c))
    return mask

def get_qs_mask(sz=14, qc=-4, sc=4):
    return get_letter_mask("Q", sz, offset_c=qc) | get_letter_mask("S", sz, offset_c=sc)

def is_center(r, c, radius=4):
    mid = N // 2
    return abs(r - mid) <= radius and abs(c - mid) <= radius

def draw_center_badge(draw, text="QS", bg=BRAND_BLUE, fg=WHITE, h_rad=5, v_rad=4):
    mid = N // 2
    x0 = PAD + (mid - h_rad) * MOD
    y0 = PAD + (mid - v_rad) * MOD
    x1 = PAD + (mid + h_rad + 1) * MOD
    y1 = PAD + (mid + v_rad + 1) * MOD
    draw.rounded_rectangle([x0, y0, x1, y1], radius=MOD, fill=bg)
    font = ImageFont.truetype(BOLD_FONT, int(MOD * v_rad * 1.4))
    bbox = font.getbbox(text)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    cx, cy = (x0+x1)//2, (y0+y1)//2
    draw.text((cx-tw//2-bbox[0], cy-th//2-bbox[1]), text, fill=fg, font=font)

def finalize(img, name, desc):
    path = os.path.join(OUT_DIR, f"{name}.png")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, WHITE)
        bg.paste(img, mask=img.split()[3])
        img = bg
    final = img.resize((IMG_W // SUPERSAMPLE, IMG_H // SUPERSAMPLE), Image.LANCZOS)
    final.save(path)
    results = pyzbar_decode(final)
    if not results:
        results = pyzbar_decode(final.convert("L"))
    ok = any(r.data.decode("utf-8") == URL for r in results) if results else False
    status = "SCAN" if ok else "FAIL"
    print(f"{name}: {status} - {desc}")
    return (name, status, desc)


# ============================================================
# VARIANTS
# ============================================================

def variant_L01():
    """Large blue Q in center, blue S bottom-right."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    draw_data(draw, skip_fn=lambda r,c: is_center(r,c, 4))

    font = ImageFont.truetype(BOLD_FONT, int(MOD * 7))
    cx, cy = qr_center()
    bbox = font.getbbox("Q")
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((cx-tw//2-bbox[0], cy-th//2-bbox[1]-MOD//2), "Q", fill=BRAND_BLUE, font=font)

    sfont = ImageFont.truetype(BOLD_FONT, int(MOD * 3.5))
    sx = PAD + (N-5)*MOD
    sy = PAD + (N-5)*MOD
    draw.text((sx, sy), "S", fill=BRAND_BLUE, font=sfont)

    return finalize(img, "L01", "Large blue Q center + blue S bottom-right")

def variant_L02():
    """QS badge on blue rounded rect center."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    draw_data(draw, skip_fn=lambda r,c: is_center(r,c, 5))
    draw_center_badge(draw, "QS", BRAND_BLUE, WHITE, 5, 4)
    return finalize(img, "L02", "QS on blue rounded rect center (PayPal style)")

def variant_L03():
    """QS formed by forced-on blue dots."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)

    q_mask = get_letter_mask("Q", 12, offset_c=-2)
    s_mask = get_letter_mask("S", 10, offset_c=6, offset_r=2)
    qs = {(r,c) for r,c in (q_mask | s_mask) if not is_finder(r,c)}

    draw_data(draw, color_fn=lambda r,c: BRAND_BLUE if (r,c) in qs else BLACK, force_on=qs)
    return finalize(img, "L03", "QS made of forced-on blue dots")

def variant_L04():
    """Finder Q-tails + blue S center."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)

    for fr, fc in FINDERS:
        draw_standard_finder(draw, fr, fc)
        tx = PAD + (fc+5)*MOD + MOD//2
        ty = PAD + (fr+5)*MOD + MOD//2
        draw.line([tx, ty, tx+int(MOD*1.5), ty+int(MOD*1.5)], fill=BLACK, width=MOD//2)

    draw_data(draw, skip_fn=lambda r,c: is_center(r,c, 3))

    font = ImageFont.truetype(BOLD_FONT, int(MOD * 5))
    cx, cy = qr_center()
    bbox = font.getbbox("S")
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((cx-tw//2-bbox[0], cy-th//2-bbox[1]), "S", fill=BRAND_BLUE, font=font)

    return finalize(img, "L04", "Q-tail finders + blue S center")

def variant_L05():
    """Negative space QS carved from data modules."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = {(r,c) for r,c in get_qs_mask(11, -4, 4) if not is_finder(r,c)}
    draw_data(draw, skip_fn=lambda r,c: (r,c) in qs)
    return finalize(img, "L05", "Negative space QS (white letters in dots)")

def variant_L06():
    """Dot-size QS: large=letters, small=background."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(14, -4, 4)

    draw_data(draw, size_fn=lambda r,c: 0.95 if (r,c) in qs else 0.55,
              shape=lambda r,c: "circle")
    return finalize(img, "L06", "Dot-size QS (large=letters, small=bg)")

def variant_L07():
    """Color QS: blue letter dots, black rest."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(14, -4, 4)
    draw_data(draw, color_fn=lambda r,c: BRAND_BLUE if (r,c) in qs else BLACK)
    return finalize(img, "L07", "Color QS (blue letter dots, black rest)")

def variant_L08():
    """Shape QS: squares=letters, rounded=background."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(14, -4, 4)
    draw_data(draw, shape=lambda r,c: "square" if (r,c) in qs else "rounded",
              size_fn=lambda r,c: 0.88 if (r,c) in qs else None)
    return finalize(img, "L08", "Shape QS (squares=letters, rounded=bg)")

def variant_L09():
    """Faint QS watermark behind QR modules."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(BOLD_FONT, int(MOD * 16))
    cx, cy = qr_center()
    bbox = font.getbbox("QS")
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((cx-tw//2-bbox[0], cy-th//2-bbox[1]), "QS", fill=(215, 225, 245), font=font)

    draw_all_finders(draw, etched=True)
    draw_data(draw)
    return finalize(img, "L09", "QS watermark behind QR dots")

def variant_L10():
    """Combined color+size QS modulation."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(14, -4, 4)

    draw_data(draw,
        color_fn=lambda r,c: BRAND_BLUE if (r,c) in qs else (60, 60, 60),
        size_fn=lambda r,c: 0.95 if (r,c) in qs else 0.6,
        shape=lambda r,c: "circle")
    return finalize(img, "L10", "Combined color+size QS (blue large vs gray small)")

def variant_L11():
    """Q in blue circle center + S outlined by blue dots."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)

    s_mask = {(r,c) for r,c in get_letter_mask("S", 13, offset_c=5, offset_r=2) if not is_finder(r,c)}
    draw_data(draw,
        skip_fn=lambda r,c: is_center(r,c, 3),
        color_fn=lambda r,c: BRAND_BLUE if (r,c) in s_mask else BLACK)

    cx, cy = qr_center()
    radius = int(3.5 * MOD)
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=BRAND_BLUE)
    font = ImageFont.truetype(BOLD_FONT, int(MOD * 4.5))
    bbox = font.getbbox("Q")
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((cx-tw//2-bbox[0], cy-th//2-bbox[1]), "Q", fill=WHITE, font=font)

    return finalize(img, "L11", "White Q in blue circle + blue S dots")

def variant_L12():
    """Gradient blue QS dots."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(14, -4, 4)

    def color_fn(r, c):
        if (r,c) in qs:
            t = c / N
            return tuple(int(DARK_BLUE[i] + (BRAND_BLUE[i]-DARK_BLUE[i])*t) for i in range(3))
        return BLACK

    draw_data(draw, color_fn=color_fn,
        size_fn=lambda r,c: 0.95 if (r,c) in qs else 0.65,
        shape=lambda r,c: "circle")
    return finalize(img, "L12", "Gradient blue QS dots + size modulation")

def variant_L13():
    """Compact center QS badge."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    draw_data(draw, skip_fn=lambda r,c: is_center(r,c, 4))
    draw_center_badge(draw, "QS", BRAND_BLUE, WHITE, 4, 3)
    return finalize(img, "L13", "Compact center QS badge (more data)")

def variant_L14():
    """QS badge center + color hint in surrounding dots."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = get_qs_mask(16, -5, 5)

    draw_data(draw,
        skip_fn=lambda r,c: is_center(r,c, 4),
        color_fn=lambda r,c: BRAND_BLUE if (r,c) in qs else (50, 50, 50),
        size_fn=lambda r,c: 0.9 if (r,c) in qs else 0.65,
        shape=lambda r,c: "circle")
    draw_center_badge(draw, "QS", BRAND_BLUE, WHITE, 4, 3)
    return finalize(img, "L14", "QS badge + QS-hinted dot colors/sizes")

def variant_L15():
    """Triple modulation: blue diamonds QS + gray circles bg + forced."""
    img = Image.new("RGB", (IMG_W, IMG_H), WHITE)
    draw = ImageDraw.Draw(img)
    draw_all_finders(draw, etched=True)
    qs = {(r,c) for r,c in get_qs_mask(14, -4, 4) if not is_finder(r,c)}

    draw_data(draw,
        color_fn=lambda r,c: BRAND_BLUE if (r,c) in qs else (40, 40, 40),
        size_fn=lambda r,c: 0.95 if (r,c) in qs else 0.55,
        shape=lambda r,c: "diamond" if (r,c) in qs else "circle",
        force_on=qs)
    return finalize(img, "L15", "Triple: blue diamonds QS + gray circles bg")


# ============================================================
all_variants = [
    variant_L01, variant_L02, variant_L03, variant_L04, variant_L05,
    variant_L06, variant_L07, variant_L08, variant_L09, variant_L10,
    variant_L11, variant_L12, variant_L13, variant_L14, variant_L15,
]

results = []
for fn in all_variants:
    try:
        results.append(fn())
    except Exception as e:
        import traceback
        traceback.print_exc()
        name = fn.__name__.replace("variant_", "")
        results.append((name, "ERROR", str(e)))

print("\n" + "=" * 75)
print(f"{'Name':<6} {'Status':<7} {'Description'}")
print("-" * 75)
for name, status, desc in results:
    print(f"{name:<6} {status:<7} {desc}")
print("=" * 75)
sc = sum(1 for _,s,_ in results if s == "SCAN")
fl = sum(1 for _,s,_ in results if s == "FAIL")
er = sum(1 for _,s,_ in results if s == "ERROR")
print(f"Total: {sc} SCAN, {fl} FAIL, {er} ERROR out of {len(results)}")
