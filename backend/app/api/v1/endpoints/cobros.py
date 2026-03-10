"""
Endpoints de administración del módulo Cobros (requieren autenticación).
Listado de pagos reportados, detalle, aprobar, rechazar, histórico por cédula.
"""
import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.cliente import Cliente
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado, WHATSAPP_LINK, WHATSAPP_DISPLAY
from app.core.email import send_email

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# Mensaje genérico al rechazar: indicar que se comuniquen por WhatsApp (424-4579934)
MENSAJE_RECHAZO_GENERICO = (
    "Su reporte de pago no ha sido aprobado. "
    "Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {whatsapp} ({link}).\n\n"
    "RapiCredit C.A."
).format(whatsapp=WHATSAPP_DISPLAY, link=WHATSAPP_LINK)


class PagoReportadoListItem(BaseModel):
    id: int
    referencia_interna: str
    nombres: str
    apellidos: str
    cedula_display: str
    institucion_financiera: str
    monto: float
    moneda: str
    fecha_pago: date
    numero_operacion: str
    fecha_reporte: datetime
    estado: str
    gemini_coincide_exacto: Optional[str] = None
    observacion: Optional[str] = None  # Divergencias Gemini (gemini_comentario) para facilidad de revisión

    class Config:
        from_attributes = True


class PagoReportadoDetalle(BaseModel):
    id: int
    referencia_interna: str
    nombres: str
    apellidos: str
    tipo_cedula: str
    numero_cedula: str
    fecha_pago: date
    institucion_financiera: str
    numero_operacion: str
    monto: float
    moneda: str
    ruta_comprobante: Optional[str] = None
    tiene_comprobante: bool = False
    tiene_recibo_pdf: bool = False
    observacion: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    estado: str
    motivo_rechazo: Optional[str] = None
    gemini_coincide_exacto: Optional[str] = None
    gemini_comentario: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    historial: List[dict]

    class Config:
        from_attributes = True


class AprobarRechazarBody(BaseModel):
    motivo: Optional[str] = None  # Obligatorio si rechaza


# Nombres de columnas para Observación (solo mostrar estos en el listado)
OBSERVACION_COLUMNAS = ["Cédula", "Banco", "Fecha pago", "Nº operación", "Monto", "Moneda"]


def _observacion_solo_columnas(raw: Optional[str]) -> Optional[str]:
    """Devuelve la observación mostrando solo nombres de columnas. Si raw ya es una lista corta de columnas, la devuelve; si es texto largo, extrae columnas por palabras clave."""
    if not raw or not (raw := raw.strip()):
        return None
    # Si ya parece lista de columnas (corta, sin frases largas)
    if len(raw) <= 80 and not any(x in raw for x in ("en la imagen", "en el formulario", "mientras que", "incluye el", "no coincide")):
        return raw
    # Extraer columnas por palabras clave (registros antiguos con texto largo)
    lower = raw.lower()
    columnas = []
    if "cédula" in lower or "cedula" in lower:
        columnas.append("Cédula")
    if "banco" in lower or "institución" in lower or "institucion" in lower or "financiera" in lower:
        columnas.append("Banco")
    if "fecha" in lower and ("pago" in lower or "operación" not in lower):
        columnas.append("Fecha pago")
    if "operación" in lower or "operacion" in lower or "referencia" in lower or "serial" in lower:
        columnas.append("Nº operación")
    if "monto" in lower or "cantidad" in lower:
        columnas.append("Monto")
    if "moneda" in lower:
        columnas.append("Moneda")
    return ", ".join(columnas) if columnas else raw[:100]


