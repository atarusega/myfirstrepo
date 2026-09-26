from datetime import datetime, timezone

from app.criteria import Criteria, fallback_parse
from app.db import Band
from app.matching import match, price_for


def band(**kw):
    base = dict(status="published", city="Москва", travel_scope="region", lineup="band_4_5",
                instruments=["vocal_m", "guitar", "bass", "drums"], genres=["dance_mix"], services=[],
                video_links=[], source="self", price_private=50000, price_corporate=70000, price_newyear=100000,
                sound="included", updated_at=datetime.now(timezone.utc))
    base.update(kw)
    b = Band(**base)
    b.id = kw.get("id", id(b) % 100000)
    return b


def test_budget_filter_and_slack():
    cheap, pricey = band(id=1, price_corporate=100000), band(id=2, price_corporate=200000)
    res, note = match([cheap, pricey], Criteria(city="Москва", budget=90000, event_type="corporate"))
    assert [b.id for b, _, _ in res] == [1]  # 100к в пределах +15% от 90к
    assert note is None


def test_relax_budget_when_empty():
    res, note = match([band(id=1, price_corporate=300000)], Criteria(city="Москва", budget=50000,
                                                                      event_type="corporate"))
    assert res and note


def test_city_and_region():
    assert match([band(id=1, city="Москва", travel_scope="region")], Criteria(city="Химки", budget_any=True))[0]
    assert not match([band(id=1, city="Москва", travel_scope="city")], Criteria(city="Казань", budget_any=True))[0]
    assert match([band(id=1, city="Москва", travel_scope="russia")], Criteria(city="Казань", budget_any=True))[0]


def test_instruments_required_and_genre_ranking():
    sax = band(id=1, instruments=["vocal_f", "sax"], genres=["jazz_lounge"])
    rock = band(id=2, genres=["rock"])
    crit = Criteria(city="Москва", budget_any=True, genres=["jazz_lounge"])
    res, _ = match([rock, sax], crit)
    assert res[0][0].id == 1
    res, _ = match([rock, sax], crit.model_copy(update={"instruments": ["sax"]}))
    assert [b.id for b, _, _ in res] == [1]


def test_price_for_fallbacks():
    b = band(price_private=None, price_corporate=60000, price_newyear=None)
    assert price_for(b, "corporate") == 60000
    assert price_for(b, None) == 60000
    # группа не берёт Новый год — в такой поиск не попадает
    res, _ = match([b], Criteria(city="Москва", budget_any=True, event_type="newyear"))
    assert res == []


def test_fallback_parser():
    c = fallback_parse("Нужна кавер-группа на корпоратив 14 декабря, мск, 150 человек, до 120к, саксофон и свой звук")
    assert c.event_type == "corporate"
    assert c.city == "Москва"
    assert c.budget == 120000
    assert c.guests == 150
    assert "sax" in c.instruments
    assert c.need_sound is True
    assert c.missing() == []
    c2 = fallback_parse("а можно подешевле, до 80к", c)
    assert c2.budget == 80000 and c2.city == "Москва"


def test_fallback_genres_ignore_numbers_and_popular():
    assert "retro" not in fallback_parse("день рождения 35 лет, 40 гостей, бюджет 80 тысяч").genres
    assert "retro" not in fallback_parse("выпускной, 90 выпускников, до 90к").genres
    assert "pop" not in fallback_parse("нужна популярная кавер-группа").genres
    assert "retro" in fallback_parse("ретро хиты 80-90х").genres
    assert "retro" in fallback_parse("хиты 90х на юбилей").genres
    assert {"rock", "pop"} <= set(fallback_parse("поп-рок кавер на свадьбу").genres)
