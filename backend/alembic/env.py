from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Agregar el directorio raíz al path de Python
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importar configuración
from app.config import settings
from app.db.session import Base

# Importar TODOS los modelos para que Alembic los detecte
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago

# Configuración de Alembic
config = context.config

# Sobrescribir la URL de SQLAlchemy con la variable de entorno
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar logging si existe archivo de configuración
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata target para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecutar migraciones en modo 'offline'.
    Útil para generar scripts SQL sin conexión a BD.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecutar migraciones en modo 'online'.
    Se conecta a la base de datos y aplica cambios.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Determinar modo de ejecución
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
