"""Справочники. Коды — латиницей (хранятся в БД), подписи — для пользователя."""

GENRES = {
    "dance_mix": "Танцевальный микс",
    "pop": "Поп-хиты",
    "ru_hits": "Русские хиты",
    "foreign_hits": "Зарубежные хиты",
    "rock": "Рок / русский рок",
    "retro": "Ретро 70–90-х",
    "disco_funk": "Диско / фанк",
    "jazz_lounge": "Джаз / лаунж / свинг",
    "acoustic": "Акустика",
    "mashup": "Mash-up",
    "instrumental": "Инструментальный кавер",
    "ethno": "Этно / фолк",
}

SERVICES = {
    "welcome": "Welcome-музыка",
    "ceremony": "Музыка на церемонию",
    "custom_song": "Песня на заказ",
    "dj": "DJ между сетами",
    "extra_lineup": "Усиление состава",
    "own_light": "Свой свет",
    "mc": "Ведущий / MC",
    "theme_show": "Тематическая программа",
    "travel": "Выезд в другой город",
}

INSTRUMENTS = {
    "vocal_m": "Вокал (м)",
    "vocal_f": "Вокал (ж)",
    "guitar": "Гитара",
    "bass": "Бас",
    "drums": "Барабаны",
    "keys": "Клавиши",
    "sax": "Саксофон",
    "violin": "Скрипка",
    "brass": "Труба / духовые",
    "percussion": "Перкуссия",
}

LINEUPS = {
    "solo": "Соло",
    "duo": "Дуэт",
    "trio": "Трио",
    "band_4_5": "Группа 4–5",
    "band_6_plus": "Группа 6+",
}

TRAVEL = {
    "city": "Только свой город",
    "region": "Город + область",
    "russia": "По России",
}

SOUND = {
    "included": "Свой звук, включён в цену",
    "extra": "Свой звук за доплату",
    "venue": "Нужен звук площадки",
}

EVENT_TYPES = {
    "private": "Частное (свадьба, ДР, юбилей)",
    "corporate": "Корпоратив",
    "newyear": "Новый год",
}

PROGRAM_FORMATS = {
    "2x45": "2 × 45 мин",
    "3x30": "3 × 30 мин",
    "3x45": "3 × 45 мин",
    "hourly": "Почасово",
    "other": "Другое",
}

BUDGET_OPTIONS = [
    (50_000, "до 50к"),
    (100_000, "до 100к"),
    (200_000, "до 200к"),
    (400_000, "до 400к"),
    (0, "Не важно"),
]


def labels(codes, dictionary) -> str:
    return ", ".join(dictionary.get(c, c) for c in (codes or []))
