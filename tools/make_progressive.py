"""Переводит все JPEG сайта (app/public) в прогрессивные: на медленной сети сначала виден размытый
кадр целиком, потом он дорисовывается. Пересохраняет с исходными таблицами квантования
(quality="keep") — потеря ~45–65 дБ PSNR, глазом не видна; файлы на ~5 % меньше.
Уже прогрессивные файлы и историю дизайна (history/) не трогает. Запуск: python tools/make_progressive.py [папка ...]"""
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "app" / "public"
# История дизайна не трогаем (решение Никиты): её картинки готовит свой конвейер sync_history.py
SKIP = [PUBLIC / "history"]


def is_progressive(im: Image.Image) -> bool:
    return bool(im.info.get("progressive") or im.info.get("progression"))


def progressive_bytes(im: Image.Image) -> bytes:
    """JPEG → прогрессивный JPEG с теми же таблицами квантования и субдискретизацией."""
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality="keep", subsampling="keep", progressive=True, optimize=True,
            exif=im.info.get("exif", b""), icc_profile=im.info.get("icc_profile"))
    return buf.getvalue()


def make_progressive(path: Path) -> tuple[int, int] | None:
    """Пересохраняет файл на месте. Возвращает (было, стало) в байтах или None, если уже прогрессивный."""
    with Image.open(path) as im:
        if im.format != "JPEG" or is_progressive(im):
            return None
        data = progressive_bytes(im)
    before = path.stat().st_size
    path.write_bytes(data)
    return before, len(data)


def main(dirs: list[Path]):
    done = skipped = before = after = 0
    for d in dirs:
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() not in (".jpg", ".jpeg"):
                continue
            if any(f.resolve().is_relative_to(s) for s in SKIP):
                continue
            res = make_progressive(f)
            if res is None:
                skipped += 1
                continue
            done += 1
            before += res[0]
            after += res[1]
    print(f"переведено {done}, уже были прогрессивными {skipped}; "
          f"{before / 1e6:.1f} → {after / 1e6:.1f} МБ")


if __name__ == "__main__":
    main([Path(a) for a in sys.argv[1:]] or [PUBLIC])
