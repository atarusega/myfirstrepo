import csv
import io
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import func, select

from app.cards import STATUS_LABELS, moderation_card
from app.config import settings
from app.db import Band, Lead, Producer, Recommendation, SearchRequest, Session
from app.handlers.support import user_id_from_tag
from app.keyboards import moderation_kb, undo_kb

router = Router()

REJECT_REASONS = {
    "video": "Видео не открывается — пришлите рабочие ссылки на живые выступления.",
    "data": "Не хватает данных — проверьте цену, жанры и состав.",
    "scope": "Сейчас каталог только для кавер-групп и музыкальных коллективов.",
}


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        return event.from_user is not None and event.from_user.id in settings.admin_ids


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def is_support_reply(message: Message) -> bool:
    target = message.reply_to_message
    return bool(target and target.from_user and target.from_user.is_bot
                and user_id_from_tag(target.text or target.caption) is not None)


@router.message(is_support_reply)
async def support_reply(message: Message):
    """Ответ реплаем на сообщение поддержки → пользователю (app/handlers/support.py)."""
    target = message.reply_to_message
    user_id = user_id_from_tag(target.text or target.caption)
    try:
        if message.text:
            await message.bot.send_message(user_id, f"💬 <b>Ответ поддержки</b>\n\n{escape(message.text)}\n\n"
                                                    "Написать ещё: /support", disable_web_page_preview=True)
        else:
            await message.bot.send_message(user_id, "💬 <b>Ответ поддержки</b> 👇")
            await message.copy_to(user_id)
    except TelegramAPIError as e:
        await message.reply(f"Не доставлено: {escape(str(e))}")
        return
    await message.reply("Отправлено ✅")


@router.callback_query(F.data.startswith("adm:"))
async def moderate(cb: CallbackQuery):
    parts = cb.data.split(":")
    action, band_id = parts[1], int(parts[2])
    if action == "undo":
        await undo_decision(cb, band_id, prev_status=parts[3], user_msg_id=int(parts[4]))
        return
    async with Session() as s:
        band = await s.get(Band, band_id)
        if band is None:
            await cb.answer("Карточка не найдена", show_alert=True)
            return
        prev_status = band.status
        if action == "ok":
            band.status, band.reject_reason = "published", None
            user_text = "🎉 Ваша карточка опубликована! Теперь продюсеры находят вас в поиске. Обновить: /band"
        else:
            band.status = "rejected"
            band.reject_reason = REJECT_REASONS.get(parts[3], "Анкета не прошла модерацию.")
            user_text = f"Анкета пока не опубликована. {band.reject_reason}\nИсправить: /band"
        await s.commit()
    verdict = "✅ Одобрено" if action == "ok" else "❌ Отклонено"
    user_msg_id = 0
    if band.tg_user_id:
        try:
            user_msg_id = (await cb.bot.send_message(band.tg_user_id, user_text)).message_id
        except TelegramAPIError:
            pass
    await cb.message.edit_reply_markup(reply_markup=undo_kb(band.id, prev_status, user_msg_id, verdict))
    await cb.answer(f"{verdict}. Ошиблись — нажмите «Отменить».")


async def undo_decision(cb: CallbackQuery, band_id: int, prev_status: str, user_msg_id: int):
    """Вернуть статус, который был до решения, и убрать у группы сообщение о решении."""
    async with Session() as s:
        band = await s.get(Band, band_id)
        if band is None:
            await cb.answer("Карточка не найдена", show_alert=True)
            return
        band.status, band.reject_reason = prev_status, None
        await s.commit()
    if band.tg_user_id and user_msg_id:
        try:  # бот может удалить своё сообщение в течение 48 часов
            await cb.bot.delete_message(band.tg_user_id, user_msg_id)
        except TelegramAPIError:
            try:
                await cb.bot.send_message(band.tg_user_id, "Предыдущее сообщение о модерации неактуально — "
                                                            "проверяем анкету ещё раз.")
            except TelegramAPIError:
                pass
    await cb.message.edit_reply_markup(reply_markup=moderation_kb(band.id))
    await cb.answer(f"Решение отменено, статус: {STATUS_LABELS.get(prev_status, prev_status)}")


