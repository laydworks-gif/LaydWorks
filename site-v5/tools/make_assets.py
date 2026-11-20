#!/usr/bin/env python3
"""Готує зображення й іконки для сайту (потрібен Pillow). Запускається вручну, коли змінюються фото:

    python tools/make_assets.py

Вихідні JPG лежать у tools/originals/. Результат: images/*.webp, images/og.jpg, favicon.*, apple-touch-icon.png, icon-*.png.
"""
import pathlib
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIG = ROOT / 'tools' / 'originals'
IMG = ROOT / 'images'
IMG.mkdir(exist_ok=True)

INK, LAMP, PAPER = (15, 19, 22), (227, 154, 18), (241, 242, 239)


def webp(im, dst, q=80):
    im.save(dst, 'WEBP', quality=q, method=6)
    print('  %-22s %6.0f KB' % (dst.name, dst.stat().st_size / 1024))


# --- hero: три ширини для srcset
hero = Image.open(ORIG / 'hero.jpg').convert('RGB')
for w in (800, 1200, 1600):
    h = round(hero.height * w / hero.width)
    webp(hero.resize((w, h), Image.LANCZOS) if w < hero.width else hero, IMG / ('hero-%d.webp' % w), 78)

# --- галерея: той самий розмір, але WebP
for i in range(1, 8):
    im = Image.open(ORIG / ('gallery-%d.jpg' % i)).convert('RGB')
    k = 1000 / max(im.size)
    if k < 1:  # пропорції не змінюються, тож width/height у HTML лишаються коректними
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    webp(im, IMG / ('gallery-%d.webp' % i), 74)


# --- Open Graph 1200x630 (фото студії + підпис)
def font(size, bold=True):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


ph = Image.open(ORIG / 'gallery-4.jpg').convert('RGB')
W, H = 1200, 630
top = int((ph.height - H) * 0.45)
og = ph.crop((0, top, W, top + H))
shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(shade)
for y in range(H):
    a = int(235 * max(0, (y - H * 0.38) / (H * 0.62)) ** 1.3)
    d.line([(0, y), (W, y)], fill=INK + (a,))
og = Image.alpha_composite(og.convert('RGBA'), shade).convert('RGB')
d = ImageDraw.Draw(og)
d.rectangle([64, 452, 64 + 56, 452 + 8], fill=LAMP)
d.text((64, 474), 'AutoPolish', font=font(64), fill=(255, 255, 255))
d.text((64, 556), 'Детейлінг у Дніпрі · вул. Стара Пристань, 6', font=font(30, False), fill=(222, 226, 228))
og.save(IMG / 'og.jpg', 'JPEG', quality=84, optimize=True, progressive=True)
print('  og.jpg                 %6.0f KB' % ((IMG / 'og.jpg').stat().st_size / 1024))


# --- іконки: темний округлений квадрат + бурштинове коло (як у вшитому SVG)
def icon(size, radius_ratio=0.25, pad=0.0):
    s = size * 4
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * radius_ratio), fill=INK + (255,))
    r = s * 0.22
    c = s / 2
    dr.ellipse([c - r, c - r, c + r, c + r], fill=LAMP + (255,))
    return im.resize((size, size), Image.LANCZOS)


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0F1316"/>'
       '<circle cx="16" cy="16" r="7" fill="#E39A12"/></svg>\n')
(ROOT / 'favicon.svg').write_text(SVG, encoding='utf-8')
icon(48).save(ROOT / 'favicon-48.png')
icon(180, 0.0).save(ROOT / 'apple-touch-icon.png')       # iOS сам заокруглює кути
icon(192).save(ROOT / 'icon-192.png')
icon(512).save(ROOT / 'icon-512.png')
icon(256).save(ROOT / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
print('  іконки готові')
