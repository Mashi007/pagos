"""
Endpoints de administración del módulo Cobros (requieren autenticación).
Listado de pagos reportados, detalle, aprobar, rechazar, histórico por cédula.
"""
import logging
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, case

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.cedula_reportar_bs import CedulaReportarBs
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado, WHATSAPP_LINK, WHATSAPP_DISPLAY
from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio
from app.api.v1.endpoints.validadores import validate_cedula
from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno

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
    correo_enviado_a: Optional[str] = None  # Para icono estado envío recibo en Acciones
    tiene_recibo_pdf: bool = False

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


def _observacion_reglas_carga(
    db: Session,
    rows: list,
    cedulas_en_clientes: set,
    cedulas_bolivares: set,
    numeros_doc_en_pagos: set,
) -> list:
    """Para cada fila de pagos_reportados, devuelve lista de observaciones por reglas: NO CLIENTES, Monto (Bs no autorizado), DUPLICADO DOC."""
    result = []
    for r in rows:
        partes = []
        cedula_norm = ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        if cedula_norm and cedula_norm not in cedulas_en_clientes:
            partes.append("NO CLIENTES")
        moneda = (r.moneda or "BS").strip().upper()
        if moneda == "BS" and cedula_norm and cedula_norm not in cedulas_bolivares:
            partes.append("Monto: solo Bs si está en lista Bolívares")
        num_op = (r.numero_operacion or "").strip()
        if num_op and num_op in numeros_doc_en_pagos:
            partes.append("DUPLICADO DOC")
        result.append(partes)
    return result


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
    """Lista paginada de pagos reportados con filtros. Por defecto excluye aprobados para mostrar solo casos pendientes."""
    q = select(PagoReportado)
    count_q = select(func.count(PagoReportado.id))
    if estado:
        q = q.where(PagoReportado.estado == estado)
        count_q = count_q.where(PagoReportado.estado == estado)
    else:
        # Por defecto ocultar aprobados: solo casos pendientes (revisi�n, pendiente, rechazado)
        q = q.where(PagoReportado.estado != "aprobado")
        count_q = count_q.where(PagoReportado.estado != "aprobado")
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
    # Rechazados al final de la lista; luego por fecha (más viejo primero)
    q = q.order_by(
        case((PagoReportado.estado == "rechazado", 1), else_=0),
        PagoReportado.created_at.asc(),
    ).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).scalars().all()

    # Conjuntos para reglas de observación al cargar (cédula en clientes, lista Bs, duplicado en pagos)
    cedula_norms = [
        ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        for r in rows
    ]
    unique_cedulas = set(c for c in cedula_norms if c)
    cedulas_en_clientes = set()
    if unique_cedulas:
        cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
        existing = db.execute(
            select(cedula_lookup).select_from(Cliente).where(cedula_lookup.in_(unique_cedulas))
        ).scalars().all()
        cedulas_en_clientes = {row[0] for row in existing if row[0]}

    cedulas_bolivares = set()
    list_bs = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
    cedulas_bolivares = {
        (row[0] or "").strip().upper().replace("-", "").replace(" ", "")
        for row in list_bs if row[0]
    }

    num_ops = list({(r.numero_operacion or "").strip() for r in rows if (r.numero_operacion or "").strip()})
    numeros_doc_en_pagos = set()
    if num_ops:
        existing_docs = db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(num_ops))
        ).scalars().all()
        numeros_doc_en_pagos = {row[0] for row in existing_docs if row[0]}

    partes_por_fila = _observacion_reglas_carga(
        db, rows, cedulas_en_clientes, cedulas_bolivares, numeros_doc_en_pagos
    )

    items = []
    for i, r in enumerate(rows):
        obs_gemini = _observacion_solo_columnas(r.gemini_comentario)
        partes_reglas = partes_por_fila[i] if i < len(partes_por_fila) else []
        observacion = " / ".join(filter(None, [obs_gemini] + partes_reglas)) if (obs_gemini or partes_reglas) else None
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
            observacion=observacion,
            correo_enviado_a=r.correo_enviado_a,
            tiene_recibo_pdf=bool(r.recibo_pdf),
        ))
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/pagos-reportados/kpis", response_model=dict)
def kpis_pagos_reportados(
    db: Session = Depends(get_db),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
):
    """Conteos por estado (pendiente, en_revision, aprobado, rechazado) con los mismos filtros opcionales que el listado."""
    base = select(PagoReportado.estado, func.count(PagoReportado.id).label("cnt")).where(True)
    if fecha_desde:
        base = base.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
    if fecha_hasta:
        base = base.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
    if cedula:
        ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
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
        base = base.where(cond_cedula)
    if institucion:
        base = base.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))
    base = base.group_by(PagoReportado.estado)
    rows = db.execute(base).all()
    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0}
    for row in rows:
        if row.estado in counts:
            counts[row.estado] = row.cnt
    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado"))
    return counts


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


