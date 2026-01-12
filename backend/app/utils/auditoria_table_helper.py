"""
Helper para asegurar que la tabla de auditoría existe
Crea la tabla si no existe para evitar errores en producción
"""

import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import engine, Base
from app.models.auditoria import Auditoria

logger = logging.getLogger(__name__)

# Cache para evitar verificaciones repetidas en la misma sesión
_table_exists_cache = None


def verificar_tabla_auditoria_existe(db: Session) -> bool:
    """
    Verifica si la tabla auditoria existe en la base de datos.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        True si existe, False en caso contrario
    """
    global _table_exists_cache
    
    # Si ya verificamos y existe, retornar True
    if _table_exists_cache is True:
        return True
    
    try:
        inspector = inspect(engine)
        tablas = inspector.get_table_names()
        existe = "auditoria" in tablas
        
        # Actualizar cache solo si existe
        if existe:
            _table_exists_cache = True
            
        return existe
    except Exception as e:
        logger.warning(f"Error al verificar existencia de tabla auditoria: {e}")
        return False


def crear_tabla_auditoria_si_no_existe(db: Session) -> bool:
    """
    Crea la tabla auditoria si no existe.
    Usa el modelo SQLAlchemy para crear la tabla.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        True si la tabla existe o se creó exitosamente, False en caso contrario
    """
    global _table_exists_cache
    
    # Verificar si ya existe
    if verificar_tabla_auditoria_existe(db):
        logger.debug("Tabla 'auditoria' ya existe")
        return True
    
    try:
        logger.info("⚠️ Tabla 'auditoria' no existe. Intentando crearla...")
        
        # Crear la tabla usando el modelo SQLAlchemy
        Base.metadata.create_all(engine, tables=[Auditoria.__table__], checkfirst=True)
        
        # Verificar que se creó correctamente
        if verificar_tabla_auditoria_existe(db):
            logger.info("✅ Tabla 'auditoria' creada exitosamente")
            _table_exists_cache = True
            return True
        else:
            logger.error("❌ No se pudo verificar la creación de la tabla 'auditoria'")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error al crear tabla 'auditoria': {e}")
        # Intentar crear usando SQL directo como fallback
        try:
            logger.info("Intentando crear tabla usando SQL directo...")
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS auditoria (
                        id SERIAL PRIMARY KEY,
                        usuario_id INTEGER NOT NULL REFERENCES users(id),
                        accion VARCHAR(50) NOT NULL,
                        entidad VARCHAR(50) NOT NULL,
                        entidad_id INTEGER,
                        detalles TEXT,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        exito BOOLEAN NOT NULL DEFAULT true,
                        mensaje_error TEXT,
                        fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                    )
                """))
                
                # Crear índices
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_id ON auditoria(id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_usuario_id ON auditoria(usuario_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_accion ON auditoria(accion)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_entidad ON auditoria(entidad)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_entidad_id ON auditoria(entidad_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auditoria_fecha ON auditoria(fecha)
                """))
                
                conn.commit()
                
            if verificar_tabla_auditoria_existe(db):
                logger.info("✅ Tabla 'auditoria' creada exitosamente usando SQL directo")
                _table_exists_cache = True
                return True
            else:
                logger.error("❌ No se pudo verificar la creación de la tabla después de SQL directo")
                return False
                
        except Exception as sql_error:
            logger.error(f"❌ Error al crear tabla usando SQL directo: {sql_error}")
            return False


def asegurar_tabla_auditoria(db: Session) -> bool:
    """
    Asegura que la tabla auditoria existe.
    Si no existe, intenta crearla.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        True si la tabla existe o se creó exitosamente, False en caso contrario
    """
    if verificar_tabla_auditoria_existe(db):
        return True
    
    return crear_tabla_auditoria_si_no_existe(db)
