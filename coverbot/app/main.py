import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aiogram.utils.token import TokenValidationError

from app import reminders
from app.config import settings
from app.db import init_db
from app.handlers import admin, onboarding, search, start

# брошенные анкеты и поиски не копятся в Redis вечно
STATE_TTL = timedelta(days=30)


def build_storage(redis_url: str | None) -> BaseStorage:
    if not redis_url:
        logging.warning("REDIS_URL не задан — состояния диалогов в памяти, при рестарте анкеты сбросятся")
        return MemoryStorage()
    return RedisStorage.from_url(redis_url, state_ttl=STATE_TTL, data_ttl=STATE_TTL)


async def check_telegram(bot: Bot) -> None:
    """Понятная ошибка вместо трассировки, если токен неверный или нет связи с Telegram."""
    try:
        me = await bot.get_me()
    except TelegramUnauthorizedError:
        raise SystemExit("Telegram не принял BOT_TOKEN — скопируйте токен от @BotFather в .env заново")
    except TelegramNetworkError as e:
        raise SystemExit(f"Нет связи с Telegram — проверьте интернет или VPN ({e})")
    if settings.bot_username and settings.bot_username.lower() != (me.username or "").lower():
        logging.warning("BOT_USERNAME=%s, а токен от бота @%s — ссылки импорта будут вести не туда",
                        settings.bot_username, me.username)
    logging.info("Бот @%s запущен", me.username)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан — заполните .env")
    if not settings.anthropic_api_key:
        logging.warning("ANTHROPIC_API_KEY не задан — работает простой разбор запросов без нейросети")
    try:
        bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    except TokenValidationError:
        raise SystemExit("BOT_TOKEN в .env не похож на токен от @BotFather (вида 123456789:AA...)")
    try:
        await check_telegram(bot)
        await init_db()
        dp = Dispatcher(storage=build_storage(settings.redis_url))
        dp.include_routers(start.router, admin.router, reminders.router, onboarding.router, search.router)
        await bot.set_my_commands([
            BotCommand(command="search", description="Найти кавер-группу"),
            BotCommand(command="band", description="Моя группа / добавить группу"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
            BotCommand(command="help", description="Помощь"),
        ])
        await bot.delete_webhook(drop_pending_updates=True)
        reminder_task = asyncio.create_task(reminders.price_reminder_loop(bot))
        try:
            await dp.start_polling(bot)
        finally:
            reminder_task.cancel()
            await dp.storage.close()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