@router.get("/pagos-reportados", response_model=dict)
def list_pagos_reportados(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Lista paginada de pagos reportados con filtros."""
    q = select(PagoReportado)
    count_q = select(func.count(PagoReportado.id))
    if estado:
        q = q.where(PagoReportado.estado == estado)
        count_q = count_q.where(PagoReportado.estado == estado)
    if fecha_desde:
        q = q.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
        count_q = count_q.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
    if fecha_hasta:
        q = q.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
        count_q = count_q.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
    # Búsqueda por cédula: todas las formas posibles (tipo+numero, solo numero, con/sin guión)
    if cedula:
        ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
        # Coincide: concatenación tipo+numero, o solo numero_cedula, o tipo
        cond_cedula = or_(
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula).like(f"%{ced_clean}%"),
            PagoReportado.numero_cedula.like(f"%{ced_clean}%"),
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula) == ced_clean,
            PagoReportado.numero_cedula == ced_clean,
        )
        if len(ced_clean) >= 1 and ced_clean[0:1] in ("V", "E", "J") and ced_clean[1:].isdigit():
            cond_cedula = or_(
                cond_cedula,
                and_(PagoReportado.tipo_cedula == ced_clean[0:1], PagoReportado.numero_cedula == ced_clean[1:]),
            )
        q = q.where(cond_cedula)
        count_q = count_q.where(cond_cedula)
    if institucion:
        q = q.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))
        count_q = count_q.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))

    total = db.execute(count_q).scalar()
    q = q.order_by(PagoReportado.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).scalars().all()

    items = []
    for r in rows:
        items.append(PagoReportadoListItem(
            id=r.id,
            referencia_interna=r.referencia_interna,
            nombres=r.nombres,
            apellidos=r.apellidos,
            cedula_display=f"{r.tipo_cedula}{r.numero_cedula}",
            institucion_financiera=r.institucion_financiera,
            monto=float(r.monto),
            moneda=r.moneda or "BS",
            fecha_pago=r.fecha_pago,
            numero_operacion=r.numero_operacion,
            fecha_reporte=r.created_at,
            estado=r.estado,
            gemini_coincide_exacto=r.gemini_coincide_exacto,
            observacion=_observacion_solo_columnas(r.gemini_comentario),
        ))
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/pagos-reportados/{pago_id}", response_model=PagoReportadoDetalle)
def get_pago_reportado_detalle(pago_id: int, db: Session = Depends(get_db)):
    """Detalle de un pago reportado + historial de cambios de estado."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    hist = db.execute(
        select(PagoReportadoHistorial)
        .where(PagoReportadoHistorial.pago_reportado_id == pago_id)
        .order_by(PagoReportadoHistorial.created_at.asc())
    ).scalars().all()
    historial = [
        {
            "estado_anterior": h.estado_anterior,
            "estado_nuevo": h.estado_nuevo,
            "usuario_email": h.usuario_email,
            "motivo": h.motivo,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in hist
    ]
    return PagoReportadoDetalle(
        id=pr.id,
        referencia_interna=pr.referencia_interna,
        nombres=pr.nombres,
        apellidos=pr.apellidos,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
        fecha_pago=pr.fecha_pago,
        institucion_financiera=pr.institucion_financiera,
        numero_operacion=pr.numero_operacion,
        monto=float(pr.monto),
        moneda=pr.moneda or "BS",
        ruta_comprobante=pr.ruta_comprobante,
        tiene_comprobante=bool(pr.comprobante),
        tiene_recibo_pdf=bool(pr.recibo_pdf),
        observacion=pr.observacion,
        correo_enviado_a=pr.correo_enviado_a,
        estado=pr.estado,
        motivo_rechazo=pr.motivo_rechazo,
        gemini_coincide_exacto=pr.gemini_coincide_exacto,
        gemini_comentario=pr.gemini_comentario,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        historial=historial,
    )


def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):
    h = PagoReportadoHistorial(
        pago_reportado_id=pago_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_email=usuario_email,
        motivo=motivo,
    )
    db.add(h)


