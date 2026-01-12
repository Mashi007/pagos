"""
Script para crear la tabla de auditoría si no existe
Útil para ejecutar manualmente en producción si las migraciones fallaron
"""

import logging
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.utils.auditoria_table_helper import asegurar_tabla_auditoria, verificar_tabla_auditoria_existe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Función principal"""
    logger.info("=" * 60)
    logger.info("🔍 VERIFICANDO/CREANDO TABLA DE AUDITORÍA")
    logger.info("=" * 60)
    
    db = SessionLocal()
    try:
        # Verificar si existe
        if verificar_tabla_auditoria_existe(db):
            logger.info("✅ La tabla 'auditoria' ya existe")
            return 0
        
        logger.info("⚠️ La tabla 'auditoria' no existe. Intentando crearla...")
        
        # Intentar crear
        if asegurar_tabla_auditoria(db):
            logger.info("✅ Tabla 'auditoria' creada exitosamente")
            return 0
        else:
            logger.error("❌ No se pudo crear la tabla 'auditoria'")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error al verificar/crear tabla: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
