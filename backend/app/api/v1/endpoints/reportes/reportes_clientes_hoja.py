"""
Excel Clientes: snapshot hoja CONCILIACIÓN filtrado por año/mes de la columna MES.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.reporte_clientes_hoja import build_clientes_hoja_excel, parse_anos_meses_query

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/clientes-hoja")
def exportar_clientes_hoja_excel(
    db: Session = Depends(get_db),
    anos: str = Query("", description="Años separados por coma, ej. 2024,2025"),
    meses: str = Query("", description="Meses 1-12 separados por coma, ej. 10,11"),
):
    """
    Descarga Excel (hoja Clientes) desde conciliacion_sheet_rows.
    Columnas: Cédula, Nombres, Teléfono, Email.
    Solo filas cuya columna MES parsea a una fecha con año ∈ anos y mes ∈ meses.
    """
    logger.info("[clientes_hoja] GET /exportar/clientes-hoja anos=%r meses=%r", anos, meses)
    try:
        ya, mo = parse_anos_meses_query(anos, meses)
        content, n = build_clientes_hoja_excel(db, ya, mo)
    except ValueError as e:
        logger.warning("[clientes_hoja] GET 400/404: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("[clientes_hoja] GET error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el reporte Clientes (hoja).",
        ) from e

    hoy_str = date.today().isoformat()
    fname = f"Clientes_hoja_CONCILIACION_{hoy_str}.xlsx"
    logger.info("[clientes_hoja] GET OK filas=%s bytes=%s", n, len(content))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
