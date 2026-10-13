"""Подбор групп: жёсткий фильтр → скоринг 0–100. Чистые функции, без БД и сети."""
import re
from datetime import datetime, timezone

from app.criteria import Criteria
from app.utils import normalize_city, region_of

BUDGET_SLACK = 1.15  # запас на торг: показываем группы до +15% от бюджета

WEIGHTS = {
    "genres": 30,
    "text": 20,
    "services": 15,
    "trust": 15,
    "price": 15,
    "fresh": 5,
}


def price_for(band, event_type: str | None) -> int | None:
    prices = {
        "private": band.price_private,
        "corporate": band.price_corporate,
        "newyear": band.price_newyear,
    }
    if event_type:
        return prices.get(event_type)
    known = [p for p in prices.values() if p]
    return min(known) if known else None


def does_event(band, event_type: str | None) -> bool:
    """Группа указала цену под этот тип события (или цен нет вовсе — тогда не отсекаем)."""
    if not event_type:
        return True
    prices = [band.price_private, band.price_corporate, band.price_newyear]
    return not any(prices) or bool(price_for(band, event_type))


def city_ok(band, city: str | None) -> bool:
    if not city:
        return True
    want, have = normalize_city(city), normalize_city(band.city)
    if want == have or band.travel_scope == "russia":
        return True
    if band.travel_scope == "region" and region_of(want) == region_of(have):
        return True
    return False


def passes(band, crit: Criteria, check_budget: bool = True) -> bool:
    if band.status != "published":
        return False
    if not city_ok(band, crit.city):
        return False
    if not does_event(band, crit.event_type):
        return False
    if check_budget and crit.budget:
        price = price_for(band, crit.event_type)
        if price and price > crit.budget * BUDGET_SLACK:
            return False
    if crit.instruments and not all(i in (band.instruments or []) for i in crit.instruments):
        return False
    if crit.lineup and band.lineup and band.lineup not in crit.lineup:
        return False
    return True


_WORD = re.compile(r"[a-zа-яё]{4,}", re.I)


def _words(text: str | None) -> set[str]:
    return {w[:6] for w in _WORD.findall((text or "").lower())}


def score(band, crit: Criteria, recs: dict[str, int] | None = None) -> float:
    recs = recs or {}
    s = 0.0
    # жанры
    if crit.genres:
        overlap = len(set(crit.genres) & set(band.genres or []))
        s += WEIGHTS["genres"] * overlap / len(crit.genres)
    else:
        s += WEIGHTS["genres"] * 0.6
    # смысловая близость текста (упрощённо: пересечение основ слов; позже — pgvector)
    q = _words(crit.free_text)
    if q:
        d = _words(band.description) | _words(" ".join(band.genres or []))
        s += WEIGHTS["text"] * min(1.0, len(q & d) / max(3, len(q) * 0.3))
    else:
        s += WEIGHTS["text"] * 0.5
    # услуги и звук
    wanted = len(crit.services) + (1 if crit.need_sound else 0)
    if wanted:
        got = len(set(crit.services) & set(band.services or []))
        if crit.need_sound and band.sound in ("included", "extra"):
            got += 1 if band.sound == "included" else 0.6
        s += WEIGHTS["services"] * got / wanted
    else:
        s += WEIGHTS["services"] * 0.5
    # доверие
    trust = 0.0
    if band.source == "tutvse":
        trust += 0.4
    trust += min(0.6, 0.15 * (recs.get("tutvse", 0) + recs.get("producer", 0)))
    s += WEIGHTS["trust"] * min(1.0, trust)
    # цена: лучше всего — в бюджете и не сильно дешевле
    price = price_for(band, crit.event_type)
    if crit.budget and price:
        ratio = price / crit.budget
        if ratio <= 1:
            s += WEIGHTS["price"] * (0.6 + 0.4 * ratio)
        else:
            s += WEIGHTS["price"] * max(0.0, 1 - (ratio - 1) * 4)
    elif price:
        s += WEIGHTS["price"] * 0.5
    # свежесть данных
    ts = band.prices_confirmed_at or band.updated_at
    if ts:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - ts).days
        s += WEIGHTS["fresh"] * max(0.0, 1 - days / 180)
    return round(s, 1)


def match(bands, crit: Criteria, rec_counts: dict[int, dict[str, int]] | None = None):
    """Возвращает (результаты, заметка). Результаты: [(band, score, price)] по убыванию."""
    rec_counts = rec_counts or {}
    found = [b for b in bands if passes(b, crit)]
    note = None
    if not found and crit.budget:
        found = [b for b in bands if passes(b, crit, check_budget=False)]
        if found:
            found.sort(key=lambda b: price_for(b, crit.event_type) or 10**9)
            found = found[:5]
            note = "В этом бюджете никого не нашлось. Вот ближайшие варианты по цене:"
            return [(b, score(b, crit, rec_counts.get(b.id)), price_for(b, crit.event_type)) for b in found], note
    if not found and crit.instruments:
        relaxed = crit.model_copy(update={"instruments": []})
        found = [b for b in bands if passes(b, relaxed)]
        if found:
            note = "С нужными инструментами в составе никого нет. Вот группы без этого условия (часто состав можно усилить):"
    result = [(b, score(b, crit, rec_counts.get(b.id)), price_for(b, crit.event_type)) for b in found]
    result.sort(key=lambda x: x[1], reverse=True)
    return result, note
