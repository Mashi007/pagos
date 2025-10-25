
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    try:
        logger.info(
        )

        total_result = db.execute(
        )
        total = total_result.fetchone()[0]

        # 2. Verificar estructura de la tabla
        columns_result = db.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
        """
            )
        )
        columns = columns_result.fetchall()

            text(
                """
            SELECT id, nombre, activo, created_at, updated_at
            ORDER BY id
            LIMIT 10
        """
            )
        )

        stats_result = db.execute(
            text(
                """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN nombre NOT LIKE 'Concesionario #%' THEN 1 END) as reales
        """
            )
        )
        stats = stats_result.fetchone()

        nombres_reales_result = db.execute(
            text(
                """
            SELECT nombre
            WHERE nombre NOT LIKE 'Concesionario #%'
            LIMIT 5
        """
            )
        )
        nombres_reales = nombres_reales_result.fetchall()

            text(
                """
            WHERE activo = true
        """
            )
        )

        # Preparar respuesta
        response = {
            "usuario": current_user.email,
            "analisis": {
                "estructura_tabla": [
                    {
                        "columna": col[0],
                        "tipo": col[1],
                        "nullable": col[2] == "YES",
                    }
                    for col in columns
                ],
                    {
                        "id": reg[0],
                        "nombre": reg[1],
                        "activo": reg[2],
                        "created_at": reg[3].isoformat() if reg[3] else None,
                        "updated_at": reg[4].isoformat() if reg[4] else None,
                    }
                ],
                "estadisticas": {
                    "total": stats[0],
                    "reales": stats[2],
                    "porcentaje_reales": (
                        round((stats[2] / stats[0]) * 100, 2)
                        if stats[0] > 0
                        else 0
                    ),
                },
                "nombres_reales": [nombre[0] for nombre in nombres_reales],
            },
            "conclusion": {
                "problema_identificado": (
                    if stats[1] > stats[2]
                ),
                "recomendacion": (
                    if stats[1] > stats[2]
                ),
            },
        }

        logger.info(
            f"✅ Verificación completada - Total: {total}, Reales: {stats[2]}"
        )
        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
        )
