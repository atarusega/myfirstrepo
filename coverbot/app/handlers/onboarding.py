"""Анкета кавер-группы. Один FSM-state + индекс шага в данных — шаги описаны таблицей STEPS."""
import logging
from datetime import datetime, timezone
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy import select

from app.cards import STATUS_LABELS, band_card
from app.config import settings
from app.db import Band, Session
from app.dictionaries import GENRES, INSTRUMENTS, LINEUPS, PROGRAM_FORMATS, SERVICES, SOUND, TRAVEL
from app.keyboards import consent_kb, keep_or_skip, main_menu, moderation_kb, multi_select, my_band_kb, single_select
from app.utils import URL_RE, fmt_money, parse_money

log = logging.getLogger(__name__)
router = Router()


class Onb(StatesGroup):
    filling = State()
    consent = State()


# (поле, тип, текст вопроса, опции, обязательное, текст кнопки «пропустить»)
STEPS = [
    ("name", "text", "Как называется ваш проект или группа?", None, True, None),
    ("city", "text", "В каком городе вы базируетесь?", None, True, None),
    ("travel_scope", "single", "Куда готовы выезжать?", TRAVEL, True, None),
    ("lineup", "single", "Какой у вас состав?", LINEUPS, True, None),
    ("instruments", "multi", "Отметьте вокал и инструменты в составе (можно несколько):", INSTRUMENTS, True, None),
    ("genres", "multi", "Какие жанры играете? Отметьте всё подходящее:", GENRES, True, None),
    ("description", "text",
     "Коротко: чем вы отличаетесь? Репертуар, фишки, опыт — 2–3 предложения.\n"
     "<i>Это помогает точнее подбирать вас под запросы.</i>", None, False, "Пропустить"),
    ("price_private", "money",
     "Цена <b>«от»</b> за стандартную программу на <b>частном событии</b> (свадьба, ДР, юбилей).\n"
     "Например: <code>60к</code> или <code>60 000</code>", None, False, "Не берём такие"),
    ("price_corporate", "money", "Цена <b>«от»</b> на <b>корпоративе</b>:", None, False, "Не берём такие"),
    ("price_newyear", "money", "Цена <b>«от»</b> на <b>Новый год</b> (декабрьские корпоративы):", None, False,
     "Не берём такие"),
    ("program_format", "single", "Что входит в стандартную программу?", PROGRAM_FORMATS, True, None),
    ("sound", "single", "Как со звуком?", SOUND, True, None),
    ("services", "multi", "Какие доп. услуги можете предложить? Если никаких — просто «Готово».", SERVICES,
     False, None),
    ("video_links", "videos",
     "Пришлите 1–3 ссылки на <b>живые выступления</b> (YouTube, VK, Rutube, Яндекс Диск, Telegram). "
     "Можно одним сообщением.", None, True, None),
    ("phone", "phone", "Телефон для связи (необязательно — продюсеры увидят ваш Telegram):", None, False,
     "Пропустить"),
    ("website", "text", "Сайт или соцсети (необязательно):", None, False, "Пропустить"),
]
FIELDS = [s[0] for s in STEPS]
PRICE_FIELDS = ("price_private", "price_corporate", "price_newyear")


def _display(field: str, value) -> str | None:
    if value in (None, "", []):
        return None
    if field in PRICE_FIELDS:
        return fmt_money(value)
    if field == "video_links":
        return f"{len(value)} ссылк(и)"
    return str(value)


# ---------- вход в анкету ----------

async def start_onboarding(message: Message, state: FSMContext, user: User, existing: Band | None = None):
    band_data = {f: getattr(existing, f) for f in FIELDS} if existing else {}
    await state.set_state(Onb.filling)
    await state.update_data(
        step=0,
        band=band_data,
        band_id=existing.id if existing else None,
        tg_username=user.username,
    )
    intro = (
        "Обновим анкету. На каждом шаге можно оставить текущее значение."
        if existing and existing.name
        else "Заполним анкету группы — это 3–5 минут, почти всё кнопками. Отменить: /cancel"
    )
    await message.answer(intro)
    await ask_step(message, state)


