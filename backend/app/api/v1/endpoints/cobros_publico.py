"""
Endpoints PÚBLICOS del módulo Cobros (formulario de reporte de pago).
Sin autenticación. Incluye: rate limiting por IP, honeypot anti-bot, validación de archivo por magic bytes.
"""
import os
import re
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.cobros_public_rate_limit import (
    get_client_ip,
    check_rate_limit_validar_cedula,
    check_rate_limit_enviar_reporte,
)
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago_reportado import PagoReportado
from app.api.v1.endpoints.validadores import validate_cedula
# Servicio Gemini del sistema (mismo GEMINI_API_KEY y GEMINI_MODEL que Pagos Gmail / health)
from app.services.pagos_gmail.gemini_service import compare_form_with_image
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado, WHATSAPP_LINK
from app.core.email import send_email

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[])  # Sin get_current_user

# Tipos de archivo permitidos para comprobante
ALLOWED_COMPROBANTE_TYPES = {"image/jpeg", "image/jpg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Magic bytes (inicio de archivo) para validar tipo real
MAGIC_JPEG = bytes([0xFF, 0xD8, 0xFF])
MAGIC_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
MAGIC_PDF = bytes([0x25, 0x50, 0x44, 0x46])  # %PDF


def _sanitize_filename(name: str) -> str:
    """Elimina path traversal y caracteres no seguros."""
    if not name or not name.strip():
        return "comprobante"
    name = name.strip()
    name = os.path.basename(name)  # sin rutas
    name = re.sub(r"[^\w.\-]", "_", name)[:80]
    return name or "comprobante"


def _validate_file_magic(content: bytes, content_type: str) -> bool:
    """Verifica que el contenido coincida con el tipo declarado (anti-spoofing)."""
    if len(content) < 8:
        return False
    ctype = (content_type or "").lower()
    if "jpeg" in ctype or "jpg" in ctype:
        return content[:3] == MAGIC_JPEG
    if "png" in ctype:
        return content[:8] == MAGIC_PNG
    if "pdf" in ctype:
        return content[:4] == MAGIC_PDF
    return False


def _normalize_cedula_for_lookup(tipo: str, numero: str) -> str:
    """Cédula para búsqueda en BD: V12345678 (sin guión)."""
    t = (tipo or "").strip().upper()
    n = (numero or "").strip()
    if not n:
        return ""
    return f"{t}{n}"


def _mask_email(email: str) -> str:
    """Enmascara correo: r***z@gmail.com"""
    if not email or "@" not in email:
        return "***@***"
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _generar_referencia_interna(db: Session) -> str:
    """Formato RPC-YYYYMMDD-XXXXX con XXXXX secuencial del día."""
    hoy = date.today().strftime("%Y%m%d")
    prefix = f"RPC-{hoy}-"
    row = db.execute(
        select(func.count(PagoReportado.id)).where(PagoReportado.referencia_interna.like(f"{prefix}%"))
    ).scalar()
    row = row or 0
    seq = row + 1
    return f"{prefix}{seq:05d}"


class ValidarCedulaResponse(BaseModel):
    ok: bool
    nombre: Optional[str] = None
    """Correo completo para que el cliente lo compruebe en pantalla (no enmascarado)."""
    email: Optional[str] = None
    email_enmascarado: Optional[str] = None
    error: Optional[str] = None


class EnviarReporteResponse(BaseModel):
    ok: bool
    referencia_interna: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None


# Longitud máxima para evitar abuso (cédula venezolana: V/E/J + hasta 11 dígitos)
MAX_CEDULA_LENGTH = 20


@router.get("/validar-cedula", response_model=ValidarCedulaResponse)
def validar_cedula_publico(
    request: Request,
    cedula: str,
    db: Session = Depends(get_db),
):
    """
    Valida cédula (formato V/E/J + dígitos) y verifica si tiene préstamo.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.
    """
    ip = get_client_ip(request)
    check_rate_limit_validar_cedula(ip)
    if not cedula or not cedula.strip():
        return ValidarCedulaResponse(ok=False, error="Ingrese el número de cédula.")
    if len(cedula.strip()) > MAX_CEDULA_LENGTH:
        return ValidarCedulaResponse(ok=False, error="Datos inválidos.")
    result = validate_cedula(cedula.strip())
    if not result.get("valido"):
        return ValidarCedulaResponse(ok=False, error=result.get("error", "Cédula inválida."))
    # Valor formateado V-12345678 → para lookup en BD usamos V12345678
    valor = result.get("valor_formateado", "")
    cedula_lookup = valor.replace("-", "") if valor else ""
    if not cedula_lookup:
        return ValidarCedulaResponse(ok=False, error="Formato de cédula no reconocido.")
    # Búsqueda que acepta cédula con o sin guión en BD (normalizar para comparar)
    cliente = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return ValidarCedulaResponse(ok=False, error="La cédula ingresada no se encuentra registrada en nuestro sistema.")
    # ¿Tiene préstamo? (cualquier préstamo asociado al cliente)
    prestamo = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente.id).limit(1)
    ).scalars().first()
    if not prestamo:
        return ValidarCedulaResponse(ok=False, error="La cédula no tiene un préstamo asociado en nuestro sistema.")
    nombre = (cliente.nombres or "").strip()
    email = (cliente.email or "").strip()
    return ValidarCedulaResponse(
        ok=True,
        nombre=nombre,
        email=email or None,
        email_enmascarado=_mask_email(email),
    )


