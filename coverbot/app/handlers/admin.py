import csv
import io
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import func, select

from app.cards import band_card
from app.config import settings
from app.db import Band, Lead, Producer, Recommendation, SearchRequest, Session
from app.keyboards import moderation_kb

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


@router.callback_query(F.data.startswith("adm:"))
async def moderate(cb: CallbackQuery):
    parts = cb.data.split(":")
    action, band_id = parts[1], int(parts[2])
    async with Session() as s:
        band = await s.get(Band, band_id)
        if band is None:
            await cb.answer("Карточка не найдена", show_alert=True)
            return
        if action == "ok":
            band.status, band.reject_reason = "published", None
            user_text = "🎉 Ваша карточка опубликована! Теперь продюсеры находят вас в поиске. Обновить: /band"
        else:
            band.status = "rejected"
            band.reject_reason = REJECT_REASONS.get(parts[3], "Анкета не прошла модерацию.")
            user_text = f"Анкета пока не опубликована. {band.reject_reason}\nИсправить: /band"
        await s.commit()
    verdict = "✅ Одобрено" if action == "ok" else "❌ Отклонено"
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(f"{verdict}: #{band.id} {band.name} ({cb.from_user.full_name})")
    await cb.answer()
    if band.tg_user_id:
        try:
            await cb.bot.send_message(band.tg_user_id, user_text)
        except Exception:  # noqa: BLE001
            pass


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    async with Session() as s:
        bands = (await s.execute(select(Band).where(Band.status == "pending").order_by(Band.id))).scalars().all()
    if not bands:
        await message.answer("Очередь модерации пуста.")
        return
    for band in bands[:10]:
        await message.answer(f"#{band.id}\n" + band_card(band, full=True), reply_markup=moderation_kb(band.id),
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
        "Команды админа:\n/pending — очередь модерации\n/stats — статистика\n/export — выгрузка базы в CSV\n"
        "/tvrec &lt;id&gt; [tg_id] — рекомендация резидента «Тут все»"
    )
