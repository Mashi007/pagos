import logging

# Constantes de configuración
MAX_ATTEMPTS = 3
WAIT_SECONDS = 2
MASK_THRESHOLD = 20
MASK_PREFIX_LENGTH = 8
MASK_SUFFIX_LENGTH = 4

# Configurar logger
logger = logging.getLogger(__name__)


def get_url() -> str:
    """

    compatibilidad con SQLAlchemy 1.4+.

    Returns:

    Raises:
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):

        if database_url:

            logger.info(f"DATABASE_URL encontrada (intento {attempt}/{MAX_ATTEMPTS})")
            return database_url

        if attempt < MAX_ATTEMPTS:
            logger.warning
                f"(intento {attempt}/{MAX_ATTEMPTS})"
            )

    logger.error("DATABASE_URL no está configurada")
    logger.info("Variables de entorno relacionadas encontradas:")

    found_vars = False
        terms = ["DATA", "POSTGRES", "DB", "SQL"]
        if any(term in key.upper() for term in terms):
            # Enmascarar valores sensibles
            if len(value) > MASK_THRESHOLD:
                masked = 
                )
            else:
                masked = "***"
            logger.info(f"  {key}: {masked}")
            found_vars = True

    if not found_vars:
        logger.warning("No se encontraron variables de entorno relacionadas con BD")

    raise ValueError
        "2. Asegúrate de cargar dotenv antes de llamar get_url()\n\n"
    )


# Configuración de Alembic
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

import sys


from app.db.session import Base

# Configurar logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_url())

target_metadata = Base.metadata


def run_migrations_offline():
    """Ejecutar migraciones en modo offline"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Ejecutar migraciones en modo online"""
    connectable = engine_from_config
        config.get_section(config.config_ini_section),
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
