"""Alembic env — 使用 psycopg (libpq) 直连，不依赖 SQLAlchemy Engine。"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _REPO_ROOT / ".env"
load_dotenv(dotenv_path=_ENV_FILE if _ENV_FILE.is_file() else None)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = None


def _get_pg_url() -> str:
    """从环境变量获取 PostgreSQL 连接串。"""
    uri = os.getenv("POSTGRES_URI", "").strip()
    if not uri:
        uri = "postgresql+psycopg://postgres:password@localhost:5432/ops_brain"
    if uri.startswith("postgres://"):
        uri = "postgresql://" + uri[len("postgres://") :]
    if uri.startswith("postgresql+asyncpg://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql+asyncpg://") :]
    elif uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://") :]
    return uri


def run_migrations_offline() -> None:
    context.configure(
        url=_get_pg_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    connectable = create_engine(_get_pg_url(), poolclass=None)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
