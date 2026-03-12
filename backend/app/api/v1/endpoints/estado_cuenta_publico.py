"""
Endpoints PÚBLICOS para consulta de estado de cuenta por cédula.
SEGURIDAD: Sin autenticación (router sin get_current_user). Solo datos del cliente
identificado por la cédula consultada. Rate limiting por IP. No expone otros servicios
ni datos de otros clientes. Solo expone: validar-cedula (nombre/email) y solicitar-estado-cuenta
(PDF estado de cuenta de esa cédula + envío al email registrado).
"""
import base64
import io
import json
import logging
import random
import string
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.cobros_public_rate_limit import (
    get_client_ip,
    check_rate_limit_estado_cuenta_validar,
    check_rate_limit_estado_cuenta_solicitar,
    check_rate_limit_estado_cuenta_verificar,
)
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.configuracion import Configuracion
from app.models.estado_cuenta_codigo import EstadoCuentaCodigo
from app.api.v1.endpoints.validadores import validate_cedula
from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio

from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta
logger = logging.getLogger(__name__)

CLAVE_ESTADO_CUENTA_EMAIL = "estado_cuenta_codigo_email"
DEFAULT_ASUNTO = "Codigo para estado de cuenta - RapiCredit"
DEFAULT_CUERPO = (
    "Estimado(a) {{nombre}},\n\n"
    "Tu codigo de verificacion es: {{codigo}}\n\n"
    "Valido por {{minutos_valido}} horas. No lo compartas.\n\n"
    "Saludos,\nRapiCredit"
)

router = APIRouter(dependencies=[])

MAX_CEDULA_LENGTH = 20


class ValidarCedulaEstadoCuentaResponse(BaseModel):
    ok: bool
    nombre: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class SolicitarEstadoCuentaRequest(BaseModel):
    cedula: str


class SolicitarEstadoCuentaResponse(BaseModel):
    ok: bool
    pdf_base64: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None


class SolicitarCodigoRequest(BaseModel):
    cedula: str


class SolicitarCodigoResponse(BaseModel):
    ok: bool
    mensaje: Optional[str] = None
    error: Optional[str] = None
    expira_en: Optional[str] = None  # ISO 8601 (ej. "2025-03-11T16:30:00Z") para mostrar "Código válido hasta las HH:MM"


class VerificarCodigoRequest(BaseModel):
    cedula: str
    codigo: str


class VerificarCodigoResponse(BaseModel):
    ok: bool
    pdf_base64: Optional[str] = None
    error: Optional[str] = None
    expira_en: Optional[str] = None  # ISO 8601 del código verificado (informativo)


CODIGO_EXPIRA_MINUTES = 120  # 2 horas
MAX_CODIGOS_ACTIVOS_POR_CEDULA = 3  # Máximo de códigos no usados y no expirados por cédula; los más viejos se eliminan


def _cedula_lookup(cedula_input: str) -> str:
    """Normaliza cédula para búsqueda en BD (sin guión)."""
    result = validate_cedula(cedula_input.strip())
    if not result.get("valido"):
        return ""
    valor = result.get("valor_formateado", "")
    return valor.replace("-", "") if valor else ""


def _generar_codigo_6() -> str:
    return "".join(random.choices(string.digits, k=6))


def _get_plantilla_email_codigo(
    db: Session,
    nombre: str = "Cliente",
    codigo: str = "",
) -> tuple:
    """
    Obtiene asunto y cuerpo del email del código desde configuracion (clave estado_cuenta_codigo_email).
    JSON: {"asunto": "...", "cuerpo": "..."}. Variables: {{nombre}}, {{codigo}}, {{minutos_valido}}.
    Si no hay config, devuelve valores por defecto.
    """
    try:
        row = db.get(Configuracion, CLAVE_ESTADO_CUENTA_EMAIL)
        if row and getattr(row, "valor", None):
            data = json.loads(row.valor) if isinstance(row.valor, str) else row.valor
            asunto = (data.get("asunto") or "").strip() or DEFAULT_ASUNTO
            cuerpo = (data.get("cuerpo") or "").strip() or DEFAULT_CUERPO
        else:
            asunto = DEFAULT_ASUNTO
            cuerpo = DEFAULT_CUERPO
    except Exception as e:
        logger.warning("No se pudo cargar plantilla estado_cuenta_codigo_email: %s", e)
        asunto = DEFAULT_ASUNTO
        cuerpo = DEFAULT_CUERPO
    minutos = CODIGO_EXPIRA_MINUTES // 60
    cuerpo = (
        cuerpo.replace("{{nombre}}", nombre)
        .replace("{{codigo}}", codigo)
        .replace("{{minutos_valido}}", str(minutos))
    )
    return asunto, cuerpo