async def ask_step(message: Message, state: FSMContext):
    data = await state.get_data()
    idx, band = data["step"], data["band"]
    if idx >= len(STEPS):
        await show_preview(message, state)
        return
    field, kind, prompt, options, required, skip = STEPS[idx]
    current = band.get(field)
    header = f"<b>Шаг {idx + 1}/{len(STEPS)}</b>\n"
    if kind == "single":
        await message.answer(header + prompt, reply_markup=single_select(options, current))
    elif kind == "multi":
        await message.answer(header + prompt, reply_markup=multi_select(options, current or []))
    else:
        if field == "phone" and not data.get("tg_username"):
            prompt = ("У вашего Telegram-аккаунта нет юзернейма, поэтому продюсерам нужен телефон. "
                      "Пришлите номер для связи:")
            skip = None
        await message.answer(header + prompt, reply_markup=keep_or_skip(_display(field, current), skip))


async def next_step(message: Message, state: FSMContext, field: str, value, set_value: bool = True):
    data = await state.get_data()
    band = data["band"]
    if set_value:
        band[field] = value
    idx = data["step"] + 1
    # после последней цены проверяем, что хотя бы одна указана
    if field == "price_newyear" and not any(band.get(p) for p in PRICE_FIELDS):
        await message.answer("Нужна хотя бы одна цена — иначе продюсер не сможет сравнить варианты.")
        idx = FIELDS.index("price_private")
    await state.update_data(band=band, step=idx)
    await ask_step(message, state)


# ---------- ответы текстом ----------

@router.message(Onb.filling, F.text & ~F.text.startswith("/"))
async def on_text(message: Message, state: FSMContext):
    data = await state.get_data()
    field, kind, *_ = STEPS[data["step"]]
    text = message.text.strip()
    if kind in ("single", "multi"):
        await message.answer("Выберите вариант кнопками выше 👆")
        return
    if kind == "money":
        value = parse_money(text)
        if not value or value < 1000:
            await message.answer("Не понял сумму. Напишите, например, <code>60к</code> или <code>60 000</code>.")
            return
        await next_step(message, state, field, value)
    elif kind == "videos":
        links = URL_RE.findall(text)[:3]
        if not links:
            await message.answer("Не вижу ссылок. Пришлите ссылку, начинающуюся с https://")
            return
        await next_step(message, state, field, links)
    elif kind == "phone":
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) < 10:
            await message.answer("Похоже, номер неполный. Пример: +7 999 123-45-67")
            return
        await next_step(message, state, field, text[:50])
    else:
        await next_step(message, state, field, text[:1000] if field == "description" else text[:200])


# ---------- кнопки ----------

