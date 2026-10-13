"""Окружение Alembic. Два режима:
- из командной строки (`alembic upgrade head`) — сам подключается к DATABASE_URL;
- из бота (`app.db.init_db`) — получает готовое соединение через config.attributes["connection"].
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    # render_as_batch: SQLite не умеет ALTER COLUMN, Alembic пересоздаёт таблицу
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True,
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
elif (connection := config.attributes.get("connection")) is not None:
    do_run_migrations(connection)
else:
    if config.config_file_name:
        fileConfig(config.config_file_name, disable_existing_loggers=False)
    asyncio.run(run_async_migrations())
