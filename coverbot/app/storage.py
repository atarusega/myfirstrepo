"""Состояния диалогов в нашей же базе: незаконченная анкета переживает перезапуск бота без Redis."""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from app.db import FsmState, Session

STATE_TTL = timedelta(days=30)  # брошенная анкета через месяц считается пустой


def _key(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or ''}:{key.destiny}"


def _fresh(row: FsmState | None) -> FsmState | None:
    if row is None:
        return None
    updated = row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=timezone.utc)
    return row if datetime.now(timezone.utc) - updated <= STATE_TTL else None


class DbStorage(BaseStorage):
    def __init__(self, session_factory=Session):
        self.session = session_factory

    async def _load(self, key: StorageKey) -> FsmState | None:
        async with self.session() as s:
            return _fresh(await s.get(FsmState, _key(key)))

    async def _save(self, key: StorageKey, **values) -> None:
        async with self.session() as s:
            row = await s.get(FsmState, _key(key))
            state, data = (row.state, row.data) if _fresh(row) else (None, "{}")
            state, data = values.get("state", state), values.get("data", data)
            if state is None and data == "{}":
                if row is not None:
                    await s.delete(row)
            else:
                if row is None:
                    row = FsmState(key=_key(key))
                    s.add(row)
                row.state, row.data, row.updated_at = state, data, datetime.now(timezone.utc)
            await s.commit()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        await self._save(key, state=state.state if isinstance(state, State) else state)

    async def get_state(self, key: StorageKey) -> str | None:
        row = await self._load(key)
        return row.state if row else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        await self._save(key, data=json.dumps(dict(data), ensure_ascii=False))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        row = await self._load(key)
        return json.loads(row.data) if row else {}

    async def close(self) -> None:
        pass