def _email_cliente_pago_reportado(db: Session, pr: PagoReportado) -> str:
    """Email del cliente para enviar recibo: pr.correo_enviado_a o, si falta, busqueda por cedula en clientes."""
    to = (pr.correo_enviado_a or "").strip()
    if to and "@" in to:
        return to
    cedula_norm = (f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}").replace("-", "").strip()
    if not cedula_norm:
        return ""
    cliente = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_norm)
    ).scalars().first()
    if cliente and (cliente.email or "").strip():
        return (cliente.email or "").strip()
    return ""


def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):
    h = PagoReportadoHistorial(
        pago_reportado_id=pago_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_email=usuario_email,
        motivo=motivo,
    )
    db.add(h)



def _crear_pago_desde_reportado_y_aplicar_cuotas(db: Session, pr: PagoReportado, usuario_email: Optional[str]) -> None:
    """Tras aprobar un pago reportado: crea registro en tabla pagos y aplica a cuotas (FIFO) para que prestamos y estado de cuenta se actualicen. Debe llamarse ANTES de commit; si falla lanza HTTPException."""
    _rechazar_si_numero_operacion_duplicado(db, pr.numero_operacion)
    cedula_norm = ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
    if not cedula_norm:
        raise HTTPException(status_code=400, detail="Cédula del reporte vacía; no se puede crear el pago en préstamos.")
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(
        select(Cliente).where(cedula_lookup == cedula_norm)
    ).scalars().first()
    if not cliente:
        raise HTTPException(
            status_code=400,
            detail="No se encontró cliente con la cédula indicada. Verifique la cédula o registre al cliente para que el estado de cuenta se actualice.",
        )
    prestamo = db.execute(
        select(Prestamo)
        .where(Prestamo.cliente_id == cliente.id, func.upper(Prestamo.estado) == "APROBADO")
        .order_by(Prestamo.id.desc())
        .limit(1)
    ).scalars().first()
    if not prestamo:
        raise HTTPException(
            status_code=400,
            detail="El cliente no tiene un préstamo APROBADO activo. No se puede actualizar estado de cuenta.",
        )
    num_doc = ("COB-" + pr.referencia_interna)[:100]
    if db.execute(select(Pago.id).where(Pago.numero_documento == num_doc)).scalar() is not None:
        logger.info("[COBROS] Aprobar ref=%s: ya existe pago con documento %s; omitir creacion (idempotente).", pr.referencia_interna, num_doc)
        return
    fecha_ts = datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now()
    monto = Decimal(str(round(float(pr.monto), 2)))
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto del reporte debe ser mayor que cero.")
    row = Pago(
        cedula_cliente=cedula_norm,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_ts,
        monto_pagado=monto,
        numero_documento=num_doc,
        institucion_bancaria=(pr.institucion_financiera or "").strip()[:255] or None,
        estado="PENDIENTE",
        referencia_pago=num_doc,
        usuario_registro=usuario_email or "cobros@rapicredit.com",
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    _aplicar_pago_a_cuotas_interno(row, db)
    row.estado = "PAGADO"
    logger.info("[COBROS] Aprobar ref=%s: creado pago id=%s y aplicado a cuotas del prestamo %s.", pr.referencia_interna, row.id, prestamo.id)


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
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    if pr.estado == "aprobado":
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            db.commit()
        except HTTPException:
            pass
        return {"ok": True, "mensaje": "Ya estaba aprobado."}
    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    estado_anterior = pr.estado
    pr.estado = "aprobado"
    pr.motivo_rechazo = None
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    try:
        pdf_bytes = generar_recibo_pago_reportado(
            referencia_interna=pr.referencia_interna,
            nombres=pr.nombres,
            apellidos=pr.apellidos,
            tipo_cedula=pr.tipo_cedula,
            numero_cedula=pr.numero_cedula,
            institucion_financiera=pr.institucion_financiera,
            monto=f"{pr.monto} {pr.moneda}",
            numero_operacion=pr.numero_operacion,
            fecha_pago=pr.fecha_pago,
        )
    except Exception as e:
        logger.exception("[COBROS] Aprobar ref=%s: error generando recibo PDF: %s", pr.referencia_interna, e)
        raise HTTPException(status_code=500, detail=f"Error al generar el recibo PDF: {e!s}")
    pr.recibo_pdf = pdf_bytes
    to_email = _email_cliente_pago_reportado(db, pr)
    if not pr.correo_enviado_a and to_email:
        pr.correo_enviado_a = to_email
    mensaje_final = "Pago aprobado y recibo enviado por correo."
    if to_email:
        body = f"Su reporte de pago ha sido aprobado. Número de referencia: {pr.referencia_interna}. Adjunto encontrará el recibo.\n\nRapiCredit C.A."
        ok_mail, err_mail = send_email([to_email], f"Recibo de reporte de pago #{pr.referencia_interna}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", pdf_bytes)], servicio="cobros", respetar_destinos_manuales=True)
        if not ok_mail:
            logger.error(
                "[COBROS] Aprobar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
            mensaje_final = "Pago aprobado. El recibo no pudo enviarse por correo; use 'Enviar recibo por correo' desde el detalle."
    _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)
    try:
        _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("[COBROS] Aprobar ref=%s: error al crear pago o aplicar a cuotas: %s", pr.referencia_interna, e)
        raise HTTPException(status_code=500, detail=f"Error al aprobar: {e!s}")
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

    to_email = _email_cliente_pago_reportado(db, pr)
    if to_email and get_email_activo_servicio("notificaciones"):
        body_text = (
            f"Referencia: {pr.referencia_interna}\n\n"
            f"Su reporte de pago no ha sido aprobado.\n\n"
            f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
            f"Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
            "RapiCredit C.A."
        )
        attachments: List[Tuple[str, bytes]] = []
        if pr.comprobante:
            nombre_adj = (pr.comprobante_nombre or "comprobante").strip() or "comprobante"
            if not nombre_adj or "." not in nombre_adj:
                ext = "pdf" if (pr.comprobante_tipo or "").lower().find("pdf") >= 0 else "jpg"
                nombre_adj = f"comprobante_{pr.referencia_interna}.{ext}"
            attachments.append((nombre_adj, bytes(pr.comprobante)))
        ok_mail, err_mail = send_email(
            [to_email],
            f"Reporte de pago no aprobado #{pr.referencia_interna}",
            body_text,
            attachments=attachments if attachments else None,
            servicio="notificaciones",
            respetar_destinos_manuales=True,
        )
        if not ok_mail:
            logger.error(
                "[COBROS] Rechazar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
    elif to_email and not get_email_activo_servicio("notificaciones"):
        logger.warning("[COBROS] Rechazar ref=%s: email notificaciones desactivado, no se envió correo a %s.", pr.referencia_interna, to_email)
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
    to_email = _email_cliente_pago_reportado(db, pr)
    if not to_email:
        raise HTTPException(status_code=400, detail="No hay correo del cliente para este pago. Registre el correo en el detalle del pago o en la ficha del cliente.")
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
            fecha_pago=pr.fecha_pago,
        )
        pr.recibo_pdf = pdf_bytes
        db.commit()
    body = (
        f"Recibo de reporte de pago. Número de referencia: {pr.referencia_interna}.\n\n"
        "Adjunto encontrará el recibo.\n\nRapiCredit C.A."
    )
    send_email([to_email], f"Recibo de reporte de pago #{pr.referencia_interna}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", bytes(pdf_bytes))], servicio="cobros", respetar_destinos_manuales=True)
    return {"ok": True, "mensaje": "Recibo enviado por correo."}


