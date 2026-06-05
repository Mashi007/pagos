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
from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Optional, Tuple

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago_reportado import PagoReportado
from app.models.prestamo import Prestamo
from app.services.tasa_cambio_service import (
    fecha_hoy_caracas,
    mensaje_sin_tasa_para_fuente,
    normalizar_fuente_tasa,
    obtener_tasa_por_fecha,
    valor_tasa_para_fuente,
)
from app.services.cobros.cedula_reportar_bs_service import (
    cedula_autorizada_para_bs,
    fuente_tasa_bs_efectiva_para_cedula,
)
from app.services.pagos_gmail.parse_campos_comprobante import (
    fusionar_validacion_reglas_monto_alto_escaneo,
)

logger = logging.getLogger(__name__)


def _elapsed_ms(start_perf: float) -> float:
    return round((perf_counter() - start_perf) * 1000, 2)

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
DUPLICADO_NUMERO_OP_VENTANA_MIN = 10

# Solo estos estados deben bloquear un nuevo envío con el mismo número de operación en la ventana
# anti-doble-click. Excluye:
# - eliminado_duplicado: sigue en BD pero no es un "reporte activo"; ignorarlo evita falsos
#   "ya duplicado" cuando el listado de cobros / pestañas no lo muestra.
# - rechazado: cobranzas rechazó el reporte; el cliente debe poder reenviar el mismo Nº de operación.
# - importado: el reporte ya se materializó en cartera; la colisión real se decide con `pagos`
#   (p. ej. `pago_reportado_colisiona_tabla_pagos` en escáner). Si operación borró los pagos
#   del préstamo («reemplazar pagos») pero el reportado sigue "importado", incluirlo aquí
#   bloqueaba reenvíos válidos en la misma ventana de minutos.
_ESTADOS_VENTANA_DUPLICADO_NUM_OP = (
    "pendiente",
    "en_revision",
    "aprobado",
)


def _es_banco_mercantil(nombre_banco: Optional[str]) -> bool:
    return "mercantil" in (nombre_banco or "").strip().lower()

MAGIC_JPEG = bytes([0xFF, 0xD8, 0xFF])
MAGIC_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
MAGIC_PDF = bytes([0x25, 0x50, 0x44, 0x46])  # %PDF
MAGIC_WEBP = bytes([0x52, 0x49, 0x46, 0x46])  # RIFF....WEBP

ERROR_TASA_BS_NO_REGISTRADA = (
    "No hay tasa de cambio para la fecha de pago {fp} y la fuente elegida (BCV, Euro o Binance). "
    "Un administrador debe registrarla en Tasas de cambio para esa fecha antes de reportar en bolívares."
)
ERROR_BS_NO_AUTORIZADO = (
    "Observación: Bolívares. No puede enviar pago en Bolívares; su cédula no está autorizada. Use USD."
)

MIN_MONTO_BS_REPORTAR = 1.0
MAX_MONTO_BS_REPORTAR = 10_000_000.0


