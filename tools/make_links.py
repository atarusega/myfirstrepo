"""Персональные ссылки на сайт для агентств и HR — чтобы в Метрике было видно, кто открыл.

Берёт получателей из tools/recipients.txt (по одному в строке, # — комментарий),
переводит имя в латиницу и нижний регистр, пробелы → «_», и печатает ссылки вида
  https://struktorum.space/?utm_source=<имя>&utm_medium=direct&utm_campaign=portfolio_2026
Результат также пишет в tools/links.csv (получатель;ссылка), CSV открывается в Excel.

Запуск из корня репозитория:  py tools/make_links.py
Свой файл или кампания:       py tools/make_links.py список.txt --campaign portfolio_2027

recipients.txt и links.csv в git не попадают (.gitignore) — репозиторий публичный.
"""
import argparse
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
SITE = "https://struktorum.space/"

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slug(name: str) -> str:
    """«Родня Агентство» → rodnya_agentstvo; всё, кроме a-z, 0-9, _ и -, выбрасывается."""
    s = "".join(TRANSLIT.get(ch, ch) for ch in name.strip().lower())
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_-]", "", s)
    return re.sub(r"_+", "_", s).strip("_-")


def main() -> None:
    ap = argparse.ArgumentParser(description="Персональные UTM-ссылки на struktorum.space")
    ap.add_argument("recipients", nargs="?", default=HERE / "recipients.txt", type=Path)
    ap.add_argument("--out", default=HERE / "links.csv", type=Path)
    ap.add_argument("--campaign", default="portfolio_2026")
    ap.add_argument("--medium", default="direct")
    args = ap.parse_args()

    if not args.recipients.exists():
        sys.exit(f"Нет файла {args.recipients}. Создай его по образцу tools/recipients.example.txt")

    rows, seen = [], set()
    for raw in args.recipients.read_text(encoding="utf-8-sig").splitlines():
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        source = slug(name)
        if not source:
            print(f"! пропуск «{name}»: после перевода в латиницу имя пустое", file=sys.stderr)
            continue
        if source in seen:
            print(f"! пропуск «{name}»: метка {source} уже есть", file=sys.stderr)
            continue
        seen.add(source)
        query = urlencode({"utm_source": source, "utm_medium": args.medium, "utm_campaign": args.campaign})
        rows.append((source, f"{SITE}?{query}"))

    # utf-8-sig — чтобы Excel сам понял кодировку; разделитель «;» — как в русском Excel
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["получатель", "ссылка"])
        w.writerows(rows)

    for source, url in rows:
        print(f"{source};{url}")
    print(f"\n{len(rows)} ссылок → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