class CambiarEstadoBody(BaseModel):
    estado: str  # pendiente | en_revision | aprobado | rechazado
    motivo: Optional[str] = None


class EditarPagoReportadoBody(BaseModel):
    """Campos editables para que el pago cumpla con los validadores (cédula, fecha, monto, etc.)."""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    tipo_cedula: Optional[str] = None
    numero_cedula: Optional[str] = None
    fecha_pago: Optional[date] = None
    institucion_financiera: Optional[str] = None
    numero_operacion: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    observacion: Optional[str] = None


def _rechazar_si_numero_operacion_duplicado(db: Session, numero_operacion: str) -> None:
    """Si el número de operación ya existe en tabla pagos (numero_documento), lanza HTTPException 400. Nunca se permite guardar duplicado."""
    num_op = (numero_operacion or "").strip()
    if not num_op:
        return
    existe = db.execute(select(Pago.id).where(Pago.numero_documento == num_op)).scalar() is not None
    if existe:
        raise HTTPException(
            status_code=400,
            detail="Número de operación duplicado. No se permite guardar. Ya existe un pago con ese documento.",
        )


def _normalizar_cedula_editar(tipo: Optional[str], numero: Optional[str]) -> Tuple[str, str]:
    """Devuelve (tipo, numero) normalizados; si solo viene numero con 6-11 dígitos, antepone V."""
    if tipo is None and numero is None:
        return "", ""
    t = (tipo or "").strip().upper()
    n = (numero or "").strip().replace(" ", "").replace("-", "").replace(".", "")
    if not n:
        return t[:1] if t else "", ""
    if t and t in ("V", "E", "J", "G") and n.isdigit() and 6 <= len(n) <= 11:
        return t, n
    if not t and n.isdigit() and 6 <= len(n) <= 11:
        return "V", n
    # Intentar validar como cédula completa
    cedula_input = f"{t}{n}" if t else n
    val = validate_cedula(cedula_input)
    if val.get("valido"):
        formateado = val.get("valor_formateado", "") or cedula_input
        if "-" in formateado:
            a, b = formateado.split("-", 1)
            return a.strip(), b.strip()
        return (formateado[0] if formateado else "V", formateado[1:] if len(formateado) > 1 else n)
    return t[:1] if t else "V", n


