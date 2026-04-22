"""
Endpoints PÚBLICOS del módulo Cobros (formulario de reporte de pago).

SEGURIDAD: Sin login de panel. Por defecto (COBROS_PUBLICO_OTP_DISABLED=True) rapicredit-cobros
solo exige cedula valida + rate limit + honeypot; opcionalmente COBROS_PUBLICO_OTP_DISABLED=False
activa OTP por correo y JWT cobros_public en validar-cedula y enviar-reporte.
El bypass por origen=infopagos solo aplica cuando la petición trae Bearer válido de staff.
Estado de cuenta publico usa endpoints propios con OTP (no este flag).
"""

import logging
import random
import re
import string
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.database import get_db, SessionLocal
from app.core.cobros_public_rate_limit import (
    get_client_ip,
    check_rate_limit_validar_cedula,
    check_rate_limit_enviar_reporte,
    check_rate_limit_cobros_public_solicitar,
    check_rate_limit_cobros_public_verificar,
)
from app.models.cliente import Cliente
from app.models.pago_reportado import PagoReportado
from app.models.cobros_publico_codigo import CobrosPublicoCodigo
from app.api.v1.endpoints.validadores import validate_cedula
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar
from app.services.cobros.cedula_reportar_bs_service import cedula_autorizada_para_bs
from app.services.pagos_gmail.gemini_service import (
    compare_form_with_image,
    extract_infopagos_campos_desde_comprobante,
)
from app.services.cobros.recibo_pdf import (
    RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE,
    WHATSAPP_LINK,
)
from app.services.documentos_cliente_centro import generar_recibo_pdf_desde_pago_reportado
from app.services.cobros.recibo_cuotas_lookup import texto_cuotas_aplicadas_pago_reportado
from app.services.cobros import cobros_publico_reporte_service as cpr
from app.core.email import cobros_recibo_attachments_or_oversize_note, send_email
from app.services.notificaciones_exclusion_desistimiento import cliente_bloqueado_por_desistimiento
from app.core.security import decode_token, create_recibo_infopagos_token, create_cobros_public_token
from app.core.config import settings
from app.core.email_config_holder import get_email_activo_servicio
from app.utils.cliente_emails import emails_destino_desde_objeto, unir_destinatarios_log
from app.api.v1.endpoints.cobros.routes import reportado_falla_validadores_cobros

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[])


def _procesar_recibo_y_correo_aprobado_background(
    pago_reportado_id: int,
    referencia: str,
    cliente_id: int,
    canal: str,
) -> None:
    """
    Tareas no críticas (PDF + correo) en segundo plano para no bloquear el POST.
    """
    db_bg = SessionLocal()
    try:
        pr = db_bg.execute(
            select(PagoReportado).where(PagoReportado.id == int(pago_reportado_id))
        ).scalars().first()
        cliente = db_bg.execute(
            select(Cliente).where(Cliente.id == int(cliente_id))
        ).scalars().first()
        if not pr or not cliente:
            logger.warning(
                "[%s] Background recibo: pago/cliente no encontrado (pago_id=%s cliente_id=%s)",
                canal,
                pago_reportado_id,
                cliente_id,
            )
            return

        pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db_bg, pr)
        pr.recibo_pdf = pdf_bytes

        to_emails = emails_destino_desde_objeto(cliente)
        if cliente_bloqueado_por_desistimiento(
            db_bg,
            cliente_id=cliente.id,
            cedula=cliente.cedula,
            email=(to_emails[0] if to_emails else ""),
        ):
            logger.info(
                "[%s] Bloqueo recibo ref=%s: cliente_id=%s con prestamo DESISTIMIENTO",
                canal,
                referencia,
                cliente.id,
            )
            to_emails = []

        if to_emails:
            att, size_note = cobros_recibo_attachments_or_oversize_note(
                f"recibo_{referencia}.pdf", pdf_bytes
            )
            if canal == "INFOPAGOS":
                subject = f"Recibo de pago {cpr.referencia_display(referencia)}"
                body_intro = "Se ha registrado un pago a su nombre."
            else:
                subject = (
                    f"Recibo de reporte de pago {cpr.referencia_display(referencia)}"
                )
                body_intro = "Se ha recibido su reporte de pago."
            body = (
                f"{body_intro}\n\n"
                f"Número de referencia: {cpr.referencia_display(referencia)}\n\n"
                + (
                    "El recibo se adjunta en PDF.\n\n"
                    if att
                    else "El recibo no se adjunta en este correo (archivo demasiado grande para el servidor de correo).\n\n"
                )
                + f"Si necesita información adicional, contáctenos por WhatsApp: {WHATSAPP_LINK}\n\n"
                + size_note
                + "RapiCredit C.A."
            )
            ok_mail, err_mail = send_email(
                to_emails,
                subject,
                body,
                attachments=att,
                servicio="cobros",
                respetar_destinos_manuales=True,
            )
            if not ok_mail:
                logger.error(
                    "[%s] Recibo ref=%s: correo NO enviado a %s. Error: %s.",
                    canal,
                    referencia,
                    unir_destinatarios_log(to_emails),
                    err_mail or "desconocido",
                )
            else:
                logger.info(
                    "[%s] Recibo ref=%s: correo enviado a %s.",
                    canal,
                    referencia,
                    unir_destinatarios_log(to_emails),
                )

        db_bg.commit()
    except Exception as e:
        db_bg.rollback()
        logger.exception(
            "[%s] Background recibo/correo falló (pago_id=%s): %s",
            canal,
            pago_reportado_id,
            e,
        )
    finally:
        db_bg.close()


