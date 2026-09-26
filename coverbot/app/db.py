from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import (JSON, BigInteger, DateTime, ForeignKey, Integer, MetaData, String, Text, UniqueConstraint,
                        func, inspect, select)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    # имена ограничений как у PostgreSQL по умолчанию: миграции могут ссылаться на них по имени
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "%(table_name)s_%(column_0_N_name)s_key",
        "fk": "%(table_name)s_%(column_0_name)s_fkey",
        "pk": "%(table_name)s_pkey",
    })


class Band(Base):
    __tablename__ = "bands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    travel_scope: Mapped[str | None] = mapped_column(String(20))  # city / region / russia
    lineup: Mapped[str | None] = mapped_column(String(20))
    instruments: Mapped[list] = mapped_column(JSON, default=list)
    genres: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    price_private: Mapped[int | None] = mapped_column(Integer)
    price_corporate: Mapped[int | None] = mapped_column(Integer)
    price_newyear: Mapped[int | None] = mapped_column(Integer)
    program_format: Mapped[str | None] = mapped_column(String(20))
    sound: Mapped[str | None] = mapped_column(String(20))
    services: Mapped[list] = mapped_column(JSON, default=list)
    video_links: Mapped[list] = mapped_column(JSON, default=list)
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(300))
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    tg_username: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(20), default="self")  # self / tutvse / demo
    source_note: Mapped[str | None] = mapped_column(Text)  # исходная «специализация» из импорта
    claim_token: Mapped[str | None] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/pending/published/rejected/archived
    reject_reason: Mapped[str | None] = mapped_column(Text)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prices_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # app/reminders.py
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Producer(Base):
    __tablename__ = "producers"

    tg_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100))
    full_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchRequest(Base):
    __tablename__ = "search_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)
    result_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int | None] = mapped_column(Integer)
    band_id: Mapped[int] = mapped_column(ForeignKey("bands.id", ondelete="CASCADE"), index=True)
    producer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("band_id", "recommender_tg_id", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    band_id: Mapped[int] = mapped_column(ForeignKey("bands.id", ondelete="CASCADE"), index=True)
    recommender_tg_id: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20))  # producer / tutvse
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
# первая миграция = схема, которую раньше создавал create_all
BASELINE_REVISION = "db4d70d6040a"


def migrate(connection) -> None:
    """Довести схему до последней миграции. Базу, созданную ещё через create_all, помечает как baseline."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["connection"] = connection
    tables = inspect(connection).get_table_names()
    if "bands" in tables and "alembic_version" not in tables:
        command.stamp(cfg, BASELINE_REVISION)
    command.upgrade(cfg, "head")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(migrate)


async def rec_counts(session: AsyncSession) -> dict[int, dict[str, int]]:
    rows = await session.execute(
        select(Recommendation.band_id, Recommendation.source, func.count()).group_by(
            Recommendation.band_id, Recommendation.source
        )
    )
    result: dict[int, dict[str, int]] = {}
    for band_id, source, count in rows:
        result.setdefault(band_id, {})[source] = count
    return result


async def ensure_producer(session: AsyncSession, user) -> None:
    if await session.get(Producer, user.id) is None:
        session.add(Producer(tg_user_id=user.id, username=user.username, full_name=user.full_name))
