"""Демо-группы для показа и проверки поиска: в названии «[Демо]», source="demo".
Запуск: python -m app.seed   Удалить все демо-группы (настоящие анкеты не трогает): python -m app.seed --clear"""
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
    # --- ещё 10 для проверки фильтров: другие города, крайние цены, выезд, редкие инструменты ---
    dict(name="[Демо] Казань Live", city="Казань", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_m", "vocal_f", "guitar", "bass", "drums"], genres=["dance_mix", "pop", "ru_hits"],
         description="Танцевальные хиты на русском и татарском, свадьбы и корпоративы по Татарстану.",
         price_private=45000, price_corporate=60000, price_newyear=85000, program_format="2x45", sound="included",
         services=["dj", "mc"]),
    dict(name="[Демо] Уральский Драйв", city="Екатеринбург", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_m", "guitar", "bass", "drums", "keys"], genres=["rock", "foreign_hits", "retro"],
         description="Рок-хиты от Queen до Arctic Monkeys и русский рок. Громко, живо, с настоящим драйвом.",
         price_private=55000, price_corporate=70000, price_newyear=100000, program_format="3x30", sound="extra",
         services=["theme_show"]),
    dict(name="[Демо] Сибирский Джаз", city="Новосибирск", travel_scope="city", lineup="trio",
         instruments=["vocal_f", "keys", "sax"], genres=["jazz_lounge", "acoustic", "foreign_hits"],
         description="Джаз-трио с саксофоном: фоновая музыка на ужин, лаунж, свинг. Только по Новосибирску.",
         price_private=35000, price_corporate=45000, price_newyear=None, program_format="hourly", sound="included",
         services=["welcome"]),
    dict(name="[Демо] Сочи Summer Band", city="Сочи", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_f", "vocal_m", "guitar", "bass", "drums", "percussion"],
         genres=["pop", "disco_funk", "foreign_hits", "dance_mix"],
         description="Летние хиты и диско на open-air, свадьбы на берегу и выездные корпоративы.",
         price_private=80000, price_corporate=100000, price_newyear=140000, program_format="3x45", sound="included",
         services=["welcome", "ceremony", "own_light"]),
    dict(name="[Демо] Волжский Фолк", city="Нижний Новгород", travel_scope="russia", lineup="band_6_plus",
         instruments=["vocal_f", "vocal_m", "violin", "percussion", "guitar", "keys"], genres=["ethno", "ru_hits"],
         description="Этно-кавер: русские хиты в фолк-аранжировке с баяном и скрипкой. Тематические вечера.",
         price_private=70000, price_corporate=90000, price_newyear=120000, program_format="2x45", sound="extra",
         services=["theme_show", "extra_lineup", "travel"]),
    dict(name="[Демо] Кубань Бэнд", city="Краснодар", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_m", "guitar", "bass", "drums"], genres=["ru_hits", "pop", "retro"],
         description="Русские хиты и ретро для юбилеев и семейных праздников. Спокойно, душевно, по-домашнему.",
         price_private=30000, price_corporate=40000, price_newyear=55000, program_format="2x45", sound="included",
         services=["custom_song"]),
    dict(name="[Демо] Гитара и Голос", city="Москва", travel_scope="city", lineup="solo",
         instruments=["vocal_m", "guitar"], genres=["acoustic", "ru_hits", "foreign_hits"],
         description="Соло под гитару: камерные дни рождения, ужины, небольшие компании до 30 человек.",
         price_private=15000, price_corporate=20000, price_newyear=30000, program_format="hourly", sound="included",
         services=["custom_song"]),
    dict(name="[Демо] Royal Show Orchestra", city="Москва", travel_scope="russia", lineup="band_6_plus",
         instruments=["vocal_m", "vocal_f", "guitar", "bass", "drums", "keys", "sax", "brass", "violin"],
         genres=["disco_funk", "jazz_lounge", "dance_mix", "foreign_hits", "pop"],
         description="Шоу-оркестр из 12 музыкантов с балетом и светом. Премиальные корпоративы и свадьбы.",
         price_private=300000, price_corporate=350000, price_newyear=450000, program_format="3x45", sound="included",
         services=["welcome", "ceremony", "extra_lineup", "own_light", "mc", "dj", "travel"]),
    dict(name="[Демо] Химки Кавер", city="Химки", travel_scope="region", lineup="band_4_5",
         instruments=["vocal_f", "guitar", "bass", "drums"], genres=["pop", "dance_mix", "ru_hits"],
         description="Поп и танцевальные хиты с женским вокалом. Москва и область без доплаты за выезд.",
         price_private=40000, price_corporate=50000, price_newyear=75000, program_format="2x45", sound="extra",
         services=["dj"]),
    dict(name="[Демо] Петербургский Свинг", city="Санкт-Петербург", travel_scope="russia", lineup="band_6_plus",
         instruments=["vocal_f", "keys", "bass", "drums", "sax", "brass"], genres=["jazz_lounge", "retro", "disco_funk"],
         description="Свинг-бэнд 30–60-х: Синатра, Армстронг, Утёсов. Стильные вечеринки в духе Гэтсби.",
         price_private=110000, price_corporate=140000, price_newyear=None, program_format="3x45", sound="included",
         services=["theme_show", "welcome"]),
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
