"""

Endpoints PÚBLICOS del módulo Cobros (formulario de reporte de pago).

SEGURIDAD: Sin autenticación (router sin get_current_user). No permitir acceso a datos

de otros clientes ni a rutas internas. Incluye: rate limiting por IP, honeypot anti-bot,

validación de archivo por magic bytes. Solo expone: validar-cedula (nombre/email del cliente

consultado) y enviar-reporte (crear PagoReportado para esa cédula).

"""

import os

import re

import logging

from datetime import date, datetime

from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query

from fastapi.responses import Response

from pydantic import BaseModel

from sqlalchemy.orm import Session

from sqlalchemy import select, func, text

from sqlalchemy.exc import IntegrityError



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

from app.services.cobros.cedula_reportar_bs_service import cedula_autorizada_para_bs

# Servicio Gemini del sistema (mismo GEMINI_API_KEY y GEMINI_MODEL que Pagos Gmail / health)

from app.services.pagos_gmail.gemini_service import compare_form_with_image

from app.services.cobros.recibo_pdf import (
    generar_recibo_pago_reportado,
    RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE,
    WHATSAPP_LINK,
)
from app.services.tasa_cambio_service import (
    obtener_tasa_por_fecha,
    fecha_hoy_caracas,
)

from app.services.cobros.recibo_cuotas_lookup import texto_cuotas_aplicadas_pago_reportado

from app.core.email import send_email

from app.core.security import decode_token, create_recibo_infopagos_token



logger = logging.getLogger(__name__)




def _validar_monto_reporte_publico(monto: float, moneda_upper: str) -> Optional[str]:
    """Si moneda BS, rango Bs autorizado; si USD/USDT, limite general. None = OK."""
    if moneda_upper == "BS":
        if monto < MIN_MONTO_BS_REPORTAR or monto > MAX_MONTO_BS_REPORTAR:
            return (
                f"Monto en bolivares debe estar entre "
                f"{MIN_MONTO_BS_REPORTAR:,.0f} y {MAX_MONTO_BS_REPORTAR:,.0f} Bs. "
                "(cedula autorizada para pagos en bolivares)."
            )
        return None
    if monto <= 0 or monto > 999_999_999.99:
        return "Monto no valido."
    return None

def _referencia_display(referencia_interna: str) -> str:

    ref = (referencia_interna or "").strip()

    if not ref:

        return "-"

    return ref if ref.startswith("#") else f"#{ref}"





def _monto_con_moneda(pr: PagoReportado) -> str:

    monto = getattr(pr, "monto", "")

    moneda = (getattr(pr, "moneda", "") or "").strip()

    monto_str = str(monto).strip()

    return f"{monto_str} {moneda}".strip()





def _generar_recibo_desde_pago(db: Session, pr: PagoReportado) -> bytes:

    cuotas_txt = texto_cuotas_aplicadas_pago_reportado(db, pr)

    saldo_init, saldo_fin, num_cuota = None, None, None

    try:

        from app.services.cobros.recibo_cuotas_lookup import obtener_saldos_cuota_aplicada

        saldo_init, saldo_fin, num_cuota = obtener_saldos_cuota_aplicada(db, pr)

    except Exception:

        pass

    fecha_pago_display = pr.fecha_pago.strftime("%d/%m/%Y") if pr.fecha_pago else None

    moneda = (pr.moneda or "BS").strip().upper()

    tasa_cambio = None

    if moneda == "BS" and pr.fecha_pago:

        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)

        tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None

    elif moneda == "BS":

        tasa_cambio = None

    fecha_reporte_aprobacion_display = None

    u = getattr(pr, "updated_at", None)

    if u and hasattr(u, "strftime"):

        fecha_reporte_aprobacion_display = u.strftime("%d/%m/%Y %H:%M")

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

        fecha_reporte_aprobacion_display=fecha_reporte_aprobacion_display,

        aplicado_a_cuotas=cuotas_txt,

        saldo_inicial=saldo_init,

        saldo_final=saldo_fin,

        numero_cuota=num_cuota,

        fecha_pago_display=fecha_pago_display,

        moneda=moneda,

        tasa_cambio=tasa_cambio,

    )





