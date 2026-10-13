import asyncio
import json
from types import SimpleNamespace

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.criteria import fallback_parse
from app.db import Band, migrate
from app.handlers.onboarding import Onb, start_onboarding
from app.main import build_storage
from app.storage import DbStorage


class JsonCheckingStorage(MemoryStorage):
    """Как MemoryStorage, но падает на данных, которые RedisStorage не сможет сохранить."""

    async def set_data(self, key, data):
        assert json.loads(json.dumps(data)) == data
        await super().set_data(key, data)


class FakeMessage:
    async def answer(self, *args, **kwargs):
        pass


def test_build_storage():
    assert isinstance(build_storage(None), DbStorage)
    assert isinstance(build_storage("redis://localhost:6379/0"), RedisStorage)


def test_onboarding_data_is_json_safe():
    existing = Band(id=7, name="Кавер Бэнд", city="Москва", travel_scope="region", lineup="band_4_5",
                    instruments=["vocal_m", "guitar"], genres=["dance_mix"], description="Играем всё",
                    price_private=50000, price_corporate=None, price_newyear=100000, program_format="std",
                    sound="included", services=[], video_links=["https://youtu.be/x"], phone=None, website=None)
    user = SimpleNamespace(username="band")
    state = FSMContext(JsonCheckingStorage(), StorageKey(bot_id=1, chat_id=2, user_id=2))
    asyncio.run(start_onboarding(FakeMessage(), state, user, existing=existing))
    assert asyncio.run(state.get_data())["band"]["name"] == "Кавер Бэнд"


def test_search_criteria_is_json_safe():
    data = fallback_parse("корпоратив в Москве, 150 человек, до 120к, рок").model_dump()
    assert json.loads(json.dumps(data)) == data


def test_db_storage_survives_restart(tmp_path):
    with create_engine(f"sqlite:///{tmp_path / 'fsm.db'}").begin() as conn:
        migrate(conn)
    key = StorageKey(bot_id=1, chat_id=2, user_id=2)

    async def run():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'fsm.db'}")
        factory = async_sessionmaker(engine, expire_on_commit=False)
        first = DbStorage(factory)
        await first.set_state(key, Onb.filling)
        await first.set_data(key, {"step": 4, "band": {"name": "Кавер Бэнд", "genres": ["pop"]}})
        restarted = DbStorage(factory)  # «перезапуск бота» — новое хранилище, та же база
        assert await restarted.get_state(key) == Onb.filling.state
        assert (await restarted.get_data(key))["band"]["name"] == "Кавер Бэнд"
        await restarted.set_state(key, None)
        await restarted.set_data(key, {})
        assert await restarted.get_state(key) is None and await restarted.get_data(key) == {}
        await engine.dispose()

    asyncio.run(run())
