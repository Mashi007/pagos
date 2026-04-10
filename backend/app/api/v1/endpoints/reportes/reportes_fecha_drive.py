"""
Excel Fecha Drive: ID préstamo, cédulas Drive/Sistema, fecha aprobación Q hoja vs BD.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.reporte_fecha_drive import build_fecha_drive_excel

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/fecha-drive")
def exportar_fecha_drive_excel(db: Session = Depends(get_db)):
    """
    Descarga Excel (hoja Fecha Drive) a partir de conciliacion_sheet_rows + prestamos.
    Columnas: ID préstamo, Cédula Drive, Cédula Sistema, Fecha aprobación Drive (Q), Fecha aprobación sistema.
    Ausencia en un lado: NE. Incluye filas solo en Drive y solo en sistema (sin cédula en hoja).
    """
    logger.info("[fecha_drive] GET /exportar/fecha-drive solicitud")
    try:
        content, n = build_fecha_drive_excel(db)
    except ValueError as e:
        logger.warning("[fecha_drive] GET /exportar/fecha-drive 404: %s", e)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("[fecha_drive] GET /exportar/fecha-drive error: %s", e)
        raise HTTPException(
            status_code=500, detail="Error al generar el reporte Fecha Drive."
        ) from e

    hoy_str = date.today().isoformat()
    logger.info(
        "[fecha_drive] GET /exportar/fecha-drive OK filas=%s bytes=%s",
        n,
        len(content),
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=FechaDrive_vs_hoja_CONCILIACION_5cols_{hoy_str}.xlsx"
            )
        },
    )
