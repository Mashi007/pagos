"""API admin: Recibos (vista previa de pagos en ventana y ejecución manual)."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.email import preparar_body_html_para_mime
from app.services.cuota_estado import hoy_negocio, parse_fecha_referencia_negocio
from app.services.recibos_conciliacion_email_job import (
    RECIBOS_VENTANA_SLOT,
    _cuerpo_html_recibos_confirmacion,
    ejecutar_recibos_envio_slot,
    persistir_plantilla_recibos_html_en_bd,
    ruta_archivo_plantilla_recibos_confirmacion,
)
from app.services.recibos_conciliacion_listado_ui import listar_recibos_ventana_con_ui

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])

_MAX_PLANTILLA_CHARS = 1_800_000


class RecibosPlantillaHtmlBody(BaseModel):
    """Cuerpo HTML de la plantilla Recibos (crudo: puede incluir {{LOGO_URL}}; el envío lo sanea como send_email)."""

    html: str = Field(..., max_length=_MAX_PLANTILLA_CHARS)


@router.get("/plantilla-correo-html", response_class=HTMLResponse)
def get_recibos_plantilla_correo_html(db: Session = Depends(get_db)):
    """
    Contenido **crudo** de la plantilla Recibos (sin pasar por el pipeline de ``send_email``): primero
    la copia guardada en ``configuracion`` (admin «Guardar plantilla»); si no hay, el archivo en disco.
    Sirve para cargar el editor; la vista previa idéntica al SMTP se obtiene con ``POST /plantilla-html-preview``.
    """
    raw = _cuerpo_html_recibos_confirmacion(db)
    return HTMLResponse(content=raw, media_type="text/html; charset=utf-8")


@router.post("/plantilla-html-preview")
def post_recibos_plantilla_html_preview(payload: RecibosPlantillaHtmlBody) -> dict[str, Any]:
    """
    Devuelve el HTML tal como lo prepara ``send_email`` (UTF-8 + ``preparar_body_html_para_mime``) a partir
    del texto pegado en el admin. Debe coincidir con la parte ``text/html`` del mensaje si ese mismo
    cuerpo se envía como prueba con ``recibos_html_plantilla``.
    """
    out = preparar_body_html_para_mime(payload.html)
    return {"html": out or ""}


@router.get("/plantilla-html-envio-preview")
def get_recibos_plantilla_html_envio_preview(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    HTML de la parte ``text/html`` que usarán los envíos reales (manual / lote): misma fuente que
    ``_cuerpo_html_recibos_confirmacion`` (BD o archivo) + ``preparar_body_html_para_mime`` (igual que
    ``send_email``). Una sola lectura en servidor; alinea la UI con lo persistido sin depender del editor.
    """
    raw = _cuerpo_html_recibos_confirmacion(db)
    out = preparar_body_html_para_mime(raw)
    return {"html": out or ""}


@router.put("/plantilla-correo-html")
def put_recibos_plantilla_correo_html(
    payload: RecibosPlantillaHtmlBody, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Persiste la plantilla en BD (todas las réplicas) y, si se puede, en disco local del worker."""
    html = payload.html
    low = html.lower()
    if "<html" not in low and "<!doctype" not in low:
        raise HTTPException(
            status_code=422,
            detail="El contenido no parece un documento HTML (falta <!DOCTYPE o <html>).",
        )
    persistir_plantilla_recibos_html_en_bd(db, html)
    db.commit()
    path = ruta_archivo_plantilla_recibos_confirmacion()
    try:
        path.write_text(html, encoding="utf-8")
    except OSError as e:
        logger.warning(
            "recibos plantilla: guardada en BD; no se pudo escribir archivo local %s: %s",
            path,
            e,
        )
    return {
        "ok": True,
        "ruta": str(path),
        "bytes_utf8": len(html.encode("utf-8")),
        "persistido_bd": True,
    }


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
