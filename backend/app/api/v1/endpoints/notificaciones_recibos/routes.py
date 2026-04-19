"""API admin: Recibos (vista previa de pagos en ventana y ejecución manual)."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.services.cuota_estado import hoy_negocio, parse_fecha_referencia_negocio
from app.services.recibos_conciliacion_email_job import (
    RecibosSlot,
    ejecutar_recibos_envio_slot,
    listar_pagos_recibos_ventana,
)

router = APIRouter(dependencies=[Depends(require_admin)])


class RecibosEjecutarBody(BaseModel):
    slot: Literal["manana", "tarde", "noche"]
    fecha_caracas: Optional[str] = Field(
        None,
        description=(
            "Día calendario Caracas (YYYY-MM-DD). Listado y simulación: opcional (omisión = hoy). "
            "Envío real: ignorado en servidor — solo hoy, alineado al job programado y fecha_registro."
        ),
    )
    solo_simular: bool = Field(
        False,
        description="Si true: no envía correos ni escribe recibos_email_envio.",
    )


@router.get("/listado")
def get_recibos_listado(
    slot: RecibosSlot = Query(..., description="Franja: manana | tarde | noche"),
    fecha_caracas: Optional[str] = Query(
        None,
        description="Día de referencia Caracas (YYYY-MM-DD). Omisión = hoy.",
    ),
    db: Session = Depends(get_db),
):
    """Pagos conciliados PAGADO con fecha_registro en la ventana y vínculo a cuotas."""
    raw_fc = (fecha_caracas or "").strip()
    try:
        d = parse_fecha_referencia_negocio(raw_fc) if raw_fc else hoy_negocio()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if d is None:
        d = hoy_negocio()
    pagos = listar_pagos_recibos_ventana(db, fecha_dia=d, slot=slot)
    cedulas = sorted({(p.get("cedula_normalizada") or "").strip() for p in pagos if p.get("cedula_normalizada")})
    return {
        "fecha_dia": d.isoformat(),
        "slot": slot,
        "total_pagos": len(pagos),
        "cedulas_distintas": len(cedulas),
        "pagos": pagos,
    }


@router.post("/ejecutar")
def post_recibos_ejecutar(body: RecibosEjecutarBody, db: Session = Depends(get_db)):
    """Ejecuta el mismo lote que el job programado (admin). Envío real: solo fecha de hoy Caracas."""
    hoy = hoy_negocio()
    try:
        d = parse_fecha_referencia_negocio(body.fecha_caracas) if body.fecha_caracas else hoy
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if d is None:
        d = hoy
    if not body.solo_simular and d != hoy:
        raise HTTPException(
            status_code=422,
            detail=(
                "El envío real de Recibos solo permite la fecha de hoy (America/Caracas), "
                "la misma que usa el job programado para fecha_registro de recepción. "
                "Use «Solo simular» para revisar otras fechas, u omita fecha_caracas al ejecutar hoy."
            ),
        )
    return ejecutar_recibos_envio_slot(
        db,
        fecha_dia=d,
        slot=body.slot,
        solo_simular=body.solo_simular,
    )