def aplicar_revision_manual_por_monto_alto_en_reportado(
    *,
    monto: float,
    moneda_upper: str,
    pr: PagoReportado,
) -> bool:
    """
    Si el monto supera el umbral global de escaneo, anota el reporte y devuelve True
    (el caller debe forzar estado en_revision / falla_validadores).
    """
    from app.services.pagos_gmail.parse_campos_comprobante import (
        mensaje_monto_revision_manual,
        monto_requiere_revision_manual,
    )

    if not monto_requiere_revision_manual(monto, moneda=moneda_upper):
        return False
    extra = mensaje_monto_revision_manual(monto, moneda=moneda_upper)
    prev = (getattr(pr, "gemini_comentario", None) or "").strip()
    pr.gemini_comentario = (f"{prev} {extra}".strip() if prev else extra)[:500]
    return True


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
) -> AutoImportResultado:
    """
    Si el reporte quedó en estado aprobado: crea Pago (mismas reglas que importar-desde-cobros),
    aplica a cuotas y marca el reporte como importado. Fallos solo en log (no rompe la respuesta al cliente).
    """
    started_total = perf_counter()
    if pr is None or getattr(pr, "estado", None) != "aprobado":
        return AutoImportResultado(total_ms=_elapsed_ms(started_total))
    lookup_ms = 0.0
    importar_pago_ms = 0.0
    cascada_ms = 0.0
    commit_ms = 0.0
    try:
        from app.models.pago import Pago
        from app.api.v1.endpoints.pagos import importar_un_pago_reportado_a_pagos, _aplicar_pago_a_cuotas_interno
        from app.services.cobros.pago_reportado_documento import (
            claves_documento_pago_para_reportado,
            pago_reportado_colisiona_tabla_pagos,
        )

        lookup_started = perf_counter()
        db.refresh(pr)
        if pago_reportado_colisiona_tabla_pagos(db, pr):
            lookup_ms = _elapsed_ms(lookup_started)
            pr.estado = "importado"
            pr.falla_validadores_manual = False
            db.add(pr)
            commit_started = perf_counter()
            db.commit()
            commit_ms = _elapsed_ms(commit_started)
            result = AutoImportResultado(
                ya_existia_en_pagos=True,
                lookup_ms=lookup_ms,
                commit_ms=commit_ms,
                total_ms=_elapsed_ms(started_total),
            )
            logger.info(
                "[%s] Reportado marcado importado ref=%s: ya existe un pago con el mismo comprobante "
                "(no se duplica fila en pagos).",
                log_tag,
                referencia,
            )
            logger.info(
                "[%s_TIMING] ref=%s autoimport=colision_existente lookup_ms=%s importar_pago_ms=%s "
                "cascada_ms=%s commit_ms=%s total_ms=%s",
                log_tag,
                referencia,
                result.lookup_ms,
                result.importar_pago_ms,
                result.cascada_ms,
                result.commit_ms,
                result.total_ms,
            )
            return result
        claves_pr = claves_documento_pago_para_reportado(pr)
        docs_bd: set[str] = set()
        if claves_pr:
            rows = db.execute(
                select(Pago.numero_documento).where(Pago.numero_documento.in_(claves_pr))
            ).scalars().all()
            docs_bd = {str(x) for x in rows if x}
        lookup_ms = _elapsed_ms(lookup_started)

        usuario = "infopagos@rapicredit" if log_tag == "INFOPAGOS" else "cobros-publico@rapicredit"

        importar_started = perf_counter()
        res = importar_un_pago_reportado_a_pagos(
            db,
            pr,
            usuario_email=usuario,
            documentos_ya_en_bd=docs_bd,
            docs_en_lote=set(),
            registrar_error_en_tabla=False,
        )
        importar_pago_ms = _elapsed_ms(importar_started)
        if not res.get("ok"):
            result = AutoImportResultado(
                error=res.get("error"),
                lookup_ms=lookup_ms,
                importar_pago_ms=importar_pago_ms,
                total_ms=_elapsed_ms(started_total),
            )
            logger.warning("[%s] Auto-import ref=%s omitido: %s", log_tag, referencia, res.get("error"))
            logger.info(
                "[%s_TIMING] ref=%s autoimport=omitido lookup_ms=%s importar_pago_ms=%s "
                "cascada_ms=%s commit_ms=%s total_ms=%s",
                log_tag,
                referencia,
                result.lookup_ms,
                result.importar_pago_ms,
                result.cascada_ms,
                result.commit_ms,
                result.total_ms,
            )
            return result

        pago = res["pago"]
        cascada_started = perf_counter()
        cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
        cascada_ms = _elapsed_ms(cascada_started)
        if cc > 0 or cp > 0:
            pago.estado = "PAGADO"
        pr.estado = "importado"
        pr.falla_validadores_manual = False
        commit_started = perf_counter()
        db.commit()
        commit_ms = _elapsed_ms(commit_started)
        result = AutoImportResultado(
            pago_id=getattr(pago, "id", None),
            lookup_ms=lookup_ms,
            importar_pago_ms=importar_pago_ms,
            cascada_ms=cascada_ms,
            commit_ms=commit_ms,
            total_ms=_elapsed_ms(started_total),
        )
        logger.info("[%s] Auto-import OK ref=%s pago_id=%s", log_tag, referencia, getattr(pago, "id", None))
        logger.info(
            "[%s_TIMING] ref=%s autoimport=ok pago_id=%s lookup_ms=%s importar_pago_ms=%s "
            "cascada_ms=%s commit_ms=%s total_ms=%s",
            log_tag,
            referencia,
            result.pago_id,
            result.lookup_ms,
            result.importar_pago_ms,
            result.cascada_ms,
            result.commit_ms,
            result.total_ms,
        )
        return result
    except Exception as e:
        logger.warning("[%s] Auto-import fallo ref=%s: %s", log_tag, referencia, e)
        try:
            db.rollback()
        except Exception:
            pass
        return AutoImportResultado(
            error=str(e),
            lookup_ms=lookup_ms,
            importar_pago_ms=importar_pago_ms,
            cascada_ms=cascada_ms,
            commit_ms=commit_ms,
            total_ms=_elapsed_ms(started_total),
        )


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