# Honeypot: campo oculto que no debe rellenar el usuario. Si viene con valor = bot, rechazar.
HONEYPOT_FIELD = "contact_website"


@router.post("/enviar-reporte", response_model=EnviarReporteResponse)
async def enviar_reporte_publico(
    request: Request,
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
    contact_website: Optional[str] = Form(None),  # honeypot: debe estar vacío
):
    """
    Recibe el reporte de pago del formulario público.
    Rate limit: 5 envíos/hora por IP. Honeypot anti-bot. Validación de archivo por magic bytes.
    """
    ip = get_client_ip(request)
    check_rate_limit_enviar_reporte(ip)
    # Honeypot: si un bot rellenó el campo oculto, rechazar sin revelar motivo
    if contact_website and str(contact_website).strip():
        logger.warning("[COBROS_PUBLIC] Honeypot activado desde IP %s", ip)
        return EnviarReporteResponse(ok=False, error="No se pudo procesar el envío. Intente de nuevo.")
    # Validar cédula de nuevo
    cedula_input = f"{tipo_cedula}{numero_cedula}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        return EnviarReporteResponse(ok=False, error=val.get("error", "Cédula inválida."))
    cedula_lookup = val.get("valor_formateado", "").replace("-", "")
    # Búsqueda que acepta cédula con o sin guión en BD
    cliente = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente:
        return EnviarReporteResponse(ok=False, error="La cédula no está registrada.")
    prestamo = db.execute(select(Prestamo).where(Prestamo.cliente_id == cliente.id).limit(1)).scalars().first()
    if not prestamo:
        return EnviarReporteResponse(ok=False, error="No tiene préstamo asociado.")

    # Límites de longitud para evitar inyección o abuso
    if len(tipo_cedula.strip()) > 2 or len(numero_cedula.strip()) > 13:
        return EnviarReporteResponse(ok=False, error="Datos inválidos.")
    if len(institucion_financiera.strip()) > 100 or len(numero_operacion.strip()) > 100:
        return EnviarReporteResponse(ok=False, error="Datos inválidos.")
    if observacion and len(observacion) > 300:
        observacion = observacion[:300]
    if (moneda or "BS").strip().upper() not in ("BS", "USD"):
        return EnviarReporteResponse(ok=False, error="Moneda no válida.")
    if monto <= 0 or monto > 999_999_999.99:
        return EnviarReporteResponse(ok=False, error="Monto no válido.")
    if fecha_pago > date.today():
        return EnviarReporteResponse(ok=False, error="La fecha de pago no puede ser futura.")

    # Validar archivo
    content = await comprobante.read()
    if len(content) > MAX_FILE_SIZE:
        return EnviarReporteResponse(ok=False, error="El comprobante no puede superar 5 MB.")
    if len(content) < 4:
        return EnviarReporteResponse(ok=False, error="El archivo está vacío o no es válido.")
    ctype = (comprobante.content_type or "").lower()
    if ctype not in ALLOWED_COMPROBANTE_TYPES:
        return EnviarReporteResponse(ok=False, error="Solo se permiten archivos JPG, PNG o PDF.")
    if not _validate_file_magic(content, ctype):
        return EnviarReporteResponse(ok=False, error="El archivo no corresponde a una imagen o PDF válido.")
    filename = _sanitize_filename(comprobante.filename or "comprobante")

    try:
        referencia = _generar_referencia_interna(db)
        nombres = (cliente.nombres or "").strip()
        apellidos = ""  # clientes tiene solo nombres; si hay apellido en otro campo se puede mapear
        if " " in nombres:
            parts = nombres.split(None, 1)
            nombres = parts[0]
            apellidos = parts[1] if len(parts) > 1 else ""

        pr = PagoReportado(
            referencia_interna=referencia,
            nombres=nombres,
            apellidos=apellidos,
            tipo_cedula=tipo_cedula.strip().upper(),
            numero_cedula=numero_cedula.strip(),
            fecha_pago=fecha_pago,
            institucion_financiera=institucion_financiera.strip()[:100],
            numero_operacion=numero_operacion.strip()[:100],
            monto=monto,
            moneda=(moneda or "BS").strip()[:10],
            comprobante=content,
            comprobante_nombre=filename[:255],
            comprobante_tipo=ctype,
            ruta_comprobante=None,
            observacion=observacion[:300] if observacion else None,
            correo_enviado_a=cliente.email,
            estado="pendiente",
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)

        # Gemini: comparar formulario vs imagen del comprobante
        form_data = {
            "fecha_pago": str(fecha_pago),
            "institucion_financiera": institucion_financiera,
            "numero_operacion": numero_operacion,
            "monto": str(monto),
            "moneda": moneda,
            "tipo_cedula": tipo_cedula,
            "numero_cedula": numero_cedula,
        }
        from app.core.config import settings as _s
        _gemini_configured = bool((getattr(_s, "GEMINI_API_KEY", None) or "").strip())
        if _gemini_configured:
            logger.info("[COBROS_PUBLIC] Usando servicio Gemini para validar comprobante ref=%s", referencia)
        else:
            logger.info("[COBROS_PUBLIC] GEMINI_API_KEY no configurado: ref=%s irá a revisión manual", referencia)
        gemini_result = compare_form_with_image(form_data, content, filename)
        coincide = gemini_result.get("coincide_exacto", False)
        pr.gemini_coincide_exacto = "true" if coincide else "false"
        pr.gemini_comentario = gemini_result.get("comentario")

        if coincide:
            pr.estado = "aprobado"
            pdf_bytes = generar_recibo_pago_reportado(
                referencia_interna=referencia,
                nombres=pr.nombres,
                apellidos=pr.apellidos,
                tipo_cedula=pr.tipo_cedula,
                numero_cedula=pr.numero_cedula,
                institucion_financiera=pr.institucion_financiera,
                monto=f"{pr.monto} {pr.moneda}",
                numero_operacion=pr.numero_operacion,
            )
            pr.recibo_pdf = pdf_bytes
            to_email = (cliente.email or "").strip()
            if to_email:
                body = (
                    f"Se ha recibido su reporte de pago.\n\n"
                    f"Número de referencia: {referencia}\n\n"
                    f"El recibo se adjunta. Si necesita información adicional, contáctenos por WhatsApp: {WHATSAPP_LINK}\n\n"
                    "RapiCredit C.A."
                )
                ok_mail, err_mail = send_email(
                    [to_email],
                    f"Recibo de reporte de pago #{referencia}",
                    body,
                    attachments=[(f"recibo_{referencia}.pdf", pdf_bytes)],
                )
                if not ok_mail:
                    logger.error(
                        "[COBROS_PUBLIC] Recibo aprobado ref=%s: correo NO enviado a %s. Error: %s.",
                        referencia, to_email, err_mail or "desconocido",
                    )
        else:
            pr.estado = "en_revision"

        db.commit()

        return EnviarReporteResponse(
            ok=True,
            referencia_interna=referencia,
            mensaje="Tu reporte de pago fue recibido exitosamente.",
        )
    except Exception as e:
        logger.exception("[COBROS_PUBLIC] Error en enviar-reporte: %s", e)
        db.rollback()
        return EnviarReporteResponse(
            ok=False,
            error="No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934.",
        )
