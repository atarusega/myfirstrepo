"""Фоновые напоминания группам:
- раз в 90 дней подтвердить цены (устаревшие цены опускают группу в поиске), через год без ответа — архив;
- через день после анкеты без видео — прислать видео (один раз)."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.db import Band, Session
from app.keyboards import price_reminder_kb, video_reminder_kb
from app.utils import fmt_money

log = logging.getLogger(__name__)
router = Router()

PRICES_TTL = timedelta(days=90)
REMIND_AGAIN_AFTER = timedelta(days=30)  # если на прошлое напоминание не ответили
ARCHIVE_AFTER = timedelta(days=365)  # так написано в согласии (app/consent.py)
VIDEO_REMIND_AFTER = timedelta(days=1)
CHECK_EVERY = timedelta(hours=6)
FIRST_CHECK_DELAY = timedelta(minutes=1)


def _utc(ts: datetime | None) -> datetime | None:
    # SQLite возвращает даты без часового пояса
    return ts.replace(tzinfo=timezone.utc) if ts and ts.tzinfo is None else ts


def needs_price_reminder(band: Band, now: datetime) -> bool:
    if band.status != "published" or not band.tg_user_id:
        return False
    confirmed = _utc(band.prices_confirmed_at or band.created_at)
    if confirmed is None or now - confirmed < PRICES_TTL:
        return False
    reminded = _utc(band.price_reminder_at)
    return reminded is None or now - reminded >= REMIND_AGAIN_AFTER


def should_archive(band: Band, now: datetime) -> bool:
    if band.status != "published":
        return False
    confirmed = _utc(band.prices_confirmed_at or band.created_at)
    return confirmed is not None and now - confirmed >= ARCHIVE_AFTER


def needs_video_reminder(band: Band, now: datetime) -> bool:
    if band.status != "draft" or not band.tg_user_id or band.video_links or band.video_reminder_at:
        return False
    consented = _utc(band.consent_at)
    return consented is not None and now - consented >= VIDEO_REMIND_AFTER


def price_reminder_text(band: Band) -> str:
    return (
        f"Прошло 3 месяца с последней проверки цен у <b>{escape(band.name)}</b>. Они всё ещё актуальны?\n\n"
        f"💰 Частное: {fmt_money(band.price_private)} · Корпоратив: {fmt_money(band.price_corporate)} · "
        f"Новый год: {fmt_money(band.price_newyear)}\n\n"
        "<i>Группы со свежими ценами стоят выше в поиске.</i>"
    )


async def send_price_reminders(bot: Bot, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    async with Session() as s:
        bands = (await s.execute(
            select(Band).where(Band.status == "published", Band.tg_user_id.is_not(None))
        )).scalars().all()
        due = [b for b in bands if needs_price_reminder(b, now)]
        for band in due:
            try:
                await bot.send_message(band.tg_user_id, price_reminder_text(band),
                                       reply_markup=price_reminder_kb(band.id))
            except TelegramAPIError as e:
                # отмечаем и при ошибке: заблокировавшего бота не дёргаем каждые 6 часов
                log.warning("Price reminder for band %s failed: %s", band.id, e)
            # updated_at = прежнее значение: напоминание — не правка анкеты
            await s.execute(update(Band).where(Band.id == band.id)
                            .values(price_reminder_at=now, updated_at=Band.updated_at))
            await s.commit()
            await asyncio.sleep(0.05)  # лимит Telegram — 30 сообщений в секунду
    return len(due)


async def archive_stale(bot: Bot, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    async with Session() as s:
        bands = (await s.execute(select(Band).where(Band.status == "published"))).scalars().all()
        stale = [b for b in bands if should_archive(b, now)]
        for band in stale:
            band.status = "archived"
        await s.commit()
    for band in stale:
        if band.tg_user_id:
            try:
                await bot.send_message(band.tg_user_id,
                                       f"Карточка <b>{escape(band.name)}</b> ушла в архив: цены не подтверждались "
                                       "год. Вернуть в каталог: /band → «Цены актуальны».")
            except TelegramAPIError as e:
                log.warning("Archive notice for band %s failed: %s", band.id, e)
    return len(stale)


async def send_video_reminders(bot: Bot, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    async with Session() as s:
        bands = (await s.execute(select(Band).where(Band.status == "draft"))).scalars().all()
        due = [b for b in bands if needs_video_reminder(b, now)]
        for band in due:
            try:
                await bot.send_message(
                    band.tg_user_id,
                    f"Анкета <b>{escape(band.name or 'вашей группы')}</b> почти готова — не хватает видео. "
                    "Пришлите 1–3 ссылки на живые выступления, и она уйдёт на модерацию.",
                    reply_markup=video_reminder_kb(),
                )
            except TelegramAPIError as e:
                log.warning("Video reminder for band %s failed: %s", band.id, e)
            await s.execute(update(Band).where(Band.id == band.id)
                            .values(video_reminder_at=now, updated_at=Band.updated_at))
            await s.commit()
            await asyncio.sleep(0.05)
    return len(due)


async def price_reminder_loop(bot: Bot) -> None:
    await asyncio.sleep(FIRST_CHECK_DELAY.total_seconds())
    while True:
        try:
            sent = await send_price_reminders(bot)
            if sent:
                log.info("Price reminders sent: %s", sent)
            sent = await send_video_reminders(bot)
            if sent:
                log.info("Video reminders sent: %s", sent)
            archived = await archive_stale(bot)
            if archived:
                log.info("Archived stale bands: %s", archived)
        except Exception:
            log.exception("Price reminders failed")
        await asyncio.sleep(CHECK_EVERY.total_seconds())


@router.callback_query(F.data.startswith("pc:"))
async def on_prices_confirmed(cb: CallbackQuery):
    await cb.answer()
    band_id = cb.data[3:]
    if not band_id.isdigit():
        return
    async with Session() as s:
        band = await s.get(Band, int(band_id))
        if band is None or band.tg_user_id != cb.from_user.id:
            return
        band.prices_confirmed_at = datetime.now(timezone.utc)
        await s.commit()
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Спасибо! Отметил цены как актуальные ✅ Напомню снова через 3 месяца.")
