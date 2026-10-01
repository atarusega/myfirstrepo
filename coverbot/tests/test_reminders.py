from datetime import datetime, timedelta, timezone

from app.db import Band
from app.reminders import needs_price_reminder, price_reminder_text

NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


def band(confirmed_days_ago=None, reminded_days_ago=None, **kw):
    ago = lambda d: None if d is None else NOW - timedelta(days=d)  # noqa: E731
    base = dict(name="Кавер <Бэнд>", status="published", tg_user_id=42, price_private=50000,
                prices_confirmed_at=ago(confirmed_days_ago), price_reminder_at=ago(reminded_days_ago),
                created_at=NOW - timedelta(days=400))
    base.update(kw)
    return Band(**base)


def test_fresh_prices_no_reminder():
    assert not needs_price_reminder(band(confirmed_days_ago=89), NOW)


def test_stale_prices_remind_once_then_wait():
    assert needs_price_reminder(band(confirmed_days_ago=90), NOW)
    assert not needs_price_reminder(band(confirmed_days_ago=120, reminded_days_ago=10), NOW)
    assert needs_price_reminder(band(confirmed_days_ago=120, reminded_days_ago=30), NOW)


def test_confirmation_starts_new_cycle():
    # напомнили 100 дней назад, группа подтвердила 20 дней назад — ждём следующие 90 дней
    assert not needs_price_reminder(band(confirmed_days_ago=20, reminded_days_ago=100), NOW)


def test_only_published_bands_with_telegram():
    assert not needs_price_reminder(band(confirmed_days_ago=200, status="pending"), NOW)
    assert not needs_price_reminder(band(confirmed_days_ago=200, tg_user_id=None), NOW)


def test_falls_back_to_created_at_and_handles_naive_dates():
    naive = (NOW - timedelta(days=100)).replace(tzinfo=None)  # так даты отдаёт SQLite
    assert needs_price_reminder(band(created_at=naive), NOW)
    assert not needs_price_reminder(band(created_at=NOW - timedelta(days=5)), NOW)


def test_text_escapes_name():
    assert "Кавер &lt;Бэнд&gt;" in price_reminder_text(band())