def _max_secuencial_referencia_dia(db: Session, hoy_str: str) -> int:
    """Maximo XXXXX ya persistido en pagos_reportados para RPC-{hoy_str}-XXXXX."""
    prefix = f"RPC-{hoy_str}-%"
    row = db.execute(
        text(
            """
            SELECT COALESCE(MAX(CAST(SUBSTRING(referencia_interna FROM 14 FOR 5) AS INTEGER)), 0)
            FROM pagos_reportados
            WHERE referencia_interna LIKE :prefix
            """
        ),
        {"prefix": prefix},
    ).scalar_one()
    return int(row or 0)


def generar_referencia_interna(db: Session) -> str:
    """
    Formato RPC-YYYYMMDD-XXXXX con XXXXX secuencial del dia (America/Caracas).

    La secuencia en BD se alinea con MAX(pagos_reportados) en cada llamada para
    tolerar rollback tras UniqueViolation y evitar desfase UTC vs Caracas.
    """
    hoy = fecha_hoy_caracas()
    hoy_str = hoy.strftime("%Y%m%d")
    hoy_iso = hoy.isoformat()
    max_existente = _max_secuencial_referencia_dia(db, hoy_str)

    try:
        db.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS secuencia_referencia_cobros (
                fecha DATE PRIMARY KEY,
                siguiente INTEGER NOT NULL DEFAULT 0
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
            VALUES (:fecha, :max_existente)
            ON CONFLICT (fecha) DO NOTHING
        """
            ),
            {"fecha": hoy_iso, "max_existente": max_existente},
        )
        db.execute(
            text(
                """
            UPDATE secuencia_referencia_cobros
            SET siguiente = CASE
                WHEN siguiente >= :max_existente THEN siguiente
                ELSE :max_existente
            END
            WHERE fecha = :fecha
        """
            ),
            {"fecha": hoy_iso, "max_existente": max_existente},
        )
        row = db.execute(
            text(
                """
            UPDATE secuencia_referencia_cobros
            SET siguiente = siguiente + 1
            WHERE fecha = :fecha
            RETURNING siguiente
        """
            ),
            {"fecha": hoy_iso},
        ).scalar_one()
    except Exception:
        db.rollback()
        raise
    return f"RPC-{hoy_str}-{int(row):05d}"


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


@dataclass(frozen=True)
class AutoImportResultado:
    pago_id: Optional[int] = None
    ya_existia_en_pagos: bool = False
    error: Optional[str] = None
    lookup_ms: float = 0.0
    importar_pago_ms: float = 0.0
    cascada_ms: float = 0.0
    commit_ms: float = 0.0
    total_ms: float = 0.0


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


def resolver_fuente_tasa_reporte_publico(
    db: Session,
    *,
    cedula_lookup: str,
    moneda_upper: str,
    fuente_tasa_cambio: Optional[str] = None,
) -> Optional[str]:
    """Bs.: solo la tasa de cedulas_reportar_bs; el cliente no elige fuente."""
    if (moneda_upper or "").upper() == "BS":
        return fuente_tasa_bs_efectiva_para_cedula(db, cedula_lookup)
    return normalizar_fuente_tasa(fuente_tasa_cambio)


def validar_reglas_bs_tasa_monto_fecha(
    db: Session,
    *,
    cedula_lookup: str,
    fecha_pago: date,
    monto: float,
    mon: MonedaObservacionNormalizados,
    fuente_tasa_cambio: Optional[str] = None,
) -> Optional[str]:
    """Reglas que requieren BD o fecha de hoy (Caracas)."""
    if mon.moneda_upper == "BS":
        if not cedula_autorizada_para_bs(db, cedula_lookup):
            return ERROR_BS_NO_AUTORIZADO
        fuente = resolver_fuente_tasa_reporte_publico(
            db,
            cedula_lookup=cedula_lookup,
            moneda_upper=mon.moneda_upper,
            fuente_tasa_cambio=fuente_tasa_cambio,
        )
        if not fuente:
            return (
                "No hay tasa de cambio configurada para esta cédula en bolívares. "
                "Contacte al administrador."
            )
        row = obtener_tasa_por_fecha(db, fecha_pago)
        if row is None:
            return ERROR_TASA_BS_NO_REGISTRADA.format(fp=fecha_pago.strftime("%d/%m/%Y"))
        t_val = valor_tasa_para_fuente(row, fuente)
        if t_val is None or not float(t_val) > 0:
            fp = fecha_pago.strftime("%d/%m/%Y")
            return mensaje_sin_tasa_para_fuente(fuente, fp)
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
    fuente_tasa_cambio: Optional[str] = None,
    comprobante_imagen_id_existente: Optional[str] = None,
) -> Tuple[Optional[PagoReportado], Optional[str], Optional[str]]:
    """
    Intenta hasta 4 veces ante colisión de referencia_interna.

    Returns:
        (pr, referencia, error) — si error, pr y referencia son None.
    """
    from app.models.pago_comprobante_imagen import PagoComprobanteImagen
    from app.services.pagos_gmail.comprobante_bd import persistir_comprobante_gmail_en_bd

    pr: Optional[PagoReportado] = None
    referencia: Optional[str] = None
    num_key = normalize_documento((numero_operacion or "").strip()) or (numero_operacion or "").strip()
    now_local = datetime.now()
    ventana_desde = now_local - timedelta(minutes=DUPLICADO_NUMERO_OP_VENTANA_MIN)

    def _eliminar_duplicados_rapidos_conservar_primero() -> Tuple[Optional[int], Optional[str], int]:
        """
        Ventana anti-doble-click: mismo numero_operacion en pocos minutos.
        Conserva el primer reporte (created_at/id) y elimina hermanos nuevos en estados no terminales.

        Solo considera filas en estados activos previos a cartera (`_ESTADOS_VENTANA_DUPLICADO_NUM_OP`).
        No usa `eliminado_duplicado`, `rechazado` ni `importado` para bloquear: evita "duplicado fantasma"
        y permite reenvío tras rechazo o tras borrar el pago importado (reemplazo de cartera).
        """
        if not num_key:
            return None, None, 0
        rows = db.execute(
            select(
                PagoReportado.id,
                PagoReportado.referencia_interna,
                PagoReportado.estado,
                PagoReportado.numero_operacion,
                PagoReportado.created_at,
            )
            .where(
                PagoReportado.created_at >= ventana_desde,
                PagoReportado.estado.in_(_ESTADOS_VENTANA_DUPLICADO_NUM_OP),
            )
            .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
        ).all()
        same: list[tuple[int, str, str]] = []
        for rid, rref, rstate, rop, _rc in rows:
            k = normalize_documento((rop or "").strip()) or (rop or "").strip()
            if k == num_key:
                same.append((int(rid), str(rref or ""), str(rstate or "")))
        if not same:
            return None, None, 0
        keep_id, keep_ref, _keep_state = same[0]
        to_mark = [rid for rid, _rref, st in same[1:] if st in ("pendiente", "en_revision", "rechazado")]
        if to_mark:
            # Excepción confirmada: Mercantil no se auto-elimina; pasa a revisión manual.
            if _es_banco_mercantil(institucion_financiera):
                db.execute(
                    update(PagoReportado)
                    .where(PagoReportado.id.in_(to_mark))
                    .values(
                        estado="en_revision",
                        falla_validadores_manual=True,
                        motivo_rechazo=(
                            "Duplicado por número de operación en banco Mercantil: "
                            "excepción activa, requiere revisión manual."
                        )[:2000],
                    )
                )
                return keep_id, keep_ref, 0
            db.execute(
                update(PagoReportado)
                .where(PagoReportado.id.in_(to_mark))
                .values(
                    estado="eliminado_duplicado",
                    falla_validadores_manual=False,
                    motivo_rechazo=(
                        "Eliminado automáticamente por duplicado de número de operación "
                        f"(mismo número que reporte {keep_ref or keep_id})."
                    )[:2000],
                )
            )
        return keep_id, keep_ref, len(to_mark)
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
                if num_key:
                    db.execute(
                        text("SELECT pg_advisory_xact_lock(887766554, hashtext(:k))"),
                        {"k": num_key},
                    )
            keep_id, keep_ref, removed = _eliminar_duplicados_rapidos_conservar_primero()
            if keep_id is not None:
                if removed > 0:
                    logger.info(
                        "[%s] numero_operacion duplicado=%s: eliminados %s reportes rápidos; se conserva id=%s ref=%s",
                        log_tag_duplicate,
                        num_key,
                        removed,
                        keep_id,
                        keep_ref,
                    )
                return (
                    None,
                    None,
                    "Ya recibimos este número de operación recientemente. Se conserva el primer reporte y se eliminaron duplicados enviados en segundos.",
                )
            referencia = generar_referencia_interna(db)
            nombres, apellidos = nombres_y_apellidos_desde_cliente_nombres(cliente_nombres)
            img_ex = (comprobante_imagen_id_existente or "").strip()
            if img_ex:
                hit = db.execute(
                    select(PagoComprobanteImagen.id).where(PagoComprobanteImagen.id == img_ex)
                ).scalars().first()
                if not hit:
                    return (
                        None,
                        None,
                        "El comprobante asociado al borrador ya no está disponible. Vuelva a escanear.",
                    )
                img_id = str(hit)
            else:
                stored = persistir_comprobante_gmail_en_bd(db, content, ctype)
                if not stored:
                    return (
                        None,
                        None,
                        "No se pudo almacenar el comprobante. Use PDF o imagen JPEG, PNG, HEIC o WebP válida.",
                    )
                img_id, _url = stored
            cedula_lookup = (
                f"{(tipo_cedula or '').strip().upper()}{(numero_cedula or '').strip()}"
                .replace("-", "")
                .replace(" ", "")
            )
            moneda_upper = (moneda_guardar or "").strip().upper()
            if moneda_upper == "BS":
                fuente_guardar = resolver_fuente_tasa_reporte_publico(
                    db,
                    cedula_lookup=cedula_lookup,
                    moneda_upper="BS",
                )
                if not fuente_guardar:
                    return (
                        None,
                        None,
                        "No hay tasa de cambio configurada para esta cédula en bolívares.",
                    )
            else:
                fuente_guardar = normalizar_fuente_tasa(fuente_tasa_cambio)
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
                fuente_tasa_cambio=fuente_guardar,
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