@router.post("/pagos-reportados/{pago_id}/aprobar")
def aprobar_pago_reportado(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Aprueba el pago reportado: genera recibo PDF, envía por correo, guarda en recibos/."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado == "aprobado":
        return {"ok": True, "mensaje": "Ya estaba aprobado."}
    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    estado_anterior = pr.estado
    pr.estado = "aprobado"
    pr.motivo_rechazo = None
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    pdf_bytes = generar_recibo_pago_reportado(
        referencia_interna=pr.referencia_interna,
        nombres=pr.nombres,
        apellidos=pr.apellidos,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
        institucion_financiera=pr.institucion_financiera,
        monto=f"{pr.monto} {pr.moneda}",
        numero_operacion=pr.numero_operacion,
    )
    pr.recibo_pdf = pdf_bytes
    to_email = (pr.correo_enviado_a or "").strip()
    mensaje_final = "Pago aprobado y recibo enviado por correo."
    if to_email:
        body = f"Su reporte de pago ha sido aprobado. Número de referencia: {pr.referencia_interna}. Adjunto encontrará el recibo.\n\nRapiCredit C.A."
        ok_mail, err_mail = send_email([to_email], f"Recibo de reporte de pago #{pr.referencia_interna}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", pdf_bytes)])
        if not ok_mail:
            logger.error(
                "[COBROS] Aprobar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
            mensaje_final = "Pago aprobado. El recibo no pudo enviarse por correo; use 'Enviar recibo por correo' desde el detalle."
    _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)
    db.commit()
    return {"ok": True, "mensaje": mensaje_final}


