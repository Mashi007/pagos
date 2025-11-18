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

# Importar configuración básica primero (sin modelos todavía)
# Esto es necesario para get_url() y otras funciones
try:
    from app.core.config import settings
    from app.db.base import Base
except Exception as e:
    error_msg = str(e)[:200]
    print(f"[ERROR] Error al importar configuración: {error_msg}")
    raise

# Importación lazy y segura de modelos para evitar congelamientos
# NO importar modelos aquí - se importarán solo cuando sea necesario
_models_imported = False

def import_models():
    """Importar modelos de forma lazy solo cuando sea necesario"""
    global _models_imported
    if _models_imported:
        return
    
    try:
        # Importar modelos solo si los metadatos están vacíos
        # Usar importación directa pero con manejo de errores robusto
        if not Base.metadata.tables:
            # Importar modelos directamente - esto es necesario para que Alembic los detecte
            # La importación directa es más rápida que importlib para este caso
            import app.models  # noqa: F401
            
        _models_imported = True
    except Exception as e:
        # Mensajes de error más concisos para evitar problemas de serialización
        error_msg = str(e)[:200]  # Limitar longitud del mensaje
        print(f"[ERROR] Error al importar modelos: {error_msg}")
        print(f"[INFO] Dir: {os.getcwd()}")
        db_url_preview = os.getenv('DATABASE_URL', 'NO CONFIGURADA')[:30] if os.getenv('DATABASE_URL') else 'NO CONFIGURADA'
        print(f"[INFO] DB: {db_url_preview}...")
        # No hacer raise aquí - permitir que continúe si los modelos ya están cargados
        # Esto evita bloqueos si hay un error menor en la importación
        if not _models_imported:
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
# Inicializar target_metadata con Base.metadata (vacío por ahora)
# Los modelos se importarán de forma lazy cuando sea necesario
target_metadata = Base.metadata

# Función para asegurar que los modelos estén importados
def ensure_models_imported():
    """Asegurar que los modelos estén importados antes de usar target_metadata"""
    import_models()

def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo 'offline'."""
    # Asegurar que los modelos estén importados antes de ejecutar migraciones
    ensure_models_imported()
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
    # Asegurar que los modelos estén importados antes de ejecutar migraciones
    ensure_models_imported()
    configuration = config.get_section(config.config_ini_section)
    database_url = get_url()
    configuration["sqlalchemy.url"] = database_url

    # Configurar pool con timeout para evitar bloqueos
    # Agregar parámetros de conexión con timeout para PostgreSQL
    connect_args = {}
    if database_url.startswith("postgresql"):
        connect_args["connect_timeout"] = 10  # 10 segundos timeout de conexión
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No usar pool para evitar bloqueos
        connect_args=connect_args,
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
