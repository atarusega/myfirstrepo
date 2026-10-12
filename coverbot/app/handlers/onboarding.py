"""Анкета кавер-группы. Шаги описаны таблицей BLOCKS; один FSM-state заполнения + индекс шага в данных.
«Исправить поле» проходит те же шаги, но только диапазон fix_start..stop, потом превью или сразу сохранение."""
import logging
from datetime import datetime, timezone
from html import escape
from typing import NamedTuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, User
from sqlalchemy import delete, select

from app.cards import STATUS_LABELS, band_card
from app.config import settings
from app.consent import CONSENT_FULL, CONSENT_SHORT, CONSENT_VERSION
from app.db import Band, Lead, Producer, Recommendation, SearchRequest, Session
from app.dictionaries import (GENRES, INSTRUMENTS, LINEUPS, NEWYEAR_MARKUP, PRICE_PRESETS, PROGRAM_FORMATS,
                              SERVICES, SOUND, TOP_CITIES, TRAVEL)
from app.keyboards import (BACK_TEXT, PHONE_KEEP, PHONE_SKIP, city_select, consent_intro_kb, delete_confirm_kb,
                           fields_kb, keep_or_skip, main_menu, moderation_kb, multi_select, my_band_kb, phone_kb,
                           preview_kb, price_select, single_select, with_rows)
from app.utils import URL_RE, fmt_money, fmt_short, parse_money

log = logging.getLogger(__name__)
router = Router()


class Onb(StatesGroup):
    intro = State()    # согласие перед первым вопросом
    filling = State()
    preview = State()
    fields = State()   # меню «Исправить поле»


class Step(NamedTuple):
    field: str
    kind: str  # text / city / single / multi / price / videos / phone
    prompt: str
    options: dict | None = None
    required: bool = True
    skip: str | None = None  # текст кнопки «пропустить»


NO_PRICE = "Не берём такие"

BLOCKS: list[tuple[str, list[Step]]] = [
    ("О группе", [
        Step("name", "text", "Как называется ваш проект или группа?"),
        Step("city", "city", "В каком городе вы базируетесь? Выберите или напишите свой."),
        Step("travel_scope", "single", "Куда готовы выезжать?", TRAVEL),
    ]),
    ("Состав и жанры", [
        Step("lineup", "single", "Какой у вас состав?", LINEUPS),
        Step("instruments", "multi", "Отметьте вокал и инструменты в составе (можно несколько):", INSTRUMENTS),
        Step("genres", "multi", "Какие жанры играете? Отметьте всё подходящее:", GENRES),
    ]),
    ("Цены", [
        Step("price_private", "price", "Цена <b>«от»</b> за стандартную программу на <b>частном событии</b> "
             "(свадьба, ДР, юбилей):", required=False, skip=NO_PRICE),
        Step("price_corporate", "price", "Цена <b>«от»</b> на <b>корпоративе</b>:", required=False, skip=NO_PRICE),
        Step("price_newyear", "price", "Цена <b>«от»</b> на <b>Новый год</b> (декабрьские корпоративы):",
             required=False, skip=NO_PRICE),
    ]),
    ("Программа", [
        Step("program_format", "single", "Что входит в стандартную программу?", PROGRAM_FORMATS),
        Step("sound", "single", "Как со звуком?", SOUND),
        Step("services", "multi", "Какие доп. услуги можете предложить? Если никаких — просто «Готово».",
             SERVICES, required=False),
    ]),
    ("Видео и контакты", [
        Step("video_links", "videos",
             "Пришлите 1–3 ссылки на <b>живые выступления</b> (YouTube, VK, Rutube, Яндекс Диск, Telegram). "
             "Можно одним сообщением.\n"
             "<i>Нет под рукой — жмите «Пришлю позже»: анкета сохранится черновиком.</i>"),
        Step("phone", "phone", "Телефон для связи: нажмите «Поделиться номером» внизу или напишите. "
             "Необязательно — продюсеры увидят ваш Telegram.", required=False, skip=PHONE_SKIP),
        Step("website", "text", "Сайт или соцсети (необязательно):", required=False, skip="Пропустить"),
        Step("description", "text", "И последнее: чем вы отличаетесь? Репертуар, фишки, опыт — 2–3 предложения.\n"
             "<i>Необязательно, но так точнее подбирать вас под запросы.</i>", required=False, skip="Пропустить"),
    ]),
]
STEPS = [step for _, steps in BLOCKS for step in steps]
STEP_BLOCK = [b for b, (_, steps) in enumerate(BLOCKS) for _ in steps]
FIELDS = [s.field for s in STEPS]
PRICE_FIELDS = ("price_private", "price_corporate", "price_newyear")

