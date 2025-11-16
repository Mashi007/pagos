from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent.parent))

# Cargar variables de entorno desde .env si existe
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # Si python-dotenv no está instalado, intentar cargar manualmente
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        except Exception:
            pass  # Si falla, continuar sin cargar .env

try:
    from app.core.config import settings
    from app.db.base import Base

    # Importar todos los modelos para que Alembic los detecte
    # Importación optimizada: solo importar cuando sea necesario para evitar problemas de serialización
    # Esto asegura que todos los modelos estén registrados en Base.metadata
    if not Base.metadata.tables:
        # Solo importar si los metadatos están vacíos (primera vez)
        import app.models  # noqa: F401
except Exception as e:
    # Mensajes de error más concisos para evitar problemas de serialización
    error_msg = str(e)[:200]  # Limitar longitud del mensaje
    print(f"[ERROR] Error al importar: {error_msg}")
    print(f"[INFO] Dir: {os.getcwd()}")
    db_url_preview = os.getenv('DATABASE_URL', 'NO CONFIGURADA')[:30] if os.getenv('DATABASE_URL') else 'NO CONFIGURADA'
    print(f"[INFO] DB: {db_url_preview}...")
    raise

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