class ValidarCedulaResponse(BaseModel):
    ok: bool
    nombre: Optional[str] = None
    """Correo enmascarado para validación visual sin exponer PII completa."""
    email_enmascarado: Optional[str] = None
    error: Optional[str] = None
    """True si esta cédula puede reportar pagos en Bolívares (Bs) en cobros/infopagos."""
    puede_reportar_bs: Optional[bool] = None


class EnviarReporteResponse(BaseModel):
    ok: bool
    referencia_interna: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None
    estado_reportado: Optional[str] = None
    recibo_enviado: Optional[bool] = None


class EnviarReporteInfopagosResponse(BaseModel):
    """Respuesta de Infopagos. Token y recibo solo si quedo aprobado (misma politica que cobros publico)."""

    ok: bool
    referencia_interna: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None
    recibo_descarga_token: Optional[str] = None
    pago_id: Optional[int] = None
    estado_reportado: Optional[str] = None
    aplicado_a_cuotas: Optional[str] = None
    recibo_listo: Optional[bool] = None


class ReciboInfopagosStatusResponse(BaseModel):
    ok: bool
    pago_id: int
    recibo_listo: bool
    estado_reportado: Optional[str] = None
    mensaje: Optional[str] = None


class DigitalizarComprobanteSugerencia(BaseModel):
    fecha_pago: Optional[str] = None
    institucion_financiera: str = ""
    numero_operacion: str = ""
    monto: Optional[float] = None
    moneda: str = "BS"
    cedula_pagador_en_comprobante: str = ""
    notas_modelo: str = ""


class DigitalizarComprobanteResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    sugerencia: Optional[DigitalizarComprobanteSugerencia] = None


MAX_CEDULA_LENGTH = 20

COBROS_CODIGO_EXPIRA_MINUTES = 120
MAX_CODIGOS_COBROS_PUBLICO_POR_CEDULA = 3


class SolicitarCodigoReporteRequest(BaseModel):
    cedula: str
    email: str


class SolicitarCodigoReporteResponse(BaseModel):
    ok: bool
    mensaje: Optional[str] = None
    error: Optional[str] = None
    expira_en: Optional[str] = None


class VerificarCodigoReporteRequest(BaseModel):
    cedula: str
    email: str
    codigo: str


class VerificarCodigoReporteResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    nombre: Optional[str] = None
    puede_reportar_bs: Optional[bool] = None
    email_enmascarado: Optional[str] = None


def _is_internal_staff_request(request: Request) -> bool:
    """
    Solo considera "interno" a quien trae Bearer token de personal válido.
    Evita que un cliente público eleve privilegios forzando `origen=infopagos`.
    """
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    payload = decode_token(token)
    if not payload:
        return False
    if payload.get("type") != "access":
        return False
    if payload.get("scope") == "finiquito":
        return False
    return True


def _cobros_public_otp_required(origen: Optional[str], request: Request) -> bool:
    """OTP cobros público: solo se omite para flujo interno autenticado."""
    if settings.COBROS_PUBLICO_OTP_DISABLED:
        return False
    if (
        (origen or "").strip().lower() == "infopagos"
        and _is_internal_staff_request(request)
    ):
        return False
    return True


def _token_bearer_only(request: Request) -> Optional[str]:
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return None
    tok = auth[7:].strip()
    return tok or None


