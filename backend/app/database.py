from __future__ import annotations

from typing import Any
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import DATABASE_URL

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine_kwargs: dict[str, Any] = {
    "future": True,
}

if IS_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL pool tuning (Render / Neon / Supabase)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(DATABASE_URL, **engine_kwargs)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db_backend_name() -> str:
    return "sqlite" if IS_SQLITE else engine.dialect.name


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
