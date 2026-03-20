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
from app.core.documento import normalize_documento
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


def _monto_con_moneda(pr: PagoReportado) -> str:
    monto = getattr(pr, "monto", "")
    moneda = (getattr(pr, "moneda", "") or "").strip()
    monto_str = str(monto).strip()
    return f"{monto_str} {moneda}".strip()


def _generar_recibo_desde_pago(pr: PagoReportado) -> bytes:
    """Genera recibo siempre con datos del pago reportado actual."""
    return generar_recibo_pago_reportado(
        referencia_interna=pr.referencia_interna,
        nombres=pr.nombres,
        apellidos=pr.apellidos,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
        institucion_financiera=pr.institucion_financiera,
        monto=_monto_con_moneda(pr),
        numero_operacion=pr.numero_operacion,
        fecha_pago=pr.fecha_pago,
    )


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
    """Devuelve la observación mostrando solo nombres de columnas (formato estándar: separador único ' / '). Si raw ya es lista corta, normaliza separadores; si es texto largo, extrae columnas por palabras clave."""
    if not raw or not (raw := raw.strip()):
        return None
    # Si ya parece lista de columnas (corta, sin frases largas): normalizar a " / "
    if len(raw) <= 80 and not any(x in raw for x in ("en la imagen", "en el formulario", "mientras que", "incluye el", "no coincide")):
        parts = [p.strip() for p in raw.replace(",", " / ").split(" / ") if p.strip()]
        return " / ".join(parts) if parts else raw[:80]
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
    return " / ".join(columnas) if columnas else raw[:100]


def _normalize_cedula_for_client_lookup(cedula: str) -> str:
    """Normaliza cédula para comparar con tabla clientes: sin guión/espacios, mayúsculas, sin ceros a la izquierda en el número (V08752971 -> V8752971)."""
    s = (cedula or "").replace("-", "").replace(" ", "").strip().upper()
    if not s:
        return s
    if len(s) >= 2 and s[0] in ("V", "E", "J", "G") and s[1:].isdigit():
        num = s[1:].lstrip("0") or "0"
        return s[0] + num
    return s


def _cedula_lookup_variants(cedula_norm: str) -> List[str]:
    """Para buscar cliente por cédula: si cedula_norm es V/E/J/G + dígitos, incluir también solo los dígitos (en clientes a veces está solo el número)."""
    if not cedula_norm:
        return []
    variants = [cedula_norm]
    if len(cedula_norm) >= 2 and cedula_norm[0] in ("V", "E", "J", "G") and cedula_norm[1:].isdigit():
        variants.append(cedula_norm[1:])
    return variants


def _cedulas_en_clientes_set(db: Session) -> set:
    """
    Devuelve el conjunto de cédulas que se consideran "en clientes" para la regla NO CLIENTES.
    Incluye la forma normalizada de cada clientes.cedula y, si la cédula en BD es solo dígitos (ej. 20149164),
    también añade la variante con prefijo V (V20149164), porque en préstamos/reportes suele usarse V+numero
    y el cliente puede estar guardado solo con el número.
    """
    clientes_cedulas = db.execute(select(Cliente.cedula).select_from(Cliente)).scalars().all()
    out = set()
    for row in clientes_cedulas:
        if not row or not row[0]:
            continue
        raw = (row[0] or "").strip().upper().replace("-", "").replace(" ", "")
        norm = _normalize_cedula_for_client_lookup(raw)
        if not norm:
            continue
        out.add(norm)
        # Si en clientes está solo el número (con o sin ceros a la izq.), añadir variante sin ceros y V+numero
        if len(norm) >= 6 and norm.isdigit():
            num = norm.lstrip("0") or "0"
            out.add(num)
            out.add("V" + num)
    return out


