
import logging
from fastapi 
import APIRouter, Depends, HTTPException
from sqlalchemy 
import text
from sqlalchemy.orm 
import Session
from app.api.deps 
import get_current_user, get_db
from app.models.user 
import Userlogger = logging.getLogger(__name__)router = APIRouter()@router.post("/ejecutar-migracion-concesionario-analista")async 
def ejecutar_migracion_emergencia(    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    Endpoint de emergencia para ejecutar la migraciÃ³n de concesionarioy    analista    """    try:
        logger.info(            f"Ejecutando migraciÃ³n de emergencia -     Usuario:
 {current_uuser.email}"        )        # Verificar si las columnas ya existen        
from sqlalchemy 
import inspect        inspector = inspect(db.bind)        columns = [col["name"] for col in inspector.get_columns("clientes")]        logger.info(f"Columnas actuales en clientes:
 {columns}")        # Agregar concesionario si no existe        if "concesionario" not in columns:
            logger.info("Agregando columna 'concesionario'")            db.execute(                text(                    "ALTER TABLE clientes ADD COLUMN concesionario VARCHAR    (100)"                )            )            db.execute(                text(                    "CREATE INDEX idx_clientes_concesionario ON clientes     (concesionario)"                )            )            logger.info("âœ… Columna 'concesionario' agregada")        else:
            logger.info("â„¹ï¸ Columna 'concesionario' ya existe")        # Agregar analista si no existe        if "analista" not in columns:
            logger.info("Agregando columna 'analista'")            db.execute(                text("ALTER TABLE clientes ADD COLUMN analista VARCHAR(100)")            )            db.execute(                text(                    "CREATE INDEX idx_clientes_analista ON clientes (analista)"                )            )            logger.info("âœ… Columna 'analista' agregada")        else:
            logger.info("â„¹ï¸ Columna 'analista' ya existe")        # Confirmar cambios        db.commit()        # Verificar estructura final        inspector = inspect(db.bind)        final_columns = [            col["name"] for col in inspector.get_columns("clientes")        ]        logger.info(f"Columnas finales en clientes:
 {final_columns}")        return {            "success":
 True,            "message":
 "MigraciÃ³n ejecutada exitosamente",            "columns_added":
 {                "concesionario":
 "concesionario" in final_columns,                "analista":
 "analista" in final_columns,            },            "total_columns":
 len(final_columns),        }    except Exception as e:
        logger.error(f"Error en migraciÃ³n de emergencia:
 {e}")        db.rollback()        raise HTTPException(            status_code=500, detail=f"Error ejecutando migraciÃ³n:
 {str(e)}"        )