def _prestamos_aprobados_del_cliente(db: Session, cliente_id: int) -> list:

    """
    Misma regla que importar reportados a pagos: solo préstamos en estado APROBADO.

    Usa solo la columna id vía Core (Prestamo.__table__) para no disparar SELECT del mapper
    completo; si en BD no existe prestamos.fecha_liquidado (migracion pendiente), ORM fallaria.
    Los llamadores solo usan len() de la lista.
    """

    t = Prestamo.__table__

    stmt = (

        select(t.c.id)

        .where(t.c.cliente_id == cliente_id, t.c.estado == "APROBADO")

        .order_by(t.c.id)

    )

    return [row[0] for row in db.execute(stmt).all()]





def _error_si_no_puede_reportar_en_web(prestamos_aprobados: list) -> Optional[str]:

    """

    El formulario web asigna el pago a un único préstamo APROBADO. Si hay 0 o >1, coherente con importación a pagos.

    """

    if len(prestamos_aprobados) == 0:

        return (

            "No tiene un crédito en estado APROBADO para reportar pagos en línea. "

            "Si su crédito está en otro estado o ya fue liquidado, contacte a cobranza."

        )

    if len(prestamos_aprobados) > 1:

        return (

            "Su cédula tiene más de un crédito aprobado activo; el reporte en línea no está disponible. "

            "Contacte a RapiCredit / cobranza para indicar a qué crédito corresponde el pago."

        )

    return None





def _intentar_importar_reportado_automatico(

    db: Session,

    pr: PagoReportado,

    referencia: str,

    log_tag: str,

) -> None:

    """

    Si el reporte quedó en estado aprobado: crea Pago (mismas reglas que importar-desde-cobros),

    aplica a cuotas y marca el reporte como importado. Fallos solo en log (no rompe la respuesta al cliente).

    """

    if pr is None or getattr(pr, "estado", None) != "aprobado":

        return

    try:

        from app.models.pago import Pago

        from app.api.v1.endpoints.pagos import importar_un_pago_reportado_a_pagos, _aplicar_pago_a_cuotas_interno
        from app.services.cobros.pago_reportado_documento import claves_documento_pago_para_reportado

        db.refresh(pr)

        claves_pr = claves_documento_pago_para_reportado(pr)

        docs_bd: set[str] = set()

        if claves_pr:

            rows = db.execute(

                select(Pago.numero_documento).where(Pago.numero_documento.in_(claves_pr))

            ).scalars().all()

            docs_bd = {str(x) for x in rows if x}

        usuario = "infopagos@rapicredit" if log_tag == "INFOPAGOS" else "cobros-publico@rapicredit"

        res = importar_un_pago_reportado_a_pagos(

            db,

            pr,

            usuario_email=usuario,

            documentos_ya_en_bd=docs_bd,

            docs_en_lote=set(),

            registrar_error_en_tabla=False,

        )

        if not res.get("ok"):

            logger.warning("[%s] Auto-import ref=%s omitido: %s", log_tag, referencia, res.get("error"))

            return

        pago = res["pago"]

        cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)

        if cc > 0 or cp > 0:

            pago.estado = "PAGADO"

        pr.estado = "importado"

        db.commit()

        logger.info("[%s] Auto-import OK ref=%s pago_id=%s", log_tag, referencia, getattr(pago, "id", None))

    except Exception as e:

        logger.warning("[%s] Auto-import fallo ref=%s: %s", log_tag, referencia, e)

        try:

            db.rollback()

        except Exception:

            pass







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

    """Formato RPC-YYYYMMDD-XXXXX con XXXXX secuencial del dia (atomico por tabla)."""

    try:

        db.execute(text("""

            CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (

                fecha DATE PRIMARY KEY,

                siguiente INTEGER NOT NULL DEFAULT 1

            )

        """))

    except Exception:

        db.rollback()

        raise

    # Sincronizar con referencias ya existentes hoy (p. ej. tras migrar de COUNT a tabla)

    try:

        db.execute(text("""

            INSERT INTO secuencia_referencia_cobros (fecha, siguiente)

            SELECT CURRENT_DATE, COALESCE((

                SELECT MAX(CAST(SUBSTRING(referencia_interna FROM 14 FOR 5) AS INTEGER))

                FROM pagos_reportados

                WHERE referencia_interna LIKE 'RPC-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-%'

            ), 0)

            ON CONFLICT (fecha) DO NOTHING

        """))

    except Exception:

        db.rollback()

        raise

    row = db.execute(text("""

        INSERT INTO secuencia_referencia_cobros (fecha, siguiente)

        VALUES (CURRENT_DATE, 1)

        ON CONFLICT (fecha) DO UPDATE SET siguiente = secuencia_referencia_cobros.siguiente + 1

        RETURNING siguiente

    """)).scalar_one()

    hoy = fecha_hoy_caracas().strftime("%Y%m%d")

    return f"RPC-{hoy}-{row:05d}"