def _observacion_reglas_carga(
    db: Session,
    rows: list,
    cedulas_en_clientes: set,
    cedulas_bolivares: set,
    numeros_doc_en_pagos: set,
) -> list:
    """Para cada fila de pagos_reportados, devuelve lista de observaciones por reglas: NO CLIENTES, Monto (Bs no autorizado), DUPLICADO DOC. Cédula normalizada igual que en clientes (sin ceros a la izquierda)."""
    result = []
    for r in rows:
        partes = []
        raw_cedula = ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
        if cedula_norm and cedula_norm not in cedulas_en_clientes:
            partes.append("NO CLIENTES")
            # Auditoría: log para diagnosticar por qué se marca NO CLIENTES
            logger.info(
                "[COBROS] NO CLIENTES: ref=%s tipo_cedula=%r numero_cedula=%r raw=%r cedula_norm=%r | set_size=%s V20149164_in_set=%s",
                getattr(r, "referencia_interna", None),
                getattr(r, "tipo_cedula", None),
                getattr(r, "numero_cedula", None),
                raw_cedula,
                cedula_norm,
                len(cedulas_en_clientes),
                "V20149164" in cedulas_en_clientes,
            )
        moneda = (r.moneda or "BS").strip().upper()
        if moneda == "BS" and cedula_norm and cedula_norm not in cedulas_bolivares:
            partes.append("Monto: solo Bs si está en lista Bolívares")
        num_op = (r.numero_operacion or "").strip()
        n_doc = normalize_documento(num_op) if num_op else None
        if n_doc and n_doc in numeros_doc_en_pagos:
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
        q = q.where(~PagoReportado.estado.in_(("aprobado", "importado")))
        count_q = count_q.where(~PagoReportado.estado.in_(("aprobado", "importado")))
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

    # Conjuntos para reglas de observación al cargar (cédula en clientes, lista Bs, duplicado en pagos).
    # Normalizar cédula igual que en clientes: sin guión/espacios y sin ceros a la izquierda (V08752971 = V8752971).
    cedula_norms = [
        _normalize_cedula_for_client_lookup(
            ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        )
        for r in rows
    ]
    unique_cedulas = set(c for c in cedula_norms if c)
    # Conjunto de cédulas que existen en clientes (incluye variante V+numero si en BD está solo el número)
    cedulas_en_clientes = _cedulas_en_clientes_set(db)
    logger.debug(
        "[COBROS] pagos-reportados: cedulas_en_clientes set_size=%s V20149164_in_set=%s",
        len(cedulas_en_clientes),
        "V20149164" in cedulas_en_clientes,
    )

    cedulas_bolivares = set()
    list_bs = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
    cedulas_bolivares = {
        _normalize_cedula_for_client_lookup((row[0] or "").strip().upper().replace("-", "").replace(" ", ""))
        for row in list_bs if row[0]
    }

    num_ops_raw = list({(r.numero_operacion or "").strip() for r in rows if (r.numero_operacion or "").strip()})
    norms_for_query = {n for o in num_ops_raw for n in [normalize_documento(o)] if n}
    numeros_doc_en_pagos = set()
    if norms_for_query:
        existing_docs = db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(list(norms_for_query)))
        ).scalars().all()
        numeros_doc_en_pagos = {str(d) for d in existing_docs if d}

    partes_por_fila = _observacion_reglas_carga(
        db, rows, cedulas_en_clientes, cedulas_bolivares, numeros_doc_en_pagos
    )

    items = []
    for i, r in enumerate(rows):
        obs_gemini = _observacion_solo_columnas(r.gemini_comentario)
        partes_reglas = partes_por_fila[i] if i < len(partes_por_fila) else []
        # Orden estándar: reglas (NO CLIENTES, DUPLICADO DOC, Monto...) primero; luego divergencias Gemini (columnas). Un solo separador " / ".
        partes_final = partes_reglas + ([obs_gemini] if obs_gemini else [])
        observacion = " / ".join(partes_final) if partes_final else None
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
    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0, "importado": 0}
    for row in rows:
        if row.estado in counts:
            counts[row.estado] = row.cnt
    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado", "importado"))
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
    cedula_raw = (f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}").replace("-", "").replace(" ", "").strip().upper()
    if not cedula_raw:
        return ""
    cedula_norm = _normalize_cedula_for_client_lookup(cedula_raw)
    variants = _cedula_lookup_variants(cedula_norm)
    if not variants:
        return ""
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(select(Cliente).where(cedula_lookup.in_(variants))).scalars().first()
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
    cedula_norm = _normalize_cedula_for_client_lookup(
        ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
    )
    if not cedula_norm:
        raise HTTPException(status_code=400, detail="Cédula del reporte vacía; no se puede crear el pago en préstamos.")
    variants = _cedula_lookup_variants(cedula_norm)
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(
        select(Cliente).where(cedula_lookup.in_(variants))
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
        conciliado=True,
        fecha_conciliacion=datetime.now(),
        verificado_concordancia="SI",
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
    if pr.estado == "importado":
        return {"ok": True, "mensaje": "Ya importado a la tabla de pagos."}
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
        pdf_bytes = _generar_recibo_desde_pago(pr)
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
        if ok_mail:
            logger.info("[COBROS] Aprobar ref=%s: recibo enviado por correo a %s.", pr.referencia_interna, to_email)
        else:
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
    notif_activo = get_email_activo_servicio("notificaciones")
    logger.info(
        "[COBROS] Rechazar ref=%s: destino=%s servicio_notificaciones_activo=%s.",
        pr.referencia_interna, to_email or "sin correo", notif_activo,
    )
    if to_email and notif_activo:
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
        if ok_mail:
            logger.info("[COBROS] Rechazar ref=%s: correo enviado a %s (servicio notificaciones OK).", pr.referencia_interna, to_email)
        else:
            logger.error(
                "[COBROS] Rechazar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
    elif to_email and not notif_activo:
        logger.warning("[COBROS] Rechazar ref=%s: servicio notificaciones desactivado, no se envió correo a %s.", pr.referencia_interna, to_email)
    elif not to_email:
        logger.info("[COBROS] Rechazar ref=%s: no hay correo del cliente, no se envió notificación.", pr.referencia_interna)
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
    """Devuelve el PDF del recibo regenerado desde el pago reportado."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    pdf_bytes = _generar_recibo_desde_pago(pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    return Response(
        content=bytes(pdf_bytes),
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
    pdf_bytes = _generar_recibo_desde_pago(pr)
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
    if pr.estado in ("aprobado", "importado"):
        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado o importado a pagos.")
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

    # Si la moneda queda en BS, la cédula debe estar en la lista de autorizadas para Bolívares (misma normalización que en listado)
    moneda_final = (pr.moneda or "").strip().upper()
    if moneda_final == "BS":
        raw_cedula = ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
        if cedula_norm:
            list_bs_all = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
            cedulas_bs_norm = {
                _normalize_cedula_for_client_lookup((r[0] or "").strip().upper().replace("-", "").replace(" ", ""))
                for r in list_bs_all if r[0]
            }
            permitido_bs = cedula_norm in cedulas_bs_norm
            if not permitido_bs:
                raise HTTPException(
                    status_code=400,
                    detail="Observación: Bolívares. No puede guardar con moneda Bs; la cédula no está en la lista autorizada. Cambie a USD.",
                )

    if pr.recibo_pdf:
        pr.recibo_pdf = _generar_recibo_desde_pago(pr)
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
        pdf_bytes = _generar_recibo_desde_pago(pr)
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
                logger.info("[COBROS] Cambiar a aprobado ref=%s: recibo enviado por correo a %s.", pr.referencia_interna, to_email)
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
    elif body.estado == "rechazado":
        to_email = _email_cliente_pago_reportado(db, pr)
        notif_activo = get_email_activo_servicio("notificaciones")
        logger.info(
            "[COBROS] PATCH estado=rechazado ref=%s: destino=%s servicio_notificaciones_activo=%s.",
            pr.referencia_interna, to_email or "sin correo", notif_activo,
        )
        if to_email and notif_activo:
            body_text = (
                f"Referencia: {pr.referencia_interna}\n\n"
                f"Su reporte de pago no ha sido aprobado.\n\n"
                f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
                f"Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
                "RapiCredit C.A."
            )
            attachments_rech: List[Tuple[str, bytes]] = []
            if pr.comprobante:
                nombre_adj = (pr.comprobante_nombre or "comprobante").strip() or "comprobante"
                if not nombre_adj or "." not in nombre_adj:
                    ext = "pdf" if (pr.comprobante_tipo or "").lower().find("pdf") >= 0 else "jpg"
                    nombre_adj = f"comprobante_{pr.referencia_interna}.{ext}"
                attachments_rech.append((nombre_adj, bytes(pr.comprobante)))
            ok_mail, err_mail = send_email(
                [to_email],
                f"Reporte de pago no aprobado #{pr.referencia_interna}",
                body_text,
                attachments=attachments_rech if attachments_rech else None,
                servicio="notificaciones",
                respetar_destinos_manuales=True,
            )
            if ok_mail:
                logger.info("[COBROS] PATCH estado=rechazado ref=%s: correo enviado a %s (servicio notificaciones OK).", pr.referencia_interna, to_email)
                mensaje = "Estado actualizado a rechazado. Cliente notificado por correo (notificaciones@rapicreditca.com)."
            else:
                logger.error(
                    "[COBROS] PATCH estado=rechazado ref=%s: correo NO enviado a %s. Error: %s.",
                    pr.referencia_interna, to_email, err_mail or "desconocido",
                )
                mensaje = "Estado actualizado a rechazado. El correo al cliente no pudo enviarse."
        elif to_email and not notif_activo:
            logger.warning("[COBROS] PATCH estado=rechazado ref=%s: servicio notificaciones desactivado, no se envió correo a %s.", pr.referencia_interna, to_email)
            mensaje = "Estado actualizado a rechazado. Servicio de correo desactivado."
        else:
            logger.info("[COBROS] PATCH estado=rechazado ref=%s: no hay correo del cliente, no se envió notificación.", pr.referencia_interna)
            mensaje = "Estado actualizado a rechazado."

    _registrar_historial(db, pago_id, estado_anterior, body.estado, usuario_email, body.motivo)
    db.commit()
    return {"ok": True, "mensaje": mensaje}

