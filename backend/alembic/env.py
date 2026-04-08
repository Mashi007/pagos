"""
Entorno Alembic: usa DATABASE_URL de app.core.config (carga .env en backend).
Ejecutar siempre con cwd = backend:  alembic upgrade head
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Raíz del paquete backend (directorio que contiene `app/`)
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def get_database_url() -> str:
    from app.core.config import settings

    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            # Una transacción por revisión: libera bloqueos entre pasos y reduce
            # deadlocks con la app (p. ej. ALTER en usuarios tras muchos DDL).
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
