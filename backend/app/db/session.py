"""
Configuración de la sesión de base de datos y creación de Base.
"""
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


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
    max_attempts = 3
    wait_seconds = 2
    
    for attempt in range(1, max_attempts + 1):
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            # Normalizar: Railway puede usar postgres://, SQLAlchemy necesita postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            print(f"✅ DATABASE_URL encontrada (intento {attempt}/{max_attempts})")
            return database_url
        
        if attempt < max_attempts:
            print(
                f"⏳ DATABASE_URL no encontrada, reintentando en {wait_seconds}s... "
                f"(intento {attempt}/{max_attempts})"
            )
            time.sleep(wait_seconds)
    
    # DATABASE_URL no encontrada después de todos los reintentos
    print("\n" + "=" * 70)
    print("❌ DATABASE_URL no está configurada")
    print("=" * 70)
    print("\n📋 Variables de entorno relacionadas encontradas:")
    
    found_vars = False
    for key in sorted(os.environ.keys()):
        if any(term in key.upper() for term in ["DATA", "POSTGRES", "DB", "SQL"]):
            value = os.environ[key]
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 20 else "***"
            print(f"  • {key} = {masked}")
            found_vars = True
    
    if not found_vars:
        print("  ⚠️  Ninguna variable relacionada encontrada")
    
    print("=" * 70 + "\n")
    
    raise ValueError(
        "DATABASE_URL no está configurada después de múltiples reintentos.\n\n"
        "🔧 SOLUCIÓN EN RAILWAY:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Verifica que el servicio PostgreSQL esté vinculado al proyecto\n"
        "2. Ve a: Settings → Variables\n"
        "3. DATABASE_URL debe aparecer automáticamente al vincular PostgreSQL\n"
        "4. Si falta, regenera la vinculación desde el panel de PostgreSQL\n\n"
        "🔍 DESARROLLO LOCAL:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Crea archivo .env con:\n"
        "   DATABASE_URL=postgresql://user:password@localhost:5432/dbname\n"
        "2. Asegúrate de cargar dotenv antes de llamar get_url()\n\n"
        "💡 Formato: postgresql://usuario:contraseña@host:puerto/base_datos"
    )


# Obtener DATABASE_URL
DATABASE_URL = get_url()

# Crear engine de SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica conexiones antes de usarlas
    pool_size=10,              # Tamaño del pool de conexiones
    max_overflow=20,           # Conexiones adicionales permitidas
    echo=False,                # True para ver SQL queries (debug)
)

# Crear SessionLocal para instancias de sesión
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Crear Base declarativa - CRÍTICO: esto es lo que importa base.py
Base = declarative_base()


# Dependency para FastAPI
def get_db():
    """
    Generador de sesión de base de datos para dependencias de FastAPI.
    
    Yields:
        Session: Sesión de base de datos activa.
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
