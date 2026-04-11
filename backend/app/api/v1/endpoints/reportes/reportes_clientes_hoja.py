"""
Excel Clientes: snapshot hoja CONCILIACIÓN filtrado por columna LOTE.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.reporte_clientes_hoja import build_clientes_hoja_excel, parse_lotes_query

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/clientes-hoja")
def exportar_clientes_hoja_excel(
    db: Session = Depends(get_db),
    lotes: str = Query("", description="Lotes separados por coma (columna LOTE en la hoja), ej. 70 o 70,71"),
):
    """
    Descarga Excel (hoja Clientes) desde conciliacion_sheet_rows.
    Columnas: Cédula, Nombres, Teléfono, Email.
    Solo filas cuyo LOTE (cabecera detectada, p. ej. columna B) coincide con uno de los valores en `lotes`.
    """
    logger.info("[clientes_hoja] GET /exportar/clientes-hoja lotes=%r", lotes)
    try:
        lo = parse_lotes_query(lotes)
        content, n = build_clientes_hoja_excel(db, lo)
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
    lpart = "-".join(str(x) for x in sorted(set(lo)))
    fname = f"Clientes_hoja_CONCILIACION_lotes_{lpart}_{hoy_str}.xlsx"
    logger.info("[clientes_hoja] GET OK filas=%s bytes=%s", n, len(content))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
