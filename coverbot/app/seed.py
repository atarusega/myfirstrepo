"""Демо-группы для показа партнёру. Запуск: python -m app.seed   Удалить: python -m app.seed --clear"""
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import delete

from app.db import Band, Session, init_db

DEMO = [
    dict(name="[Демо] Neon Party Band", city="Москва", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_m", "vocal_f", "guitar", "bass", "drums"], genres=["dance_mix", "pop", "ru_hits", "foreign_hits"],
         description="Танцевальные хиты 2000–2020-х, живой звук, раскачиваем зал с первой песни.",
         price_private=70000, price_corporate=90000, price_newyear=130000, program_format="2x45", sound="included",
         services=["dj", "custom_song"]),
    dict(name="[Демо] Brass & Soul", city="Москва", travel_scope="russia", lineup="band_6_plus",
         instruments=["vocal_f", "guitar", "bass", "drums", "sax", "brass"], genres=["disco_funk", "jazz_lounge", "foreign_hits"],
         description="Фанк и соул с духовой секцией, лаунж на ужин и диско на танцы. Работаем на крупных корпоративах.",
         price_private=150000, price_corporate=180000, price_newyear=250000, program_format="3x45", sound="included",
         services=["welcome", "extra_lineup", "own_light"]),
    dict(name="[Демо] Акустика на двоих", city="Москва", travel_scope="region", lineup="duo",
         instruments=["vocal_f", "guitar"], genres=["acoustic", "pop", "ru_hits"],
         description="Нежный акустический дуэт: церемонии, welcome-зона, камерные ужины.",
         price_private=25000, price_corporate=35000, price_newyear=None, program_format="hourly", sound="included",
         services=["welcome", "ceremony", "custom_song"]),
    dict(name="[Демо] Рок-н-ролл 90", city="Московская область", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_m", "guitar", "bass", "drums"], genres=["rock", "retro", "ru_hits"],
         description="Русский рок и хиты 80–90-х: Кино, Сплин, Би-2, Чайф. Для юбилеев и корпоративов.",
         price_private=50000, price_corporate=65000, price_newyear=90000, program_format="2x45", sound="extra",
         services=["theme_show"]),
    dict(name="[Демо] Mash Up Crew", city="Москва", travel_scope="russia", lineup="band_6_plus",
         instruments=["vocal_m", "vocal_f", "guitar", "bass", "drums", "keys", "violin"],
         genres=["mashup", "dance_mix", "pop", "foreign_hits"],
         description="Мэшапы хитов: два трека в одном, 40+ песен за вечер. Свадьбы и корпоративы.",
         price_private=90000, price_corporate=120000, price_newyear=170000, program_format="3x30", sound="included",
         services=["dj", "mc", "extra_lineup"]),
    dict(name="[Демо] Невские Струны", city="Санкт-Петербург", travel_scope="region", lineup="trio",
         instruments=["vocal_f", "keys", "violin"], genres=["instrumental", "jazz_lounge", "acoustic"],
         description="Инструментальные каверы и джаз для приёмов, ресторанов и свадебных церемоний.",
         price_private=40000, price_corporate=55000, price_newyear=75000, program_format="3x45", sound="included",
         services=["welcome", "ceremony"]),
]


async def main(clear: bool):
    await init_db()
    async with Session() as s:
        await s.execute(delete(Band).where(Band.source == "demo"))
        if not clear:
            now = datetime.now(timezone.utc)
            for d in DEMO:
                s.add(Band(**d, source="demo", status="published", video_links=["https://youtube.com/"],
                           tg_username="demo_band_contact", consent_at=now, prices_confirmed_at=now))
        await s.commit()
    print("Демо-группы удалены" if clear else f"Добавлено демо-групп: {len(DEMO)}")


if __name__ == "__main__":
    asyncio.run(main("--clear" in sys.argv))