@router.message(Command("card"))
async def cmd_card(message: Message, command: CommandObject):
    arg = (command.args or "").strip().lstrip("#№")
    if not arg.isdigit():
        await message.answer("Напишите номер анкеты: <code>/card 18</code>")
        return
    async with Session() as s:
        band = await s.get(Band, int(arg))
    if band is None:
        await message.answer(f"Анкеты №{arg} нет.")
        return
    await message.answer(f"#{band.id} · <b>{STATUS_LABELS.get(band.status, band.status)}</b>\n" + moderation_card(band),
                         reply_markup=moderation_kb(band.id), disable_web_page_preview=True)


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    async with Session() as s:
        bands = (await s.execute(select(Band).where(Band.status == "pending").order_by(Band.id))).scalars().all()
    if not bands:
        await message.answer("Очередь модерации пуста.")
        return
    for band in bands[:10]:
        await message.answer(f"#{band.id}\n" + moderation_card(band), reply_markup=moderation_kb(band.id),
                             disable_web_page_preview=True)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    week = datetime.now(timezone.utc) - timedelta(days=7)
    async with Session() as s:
        async def count(q):
            return (await s.execute(q)).scalar() or 0

        by_status = dict((await s.execute(select(Band.status, func.count()).group_by(Band.status))).all())
        producers = await count(select(func.count()).select_from(Producer))
        searches = await count(select(func.count()).select_from(SearchRequest))
        searches_w = await count(select(func.count()).select_from(SearchRequest).where(SearchRequest.created_at >= week))
        leads = await count(select(func.count()).select_from(Lead))
        leads_w = await count(select(func.count()).select_from(Lead).where(Lead.created_at >= week))
        searches_with_lead = await count(select(func.count(func.distinct(Lead.request_id))))
        recs = await count(select(func.count()).select_from(Recommendation))
    conv = f"{searches_with_lead / searches:.0%}" if searches else "—"
    await message.answer(
        "<b>Статистика</b>\n"
        f"Группы: опубликовано {by_status.get('published', 0)}, на модерации {by_status.get('pending', 0)}, "
        f"черновиков {by_status.get('draft', 0)}, отклонено {by_status.get('rejected', 0)}\n"
        f"Продюсеров: {producers}\n"
        f"Поисков: {searches} (за 7 дней {searches_w})\n"
        f"Показов контакта: {leads} (за 7 дней {leads_w})\n"
        f"Поисков, закончившихся контактом: {conv}\n"
        f"Рекомендаций: {recs}"
    )


@router.message(Command("export"))
async def cmd_export(message: Message):
    async with Session() as s:
        bands = (await s.execute(select(Band).order_by(Band.id))).scalars().all()
    cols = ["id", "name", "city", "travel_scope", "lineup", "instruments", "genres", "price_private",
            "price_corporate", "price_newyear", "program_format", "sound", "services", "video_links",
            "phone", "website", "tg_username", "source", "status", "created_at"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for b in bands:
        row = []
        for c in cols:
            v = getattr(b, c)
            row.append(", ".join(v) if isinstance(v, list) else v)
        w.writerow(row)
    data = buf.getvalue().encode("utf-8-sig")
    await message.answer_document(BufferedInputFile(data, filename="bands.csv"), caption=f"Групп: {len(bands)}")


@router.message(Command("tvrec"))
async def cmd_tvrec(message: Message, command: CommandObject):
    """/tvrec <id группы> [telegram id резидента] — рекомендация от резидента «Тут все»."""
    args = (command.args or "").split()
    if not args or not args[0].isdigit():
        await message.answer("Формат: /tvrec <id группы> [telegram id резидента]")
        return
    band_id = int(args[0])
    recommender = int(args[1]) if len(args) > 1 and args[1].isdigit() else message.from_user.id
    async with Session() as s:
        if await s.get(Band, band_id) is None:
            await message.answer("Группа не найдена.")
            return
        s.add(Recommendation(band_id=band_id, recommender_tg_id=recommender, source="tutvse"))
        try:
            await s.commit()
        except Exception:  # noqa: BLE001 — дубль
            await message.answer("Такая рекомендация уже есть.")
            return
    await message.answer("Рекомендация резидента «Тут все» добавлена 👍")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer(
        "Команды админа:\n/pending — очередь модерации\n/card N — анкета №N: посмотреть, одобрить или отклонить\n"
        "/stats — статистика\n/export — выгрузка базы в CSV\n"
        "/tvrec &lt;id&gt; [tg_id] — рекомендация резидента «Тут все»\n\n"
        "Вопросы в поддержку приходят сюда с меткой #u…: ответьте реплаем — ответ уйдёт пользователю."
    )
