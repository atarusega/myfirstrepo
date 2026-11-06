"""Скрытая страница «История дизайна» → struktorum.space/history/.
Копирует из C:/Users/PC/design-history/site: data.js, design/*.html, img/* (ужимает до 600 px, JPEG 80).
Ссылок с главной нет, страницы с noindex. Запуск: python tools/sync_history.py, затем коммит и пуш."""
import os, shutil, glob
from PIL import Image

SRC = "C:/Users/PC/design-history/site"
DST = os.path.join(os.path.dirname(__file__), "..", "app", "public", "history")
os.makedirs(os.path.join(DST, "img"), exist_ok=True); os.makedirs(os.path.join(DST, "design"), exist_ok=True)

shutil.copy(os.path.join(SRC, "data.js"), DST)
pages = []
for f in glob.glob(os.path.join(SRC, "design", "*.html")):
    shutil.copy(f, os.path.join(DST, "design")); pages.append(os.path.basename(f))

src_names = set(os.listdir(os.path.join(SRC, "img")))
for f in os.listdir(os.path.join(DST, "img")):  # картинки, убранные из базы (чужие совпадения), удалить и с сайта
    if f not in src_names: os.remove(os.path.join(DST, "img", f)); print("  удалена", f)

n = 0
for f in glob.glob(os.path.join(SRC, "img", "*")):
    name = os.path.basename(f); out = os.path.join(DST, "img", name)
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(f): continue
    try:
        im = Image.open(f); im.thumbnail((600, 600))
        if name.endswith(".png"): im.save(out, optimize=True)
        else: im.convert("RGB").save(out, quality=80, optimize=True)
        n += 1
    except Exception as e:
        print("  !", name, e)

links = "".join(f'<li><a href="design/{p}">{p}</a></li>' for p in sorted(pages))
open(os.path.join(DST, "index.html"), "w", encoding="utf-8").write(
    f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
    f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>История дизайна — макеты</title>'
    f'<meta http-equiv="refresh" content="0;url=design/{sorted(pages)[0]}"><ul>{links}</ul>')
print(f"страниц {len(pages)}, новых картинок {n}")
