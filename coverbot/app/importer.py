"""Импорт базы партнёра «Тут все» (только по договорённости с владельцем).

Использование:
    python -m app.importer data/tutvse.csv
Результат: карточки-черновики в БД + data/invite_links.csv со ссылками для рассылки резидентам.
Карточка попадает в поиск только после того, как музыкант перейдёт по ссылке, дозаполнит анкету
и даст согласие, а админ её одобрит.
"""
import asyncio
import csv
import re
import secrets
import sys
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db import Band, Session, init_db

MUSIC_RE = re.compile(
    r"кавер|cover|групп|бэнд|band|музык|вокал|певи|певец|гитар|саксоф|скрип|барабан|клавиш|ансамбл|дуэт|трио",
    re.I,
)

# Колонки формы «База партнёров»; при другой выгрузке поправьте названия здесь
COL = {
    "name": "Имя Фамилия",
    "spec": "Специализация",
    "company": "Компания",
    "city": "Город",
    "phone": "Телефон",
    "telegram": "Телеграм",
    "links": "Ссылки",
    "social": "Соцсети",
}


def _get(row: dict, key: str) -> str:
    wanted = COL[key].lower()
    for k, v in row.items():
        if k and k.strip().lower() == wanted:
            return (v or "").strip()
    return ""


async def run(path: str):
    await init_db()
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    out_rows, skipped, created = [], 0, 0
    async with Session() as s:
        for row in rows:
            spec = _get(row, "spec")
            if not MUSIC_RE.search(spec):
                skipped += 1
                continue
            tg = _get(row, "telegram").lstrip("@").replace("https://t.me/", "")
            name = _get(row, "company") or _get(row, "name")
            if tg:
                exists = (await s.execute(
                    select(Band).where(Band.tg_username == tg, Band.source == "tutvse")
                )).scalar_one_or_none()
                if exists:
                    skipped += 1
                    continue
            token = secrets.token_urlsafe(9)
            links = re.findall(r"https?://\S+", _get(row, "links") + " " + _get(row, "social"))
            band = Band(
                name=name[:200] or "Без названия",
                city=_get(row, "city") or None,
                phone=_get(row, "phone") or None,
                tg_username=tg or None,
                website=(links[0] if links else None),
                video_links=[],
                instruments=[],
                genres=[],
                services=[],
                source="tutvse",
                source_note=spec[:500],
                claim_token=token,
                status="draft",
            )
            s.add(band)
            created += 1
            out_rows.append({
                "Имя": _get(row, "name"),
                "Проект": name,
                "Телеграм": f"@{tg}" if tg else "",
                "Специализация": spec,
                "Ссылка": f"https://t.me/{settings.bot_username}?start=tv_{token}",
            })
        await s.commit()
    out = Path("data/invite_links.csv")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Имя", "Проект", "Телеграм", "Специализация", "Ссылка"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"Создано черновиков: {created}, пропущено (не музыканты или дубли): {skipped}")
    print(f"Ссылки для рассылки: {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Укажите путь к CSV: python -m app.importer data/tutvse.csv")
    asyncio.run(run(sys.argv[1]))