@router.callback_query(Onb.filling, F.data.startswith("ss:"))
async def on_single(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    field, kind, _, options, *_ = STEPS[data["step"]]
    code = cb.data[3:]
    if kind != "single" or code not in options:
        return
    await cb.message.edit_text(f"{cb.message.html_text}\n\n→ <b>{escape(options[code])}</b>")
    await next_step(cb.message, state, field, code)


@router.callback_query(Onb.filling, F.data.startswith("ms:"))
async def on_multi_toggle(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    field, kind, _, options, *_ = STEPS[data["step"]]
    code = cb.data[3:]
    if kind != "multi" or code not in options:
        await cb.answer()
        return
    band = data["band"]
    selected = list(band.get(field) or [])
    selected.remove(code) if code in selected else selected.append(code)
    band[field] = selected
    await state.update_data(band=band)
    await cb.message.edit_reply_markup(reply_markup=multi_select(options, selected))
    await cb.answer()


@router.callback_query(Onb.filling, F.data == "ms_done")
async def on_multi_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    field, kind, _, options, required, _ = STEPS[data["step"]]
    selected = data["band"].get(field) or []
    if required and not selected:
        await cb.answer("Отметьте хотя бы один вариант", show_alert=True)
        return
    await cb.answer()
    chosen = ", ".join(options[c] for c in selected) or "ничего"
    await cb.message.edit_text(f"{cb.message.html_text}\n\n→ <b>{escape(chosen)}</b>")
    await next_step(cb.message, state, field, selected, set_value=False)


@router.callback_query(Onb.filling, F.data.in_({"keep", "skip"}))
async def on_keep_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    field = STEPS[data["step"]][0]
    await cb.message.edit_reply_markup(reply_markup=None)
    if cb.data == "keep":
        await next_step(cb.message, state, field, None, set_value=False)
    else:
        await next_step(cb.message, state, field, [] if field == "video_links" else None)


# ---------- превью, согласие, сохранение ----------

def _band_from_data(band: dict) -> Band:
    b = Band(**{k: v for k, v in band.items() if k in FIELDS})
    for list_field in ("instruments", "genres", "services", "video_links"):
        if getattr(b, list_field) is None:
            setattr(b, list_field, [])
    b.source = "self"
    return b


async def show_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    preview = band_card(_band_from_data(data["band"]), full=True)
    await state.set_state(Onb.consent)
    await message.answer("Так вашу карточку увидят продюсеры:\n\n" + preview, disable_web_page_preview=True)
    await message.answer(
        "Отправляя анкету, вы соглашаетесь на публикацию карточки в каталоге и передачу "
        "ваших контактов продюсерам, которые ищут группу.",
        reply_markup=consent_kb(),
    )


@router.callback_query(Onb.consent, F.data.startswith("consent:"))
async def on_consent(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    action = cb.data.split(":")[1]
    await cb.message.edit_reply_markup(reply_markup=None)
    if action == "cancel":
        await state.clear()
        await cb.message.answer("Анкета не отправлена. Вернуться: /band", reply_markup=main_menu())
        return
    if action == "restart":
        await state.set_state(Onb.filling)
        await state.update_data(step=0)
        await ask_step(cb.message, state)
        return
    data = await state.get_data()
    now = datetime.now(timezone.utc)
    async with Session() as s:
        band = await s.get(Band, data["band_id"]) if data.get("band_id") else None
        if band is None:
            band = Band(source="self")
            s.add(band)
        for k, v in data["band"].items():
            if k in FIELDS:
                setattr(band, k, v)
        band.tg_user_id = cb.from_user.id
        band.tg_username = cb.from_user.username
        band.status = "pending"
        band.reject_reason = None
        band.consent_at = now
        band.prices_confirmed_at = now
        await s.commit()
        await s.refresh(band)
    await state.clear()
    await cb.message.answer(
        "Спасибо! Анкета отправлена на модерацию — обычно это занимает до суток. Я напишу, когда карточка "
        "появится в поиске. Посмотреть или обновить её: /band"
    )
    await notify_admins(cb.bot, band)


async def notify_admins(bot, band: Band):
    text = f"🆕 Анкета на модерацию (#{band.id}, источник: {band.source})\n\n" + band_card(band, full=True)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=moderation_kb(band.id),
                                   disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            log.warning("Cannot notify admin %s: %s", admin_id, e)


# ---------- «Моя группа» ----------

async def open_my_band(message: Message, state: FSMContext, user: User):
    await state.clear()
    async with Session() as s:
        band = (await s.execute(
            select(Band).where(Band.tg_user_id == user.id).order_by(Band.id.desc())
        )).scalars().first()
    if band is None:
        await start_onboarding(message, state, user)
        return
    status = STATUS_LABELS.get(band.status, band.status)
    extra = f"\nПричина: {escape(band.reject_reason)}" if band.status == "rejected" and band.reject_reason else ""
    await message.answer(
        f"Статус: <b>{status}</b>{extra}\n\n" + band_card(band, full=True),
        reply_markup=my_band_kb(),
        disable_web_page_preview=True,
    )


@router.message(Command("band"))
async def cmd_band(message: Message, state: FSMContext):
    await open_my_band(message, state, message.from_user)


@router.callback_query(F.data == "role:band")
async def role_band(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await open_my_band(cb.message, state, cb.from_user)


@router.callback_query(F.data.startswith("band:"))
async def my_band_actions(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    async with Session() as s:
        band = (await s.execute(
            select(Band).where(Band.tg_user_id == cb.from_user.id).order_by(Band.id.desc())
        )).scalars().first()
        if band is None:
            await start_onboarding(cb.message, state, cb.from_user)
            return
        if cb.data == "band:confirm":
            band.prices_confirmed_at = datetime.now(timezone.utc)
            await s.commit()
            await cb.message.answer("Отлично, отметил цены как актуальные ✅")
            return
    await start_onboarding(cb.message, state, cb.from_user, existing=band)
