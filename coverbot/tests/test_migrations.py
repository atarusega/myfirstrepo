from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.db import Base, migrate


def _diff(conn):
    return compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)


def _revision(conn):
    return MigrationContext.configure(conn).get_current_revision()


def test_migrations_match_models(tmp_path):
    # упал — в app/db.py поменяли модель без миграции: alembic revision --autogenerate -m "..."
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    with engine.begin() as conn:
        migrate(conn)
    with engine.connect() as conn:
        assert _diff(conn) == []
        assert _revision(conn) is not None


def test_legacy_create_all_db_is_adopted(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        conn.execute(text("INSERT INTO bands (name, instruments, genres, services, video_links, source, status) "
                          "VALUES ('Старая', '[]', '[]', '[]', '[]', 'self', 'published')"))
    with engine.begin() as conn:
        migrate(conn)
    with engine.connect() as conn:
        assert "alembic_version" in inspect(conn).get_table_names()
        assert _revision(conn) is not None
        assert conn.execute(text("SELECT name FROM bands")).scalar_one() == "Старая"
    with engine.begin() as conn:  # повторный старт ничего не ломает
        migrate(conn)
