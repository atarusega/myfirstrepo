import re

from pydantic import BaseModel, Field, field_validator

from app.dictionaries import EVENT_TYPES, GENRES, INSTRUMENTS, LINEUPS, SERVICES
from app.utils import find_budget, normalize_city


class Criteria(BaseModel):
    event_type: str | None = None
    budget: int | None = None
    budget_any: bool = False
    city: str | None = None
    genres: list[str] = Field(default_factory=list)
    date: str | None = None
    guests: int | None = None
    instruments: list[str] = Field(default_factory=list)
    lineup: list[str] = Field(default_factory=list)
    need_sound: bool | None = None
    services: list[str] = Field(default_factory=list)
    free_text: str | None = None

    @field_validator("event_type")
    @classmethod
    def _event(cls, v):
        return v if v in EVENT_TYPES else None

    @field_validator("genres")
    @classmethod
    def _genres(cls, v):
        return [x for x in v if x in GENRES]

    @field_validator("instruments")
    @classmethod
    def _instr(cls, v):
        return [x for x in v if x in INSTRUMENTS]

    @field_validator("lineup")
    @classmethod
    def _lineup(cls, v):
        return [x for x in v if x in LINEUPS]

    @field_validator("services")
    @classmethod
    def _services(cls, v):
        return [x for x in v if x in SERVICES]

    def missing(self) -> list[str]:
        out = []
        if not self.budget and not self.budget_any:
            out.append("budget")
        if not self.city:
            out.append("city")
        return out

    def summary(self) -> str:
        parts = []
        if self.event_type:
            parts.append(EVENT_TYPES[self.event_type].split(" (")[0])
        if self.city:
            parts.append(self.city)
        if self.budget:
            parts.append(f"до {self.budget // 1000}к")
        elif self.budget_any:
            parts.append("бюджет любой")
        if self.genres:
            parts.append(", ".join(GENRES[g] for g in self.genres))
        if self.instruments:
            parts.append(", ".join(INSTRUMENTS[i] for i in self.instruments))
        if self.date:
            parts.append(self.date)
        if self.guests:
            parts.append(f"{self.guests} гостей")
        if self.need_sound:
            parts.append("со своим звуком")
        return " · ".join(parts) or "без критериев"


# ---------- Простой разбор без нейросети (запасной вариант) ----------

_EVENT_KW = [
    (r"нов\w* год|новогод|нг\b|корпоратив\w* в декабре", "newyear"),
    (r"корпорат|конференц|компани|бизнес", "corporate"),
    (r"свадьб|день рожд|др\b|юбиле|выпускн|вечеринк|праздник", "private"),
]
_GENRE_KW = {
    "rock": r"рок",
    "jazz_lounge": r"джаз|лаунж|свинг|lounge|jazz",
    "retro": r"ретро|80|90|70|диско 80",
    "disco_funk": r"диско|фанк|funk|disco",
    "ru_hits": r"русск\w* хит|русск\w* песн|на русском",
    "foreign_hits": r"зарубеж|иностран|на английском",
    "acoustic": r"акустик|акустич",
    "mashup": r"mash|мэшап|мешап|меш-ап",
    "ethno": r"этно|фолк|народн",
    "instrumental": r"инструментал|без вокала",
    "dance_mix": r"танцев|раскач|танцпол|движ",
    "pop": r"поп",
}
_INSTR_KW = {
    "sax": r"саксоф|сакс\b",
    "violin": r"скрипк|скрипач",
    "brass": r"труб|духов",
    "keys": r"клавиш|пиан|рояль",
    "vocal_f": r"вокалистк|женск\w* вокал|певиц",
    "vocal_m": r"мужск\w* вокал|вокалист\b|певец",
}
_SERVICE_KW = {
    "welcome": r"welcome|велком|встреч\w* гостей",
    "ceremony": r"церемон|выход невест|регистрац",
    "custom_song": r"на заказ|разучить|выучить",
    "dj": r"\bdj\b|диджей|ди-джей",
    "mc": r"ведущ",
    "theme_show": r"тематич|стиляг",
}
_KNOWN_CITIES = ["москв", "мск", "подмосков", "московск", "санкт-петербург", "петербург", "спб", "питер",
                 "казан", "екатеринбург", "новосибирск", "нижн\\w* новгород", "сочи", "краснодар", "самар"]
_CITY_CANON = {
    "москв": "Москва", "мск": "Москва", "подмосков": "Московская область", "московск": "Московская область",
    "санкт-петербург": "Санкт-Петербург", "петербург": "Санкт-Петербург", "спб": "Санкт-Петербург",
    "питер": "Санкт-Петербург", "казан": "Казань", "екатеринбург": "Екатеринбург",
    "новосибирск": "Новосибирск", "нижн\\w* новгород": "Нижний Новгород", "сочи": "Сочи",
    "краснодар": "Краснодар", "самар": "Самара",
}


def fallback_parse(text: str, previous: Criteria | None = None) -> Criteria:
    c = previous.model_copy(deep=True) if previous else Criteria()
    t = text.lower()
    for pattern, code in _EVENT_KW:
        if re.search(pattern, t):
            c.event_type = code
            break
    budget = find_budget(t)
    if budget:
        c.budget, c.budget_any = budget, False
    if re.search(r"бюджет\w* (не важ|любой|без огранич)|не важно сколько", t):
        c.budget_any = True
    for key in _KNOWN_CITIES:
        if re.search(key, t):
            c.city = _CITY_CANON[key]
            break
    for code, pattern in _GENRE_KW.items():
        if re.search(pattern, t) and code not in c.genres:
            c.genres.append(code)
    for code, pattern in _INSTR_KW.items():
        if re.search(pattern, t) and code not in c.instruments:
            c.instruments.append(code)
    for code, pattern in _SERVICE_KW.items():
        if re.search(pattern, t) and code not in c.services:
            c.services.append(code)
    if re.search(r"сво\w* звук|свою аппарат|с аппаратур", t):
        c.need_sound = True
    m = re.search(r"(\d{2,4})\s*(человек|чел|гост|персон)", t)
    if m:
        c.guests = int(m.group(1))
    c.free_text = ((c.free_text or "") + " " + text).strip()[:500]
    return c


def city_key(city: str | None) -> str:
    return normalize_city(city)
