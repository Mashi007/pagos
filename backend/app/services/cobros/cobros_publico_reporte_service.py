"""
Lógica compartida del reporte de pago (formulario público + Infopagos).

Mantiene reglas y textos alineados con los endpoints en
`app.api.v1.endpoints.cobros_publico.routes` sin acoplar a APIRouter.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.pago_reportado import PagoReportado
from app.models.prestamo import Prestamo
from app.services.tasa_cambio_service import fecha_hoy_caracas, obtener_tasa_por_fecha
from app.services.cobros.cedula_reportar_bs_service import cedula_autorizada_para_bs

logger = logging.getLogger(__name__)

ALLOWED_COMPROBANTE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "application/pdf",
    }
)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

MAGIC_JPEG = bytes([0xFF, 0xD8, 0xFF])
MAGIC_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
MAGIC_PDF = bytes([0x25, 0x50, 0x44, 0x46])  # %PDF
MAGIC_WEBP = bytes([0x52, 0x49, 0x46, 0x46])  # RIFF....WEBP

ERROR_TASA_BS_NO_REGISTRADA = (
    "No hay tasa de cambio oficial para la fecha de pago {fp}. "
    "Un administrador debe registrarla en Administracion > Tasas de cambio para esa fecha "
    "antes de reportar en bolivares."
)
ERROR_BS_NO_AUTORIZADO = (
    "Observación: Bolívares. No puede enviar pago en Bolívares; su cédula no está autorizada. Use USD."
)

MIN_MONTO_BS_REPORTAR = 1.0
MAX_MONTO_BS_REPORTAR = 10_000_000.0


def validar_monto_reporte_publico(monto: float, moneda_upper: str) -> Optional[str]:
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


def referencia_display(referencia_interna: str) -> str:
    ref = (referencia_interna or "").strip()
    if not ref:
        return "-"
    return ref if ref.startswith("#") else f"#{ref}"


def prestamos_aprobados_del_cliente(db: Session, cliente_id: int) -> list:
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


def error_si_no_puede_reportar_en_web(prestamos_aprobados: list) -> Optional[str]:
    """
    El formulario web asigna el pago a un único préstamo APROBADO. Si hay 0 o >1, coherente
    con importación a pagos.
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


def intentar_importar_reportado_automatico(
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
        from app.services.cobros.pago_reportado_documento import (
            claves_documento_pago_para_reportado,
            pago_reportado_colisiona_tabla_pagos,
        )

        db.refresh(pr)
        if pago_reportado_colisiona_tabla_pagos(db, pr):
            pr.estado = "importado"
            db.add(pr)
            db.commit()
            logger.info(
                "[%s] Reportado marcado importado ref=%s: ya existe un pago con el mismo comprobante "
                "(no se duplica fila en pagos).",
                log_tag,
                referencia,
            )
            return
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


def inferir_mime_comprobante_desde_extension(filename_raw: str) -> Optional[str]:
    """Cuando el navegador manda application/octet-stream o MIME vacío (típico en móviles)."""
    ext = (os.path.splitext(filename_raw or "")[1] or "").lower().lstrip(".")
    if not ext:
        return None
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "heic": "image/heic",
        "heif": "image/heif",
        "pdf": "application/pdf",
    }.get(ext)


def mime_efectivo_comprobante_web(content_type: str, filename_raw: str) -> str:
    """Normaliza Content-Type declarado y completa desde extensión si hace falta."""
    base = (content_type or "").split(";")[0].strip().lower()
    if base in ("", "application/octet-stream", "binary/octet-stream"):
        inf = inferir_mime_comprobante_desde_extension(filename_raw)
        if inf:
            base = inf
    if base == "image/jpg":
        base = "image/jpeg"
    return base


def sanitize_filename(name: str) -> str:
    """Elimina path traversal y caracteres no seguros."""
    if not name or not name.strip():
        return "comprobante"
    name = name.strip()
    name = os.path.basename(name)
    name = re.sub(r"[^\w.\-]", "_", name)[:80]
    return name or "comprobante"