# «Исправить поле»: подпись → первое и последнее поле диапазона шагов
FIX_MENU = [
    ("Название", "name", "name"), ("Город", "city", "city"), ("Выезд", "travel_scope", "travel_scope"),
    ("Состав", "lineup", "lineup"), ("Инструменты", "instruments", "instruments"), ("Жанры", "genres", "genres"),
    ("Цены", "price_private", "price_newyear"), ("Программа", "program_format", "program_format"),
    ("Звук", "sound", "sound"), ("Доп. услуги", "services", "services"), ("Видео", "video_links", "video_links"),
    ("Телефон", "phone", "phone"), ("Сайт", "website", "website"), ("Описание", "description", "description"),
]
# правка этих полей у опубликованной карточки снова отправляет её на модерацию
MODERATED_FIELDS = {"name", "description"}


def _display(field: str, value) -> str | None:
    if value in (None, "", []):
        return None
    if field in PRICE_FIELDS:
        return fmt_money(value)
    if field == "video_links":
        return f"{len(value)} ссылк(и)"
    return str(value)


def _header(data: dict) -> str:
    if data.get("stop") is not None:
        return "<b>Исправляем</b>\n"
    b = STEP_BLOCK[data["step"]]
    return f"<b>{BLOCKS[b][0]}</b> · блок {b + 1} из {len(BLOCKS)}\n"


def _new_data(user: User, existing: Band | None) -> dict:
    return {
        "step": 0, "stop": None, "fix_start": None, "back_to": None,
        "band": {f: getattr(existing, f) for f in FIELDS} if existing else {},
        "band_id": existing.id if existing else None,
        "tg_username": user.username,
        "consent": bool(existing and existing.consent_version == CONSENT_VERSION),
    }


# ---------- вход в анкету и согласие ----------

async def start_onboarding(message: Message, state: FSMContext, user: User, existing: Band | None = None):
    data = _new_data(user, existing)
    await state.set_data(data)
    if not data["consent"]:
        await state.set_state(Onb.intro)
        await message.answer(CONSENT_SHORT, reply_markup=consent_intro_kb())
        return
    await _begin(message, state, updating=bool(existing and existing.name))


async def _begin(message: Message, state: FSMContext, updating: bool):
    await state.set_state(Onb.filling)
    await message.answer(
        "Обновим анкету. На каждом шаге можно оставить текущее значение."
        if updating else
        "Заполним анкету — ≈3 минуты, почти всё кнопками. Ошиблись — жмите «← Назад». Отменить: /cancel"
    )
    await ask_step(message, state)


