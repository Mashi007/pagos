import os
import time

def get_url():
    """Obtiene DATABASE_URL con normalización y reintentos"""
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            # Normalizar: Railway puede usar postgres://, SQLAlchemy necesita postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            print(f"✅ DATABASE_URL encontrada (intento {attempt})")
            return database_url
        
        if attempt < max_attempts:
            print(f"⏳ DATABASE_URL no encontrada, esperando... (intento {attempt}/{max_attempts})")
            time.sleep(2)
    
    # Si llegamos aquí, no se encontró DATABASE_URL
    print("❌ DATABASE_URL no está configurada")
    print("Variables de entorno disponibles:")
    for key in os.environ:
        if "DATA" in key or "POSTGRES" in key or "DB" in key:
            print(f"  - {key}")
    
    raise ValueError(
        "DATABASE_URL no está configurada.\n"
        "En Railway:\n"
        "1. Verifica que el servicio PostgreSQL esté vinculado\n"
        "2. Ve a Settings > Variables\n"
        "3. Debe existir DATABASE_URL automáticamente"
    )
