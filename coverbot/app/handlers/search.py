import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy import select

from app import llm
from app.cards import band_card, contact_card
from app.config import settings
from app.criteria import Criteria
from app.db import Band, Lead, Recommendation, SearchRequest, Session, ensure_producer, rec_counts
from app.keyboards import band_result_kb, budget_kb, city_kb, recommend_kb, results_nav_kb
from app.matching import match
from app.utils import parse_money

log = logging.getLogger(__name__)
router = Router()


class Search(StatesGroup):
    query = State()
    budget = State()
    city = State()


PROMPT = (
    "Опишите, кого ищете, как написали бы коллеге. Например:\n\n"
    "<i>«Кавер-группа на корпоратив 14 декабря, Москва, 150 человек, до 120к, нужен саксофон и свой звук»</i>\n\n"
    "Главное — город, бюджет и формат события. Остальное — по желанию."
)


async def start_search(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Search.query)
    await message.answer(PROMPT)


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await start_search(message, state)


@router.callback_query(F.data == "role:search")
async def role_search(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await start_search(cb.message, state)


def _crit(data) -> Criteria | None:
    return Criteria(**data["criteria"]) if data.get("criteria") else None


@router.message(Search.query, F.voice | F.audio | F.video_note)
async def on_voice(message: Message):
    await message.answer("Пока я понимаю только текст — напишите, пожалуйста, запрос сообщением 🙏")


@router.message(Search.query, F.text & ~F.text.startswith("/"))
async def on_query(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.bot.send_chat_action(message.chat.id, "typing")
    crit = await llm.parse_request(message.text, _crit(data))
    raw = ((data.get("raw_text") or "") + "\n" + message.text).strip()
    await state.update_data(criteria=crit.model_dump(), raw_text=raw, req_id=None, offset=0)
    await proceed(message, state, message.from_user)


async def proceed(message: Message, state: FSMContext, user: User):
    data = await state.get_data()
    crit = _crit(data)
    missing = crit.missing()
    if "city" in missing:
        await state.set_state(Search.city)
        await message.answer("В каком городе мероприятие? Выберите или напишите:", reply_markup=city_kb())
        return
    if "budget" in missing:
        await state.set_state(Search.budget)
        await message.answer("Какой бюджет на группу? Выберите или напишите сумму:", reply_markup=budget_kb())
        return
    await run_search(message, state, user)


@router.callback_query(Search.city, F.data.startswith("city:"))
async def on_city_btn(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _set_criteria(state, city=cb.data[5:])
    await cb.message.edit_reply_markup(reply_markup=None)
    await proceed(cb.message, state, cb.from_user)


@router.message(Search.city, F.text & ~F.text.startswith("/"))
async def on_city_text(message: Message, state: FSMContext):
    await _set_criteria(state, city=message.text.strip()[:100])
    await proceed(message, state, message.from_user)


@router.callback_query(Search.budget, F.data.startswith("bud:"))
async def on_budget_btn(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    value = int(cb.data[4:])
    await _set_criteria(state, budget=value or None, budget_any=value == 0)
    await cb.message.edit_reply_markup(reply_markup=None)
    await proceed(cb.message, state, cb.from_user)


@router.message(Search.budget, F.text & ~F.text.startswith("/"))
async def on_budget_text(message: Message, state: FSMContext):
    value = parse_money(message.text)
    if not value:
        await message.answer("Не понял сумму. Например: <code>150к</code>", reply_markup=budget_kb())
        return
    await _set_criteria(state, budget=value, budget_any=False)
    await proceed(message, state, message.from_user)


async def _set_criteria(state: FSMContext, **changes):
    data = await state.get_data()
    crit = (_crit(data) or Criteria()).model_copy(update=changes)
    await state.update_data(criteria=crit.model_dump())


async def run_search(message: Message, state: FSMContext, user: User, offset: int = 0):
    data = await state.get_data()
    crit = _crit(data)
    async with Session() as s:
        await ensure_producer(s, user)
        bands = (await s.execute(select(Band).where(Band.status == "published"))).scalars().all()
        recs = await rec_counts(s)
        results, note = match(bands, crit, recs)
        req_id = data.get("req_id")
        if req_id is None:
            req = SearchRequest(
                producer_id=user.id,
                raw_text=data.get("raw_text") or "",
                parsed=crit.model_dump(),
                result_ids=[b.id for b, _, _ in results[:20]],
            )
            s.add(req)
            await s.commit()
            req_id = req.id
        else:
            await s.commit()

    await state.set_state(Search.query)  # любое следующее сообщение — уточнение запроса
    await state.update_data(req_id=req_id, offset=offset)

    if not results:
        await message.answer(
            f"Понял запрос: <i>{escape(crit.summary())}</i>\n\n"
            "Пока никого не нашлось. Попробуйте ослабить условия — например, другой бюджет или город. "
            "Просто напишите, что поменять.",
            reply_markup=results_nav_kb(False),
        )
        return

    page = results[offset : offset + settings.page_size]
    if offset == 0:
        head = f"Понял запрос: <i>{escape(crit.summary())}</i>\nНашёл вариантов: {len(results)}"
        if note:
            head += f"\n\n{note}"
        await message.answer(head)
    await message.bot.send_chat_action(message.chat.id, "typing")
    reasons = await llm.explain(crit, page)
    for band, _score, price in page:
        await message.answer(
            band_card(band, recs.get(band.id), reasons.get(band.id), price),
            reply_markup=band_result_kb(band.id, req_id),
            disable_web_page_preview=True,
        )
    has_more = offset + settings.page_size < len(results)
    await message.answer(
        "Чтобы уточнить — просто напишите, что изменить («дешевле», «нужен джаз», «с DJ»).",
        reply_markup=results_nav_kb(has_more),
    )


@router.callback_query(F.data.startswith("srch:"))
async def on_nav(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    action = cb.data[5:]
    await cb.message.edit_reply_markup(reply_markup=None)
    if action == "new":
        await start_search(cb.message, state)
        return
    data = await state.get_data()
    if not data.get("criteria"):
        await start_search(cb.message, state)
        return
    if action == "more":
        await run_search(cb.message, state, cb.from_user, offset=data.get("offset", 0) + settings.page_size)
    elif action == "refine":
        await state.set_state(Search.query)
        await state.update_data(req_id=None)
        await cb.message.answer("Напишите, что изменить в запросе:")


@router.callback_query(F.data.startswith("lead:"))
async def on_lead(cb: CallbackQuery):
    await cb.answer()
    _, band_id, req_id = cb.data.split(":")
    async with Session() as s:
        band = await s.get(Band, int(band_id))
        if band is None or band.status != "published":
            await cb.message.answer("Эта карточка больше недоступна.")
            return
        await ensure_producer(s, cb.from_user)
        s.add(Lead(request_id=int(req_id) or None, band_id=band.id, producer_id=cb.from_user.id))
        await s.commit()
    await cb.message.answer(contact_card(band), reply_markup=recommend_kb(band.id))
    if band.tg_user_id:
        who = f"@{cb.from_user.username}" if cb.from_user.username else cb.from_user.full_name
        try:
            await cb.bot.send_message(
                band.tg_user_id,
                f"🔔 Продюсер {escape(who)} запросил ваш контакт через бот. Возможно, скоро напишет!",
            )
        except Exception as e:  # noqa: BLE001 — группа могла не запускать бота
            log.info("Cannot notify band %s: %s", band.id, e)


@router.callback_query(F.data.startswith("rec:"))
async def on_recommend(cb: CallbackQuery):
    band_id = int(cb.data[4:])
    async with Session() as s:
        exists = (await s.execute(
            select(Recommendation).where(
                Recommendation.band_id == band_id,
                Recommendation.recommender_tg_id == cb.from_user.id,
                Recommendation.source == "producer",
            )
        )).scalar_one_or_none()
        if exists:
            await cb.answer("Вы уже рекомендовали эту группу 👍")
            return
        s.add(Recommendation(band_id=band_id, recommender_tg_id=cb.from_user.id, source="producer"))
        await s.commit()
    await cb.answer("Спасибо! Рекомендация учтена ⭐", show_alert=True)
    await cb.message.edit_reply_markup(reply_markup=None)