@router.post("/pagos-reportados/{pago_id}/rechazar")
def rechazar_pago_reportado(
  pago_id: int,
  body: AprobarRechazarBody,
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_user),
):
    """Rechaza el pago reportado. Motivo obligatorio. Envía correo al cliente informando que no fue aprobado."""
    if not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo de rechazo es obligatorio.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado == "rechazado":
        return {"ok": True, "mensaje": "Ya estaba rechazado."}
    estado_anterior = pr.estado
    pr.estado = "rechazado"
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000]
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    to_email = (pr.correo_enviado_a or "").strip()
    if to_email:
        body_text = (
            f"Referencia: {pr.referencia_interna}\n\n"
            f"{MENSAJE_RECHAZO_GENERICO}"
        )
        ok_mail, err_mail = send_email([to_email], f"Reporte de pago no aprobado #{pr.referencia_interna}", body_text)
        if not ok_mail:
            logger.error(
                "[COBROS] Rechazar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
    _registrar_historial(db, pago_id, estado_anterior, "rechazado", usuario_email, pr.motivo_rechazo)
    db.commit()
    return {"ok": True, "mensaje": "Pago rechazado y cliente notificado."}


@router.delete("/pagos-reportados/{pago_id}")
def eliminar_pago_reportado(
    pago_id: int,
    db: Session = Depends(get_db),
):
    """Elimina un pago reportado y su historial (CASCADE). Acción irreversible."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    ref = pr.referencia_interna
    db.delete(pr)
    db.commit()
    logger.info("[COBROS] Pago reportado eliminado: id=%s ref=%s", pago_id, ref)
    return {"ok": True, "mensaje": f"Pago reportado {ref} eliminado."}


@router.get("/historico-cliente", response_model=dict)
def historico_por_cliente(
    cedula: str = Query(..., min_length=6),
    db: Session = Depends(get_db),
):
    """Lista todos los pagos reportados por un cliente (por cédula). Incluye acceso a recibos PDF."""
    ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
    if len(ced_clean) < 6:
        raise HTTPException(status_code=400, detail="Cédula inválida.")
    if ced_clean[0:1] in ("V", "E", "J") and ced_clean[1:].isdigit():
        tipo, num = ced_clean[0:1], ced_clean[1:]
        q = select(PagoReportado).where(
            PagoReportado.tipo_cedula == tipo,
            PagoReportado.numero_cedula == num,
        )
    else:
        q = select(PagoReportado).where(PagoReportado.numero_cedula == ced_clean)
    rows = db.execute(q.order_by(PagoReportado.created_at.desc())).scalars().all()
    items = [
        {
            "id": r.id,
            "referencia_interna": r.referencia_interna,
            "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else None,
            "fecha_reporte": r.created_at.isoformat() if r.created_at else None,
            "monto": float(r.monto),
            "moneda": r.moneda,
            "estado": r.estado,
            "tiene_recibo": bool(r.recibo_pdf),
        }
        for r in rows
    ]
    return {"cedula": cedula, "items": items}


@router.get("/pagos-reportados/{pago_id}/comprobante")
def get_comprobante(pago_id: int, db: Session = Depends(get_db)):
    """Devuelve el archivo comprobante (imagen o PDF) desde BD."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if not pr.comprobante:
        raise HTTPException(status_code=404, detail="No hay comprobante almacenado.")
    media = (pr.comprobante_tipo or "application/octet-stream").split(";")[0].strip()
    nombre = pr.comprobante_nombre or "comprobante"
    return Response(content=bytes(pr.comprobante), media_type=media, headers={"Content-Disposition": f'inline; filename="{nombre}"'})


@router.get("/pagos-reportados/{pago_id}/recibo.pdf")
def get_recibo_pdf(pago_id: int, db: Session = Depends(get_db)):
    """Devuelve el PDF del recibo desde BD."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if not pr.recibo_pdf:
        raise HTTPException(status_code=404, detail="No hay recibo PDF generado para este pago.")
    return Response(
        content=bytes(pr.recibo_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pr.referencia_interna}.pdf"'},
    )


@router.post("/pagos-reportados/{pago_id}/enviar-recibo")
def enviar_recibo_manual(
    pago_id: int,
    db: Session = Depends(get_db),
):
    """Envía por correo el recibo PDF del pago (manual). Genera el PDF si no existe y lo guarda en BD."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    to_email = (pr.correo_enviado_a or "").strip()
    if not to_email:
        raise HTTPException(status_code=400, detail="No hay correo registrado para este pago.")
    pdf_bytes = pr.recibo_pdf
    if not pdf_bytes:
        pdf_bytes = generar_recibo_pago_reportado(
            referencia_interna=pr.referencia_interna,
            nombres=pr.nombres,
            apellidos=pr.apellidos,
            tipo_cedula=pr.tipo_cedula,
            numero_cedula=pr.numero_cedula,
            institucion_financiera=pr.institucion_financiera,
            monto=f"{pr.monto} {pr.moneda}",
            numero_operacion=pr.numero_operacion,
        )
        pr.recibo_pdf = pdf_bytes
        db.commit()
    body = (
        f"Recibo de reporte de pago. Número de referencia: {pr.referencia_interna}.\n\n"
        "Adjunto encontrará el recibo.\n\nRapiCredit C.A."
    )
    send_email([to_email], f"Recibo de reporte de pago #{pr.referencia_interna}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", bytes(pdf_bytes))])
    return {"ok": True, "mensaje": "Recibo enviado por correo."}


class CambiarEstadoBody(BaseModel):
    estado: str  # pendiente | en_revision | aprobado | rechazado
    motivo: Optional[str] = None


@router.patch("/pagos-reportados/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    body: CambiarEstadoBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia el estado del pago reportado (pendiente, en_revision, aprobado, rechazado)."""
    if body.estado not in ("pendiente", "en_revision", "aprobado", "rechazado"):
        raise HTTPException(status_code=400, detail="Estado no válido.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if body.estado == "rechazado" and not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo es obligatorio al rechazar.")
    estado_anterior = pr.estado
    pr.estado = body.estado
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000] if body.estado == "rechazado" else None
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    _registrar_historial(db, pago_id, estado_anterior, body.estado, usuario_email, body.motivo)
    db.commit()
    return {"ok": True, "mensaje": f"Estado actualizado a {body.estado}."}
