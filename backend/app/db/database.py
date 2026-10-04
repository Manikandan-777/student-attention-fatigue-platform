"""Database engine, session factory, and dependency injection. CON §7, SYS-12."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.db.models import Base


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _create_engine():
    url = settings.DATABASE_URL
    kwargs = {}
    if url.startswith("sqlite"):
        # Required for SQLite: enable FK enforcement and WAL mode
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, echo=False, **kwargs)


engine = _create_engine()

# Enable SQLite foreign-key enforcement on each connection
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create all tables (dev / test convenience). Use Alembic in production."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all tables (test teardown only)."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context-manager-based DB session for non-FastAPI callers (services, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
