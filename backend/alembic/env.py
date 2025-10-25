from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.base import Base

# Configurar logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configurar la URL de la base de datos
def get_url():
    """Obtener URL de la base de datos desde configuración"""
    database_url = settings.DATABASE_URL
    if not database_url:
        raise ValueError("DATABASE_URL no está configurada")
    return database_url

# Configurar el contexto de Alembic
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo 'offline'."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Ejecutar migraciones en modo 'online'."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()