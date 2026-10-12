from app.db import Band
from app.handlers.onboarding import BLOCKS, FIELDS, FIX_MENU, MODERATED_FIELDS, PRICE_FIELDS, STEPS
from app.handlers.support import user_id_from_tag
from app.keyboards import fields_kb, price_select


def test_every_step_is_a_band_column():
    assert len(FIELDS) == len(set(FIELDS)) == 16
    assert all(hasattr(Band, f) for f in FIELDS)


def test_fix_menu_covers_all_fields_in_order():
    covered = []
    for _, first, last in FIX_MENU:
        assert FIELDS.index(first) <= FIELDS.index(last)
        covered += FIELDS[FIELDS.index(first):FIELDS.index(last) + 1]
    assert covered == FIELDS
    assert MODERATED_FIELDS <= set(FIELDS) and set(PRICE_FIELDS) <= set(FIELDS)


def test_description_is_last_and_optional():
    assert STEPS[-1].field == "description" and not STEPS[-1].required
    assert len(BLOCKS) == 5


def test_callback_data_fits_telegram_limit():
    for kb in (price_select(None), fields_kb([label for label, *_ in FIX_MENU])):
        for row in kb.inline_keyboard:
            for button in row:
                assert len(button.callback_data.encode()) <= 64


def test_support_tag_roundtrip():
    assert user_id_from_tag("💬 Поддержка · Иван (@ivan) · #u123456789\nАнкета №3") == 123456789
    assert user_id_from_tag("обычное сообщение") is None
