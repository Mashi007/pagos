"""API admin: Recibos (vista previa de pagos en ventana y ejecución manual)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.services.cuota_estado import hoy_negocio, parse_fecha_referencia_negocio
from app.services.recibos_conciliacion_email_job import (
    RECIBOS_VENTANA_SLOT,
    _cuerpo_html_recibos_confirmacion,
    ejecutar_recibos_envio_slot,
)
from app.services.recibos_conciliacion_listado_ui import listar_recibos_ventana_con_ui

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/plantilla-correo-html", response_class=HTMLResponse)
def get_recibos_plantilla_correo_html():
    """
    Devuelve el HTML exacto del correo Recibos (archivo en disco).
    Sirve de vista previa en la pantalla de configuración Recibos del frontend.
    """
    return HTMLResponse(
        content=_cuerpo_html_recibos_confirmacion(),
        media_type="text/html; charset=utf-8",
    )


class RecibosEjecutarBody(BaseModel):
    fecha_caracas: Optional[str] = Field(
        None,
        description=(
            "Día calendario Caracas (YYYY-MM-DD). Listado y simulación: opcional (omisión = hoy). "
            "Envío real de hoy: opcional (omisión = hoy). "
            "Envío real de un día pasado: obligatorio y además forzar_envio_fecha_pasada=true."
        ),
    )
    solo_simular: bool = Field(
        False,
        description="Si true: no envía correos ni escribe recibos_email_envio.",
    )
    forzar_envio_fecha_pasada: bool = Field(
        False,
        description=(
            "Solo envío real: confirma envío SMTP para fecha_caracas estrictamente anterior a hoy Caracas. "
            "Los jobs automáticos no usan este flag."
        ),
    )


@router.get("/listado")
def get_recibos_listado(
    fecha_caracas: Optional[str] = Query(
        None,
        description="Día de referencia Caracas (YYYY-MM-DD). Omisión = hoy.",
    ),
    db: Session = Depends(get_db),
):
    """Pagos conciliados PAGADO en la ventana con vínculo a cuotas, excluyendo cédulas ya enviadas Recibos ese día."""
    raw_fc = (fecha_caracas or "").strip()
    try:
        d = parse_fecha_referencia_negocio(raw_fc) if raw_fc else hoy_negocio()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if d is None:
        d = hoy_negocio()
    filas, kpis, total_pagos, cedulas_dist = listar_recibos_ventana_con_ui(db, fecha_dia=d)
    return {
        "fecha_dia": d.isoformat(),
        "slot": RECIBOS_VENTANA_SLOT,
        "total_pagos": total_pagos,
        "cedulas_distintas": cedulas_dist,
        "kpis": kpis,
        "pagos": filas,
    }


@router.post("/ejecutar")
def post_recibos_ejecutar(body: RecibosEjecutarBody, db: Session = Depends(get_db)):
    """
    Ejecuta el lote Recibos (admin). Simulación: cualquier fecha válida.
    Envío real: hoy sin flag extra; día pasado solo con forzar_envio_fecha_pasada=true (no fechas futuras).
    """
    hoy = hoy_negocio()
    try:
        d = parse_fecha_referencia_negocio(body.fecha_caracas) if body.fecha_caracas else hoy
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if d is None:
        d = hoy
    if not body.solo_simular:
        if d > hoy:
            raise HTTPException(
                status_code=422,
                detail="No se permite envío real de Recibos para una fecha futura (America/Caracas).",
            )
        if d < hoy and not body.forzar_envio_fecha_pasada:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Envío real para un día pasado requiere forzar_envio_fecha_pasada=true en el cuerpo "
                    "y fecha_caracas explícita. Use «Solo simular» para revisar sin SMTP, o el botón "
                    "de envío manual de lote pasado en la interfaz."
                ),
            )
    permite_pasado = bool(
        not body.solo_simular and d < hoy and body.forzar_envio_fecha_pasada
    )
    return ejecutar_recibos_envio_slot(
        db,
        fecha_dia=d,
        solo_simular=body.solo_simular,
        permite_envio_real_fecha_no_hoy=permite_pasado,
    )
