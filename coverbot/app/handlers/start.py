from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import settings
from app.db import Band, Session
from app.handlers import onboarding
from app.keyboards import claim_kb, main_menu

router = Router()

WELCOME = (
    "Привет! Я помогаю быстро найти кавер-группу на свадьбу, корпоратив или любое событие.\n\n"
    "🔎 <b>Продюсерам</b> — опишите задачу своими словами, и я подберу подходящие группы с ценами и видео.\n"
    "🎸 <b>Музыкантам</b> — заполните короткую анкету, и продюсеры смогут найти вас.\n\n"
    "Команды: /search — поиск, /band — моя группа, /support — написать нам, /delete — удалить мои данные."
)
# этап 1: поиск выключен — зовём музыкантов
WELCOME_COLLECTING = (
    "Привет! Я собираю каталог кавер-групп для ивент-продюсеров: свадьбы, корпоративы, Новый год.\n\n"
    "🎸 <b>Музыкантам</b> — анкета ≈3 минуты, почти всё кнопками. Продюсеры будут находить вас "
    "по городу, бюджету и жанрам.\n"
    "🔎 <b>Продюсерам</b> — подбор групп скоро запустим.\n\n"
    "Команды: /band — моя группа, /support — написать нам, /delete — удалить мои данные."
)


def welcome() -> str:
    return WELCOME if settings.search_enabled else WELCOME_COLLECTING


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    args = command.args or ""
    if args.startswith("tv_"):
        await show_claim(message, args[3:])
        return
    await message.answer(welcome(), reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(welcome(), reply_markup=main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок, отменил. Что дальше?", reply_markup=main_menu())


async def show_claim(message: Message, token: str):
    async with Session() as s:
        band = (await s.execute(select(Band).where(Band.claim_token == token))).scalar_one_or_none()
    if band is None or (band.tg_user_id and band.tg_user_id != message.from_user.id):
        await message.answer("Ссылка недействительна или уже использована.", reply_markup=main_menu())
        return
    text = (
        "Мы нашли вашу карточку из базы «Тут все»:\n\n"
        f"<b>{band.name}</b>\nГород: {band.city or '—'}\n"
        f"Специализация: {band.source_note or '—'}\n\n"
        "Чтобы продюсеры находили вас в поиске, нужно добавить цену, жанры и видео — это ≈3 минуты. Это вы?"
    )
    await message.answer(text, reply_markup=claim_kb(token))


@router.callback_query(F.data.startswith("claim:"))
async def claim_cb(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    parts = cb.data.split(":")
    if parts[1] == "no":
        await cb.message.edit_text("Понял, карточку не трогаю. Если что — /start.")
        return
    token = parts[2]
    async with Session() as s:
        band = (await s.execute(select(Band).where(Band.claim_token == token))).scalar_one_or_none()
        if band is None or (band.tg_user_id and band.tg_user_id != cb.from_user.id):
            await cb.message.answer("Ссылка недействительна.")
            return
        band.tg_user_id = cb.from_user.id
        band.tg_username = cb.from_user.username
        await s.commit()
        await s.refresh(band)
    await cb.message.edit_reply_markup(reply_markup=None)
    await onboarding.start_onboarding(cb.message, state, cb.from_user, existing=band)