def _validar_token_recibo_infopagos(request: Request, pago_id: int) -> None:
    token_to_use = _token_bearer_only(request)
    if not token_to_use:
        raise HTTPException(
            status_code=401,
            detail="Token requerido en Authorization header.",
        )

    payload = decode_token(token_to_use)
    if not payload or payload.get("type") != "recibo_infopagos":
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    token_pago_id = payload.get("pago_id") or payload.get("sub")
    if token_pago_id is None:
        raise HTTPException(status_code=401, detail="Token inválido.")
    try:
        token_pago_id = int(token_pago_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido.")

    if token_pago_id != int(pago_id):
        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")


def _validar_bearer_cobros_public(request: Request, cedula_lookup: str) -> Optional[str]:
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("bearer "):
        return (
            "Debe verificar su correo con el codigo enviado antes de continuar. "
            "Use el paso anterior del formulario."
        )
    token = auth[7:].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "cobros_public":
        return "La sesion de verificacion expiro o no es valida. Solicite un nuevo codigo."
    sub = (payload.get("sub") or "").strip().replace("-", "")
    if not sub or sub != cedula_lookup:
        return "La cedula no coincide con la verificacion por correo."
    return None


def _norm_email_reporte_pub(e: str) -> str:
    return (e or "").strip().lower()


def _generar_codigo_6_reporte_pub() -> str:
    return "".join(random.choices(string.digits, k=6))


def _mask_email(email: str) -> str:
    """Enmascara correo: r***z@gmail.com"""
    if not email or "@" not in email:
        return "***@***"
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


@router.post("/solicitar-codigo-reporte", response_model=SolicitarCodigoReporteResponse)
def cobros_public_solicitar_codigo_reporte(
    request: Request,
    body: SolicitarCodigoReporteRequest,
    db: Session = Depends(get_db),
):
    """
    Envia un codigo de 6 digitos al correo registrado del cliente si cedula y correo coinciden
    con la base de datos y el cliente puede reportar pago en web. Respuesta generica si no aplica.
    """
    ip = get_client_ip(request)
    try:
        check_rate_limit_cobros_public_solicitar(ip)
    except HTTPException:
        raise

    cedula_raw = (body.cedula or "").strip()
    email_in = _norm_email_reporte_pub(body.email or "")
    if not cedula_raw or not email_in:
        return SolicitarCodigoReporteResponse(ok=False, error="Ingrese cedula y correo electronico.")
    if len(cedula_raw) > MAX_CEDULA_LENGTH:
        return SolicitarCodigoReporteResponse(ok=False, error="Datos invalidos.")

    result = validate_cedula(cedula_raw)
    if not result.get("valido"):
        return SolicitarCodigoReporteResponse(ok=False, error=result.get("error", "Cedula invalida."))

    valor = result.get("valor_formateado", "")
    cedula_lookup = valor.replace("-", "") if valor else ""
    if not cedula_lookup:
        return SolicitarCodigoReporteResponse(ok=False, error="Formato de cedula no reconocido.")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        logger.info("cobros_public solicitar-codigo: cedula no registrada ip=%s", ip)
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
        )

    destinos_reg = emails_destino_desde_objeto(cliente)
    if not destinos_reg:
        logger.info(
            "cobros_public solicitar-codigo: cliente sin email cedula_suffix=***%s",
            cedula_lookup[-4:] if len(cedula_lookup) >= 4 else "****",
        )
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
        )

    if email_in.lower() not in {d.lower() for d in destinos_reg}:
        logger.info("cobros_public solicitar-codigo: email no coincide con BD")
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
        )

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        logger.info("cobros_public solicitar-codigo: no puede reportar web")
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    activos = (
        db.execute(
            select(CobrosPublicoCodigo)
            .where(
                and_(
                    CobrosPublicoCodigo.cedula_normalizada == cedula_lookup,
                    CobrosPublicoCodigo.usado == False,
                    CobrosPublicoCodigo.expira_en > now_utc,
                )
            )
            .order_by(CobrosPublicoCodigo.creado_en.desc())
        )
        .scalars()
        .all()
    )
    if len(activos) >= MAX_CODIGOS_COBROS_PUBLICO_POR_CEDULA:
        for item in activos[MAX_CODIGOS_COBROS_PUBLICO_POR_CEDULA - 1 :]:
            db.delete(item)
        db.flush()

    codigo = _generar_codigo_6_reporte_pub()
    expira_en = now_utc + timedelta(minutes=COBROS_CODIGO_EXPIRA_MINUTES)
    row = CobrosPublicoCodigo(
        cedula_normalizada=cedula_lookup,
        email=email_in,
        codigo=codigo,
        expira_en=expira_en,
        usado=False,
        creado_en=now_utc,
    )
    db.add(row)
    db.commit()

    nombre_c = (cliente.nombres or "").strip() or "Cliente"
    asunto = "[RapiCredit] Codigo para reportar su pago"
    cuerpo = (
        f"Estimado(a) {nombre_c},\n\n"
        f"Su codigo para continuar en el formulario de reporte de pago es: {codigo}\n\n"
        f"Valido por {COBROS_CODIGO_EXPIRA_MINUTES} minutos. No lo comparta.\n\n"
        "Si usted no solicito este codigo, ignore este mensaje.\n\n"
        "RapiCredit"
    )

    if not get_email_activo_servicio("estado_cuenta"):
        logger.warning(
            "cobros_public solicitar-codigo: servicio email estado_cuenta desactivado, codigo no enviado"
        )
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
            expira_en=expira_en.isoformat() + "Z",
        )

    if cliente_bloqueado_por_desistimiento(db, cedula=cedula_lookup, email=email_in):
        logger.info("cobros_public solicitar-codigo: bloqueo desistimiento")
        return SolicitarCodigoReporteResponse(
            ok=True,
            mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
            expira_en=expira_en.isoformat() + "Z",
        )

    ok_send, err_send = send_email(
        [email_in],
        asunto,
        cuerpo,
        servicio="estado_cuenta",
        respetar_destinos_manuales=True,
    )
    if not ok_send:
        logger.warning("cobros_public solicitar-codigo: SMTP fallo %s", err_send)

    return SolicitarCodigoReporteResponse(
        ok=True,
        mensaje="Si los datos coinciden con nuestros registros, recibira un codigo en su correo.",
        expira_en=expira_en.isoformat() + "Z",
    )


