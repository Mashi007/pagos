"""
Excel Prestamos Drive: snapshot hoja CONCILIACIÓN filtrado por columna LOTE.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.services.reporte_clientes_hoja import parse_lotes_query
from app.services.reporte_prestamos_drive import build_prestamos_drive_excel

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/prestamos-drive/debug-headers")
def debug_prestamos_drive_headers(
    db: Session = Depends(get_db),
):
    """
    DEBUG: Muestra las cabeceras detectadas en la hoja CONCILIACIÓN.
    Útil para diagnóstico cuando falla la detección de columnas.
    """
    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    
    normalized_headers = {}
    for i, h in enumerate(headers, 1):
        from app.services.reporte_prestamos_drive import _norm_header_cell
        normalized = _norm_header_cell(h)
        normalized_headers[f"Col_{i}"] = {
            "original": h,
            "normalized": normalized,
            "length": len(h) if h else 0,
        }
    
    return JSONResponse({
        "total_headers": len(headers),
        "headers_raw": headers,
        "headers_normalized": normalized_headers,
        "mensaje": "Copia los valores 'original' para ver exactamente el nombre de cada columna en la hoja",
    })


@router.get("/exportar/prestamos-drive")
def exportar_prestamos_drive_excel(
    db: Session = Depends(get_db),
    lotes: str = Query("", description="Lotes separados por coma (columna LOTE en la hoja), ej. 70 o 70,71"),
):
    """
    Descarga Excel desde conciliacion_sheet_rows (misma fuente que Clientes hoja).
    Columnas: cedula, total_financiamiento, modalidad_pago, fecha_requerimiento,
    fecha_aprobacion, producto, concesionario, analista, modelo_vehiculo, numero_cuotas.
    Solo filas cuyo LOTE coincide con uno de los valores en `lotes`.
    """
    logger.info("[prestamos_drive] GET /exportar/prestamos-drive lotes=%r", lotes)
    try:
        lo = parse_lotes_query(lotes)
        content, n = build_prestamos_drive_excel(db, lo)
    except ValueError as e:
        logger.warning("[prestamos_drive] GET 400/404: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("[prestamos_drive] GET error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el reporte Préstamos Drive.",
        ) from e

    hoy_str = date.today().isoformat()
    lpart = "-".join(str(x) for x in sorted(set(lo)))
    fname = f"Prestamos_drive_CONCILIACION_lotes_{lpart}_{hoy_str}.xlsx"
    logger.info("[prestamos_drive] GET OK filas=%s bytes=%s", n, len(content))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
