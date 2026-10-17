"""Обложки-миниатюры для WebGL-сетки: app/public/images/<id>/cover.webp — квадрат COVER px.
Галерея грузит их вместо полноразмерных 01.jpg (~120 КБ → ~25 КБ на проект), и сетка
появляется за доли секунды. В projects.json у проекта появляется поле "cover".
Запуск: python tools/make_covers.py (sync_telegram.py вызывает его сам)."""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "app" / "public" / "images"
DATA = ROOT / "app" / "src" / "data" / "projects.json"
COVER = 480  # сторона квадрата; в сетке картинка ≤ ~250 css px, хватает и на Retina


def make_cover(folder: Path, src: str = "01.jpg") -> Path:
    """Центральный квадрат из первого фото → cover.webp. Сетка и так кропит в квадрат."""
    im = Image.open(folder / src).convert("RGB")
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    im = im.crop((left, top, left + side, top + side)).resize((COVER, COVER), Image.LANCZOS)
    out = folder / "cover.webp"
    im.save(out, "WEBP", quality=80, method=6)
    return out


def main():
    projects = json.loads(DATA.read_text(encoding="utf-8"))
    total = 0
    for p in projects:
        out = make_cover(IMAGES / str(p["id"]))
        p["cover"] = f"images/{p['id']}/cover.webp"
        total += out.stat().st_size
        print(p["id"], f"{out.stat().st_size // 1024} КБ")
    DATA.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"итого {total // 1024} КБ на {len(projects)} обложек")


if __name__ == "__main__":
    main()
