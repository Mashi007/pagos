# -*- coding: utf-8 -*-
"""
Excel: auditoría Gmail plantilla A–D → pagos → cuotas (`pagos_gmail_abcd_cuotas_traza`).
"""
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza

from app.api.v1.endpoints.reportes_utils import _parse_fecha

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

_MAX_RANGO_DIAS = 366


@router.get("/exportar/pagos-gmail-abcd")
def exportar_pagos_gmail_abcd_excel(
    db: Session = Depends(get_db),
    fecha_desde: str = Query(..., description="YYYY-MM-DD inicio (inclusive)"),
    fecha_hasta: str = Query(..., description="YYYY-MM-DD fin (inclusive)"),
):
    """
    Descarga Excel con filas de `pagos_gmail_abcd_cuotas_traza` cuyo `created_at`
    cae en el rango [fecha_desde, fecha_hasta] por día calendario.
    """
    fd = _parse_fecha(fecha_desde)
    fh = _parse_fecha(fecha_hasta)
    if fd > fh:
        fd, fh = fh, fd
    if (fh - fd).days > _MAX_RANGO_DIAS:
        raise HTTPException(
            status_code=400,
            detail=f"El rango no puede superar {_MAX_RANGO_DIAS} días.",
        )

    try:
        rows = (
            db.execute(
                select(PagosGmailAbcdCuotasTraza)
                .where(
                    func.date(PagosGmailAbcdCuotasTraza.created_at) >= fd,
                    func.date(PagosGmailAbcdCuotasTraza.created_at) <= fh,
                )
                .order_by(PagosGmailAbcdCuotasTraza.created_at.asc())
            )
            .scalars()
            .all()
        )
    except ProgrammingError as e:
        logger.warning("exportar pagos-gmail-abcd: tabla ausente o error SQL: %s", e)
        raise HTTPException(
            status_code=503,
            detail="La tabla de auditoría Gmail no está disponible. Aplique la migración 059 o el SQL de creación.",
        ) from e
    except Exception as e:
        logger.exception("exportar pagos-gmail-abcd: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al consultar la auditoría Gmail.",
        ) from e

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos Gmail"
    ws.append(
        [
            "Reporte Pagos Gmail (ABCD → pagos → cuotas)",
            f"Desde {fd.isoformat()} hasta {fh.isoformat()}",
        ]
    )
    ws.append([])
    ws.append(
        [
            "id",
            "created_at",
            "sync_id",
            "sync_item_id",
            "plantilla",
            "cedula",
            "numero_referencia",
            "banco_excel",
            "archivo_adjunto",
            "comprobante_imagen_id",
            "duplicado_documento",
            "etapa_final",
            "motivo",
            "detalle",
            "pago_id",
            "prestamo_id",
            "cuotas_completadas",
            "cuotas_parciales",
            "conciliado_final",
            "pago_estado_final",
        ]
    )
    for r in rows:
        ca = r.created_at
        ca_str = ca.isoformat(sep=" ", timespec="seconds") if ca else ""
        ws.append(
            [
                r.id,
                ca_str,
                r.sync_id,
                r.sync_item_id,
                r.plantilla_fmt or "",
                r.cedula or "",
                r.numero_referencia or "",
                r.banco_excel or "",
                r.archivo_adjunto or "",
                r.comprobante_imagen_id or "",
                bool(r.duplicado_documento),
                r.etapa_final or "",
                r.motivo or "",
                (r.detalle or "")[:32000],
                r.pago_id,
                r.prestamo_id,
                int(r.cuotas_completadas or 0),
                int(r.cuotas_parciales or 0),
                r.conciliado_final if r.conciliado_final is not None else "",
                r.pago_estado_final or "",
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    fname = f"reporte_pagos_gmail_{fd.isoformat()}_{fh.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