def _obtener_datos_pdf(db: Session, cedula_lookup: str):
    """Obtiene cliente y datos para PDF. Retorna dict o None si no existe cliente."""
    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return None
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or "").strip()
    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()
    prestamos_list = []
    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)
        prestamos_list.append({
            "id": p.id,
            "producto": getattr(p, "producto", None) or "",
            "total_financiamiento": float(getattr(p, "total_financiamiento", 0) or 0),
            "estado": getattr(p, "estado", None) or "",
        })
    cuotas_pendientes = []
    total_pendiente = 0.0
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for cu in cuotas_rows:
            c = cu[0] if hasattr(cu, "__getitem__") else cu
            m = float(getattr(c, "monto", 0) or 0)
            total_pendiente += m
            cuotas_pendientes.append({
                "prestamo_id": getattr(c, "prestamo_id", ""),
                "numero_cuota": getattr(c, "numero_cuota", ""),
                "fecha_vencimiento": (getattr(c, "fecha_vencimiento", None) or "").isoformat() if getattr(c, "fecha_vencimiento", None) else "",
                "monto": m,
                "estado": getattr(c, "estado", None) or "PENDIENTE",
            })
    fecha_corte = date.today()
    amortizaciones_por_prestamo = []
    for p in prestamos_list:
        estado = (p.get("estado") or "").strip().upper()
        if estado not in ("APROBADO", "DESEMBOLSADO"):
            continue
        prestamo_id = p.get("id")
        if not prestamo_id:
            continue
        cuotas = _obtener_amortizacion_prestamo(db, prestamo_id)
        if not cuotas:
            continue
        amortizaciones_por_prestamo.append({
            "prestamo_id": prestamo_id,
            "producto": p.get("producto") or "Prestamo",
            "cuotas": cuotas,
        })
    return {
        "cedula_display": cedula_display,
        "nombre": nombre,
        "email": email,
        "prestamos_list": prestamos_list,
        "cuotas_pendientes": cuotas_pendientes,
        "total_pendiente": total_pendiente,
        "fecha_corte": fecha_corte,
        "amortizaciones_por_prestamo": amortizaciones_por_prestamo,
    }


