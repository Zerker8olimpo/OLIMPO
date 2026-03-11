from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context


# -------------------------------------------------------
# FIX PATH FOR RENDER
# Permite que Alembic encuentre el módulo "backend"
# -------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))


# -------------------------------------------------------
# ALEMBIC CONFIG
# -------------------------------------------------------
config = context.config


# -------------------------------------------------------
# DATABASE URL FROM ENV (Render)
# -------------------------------------------------------
database_url = os.getenv("DATABASE_URL")

if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


# -------------------------------------------------------
# LOGGING
# -------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# -------------------------------------------------------
# IMPORT MODELS FOR AUTOGENERATE
# -------------------------------------------------------
from backend.database.base import Base

import backend.database.models.user
import backend.database.models.subscription


target_metadata = Base.metadata


# -------------------------------------------------------
# OFFLINE MIGRATIONS
# -------------------------------------------------------
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


# -------------------------------------------------------
# ONLINE MIGRATIONS
# -------------------------------------------------------
def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------------
# RUN
# -------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()