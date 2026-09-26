import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.db import init_db
from app.handlers import admin, onboarding, search, start


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан — заполните .env")
    if not settings.anthropic_api_key:
        logging.warning("ANTHROPIC_API_KEY не задан — работает простой разбор запросов без нейросети")
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(start.router, admin.router, onboarding.router, search.router)
    await bot.set_my_commands([
        BotCommand(command="search", description="Найти кавер-группу"),
        BotCommand(command="band", description="Моя группа / добавить группу"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
        BotCommand(command="help", description="Помощь"),
    ])
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