@router.post("/verificar-codigo-reporte", response_model=VerificarCodigoReporteResponse)
def cobros_public_verificar_codigo_reporte(
    request: Request,
    body: VerificarCodigoReporteRequest,
    db: Session = Depends(get_db),
):
    """Verifica el codigo y devuelve JWT de sesion para validar-cedula y enviar-reporte."""
    ip = get_client_ip(request)
    try:
        check_rate_limit_cobros_public_verificar(ip)
    except HTTPException:
        raise

    cedula_raw = (body.cedula or "").strip()
    email_in = _norm_email_reporte_pub(body.email or "")
    codigo = (body.codigo or "").strip()
    if not cedula_raw or not email_in or not codigo:
        return VerificarCodigoReporteResponse(ok=False, error="Ingrese cedula, correo y codigo.")

    result = validate_cedula(cedula_raw)
    if not result.get("valido"):
        return VerificarCodigoReporteResponse(ok=False, error=result.get("error", "Cedula invalida."))

    cedula_lookup = (result.get("valor_formateado", "") or "").replace("-", "")
    if not cedula_lookup:
        return VerificarCodigoReporteResponse(ok=False, error="Formato de cedula no reconocido.")

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    fila = db.execute(
        select(CobrosPublicoCodigo).where(
            and_(
                CobrosPublicoCodigo.cedula_normalizada == cedula_lookup,
                CobrosPublicoCodigo.email == email_in,
                CobrosPublicoCodigo.codigo == codigo.strip(),
                CobrosPublicoCodigo.expira_en > now_utc,
                CobrosPublicoCodigo.usado == False,
            )
        )
    ).scalars().first()
    if not fila:
        return VerificarCodigoReporteResponse(
            ok=False,
            error="No fue posible validar los datos. Verifique e intente nuevamente.",
        )

    fila.usado = True
    db.commit()

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return VerificarCodigoReporteResponse(
            ok=False,
            error="No fue posible validar los datos. Verifique e intente nuevamente.",
        )

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return VerificarCodigoReporteResponse(
            ok=False,
            error="No fue posible validar los datos. Verifique e intente nuevamente.",
        )

    nombre = (cliente.nombres or "").strip()
    email_raw = ((fila.email or "").strip() or (cliente.email or "").strip())
    puede_bs = cedula_autorizada_para_bs(db, cedula_lookup)
    token = create_cobros_public_token(cedula_lookup, expire_minutes=COBROS_CODIGO_EXPIRA_MINUTES)

    return VerificarCodigoReporteResponse(
        ok=True,
        access_token=token,
        expires_in=COBROS_CODIGO_EXPIRA_MINUTES * 60,
        nombre=nombre,
        puede_reportar_bs=puede_bs,
        email_enmascarado=_mask_email(email_raw) if email_raw else None,
    )


