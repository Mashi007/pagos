"""
Excel Prestamos Drive: snapshot hoja CONCILIACIÓN filtrado por año/mes de la columna MES.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.reporte_clientes_hoja import parse_anos_meses_query
from app.services.reporte_prestamos_drive import build_prestamos_drive_excel

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/prestamos-drive")
def exportar_prestamos_drive_excel(
    db: Session = Depends(get_db),
    anos: str = Query("", description="Años separados por coma, ej. 2024,2025"),
    meses: str = Query("", description="Meses 1-12 separados por coma, ej. 10,11"),
):
    """
    Descarga Excel desde conciliacion_sheet_rows (misma fuente que Clientes hoja).
    Columnas: cedula, total_financiamiento, modalidad_pago, fecha_requerimiento,
    fecha_aprobacion, producto, concesionario, analista, modelo_vehiculo, numero_cuotas.
    Solo filas cuya columna MES parsea a año ∈ anos y mes ∈ meses.
    """
    logger.info(
        "[prestamos_drive] GET /exportar/prestamos-drive anos=%r meses=%r",
        anos,
        meses,
    )
    try:
        ya, mo = parse_anos_meses_query(anos, meses)
        content, n = build_prestamos_drive_excel(db, ya, mo)
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
    fname = f"Prestamos_drive_CONCILIACION_{hoy_str}.xlsx"
    logger.info("[prestamos_drive] GET OK filas=%s bytes=%s", n, len(content))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
