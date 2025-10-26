# Endpoint de migración de emergencia
# Migración de emergencia para agregar columnas concesionario y analista

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/migracion-emergencia")
def migracion_emergencia(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Migración de emergencia para agregar columnas faltantes
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ejecutar migraciones")

    try:
        # Verificar si las columnas ya existen
        inspector = inspect(db.bind)
        columns = inspector.get_columns("clientes")
        column_names = [col["name"] for col in columns]

        migrations_applied = []

        # Agregar columna concesionario_id si no existe
        if "concesionario_id" not in column_names:
            db.execute(text("ALTER TABLE clientes ADD COLUMN concesionario_id INTEGER"))
            db.commit()
            migrations_applied.append("Agregada columna concesionario_id")

        # Agregar columna analista_id si no existe
        if "analista_id" not in column_names:
            db.execute(text("ALTER TABLE clientes ADD COLUMN analista_id INTEGER"))
            db.commit()
            migrations_applied.append("Agregada columna analista_id")

        return {
            "message": "Migración completada exitosamente",
            "migrations_applied": migrations_applied,
            "total_migrations": len(migrations_applied),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error en migración de emergencia: {e}")
        raise HTTPException(status_code=500, detail=f"Error en migración: {str(e)}")
