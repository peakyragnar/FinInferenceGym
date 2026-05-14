"""Alembic environment.

Reads DATABASE_URL from the process environment (typically loaded via
`uv run --env-file .env ...` for local work, or a secret manager in
production) and injects it into Alembic's SQLAlchemy URL before any
migration runs.

`alembic.ini` deliberately does NOT carry the connection string — that
keeps the credential out of version control. See TECHNICAL.md.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_database_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is not set. Run alembic via "
            "`uv run --env-file .env ...` or export DATABASE_URL in your shell."
        )
    # SQLAlchemy needs the driver prefix to dispatch over psycopg3
    # rather than the legacy psycopg2. Keep the env value as a vanilla
    # postgresql:// URL (which psql, psycopg directly, and other tools
    # expect); rewrite only for SQLAlchemy here.
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


config.set_main_option("sqlalchemy.url", _resolve_database_url())

# No ORM models yet. Each consuming layer registers its SQLModel/SQLAlchemy
# metadata here as it lands (substep 4 -> beliefs/scores; Phase 1 -> emissions).
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
