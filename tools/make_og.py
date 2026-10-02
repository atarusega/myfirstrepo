"""Картинка превью ссылки (Open Graph) 1200×630 в фирменном стиле: app/public/og.jpg.
Шрифт Unbounded берётся из node_modules (@fontsource) и переводится из woff2 в ttf.
Запуск: python tools/make_og.py"""
import io
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
FONTS = APP / "node_modules" / "@fontsource" / "unbounded" / "files"
OUT = APP / "public" / "og.jpg"

W, H = 1200, 630
BLUE, SOFT, WHITE = "#3A3ED8", "#C9CBF5", "#FFFFFF"
CIRCLES = [(100, 100, 100, "#F2642A"), (108, 106, 84, "#9FE3D4"), (116, 113, 67, "#3A3ED8"),
           (128, 122, 42, "#D9BDF2"), (134, 127, 24, "#F2B31A")]
# Обложки для нижнего ряда: id постов
COVERS = [444, 437, 428, 110, 411]


def load_font(weight, size):
    """Кириллица и латиница у @fontsource лежат в разных файлах — возвращаем обе."""
    fonts = {}
    for subset in ("latin", "cyrillic"):
        tt = TTFont(FONTS / f"unbounded-{subset}-{weight}-normal.woff2")
        tt.flavor = None
        buf = io.BytesIO()
        tt.save(buf)
        tmp = Path(tempfile.gettempdir()) / f"unbounded-{subset}-{weight}.ttf"
        tmp.write_bytes(buf.getvalue())
        fonts[subset] = (ImageFont.truetype(str(tmp), size), set(tt.getBestCmap() or {}))
    return fonts


def draw_text(d, xy, text, fonts, fill, spacing=0.0):
    """Посимвольно: подбираем файл шрифта, где есть глиф, и добавляем разрядку."""
    x, y = xy
    for ch in text:
        font = fonts["cyrillic"][0] if ord(ch) in fonts["cyrillic"][1] and ord(ch) not in fonts["latin"][1] else fonts["latin"][0]
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + font.size * spacing
    return x


def mark(size):
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = S / 200
    for x, y, r, c in CIRCLES:
        d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=c)
    return im.resize((size, size), Image.LANCZOS)


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius=radius, fill=255)
    img.putalpha(mask)
    return img


def main():
    im = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(im)

    # Знак + слово STRUKTORUM (700, разрядка +8%), под ним подпись (500, +6%)
    m = mark(132)
    im.paste(m, (72, 88), m)
    draw_text(d, (232, 104), "STRUKTORUM", load_font(700, 76), WHITE, spacing=0.08)
    draw_text(d, (236, 198), "3D-визуализация событийных пространств", load_font(500, 25), SOFT, spacing=0.06)

    # Нижний ряд — обложки проектов со скруглением, как карточки в брендбуке
    size, gap, top = 196, 22, 288
    left = (W - (len(COVERS) * size + (len(COVERS) - 1) * gap)) // 2
    for i, pid in enumerate(COVERS):
        cover = ImageOps.fit(Image.open(APP / "public" / "images" / str(pid) / "01.jpg").convert("RGB"), (size * 2, size * 2))
        cover = rounded(cover.convert("RGBA"), 28).resize((size, size), Image.LANCZOS)
        im.paste(cover, (left + i * (size + gap), top), cover)

    draw_text(d, (left, top + size + 34), "STRUKTORUM.SPACE", load_font(500, 20), SOFT, spacing=0.1)
    im.save(OUT, quality=88, optimize=True)
    print("ok:", OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