@router.patch("/pagos-reportados/{pago_id}")
def editar_pago_reportado(
    pago_id: int,
    body: EditarPagoReportadoBody,
    db: Session = Depends(get_db),
):
    """Edita los datos del pago reportado para que cumplan con los validadores (cédula, fecha, monto, etc.). Solo actualiza los campos enviados."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado == "aprobado":
        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado.")
    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede editar un pago rechazado.")

    if body.nombres is not None:
        pr.nombres = (body.nombres or "").strip()[:200] or pr.nombres
    if body.apellidos is not None:
        pr.apellidos = (body.apellidos or "").strip()[:200] or pr.apellidos
    if body.tipo_cedula is not None or body.numero_cedula is not None:
        t_env = body.tipo_cedula if body.tipo_cedula is not None else pr.tipo_cedula
        n_env = body.numero_cedula if body.numero_cedula is not None else pr.numero_cedula
        tipo, numero = _normalizar_cedula_editar(t_env, n_env)
        if tipo and numero:
            val = validate_cedula(f"{tipo}{numero}")
            if not val.get("valido"):
                raise HTTPException(status_code=400, detail=val.get("error", "Cédula inválida."))
            pr.tipo_cedula = tipo
            pr.numero_cedula = numero[:13]
    if body.fecha_pago is not None:
        pr.fecha_pago = body.fecha_pago
    if body.institucion_financiera is not None:
        pr.institucion_financiera = (body.institucion_financiera or "").strip()[:100] or pr.institucion_financiera
    if body.numero_operacion is not None:
        pr.numero_operacion = (body.numero_operacion or "").strip()[:100] or pr.numero_operacion
    if body.monto is not None:
        if body.monto < 0:
            raise HTTPException(status_code=400, detail="El monto no puede ser negativo.")
        pr.monto = body.monto
    if body.moneda is not None:
        m = (body.moneda or "BS").strip().upper()[:10]
        # USDT = Dólares = USD = $; normalizar a USD
        if m in ("USD", "USDT"):
            m = "USD"
        pr.moneda = m or pr.moneda
    if body.correo_enviado_a is not None:
        pr.correo_enviado_a = (body.correo_enviado_a or "").strip()[:255] or None
    if body.observacion is not None:
        pr.observacion = (body.observacion or "").strip()[:500] or None

    # Número de operación: nunca permitir duplicado en tabla pagos
    _rechazar_si_numero_operacion_duplicado(db, pr.numero_operacion)

    # Si la moneda queda en BS, la cédula debe estar en la lista de autorizadas para Bolívares
    moneda_final = (pr.moneda or "").strip().upper()
    if moneda_final == "BS":
        cedula_lookup = ((pr.tipo_cedula or "").strip().upper() + (pr.numero_cedula or "").strip().replace(" ", "").replace("-", "")).strip()
        if cedula_lookup:
            permitido_bs = db.execute(
                select(CedulaReportarBs).where(CedulaReportarBs.cedula == cedula_lookup).limit(1)
            ).scalars().first() is not None
            if not permitido_bs:
                raise HTTPException(
                    status_code=400,
                    detail="Observación: Bolívares. No puede guardar con moneda Bs; la cédula no está en la lista autorizada. Cambie a USD.",
                )

    db.commit()
    logger.info("[COBROS] Pago reportado editado: id=%s ref=%s", pago_id, pr.referencia_interna)
    return {"ok": True, "mensaje": "Datos actualizados. Los cambios cumplen con los validadores."}


@router.patch("/pagos-reportados/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    body: CambiarEstadoBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia el estado del pago reportado (pendiente, en_revision, aprobado, rechazado). Si pasa a aprobado, genera recibo PDF y envía por correo al email del cliente (cédula)."""
    if body.estado not in ("pendiente", "en_revision", "aprobado", "rechazado"):
        raise HTTPException(status_code=400, detail="Estado no válido.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if body.estado == "rechazado" and not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo es obligatorio al rechazar.")
    if body.estado == "aprobado" and pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    estado_anterior = pr.estado
    pr.estado = body.estado
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000] if body.estado == "rechazado" else None
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)

    mensaje = f"Estado actualizado a {body.estado}."
    if body.estado == "aprobado":
        pdf_bytes = generar_recibo_pago_reportado(
            referencia_interna=pr.referencia_interna,
            nombres=pr.nombres,
            apellidos=pr.apellidos,
            tipo_cedula=pr.tipo_cedula,
            numero_cedula=pr.numero_cedula,
            institucion_financiera=pr.institucion_financiera,
            monto=f"{pr.monto} {pr.moneda}",
            numero_operacion=pr.numero_operacion,
            fecha_pago=pr.fecha_pago,
        )
        pr.recibo_pdf = pdf_bytes
        to_email = _email_cliente_pago_reportado(db, pr)
        if not pr.correo_enviado_a and to_email:
            pr.correo_enviado_a = to_email
        if to_email:
            body_mail = f"Su reporte de pago ha sido aprobado. Número de referencia: {pr.referencia_interna}. Adjunto encontrará el recibo.\n\nRapiCredit C.A."
            ok_mail, err_mail = send_email(
                [to_email],
                f"Recibo de reporte de pago #{pr.referencia_interna}",
                body_mail,
                attachments=[(f"recibo_{pr.referencia_interna}.pdf", pdf_bytes)],
                servicio="cobros",
                respetar_destinos_manuales=True,
            )
            if ok_mail:
                mensaje = "Estado actualizado a aprobado. Recibo enviado por correo."
            else:
                logger.error(
                    "[COBROS] Cambiar a aprobado ref=%s: correo NO enviado a %s. Error: %s.",
                    pr.referencia_interna, to_email, err_mail or "desconocido",
                )
                mensaje = "Estado actualizado a aprobado. El recibo no pudo enviarse por correo."
        else:
            mensaje = "Estado actualizado a aprobado. No hay correo registrado para este pago (no se envió recibo)."
        # Crear pago en tabla pagos y aplicar a cuotas (igual que POST /aprobar) para que estado de cuenta y préstamos se actualicen
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
        except HTTPException:
            raise

    _registrar_historial(db, pago_id, estado_anterior, body.estado, usuario_email, body.motivo)
    db.commit()
    return {"ok": True, "mensaje": mensaje}