def _obtener_amortizacion_prestamo(db: Session, prestamo_id: int) -> List[dict]:
    """Obtiene todas las cuotas del préstamo formateadas como tabla de amortización."""
    cuotas_rows = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota)
    ).scalars().all()
    resultado = []
    for c in cuotas_rows:
        cu = c[0] if hasattr(c, "__getitem__") else c
        saldo_inicial = float(getattr(cu, "saldo_capital_inicial", None) or 0)
        saldo_final = float(getattr(cu, "saldo_capital_final", None) or 0)
        monto_cuota = float(getattr(cu, "monto", None) or 0)
        monto_capital = max(0, saldo_inicial - saldo_final)
        monto_interes = max(0, monto_cuota - monto_capital)
        fecha_venc = getattr(cu, "fecha_vencimiento", None)
        fecha_iso = fecha_venc.isoformat() if fecha_venc else ""
        total_pagado_val = getattr(cu, "total_pagado", None)
        try:
            pago_conciliado_display = f"{float(total_pagado_val):,.2f}" if total_pagado_val is not None and float(total_pagado_val) > 0 else "-"
        except (TypeError, ValueError):
            pago_conciliado_display = "-"
        try:
            from datetime import datetime as _dt
            fecha_ddmm = _dt.strptime(fecha_iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y") if len(fecha_iso) >= 10 else (fecha_iso or "")
        except Exception:
            fecha_ddmm = fecha_iso[:10] if fecha_iso else ""
        resultado.append({
            "numero_cuota": getattr(cu, "numero_cuota", 0),
            "fecha_vencimiento": fecha_ddmm,
            "monto_capital": monto_capital,
            "monto_interes": monto_interes,
            "monto_cuota": monto_cuota,
            "saldo_capital_final": saldo_final,
            "pago_conciliado_display": pago_conciliado_display,
            "estado": getattr(cu, "estado", None) or "PENDIENTE",
        })
    return resultado


@router.get("/validar-cedula", response_model=ValidarCedulaEstadoCuentaResponse)
def validar_cedula_estado_cuenta(
    request: Request,
    cedula: str,
    db: Session = Depends(get_db),
):
    """
    Valida cédula y verifica que exista en tabla clientes.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y email si ok.
    """
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_validar(ip)
    if not cedula or not cedula.strip():
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Datos inválidos.")
    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return ValidarCedulaEstadoCuentaResponse(ok=False, error=result.get("error", "Cédula inválida."))
    cedula_lookup = _cedula_lookup(cedula.strip())
    if not cedula_lookup:
        return ValidarCedulaEstadoCuentaResponse(ok=False, error="Formato de cédula no reconocido.")

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return ValidarCedulaEstadoCuentaResponse(
            ok=False,
            error="La cédula ingresada no se encuentra registrada en nuestro sistema.",
        )
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    return ValidarCedulaEstadoCuentaResponse(
        ok=True,
        nombre=nombre,
        email=email or None,
    )



@router.post("/solicitar-codigo", response_model=SolicitarCodigoResponse)
def solicitar_codigo_estado_cuenta(
    request: Request,
    body: SolicitarCodigoRequest,
    db: Session = Depends(get_db),
):
    """
    Envia un codigo de un solo uso al email del cliente. El usuario debe ingresar
    ese codigo en verificar-codigo para descargar el PDF. Mensaje generico para no revelar si la cedula existe.
    Rate limit: 5/hora por IP.
    """
    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    try:
        check_rate_limit_estado_cuenta_solicitar(ip)
    except HTTPException as e:
        if e.status_code == 429:
            logger.info("estado_cuenta solicitar ip=%s outcome=fail reason=rate_limit", ip)
        raise
    if not cedula:
        logger.info("estado_cuenta solicitar ip=%s outcome=fail reason=cedula_vacia", ip)
        return SolicitarCodigoResponse(ok=False, error="Ingrese el numero de cedula.")
    if len(cedula) > MAX_CEDULA_LENGTH:
        logger.info("estado_cuenta solicitar ip=%s outcome=fail reason=cedula_larga", ip)
        return SolicitarCodigoResponse(ok=False, error="Datos invalidos.")
    result = validate_cedula(cedula)
    if not result.get("valido"):
        logger.info("estado_cuenta solicitar ip=%s outcome=fail reason=cedula_invalida", ip)
        return SolicitarCodigoResponse(ok=False, error=result.get("error", "Cedula invalida."))
    cedula_lookup = _cedula_lookup(cedula)
    if not cedula_lookup:
        logger.info("estado_cuenta solicitar ip=%s outcome=fail reason=formato_cedula", ip)
        return SolicitarCodigoResponse(ok=False, error="Formato de cedula no reconocido.")
    datos = _obtener_datos_pdf(db, cedula_lookup)
    if not datos or not (datos.get("email") or "").strip():
        logger.info("estado_cuenta solicitar ip=%s outcome=ok_sin_email (sin cliente/email)", ip)
        return SolicitarCodigoResponse(
            ok=True,
            mensaje="Si la cedula esta registrada, recibiras un codigo en tu correo en los proximos minutos.",
        )
    email = (datos.get("email") or "").strip()
    nombre = datos.get("nombre") or "Cliente"
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    from sqlalchemy import and_
    activos = (
        db.execute(
            select(EstadoCuentaCodigo)
            .where(
                and_(
                    EstadoCuentaCodigo.cedula_normalizada == cedula_lookup,
                    EstadoCuentaCodigo.usado == False,
                    EstadoCuentaCodigo.expira_en > now_utc,
                )
            )
            .order_by(EstadoCuentaCodigo.creado_en.desc())
        )
        .scalars().all()
    )
    if len(activos) >= MAX_CODIGOS_ACTIVOS_POR_CEDULA:
        for item in activos[MAX_CODIGOS_ACTIVOS_POR_CEDULA - 1:]:
            rec = item[0] if hasattr(item, "__getitem__") else item
            db.delete(rec)
        db.flush()
    codigo = _generar_codigo_6()
    expira_en = now_utc + timedelta(minutes=CODIGO_EXPIRA_MINUTES)
    creado_en = now_utc
    row = EstadoCuentaCodigo(
        cedula_normalizada=cedula_lookup,
        email=email,
        codigo=codigo,
        expira_en=expira_en,
        usado=False,
        creado_en=creado_en,
    )
    db.add(row)
    db.commit()
    asunto, cuerpo = _get_plantilla_email_codigo(db, nombre=nombre, codigo=codigo)
    try:
        if get_email_activo_servicio("estado_cuenta"):
            send_email([email], asunto, cuerpo)
        logger.info(
            "estado_cuenta solicitar ip=%s outcome=ok cedula_suffix=***%s",
            ip,
            cedula_lookup[-4:] if len(cedula_lookup) >= 4 else "****",
        )
    except Exception as e:
        logger.warning("No se pudo enviar codigo por email a %s: %s", email, e)
        logger.info("estado_cuenta solicitar ip=%s outcome=ok_email_fail cedula_suffix=***%s", ip, cedula_lookup[-4:] if len(cedula_lookup) >= 4 else "****")
    expira_en_iso = expira_en.isoformat() + "Z" if expira_en else None
    return SolicitarCodigoResponse(
        ok=True,
        mensaje="Si la cedula esta registrada, recibiras un codigo en tu correo en los proximos minutos.",
        expira_en=expira_en_iso,
    )



@router.post("/verificar-codigo", response_model=VerificarCodigoResponse)
def verificar_codigo_estado_cuenta(
    request: Request,
    body: VerificarCodigoRequest,
    db: Session = Depends(get_db),
):
    """
    Verifica el codigo enviado al email y devuelve el PDF de estado de cuenta.
    El codigo es de un solo uso. Rate limit: 15 intentos/15 min por IP.
    """
    cedula = (body.cedula or "").strip()
    codigo = (body.codigo or "").strip()
    ip = get_client_ip(request)
    try:
        check_rate_limit_estado_cuenta_verificar(ip)
    except HTTPException as e:
        if e.status_code == 429:
            logger.info("estado_cuenta verificar ip=%s outcome=fail reason=rate_limit", ip)
        raise
    if not cedula or not codigo:
        logger.info("estado_cuenta verificar ip=%s outcome=fail reason=cedula_o_codigo_vacio", ip)
        return VerificarCodigoResponse(ok=False, error="Ingrese cedula y codigo.")
    cedula_lookup = _cedula_lookup(cedula)
    if not cedula_lookup:
        logger.info("estado_cuenta verificar ip=%s outcome=fail reason=formato_cedula", ip)
        return VerificarCodigoResponse(ok=False, error="Formato de cedula no reconocido.")
    from sqlalchemy import and_
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    fila = db.execute(
        select(EstadoCuentaCodigo).where(
            and_(
                EstadoCuentaCodigo.cedula_normalizada == cedula_lookup,
                EstadoCuentaCodigo.codigo == codigo.strip(),
                EstadoCuentaCodigo.expira_en > now,
                EstadoCuentaCodigo.usado == False,
            )
        )
    ).scalars().first()
    if not fila:
        return VerificarCodigoResponse(ok=False, error="Codigo invalido o expirado. Solicite uno nuevo.")
    rec = fila[0] if hasattr(fila, "__getitem__") else fila
    try:
        datos = _obtener_datos_pdf(db, cedula_lookup)
        if not datos:
            return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
        pdf_bytes = generar_pdf_estado_cuenta(
            cedula=datos.get("cedula_display") or "",
            nombre=datos.get("nombre") or "",
            prestamos=datos.get("prestamos_list") or [],
            cuotas_pendientes=datos.get("cuotas_pendientes") or [],
            total_pendiente=float(datos.get("total_pendiente") or 0),
            fecha_corte=datos.get("fecha_corte") or date.today(),
            amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as e:
        logger.exception("Error generando PDF estado de cuenta: %s", e)
        logger.info("estado_cuenta verificar ip=%s outcome=fail reason=error_pdf", ip)
        return VerificarCodigoResponse(
            ok=False,
            error="No se pudo generar el PDF. Intente de nuevo o solicite un nuevo codigo.",
        )
    rec.usado = True
    db.commit()
    logger.info("estado_cuenta verificar ip=%s outcome=ok cedula_suffix=***%s", ip, cedula_lookup[-4:] if len(cedula_lookup) >= 4 else "****")
    return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64, expira_en=expira_en_iso)


@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)
def solicitar_estado_cuenta(
    request: Request,
    body: SolicitarEstadoCuentaRequest,
    db: Session = Depends(get_db),
):
    """
    Genera el PDF de estado de cuenta para la cédula consultada, lo envía al email
    registrado del cliente y devuelve el PDF en base64 para visualización.
    Público, sin auth. Rate limit: 5 solicitudes/hora por IP.
    """
    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_solicitar(ip)
    if not cedula:
        return SolicitarEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return SolicitarEstadoCuentaResponse(ok=False, error="Datos inválidos.")
    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return SolicitarEstadoCuentaResponse(ok=False, error=result.get("error", "Cédula inválida."))
    cedula_lookup = _cedula_lookup(cedula.strip())
    if not cedula_lookup:
        return SolicitarEstadoCuentaResponse(ok=False, error="Formato de cédula no reconocido.")

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return SolicitarEstadoCuentaResponse(
            ok=False,
            error="La cédula no se encuentra registrada.",
        )
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or cedula).strip()

    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()
    prestamos_list = []
    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)
        prestamos_list.append({
            "id": p.id,
            "producto": getattr(p, "producto", None) or "",
            "total_financiamiento": float(getattr(p, "total_financiamiento", 0) or 0),
            "estado": getattr(p, "estado", None) or "",
        })

    cuotas_pendientes = []
    total_pendiente = 0.0
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for c in cuotas_rows:
            cu = c[0] if hasattr(c, "__getitem__") else c
            m = float(getattr(cu, "monto", 0) or 0)
            total_pendiente += m
            cuotas_pendientes.append({
                "prestamo_id": getattr(cu, "prestamo_id", ""),
                "numero_cuota": getattr(cu, "numero_cuota", ""),
                "fecha_vencimiento": (getattr(cu, "fecha_vencimiento", None) or "").isoformat() if getattr(cu, "fecha_vencimiento", None) else "",
                "monto": m,
                "estado": getattr(cu, "estado", None) or "PENDIENTE",
            })

    fecha_corte = date.today()
    # Tablas de amortización para préstamos APROBADOS/DESEMBOLSADOS (misma estructura que en Detalles del Préstamo)
    amortizaciones_por_prestamo = []
    for p in prestamos_list:
        estado = (p.get("estado") or "").strip().upper()
        if estado not in ("APROBADO", "DESEMBOLSADO"):
            continue
        prestamo_id = p.get("id")
        if not prestamo_id:
            continue
        cuotas = _obtener_amortizacion_prestamo(db, prestamo_id)
        if not cuotas:
            continue
        amortizaciones_por_prestamo.append({
            "prestamo_id": prestamo_id,
            "producto": p.get("producto") or "Préstamo",
            "cuotas": cuotas,
        })

    pdf_bytes = generar_pdf_estado_cuenta(
        cedula=cedula_display,
        nombre=nombre,
        prestamos=prestamos_list,
        cuotas_pendientes=cuotas_pendientes,
        total_pendiente=total_pendiente,
        fecha_corte=fecha_corte,
        amortizaciones_por_prestamo=amortizaciones_por_prestamo,
    )

    if email:
        try:
            filename = f"estado_cuenta_{cedula_display.replace('-', '_')}.pdf"
            email_body = (f"Estimado(a) {nombre},\n\nSe adjunta su estado de cuenta con fecha de corte {fecha_corte.isoformat()}.\n\nSaludos,\nRapiCredit")
            if get_email_activo_servicio("estado_cuenta"):
                send_email([email], f"Estado de cuenta - {fecha_corte.isoformat()}", email_body,
                attachments=[(filename, pdf_bytes)],
            )
        except Exception as e:
            logger.warning("No se pudo enviar estado de cuenta por email a %s: %s", email, e)
            # No fallar la petición: el PDF se devuelve igual

    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    mensaje = "Estado de cuenta generado. Se ha enviado una copia al correo registrado." if email else "Estado de cuenta generado."
    return SolicitarEstadoCuentaResponse(
        ok=True,
        pdf_base64=pdf_b64,
        mensaje=mensaje,
    )