@router.callback_query(Onb.intro, F.data.startswith("cs:"))
async def on_consent_intro(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    action = cb.data[3:]
    if action == "full":
        await cb.message.answer(CONSENT_FULL, reply_markup=consent_intro_kb())
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    if action == "no":
        await state.clear()
        await cb.message.answer("Без согласия анкету сохранить не можем. Передумаете — /band. Вопросы — /support.",
                                reply_markup=main_menu())
        return
    await state.update_data(consent=True)
    data = await state.get_data()
    await _begin(cb.message, state, updating=bool(data["band"].get("name")))


# ---------- шаги ----------

async def ask_step(message: Message, state: FSMContext):
    data = await state.get_data()
    idx, band, stop = data["step"], data["band"], data.get("stop")
    if idx >= len(STEPS) or (stop is not None and idx > stop):
        await finish_steps(message, state)
        return
    step = STEPS[idx]
    current = band.get(step.field)
    keep = _display(step.field, current)
    text = _header(data) + step.prompt
    back = idx > 0 or stop is not None
    if step.kind == "single":
        kb = with_rows(single_select(step.options, current), back=back)
    elif step.kind == "multi":
        kb = with_rows(multi_select(step.options, current or []), back=back)
    elif step.kind == "city":
        extra = [(f"Оставить: {current[:40]}", "keep")] if current and current not in TOP_CITIES.values() else []
        kb = with_rows(city_select(current), *extra, back=back)
    elif step.kind == "price":
        extra = []
        corp = band.get("price_corporate")
        if step.field == "price_newyear" and corp:
            ny = round(corp * NEWYEAR_MARKUP / 1000) * 1000
            extra.append((f"Как корпоратив + {round((NEWYEAR_MARKUP - 1) * 100)}% ({fmt_short(ny)})", f"pr:{ny}"))
        if current and current not in PRICE_PRESETS:
            extra.append((f"Оставить: {keep}", "keep"))
        extra.append((step.skip, "skip"))
        kb = with_rows(price_select(current), *extra, back=back)
    elif step.kind == "phone":
        can_skip = bool(data.get("tg_username"))
        if not can_skip:
            text = (_header(data) + "У вашего Telegram нет юзернейма, поэтому продюсерам нужен телефон. "
                    "Нажмите «Поделиться номером» внизу или напишите номер:")
        await message.answer(text, reply_markup=phone_kb(keep, can_skip, back))
        return
    elif step.kind == "videos":
        kb = with_rows(keep_or_skip(keep, None), *([] if current else [("Пришлю позже", "skip")]), back=back)
    else:
        kb = with_rows(keep_or_skip(keep, step.skip), back=back)
    await message.answer(text, reply_markup=kb)


async def next_step(message: Message, state: FSMContext, value=None, set_value: bool = True):
    data = await state.get_data()
    idx, band = data["step"], data["band"]
    step = STEPS[idx]
    if set_value:
        band[step.field] = value
    if step.kind == "phone":  # убрать кнопку «Поделиться номером» из-под поля ввода
        await message.answer("Принял ✅", reply_markup=ReplyKeyboardRemove())
    idx += 1
    # после последней цены проверяем, что хотя бы одна указана
    if step.field == "price_newyear" and not any(band.get(p) for p in PRICE_FIELDS):
        await message.answer("Нужна хотя бы одна цена — иначе продюсер не сможет сравнить варианты.")
        idx = FIELDS.index("price_private")
    await state.update_data(band=band, step=idx)
    await ask_step(message, state)


async def go_back(message: Message, state: FSMContext):
    data = await state.get_data()
    idx, stop = data["step"], data.get("stop")
    if idx < len(STEPS) and STEPS[idx].kind == "phone":
        await message.answer("Вернулись назад", reply_markup=ReplyKeyboardRemove())
    if stop is not None and idx <= data["fix_start"]:
        await show_fields(message, state)
        return
    await state.update_data(step=max(idx - 1, 0))
    await ask_step(message, state)


async def finish_steps(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("back_to") == "save":
        await save_fix(message, state)
    else:
        await show_preview(message, state)


# ---------- ответы текстом ----------

@router.message(Onb.filling, F.contact)
async def on_contact(message: Message, state: FSMContext):
    data = await state.get_data()
    if STEPS[data["step"]].kind == "phone":
        await next_step(message, state, message.contact.phone_number[:50])


@router.message(Onb.filling, F.text & ~F.text.startswith("/"))
async def on_text(message: Message, state: FSMContext):
    data = await state.get_data()
    step = STEPS[data["step"]]
    text = message.text.strip()
    if text == BACK_TEXT:
        await go_back(message, state)
        return
    if step.kind in ("single", "multi"):
        await message.answer("Выберите вариант кнопками выше 👆")
    elif step.kind == "price":
        value = parse_money(text)
        if not value or value < 1000:
            await message.answer("Не понял сумму. Напишите, например, <code>60к</code> или <code>60 000</code>.")
            return
        await next_step(message, state, value)
    elif step.kind == "videos":
        links = URL_RE.findall(text)[:3]
        if not links:
            await message.answer("Не вижу ссылок. Пришлите ссылку, начинающуюся с https://")
            return
        await next_step(message, state, links)
    elif step.kind == "phone":
        if text == PHONE_KEEP and data["band"].get("phone"):
            await next_step(message, state, set_value=False)
            return
        if text == PHONE_SKIP and data.get("tg_username"):
            await next_step(message, state, None)
            return
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) < 10:
            await message.answer("Похоже, номер неполный. Пример: +7 999 123-45-67")
            return
        await next_step(message, state, text[:50])
    elif step.kind == "city":
        await next_step(message, state, text[:100])
    else:
        await next_step(message, state, text[:1000] if step.field == "description" else text[:200])


# ---------- кнопки ----------

async def _mark_answer(cb: CallbackQuery, answer: str):
    await cb.message.edit_text(f"{cb.message.html_text}\n\n→ <b>{escape(answer)}</b>")


@router.callback_query(Onb.filling, F.data.startswith("ss:"))
async def on_single(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    step = STEPS[(await state.get_data())["step"]]
    code = cb.data[3:]
    if step.kind != "single" or code not in step.options:
        return
    await _mark_answer(cb, step.options[code])
    await next_step(cb.message, state, code)


@router.callback_query(Onb.filling, F.data.startswith("ct:"))
async def on_city(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    step = STEPS[(await state.get_data())["step"]]
    city = TOP_CITIES.get(cb.data[3:])
    if step.kind != "city" or city is None:
        return
    await _mark_answer(cb, city)
    await next_step(cb.message, state, city)


@router.callback_query(Onb.filling, F.data == "ct_other")
async def on_city_other(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("Напишите название города сообщением 👇")


@router.callback_query(Onb.filling, F.data.startswith("pr:"))
async def on_price(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    step = STEPS[(await state.get_data())["step"]]
    value = cb.data[3:]
    if step.kind != "price" or not value.isdigit():
        return
    await _mark_answer(cb, f"от {fmt_money(int(value))}")
    await next_step(cb.message, state, int(value))


@router.callback_query(Onb.filling, F.data == "pr_exact")
async def on_price_exact(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("Напишите сумму сообщением: <code>60к</code> или <code>60 000</code> 👇")


@router.callback_query(Onb.filling, F.data.startswith("ms:"))
async def on_multi_toggle(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = STEPS[data["step"]]
    code = cb.data[3:]
    if step.kind != "multi" or code not in step.options:
        await cb.answer()
        return
    band = data["band"]
    selected = list(band.get(step.field) or [])
    selected.remove(code) if code in selected else selected.append(code)
    band[step.field] = selected
    await state.update_data(band=band)
    back = data["step"] > 0 or data.get("stop") is not None
    await cb.message.edit_reply_markup(reply_markup=with_rows(multi_select(step.options, selected), back=back))
    await cb.answer()


@router.callback_query(Onb.filling, F.data == "ms_done")
async def on_multi_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = STEPS[data["step"]]
    if step.kind != "multi":
        await cb.answer()
        return
    selected = data["band"].get(step.field) or []
    if step.required and not selected:
        await cb.answer("Отметьте хотя бы один вариант", show_alert=True)
        return
    await cb.answer()
    await _mark_answer(cb, ", ".join(step.options[c] for c in selected) or "ничего")
    await next_step(cb.message, state, set_value=False)


@router.callback_query(Onb.filling, F.data.in_({"keep", "skip"}))
async def on_keep_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    step = STEPS[(await state.get_data())["step"]]
    await cb.message.edit_reply_markup(reply_markup=None)
    if cb.data == "keep":
        await next_step(cb.message, state, set_value=False)
    else:
        await next_step(cb.message, state, [] if step.field == "video_links" else None)


@router.callback_query(Onb.filling, F.data == "back")
async def on_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await go_back(cb.message, state)


# ---------- «Исправить поле» ----------

async def show_fields(message: Message, state: FSMContext):
    await state.set_state(Onb.fields)
    await message.answer("Что исправить?", reply_markup=fields_kb([label for label, *_ in FIX_MENU]))


async def start_fix(message: Message, state: FSMContext, first: str, last: str):
    start = FIELDS.index(first)
    await state.update_data(step=start, fix_start=start, stop=FIELDS.index(last))
    await state.set_state(Onb.filling)
    await ask_step(message, state)


@router.callback_query(Onb.fields, F.data.startswith("fx:"))
async def on_fix_field(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    i = cb.data[3:]
    if not i.isdigit() or int(i) >= len(FIX_MENU):
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    _, first, last = FIX_MENU[int(i)]
    await start_fix(cb.message, state, first, last)


@router.callback_query(Onb.fields, F.data == "fx_back")
async def on_fix_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if (await state.get_data()).get("back_to") == "preview":
        await show_preview(cb.message, state)
    else:
        await open_my_band(cb.message, state, cb.from_user)


# ---------- превью и отправка ----------

def _band_from_data(band: dict) -> Band:
    b = Band(**{k: v for k, v in band.items() if k in FIELDS})
    for list_field in ("instruments", "genres", "services", "video_links"):
        if getattr(b, list_field) is None:
            setattr(b, list_field, [])
    b.source = "self"
    return b


async def show_preview(message: Message, state: FSMContext):
    await state.update_data(stop=None, fix_start=None, step=len(STEPS))
    await state.set_state(Onb.preview)
    band = (await state.get_data())["band"]
    await message.answer("Так вашу карточку увидят продюсеры:\n\n" + band_card(_band_from_data(band), full=True),
                         disable_web_page_preview=True)
    has_video = bool(band.get("video_links"))
    await message.answer(
        "Всё верно?" if has_video else
        "Видео пока нет — сохраним анкету черновиком. В каталог она попадёт, когда пришлёте ссылки: "
        "/band → «Исправить поле» → «Видео».",
        reply_markup=preview_kb(has_video),
    )


@router.callback_query(Onb.preview, F.data.startswith("pv:"))
async def on_preview(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    action = cb.data[3:]
    await cb.message.edit_reply_markup(reply_markup=None)
    if action == "cancel":
        await state.clear()
        await cb.message.answer("Анкета не отправлена. Вернуться: /band", reply_markup=main_menu())
    elif action == "fix":
        await state.update_data(back_to="preview")
        await show_fields(cb.message, state)
    elif action == "send":
        await submit(cb, state)


async def submit(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    has_video = bool(data["band"].get("video_links"))
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
        band.status = "pending" if has_video else "draft"
        band.reject_reason = None
        if band.consent_version != CONSENT_VERSION:
            band.consent_at, band.consent_version = now, CONSENT_VERSION
        band.prices_confirmed_at = now
        band.video_reminder_at = None
        await s.commit()
        await s.refresh(band)
    await state.clear()
    if has_video:
        await cb.message.answer(
            f"Спасибо! Анкета №{band.id} отправлена на модерацию — обычно это до суток. "
            "Напишу, когда карточка появится в каталоге.\n\nИсправить что-то: /band · Вопросы: /support"
        )
        await notify_admins(cb.bot, band)
    else:
        await cb.message.answer(
            f"Анкета №{band.id} сохранена черновиком. Пришлите видео — /band → «Исправить поле» → «Видео», "
            "и она уйдёт на модерацию. Завтра напомню."
        )


async def save_fix(message: Message, state: FSMContext):
    """Правка сохранённой анкеты из «Моей группы»: пишем сразу, на модерацию — только если нужно."""
    data = await state.get_data()
    await state.clear()
    now = datetime.now(timezone.utc)
    async with Session() as s:
        band = await s.get(Band, data["band_id"])
        if band is None or band.tg_user_id != data.get("owner_id"):
            await message.answer("Анкета не найдена. Заполнить заново: /band")
            return
        changed = {k for k, v in data["band"].items() if k in FIELDS and getattr(band, k) != v}
        for k in changed:
            setattr(band, k, data["band"][k])
        if changed & set(PRICE_FIELDS):
            band.prices_confirmed_at = now
        to_moderation = bool(changed) and bool(band.video_links) and (
            band.status in ("draft", "rejected") or (band.status == "published" and changed & MODERATED_FIELDS)
        )
        if to_moderation:
            band.status, band.reject_reason = "pending", None
        await s.commit()
        await s.refresh(band)
    if not changed:
        await message.answer("Ничего не поменялось.")
    elif to_moderation:
        await message.answer("Сохранил ✅ Анкета ушла на модерацию — обычно это до суток.")
        await notify_admins(message.bot, band)
    else:
        await message.answer("Сохранил ✅")
    await show_my_band(message, band)


async def notify_admins(bot, band: Band):
    text = f"🆕 Анкета №{band.id} на модерацию (источник: {band.source})\n\n" + band_card(band, full=True)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=moderation_kb(band.id),
                                   disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            log.warning("Cannot notify admin %s: %s", admin_id, e)


# ---------- «Моя группа» ----------

async def _my_band(tg_user_id: int) -> Band | None:
    async with Session() as s:
        return (await s.execute(
            select(Band).where(Band.tg_user_id == tg_user_id).order_by(Band.id.desc())
        )).scalars().first()


async def show_my_band(message: Message, band: Band):
    status = STATUS_LABELS.get(band.status, band.status)
    extra = ""
    if band.status == "rejected" and band.reject_reason:
        extra = f"\nПричина: {escape(band.reject_reason)}"
    elif band.status == "draft" and not band.video_links:
        extra = "\nДобавьте видео — и анкета уйдёт на модерацию: «Исправить поле» → «Видео»."
    elif band.status == "archived":
        extra = "\nЦены давно не подтверждались. Нажмите «Цены актуальны» — карточка вернётся в каталог."
    await message.answer(
        f"<b>Анкета №{band.id}</b> · {status}{extra}\n\n" + band_card(band, full=True),
        reply_markup=my_band_kb(),
        disable_web_page_preview=True,
    )


async def open_my_band(message: Message, state: FSMContext, user: User):
    await state.clear()
    band = await _my_band(user.id)
    if band is None:
        await start_onboarding(message, state, user)
        return
    await show_my_band(message, band)


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
    action = cb.data[5:]
    band = await _my_band(cb.from_user.id)
    if band is None:
        await start_onboarding(cb.message, state, cb.from_user)
        return
    if action == "confirm":
        async with Session() as s:
            band = await s.get(Band, band.id)
            band.prices_confirmed_at = datetime.now(timezone.utc)
            restored = band.status == "archived"
            if restored:
                band.status = "published"
            await s.commit()
        await cb.message.answer("Карточка снова в каталоге, цены отмечены как актуальные ✅" if restored
                                else "Отлично, отметил цены как актуальные ✅")
        return
    if action == "delete":
        await ask_delete(cb.message)
        return
    if action == "edit" or band.consent_version != CONSENT_VERSION:
        await start_onboarding(cb.message, state, cb.from_user, existing=band)
        return
    await state.clear()
    data = _new_data(cb.from_user, band)
    data.update(back_to="save", owner_id=cb.from_user.id)
    await state.set_data(data)
    if action == "prices":
        await start_fix(cb.message, state, "price_private", "price_newyear")
    elif action == "video":
        await start_fix(cb.message, state, "video_links", "video_links")
    else:
        await show_fields(cb.message, state)


# ---------- удаление данных ----------

async def ask_delete(message: Message):
    await message.answer(
        "Удалить все ваши данные из бота? Карточка группы пропадёт из каталога, анкету, контакты и историю "
        "поиска сотрём. Отменить это нельзя.",
        reply_markup=delete_confirm_kb(),
    )


async def delete_user_data(tg_user_id: int) -> int:
    """Стереть всё, что связано с пользователем: его группы (с лидами и рекомендациями) и следы продюсера."""
    async with Session() as s:
        band_ids = (await s.execute(select(Band.id).where(Band.tg_user_id == tg_user_id))).scalars().all()
        if band_ids:
            await s.execute(delete(Lead).where(Lead.band_id.in_(band_ids)))
            await s.execute(delete(Recommendation).where(Recommendation.band_id.in_(band_ids)))
            await s.execute(delete(Band).where(Band.id.in_(band_ids)))
        await s.execute(delete(Lead).where(Lead.producer_id == tg_user_id))
        await s.execute(delete(Recommendation).where(Recommendation.recommender_tg_id == tg_user_id))
        await s.execute(delete(SearchRequest).where(SearchRequest.producer_id == tg_user_id))
        await s.execute(delete(Producer).where(Producer.tg_user_id == tg_user_id))
        await s.commit()
    return len(band_ids)


@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    await state.clear()
    await ask_delete(message)


@router.callback_query(F.data.startswith("del:"))
async def on_delete(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if cb.data != "del:yes":
        await cb.message.answer("Ок, ничего не удаляю.")
        return
    await state.clear()
    bands = await delete_user_data(cb.from_user.id)
    log.info("User %s deleted their data (%s bands)", cb.from_user.id, bands)
    await cb.message.answer("Готово: все ваши данные удалены. Захотите вернуться — /start.")
