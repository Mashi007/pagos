"""
Script para crear el índice ix_pagos_fecha_registro
Detectado como faltante en auditoría integral del endpoint /pagos
"""

import sys
import io
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.db.session import SessionLocal, engine
from app.core.config import settings

def crear_indice():
    """Crea el índice ix_pagos_fecha_registro si no existe"""
    
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        
        # Verificar si la tabla existe
        if 'pagos' not in inspector.get_table_names():
            print("⚠️ Tabla 'pagos' no existe")
            return False
        
        # Verificar si la columna existe
        columnas = [col['name'] for col in inspector.get_columns('pagos')]
        if 'fecha_registro' not in columnas:
            print("⚠️ Columna 'fecha_registro' no existe en tabla 'pagos'")
            return False
        
        # Verificar si el índice ya existe
        indices = [idx['name'] for idx in inspector.get_indexes('pagos')]
        if 'ix_pagos_fecha_registro' in indices:
            print("ℹ️ Índice 'ix_pagos_fecha_registro' ya existe")
            return True
        
        # Crear el índice
        try:
            db.execute(text(
                "CREATE INDEX ix_pagos_fecha_registro ON pagos (fecha_registro)"
            ))
            db.commit()
            print("✅ Índice 'ix_pagos_fecha_registro' creado exitosamente")
            return True
        except Exception as e:
            print(f"❌ Error creando índice: {e}")
            db.rollback()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("CREACIÓN DE ÍNDICE: ix_pagos_fecha_registro")
    print("=" * 70)
    
    exito = crear_indice()
    
    if exito:
        print("\n✅ Proceso completado exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Proceso completado con errores")
        sys.exit(1)