class ValidarCedulaResponse(BaseModel):

    ok: bool

    nombre: Optional[str] = None

    """Correo completo para que el cliente lo compruebe en pantalla (no enmascarado)."""

    email: Optional[str] = None

    email_enmascarado: Optional[str] = None

    error: Optional[str] = None

    """True si esta cédula puede reportar pagos en Bolívares (Bs) en cobros/infopagos."""

    puede_reportar_bs: Optional[bool] = None





class EnviarReporteResponse(BaseModel):

    ok: bool

    referencia_interna: Optional[str] = None

    mensaje: Optional[str] = None

    error: Optional[str] = None





class EnviarReporteInfopagosResponse(BaseModel):

    """Respuesta de Infopagos. Token y recibo solo si quedo aprobado (misma politica que cobros publico)."""

    ok: bool

    referencia_interna: Optional[str] = None

    mensaje: Optional[str] = None

    error: Optional[str] = None

    recibo_descarga_token: Optional[str] = None

    pago_id: Optional[int] = None

    estado_reportado: Optional[str] = None





# Longitud máxima para evitar abuso (cédula venezolana: V/E/J + hasta 11 dígitos)

MAX_CEDULA_LENGTH = 20



# Mensaje de rechazo cuando intentan reportar en Bs sin estar en la lista (el usuario ve Observación: Bolívares)

ERROR_TASA_BS_NO_REGISTRADA = (
    "No hay tasa de cambio oficial para la fecha de pago {fp}. "
    "Un administrador debe registrarla en Administracion > Tasas de cambio para esa fecha "
    "antes de reportar en bolivares."
)


ERROR_BS_NO_AUTORIZADO = "Observación: Bolívares. No puede enviar pago en Bolívares; su cédula no está autorizada. Use USD."

