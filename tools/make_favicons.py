"""Генерирует фавиконки из знака STRUKTORUM (цветная «подушка» из 5 кругов)
в app/public/. Запуск: python tools/make_favicons.py"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "app" / "public"
BLUE = "#3A3ED8"
# Знак из фирменного стиля: (cx, cy, r, цвет) в поле 200×200
CIRCLES = [(100, 100, 100, "#F2642A"), (108, 106, 84, "#9FE3D4"), (116, 113, 67, "#3A3ED8"),
           (128, 122, 42, "#D9BDF2"), (134, 127, 24, "#F2B31A")]

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
       + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>' for x, y, r, c in CIRCLES)
       + "</svg>\n")

def mark(size, bg=None, scale=1.0):
    """Знак size×size; bg — заливка фона, scale — доля знака от стороны."""
    ss = 8  # суперсэмплинг для гладких краёв
    S = size * ss
    im = Image.new("RGBA", (S, S), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = S * scale / 200
    off = S * (1 - scale) / 2
    for x, y, r, c in CIRCLES:
        d.ellipse([off + (x - r) * k, off + (y - r) * k, off + (x + r) * k, off + (y + r) * k], fill=c)
    return im.resize((size, size), Image.LANCZOS)

def main():
    (OUT / "favicon.svg").write_text(SVG, encoding="utf-8")
    mark(48).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    mark(32).save(OUT / "favicon-32.png")
    # Для iOS и Android — знак на синем, как аватар в Telegram (прозрачность там не поддерживается)
    mark(180, BLUE, 0.72).convert("RGB").save(OUT / "apple-touch-icon.png")
    mark(192, BLUE, 0.72).save(OUT / "icon-192.png")
    mark(512, BLUE, 0.72).save(OUT / "icon-512.png")
    (OUT / "site.webmanifest").write_text(
        '{\n  "name": "STRUKTORUM",\n  "short_name": "STRUKTORUM",\n'
        '  "icons": [\n    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },\n'
        '    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }\n  ],\n'
        '  "theme_color": "#000000",\n  "background_color": "#000000",\n  "display": "standalone"\n}\n',
        encoding="utf-8")
    print("ok:", ", ".join(sorted(p.name for p in OUT.iterdir() if p.is_file())))

if __name__ == "__main__":
    main()