def _magic_heic_o_heif(content: bytes) -> bool:
    """HEIC/HEIF (iPhone): contenedor ISO BMFF con marca ftyp y marca menor típica."""
    if len(content) < 16:
        return False
    if content[4:8] != b"ftyp":
        return False
    blob = content[8:min(48, len(content))].lower()
    return any(m in blob for m in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"))


def validate_file_magic(content: bytes, content_type: str) -> bool:
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
    if "webp" in ctype:
        return len(content) >= 12 and content[:4] == MAGIC_WEBP and content[8:12] == b"WEBP"
    if "heic" in ctype or "heif" in ctype:
        return _magic_heic_o_heif(content)
    if "gif" in ctype:
        return content[:6] in (b"GIF87a", b"GIF89a")
    return False


def generar_referencia_interna(db: Session) -> str:
    """Formato RPC-YYYYMMDD-XXXXX con XXXXX secuencial del dia (atomico por tabla)."""
    try:
        db.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (
                fecha DATE PRIMARY KEY,
                siguiente INTEGER NOT NULL DEFAULT 1
            )
        """
            )
        )
    except Exception:
        db.rollback()
        raise
    try:
        db.execute(
            text(
                """
            INSERT INTO secuencia_referencia_cobros (fecha, siguiente)
            SELECT CURRENT_DATE, COALESCE((
                SELECT MAX(CAST(SUBSTRING(referencia_interna FROM 14 FOR 5) AS INTEGER))
                FROM pagos_reportados
                WHERE referencia_interna LIKE 'RPC-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-%'
            ), 0)
            ON CONFLICT (fecha) DO NOTHING
        """
            )
        )
    except Exception:
        db.rollback()
        raise
    row = db.execute(
        text(
            """
        INSERT INTO secuencia_referencia_cobros (fecha, siguiente)
        VALUES (CURRENT_DATE, 1)
        ON CONFLICT (fecha) DO UPDATE SET siguiente = secuencia_referencia_cobros.siguiente + 1
        RETURNING siguiente
    """
        )
    ).scalar_one()
    hoy = fecha_hoy_caracas().strftime("%Y%m%d")
    return f"RPC-{hoy}-{row:05d}"


def validar_adjunto_comprobante_bytes(
    content: bytes,
    content_type: str,
    filename_raw: str,
    *,
    mensaje_excel_largo: bool,
) -> Tuple[Optional[str], str]:
    """
    Valida tamaño, tipo declarado y magic bytes. Devuelve (error o None, nombre_sanitizado).
    """
    if len(content) > MAX_FILE_SIZE:
        return "El comprobante no puede superar 10 MB.", sanitize_filename(filename_raw)
    if len(content) < 4:
        return "El archivo está vacío o no es válido.", sanitize_filename(filename_raw)
    ctype = mime_efectivo_comprobante_web(content_type or "", filename_raw)
    if "excel" in ctype or "spreadsheet" in ctype or "xls" in ctype:
        msg = (
            "El comprobante debe ser PDF o imagen (JPEG, PNG, HEIC, WebP). No se permiten archivos Excel."
            if mensaje_excel_largo
            else "El comprobante debe ser PDF o imagen (JPEG, PNG, HEIC, WebP)."
        )
        return msg, sanitize_filename(filename_raw)
    if ctype not in ALLOWED_COMPROBANTE_TYPES:
        return (
            "Solo se permiten archivos PDF, JPEG, JPG, PNG, HEIC, HEIF o WebP.",
            sanitize_filename(filename_raw),
        )
    if not validate_file_magic(content, ctype):
        return "El archivo no corresponde a una imagen o PDF válido.", sanitize_filename(filename_raw)
    return None, sanitize_filename(filename_raw)


@dataclass(frozen=True)
class MonedaObservacionNormalizados:
    moneda_upper: str
    moneda_guardar: str
    observacion: Optional[str]


def normalizar_y_validar_campos_formulario(
    *,
    tipo_cedula: str,
    numero_cedula: str,
    institucion_financiera: str,
    numero_operacion: str,
    monto: float,
    moneda: str,
    observacion: Optional[str],
) -> Tuple[Optional[str], MonedaObservacionNormalizados]:
    """
    Longitudes, moneda permitida y normalización BS/USD. Misma semántica que los endpoints.
    """
    if len(tipo_cedula.strip()) > 2 or len(numero_cedula.strip()) > 13:
        return "Datos inválidos.", MonedaObservacionNormalizados("BS", "BS", None)
    if len(institucion_financiera.strip()) > 100 or len(numero_operacion.strip()) > 100:
        return "Datos inválidos.", MonedaObservacionNormalizados("BS", "BS", None)
    obs = observacion
    if obs and len(obs) > 300:
        obs = obs[:300]
    if (moneda or "BS").strip().upper() not in ("BS", "USD", "USDT"):
        return "Moneda no válida.", MonedaObservacionNormalizados("BS", "BS", obs)
    moneda_upper = (moneda or "BS").strip().upper()
    moneda_guardar = "USD" if moneda_upper in ("USD", "USDT") else moneda_upper
    return None, MonedaObservacionNormalizados(
        moneda_upper=moneda_upper,
        moneda_guardar=moneda_guardar[:10],
        observacion=obs,
    )


def validar_reglas_bs_tasa_monto_fecha(
    db: Session,
    *,
    cedula_lookup: str,
    fecha_pago: date,
    monto: float,
    mon: MonedaObservacionNormalizados,
) -> Optional[str]:
    """Reglas que requieren BD o fecha de hoy (Caracas)."""
    if mon.moneda_upper == "BS":
        if not cedula_autorizada_para_bs(db, cedula_lookup):
            return ERROR_BS_NO_AUTORIZADO
        if obtener_tasa_por_fecha(db, fecha_pago) is None:
            return ERROR_TASA_BS_NO_REGISTRADA.format(fp=fecha_pago.strftime("%d/%m/%Y"))
    err_monto = validar_monto_reporte_publico(monto, mon.moneda_upper)
    if err_monto:
        return err_monto
    if fecha_pago > fecha_hoy_caracas():
        return "La fecha de pago no puede ser futura."
    return None


def nombres_y_apellidos_desde_cliente_nombres(nombres_cliente: str) -> Tuple[str, str]:
    """Parte `clientes.nombres` en nombres + apellidos como en el alta del reporte."""
    nombres = (nombres_cliente or "").strip()
    apellidos = ""
    if " " in nombres:
        parts = nombres.split(None, 1)
        nombres = parts[0]
        apellidos = parts[1] if len(parts) > 1 else ""
    return nombres, apellidos


def crear_pago_reportado_con_referencia_o_retry(
    db: Session,
    *,
    content: bytes,
    ctype: str,
    filename: str,
    cliente_nombres: str,
    tipo_cedula: str,
    numero_cedula: str,
    fecha_pago: date,
    institucion_financiera: str,
    numero_operacion: str,
    monto: float,
    moneda_guardar: str,
    observacion: Optional[str],
    correo_enviado_a: str,
    canal_ingreso: str,
    log_tag_duplicate: str,
) -> Tuple[Optional[PagoReportado], Optional[str], Optional[str]]:
    """
    Intenta hasta 2 veces ante colisión de referencia_interna.

    Returns:
        (pr, referencia, error) — si error, pr y referencia son None.
    """
    from app.services.pagos_gmail.comprobante_bd import persistir_comprobante_gmail_en_bd

    pr: Optional[PagoReportado] = None
    referencia: Optional[str] = None
    # Colisiones RPC-…-00001 bajo concurrencia: el bloqueo debe ser fiable; nunca continuar sin lock en PostgreSQL.
    for attempt in range(4):
        try:
            bind = db.get_bind()
            if bind.dialect.name == "postgresql":
                hoy_int = int(fecha_hoy_caracas().strftime("%Y%m%d"))
                db.execute(
                    text("SELECT pg_advisory_xact_lock(887766551, :k)"),
                    {"k": hoy_int},
                )
            referencia = generar_referencia_interna(db)
            nombres, apellidos = nombres_y_apellidos_desde_cliente_nombres(cliente_nombres)
            stored = persistir_comprobante_gmail_en_bd(db, content, ctype)
            if not stored:
                return (
                    None,
                    None,
                    "No se pudo almacenar el comprobante. Use PDF o imagen JPEG, PNG, HEIC o WebP válida.",
                )
            img_id, _url = stored
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
                comprobante_imagen_id=img_id,
                comprobante_nombre=filename[:255],
                ruta_comprobante=None,
                observacion=observacion[:300] if observacion else None,
                correo_enviado_a=correo_enviado_a,
                estado="pendiente",
                canal_ingreso=canal_ingreso,
            )
            db.add(pr)
            db.commit()
            db.refresh(pr)
            return pr, referencia, None
        except IntegrityError as ie:
            db.rollback()
            err_msg = str(ie.orig) if getattr(ie, "orig", None) else str(ie)
            if "referencia_interna" in err_msg and attempt < 3:
                logger.warning(
                    "[%s] Duplicate referencia_interna, reintentando (intento %s): %s",
                    log_tag_duplicate,
                    attempt + 1,
                    ie,
                )
                continue
            dup_msg = (
                "Ya existe un reporte con esa referencia. Si enviaste el formulario dos veces, no hace falta volver a enviar. Si no, intenta de nuevo en un momento."
                if log_tag_duplicate == "COBROS_PUBLIC"
                else "Ya existe un reporte con esa referencia. Intente de nuevo en un momento."
            )
            return None, None, dup_msg
    return None, None, "Ya existe un reporte con esa referencia. Intente de nuevo en un momento."


def token_bearer_o_query(request, token_query: Optional[str]) -> Optional[str]:
    """Authorization: Bearer … tiene prioridad sobre ?token= (deprecated)."""
    auth_header = (request.headers.get("Authorization", "") if request is not None else "") or ""
    token_from_header = None
    if auth_header.lower().startswith("bearer "):
        token_from_header = auth_header[7:].strip()
    return token_from_header or token_query
