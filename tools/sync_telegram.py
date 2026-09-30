"""Тянет посты канала t.me/struktorum, качает фото в app/public/images/<id>/
и пишет app/src/data/projects.json для React-сайта.
Запуск: python tools/sync_telegram.py"""
import html, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
IMAGES = APP / "public" / "images"
DATA = APP / "src" / "data" / "projects.json"
CHANNEL = "struktorum"
# Порядок = порядок на сайте. 443 — дубль 437, 378 — дубль 380 (T-Sync), их не берём.
POSTS = [444, 437, 428, 420, 411, 401, 380, 357, 342, 337, 329, 320, 242, 216,
         193, 185, 180, 171, 164, 110, 65]

# Названия из списка заказчика (в постах они бывают с эмодзи или без названия)
TITLES = {428: "Сбер × Фесты '26", 444: "Яндекс Маркет × Маркет '26", 437: "Т-Банк × ИТ Пикник '26",
          420: "infra.conf '26", 411: "Индилайт × Фесты '26", 401: "Яндекс Еда × Тема Еды '26",
          380: "T-Sync Conf × N:OW", 357: "Концепции для ТЦ", 342: "ФиксиФест × ЦДМ",
          337: "Haier × Fest", 329: "Encore × Resort", 320: "Yandex × ICTV",
          242: "ТБизнес × Family Day", 216: "Лента × Чтиво", 193: "Сбер × Фесты",
          185: "Сфера × Х5", 180: "Балтика × Фесты", 171: "Т2 × Фесты",
          164: "МТС", 110: "Альфа-банк", 65: "Т2 концепт"}

def accent(path):
    """Насыщенный цвет обложки для подписи: средний по ярким цветным пикселям."""
    import colorsys
    from PIL import Image
    im = Image.open(path).convert("RGB").resize((48, 48))
    acc = [0, 0, 0]; w = 0
    for r, g, b in im.get_flattened_data():
        h, sat, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        wt = sat * sat * v if 0.25 < v < 0.98 else 0
        acc[0] += r * wt; acc[1] += g * wt; acc[2] += b * wt; w += wt
    if w < 1:  # почти ч/б обложка
        return "#f2f1ec", "#111111"
    r, g, b = (c / w / 255 for c in acc)
    h, sat, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, min(1, max(sat, 0.55)), min(1, max(v, 0.85)))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return ("#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255)),
            "#111111" if lum > 0.55 else "#ffffff")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read()

def parse(post_id):
    page = get(f"https://t.me/{CHANNEL}/{post_id}?embed=1&mode=tme").decode("utf-8")
    m = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', page, re.S)
    raw = m.group(1) if m else ""
    lines = [html.unescape(re.sub(r"<[^>]+>", "", l)).strip()
             for l in re.split(r"<br\s*/?>", raw)]
    lines = [re.sub(r"\s+", " ", l) for l in lines if l.strip()]
    title = re.sub(r"^[^\w«\"']+", "", lines[0]) if lines else f"Пост {post_id}"
    photos = re.findall(r"message_photo[^>]*background-image:url\('([^']+)'\)", page)
    date = re.search(r'datetime="([^"]+)"', page)
    return {"id": post_id, "title": TITLES.get(post_id, title), "text": lines[1:],
            "date": date.group(1)[:10] if date else "",
            "url": f"https://t.me/{CHANNEL}/{post_id}", "photos": photos}

def main():
    projects = []
    for pid in POSTS:
        p = parse(pid)
        folder = IMAGES / str(pid)
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for i, u in enumerate(p.pop("photos"), 1):
            f = folder / f"{i:02d}.jpg"
            if not f.exists():
                f.write_bytes(get(u))
            files.append(f"images/{pid}/{f.name}")
        p["images"] = files
        p["color"], p["textColor"] = accent(folder / "01.jpg")
        projects.append(p)
        print(pid, p["title"], len(files))
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
