import os
import time
from alembic import context

def get_url():
    """Obtiene la URL de la base de datos con reintentos"""
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            # Railway usa postgres:// pero SQLAlchemy necesita postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            return database_url
        
        attempt += 1
        if attempt < max_attempts:
            print(f"⏳ Esperando DATABASE_URL... intento {attempt}/{max_attempts}")
            time.sleep(2)
    
    raise ValueError(
        "❌ DATABASE_URL no está configurada después de varios intentos.\n"
        "Verifica que el servicio PostgreSQL esté vinculado en Railway."
    )
