import os
import time
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
    Obtiene DATABASE_URL con normalización y reintentos.

    Normaliza automáticamente postgres:// a postgresql:// para
    compatibilidad con SQLAlchemy 1.4+.

    Returns:
        str: URL de conexión normalizada a la base de datos.

    Raises:
        ValueError: Si DATABASE_URL no está configurada después de reintentos.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        database_url = os.environ.get("DATABASE_URL")

        if database_url:
            # Normalizar: Railway puede usar postgres://, SQLAlchemy necesita
            # postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)

            logger.info(f"DATABASE_URL encontrada (intento {attempt}/{MAX_ATTEMPTS})")
            return database_url

        if attempt < MAX_ATTEMPTS:
            logger.warning(
                f"DATABASE_URL no encontrada, esperando {WAIT_SECONDS}s... "
                f"(intento {attempt}/{MAX_ATTEMPTS})"
            )
            time.sleep(WAIT_SECONDS)

    # Si llegamos aquí, no se encontró DATABASE_URL
    logger.error("DATABASE_URL no está configurada")
    logger.info("Variables de entorno relacionadas encontradas:")

    found_vars = False
    for key in sorted(os.environ.keys()):
        terms = ["DATA", "POSTGRES", "DB", "SQL"]
        if any(term in key.upper() for term in terms):
            # Enmascarar valores sensibles
            value = os.environ[key]
            if len(value) > MASK_THRESHOLD:
                masked = (
                    f"{value[:MASK_PREFIX_LENGTH]}..." f"{value[-MASK_SUFFIX_LENGTH:]}"
                )
            else:
                masked = "***"
            logger.info(f"  {key}: {masked}")
            found_vars = True

    if not found_vars:
        logger.warning("No se encontraron variables de entorno relacionadas con BD")

    raise ValueError(
        "DATABASE_URL no está configurada después de múltiples reintentos.\n\n"
        "SOLUCIÓN EN RAILWAY:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Verifica que el servicio PostgreSQL esté vinculado al proyecto\n"
        "2. Ve a: Settings -> Variables\n"
        "3. DATABASE_URL aparece auto al vincular PostgreSQL\n"
        "4. Si falta, regenera la vinculación desde el panel de PostgreSQL\n\n"
        "DESARROLLO LOCAL:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Crea archivo .env con:\n"
        "   DATABASE_URL=postgresql://user:password@localhost:5432/dbname\n"
        "2. Asegúrate de cargar dotenv antes de llamar get_url()\n\n"
        "Formato: postgresql://usuario:contraseña@host:puerto/base_datos"
    )


# Configuración de Alembic
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# Importar modelos para que Alembic los detecte
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base

# Configurar logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configurar URL de base de datos
config.set_main_option("sqlalchemy.url", get_url())

target_metadata = Base.metadata


def run_migrations_offline():
    """Ejecutar migraciones en modo offline"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Ejecutar migraciones en modo online"""
    connectable = engine_from_config(
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
