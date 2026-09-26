import re

_SPACE_THOUSANDS = re.compile(r"(?<=\d)[ \u00a0](?=\d{3}\b)")
_MONEY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(млн|m\b|к\b|k\b|тыс\w*|т\.?\s?р)?", re.I)
_MONEY_IN_TEXT = re.compile(
    r"(?:(?:до|бюджет\w*|за|в пределах|около|примерно)\s*)(\d+(?:[.,]\d+)?)\s*(млн|к|k|тыс\w*|т\.?\s?р|₽|руб\w*)?"
    r"|(\d+(?:[.,]\d+)?)\s*(млн|к|k|тыс\w*|т\.?\s?р|₽|руб\w*)",
    re.I,
)
URL_RE = re.compile(r"https?://\S+", re.I)


def _to_rub(num: str, suffix: str | None) -> int:
    value = float(num.replace(",", "."))
    s = (suffix or "").lower()
    if s.startswith(("млн", "m")):
        value *= 1_000_000
    elif s.startswith(("к", "k", "тыс", "т")):
        value *= 1000
    elif value < 1000:  # «120» в денежном контексте = 120 тысяч
        value *= 1000
    return int(value)


def parse_money(text: str | None) -> int | None:
    """Разбор суммы из ответа на прямой вопрос о цене: «40к», «40 000», «1.2 млн»."""
    if not text:
        return None
    t = _SPACE_THOUSANDS.sub("", text.lower())
    m = _MONEY.search(t)
    if not m:
        return None
    return _to_rub(m.group(1), m.group(2))


def find_budget(text: str) -> int | None:
    """Поиск бюджета внутри свободного запроса: только с маркерами «до», «к», «₽» и т. п."""
    t = _SPACE_THOUSANDS.sub("", text.lower())
    for m in _MONEY_IN_TEXT.finditer(t):
        if m.group(1):
            return _to_rub(m.group(1), m.group(2))
        if m.group(3):
            return _to_rub(m.group(3), m.group(4))
    return None


CITY_ALIASES = {
    "мск": "москва",
    "москва": "москва",
    "спб": "санкт-петербург",
    "питер": "санкт-петербург",
    "петербург": "санкт-петербург",
    "санкт-петербург": "санкт-петербург",
    "екб": "екатеринбург",
    "нск": "новосибирск",
    "нн": "нижний новгород",
}

MOSCOW_REGION = {
    "москва", "мытищи", "химки", "красногорск", "одинцово", "балашиха", "подольск", "люберцы",
    "королёв", "королев", "истра", "звенигород", "домодедово", "раменское", "жуковский",
    "щёлково", "щелково", "пушкино", "дмитров", "клин", "солнечногорск", "наро-фоминск",
    "коломна", "серпухов", "ногинск", "электросталь", "реутов", "долгопрудный", "лобня",
    "зеленоград", "видное", "дзержинский", "котельники", "московская область", "подмосковье",
}
SPB_REGION = {
    "санкт-петербург", "пушкин", "петергоф", "гатчина", "всеволожск", "выборг", "кронштадт",
    "сестрорецк", "ленинградская область", "ленобласть",
}


def normalize_city(city: str | None) -> str:
    if not city:
        return ""
    c = city.strip().lower().replace("ё", "е")
    c = re.sub(r"^(г\.|город)\s*", "", c)
    return CITY_ALIASES.get(c, c)


def region_of(city: str | None) -> str:
    c = normalize_city(city)
    if c in {x.replace("ё", "е") for x in MOSCOW_REGION} or "москов" in c:
        return "moscow"
    if c in SPB_REGION or "ленинград" in c:
        return "spb"
    return c


def fmt_money(value: int | None) -> str:
    if not value:
        return "—"
    return f"{value:,}".replace(",", " ") + " ₽"