# Monto en bolivares (solo cedulas en cedulas_reportar_bs): 1 a 10_000_000 Bs.
MIN_MONTO_BS_REPORTAR = 1.0
MAX_MONTO_BS_REPORTAR = 10_000_000.0






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

    Sin límite cuando origen=infopagos (ruta /pagos/infopagos, uso interno).

    """

    ip = get_client_ip(request)

    if (origen or "").strip().lower() != "infopagos":

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

    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)

    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)

    if err_pres:

        return ValidarCedulaResponse(ok=False, error=err_pres)

    # ¿Puede reportar en Bs? (lista cargada desde Excel en /pagos/pagos)

    puede_bs = cedula_autorizada_para_bs(db, cedula_lookup)

    nombre = (cliente.nombres or "").strip()

    email = (cliente.email or "").strip()

    return ValidarCedulaResponse(

        ok=True,

        nombre=nombre,

        email=email or None,

        email_enmascarado=_mask_email(email),

        puede_reportar_bs=puede_bs,

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

    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)

    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)

    if err_pres:

        return EnviarReporteResponse(ok=False, error=err_pres)



    # Límites de longitud para evitar inyección o abuso

    if len(tipo_cedula.strip()) > 2 or len(numero_cedula.strip()) > 13:

        return EnviarReporteResponse(ok=False, error="Datos inválidos.")

    if len(institucion_financiera.strip()) > 100 or len(numero_operacion.strip()) > 100:

        return EnviarReporteResponse(ok=False, error="Datos inválidos.")

    if observacion and len(observacion) > 300:

        observacion = observacion[:300]

    if (moneda or "BS").strip().upper() not in ("BS", "USD", "USDT"):

        return EnviarReporteResponse(ok=False, error="Moneda no válida.")

    moneda_upper = (moneda or "BS").strip().upper()

    # USDT = Dólares = USD = $; normalizar a USD para guardar

    moneda_guardar = "USD" if moneda_upper in ("USD", "USDT") else moneda_upper

    if moneda_upper == "BS":

        if not cedula_autorizada_para_bs(db, cedula_lookup):

            return EnviarReporteResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

        tasa_row = obtener_tasa_por_fecha(db, fecha_pago)

        if tasa_row is None:

            return EnviarReporteResponse(

                ok=False,

                error=ERROR_TASA_BS_NO_REGISTRADA.format(

                    fp=fecha_pago.strftime("%d/%m/%Y"),

                ),

            )

    err_monto = _validar_monto_reporte_publico(monto, moneda_upper)

    if err_monto:

        return EnviarReporteResponse(ok=False, error=err_monto)

    if fecha_pago > fecha_hoy_caracas():

        return EnviarReporteResponse(ok=False, error="La fecha de pago no puede ser futura.")



    # Validar archivo

    content = await comprobante.read()

    if len(content) > MAX_FILE_SIZE:

        return EnviarReporteResponse(ok=False, error="El comprobante no puede superar 5 MB.")

    if len(content) < 4:

        return EnviarReporteResponse(ok=False, error="El archivo está vacío o no es válido.")

    ctype = (comprobante.content_type or "").lower()

    if "excel" in ctype or "spreadsheet" in ctype or "xls" in ctype:

        return EnviarReporteResponse(ok=False, error="El comprobante debe ser PDF o imagen (JPG, PNG). No se permiten archivos Excel.")



    if ctype not in ALLOWED_COMPROBANTE_TYPES:

        return EnviarReporteResponse(ok=False, error="Solo se permiten archivos JPG, PNG o PDF.")

    if not _validate_file_magic(content, ctype):

        return EnviarReporteResponse(ok=False, error="El archivo no corresponde a una imagen o PDF válido.")

    filename = _sanitize_filename(comprobante.filename or "comprobante")





    # Cada envio genera su propia referencia (RPC-YYYYMMDD-XXXXX). La misma persona puede subir varios

    # pagos; si un envio no completa el proceso (recibo/email), puede reintentar y obtiene nueva referencia.



    try:

        pr = None

        referencia = None

        for _attempt in range(2):

            try:

                try:

                    hoy_int = int(fecha_hoy_caracas().strftime("%Y%m%d"))

                    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": hoy_int})

                except Exception:

                    db.rollback()  # Dejar transacción limpia; continuar sin lock

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

                    moneda=moneda_guardar[:10],

                    comprobante=content,

                    comprobante_nombre=filename[:255],

                    comprobante_tipo=ctype,

                    ruta_comprobante=None,

                    observacion=observacion[:300] if observacion else None,

                    correo_enviado_a=cliente.email,

                    estado="pendiente",

                    canal_ingreso="cobros_publico",

                )

                db.add(pr)

                db.commit()

                db.refresh(pr)

                break

            except IntegrityError as ie:

                db.rollback()

                err_msg = str(ie.orig) if getattr(ie, "orig", None) else str(ie)

                if _attempt == 0 and "referencia_interna" in err_msg:

                    logger.warning("[COBROS_PUBLIC] Duplicate referencia_interna, retrying once: %s", ie)

                    continue

                return EnviarReporteResponse(

                    ok=False,

                    error="Ya existe un reporte con esa referencia. Si enviaste el formulario dos veces, no hace falta volver a enviar. Si no, intenta de nuevo en un momento.",

                )



        # Gemini: comparar formulario vs imagen del comprobante

        form_data = {

            "fecha_pago": str(fecha_pago),

            "institucion_financiera": institucion_financiera,

            "numero_operacion": numero_operacion,

            "monto": str(monto),

            # USDT se normaliza a USD para BD y para Gemini (misma moneda)
            "moneda": moneda_guardar,

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

        else:

            pr.estado = "en_revision"



        db.commit()

        if coincide:

            _intentar_importar_reportado_automatico(db, pr, referencia, "COBROS_PUBLIC")

            db.refresh(pr)

            pdf_bytes = _generar_recibo_desde_pago(db, pr)

            pr.recibo_pdf = pdf_bytes

            to_email = (cliente.email or "").strip()

            if to_email:

                body = (

                    f"Se ha recibido su reporte de pago.\n\n"

                    f"Número de referencia: {_referencia_display(referencia)}\n\n"

                    f"El recibo se adjunta. Si necesita información adicional, contáctenos por WhatsApp: {WHATSAPP_LINK}\n\n"

                    "RapiCredit C.A."

                )

                ok_mail, err_mail = send_email(

                    [to_email],

                    f"Recibo de reporte de pago {_referencia_display(referencia)}",

                    body,

                    attachments=[(f"recibo_{referencia}.pdf", pdf_bytes)],

                    servicio="cobros",

                    respetar_destinos_manuales=True,

                )

                if not ok_mail:

                    logger.error(

                        "[COBROS_PUBLIC] Recibo aprobado ref=%s: correo NO enviado a %s. Error: %s.",

                        referencia, to_email, err_mail or "desconocido",

                    )

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



@router.get("/recibo")

def get_recibo_publico(

    token: str = Query(..., description="Token de sesion estado de cuenta"),

    pago_id: int = Query(..., description="ID del pago reportado"),

    db: Session = Depends(get_db),

):

    """

    Devuelve el PDF del recibo del pago reportado. Requiere token valido (emitido al verificar codigo en estado de cuenta).

    Publico, sin auth; la seguridad es el token (cedula + expiracion).

    """

    payload = decode_token(token)

    if not payload or payload.get("type") != "recibo":

        raise HTTPException(status_code=401, detail="Token invalido o expirado.")

    cedula_token = (payload.get("sub") or "").strip()

    if not cedula_token:

        raise HTTPException(status_code=401, detail="Token invalido.")

    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()

    if not pr:

        raise HTTPException(status_code=404, detail="Recibo no encontrado.")

    pr = pr[0] if hasattr(pr, "__getitem__") else pr

    cedula_pr = (getattr(pr, "tipo_cedula", "") or "") + (getattr(pr, "numero_cedula", "") or "")

    if cedula_pr.replace("-", "") != cedula_token.replace("-", ""):

        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")

    pdf_bytes = _generar_recibo_desde_pago(db, pr)

    pr.recibo_pdf = pdf_bytes

    db.commit()

    ref = getattr(pr, "referencia_interna", "recibo") or "recibo"

    return Response(

        content=bytes(pdf_bytes),

        media_type="application/pdf",

        headers={"Content-Disposition": f'inline; filename="recibo_{ref}.pdf"'},

    )





# --- Infopagos: mismo flujo que cobros público, sin token para el deudor; recibo al email y descarga para el colaborador ---



@router.post("/infopagos/enviar-reporte", response_model=EnviarReporteInfopagosResponse)

async def enviar_reporte_infopagos(

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

    contact_website: Optional[str] = Form(None),

):

    """

    Registro de pago a nombre del deudor (uso interno / personal). Misma política que enviar-reporte

    (cobros público): validación con comprobante; si coincide, aprobado, importación automática

    cuando aplique, recibo al email del deudor y token de descarga para el colaborador; si no,

    estado en revisión manual en Pagos reportados — sin recibo ni correo hasta aprobación.

    """

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

        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)

    ).scalars().first()

    if not cliente:

        return EnviarReporteInfopagosResponse(ok=False, error="La cédula no está registrada.")

    prestamos_aprob = _prestamos_aprobados_del_cliente(db, cliente.id)

    err_pres = _error_si_no_puede_reportar_en_web(prestamos_aprob)

    if err_pres:

        return EnviarReporteInfopagosResponse(ok=False, error=err_pres)

    if len(tipo_cedula.strip()) > 2 or len(numero_cedula.strip()) > 13:

        return EnviarReporteInfopagosResponse(ok=False, error="Datos inválidos.")

    if len(institucion_financiera.strip()) > 100 or len(numero_operacion.strip()) > 100:

        return EnviarReporteInfopagosResponse(ok=False, error="Datos inválidos.")

    if observacion and len(observacion) > 300:

        observacion = observacion[:300]

    if (moneda or "BS").strip().upper() not in ("BS", "USD", "USDT"):

        return EnviarReporteInfopagosResponse(ok=False, error="Moneda no válida.")

    moneda_upper = (moneda or "BS").strip().upper()

    # USDT = Dólares = USD = $; normalizar a USD para guardar

    moneda_guardar = "USD" if moneda_upper in ("USD", "USDT") else moneda_upper

    if moneda_upper == "BS":

        if not cedula_autorizada_para_bs(db, cedula_lookup):

            return EnviarReporteInfopagosResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

        tasa_row = obtener_tasa_por_fecha(db, fecha_pago)

        if tasa_row is None:

            return EnviarReporteInfopagosResponse(

                ok=False,

                error=ERROR_TASA_BS_NO_REGISTRADA.format(

                    fp=fecha_pago.strftime("%d/%m/%Y"),

                ),

            )

    err_monto = _validar_monto_reporte_publico(monto, moneda_upper)

    if err_monto:

        return EnviarReporteInfopagosResponse(ok=False, error=err_monto)

    if fecha_pago > fecha_hoy_caracas():

        return EnviarReporteInfopagosResponse(ok=False, error="La fecha de pago no puede ser futura.")

    content = await comprobante.read()

    if len(content) > MAX_FILE_SIZE:

        return EnviarReporteInfopagosResponse(ok=False, error="El comprobante no puede superar 5 MB.")

    if len(content) < 4:

        return EnviarReporteInfopagosResponse(ok=False, error="El archivo está vacío o no es válido.")

    ctype = (comprobante.content_type or "").lower()

    if "excel" in ctype or "spreadsheet" in ctype or "xls" in ctype:

        return EnviarReporteInfopagosResponse(ok=False, error="El comprobante debe ser PDF o imagen (JPG, PNG).")

    if ctype not in ALLOWED_COMPROBANTE_TYPES:

        return EnviarReporteInfopagosResponse(ok=False, error="Solo se permiten archivos JPG, PNG o PDF.")

    if not _validate_file_magic(content, ctype):

        return EnviarReporteInfopagosResponse(ok=False, error="El archivo no corresponde a una imagen o PDF válido.")

    filename = _sanitize_filename(comprobante.filename or "comprobante")

    try:

        pr = None

        referencia = None

        for _attempt in range(2):

            try:

                try:

                    hoy_int = int(fecha_hoy_caracas().strftime("%Y%m%d"))

                    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": hoy_int})

                except Exception:

                    db.rollback()

                referencia = _generar_referencia_interna(db)

                nombres = (cliente.nombres or "").strip()

                apellidos = ""

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

                    moneda=moneda_guardar[:10],

                    comprobante=content,

                    comprobante_nombre=filename[:255],

                    comprobante_tipo=ctype,

                    ruta_comprobante=None,

                    observacion=observacion[:300] if observacion else None,

                    correo_enviado_a=cliente.email,

                    estado="pendiente",

                    canal_ingreso="infopagos",

                )

                db.add(pr)

                db.commit()

                db.refresh(pr)

                break

            except IntegrityError as ie:

                db.rollback()

                err_msg = str(ie.orig) if getattr(ie, "orig", None) else str(ie)

                if _attempt == 0 and "referencia_interna" in err_msg:

                    continue

                return EnviarReporteInfopagosResponse(

                    ok=False,

                    error="Ya existe un reporte con esa referencia. Intente de nuevo en un momento.",

                )

        form_data = {

            "fecha_pago": str(fecha_pago),

            "institucion_financiera": institucion_financiera,

            "numero_operacion": numero_operacion,

            "monto": str(monto),

            # USDT se normaliza a USD para BD y para Gemini (misma moneda)
            "moneda": moneda_guardar,

            "tipo_cedula": tipo_cedula,

            "numero_cedula": numero_cedula,

        }

        from app.core.config import settings as _s

        _gemini_configured = bool((getattr(_s, "GEMINI_API_KEY", None) or "").strip())

        if _gemini_configured:

            logger.info("[INFOPAGOS] Usando servicio Gemini para validar comprobante ref=%s", referencia)

        else:

            logger.info(

                "[INFOPAGOS] GEMINI_API_KEY no configurado: ref=%s irá a revisión manual",

                referencia,

            )

        gemini_result = compare_form_with_image(form_data, content, filename)

        coincide = gemini_result.get("coincide_exacto", False)

        pr.gemini_coincide_exacto = "true" if coincide else "false"

        pr.gemini_comentario = gemini_result.get("comentario")

        if coincide:

            pr.estado = "aprobado"

        else:

            pr.estado = "en_revision"

        db.commit()

        if coincide:

            _intentar_importar_reportado_automatico(db, pr, referencia, "INFOPAGOS")

            db.refresh(pr)

            cuotas_display = texto_cuotas_aplicadas_pago_reportado(db, pr)

            pdf_bytes = _generar_recibo_desde_pago(db, pr)

            pr.recibo_pdf = pdf_bytes

            to_email = (cliente.email or "").strip()

            if to_email:

                body = (

                    f"Se ha registrado un pago a su nombre.\n\n"

                    f"Número de referencia: {_referencia_display(referencia)}\n\n"

                    f"El recibo se adjunta. Si necesita información adicional, contáctenos por WhatsApp: {WHATSAPP_LINK}\n\n"

                    "RapiCredit C.A."

                )

                ok_mail, err_mail = send_email(

                    [to_email],

                    f"Recibo de pago {_referencia_display(referencia)}",

                    body,

                    attachments=[(f"recibo_{referencia}.pdf", pdf_bytes)],

                    servicio="cobros",

                    respetar_destinos_manuales=True,

                )

                if not ok_mail:

                    logger.error(

                        "[INFOPAGOS] Recibo ref=%s: correo NO enviado a %s. Error: %s.",

                        referencia,

                        to_email,

                        err_mail or "desconocido",

                    )

            recibo_token = create_recibo_infopagos_token(pr.id, expire_hours=2)

            db.commit()

            return EnviarReporteInfopagosResponse(

                ok=True,

                referencia_interna=referencia,

                mensaje="Pago registrado. Se envió el recibo al correo del deudor. Puede descargar el recibo aquí.",

                recibo_descarga_token=recibo_token,

                pago_id=pr.id,

                aplicado_a_cuotas=(cuotas_display or "").strip() or RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE,

                estado_reportado="aprobado",

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

    token: str = Query(..., description="Token de descarga emitido tras registrar el pago"),

    pago_id: int = Query(..., description="ID del pago reportado"),

    db: Session = Depends(get_db),

):

    """

    Devuelve el PDF del recibo del pago registrado por Infopagos. Requiere el token devuelto

    en la respuesta de enviar-reporte (válido 2 horas) para que el colaborador descargue el recibo.

    """

    payload = decode_token(token)

    if not payload or payload.get("type") != "recibo_infopagos":

        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    token_pago_id = payload.get("pago_id") or payload.get("sub")

    if token_pago_id is None:

        raise HTTPException(status_code=401, detail="Token inválido.")

    try:

        token_pago_id = int(token_pago_id)

    except (TypeError, ValueError):

        raise HTTPException(status_code=401, detail="Token inválido.")

    if token_pago_id != pago_id:

        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")

    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()

    if not pr:

        raise HTTPException(status_code=404, detail="Recibo no encontrado.")

    pr = pr[0] if hasattr(pr, "__getitem__") else pr

    pdf_bytes = _generar_recibo_desde_pago(db, pr)

    pr.recibo_pdf = pdf_bytes

    db.commit()

    ref = getattr(pr, "referencia_interna", "recibo") or "recibo"

    return Response(

        content=bytes(pdf_bytes),

        media_type="application/pdf",

        headers={"Content-Disposition": f'attachment; filename="recibo_{ref}.pdf"'},

    )





