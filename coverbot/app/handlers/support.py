"""Поддержка: пользователь пишет вопрос → бот пересылает админам с меткой #u<id> → админ отвечает реплаем
на это сообщение → бот отправляет ответ пользователю (app/handlers/admin.py: support_reply)."""
import logging
import re
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy import select

from app.config import settings
from app.db import Band, Session

log = logging.getLogger(__name__)
router = Router()

USER_TAG_RE = re.compile(r"#u(\d+)")


class Support(StatesGroup):
    waiting = State()


async def ask_question(message: Message, state: FSMContext):
    await state.clear()
    if not settings.admin_ids:
        log.warning("ADMIN_IDS пуст — поддержке некуда пересылать вопросы")
        await message.answer("Поддержка временно недоступна, попробуйте позже.")
        return
    await state.set_state(Support.waiting)
    await message.answer("Напишите вопрос или опишите проблему одним сообщением — можно со скриншотом. "
                         "Передам команде, ответ придёт сюда. Отменить: /cancel")


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext):
    await ask_question(message, state)


@router.callback_query(F.data == "support")
async def support_button(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await ask_question(cb.message, state)


async def _header(user: User) -> str:
    async with Session() as s:
        band = (await s.execute(select(Band).where(Band.tg_user_id == user.id).order_by(Band.id.desc())
                                )).scalars().first()
    who = escape(user.full_name) + (f" (@{escape(user.username)})" if user.username else "")
    band_line = f"\nАнкета №{band.id}: {escape(band.name or '—')} · {band.status}" if band else ""
    return f"💬 <b>Поддержка</b> · {who} · #u{user.id}{band_line}\n<i>Ответьте реплаем — ответ уйдёт пользователю.</i>"


@router.message(Support.waiting, ~F.text.startswith("/"))
async def on_question(message: Message, state: FSMContext):
    await state.clear()
    header = await _header(message.from_user)
    delivered = 0
    for admin_id in settings.admin_ids:
        try:
            if message.text:
                await message.bot.send_message(admin_id, f"{header}\n\n{escape(message.text)}",
                                               disable_web_page_preview=True)
            else:
                caption = f"{header}\n\n{escape(message.caption)}" if message.caption else header
                try:
                    await message.copy_to(admin_id, caption=caption[:1024])
                except TelegramAPIError:  # стикеры и кружки без подписи
                    sent = await message.copy_to(admin_id)
                    await message.bot.send_message(admin_id, header, reply_to_message_id=sent.message_id)
            delivered += 1
        except TelegramAPIError as e:
            log.warning("Cannot deliver support message to admin %s: %s", admin_id, e)
    if delivered:
        await message.answer("Передал ✅ Ответим здесь же, обычно в течение дня.")
    else:
        await message.answer("Не получилось передать сообщение, попробуйте позже: /support")


def user_id_from_tag(text: str | None) -> int | None:
    match = USER_TAG_RE.search(text or "")
    return int(match.group(1)) if match else None
