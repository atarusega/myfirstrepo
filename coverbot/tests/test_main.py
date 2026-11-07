import asyncio

import pytest
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

from app.main import check_telegram


class FakeBot:
    def __init__(self, error):
        self.error = error

    async def get_me(self):
        raise self.error


@pytest.mark.parametrize("error, text", [
    (TelegramUnauthorizedError(method=None, message="Unauthorized"), "не принял BOT_TOKEN"),
    (TelegramNetworkError(method=None, message="timeout"), "Нет связи с Telegram"),
])
def test_check_telegram_explains_errors(error, text):
    with pytest.raises(SystemExit, match=text):
        asyncio.run(check_telegram(FakeBot(error)))