@router.get("/validar-cedula", response_model=ValidarCedulaResponse)
def validar_cedula_publico(
    request: Request,
    cedula: str,
    origen: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Valida cédula (formato V/E/J + dígitos), existencia en clientes y un único préstamo APROBADO
    (misma regla que la importación a la tabla pagos).

    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.
    Sin límite cuando origen=infopagos y la petición es interna autenticada (staff).
    """
    ip = get_client_ip(request)
    if not (
        (origen or "").strip().lower() == "infopagos"
        and _is_internal_staff_request(request)
    ):
        check_rate_limit_validar_cedula(ip)

    if not cedula or not cedula.strip():
        return ValidarCedulaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return ValidarCedulaResponse(ok=False, error="Datos inválidos.")

    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return ValidarCedulaResponse(ok=False, error=result.get("error", "Cédula inválida."))

    valor = result.get("valor_formateado", "")
    cedula_lookup = valor.replace("-", "") if valor else ""
    if not cedula_lookup:
        return ValidarCedulaResponse(ok=False, error="Formato de cédula no reconocido.")

    if _cobros_public_otp_required(origen, request):
        token_err = _validar_bearer_cobros_public(request, cedula_lookup)
        if token_err:
            return ValidarCedulaResponse(ok=False, error=token_err)

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return ValidarCedulaResponse(ok=False, error="No fue posible validar los datos. Verifique e intente nuevamente.")

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return ValidarCedulaResponse(ok=False, error="No fue posible validar los datos. Verifique e intente nuevamente.")

    puede_bs = cedula_autorizada_para_bs(db, cedula_lookup)
    nombre = (cliente.nombres or "").strip()
    email = (cliente.email or "").strip()
    return ValidarCedulaResponse(
        ok=True,
        # Flujo público de cobros: mostrar nombre nominal validado por cédula.
        nombre=nombre,
        email_enmascarado=_mask_email(email),
        puede_reportar_bs=puede_bs,
    )


HONEYPOT_FIELD = "contact_website"


@router.post("/digitalizar-comprobante", response_model=DigitalizarComprobanteResponse)
async def digitalizar_comprobante_publico(
    request: Request,
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    comprobante: UploadFile = File(...),
):
    """
    Digitaliza el comprobante con Gemini para sugerir datos antes de confirmar el envío.
    No guarda reporte; solo devuelve sugerencias editables por el cliente.
    """
    ip = get_client_ip(request)
    check_rate_limit_validar_cedula(ip)

    cedula_input = f"{(tipo_cedula or '').strip()}{(numero_cedula or '').strip()}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        return DigitalizarComprobanteResponse(ok=False, error=val.get("error", "Cédula inválida."))

    cedula_lookup = (val.get("valor_formateado", "") or "").replace("-", "")
    if not cedula_lookup:
        return DigitalizarComprobanteResponse(ok=False, error="Formato de cédula no reconocido.")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return DigitalizarComprobanteResponse(ok=False, error="La cédula no está registrada.")

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return DigitalizarComprobanteResponse(ok=False, error=err_pres)

    content = await comprobante.read()
    fn_comp = comprobante.filename or "comprobante"
    ctype = cpr.mime_efectivo_comprobante_web(comprobante.content_type or "", fn_comp)
    err_file, filename = cpr.validar_adjunto_comprobante_bytes(
        content,
        ctype,
        fn_comp,
        mensaje_excel_largo=False,
    )
    if err_file:
        return DigitalizarComprobanteResponse(ok=False, error=err_file)

    tipo = (tipo_cedula or "").strip().upper()[:2]
    numero = (numero_cedula or "").strip()
    ctx_ced = f"{tipo}{numero}".replace("-", "")

    gem = extract_infopagos_campos_desde_comprobante(ctx_ced, content, filename)
    if not gem.get("ok"):
        return DigitalizarComprobanteResponse(
            ok=False,
            error=gem.get("error") or "No se pudo digitalizar el comprobante.",
            sugerencia=None,
        )

    fecha_d = gem.get("fecha_pago")
    fecha_iso = fecha_d.isoformat() if isinstance(fecha_d, date) else None
    sugerencia = DigitalizarComprobanteSugerencia(
        fecha_pago=fecha_iso,
        institucion_financiera=str(gem.get("institucion_financiera") or "").strip()[:100],
        numero_operacion=str(gem.get("numero_operacion") or "").strip()[:100],
        monto=gem.get("monto"),
        moneda=(gem.get("moneda") or "BS") if (gem.get("moneda") or "BS") in ("BS", "USD") else "BS",
        cedula_pagador_en_comprobante=str(gem.get("cedula_pagador_en_comprobante") or "").strip()[:30],
        notas_modelo=str(gem.get("notas") or "").strip()[:300],
    )
    return DigitalizarComprobanteResponse(ok=True, error=None, sugerencia=sugerencia)


@router.post("/enviar-reporte", response_model=EnviarReporteResponse)
async def enviar_reporte_publico(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    fecha_pago: date = Form(...),
    institucion_financiera: str = Form(...),
    numero_operacion: str = Form(...),
    monto: float = Form(...),
    moneda: str = Form("BS"),
    comprobante: UploadFile = File(...),
    observacion: Optional[str] = Form(None),
    contact_website: Optional[str] = Form(None),
):
    """
    Recibe el reporte de pago del formulario público.

    Rate limit: 5 envíos/hora por IP. Honeypot anti-bot. Validación de archivo por magic bytes.
    """
    ip = get_client_ip(request)
    check_rate_limit_enviar_reporte(ip)

    if contact_website and str(contact_website).strip():
        logger.warning("[COBROS_PUBLIC] Honeypot activado desde IP %s", ip)
        return EnviarReporteResponse(ok=False, error="No se pudo procesar el envío. Intente de nuevo.")

    cedula_input = f"{tipo_cedula}{numero_cedula}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        return EnviarReporteResponse(ok=False, error=val.get("error", "Cédula inválida."))

    cedula_lookup = val.get("valor_formateado", "").replace("-", "")
    if _cobros_public_otp_required(None, request):
        token_err = _validar_bearer_cobros_public(request, cedula_lookup)
        if token_err:
            return EnviarReporteResponse(ok=False, error=token_err)

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return EnviarReporteResponse(ok=False, error="La cédula no está registrada.")

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return EnviarReporteResponse(ok=False, error=err_pres)

    err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
        tipo_cedula=tipo_cedula,
        numero_cedula=numero_cedula,
        institucion_financiera=institucion_financiera,
        numero_operacion=numero_operacion,
        monto=monto,
        moneda=moneda,
        observacion=observacion,
    )
    if err_campos:
        return EnviarReporteResponse(ok=False, error=err_campos)

    err_neg = cpr.validar_reglas_bs_tasa_monto_fecha(
        db,
        cedula_lookup=cedula_lookup,
        fecha_pago=fecha_pago,
        monto=monto,
        mon=mon_norm,
    )
    if err_neg:
        return EnviarReporteResponse(ok=False, error=err_neg)

    content = await comprobante.read()
    fn_comp = comprobante.filename or "comprobante"
    ctype = cpr.mime_efectivo_comprobante_web(comprobante.content_type or "", fn_comp)
    err_file, filename = cpr.validar_adjunto_comprobante_bytes(
        content,
        ctype,
        fn_comp,
        mensaje_excel_largo=True,
    )
    if err_file:
        return EnviarReporteResponse(ok=False, error=err_file)

    try:
        pr, referencia, err_crear = cpr.crear_pago_reportado_con_referencia_o_retry(
            db,
            content=content,
            ctype=ctype,
            filename=filename,
            cliente_nombres=(cliente.nombres or ""),
            tipo_cedula=tipo_cedula,
            numero_cedula=numero_cedula,
            fecha_pago=fecha_pago,
            institucion_financiera=institucion_financiera,
            numero_operacion=numero_operacion,
            monto=monto,
            moneda_guardar=mon_norm.moneda_guardar,
            observacion=mon_norm.observacion,
            correo_enviado_a=unir_destinatarios_log(emails_destino_desde_objeto(cliente)),
            canal_ingreso="cobros_publico",
            log_tag_duplicate="COBROS_PUBLIC",
        )
        if err_crear or pr is None or referencia is None:
            return EnviarReporteResponse(ok=False, error=err_crear or "No se pudo registrar el reporte.")

        form_data = {
            "fecha_pago": str(fecha_pago),
            "institucion_financiera": institucion_financiera,
            "numero_operacion": numero_operacion,
            "monto": str(monto),
            "moneda": mon_norm.moneda_guardar,
            "tipo_cedula": tipo_cedula,
            "numero_cedula": numero_cedula,
        }

        from app.core.config import settings as _s

        _gemini_configured = bool((getattr(_s, "GEMINI_API_KEY", None) or "").strip())
        if _gemini_configured:
            logger.info("[COBROS_PUBLIC] Usando servicio Gemini para validar comprobante ref=%s", referencia)
        else:
            logger.info("[COBROS_PUBLIC] GEMINI_API_KEY no configurado: ref=%s irá a revisión manual", referencia)

        try:
            gemini_result = compare_form_with_image(form_data, content, filename)
            coincide = gemini_result.get("coincide_exacto", False)
            pr.gemini_coincide_exacto = "true" if coincide else "false"
            pr.gemini_comentario = gemini_result.get("comentario")
        except Exception as gemini_err:
            logger.warning(
                "[COBROS_PUBLIC] Gemini error para ref=%s tras reintentos, enviando a revisión manual: %s",
                referencia,
                str(gemini_err),
            )
            pr.gemini_coincide_exacto = "error"
            pr.gemini_comentario = f"Error Gemini (reintentado): {str(gemini_err)[:200]}"
            coincide = False

        falla_validadores = reportado_falla_validadores_cobros(db, pr)
        pr.estado = "en_revision" if falla_validadores else "aprobado"
        db.commit()

        recibo_enviado_val = None
        if not falla_validadores:
            cpr.intentar_importar_reportado_automatico(db, pr, referencia, "COBROS_PUBLIC")
            db.refresh(pr)
            background_tasks.add_task(
                _procesar_recibo_y_correo_aprobado_background,
                int(pr.id),
                str(referencia),
                int(cliente.id),
                "COBROS_PUBLIC",
            )
            db.commit()

        db.refresh(pr)
        return EnviarReporteResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje="Tu reporte de pago fue recibido exitosamente.",
            estado_reportado=(pr.estado or "").strip() or None,
            recibo_enviado=recibo_enviado_val,
        )
    except Exception as e:
        logger.exception("[COBROS_PUBLIC] Error en enviar-reporte: %s", e)
        db.rollback()
        return EnviarReporteResponse(
            ok=False,
            error="No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934.",
        )


@router.get("/recibo")
def get_recibo_publico(
    request: Request,
    pago_id: int = Query(..., description="ID del pago reportado"),
    db: Session = Depends(get_db),
):
    """
    Devuelve el PDF del recibo del pago reportado. Requiere token valido (emitido al verificar codigo en estado de cuenta).

    Publico, sin auth; la seguridad es el token (cedula + expiracion).

    Token debe venir en:
    - Header: Authorization: Bearer <token>
    """
    token_to_use = _token_bearer_only(request)
    if not token_to_use:
        raise HTTPException(
            status_code=401,
            detail="Token requerido en Authorization header.",
        )

    payload = decode_token(token_to_use)
    if not payload or payload.get("type") != "recibo":
        raise HTTPException(status_code=401, detail="Token invalido o expirado.")

    cedula_token = (payload.get("sub") or "").strip()
    if not cedula_token:
        raise HTTPException(status_code=401, detail="Token invalido.")

    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Recibo no encontrado.")

    cedula_pr = (getattr(pr, "tipo_cedula", "") or "") + (getattr(pr, "numero_cedula", "") or "")
    if cedula_pr.replace("-", "") != cedula_token.replace("-", ""):
        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")

    pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    ref = getattr(pr, "referencia_interna", "recibo") or "recibo"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{ref}.pdf"'},
    )


@router.post("/infopagos/enviar-reporte", response_model=EnviarReporteInfopagosResponse)
async def enviar_reporte_infopagos(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    fecha_pago: date = Form(...),
    institucion_financiera: str = Form(...),
    numero_operacion: str = Form(...),
    monto: float = Form(...),
    moneda: str = Form("BS"),
    comprobante: UploadFile = File(...),
    observacion: Optional[str] = Form(None),
    contact_website: Optional[str] = Form(None),
):
    """
    Registro de pago a nombre del deudor (uso interno / personal). Misma política que enviar-reporte
    (cobros público): validación con comprobante; si coincide, aprobado, importación automática
    cuando aplique, recibo al email del deudor y token de descarga para el colaborador; si no,
    estado en revisión manual en Pagos reportados — sin recibo ni correo hasta aprobación.
    """
    if not _is_internal_staff_request(request):
        raise HTTPException(
            status_code=401,
            detail="Acceso interno requerido para este endpoint.",
        )
    ip = get_client_ip(request)
    if contact_website and str(contact_website).strip():
        logger.warning("[INFOPAGOS] Honeypot activado desde IP %s", ip)
        return EnviarReporteInfopagosResponse(ok=False, error="No se pudo procesar el envío. Intente de nuevo.")

    cedula_input = f"{tipo_cedula}{numero_cedula}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        return EnviarReporteInfopagosResponse(ok=False, error=val.get("error", "Cédula inválida."))

    cedula_lookup = val.get("valor_formateado", "").replace("-", "")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return EnviarReporteInfopagosResponse(ok=False, error="La cédula no está registrada.")

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        return EnviarReporteInfopagosResponse(ok=False, error=err_pres)

    err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
        tipo_cedula=tipo_cedula,
        numero_cedula=numero_cedula,
        institucion_financiera=institucion_financiera,
        numero_operacion=numero_operacion,
        monto=monto,
        moneda=moneda,
        observacion=observacion,
    )
    if err_campos:
        return EnviarReporteInfopagosResponse(ok=False, error=err_campos)

    err_neg = cpr.validar_reglas_bs_tasa_monto_fecha(
        db,
        cedula_lookup=cedula_lookup,
        fecha_pago=fecha_pago,
        monto=monto,
        mon=mon_norm,
    )
    if err_neg:
        return EnviarReporteInfopagosResponse(ok=False, error=err_neg)

    content = await comprobante.read()
    fn_comp = comprobante.filename or "comprobante"
    ctype = cpr.mime_efectivo_comprobante_web(comprobante.content_type or "", fn_comp)
    err_file, filename = cpr.validar_adjunto_comprobante_bytes(
        content,
        ctype,
        fn_comp,
        mensaje_excel_largo=False,
    )
    if err_file:
        return EnviarReporteInfopagosResponse(ok=False, error=err_file)

    try:
        pr, referencia, err_crear = cpr.crear_pago_reportado_con_referencia_o_retry(
            db,
            content=content,
            ctype=ctype,
            filename=filename,
            cliente_nombres=(cliente.nombres or ""),
            tipo_cedula=tipo_cedula,
            numero_cedula=numero_cedula,
            fecha_pago=fecha_pago,
            institucion_financiera=institucion_financiera,
            numero_operacion=numero_operacion,
            monto=monto,
            moneda_guardar=mon_norm.moneda_guardar,
            observacion=mon_norm.observacion,
            correo_enviado_a=unir_destinatarios_log(emails_destino_desde_objeto(cliente)),
            canal_ingreso="infopagos",
            log_tag_duplicate="INFOPAGOS",
        )
        if err_crear or pr is None or referencia is None:
            return EnviarReporteInfopagosResponse(ok=False, error=err_crear or "No se pudo registrar el reporte.")

        form_data = {
            "fecha_pago": str(fecha_pago),
            "institucion_financiera": institucion_financiera,
            "numero_operacion": numero_operacion,
            "monto": str(monto),
            "moneda": mon_norm.moneda_guardar,
            "tipo_cedula": tipo_cedula,
            "numero_cedula": numero_cedula,
        }

        from app.core.config import settings as _s

        _gemini_configured = bool((getattr(_s, "GEMINI_API_KEY", None) or "").strip())
        if _gemini_configured:
            logger.info("[INFOPAGOS] Usando servicio Gemini para validar comprobante ref=%s", referencia)
        else:
            logger.info("[INFOPAGOS] GEMINI_API_KEY no configurado: ref=%s irá a revisión manual", referencia)

        try:
            gemini_result = compare_form_with_image(form_data, content, filename)
            coincide = gemini_result.get("coincide_exacto", False)
            pr.gemini_coincide_exacto = "true" if coincide else "false"
            pr.gemini_comentario = gemini_result.get("comentario")
        except Exception as gemini_err:
            logger.warning(
                "[INFOPAGOS] Gemini error para ref=%s tras reintentos, enviando a revisión manual: %s",
                referencia,
                str(gemini_err),
            )
            pr.gemini_coincide_exacto = "error"
            pr.gemini_comentario = f"Error Gemini (reintentado): {str(gemini_err)[:200]}"
            coincide = False

        falla_validadores = reportado_falla_validadores_cobros(db, pr)
        pr.estado = "en_revision" if falla_validadores else "aprobado"
        db.commit()

        if not falla_validadores:
            cpr.intentar_importar_reportado_automatico(db, pr, referencia, "INFOPAGOS")
            db.refresh(pr)
            cuotas_display = texto_cuotas_aplicadas_pago_reportado(db, pr)
            background_tasks.add_task(
                _procesar_recibo_y_correo_aprobado_background,
                int(pr.id),
                str(referencia),
                int(cliente.id),
                "INFOPAGOS",
            )

            recibo_token = create_recibo_infopagos_token(pr.id, expire_hours=2)
            db.commit()
            return EnviarReporteInfopagosResponse(
                ok=True,
                referencia_interna=referencia,
                mensaje="Pago registrado. El recibo se está generando y enviando al correo del deudor. Puede descargarlo aquí cuando esté listo.",
                recibo_descarga_token=recibo_token,
                pago_id=pr.id,
                aplicado_a_cuotas=(cuotas_display or "").strip() or RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE,
                estado_reportado="aprobado",
                recibo_listo=False,
            )

        return EnviarReporteInfopagosResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje=(
                "Reporte recibido. El comprobante quedó en revisión manual (mismo flujo que Pagos reportados). "
                "No se envía recibo al deudor ni descarga aquí hasta que cobranzas apruebe."
            ),
            recibo_descarga_token=None,
            pago_id=None,
            aplicado_a_cuotas=None,
            estado_reportado="en_revision",
            recibo_listo=None,
        )
    except Exception as e:
        logger.exception("[INFOPAGOS] Error en enviar-reporte: %s", e)
        db.rollback()
        return EnviarReporteInfopagosResponse(
            ok=False,
            error="No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934.",
        )


@router.get("/infopagos/recibo")
def get_recibo_infopagos(
    request: Request,
    pago_id: int = Query(..., description="ID del pago reportado"),
    db: Session = Depends(get_db),
):
    """
    Devuelve el PDF del recibo del pago registrado por Infopagos. Requiere el token devuelto
    en la respuesta de enviar-reporte (válido 2 horas) para que el colaborador descargue el recibo.

    Token debe venir en:
    - Header: Authorization: Bearer <token>
    """
    _validar_token_recibo_infopagos(request, pago_id)

    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Recibo no encontrado.")

    pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    ref = getattr(pr, "referencia_interna", "recibo") or "recibo"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="recibo_{ref}.pdf"'},
    )


@router.get("/infopagos/recibo-status", response_model=ReciboInfopagosStatusResponse)
def get_recibo_infopagos_status(
    request: Request,
    pago_id: int = Query(..., description="ID del pago reportado"),
    db: Session = Depends(get_db),
):
    """
    Estado liviano para polling de UI:
    - `recibo_listo=true` cuando `recibo_pdf` ya está persistido.
    """
    _validar_token_recibo_infopagos(request, pago_id)

    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")

    listo = bool(getattr(pr, "recibo_pdf", None))
    estado = (getattr(pr, "estado", "") or "").strip() or None
    msg = "Recibo listo para descarga." if listo else "Procesando recibo en segundo plano."
    return ReciboInfopagosStatusResponse(
        ok=True,
        pago_id=int(pago_id),
        recibo_listo=listo,
        estado_reportado=estado,
        mensaje=msg,
    )
