"""
Excel Análisis financiamiento: hoja CONCILIACIÓN (sync) vs total_financiamiento en préstamos.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.reporte_analisis_financiamiento import build_analisis_financiamiento_excel

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/analisis-financiamiento")
def exportar_analisis_financiamiento_excel(db: Session = Depends(get_db)):
    """
    Descarga Excel (hoja Análisis financiamiento) desde conciliacion_sheet_rows + préstamos.
    Columnas: ID préstamo, Cédula Drive, Cédula Sistema, Total financiamiento Drive, Total financiamiento sistema.
    """
    logger.info("[analisis_financiamiento] GET /exportar/analisis-financiamiento solicitud")
    try:
        content, n = build_analisis_financiamiento_excel(db)
    except ValueError as e:
        logger.warning("[analisis_financiamiento] GET 404: %s", e)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("[analisis_financiamiento] GET error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el reporte Análisis financiamiento.",
        ) from e

    hoy_str = date.today().isoformat()
    logger.info(
        "[analisis_financiamiento] GET OK filas=%s bytes=%s",
        n,
        len(content),
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=Analisis_financiamiento_vs_hoja_CONCILIACION_5cols_{hoy_str}.xlsx"
            )
        },
    )
