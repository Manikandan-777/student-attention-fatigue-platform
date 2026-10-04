"""Alembic env.py — configured for Student Attention & Fatigue Detection System.

Uses the application engine directly so DATABASE_URL is always in sync with app.config.
render_as_batch=True enables SQLite ALTER TABLE support via table-recreation.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Make backend/ importable from the alembic/ subdirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import Base          # noqa: E402 — registers all ORM models
from app.db.database import engine      # noqa: E402 — uses settings.DATABASE_URL

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline mode — emit SQL to stdout without a live DB connection."""
    from app.config import settings

    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online mode — apply migrations against the live database."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
