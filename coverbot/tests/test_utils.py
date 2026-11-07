from app.utils import find_budget, parse_money, region_of


def test_parse_money():
    assert parse_money("60к") == 60000
    assert parse_money("60 000") == 60000
    assert parse_money("от 120 тыс") == 120000
    assert parse_money("1.2 млн") == 1_200_000
    assert parse_money("80") == 80000
    assert parse_money("abc") is None


def test_find_budget_ignores_guests():
    assert find_budget("корпоратив, 150 человек, до 120к") == 120000
    assert find_budget("на 200 гостей, бюджет 300 000") == 300000
    assert find_budget("150 человек, Москва") is None


def test_region():
    assert region_of("Химки") == "moscow"
    assert region_of("москва") == "moscow"
    assert region_of("Питер") == "spb"


def test_find_budget_colloquial():
    assert find_budget("Москва 100 тыщ") == 100000
    assert find_budget("свадьба, 150т, Питер") == 150000
    assert find_budget("корпоратив на 100 человек") is None
