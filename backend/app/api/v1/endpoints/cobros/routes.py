"""
Endpoints de administración del módulo Cobros (requieren autenticación).
Listado de pagos reportados, detalle, aprobar, rechazar, histórico por cédula.
"""
import io
import logging
import base64
import re
import threading
import time
from collections import Counter
from datetime import date, datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional, List, Tuple, Any, Dict, Set

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, case, delete, text, update
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from app.core.database import get_db
from app.core.documento import normalize_documento
from app.core.deps import get_current_user
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.cobros.recibo_pdf import WHATSAPP_LINK, WHATSAPP_DISPLAY
from app.services.documentos_cliente_centro import generar_recibo_pdf_desde_pago_reportado
from app.core.email import cobros_recibo_attachments_or_oversize_note, send_email
from app.utils.cliente_emails import emails_destino_desde_objeto, unir_destinatarios_log
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_bloqueado_por_desistimiento,
)
from app.core.email_config_holder import get_email_activo_servicio
from app.api.v1.endpoints.validadores import validate_cedula
from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno
from app.services.cobros.pago_reportado_documento import (
    claves_documento_pago_para_reportado,
    documento_numero_desde_pago_reportado,
    pago_reportado_colisiona_tabla_pagos,
    primer_pago_id_si_existe_para_claves_reportado,
    primer_reportado_id_por_norm_batch,
    primer_reportado_id_por_norm_peer_first_map,
    reportado_toca_claves_canonicas_en_pagos,
)
from app.services.cobros.cedula_reportar_bs_service import (
    load_autorizados_bs_claves,
    cedula_coincide_autorizados_bs,
)
from app.services.tasa_cambio_service import (
    obtener_tasa_por_fecha,
    convertir_bs_a_usd,
    obtener_tasas_por_fechas,
    tasa_y_equivalente_usd_excel,
)
from app.services.pagos_gmail.gemini_service import (
    compare_form_with_image,
    extract_infopagos_campos_desde_comprobante,
)
from app.services.cobros import cobros_publico_reporte_service as cpr
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar
from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import build_drive_service
from app.services.cobros.pago_reportado_comprobante_unico import (
    comprobante_bytes_y_content_type_desde_reportado,
    nombre_adjunto_email_desde_reportado,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _log_fase_aprobacion(
    *,
    flujo: str,
    fase: str,
    pago_id: int,
    referencia: str,
    start_ts: float,
    extra: str = "",
) -> None:
    elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
    logger.info(
        "[COBROS_TIMING] flujo=%s fase=%s pago_id=%s ref=%s elapsed_ms=%.2f %s",
        flujo,
        fase,
        pago_id,
        referencia,
        elapsed_ms,
        extra,
    )



class PagoReportadoHistorialItem(BaseModel):
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_email: Optional[str] = None
    motivo: Optional[str] = None
    created_at: Optional[str] = None


class PagoReportadoListItem(BaseModel):
    id: int
    referencia_interna: str
    nombres: str
    apellidos: str
    cedula_display: str
    institucion_financiera: str
    monto: float
    moneda: str
    tasa_cambio_bs_usd: Optional[float] = Field(
        None,
        description="Tasa oficial Bs por 1 USD (día fecha_pago); null si USD o sin tasa en BD.",
    )
    equivalente_usd: Optional[float] = Field(
        None,
        description="Monto en USD (Bs÷tasa si BS; si USD el monto; null si BS sin tasa).",
    )
    fecha_pago: date
    numero_operacion: str
    fecha_reporte: datetime
    estado: str
    gemini_coincide_exacto: Optional[str] = None
    observacion: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    tiene_recibo_pdf: bool
    tiene_comprobante: bool
    canal_ingreso: Optional[str] = Field(
        None,
        description="infopagos | cobros_publico | null (historico). Misma cola operativa y reglas para todos.",
    )


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
    tasa_cambio_bs_usd: Optional[float] = Field(
        None,
        description="Tasa oficial Bs por 1 USD (día fecha_pago); null si USD o sin tasa en BD.",
    )
    equivalente_usd: Optional[float] = Field(
        None,
        description="Monto en USD (Bs÷tasa si BS; si USD el monto; null si BS sin tasa).",
    )
    ruta_comprobante: Optional[str] = None
    tiene_comprobante: bool
    tiene_recibo_pdf: bool
    observacion: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    estado: str
    motivo_rechazo: Optional[str] = None
    gemini_coincide_exacto: Optional[str] = None
    gemini_comentario: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    historial: List[PagoReportadoHistorialItem]
    canal_ingreso: Optional[str] = Field(
        None,
        description="infopagos | cobros_publico | null (historico).",
    )
    duplicado_en_pagos: bool = False
    pago_existente_id: Optional[int] = None
    prestamo_existente_id: Optional[int] = None
    pago_existente_estado: Optional[str] = None
    pago_existente_fecha_pago: Optional[date] = Field(
        None,
        description="Fecha del pago ya registrado en cartera (tabla pagos), para comparar con este reporte.",
    )
    prestamo_objetivo_id: Optional[int] = None
    prestamo_objetivo_multiple: Optional[bool] = None
    prestamo_duplicado_es_objetivo: Optional[bool] = None


class AprobarRechazarBody(BaseModel):
    motivo: Optional[str] = None


class MarcarExportadosBody(BaseModel):
    pago_reportado_ids: Optional[List[int]] = None


class TendenciaFalloGeminiPunto(BaseModel):
    fecha: str
    fallos_no: int
    verificados_gemini: int
    pct_fallo: Optional[float] = None


class TendenciaFallosGeminiResponse(BaseModel):
    puntos: List[TendenciaFalloGeminiPunto]
    fecha_desde: str
    fecha_hasta: str
    dias: int
    zona: str = "America/Caracas"
    nota: str


# Mensaje genérico al rechazar: indicar que se comuniquen por WhatsApp (424-4579934)
MENSAJE_RECHAZO_GENERICO = (
    "Su reporte de pago no ha sido aprobado. "
    "Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {whatsapp} ({link}).\n\n"
    "RapiCredit C.A."
).format(whatsapp=WHATSAPP_DISPLAY, link=WHATSAPP_LINK)


def _referencia_display(referencia_interna: str) -> str:
    ref = (referencia_interna or "").strip()
    if not ref:
        return "-"
    return ref if ref.startswith("#") else f"#{ref}"


def _columna_observacion_gemini_ignora_cola_cobros(nombre: str) -> bool:
    """
    Nombres de columna (desde comentario Gemini o lista corta) que no deben
    contar como «falla validadores» ni aparecer en la observación de cola para
    bloquear aprobación automática. La fecha del comprobante sigue editable en
    Cobros; no se usa como criterio de cola frente a divergencias de imagen.
    """
    t = " ".join((nombre or "").strip().lower().split())
    t = t.replace("ó", "o")
    return t in ("fecha pago", "fecha de pago")


def _observacion_solo_columnas(raw: Optional[str]) -> Optional[str]:
    """Devuelve la observación mostrando solo nombres de columnas (formato estándar: separador único ' / '). Si raw ya es lista corta, normaliza separadores; si es texto largo, extrae columnas por palabras clave."""
    if not raw or not (raw := raw.strip()):
        return None
    # Si ya parece lista de columnas (corta, sin frases largas): normalizar a " / "
    if len(raw) <= 80 and not any(x in raw for x in ("en la imagen", "en el formulario", "mientras que", "incluye el", "no coincide")):
        parts = [p.strip() for p in raw.replace(",", " / ").split(" / ") if p.strip()]
        parts = [p for p in parts if not _columna_observacion_gemini_ignora_cola_cobros(p)]
        if not parts:
            return None
        return " / ".join(parts)
    # Extraer columnas por palabras clave (registros antiguos con texto largo)
    lower = raw.lower()
    columnas = []
    if "cédula" in lower or "cedula" in lower:
        columnas.append("Cédula")
    if "banco" in lower or "institución" in lower or "institucion" in lower or "financiera" in lower:
        columnas.append("Banco")
    if "operación" in lower or "operacion" in lower or "referencia" in lower or "serial" in lower:
        columnas.append("Nº operación")
    if "monto" in lower or "cantidad" in lower:
        columnas.append("Monto")
    if "moneda" in lower:
        columnas.append("Moneda")
    columnas = [c for c in columnas if not _columna_observacion_gemini_ignora_cola_cobros(c)]
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
    for cedula in clientes_cedulas:
        if cedula is None:
            continue
        # scalars().all() devuelve valores escalares (str/int), no tuplas
        raw = str(cedula).strip().upper().replace("-", "").replace(" ", "")
        if not raw:
            continue
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


# Listado pagos reportados: evitar leer todas las cédulas de clientes en cada request (miles de filas).
_CEDULAS_CLIENTES_CACHE_TTL_SEC = 120.0
_cedulas_clientes_cache: Optional[Tuple[float, frozenset]] = None
_autorizados_bs_cache: Optional[Tuple[float, frozenset]] = None
_cobros_list_aux_lock = threading.Lock()

# Mapas de precálculo duplicados (norm global, nº operación, presencia en pagos): costosos en GET listado/KPIs.
# Cache en proceso con token de revisión barato + TTL para no servir datos obsoletos si cambia cola/exportados/pagos.
_PRIMER_MAPS_CACHE_TTL_SEC = 90.0

# Filas SQL por iteración al barrer la cola manual (validadores en Python). Subir reduce round-trips a BD por lote.
_COBROS_LISTADO_SCAN_BATCH = 1200
_PRIMER_MAPS_CACHE_MAX_ENTRIES = 24
_primer_maps_triple_cache_lock = threading.Lock()
# scope_key -> (revision_token, monotonic_ts, primer_precalc, primer_num_op, numeros_en_pagos_frozen)
_primer_maps_triple_cache: Dict[str, Tuple[tuple, float, Dict[str, int], Dict[str, int], frozenset]] = {}
_REGULARIZA_MIN_INTERVAL_SEC = 90.0
_REGULARIZA_TIME_BUDGET_MS = 350.0
_REGULARIZA_MAX_IDS_PER_RUN = 8
_regulariza_last_run_monotonic = 0.0
_regulariza_lock = threading.Lock()


def _cedulas_en_clientes_set_cached(db: Session) -> frozenset:
    """Misma semántica que _cedulas_en_clientes_set; cache en proceso ~2 min."""
    global _cedulas_clientes_cache
    now = time.monotonic()
    with _cobros_list_aux_lock:
        if _cedulas_clientes_cache is not None:
            ts, data = _cedulas_clientes_cache
            if now - ts < _CEDULAS_CLIENTES_CACHE_TTL_SEC:
                return data
        data = frozenset(_cedulas_en_clientes_set(db))
        _cedulas_clientes_cache = (now, data)
        return data


def _autorizados_bs_claves_cached(db: Session) -> frozenset:
    global _autorizados_bs_cache
    now = time.monotonic()
    with _cobros_list_aux_lock:
        if _autorizados_bs_cache is not None:
            ts, data = _autorizados_bs_cache
            if now - ts < _CEDULAS_CLIENTES_CACHE_TTL_SEC:
                return data
        data = load_autorizados_bs_claves(db)
        _autorizados_bs_cache = (now, data)
        return data


def _collect_candidatos_canon_desde_reportados(rows: List[PagoReportado]) -> Set[str]:
    """Claves canónicas candidatas del lote (reportados) para cruzar con `pagos` por IN indexado."""
    out: Set[str] = set()
    for r in rows:
        for k in claves_documento_pago_para_reportado(r):
            if not k:
                continue
            c = normalize_documento(k) or k
            if c:
                out.add(c)
    return out


def _pagos_canonicos_presentes_para_claves(db: Session, claves: Set[str]) -> frozenset:
    """
    Subconjunto de `claves` que existen en cartera.

    Prioridad:
    1) `pagos.doc_canon_*` (rápido con índices cuando están pobladas)
    2) fallback legacy por `pagos.numero_documento` / `pagos.referencia_pago`
       para filas antiguas sin backfill canónico.
    """
    if not claves:
        return frozenset()
    found: Set[str] = set()
    chunk_size = 450
    lst = [x for x in claves if x]
    for i in range(0, len(lst), chunk_size):
        part = lst[i : i + chunk_size]
        if not part:
            continue
        for v in db.execute(
            select(Pago.doc_canon_numero).where(Pago.doc_canon_numero.in_(part))
        ).scalars().all():
            if v:
                found.add(v)
        for v in db.execute(
            select(Pago.doc_canon_referencia).where(Pago.doc_canon_referencia.in_(part))
        ).scalars().all():
            if v:
                found.add(v)
        # Fallback legacy: si hay pagos sin doc_canon_* poblado, igual marcar DUPLICADO.
        for v in db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(part))
        ).scalars().all():
            c = normalize_documento(v) if v else None
            if c:
                found.add(c)
        for v in db.execute(
            select(Pago.referencia_pago).where(Pago.referencia_pago.in_(part))
        ).scalars().all():
            c = normalize_documento(v) if v else None
            if c:
                found.add(c)
    return frozenset(found)


def _rechazar_aprobacion_si_documento_ya_en_pagos(db: Session, pr: PagoReportado) -> None:
    """Regla operativa: no aprobar si el comprobante ya existe en cartera (`pagos`)."""
    if pago_reportado_colisiona_tabla_pagos(db, pr):
        raise HTTPException(
            status_code=400,
            detail="No se puede aprobar: el número de documento / comprobante ya consta en la tabla de pagos.",
        )


def _numero_operacion_canonico(raw: Optional[str]) -> str:
    """Normaliza solo `numero_operacion` para regla estricta de duplicado."""
    op = (raw or "").strip()
    if not op:
        return ""
    return normalize_documento(op) or op


def _primer_id_por_numero_operacion_para_where(db: Session, wh: List[Any]) -> Dict[str, int]:
    """
    Mapa numero_operacion_canonico -> primer id por created_at/id dentro del WHERE dado.
    Regla estricta: duplicado solo por numero_operacion (no por referencia interna).
    """
    if not wh:
        return {}
    first: Dict[str, int] = {}
    stmt = (
        select(PagoReportado.id, PagoReportado.numero_operacion)
        .where(*wh)
        .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
    )
    res = db.execute(stmt)
    while True:
        block = res.fetchmany(3000)
        if not block:
            break
        for pid, numero_operacion in block:
            k = _numero_operacion_canonico(numero_operacion)
            if not k or k in first:
                continue
            first[k] = int(pid)
    return first


def _numeros_operacion_presentes_en_pagos(db: Session, keys: Set[str]) -> Set[str]:
    """Subconjunto de `keys` que ya existe en `pagos.doc_canon_numero`."""
    if not keys:
        return set()
    out: Set[str] = set()
    lst = [k for k in keys if k]
    for i in range(0, len(lst), 450):
        part = lst[i : i + 450]
        if not part:
            continue
        vals = db.execute(
            select(Pago.doc_canon_numero).where(Pago.doc_canon_numero.in_(part))
        ).scalars().all()
        for v in vals:
            if v:
                out.add(v)
    return out


def _duplicados_reportados_por_numero_operacion(
    db: Session,
    *,
    numero_key: str,
    excluir_id: Optional[int] = None,
) -> List[Tuple[int, str, str]]:
    """
    Devuelve reportados (id, referencia, estado) que comparten el mismo numero_operacion canonico.
    Regla estricta basada solo en numero_operacion.
    """
    if not numero_key:
        return []
    stmt = (
        select(
            PagoReportado.id,
            PagoReportado.referencia_interna,
            PagoReportado.estado,
            PagoReportado.numero_operacion,
        )
        .where(PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado", "rechazado")))
        .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
    )
    rows = db.execute(stmt).all()
    out: List[Tuple[int, str, str]] = []
    for rid, rref, rstate, rnum in rows:
        if excluir_id is not None and int(rid) == int(excluir_id):
            continue
        if _numero_operacion_canonico(rnum) != numero_key:
            continue
        out.append((int(rid), str(rref or ""), str(rstate or "")))
    return out


def _lock_numero_operacion_canonico(db: Session, numero_key: str) -> None:
    """
    Bloquea por transacción una clave de número de operación (PostgreSQL) para
    evitar carreras al aprobar dos reportes iguales al mismo tiempo.
    """
    if not numero_key:
        return
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(887766553, hashtext(:k))"),
        {"k": numero_key},
    )


def _es_banco_mercantil(nombre_banco: Optional[str]) -> bool:
    return "mercantil" in (nombre_banco or "").strip().lower()


def _observacion_reglas_carga(
    db: Session,
    rows: list,
    cedulas_en_clientes: set,
    cedulas_bolivares: frozenset,
    claves_doc_en_pagos: frozenset,
    conteo_norm_en_pagina: Counter,
    primer_id_por_norm: Dict[str, int],
) -> list:
    """
    Para cada fila: NO CLIENTES, No pag Bs., DUPLICADO.

    ``claves_doc_en_pagos``: canónicos ya presentes en cartera para las claves del lote
    (consulta indexada a ``pagos.doc_canon_*``, no toda la tabla en RAM).

    DUPLICADO entre reportados: solo si no es el primer reporte con ese documento normalizado
    (primer id global por created_at/id). Si falta en el mapa (escaneo acotado), se usa el
    conteo del lote actual como respaldo (mismo criterio antiguo para esa pagina).
    """
    result = []
    for r in rows:
        partes = []
        raw_cedula = ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
        if cedula_norm and cedula_norm not in cedulas_en_clientes:
            partes.append("NO CLIENTES")
            logger.debug(
                "[COBROS] NO CLIENTES: ref=%s tipo_cedula=%r numero_cedula=%r raw=%r cedula_norm=%r | set_size=%s",
                getattr(r, "referencia_interna", None),
                getattr(r, "tipo_cedula", None),
                getattr(r, "numero_cedula", None),
                raw_cedula,
                cedula_norm,
                len(cedulas_en_clientes),
            )
        moneda = (r.moneda or "BS").strip().upper()
        if moneda == "BS" and cedula_norm and not cedula_coincide_autorizados_bs(cedula_norm, cedulas_bolivares):
            partes.append("No pag Bs.")
        dup_pagos = reportado_toca_claves_canonicas_en_pagos(r, claves_doc_en_pagos)
        n_doc_eff = documento_numero_desde_pago_reportado(r)[1]
        dup_entre_reportados = False
        if n_doc_eff:
            pid = primer_id_por_norm.get(n_doc_eff)
            if pid is not None:
                dup_entre_reportados = r.id != pid
            elif conteo_norm_en_pagina.get(n_doc_eff, 0) > 1:
                dup_entre_reportados = True
        if dup_pagos or dup_entre_reportados:
            partes.append("DUPLICADO")
        result.append(partes)
    return result


def _pago_reportado_list_items_from_rows(
    db: Session,
    rows: List[PagoReportado],
    *,
    primer_id_por_norm_precalc: Optional[Dict[str, int]] = None,
    include_financial_fields: bool = True,
) -> List[PagoReportadoListItem]:
    """Misma lógica de observaciones / tasa que el listado paginado.

    Si ``include_financial_fields`` es False, no calcula tasa Bs/USD ni equivalente (ahorra trabajo
    en barridos masivos donde solo se usa ``observacion`` + Gemini para ``_item_falla_validadores_cobros_excel``).
    """
    if not rows:
        return []
    cedula_norms = [
        _normalize_cedula_for_client_lookup(
            ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        )
        for r in rows
    ]
    cedulas_en_clientes = _cedulas_en_clientes_set_cached(db)
    logger.debug(
        "[COBROS] pagos-reportados: cedulas_en_clientes set_size=%s (cache)",
        len(cedulas_en_clientes),
    )

    cedulas_bolivares = _autorizados_bs_claves_cached(db)

    fechas_tasa = list({r.fecha_pago for r in rows if r.fecha_pago is not None})
    tasas_por_fecha = (
        obtener_tasas_por_fechas(db, fechas_tasa) if include_financial_fields else {}
    )

    candidatos = _collect_candidatos_canon_desde_reportados(rows)
    claves_doc_en_pagos = _pagos_canonicos_presentes_para_claves(db, candidatos)
    norm_por_fila = []
    for r in rows:
        _, n_eff = documento_numero_desde_pago_reportado(r)
        norm_por_fila.append(n_eff if n_eff else None)
    conteo_norm_en_pagina = Counter(n for n in norm_por_fila if n)

    norms_en_batch = {n for n in norm_por_fila if n}
    if primer_id_por_norm_precalc is not None:
        primer_id_por_norm = primer_id_por_norm_precalc
    else:
        created_at_desde = None
        if rows:
            fechas_c = [r.created_at for r in rows if getattr(r, "created_at", None) is not None]
            if fechas_c:
                created_at_desde = min(fechas_c) - timedelta(days=45)
        primer_id_por_norm = primer_reportado_id_por_norm_batch(
            db,
            norms_en_batch,
            created_at_desde=created_at_desde,
        )

    partes_por_fila = _observacion_reglas_carga(
        db,
        rows,
        cedulas_en_clientes,
        cedulas_bolivares,
        claves_doc_en_pagos,
        conteo_norm_en_pagina,
        primer_id_por_norm,
    )

    items: List[PagoReportadoListItem] = []
    for i, r in enumerate(rows):
        # Si Gemini ya dijo coincidencia exacta, no mezclar el comentario de Gemini en la observación:
        # evita que texto informativo dispare "falla validadores" y bloquee auto-import / cola.
        if _gemini_coincide_exacto_ok(getattr(r, "gemini_coincide_exacto", None)):
            obs_gemini = None
        else:
            obs_gemini = _observacion_solo_columnas(r.gemini_comentario)
        partes_reglas = partes_por_fila[i] if i < len(partes_por_fila) else []
        partes_final = partes_reglas + ([obs_gemini] if obs_gemini else [])
        observacion = " / ".join(partes_final) if partes_final else None
        if include_financial_fields:
            tasa_x, eq_usd = tasa_y_equivalente_usd_excel(
                db, r.fecha_pago, float(r.monto), r.moneda, tasas_por_fecha=tasas_por_fecha
            )
        else:
            tasa_x, eq_usd = None, None
        items.append(PagoReportadoListItem(
            id=r.id,
            referencia_interna=r.referencia_interna,
            nombres=r.nombres,
            apellidos=r.apellidos,
            cedula_display=f"{r.tipo_cedula}{r.numero_cedula}",
            institucion_financiera=r.institucion_financiera,
            monto=float(r.monto),
            moneda=r.moneda or "BS",
            tasa_cambio_bs_usd=tasa_x,
            equivalente_usd=eq_usd,
            fecha_pago=r.fecha_pago,
            numero_operacion=r.numero_operacion,
            fecha_reporte=r.created_at,
            estado=r.estado,
            gemini_coincide_exacto=r.gemini_coincide_exacto,
            observacion=observacion,
            correo_enviado_a=r.correo_enviado_a,
            tiene_recibo_pdf=bool(r.recibo_pdf),
            tiene_comprobante=bool(getattr(r, "comprobante_imagen_id", None)),
            canal_ingreso=getattr(r, "canal_ingreso", None),
        ))
    return items


def _query_reportados_falla_validadores_pendientes_exportar(
    db: Session,
    cedula: Optional[str],
    institucion: Optional[str],
) -> List[PagoReportado]:
    """Pendiente, en revisión o aprobado (legacy), aún no exportados a Excel; sin fechas (mismos filtros opcionales que el front)."""
    exportados_subq = select(PagoReportadoExportado.pago_reportado_id)
    q = select(PagoReportado).where(PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado")))
    q = q.where(~PagoReportado.id.in_(exportados_subq))
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
        q = q.where(cond_cedula)
    if institucion:
        ins = (institucion or "").strip()
        if ins:
            q = q.where(PagoReportado.institucion_financiera.ilike(f"%{ins}%"))
    q = q.order_by(PagoReportado.created_at.asc())
    return list(db.execute(q).scalars().all())


def _gemini_coincide_exacto_ok(val: Optional[str]) -> bool:
    """True si Gemini indicó coincidencia exacta (valores habituales en BD: true, 1)."""
    g = (val or "").strip().lower()
    return g in ("true", "1")


def _regularizar_reportados_gemini_ok_sin_falla_manual(
    db: Session, max_ids: int = 24, deadline_monotonic: Optional[float] = None
) -> None:
    """
    Al listar Cobros: si un reporte ya cumple validadores (misma regla que la cola), pasa a aprobado
    e intenta importar a `pagos` + cuotas como en el flujo público.

    Candidatos: Gemini OK (`true`/`1`) o Gemini `false` sin comentario (falso negativo frecuente);
    en ambos casos `reportado_falla_validadores_cobros` debe ser False (p. ej. sin DUPLICADO).
    Errores de API (`error`) no se regularizan aquí.
    """
    from app.services.cobros import cobros_publico_reporte_service as cpr

    gem_col = func.lower(func.trim(func.coalesce(PagoReportado.gemini_coincide_exacto, "")))
    com_trim = func.trim(func.coalesce(PagoReportado.gemini_comentario, ""))
    candidatos_regularizar = or_(
        gem_col.in_(("true", "1")),
        and_(gem_col == "false", com_trim == ""),
    )
    try:
        ids = list(
            db.execute(
                select(PagoReportado.id)
                .where(
                    PagoReportado.estado.in_(("en_revision", "aprobado")),
                    candidatos_regularizar,
                )
                .order_by(PagoReportado.id.desc())
                .limit(max_ids)
            ).scalars().all()
        )
    except Exception:
        return
    ids_colision_importado: List[int] = []
    for pid in ids:
        if deadline_monotonic is not None and time.monotonic() > deadline_monotonic:
            break
        try:
            pr = db.get(PagoReportado, pid)
            if pr is None:
                continue
            # Si ya existe un Pago con este comprobante, no ejecutar validadores de listado (muy costosos)
            # ni intentar_importar en cada GET: se agrupan al final en un solo UPDATE + commit.
            if getattr(pr, "estado", None) in ("en_revision", "aprobado") and pago_reportado_colisiona_tabla_pagos(
                db, pr
            ):
                ids_colision_importado.append(pid)
                continue
            if reportado_falla_validadores_cobros(db, pr):
                continue
            ref = (pr.referencia_interna or "").strip() or str(pr.id)
            if getattr(pr, "estado", None) == "en_revision":
                pr.estado = "aprobado"
                db.add(pr)
                db.commit()
                db.refresh(pr)
            if getattr(pr, "estado", None) == "aprobado":
                if deadline_monotonic is not None and time.monotonic() > deadline_monotonic:
                    break
                cpr.intentar_importar_reportado_automatico(db, pr, ref, "COBROS_COLA_REGULARIZA")
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    if ids_colision_importado:
        try:
            db.execute(
                update(PagoReportado)
                .where(PagoReportado.id.in_(ids_colision_importado))
                .values(estado="importado", updated_at=func.now())
            )
            db.commit()
            logger.info(
                "[COBROS_COLA_REGULARIZA] Marcados %s reportados como importado (comprobante ya en pagos).",
                len(ids_colision_importado),
            )
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass


def _regularizar_reportados_guarded(db: Session) -> None:
    """
    Ejecuta regularización con control de impacto en requests de lectura:
    - un solo runner por proceso (lock no bloqueante),
    - cooldown entre ejecuciones,
    - presupuesto de tiempo por request.
    """
    global _regulariza_last_run_monotonic
    now = time.monotonic()
    if now - _regulariza_last_run_monotonic < _REGULARIZA_MIN_INTERVAL_SEC:
        return
    if not _regulariza_lock.acquire(blocking=False):
        return
    try:
        now_inside = time.monotonic()
        if now_inside - _regulariza_last_run_monotonic < _REGULARIZA_MIN_INTERVAL_SEC:
            return
        _regulariza_last_run_monotonic = now_inside
        deadline = now_inside + (_REGULARIZA_TIME_BUDGET_MS / 1000.0)
        _regularizar_reportados_gemini_ok_sin_falla_manual(
            db,
            max_ids=_REGULARIZA_MAX_IDS_PER_RUN,
            deadline_monotonic=deadline,
        )
    finally:
        _regulariza_lock.release()


def _estado_label_excel(estado: str) -> str:
    m = {
        "pendiente": "Pendiente",
        "en_revision": "En revisión (manual)",
        "aprobado": "Aprobado",
        "rechazado": "Rechazado",
        "importado": "Importado a Pagos",
    }
    return m.get((estado or "").strip(), estado or "")


def _item_falla_validadores_cobros_excel(it: PagoReportadoListItem) -> bool:
    """
    True = requiere análisis manual (cola en pantalla / Excel "no validan").

    Si Gemini marcó coincidencia exacta (`true`/`1`), solo falla si queda observación de **reglas**
    (DUPLICADO, NO CLIENTES, etc.); el texto residual de Gemini no cuenta en ese caso (se omite al armar la observación).

    Si Gemini respondió `false` pero la observación armada está vacía (sin reglas ni columnas
    deducidas del comentario), no se exige paso manual: suele ser falso negativo con comentario vacío
    cuando los validadores determinísticos ya cuadran.

    `error` (fallo de API / sin clave) sigue exigiendo revisión manual.
    """
    obs = (it.observacion or "").strip()
    if _gemini_coincide_exacto_ok(it.gemini_coincide_exacto):
        return bool(obs)
    gem = (it.gemini_coincide_exacto or "").strip().lower()
    if gem == "error":
        return True
    if gem == "false":
        return bool(obs)
    return bool(obs)


def reportado_falla_validadores_cobros(db: Session, pr: PagoReportado) -> bool:
    """
    True si el reportado NO cumple los mismos validadores que el listado/Excel (Gemini + reglas de carga).
    Usado al registrar desde formulario público / Infopagos para no mandar a revisión manual lo que ya cumple.
    """
    items = _pago_reportado_list_items_from_rows(db, [pr])
    if not items:
        return True
    return _item_falla_validadores_cobros_excel(items[0])


def _persist_marcar_exportados_y_cola(db: Session, ids: List[int]) -> dict:
    """
    Inserta exportados + quita de pagos_pendiente_descargar y hace commit.
    """
    ya_exportados = set(
        db.execute(
            select(PagoReportadoExportado.pago_reportado_id).where(
                PagoReportadoExportado.pago_reportado_id.in_(ids)
            )
        ).scalars().all()
    )

    nuevos = [
        PagoReportadoExportado(pago_reportado_id=pid)
        for pid in ids
        if pid not in ya_exportados
    ]

    if nuevos:
        db.add_all(nuevos)

    res_cola = db.execute(
        delete(PagoPendienteDescargar).where(
            PagoPendienteDescargar.pago_reportado_id.in_(ids)
        )
    )
    quitados_cola_temporal = int(res_cola.rowcount or 0)

    db.commit()

    return {
        "ok": True,
        "marcados": len(nuevos),
        "ya_exportados": len(ya_exportados),
        "total_solicitados": len(ids),
        "quitados_cola_temporal": quitados_cola_temporal,
    }


def _condicion_cedula_pago_reportado(cedula: Optional[str]) -> Any:
    """Predicado SQL para búsqueda por cédula (mismo criterio en listado y KPIs)."""
    if not cedula or not str(cedula).strip():
        return None
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
    return cond_cedula


def _filtros_fecha_cedula_institucion_reportados(
    *,
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    cedula: Optional[str],
    institucion: Optional[str],
) -> List[Any]:
    """Fragmentos WHERE compartidos entre listado paginado y agregación KPI (evita divergencia)."""
    out: List[Any] = []
    if fecha_desde:
        out.append(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
    if fecha_hasta:
        out.append(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
    ced_pred = _condicion_cedula_pago_reportado(cedula)
    if ced_pred is not None:
        out.append(ced_pred)
    if institucion and institucion.strip():
        out.append(PagoReportado.institucion_financiera.ilike(f"%{institucion.strip()}%"))
    return out


def _where_clauses_cola_reportados(
    estado: Optional[str],
    incluir_exportados: bool,
    exportados_subq: Any,
    filtros: List[Any],
) -> List[Any]:
    """Predicados WHERE compartidos: cola pendiente / en_revision / aprobado (+ exportados + filtros fecha/cédula/banco)."""
    wh: List[Any] = []
    if estado == "aprobado":
        wh.append(PagoReportado.estado == "aprobado")
        if not incluir_exportados:
            wh.append(~PagoReportado.id.in_(exportados_subq))
    elif estado in ("pendiente", "en_revision"):
        wh.append(PagoReportado.estado == estado)
        if not incluir_exportados:
            wh.append(~PagoReportado.id.in_(exportados_subq))
    else:
        wh.append(PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado")))
        if not incluir_exportados:
            wh.append(~PagoReportado.id.in_(exportados_subq))
    wh.extend(filtros)
    return wh


def _primer_id_por_norm_global_para_where(db: Session, wh: List[Any]) -> Dict[str, int]:
    """
    Calcula una sola vez el mapa documento_normalizado -> id del primer PagoReportado (cola),
    para no repetir escaneos masivos de `pagos_reportados` en cada lote de 400 filas del listado/KPIs.
    """
    if not wh:
        return {}
    lite = (
        select(PagoReportado.numero_operacion, PagoReportado.referencia_interna)
        .select_from(PagoReportado)
        .where(*wh)
    )
    all_norms: Set[str] = set()
    res = db.execute(lite)
    while True:
        block = res.fetchmany(2000)
        if not block:
            break
        for op, ref in block:
            _, n_eff = documento_numero_desde_pago_reportado(
                SimpleNamespace(numero_operacion=op, referencia_interna=ref)
            )
            if n_eff:
                all_norms.add(n_eff)
    if not all_norms:
        return {}
    return primer_reportado_id_por_norm_peer_first_map(db, all_norms)


def _primer_maps_scope_key(
    *,
    incluir_exportados: bool,
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    cedula: Optional[str],
    institucion: Optional[str],
) -> str:
    """Clave estable para mapas de duplicados: mismo criterio que `wh_primer_scope` (cola completa + filtros)."""
    c = (cedula or "").strip().upper()
    i = (institucion or "").strip().lower()
    return f"{int(bool(incluir_exportados))}|{fecha_desde!s}|{fecha_hasta!s}|{c}|{i}"


def _cobros_primer_maps_revision_token(db: Session) -> tuple:
    """
    Token barato para invalidar cache al cambiar cola, exportados o cartera (nuevo pago / doc).

    Incluye `max(Pago.id)` (índice PK, lectura O(1) típica) para que nuevos `pagos` invaliden
    `_numeros_operacion_presentes_en_pagos` sin full scan.
    """
    row = db.execute(
        select(
            func.count(PagoReportado.id),
            func.max(PagoReportado.updated_at),
        ).where(PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado")))
    ).one()
    n_exp = int(db.execute(select(func.count()).select_from(PagoReportadoExportado)).scalar_one())
    max_pago_id = db.execute(select(func.max(Pago.id))).scalar()
    return (
        int(row[0] or 0),
        row[1],
        int(n_exp),
        int(max_pago_id or 0),
    )


def _prune_primer_maps_triple_cache_unlocked() -> None:
    """Mantiene acotado el dict; caller debe tener `_primer_maps_triple_cache_lock`."""
    global _primer_maps_triple_cache
    if len(_primer_maps_triple_cache) <= _PRIMER_MAPS_CACHE_MAX_ENTRIES:
        return
    # Eliminar entradas más antiguas por `monotonic_ts`.
    items = sorted(
        _primer_maps_triple_cache.items(),
        key=lambda kv: kv[1][1],
    )
    drop = len(items) - _PRIMER_MAPS_CACHE_MAX_ENTRIES
    for k, _ in items[:drop]:
        _primer_maps_triple_cache.pop(k, None)


def _compute_primer_triple_for_where(
    db: Session, wh: List[Any]
) -> Tuple[Dict[str, int], Dict[str, int], Set[str]]:
    """Precalcula mapas duplicados / nº operación / presencia en pagos para un WHERE de cola."""
    primer_precalc = _primer_id_por_norm_global_para_where(db, wh)
    primer_num_op = _primer_id_por_numero_operacion_para_where(db, wh)
    numeros_en_pagos = _numeros_operacion_presentes_en_pagos(
        db, set(primer_num_op.keys())
    )
    return primer_precalc, primer_num_op, numeros_en_pagos


def _get_primer_triple_cached(
    db: Session,
    wh: List[Any],
    scope_key: str,
) -> Tuple[Dict[str, int], Dict[str, int], Set[str]]:
    """
    Devuelve (primer_precalc, primer_num_op, numeros_en_pagos) reusando cache si la revisión no cambió.

    Thread-safe en el dict de cache; el cálculo pesado ocurre fuera del lock para no serializar requests.
    """
    rev = _cobros_primer_maps_revision_token(db)
    now = time.monotonic()
    with _primer_maps_triple_cache_lock:
        ent = _primer_maps_triple_cache.get(scope_key)
        if ent is not None:
            stored_rev, ts, a, b, c_f = ent
            if stored_rev == rev and (now - ts) < _PRIMER_MAPS_CACHE_TTL_SEC:
                logger.debug(
                    "[COBROS_CACHE] primer_triple hit scope=%s rev=%s age_s=%.2f",
                    scope_key,
                    rev,
                    now - ts,
                )
                return a, b, set(c_f)

    primer_precalc, primer_num_op, numeros_en_pagos = _compute_primer_triple_for_where(db, wh)
    rev_after = _cobros_primer_maps_revision_token(db)
    now_store = time.monotonic()
    with _primer_maps_triple_cache_lock:
        _primer_maps_triple_cache[scope_key] = (
            rev_after,
            now_store,
            primer_precalc,
            primer_num_op,
            frozenset(numeros_en_pagos),
        )
        _prune_primer_maps_triple_cache_unlocked()
    logger.debug(
        "[COBROS_CACHE] primer_triple miss store scope=%s rev=%s",
        scope_key,
        rev_after,
    )
    return primer_precalc, primer_num_op, numeros_en_pagos


def _list_pagos_reportados_payload(
    db: Session,
    *,
    estado: Optional[str],
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    cedula: Optional[str],
    institucion: Optional[str],
    page: int,
    per_page: int,
    incluir_exportados: bool = False,
    emit_manual_estado_counts_for_kpis: bool = False,
) -> dict:
    """
    Misma lógica que GET /pagos-reportados (reutilizada por listado-y-kpis).

    Si `emit_manual_estado_counts_for_kpis` y `estado` es None (lista la cola completa
    pendiente+en_revision+aprobado), se añade `_manual_kpi_counts` al dict de retorno
    para evitar un segundo barrido completo en listado-y-kpis (solo uso interno).
    """
    _regularizar_reportados_guarded(db)
    exportados_subq = select(PagoReportadoExportado.pago_reportado_id)
    filtros = _filtros_fecha_cedula_institucion_reportados(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
    )

    # Rechazado / importado: listado sin filtro de validadores (auditoría por estado).
    if estado in ("rechazado", "importado"):
        q = select(PagoReportado).where(PagoReportado.estado == estado)
        count_q = select(func.count(PagoReportado.id)).where(PagoReportado.estado == estado)
        for w in filtros:
            q = q.where(w)
            count_q = count_q.where(w)
        total = int(db.execute(count_q).scalar() or 0)
        q = q.order_by(
            case((PagoReportado.estado == "rechazado", 1), else_=0),
            PagoReportado.created_at.asc(),
        ).offset((page - 1) * per_page).limit(per_page)
        rows = db.execute(q).scalars().all()
        items = _pago_reportado_list_items_from_rows(db, rows)
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    # Cola manual: pendiente / en_revision / aprobado que NO cumplen validadores (misma regla que Excel Cobros).
    # Cumplen 100% (reglas OK; Gemini true o false sin observación) → no entran aquí; flujo automático fuera de la cola.
    wh = _where_clauses_cola_reportados(estado, incluir_exportados, exportados_subq, filtros)
    # Con pestaña por estado, el listado filtra filas con `wh`, pero la resolución de duplicados
    # (primer reporte por documento / nº operación) debe usar la MISMA cola completa que KPIs
    # (pendiente+en_revision+aprobado); si no, totales y tarjetas divergen entre vistas.
    wh_primer_scope = (
        _where_clauses_cola_reportados(None, incluir_exportados, exportados_subq, filtros)
        if estado in ("pendiente", "en_revision", "aprobado")
        else wh
    )
    primer_scope_key = _primer_maps_scope_key(
        incluir_exportados=incluir_exportados,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
    )
    primer_precalc, primer_num_op, numeros_en_pagos = _get_primer_triple_cached(
        db, wh_primer_scope, primer_scope_key
    )
    q = select(PagoReportado).where(*wh).order_by(
        case((PagoReportado.estado == "rechazado", 1), else_=0),
        PagoReportado.created_at.asc(),
    )

    emit_counts = bool(emit_manual_estado_counts_for_kpis and estado is None)
    by_estado_manual: Dict[str, int] = {"pendiente": 0, "en_revision": 0, "aprobado": 0}

    batch = _COBROS_LISTADO_SCAN_BATCH
    offset_scan = 0
    skip_need = (page - 1) * per_page
    take_need = per_page
    page_ids_ordered: List[int] = []
    total = 0
    while True:
        rows = db.execute(q.offset(offset_scan).limit(batch)).scalars().all()
        if not rows:
            break
        for it in _pago_reportado_list_items_from_rows(
            db,
            rows,
            primer_id_por_norm_precalc=primer_precalc,
            include_financial_fields=False,
        ):
            # Regla innegociable: duplicado = mismo numero_operacion exacto/canonico.
            # En cola operativa se muestra solo el primer reporte; reenvíos no se listan.
            num_key = _numero_operacion_canonico(getattr(it, "numero_operacion", None))
            if num_key:
                first_id = primer_num_op.get(num_key)
                if first_id is not None and int(it.id) != int(first_id):
                    continue
                if num_key in numeros_en_pagos:
                    continue
            if not _item_falla_validadores_cobros_excel(it):
                continue
            total += 1
            if emit_counts:
                st = (it.estado or "").strip()
                if st in by_estado_manual:
                    by_estado_manual[st] += 1
            if skip_need > 0:
                skip_need -= 1
                continue
            if take_need > 0:
                page_ids_ordered.append(int(it.id))
                take_need -= 1
        offset_scan += len(rows)

    page_items: List[PagoReportadoListItem] = []
    if page_ids_ordered:
        seen: Set[int] = set()
        uniq_ids: List[int] = []
        for pid in page_ids_ordered:
            if pid in seen:
                continue
            seen.add(pid)
            uniq_ids.append(pid)
        rows_page = db.execute(select(PagoReportado).where(PagoReportado.id.in_(uniq_ids))).scalars().all()
        by_id = {int(r.id): r for r in rows_page}
        ordered_pr = [by_id[i] for i in uniq_ids if i in by_id]
        if ordered_pr:
            page_items = _pago_reportado_list_items_from_rows(
                db,
                ordered_pr,
                primer_id_por_norm_precalc=primer_precalc,
                include_financial_fields=True,
            )

    out: Dict[str, Any] = {"items": page_items, "total": total, "page": page, "per_page": per_page}
    if emit_counts:
        out["_manual_kpi_counts"] = dict(by_estado_manual)
    return out


def _kpis_pagos_reportados_payload(
    db: Session,
    *,
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    cedula: Optional[str],
    institucion: Optional[str],
    incluir_exportados: bool = False,
    manual_queue_counts: Optional[Dict[str, int]] = None,
) -> dict:
    """
    Conteos por estado con mismos filtros fecha/cédula/institución que el listado.
    pendiente / en_revision / aprobado: solo los que NO cumplen validadores (cola de análisis manual).
    importado / rechazado: totales SQL (estados terminales).

    Si `manual_queue_counts` viene del listado (mismo barrido), no se vuelve a escanear la cola.
    """
    filtros = _filtros_fecha_cedula_institucion_reportados(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
    )
    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0, "importado": 0}

    if incluir_exportados:
        base_term = select(PagoReportado.estado, func.count(PagoReportado.id).label("cnt")).where(
            PagoReportado.estado.in_(("importado", "rechazado"))
        )
    else:
        base_term = select(PagoReportado.estado, func.count(PagoReportado.id).label("cnt")).where(
            PagoReportado.estado.in_(("importado", "rechazado"))
        )
    for w in filtros:
        base_term = base_term.where(w)
    base_term = base_term.group_by(PagoReportado.estado)
    for row in db.execute(base_term).all():
        if row.estado in counts:
            counts[row.estado] = int(row.cnt or 0)

    if manual_queue_counts is not None:
        counts["pendiente"] = int(manual_queue_counts.get("pendiente", 0))
        counts["en_revision"] = int(manual_queue_counts.get("en_revision", 0))
        counts["aprobado"] = int(manual_queue_counts.get("aprobado", 0))
    else:
        exportados_subq = select(PagoReportadoExportado.pago_reportado_id)
        wh_kpi = _where_clauses_cola_reportados(None, incluir_exportados, exportados_subq, filtros)
        kpi_scope_key = _primer_maps_scope_key(
            incluir_exportados=incluir_exportados,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            cedula=cedula,
            institucion=institucion,
        )
        primer_kpi, _, _ = _get_primer_triple_cached(db, wh_kpi, kpi_scope_key)
        q_scan = select(PagoReportado).where(*wh_kpi).order_by(PagoReportado.created_at.asc())

        batch = _COBROS_LISTADO_SCAN_BATCH
        offset_scan = 0
        while True:
            rows_b = db.execute(q_scan.offset(offset_scan).limit(batch)).scalars().all()
            if not rows_b:
                break
            for it in _pago_reportado_list_items_from_rows(
                db,
                rows_b,
                primer_id_por_norm_precalc=primer_kpi,
                include_financial_fields=False,
            ):
                if not _item_falla_validadores_cobros_excel(it):
                    continue
                st = (it.estado or "").strip()
                if st in ("pendiente", "en_revision", "aprobado"):
                    counts[st] += 1
            offset_scan += len(rows_b)

    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado", "importado"))
    return counts


@router.get("/pagos-reportados", response_model=dict)
def list_pagos_reportados(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=300),
    incluir_exportados: bool = Query(
        False,
        description="Si true, incluye filas ya exportadas al Excel de corrección (siguen gestionables en Cobranzas).",
    ),
):
    """
    Lista paginada de pagos reportados con filtros.

    Sin `estado` o con `pendiente` / `en_revision` / `aprobado`: solo filas que **no cumplen validadores**
    (Excel Cobros: Gemini false/error u observación de reglas; si Gemini es true y no hay observación, cumple 100%
    y no se lista — sigue el proceso automático fuera de esta cola).

    `estado=importado` o `rechazado`: listado completo de ese estado (sin filtro de validadores).

    `incluir_exportados=true`: incluye pendiente/en revisión/aprobado ya exportados al Excel de corrección.

    Incluye sin distincion reportes de Infopagos (`canal_ingreso=infopagos`) y del formulario publico del deudor
    (`cobros_publico`); mismas reglas de edicion, aprobacion, rechazo e import a `pagos`.
    """
    return _list_pagos_reportados_payload(
        db,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
        page=page,
        per_page=per_page,
        incluir_exportados=incluir_exportados,
    )


@router.get("/pagos-reportados/kpis", response_model=dict)
def kpis_pagos_reportados(
    db: Session = Depends(get_db),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
    incluir_exportados: bool = Query(
        False,
        description="Alinear conteos con listado cuando se incluyen exportados al Excel.",
    ),
):
    """Conteos por estado; mismos filtros que el listado. pendiente/en_revision/aprobado solo cuentan fallas de validadores."""
    return _kpis_pagos_reportados_payload(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
        incluir_exportados=incluir_exportados,
    )


@router.get("/pagos-reportados/listado-y-kpis", response_model=dict)
def list_pagos_reportados_y_kpis(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=300),
    incluir_exportados: bool = Query(
        False,
        description="Igual que GET /pagos-reportados: muestra filas ya exportadas al Excel para seguir gestionándolas.",
    ),
):
    """
    Listado paginado + KPIs en una sola petición (mismos query params que GET /pagos-reportados).

    KPIs alineados con el listado (con o sin filas ya exportadas al Excel, según incluir_exportados).

    Sin filtro `estado`: un solo barrido de la cola manual alimenta listado + KPIs (mitad de trabajo BD vs antes).
    Con `estado` o pestaña filtrada: listado acotado + KPIs con barrido completo (misma semántica que antes).
    """
    emit_kpi_from_list = estado is None
    lista = _list_pagos_reportados_payload(
        db,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
        page=page,
        per_page=per_page,
        incluir_exportados=incluir_exportados,
        emit_manual_estado_counts_for_kpis=emit_kpi_from_list,
    )
    manual_queue = lista.pop("_manual_kpi_counts", None) if emit_kpi_from_list else None
    kpis = _kpis_pagos_reportados_payload(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
        incluir_exportados=incluir_exportados,
        manual_queue_counts=manual_queue,
    )
    return {**lista, "kpis": kpis}


@router.get("/pagos-reportados/duplicados-eliminados", response_model=dict)
def list_duplicados_eliminados(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=300),
):
    """Bitácora operativa de reportes auto-eliminados por duplicado de número de operación."""
    total = int(
        db.execute(
            select(func.count(PagoReportado.id)).where(
                PagoReportado.estado == "eliminado_duplicado"
            )
        ).scalar()
        or 0
    )
    rows = db.execute(
        select(PagoReportado)
        .where(PagoReportado.estado == "eliminado_duplicado")
        .order_by(PagoReportado.updated_at.desc(), PagoReportado.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).scalars().all()
    items = [
        {
            "id": r.id,
            "referencia_interna": r.referencia_interna,
            "numero_operacion": r.numero_operacion,
            "estado": r.estado,
            "motivo_rechazo": r.motivo_rechazo,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get(
    "/pagos-reportados/tendencia-fallos-gemini",
    response_model=TendenciaFallosGeminiResponse,
)
def tendencia_fallos_gemini_por_dia(
    db: Session = Depends(get_db),
    dias: int = Query(
        90,
        ge=7,
        le=366,
        description="Ventana hacia atras en dias calendario (zona Caracas).",
    ),
):
    """
    Serie diaria por fecha de creacion del reporte: fallos cuando la verificacion automatica
    respondio NO (gemini_coincide_exacto = false), frente al total con respuesta true/false ese dia.
    """
    tz = ZoneInfo("America/Caracas")
    hoy = datetime.now(tz).date()
    desde = hoy - timedelta(days=dias - 1)

    rows = db.execute(
        text(
            """
            SELECT CAST(created_at AS date) AS dia,
              COUNT(*) FILTER (
                WHERE LOWER(TRIM(COALESCE(gemini_coincide_exacto, ''))) = 'false'
              )::int AS fallos_no,
              COUNT(*) FILTER (
                WHERE LOWER(TRIM(COALESCE(gemini_coincide_exacto, ''))) IN ('true', 'false')
              )::int AS verificados_gemini
            FROM pagos_reportados
            WHERE CAST(created_at AS date) >= :desde
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"desde": desde},
    ).mappings().all()

    by_day: Dict[date, Tuple[int, int]] = {
        r["dia"]: (int(r["fallos_no"]), int(r["verificados_gemini"])) for r in rows
    }

    puntos: List[TendenciaFalloGeminiPunto] = []
    d = desde
    while d <= hoy:
        fallos_no, verif = by_day.get(d, (0, 0))
        pct: Optional[float] = None
        if verif > 0:
            pct = round(100.0 * fallos_no / verif, 1)
        puntos.append(
            TendenciaFalloGeminiPunto(
                fecha=d.isoformat(),
                fallos_no=fallos_no,
                verificados_gemini=verif,
                pct_fallo=pct,
            )
        )
        d += timedelta(days=1)

    return TendenciaFallosGeminiResponse(
        puntos=puntos,
        fecha_desde=desde.isoformat(),
        fecha_hasta=hoy.isoformat(),
        dias=dias,
        zona="America/Caracas",
        nota=(
            "Fallos (NO): gemini_coincide_exacto = false. "
            "Verificados: respuesta true o false (sin null/vacio). "
            "Agrupado por dia de creacion del reporte (BD)."
        ),
    )


@router.get("/pagos-reportados/exportar-aprobados-excel")
def exportar_pagos_aprobados_excel(
    db: Session = Depends(get_db),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
):
    """
    Solo filas que no cumplen validadores (Gemini NO/error u observación de reglas), pendiente, en revisión
    o aprobado (legacy), aún no exportadas. Al descargar: van al Excel y se marcan en pagos_reportados_exportados; entonces dejan
    de mostrarse en listado (hasta incluir_exportados=true). Si el usuario no descarga, esas filas siguen en pantalla.
    Filtros opcionales: cédula, institución; sin fechas.
    """
    from io import BytesIO
    from openpyxl import Workbook
    from datetime import datetime

    rows = _query_reportados_falla_validadores_pendientes_exportar(
        db,
        cedula=(cedula or "").strip() or None,
        institucion=(institucion or "").strip() or None,
    )
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="No hay pagos reportados pendientes, en revisión o aprobados sin exportar (con los filtros indicados).",
        )

    items = _pago_reportado_list_items_from_rows(db, rows)
    items = [it for it in items if _item_falla_validadores_cobros_excel(it)]
    if not items:
        raise HTTPException(
            status_code=400,
            detail="No hay filas que fallen validadores entre los candidatos (Gemini NO/error u observación). "
            "Revise filtros o corrija datos en pantalla.",
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "No validan carga masiva"

    headers = [
        "Referencia",
        "Nombre",
        "Cedula",
        "Banco",
        "Monto",
        "Moneda",
        "Tasa cambio (Bs/USD)",
        "Fecha pago",
        "Numero operacion",
        "Fecha reporte",
        "Observacion",
        "Estado",
        "Monto USD",
    ]
    ws.append(headers)

    for it in items:
        monto_val = float(it.monto)
        tasa_c = it.tasa_cambio_bs_usd
        eq_u = it.equivalente_usd
        fr = it.fecha_reporte
        ws.append(
            [
                it.referencia_interna,
                f"{(it.nombres or '').strip()} {(it.apellidos or '').strip()}".strip(),
                it.cedula_display,
                it.institucion_financiera,
                round(monto_val, 2),
                it.moneda or "BS",
                round(tasa_c, 4) if tasa_c is not None else None,
                it.fecha_pago.isoformat() if it.fecha_pago else "",
                it.numero_operacion or "",
                fr.strftime("%d/%m/%Y %H:%M") if fr else "",
                it.observacion or "",
                _estado_label_excel(it.estado),
                round(eq_u, 2) if eq_u is not None else None,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()

    ids = [it.id for it in items]
    stats = _persist_marcar_exportados_y_cola(db, ids)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pagos_reportados_falla_validadores_{ts}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
            "X-Export-Marcados": str(stats["marcados"]),
            "X-Export-Ya-Exportados": str(stats["ya_exportados"]),
            "X-Export-Quitados-Cola": str(stats["quitados_cola_temporal"]),
            "X-Export-Total-Filas": str(len(items)),
        },
    )


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
    tasa_x, eq_usd = tasa_y_equivalente_usd_excel(
        db, pr.fecha_pago, float(pr.monto), pr.moneda or "BS"
    )
    pago_existente_id: Optional[int] = primer_pago_id_si_existe_para_claves_reportado(db, pr)
    prestamo_existente_id: Optional[int] = None
    pago_existente_estado: Optional[str] = None
    pago_existente_fecha_pago: Optional[date] = None
    prestamo_objetivo_id: Optional[int] = None
    prestamo_objetivo_multiple: Optional[bool] = None
    prestamo_duplicado_es_objetivo: Optional[bool] = None
    if pago_existente_id is not None:
        p_exist = db.execute(select(Pago).where(Pago.id == pago_existente_id)).scalars().first()
        if p_exist:
            prestamo_existente_id = getattr(p_exist, "prestamo_id", None)
            pago_existente_estado = getattr(p_exist, "estado", None)
            fp = getattr(p_exist, "fecha_pago", None)
            if fp is not None:
                pago_existente_fecha_pago = (
                    fp.date() if isinstance(fp, datetime) else fp
                )
    try:
        cedula_norm = _normalize_cedula_for_client_lookup(
            ((pr.tipo_cedula or "") + (pr.numero_cedula or ""))
            .replace("-", "")
            .replace(" ", "")
            .strip()
            .upper()
        )
        variants = _cedula_lookup_variants(cedula_norm)
        if variants:
            cedula_lookup = func.upper(
                func.replace(func.replace(Cliente.cedula, "-", ""), " ", "")
            )
            cliente = db.execute(
                select(Cliente).where(cedula_lookup.in_(variants))
            ).scalars().first()
            if cliente:
                prestamos_aprob = db.execute(
                    select(Prestamo.id)
                    .where(
                        Prestamo.cliente_id == cliente.id,
                        func.upper(Prestamo.estado) == "APROBADO",
                    )
                    .order_by(Prestamo.id.desc())
                ).scalars().all()
                if prestamos_aprob:
                    prestamo_objetivo_id = int(prestamos_aprob[0])
                    prestamo_objetivo_multiple = len(prestamos_aprob) > 1
    except Exception:
        # No romper detalle por diagnóstico comparativo; los campos quedan null.
        prestamo_objetivo_id = None
        prestamo_objetivo_multiple = None
    if (
        prestamo_existente_id is not None
        and prestamo_objetivo_id is not None
    ):
        prestamo_duplicado_es_objetivo = int(prestamo_existente_id) == int(
            prestamo_objetivo_id
        )
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
        tasa_cambio_bs_usd=tasa_x,
        equivalente_usd=eq_usd,
        ruta_comprobante=pr.ruta_comprobante,
        tiene_comprobante=bool(getattr(pr, "comprobante_imagen_id", None)),
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
        canal_ingreso=getattr(pr, "canal_ingreso", None),
        duplicado_en_pagos=bool(pago_existente_id is not None),
        pago_existente_id=pago_existente_id,
        prestamo_existente_id=prestamo_existente_id,
        pago_existente_estado=pago_existente_estado,
        pago_existente_fecha_pago=pago_existente_fecha_pago,
        prestamo_objetivo_id=prestamo_objetivo_id,
        prestamo_objetivo_multiple=prestamo_objetivo_multiple,
        prestamo_duplicado_es_objetivo=prestamo_duplicado_es_objetivo,
    )


def _emails_cliente_pago_reportado(db: Session, pr: PagoReportado) -> List[str]:
    """
    Correos del cliente para enviar recibo (hasta 2: principal + secundario).
    Usa pr.correo_enviado_a si existe (admite varios separados por ; o ,); si no, busca por cédula en clientes.
    """
    to_raw = (pr.correo_enviado_a or "").strip()
    if to_raw and "@" in to_raw:
        parts = [p.strip() for p in re.split(r"[;,]", to_raw) if p.strip() and "@" in p.strip()]
        if parts:
            out: List[str] = []
            seen: set[str] = set()
            for p in parts:
                k = p.lower()
                if k not in seen:
                    seen.add(k)
                    out.append(p)
            return out[:2]
    cedula_raw = (f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}").replace("-", "").replace(" ", "").strip().upper()
    if not cedula_raw:
        return []
    cedula_norm = _normalize_cedula_for_client_lookup(cedula_raw)
    variants = _cedula_lookup_variants(cedula_norm)
    if not variants:
        return []
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(select(Cliente).where(cedula_lookup.in_(variants))).scalars().first()
    if cliente:
        return emails_destino_desde_objeto(cliente)
    return []


def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):
    h = PagoReportadoHistorial(
        pago_reportado_id=pago_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_email=usuario_email,
        motivo=motivo,
    )
    db.add(h)


def _marcar_reportados_como_eliminado_duplicado(
    db: Session,
    *,
    dup_rows: List[Tuple[int, str, str]],
    master_id: int,
    master_ref: str,
    num_key: str,
    usuario_email: Optional[str],
    via: str,
) -> Tuple[int, List[str]]:
    """
    Eliminación lógica por duplicado de número de operación:
    marca estado `eliminado_duplicado` y registra historial operativo.
    """
    dup_ids = [rid for rid, _rref, st in dup_rows if st in ("pendiente", "en_revision", "rechazado")]
    dup_refs = [rref for _rid, rref, st in dup_rows if st in ("pendiente", "en_revision", "rechazado")]
    if not dup_ids:
        return 0, []
    # Excepción confirmada: Mercantil en duplicado por numero_operacion -> revisión manual.
    if _es_banco_mercantil(master_ref):
        db.execute(
            update(PagoReportado)
            .where(PagoReportado.id.in_(dup_ids))
            .values(
                estado="en_revision",
                motivo_rechazo=(
                    f"Duplicado por numero_operacion={num_key} con banco Mercantil; "
                    "excepción activa, requiere revisión manual."
                )[:2000],
            )
        )
        for rid in dup_ids:
            _registrar_historial(
                db,
                rid,
                "pendiente",
                "en_revision",
                usuario_email,
                "Excepción Mercantil aplicada por duplicado de número de operación.",
            )
        return 0, dup_refs
    motivo = (
        f"Auto-eliminado por duplicado de numero_operacion={num_key}. "
        f"Se conserva reporte maestro id={master_id} ref={master_ref or master_id} via={via}."
    )[:2000]
    db.execute(
        update(PagoReportado)
        .where(PagoReportado.id.in_(dup_ids))
        .values(estado="eliminado_duplicado", motivo_rechazo=motivo)
    )
    prev_states = {rid: st for rid, _rref, st in dup_rows}
    for rid in dup_ids:
        _registrar_historial(
            db,
            rid,
            prev_states.get(rid, "pendiente"),
            "eliminado_duplicado",
            usuario_email,
            motivo,
        )
    return len(dup_ids), dup_refs



def _crear_pago_desde_reportado_y_aplicar_cuotas(db: Session, pr: PagoReportado, usuario_email: Optional[str]) -> None:
    """Tras aprobar un pago reportado: crea registro en tabla pagos y aplica a cuotas (cascada) para que prestamos y estado de cuenta se actualicen. Debe llamarse ANTES de commit; si falla lanza HTTPException."""
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
    num_doc_raw, num_doc = documento_numero_desde_pago_reportado(pr)
    ya = primer_pago_id_si_existe_para_claves_reportado(db, pr)
    if ya is not None:
        logger.info(
            "[COBROS] Aprobar ref=%s: ya existe pago id=%s (claves reporte); omitir creacion (idempotente).",
            pr.referencia_interna,
            ya,
        )
        return
    _rechazar_aprobacion_si_documento_ya_en_pagos(db, pr)
    fecha_ts = datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now()
    moneda_pr = ((getattr(pr, "moneda", None) or "USD") or "").strip().upper()
    if moneda_pr == "USDT":
        moneda_pr = "USD"
    monto_float = float(pr.monto or 0)
    monto_bs_original: Optional[float] = None
    tasa_aplicada: Optional[float] = None
    fecha_tasa_ref: Optional[date] = None
    if moneda_pr == "BS":
        if not pr.fecha_pago:
            raise HTTPException(
                status_code=400,
                detail="Fecha de pago requerida para convertir bolivares a USD al aplicar a cuotas.",
            )
        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)
        if tasa_obj is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No hay tasa de cambio oficial registrada para la fecha de pago "
                    f"{pr.fecha_pago.isoformat()}. Registre la tasa antes de aprobar pagos en bolívares."
                ),
            )
        tasa_aplicada = float(tasa_obj.tasa_oficial)
        monto_bs_original = monto_float
        try:
            monto_float = convertir_bs_a_usd(monto_bs_original, tasa_aplicada)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        fecha_tasa_ref = pr.fecha_pago
    elif moneda_pr != "USD":
        raise HTTPException(status_code=400, detail=f"Moneda no soportada al importar desde cobros: {moneda_pr}")
    monto = Decimal(str(round(monto_float, 2)))
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto del reporte debe ser mayor que cero.")
    ref_pago = (num_doc or num_doc_raw or "Cobros")[:100]
    rpc_tr = (pr.referencia_interna or "").strip()[:100]
    notas_pago = None
    if rpc_tr and num_doc_raw and rpc_tr != num_doc_raw:
        notas_pago = f"Ref. interna reporte: {rpc_tr}"
    img_id = (getattr(pr, "comprobante_imagen_id", None) or "").strip()
    link_comp = url_comprobante_imagen_absoluta(img_id) if img_id else None
    doc_nom = ((pr.comprobante_nombre or "").strip()[:255] or None) if img_id else None
    row = Pago(
        cedula_cliente=cedula_norm,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_ts,
        monto_pagado=monto,
        numero_documento=num_doc,
        institucion_bancaria=(pr.institucion_financiera or "").strip()[:255] or None,
        # Se crea conciliado y se aplica en cascada en la misma transaccion; no debe nacer como PENDIENTE.
        estado="PAGADO",
        referencia_pago=ref_pago,
        notas=notas_pago,
        usuario_registro=usuario_email or "cobros@rapicredit.com",
        conciliado=True,
        fecha_conciliacion=datetime.now(),
        verificado_concordancia="SI",
        moneda_registro=moneda_pr,
        monto_bs_original=Decimal(str(round(monto_bs_original, 2))) if monto_bs_original is not None else None,
        tasa_cambio_bs_usd=Decimal(str(tasa_aplicada)) if tasa_aplicada is not None else None,
        fecha_tasa_referencia=fecha_tasa_ref,
        link_comprobante=link_comp,
        documento_nombre=doc_nom,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    try:
        _aplicar_pago_a_cuotas_interno(row, db)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    row.estado = "PAGADO"
    logger.info("[COBROS] Aprobar ref=%s: creado pago id=%s y aplicado a cuotas del prestamo %s.", pr.referencia_interna, row.id, prestamo.id)


@router.post("/pagos-reportados/{pago_id}/aprobar")
def aprobar_pago_reportado(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Aprueba el pago reportado: genera recibo PDF, envía por correo, guarda en recibos/."""
    total_t0 = time.perf_counter()
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    if pr.estado == "importado":
        return {"ok": True, "mensaje": "Ya importado a la tabla de pagos."}

    completar_solo_recibo = False
    registrar_historial_aprobacion = True
    if pr.estado == "aprobado":
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            db.commit()
        except HTTPException:
            pass
        db.refresh(pr)
        if getattr(pr, "recibo_pdf", None):
            return {"ok": True, "mensaje": "Ya estaba aprobado."}
        if primer_pago_id_si_existe_para_claves_reportado(db, pr) is None:
            return {"ok": True, "mensaje": "Ya estaba aprobado."}
        logger.info(
            "[COBROS] Aprobar id=%s ref=%s: aprobado y pago en cartera, sin PDF persistido; completando recibo/correo.",
            pr.id,
            pr.referencia_interna,
        )
        completar_solo_recibo = True
        registrar_historial_aprobacion = False

    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")

    estado_anterior: Optional[str] = None
    if not completar_solo_recibo:
        if pr.estado in ("pendiente", "en_revision"):
            _rechazar_aprobacion_si_documento_ya_en_pagos(db, pr)
        num_key = _numero_operacion_canonico(getattr(pr, "numero_operacion", None))
        if num_key:
            _lock_numero_operacion_canonico(db, num_key)
            hermanos = _duplicados_reportados_por_numero_operacion(
                db, numero_key=num_key, excluir_id=pr.id
            )
            if hermanos:
                first_id = min([pr.id] + [rid for rid, _rref, _st in hermanos])
                if int(first_id) != int(pr.id):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Duplicado por número de operación: este reporte no es el primero registrado. "
                            f"Gestione primero el reporte ID {first_id}."
                        ),
                    )
        estado_anterior = pr.estado
        pr.estado = "aprobado"
        pr.motivo_rechazo = None
        pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

        try:
            fase_db_t0 = time.perf_counter()
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            # Doble envío del mismo comprobante (segundos): tras aprobar el primero, eliminar hermanos.
            num_key = _numero_operacion_canonico(getattr(pr, "numero_operacion", None))
            if num_key:
                dup_rows = _duplicados_reportados_por_numero_operacion(
                    db, numero_key=num_key, excluir_id=pr.id
                )
                n_dup, dup_refs = _marcar_reportados_como_eliminado_duplicado(
                    db,
                    dup_rows=dup_rows,
                    master_id=pr.id,
                    master_ref=str(pr.institucion_financiera or ""),
                    num_key=num_key,
                    usuario_email=usuario_email,
                    via="aprobar_directo",
                )
                if n_dup > 0:
                    logger.info(
                        "[COBROS] Aprobado id=%s ref=%s: marcados %s duplicados por numero_operacion=%s refs=%s",
                        pr.id,
                        pr.referencia_interna,
                        n_dup,
                        num_key,
                        ", ".join([x for x in dup_refs if x])[:300],
                    )
            db.commit()
            _log_fase_aprobacion(
                flujo="aprobar_directo",
                fase="db_aprobacion_commit",
                pago_id=pago_id,
                referencia=str(pr.referencia_interna or ""),
                start_ts=fase_db_t0,
            )
        except HTTPException:
            db.rollback()
            raise
        except (ProgrammingError, OperationalError) as e:
            db.rollback()
            logger.exception("[COBROS] Aprobar ref=%s: error de BD (¿migración pendiente?): %s", pr.referencia_interna, e)
            raise HTTPException(
                status_code=503,
                detail=(
                    "No se pudo guardar la aprobación. Suele deberse a una migración pendiente en el servidor "
                    "(migración o esquema de BD pendiente). Ejecute: alembic upgrade head"
                ),
            )
        except Exception as e:
            db.rollback()
            logger.exception("[COBROS] Aprobar ref=%s: error al crear pago o aplicar a cuotas: %s", pr.referencia_interna, e)
            raise HTTPException(status_code=500, detail=f"Error al aprobar: {e!s}")
        db.refresh(pr)
    else:
        estado_anterior = "aprobado"
        db.refresh(pr)
    try:
        fase_pdf_t0 = time.perf_counter()
        pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
        _log_fase_aprobacion(
            flujo="aprobar_directo",
            fase="generar_pdf",
            pago_id=pago_id,
            referencia=str(pr.referencia_interna or ""),
            start_ts=fase_pdf_t0,
            extra=f"bytes={len(pdf_bytes) if pdf_bytes else 0}",
        )
    except Exception as e:
        logger.exception("[COBROS] Aprobar ref=%s: error generando recibo PDF: %s", pr.referencia_interna, e)
        raise HTTPException(status_code=500, detail=f"Error al generar el recibo PDF: {e!s}")
    pr.recibo_pdf = pdf_bytes
    to_emails = _emails_cliente_pago_reportado(db, pr)
    cedula_cli = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}"
    if cliente_bloqueado_por_desistimiento(
        db, cedula=cedula_cli, email=(to_emails[0] if to_emails else "")
    ):
        logger.info(
            "[COBROS] Bloqueo correo ref=%s: cliente con prestamo DESISTIMIENTO",
            pr.referencia_interna,
        )
        to_emails = []
    if not pr.correo_enviado_a and to_emails:
        pr.correo_enviado_a = unir_destinatarios_log(to_emails)
    dest_log = unir_destinatarios_log(to_emails)
    mensaje_final = (
        "Pago aprobado. No hay correo del cliente registrado; no se envió recibo."
        if not to_emails
        else "Pago aprobado y recibo enviado por correo."
    )
    cobros_correo_activo = get_email_activo_servicio("cobros")
    if to_emails and cobros_correo_activo:
        fase_smtp_t0 = time.perf_counter()
        att, size_note = cobros_recibo_attachments_or_oversize_note(
            f"recibo_{pr.referencia_interna}.pdf", pdf_bytes
        )
        body = (
            f"Su reporte de pago ha sido aprobado. Número de referencia: {_referencia_display(pr.referencia_interna)}.\n\n"
            + (
                "Adjunto encontrará el recibo en PDF.\n\n"
                if att
                else "No se adjunta el recibo en este correo (archivo demasiado grande para el servidor de correo).\n\n"
            )
            + size_note
            + "RapiCredit C.A."
        )
        ok_mail, err_mail = send_email(
            to_emails,
            f"Recibo de reporte de pago {_referencia_display(pr.referencia_interna)}",
            body,
            attachments=att,
            servicio="cobros",
            respetar_destinos_manuales=True,
        )
        _log_fase_aprobacion(
            flujo="aprobar_directo",
            fase="smtp_envio",
            pago_id=pago_id,
            referencia=str(pr.referencia_interna or ""),
            start_ts=fase_smtp_t0,
            extra=f"destinos={len(to_emails)} adjuntos={len(att)} ok={bool(ok_mail)}",
        )
        if ok_mail:
            logger.info("[COBROS] Aprobar ref=%s: recibo enviado por correo a %s.", pr.referencia_interna, dest_log)
            if not att:
                mensaje_final = (
                    "Pago aprobado. Se envió un correo sin adjunto: el PDF del recibo supera el límite del proveedor "
                    "de correo; el cliente puede solicitar copia por WhatsApp o desde cobranzas."
                )
        else:
            logger.error(
                "[COBROS] Aprobar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, dest_log, err_mail or "desconocido",
            )
            mensaje_final = "Pago aprobado. El recibo no pudo enviarse por correo; use 'Enviar recibo por correo' desde el detalle."
    elif to_emails and not cobros_correo_activo:
        logger.warning(
            "[COBROS] Aprobar ref=%s: servicio correo Cobros desactivado, no se envió recibo a %s.",
            pr.referencia_interna,
            dest_log,
        )
        mensaje_final = (
            "Pago aprobado. El envío de correo para Cobros está desactivado en Configuración > Email; "
            "no se envió el recibo. Actívelo o use 'Enviar recibo por correo' cuando lo active."
        )
    if registrar_historial_aprobacion and estado_anterior is not None:
        _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)
    db.commit()
    _log_fase_aprobacion(
        flujo="aprobar_directo",
        fase="total",
        pago_id=pago_id,
        referencia=str(pr.referencia_interna or ""),
        start_ts=total_t0,
    )
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

    to_emails = _emails_cliente_pago_reportado(db, pr)
    cedula_cli = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}"
    if cliente_bloqueado_por_desistimiento(
        db, cedula=cedula_cli, email=(to_emails[0] if to_emails else "")
    ):
        logger.info(
            "[COBROS] Bloqueo correo rechazo ref=%s: cliente con prestamo DESISTIMIENTO",
            pr.referencia_interna,
        )
        to_emails = []
    dest_log = unir_destinatarios_log(to_emails)
    notif_activo = get_email_activo_servicio("notificaciones")
    rechazo_correo_enviado: Optional[bool] = None
    rechazo_correo_error: Optional[str] = None
    mensaje_final = "Pago rechazado."
    logger.info(
        "[COBROS] Rechazar ref=%s: destino=%s servicio_notificaciones_activo=%s.",
        pr.referencia_interna, dest_log or "sin correo", notif_activo,
    )
    if to_emails and notif_activo:
        body_text = (
            f"Referencia: {pr.referencia_interna}\n\n"
            f"Su reporte de pago no ha sido aprobado.\n\n"
            f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
            f"Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
            "RapiCredit C.A."
        )
        attachments: List[Tuple[str, bytes]] = []
        bcomp, ct_comp = comprobante_bytes_y_content_type_desde_reportado(db, pr)
        if bcomp:
            nombre_adj = nombre_adjunto_email_desde_reportado(pr, ct_comp)
            attachments.append((nombre_adj, bcomp))
        ok_mail, err_mail = send_email(
            to_emails,
            f"Reporte de pago no aprobado #{pr.referencia_interna}",
            body_text,
            attachments=attachments if attachments else None,
            servicio="notificaciones",
            respetar_destinos_manuales=True,
        )
        if ok_mail:
            rechazo_correo_enviado = True
            mensaje_final = (
                "Pago rechazado. Correo enviado al cliente desde notificaciones@rapicreditca.com "
                "(motivo y comprobante si aplica)."
            )
            logger.info(
                "[COBROS] Rechazar ref=%s: correo enviado a %s (servicio notificaciones OK).",
                pr.referencia_interna,
                dest_log,
            )
        else:
            rechazo_correo_enviado = False
            rechazo_correo_error = (err_mail or "desconocido")[:500]
            mensaje_final = "Pago rechazado. El correo al cliente no pudo enviarse; revise logs o configuración SMTP."
            logger.error(
                "[COBROS] Rechazar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna,
                dest_log,
                err_mail or "desconocido",
            )
    elif to_emails and not notif_activo:
        logger.warning(
            "[COBROS] Rechazar ref=%s: servicio notificaciones desactivado, no se envió correo a %s.",
            pr.referencia_interna,
            dest_log,
        )
        mensaje_final = "Pago rechazado. Servicio de correo notificaciones desactivado; no se envió correo."
    elif not to_emails:
        logger.info("[COBROS] Rechazar ref=%s: no hay correo del cliente, no se envió notificación.", pr.referencia_interna)
        mensaje_final = "Pago rechazado. No hay correo del cliente en el sistema; no se envió notificación."
    _registrar_historial(db, pago_id, estado_anterior, "rechazado", usuario_email, pr.motivo_rechazo)
    db.commit()
    out = {
        "ok": True,
        "mensaje": mensaje_final,
        "rechazo_correo_enviado": rechazo_correo_enviado,
    }
    if rechazo_correo_error:
        out["rechazo_correo_error"] = rechazo_correo_error
    return out


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
    bcomp, media = comprobante_bytes_y_content_type_desde_reportado(db, pr)
    if not bcomp:
        raise HTTPException(status_code=404, detail="No hay comprobante almacenado.")
    nombre = pr.comprobante_nombre or "comprobante"
    return Response(
        content=bcomp,
        media_type=(media or "application/octet-stream").split(";")[0].strip(),
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@router.get("/pagos-reportados/{pago_id}/recibo.pdf")
def get_recibo_pdf(pago_id: int, db: Session = Depends(get_db)):
    """Devuelve el PDF del recibo regenerado desde el pago reportado."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
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
    to_emails = _emails_cliente_pago_reportado(db, pr)
    cedula_cli = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}"
    if cliente_bloqueado_por_desistimiento(
        db, cedula=cedula_cli, email=(to_emails[0] if to_emails else "")
    ):
        logger.info(
            "[COBROS] Bloqueo enviar-recibo ref=%s: cliente con prestamo DESISTIMIENTO",
            pr.referencia_interna,
        )
        to_emails = []
    if not to_emails:
        raise HTTPException(status_code=400, detail="No hay correo del cliente para este pago. Registre el correo en el detalle del pago o en la ficha del cliente.")
    if not get_email_activo_servicio("cobros"):
        raise HTTPException(
            status_code=400,
            detail=(
                "El envío de correo para Cobros está desactivado en Configuración > Email (servicio Cobros). "
                "Actívelo para poder enviar el recibo."
            ),
        )
    pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    att, size_note = cobros_recibo_attachments_or_oversize_note(
        f"recibo_{pr.referencia_interna}.pdf", bytes(pdf_bytes)
    )
    body = (
        f"Recibo de reporte de pago. Número de referencia: {_referencia_display(pr.referencia_interna)}.\n\n"
        + (
            "Adjunto encontrará el recibo en PDF.\n\n"
            if att
            else "No se adjunta el recibo en este correo (archivo demasiado grande para el servidor de correo).\n\n"
        )
        + size_note
        + "RapiCredit C.A."
    )
    ok_mail, err_mail = send_email(
        to_emails,
        f"Recibo de reporte de pago {_referencia_display(pr.referencia_interna)}",
        body,
        attachments=att,
        servicio="cobros",
        respetar_destinos_manuales=True,
    )
    if not ok_mail:
        logger.error(
            "[COBROS] enviar-recibo ref=%s: correo NO enviado a %s. Error: %s.",
            pr.referencia_interna,
            unir_destinatarios_log(to_emails),
            err_mail or "desconocido",
        )
        raise HTTPException(
            status_code=502,
            detail=(err_mail or "No se pudo enviar el correo. Revise SMTP de la Cuenta 1 (Cobros) en Configuración > Email.")[:500],
        )
    logger.info(
        "[COBROS] enviar-recibo ref=%s: recibo enviado a %s.",
        pr.referencia_interna,
        unir_destinatarios_log(to_emails),
    )
    if not att:
        return {
            "ok": True,
            "mensaje": (
                "Correo enviado sin adjunto: el PDF del recibo supera el límite del servidor de correo. "
                "Indique al cliente que solicite copia por WhatsApp o cobranzas."
            ),
        }
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


def _rechazar_si_documento_reportado_duplicado_en_pagos(db: Session, pr: PagoReportado) -> None:
    """
    Misma colisión que aprobar/importar: `pago_reportado_colisiona_tabla_pagos`
    (doc_canon_* + respaldo legacy en numero_documento / referencia_pago y claves del reporte).
    """
    if pago_reportado_colisiona_tabla_pagos(db, pr):
        raise HTTPException(
            status_code=400,
            detail="DUPLICADO: ese número de operación / documento / serial ya está registrado en la tabla de pagos (no se permite duplicar).",
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


def _snapshot_recibo_pdf_inputs(pr: PagoReportado) -> Tuple[Any, ...]:
    """
    Tupla de valores que determinan el contenido del PDF de recibo cobros.

    Evita llamar a generar_recibo_pdf_desde_pago_reportado en cada PATCH cuando solo cambian
    observacion/correo_enviado_a (la generación embebe el comprobante y puede tardar decenas de segundos).
    """
    mon = ((getattr(pr, "moneda", None) or "") or "").strip().upper()
    if mon == "USDT":
        mon = "USD"
    try:
        monto_f = float(pr.monto or 0)
    except (TypeError, ValueError):
        monto_f = 0.0
    return (
        (getattr(pr, "referencia_interna", None) or "").strip(),
        (getattr(pr, "nombres", None) or "").strip(),
        (getattr(pr, "apellidos", None) or "").strip(),
        (getattr(pr, "tipo_cedula", None) or "").strip(),
        (getattr(pr, "numero_cedula", None) or "").strip(),
        pr.fecha_pago,
        (getattr(pr, "institucion_financiera", None) or "").strip(),
        (getattr(pr, "numero_operacion", None) or "").strip(),
        round(monto_f, 2),
        mon,
        (getattr(pr, "comprobante_imagen_id", None) or "").strip(),
        (getattr(pr, "comprobante_nombre", None) or "").strip(),
    )


@router.patch("/pagos-reportados/{pago_id}")
def editar_pago_reportado(
    pago_id: int,
    body: EditarPagoReportadoBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Edita los datos del pago reportado para que cumplan con los validadores (cédula, fecha, monto, etc.). Solo actualiza los campos enviados."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado in ("aprobado", "importado"):
        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado o importado a pagos.")
    ref = pr.referencia_interna
    try:
        key_recibo_antes = _snapshot_recibo_pdf_inputs(pr)
        estado_previo = pr.estado
        usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
        # rechazado: permitir corregir datos (monto, referencia, etc.) y volver a cola de revisión

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

        # Documento del reporte (operación ± sufijo / ref.): no duplicar frente a cartera `pagos`
        _rechazar_si_documento_reportado_duplicado_en_pagos(db, pr)

        # Si la moneda queda en BS, la cédula debe estar en la lista de autorizadas para Bolívares (misma normalización que en listado)
        moneda_final = (pr.moneda or "").strip().upper()
        if moneda_final == "BS":
            raw_cedula = ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
            cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
            if cedula_norm:
                autorizados_bs = load_autorizados_bs_claves(db)
                permitido_bs = cedula_coincide_autorizados_bs(cedula_norm, autorizados_bs)
                if not permitido_bs:
                    raise HTTPException(
                        status_code=400,
                        detail="Observación: Bolívares. No puede guardar con moneda Bs; la cédula no está en la lista autorizada. Cambie a USD.",
                    )

        mensaje = "Datos actualizados. Los cambios cumplen con los validadores."
        if estado_previo == "rechazado":
            pr.estado = "pendiente"
            pr.motivo_rechazo = None
            _registrar_historial(
                db,
                pago_id,
                "rechazado",
                "pendiente",
                usuario_email,
                "Datos corregidos tras rechazo; vuelve a revisión para aprobar o rechazar.",
            )
            mensaje = (
                "Datos guardados. El reporte pasó a pendiente: ya puede aprobarlo o rechazarlo de nuevo desde el detalle."
            )

        # PDF de recibo: si cambian datos que afectan el documento, invalidar cache (no regenerar aquí).
        # generar_recibo_pdf_desde_pago_reportado con comprobante embebido puede tardar decenas de segundos y bloquea el PATCH.
        # GET .../recibo.pdf, POST aprobar y POST enviar-recibo vuelven a generar y persistir cuando haga falta.
        key_recibo_despues = _snapshot_recibo_pdf_inputs(pr)
        _img_id = (getattr(pr, "comprobante_imagen_id", None) or "").strip()
        if key_recibo_antes != key_recibo_despues and (pr.recibo_pdf is not None or _img_id):
            pr.recibo_pdf = None
        db.commit()
        logger.info("[COBROS] Pago reportado editado: id=%s ref=%s", pago_id, pr.referencia_interna)
        return {"ok": True, "mensaje": mensaje}
    except HTTPException as exc:
        if exc.status_code == 400:
            detail_txt = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
            logger.warning(
                "[COBROS] PATCH editar fallo id=%s ref=%s moneda=%s cedula=%s%s nro_op=%s -> %s",
                pago_id,
                ref,
                getattr(pr, "moneda", None),
                getattr(pr, "tipo_cedula", "") or "",
                getattr(pr, "numero_cedula", "") or "",
                ((getattr(pr, "numero_operacion", None) or "")[:50]),
                detail_txt,
            )
        raise


@router.patch("/pagos-reportados/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    body: CambiarEstadoBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia el estado del pago reportado (pendiente, en_revision, aprobado, rechazado). Si pasa a aprobado, genera y guarda el recibo PDF; no envía correo desde este endpoint (listado). POST …/aprobar o enviar-recibo envían el recibo."""
    if body.estado not in ("pendiente", "en_revision", "aprobado", "rechazado"):
        raise HTTPException(status_code=400, detail="Estado no válido.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if body.estado == "rechazado" and not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo es obligatorio al rechazar.")
    if body.estado == "aprobado" and pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    if body.estado == "aprobado" and pr.estado == "importado":
        raise HTTPException(
            status_code=400,
            detail="Este reporte ya fue importado a la tabla de pagos; no se vuelve a aprobar desde aquí.",
        )
    if body.estado == "aprobado" and pr.estado in ("pendiente", "en_revision"):
        _rechazar_aprobacion_si_documento_ya_en_pagos(db, pr)
        num_key = _numero_operacion_canonico(getattr(pr, "numero_operacion", None))
        if num_key:
            _lock_numero_operacion_canonico(db, num_key)
            hermanos = _duplicados_reportados_por_numero_operacion(
                db, numero_key=num_key, excluir_id=pr.id
            )
            if hermanos:
                first_id = min([pr.id] + [rid for rid, _rref, _st in hermanos])
                if int(first_id) != int(pr.id):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Duplicado por número de operación: este reporte no es el primero registrado. "
                            f"Gestione primero el reporte ID {first_id}."
                        ),
                    )
    estado_anterior = pr.estado
    pr.estado = body.estado
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000] if body.estado == "rechazado" else None
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)

    mensaje = f"Estado actualizado a {body.estado}."
    total_t0 = time.perf_counter() if body.estado == "aprobado" else 0.0
    rechazo_correo_enviado: Optional[bool] = None
    rechazo_correo_error: Optional[str] = None
    if body.estado == "aprobado":
        try:
            fase_db_t0 = time.perf_counter()
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            num_key = _numero_operacion_canonico(getattr(pr, "numero_operacion", None))
            if num_key:
                dup_rows = _duplicados_reportados_por_numero_operacion(
                    db, numero_key=num_key, excluir_id=pr.id
                )
                n_dup, dup_refs = _marcar_reportados_como_eliminado_duplicado(
                    db,
                    dup_rows=dup_rows,
                    master_id=pr.id,
                master_ref=str(pr.institucion_financiera or ""),
                    num_key=num_key,
                    usuario_email=usuario_email,
                    via="aprobar_patch_estado",
                )
                if n_dup > 0:
                    logger.info(
                        "[COBROS] PATCH aprobado id=%s ref=%s: marcados %s duplicados por numero_operacion=%s refs=%s",
                        pr.id,
                        pr.referencia_interna,
                        n_dup,
                        num_key,
                        ", ".join([x for x in dup_refs if x])[:300],
                    )
            db.commit()
            _log_fase_aprobacion(
                flujo="aprobar_patch_estado",
                fase="db_aprobacion_commit",
                pago_id=pago_id,
                referencia=str(pr.referencia_interna or ""),
                start_ts=fase_db_t0,
            )
        except HTTPException as exc:
            detail_txt = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
            logger.warning(
                "[COBROS] PATCH aprobar fallo id=%s ref=%s cedula=%s%s moneda=%s fecha_pago=%s monto=%s nro_op=%s -> %s",
                pago_id,
                getattr(pr, "referencia_interna", None),
                getattr(pr, "tipo_cedula", "") or "",
                getattr(pr, "numero_cedula", "") or "",
                getattr(pr, "moneda", None),
                getattr(pr, "fecha_pago", None),
                getattr(pr, "monto", None),
                ((getattr(pr, "numero_operacion", None) or "")[:40]),
                detail_txt,
            )
            db.rollback()
            raise
        except (ProgrammingError, OperationalError) as e:
            db.rollback()
            logger.exception(
                "[COBROS] PATCH estado=aprobado id=%s ref=%s: error de BD (¿migración pendiente?): %s",
                pago_id,
                pr.referencia_interna,
                e,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "No se pudo guardar la aprobación. Suele deberse a una migración pendiente en el servidor "
                    "(migración o esquema de BD pendiente). Ejecute: alembic upgrade head"
                ),
            )
        except (IntegrityError, Exception) as e:
            db.rollback()
            logger.exception(
                "[COBROS] PATCH estado=aprobado id=%s ref=%s: %s",
                pago_id,
                pr.referencia_interna,
                e,
            )
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo completar la aprobación: {e!s}"[:500],
            )

        db.refresh(pr)
        fase_pdf_t0 = time.perf_counter()
        pdf_bytes = generar_recibo_pdf_desde_pago_reportado(db, pr)
        _log_fase_aprobacion(
            flujo="aprobar_patch_estado",
            fase="generar_pdf",
            pago_id=pago_id,
            referencia=str(pr.referencia_interna or ""),
            start_ts=fase_pdf_t0,
            extra=f"bytes={len(pdf_bytes) if pdf_bytes else 0}",
        )
        pr.recibo_pdf = pdf_bytes
        logger.info(
            "[COBROS] PATCH estado=aprobado ref=%s: recibo PDF guardado; no se envía correo desde el listado "
            "(detalle: POST …/aprobar o enviar-recibo).",
            pr.referencia_interna,
        )
        mensaje = (
            "Estado actualizado a aprobado. El recibo quedó generado; no se envía correo desde el listado. "
            "Para notificar al cliente, use la vista de detalle (Aprobar o Enviar recibo por correo)."
        )

    elif body.estado == "rechazado":
        to_emails = _emails_cliente_pago_reportado(db, pr)
        cedula_cli = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}"
        if cliente_bloqueado_por_desistimiento(
            db, cedula=cedula_cli, email=(to_emails[0] if to_emails else "")
        ):
            logger.info(
                "[COBROS] Bloqueo PATCH rechazado ref=%s: cliente con prestamo DESISTIMIENTO",
                pr.referencia_interna,
            )
            to_emails = []
        dest_log_rj = unir_destinatarios_log(to_emails)
        notif_activo = get_email_activo_servicio("notificaciones")
        logger.info(
            "[COBROS] PATCH estado=rechazado ref=%s: destino=%s servicio_notificaciones_activo=%s.",
            pr.referencia_interna,
            dest_log_rj or "sin correo",
            notif_activo,
        )
        if to_emails and notif_activo:
            body_text = (
                f"Referencia: {pr.referencia_interna}\n\n"
                f"Su reporte de pago no ha sido aprobado.\n\n"
                f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
                f"Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
                "RapiCredit C.A."
            )
            attachments_rech: List[Tuple[str, bytes]] = []
            bcr, ct_cr = comprobante_bytes_y_content_type_desde_reportado(db, pr)
            if bcr:
                nombre_adj = nombre_adjunto_email_desde_reportado(pr, ct_cr)
                attachments_rech.append((nombre_adj, bcr))
            ok_mail, err_mail = send_email(
                to_emails,
                f"Reporte de pago no aprobado #{pr.referencia_interna}",
                body_text,
                attachments=attachments_rech if attachments_rech else None,
                servicio="notificaciones",
                respetar_destinos_manuales=True,
            )
            if ok_mail:
                rechazo_correo_enviado = True
                logger.info(
                    "[COBROS] PATCH estado=rechazado ref=%s: correo enviado a %s (servicio notificaciones OK).",
                    pr.referencia_interna,
                    dest_log_rj,
                )
                mensaje = "Estado actualizado a rechazado. Cliente notificado por correo (notificaciones@rapicreditca.com)."
            else:
                rechazo_correo_enviado = False
                rechazo_correo_error = (err_mail or "desconocido")[:500]
                logger.error(
                    "[COBROS] PATCH estado=rechazado ref=%s: correo NO enviado a %s. Error: %s.",
                    pr.referencia_interna,
                    dest_log_rj,
                    err_mail or "desconocido",
                )
                mensaje = "Estado actualizado a rechazado. El correo al cliente no pudo enviarse; revise logs o configuración SMTP."
        elif to_emails and not notif_activo:
            logger.warning(
                "[COBROS] PATCH estado=rechazado ref=%s: servicio notificaciones desactivado, no se envió correo a %s.",
                pr.referencia_interna,
                dest_log_rj,
            )
            mensaje = "Estado actualizado a rechazado. Servicio de correo desactivado; no se envió correo."
        else:
            logger.info("[COBROS] PATCH estado=rechazado ref=%s: no hay correo del cliente, no se envió notificación.", pr.referencia_interna)
            mensaje = "Estado actualizado a rechazado. No hay correo del cliente; no se envió notificación."

    _registrar_historial(db, pago_id, estado_anterior, body.estado, usuario_email, body.motivo)
    db.commit()
    if body.estado == "aprobado":
        _log_fase_aprobacion(
            flujo="aprobar_patch_estado",
            fase="total",
            pago_id=pago_id,
            referencia=str(pr.referencia_interna or ""),
            start_ts=total_t0,
        )
    resp: dict = {"ok": True, "mensaje": mensaje}
    if body.estado == "rechazado":
        resp["rechazo_correo_enviado"] = rechazo_correo_enviado
        if rechazo_correo_error:
            resp["rechazo_correo_error"] = rechazo_correo_error
    return resp



@router.post("/pagos-reportados/marcar-exportados")
def marcar_pagos_reportados_exportados(
    body: MarcarExportadosBody,
    db: Session = Depends(get_db),
):
    ids = sorted({int(x) for x in (body.pago_reportado_ids or []) if int(x) > 0})
    if not ids:
        raise HTTPException(status_code=400, detail="Debe indicar al menos un pago reportado para marcar exportado.")

    rows = db.execute(
        select(PagoReportado.id, PagoReportado.estado).where(PagoReportado.id.in_(ids))
    ).all()
    estado_por_id = {int(r.id): str(r.estado or "") for r in rows}

    faltantes = [pid for pid in ids if pid not in estado_por_id]
    if faltantes:
        raise HTTPException(status_code=404, detail=f"Pagos reportados no encontrados: {faltantes}")

    permitidos = {"pendiente", "en_revision", "aprobado"}
    no_ok = [pid for pid in ids if estado_por_id[pid] not in permitidos]
    if no_ok:
        raise HTTPException(
            status_code=400,
            detail=f"Solo pendiente, en revisión o aprobado. IDs inválidos: {no_ok}",
        )

    return _persist_marcar_exportados_y_cola(db, ids)


@router.post("/pagos-reportados/{pago_id}/re-analizar-gemini")
def reanalizar_pago_con_gemini(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Re-analiza el comprobante de un pago reportado con Gemini.
    Admin puede usar esto para forzar un nuevo escaneo si quiere revisar nuevamente.
    
    Actualiza:
    - gemini_coincide_exacto (true/false/error)
    - gemini_comentario (resultado del análisis)
    
    El estado (aprobado/en_revision) NO se cambia automáticamente.
    Admin debe decidir manualmente luego de ver el nuevo resultado.
    """
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    
    # Verificar que hay comprobante guardado
    bcomp, _ct = comprobante_bytes_y_content_type_desde_reportado(db, pr)
    if not bcomp:
        raise HTTPException(
            status_code=400,
            detail="No hay comprobante guardado para este pago. No se puede re-analizar."
        )
    
    # Preparar datos del formulario como estaban en el primer envío
    form_data = {
        "fecha_pago": str(pr.fecha_pago) if pr.fecha_pago else "",
        "institucion_financiera": pr.institucion_financiera or "",
        "numero_operacion": pr.numero_operacion or "",
        "monto": str(pr.monto) if pr.monto else "",
        "moneda": pr.moneda or "BS",
        "tipo_cedula": pr.tipo_cedula or "",
        "numero_cedula": pr.numero_cedula or "",
    }
    
    logger.info(
        "[COBROS] Re-analizar con Gemini: pago_id=%s ref=%s usuario=%s",
        pago_id,
        pr.referencia_interna,
        current_user.get("email") if isinstance(current_user, dict) else "unknown",
    )
    
    # Llamar a Gemini para re-analizar
    try:
        gemini_result = compare_form_with_image(
            form_data,
            bcomp,
            filename=f"comprobante_{pago_id}.jpg"
        )
        
        coincide = gemini_result.get("coincide_exacto", False)
        pr.gemini_coincide_exacto = "true" if coincide else "false"
        pr.gemini_comentario = gemini_result.get("comentario")
        
        logger.info(
            "[COBROS] Re-analizar Gemini OK: pago_id=%s coincide=%s",
            pago_id, coincide
        )
        
    except Exception as gemini_err:
        # Si Gemini falla incluso tras reintentos
        logger.warning(
            "[COBROS] Re-analizar Gemini error pago_id=%s tras reintentos: %s",
            pago_id, str(gemini_err)
        )
        pr.gemini_coincide_exacto = "error"
        pr.gemini_comentario = f"Error Gemini en re-análisis (reintentado): {str(gemini_err)[:200]}"
    
    db.commit()
    
    # Retornar el nuevo resultado
    return {
        "ok": True,
        "pago_id": pago_id,
        "referencia_interna": pr.referencia_interna,
        "gemini_coincide_exacto": pr.gemini_coincide_exacto,
        "gemini_comentario": pr.gemini_comentario,
        "mensaje": "Comprobante re-analizado. Verifica la observación antes de aprobar o rechazar.",
    }


@router.post("/escaner/extraer-comprobante")
async def escaner_extraer_comprobante_infopagos(
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    comprobante: UploadFile = File(...),
):
    """
    Personal autenticado: sugiere campos del formulario Infopagos leyendo el comprobante con Gemini.
    Orden de uso: cédula del deudor + archivo. No guarda el reporte; el front aplica validadores y envía con /cobros/public/infopagos/enviar-reporte.
    """
    cedula_input = f"{(tipo_cedula or '').strip()}{(numero_cedula or '').strip()}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        raise HTTPException(status_code=400, detail=val.get("error", "Cédula inválida."))

    cedula_lookup = (val.get("valor_formateado") or "").replace("-", "")
    if not cedula_lookup:
        raise HTTPException(status_code=400, detail="Formato de cédula no reconocido.")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        raise HTTPException(status_code=400, detail="La cédula no está registrada.")

    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        raise HTTPException(status_code=400, detail=err_pres)

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
        raise HTTPException(status_code=400, detail=err_file)

    tipo = (tipo_cedula or "").strip().upper()[:2]
    numero = (numero_cedula or "").strip()
    ctx_ced = f"{tipo}{numero}".replace("-", "")

    t_gemini0 = time.perf_counter()
    gem = extract_infopagos_campos_desde_comprobante(ctx_ced, content, filename)
    gemini_ms = int((time.perf_counter() - t_gemini0) * 1000)
    if not gem.get("ok"):
        logger.info(
            "[ESCANER_TIMING] ok=False gemini_ms=%s bytes=%s filename=%r cedula_ctx=%s err=%s",
            gemini_ms,
            len(content) if content else 0,
            filename[:80] if filename else "",
            ctx_ced[:20],
            (str(gem.get("error") or "")[:120]),
        )
        return {
            "ok": False,
            "error": gem.get("error") or "No se pudo leer el comprobante.",
            "sugerencia": None,
            "validacion_campos": None,
            "validacion_reglas": None,
        }

    fecha_d = gem.get("fecha_pago")
    fecha_iso = fecha_d.isoformat() if isinstance(fecha_d, date) else None
    monto = gem.get("monto")
    inst = gem.get("institucion_financiera") or ""
    num_op = gem.get("numero_operacion") or ""
    moneda = gem.get("moneda") or "BS"

    validacion_campos = None
    validacion_reglas = None
    mon_norm = None

    if monto is not None and inst.strip() and num_op.strip():
        err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula=tipo,
            numero_cedula=numero,
            institucion_financiera=inst,
            numero_operacion=num_op,
            monto=float(monto),
            moneda=moneda,
            observacion=None,
        )
        validacion_campos = err_campos
        if not err_campos and isinstance(fecha_d, date):
            err_reglas = cpr.validar_reglas_bs_tasa_monto_fecha(
                db,
                cedula_lookup=cedula_lookup,
                fecha_pago=fecha_d,
                monto=float(monto),
                mon=mon_norm,
            )
            validacion_reglas = err_reglas
        elif not err_campos and not isinstance(fecha_d, date):
            validacion_reglas = "Indique la fecha de pago (no se detectó con claridad en la imagen)."
    elif monto is None:
        validacion_reglas = "Complete el monto (no se detectó con claridad en la imagen)."
    elif not inst.strip():
        validacion_reglas = "Complete la institución financiera."
    elif not num_op.strip():
        validacion_reglas = "Complete el número de operación o referencia."

    sugerencia = {
        "fecha_pago": fecha_iso,
        "institucion_financiera": inst,
        "numero_operacion": num_op,
        "monto": monto,
        "moneda": moneda if moneda in ("BS", "USD") else "BS",
        "cedula_pagador_en_comprobante": gem.get("cedula_pagador_en_comprobante") or "",
        "notas_modelo": gem.get("notas") or "",
    }

    # Misma colisión que detalle Cobros: documento ya en cartera + préstamo del pago existente / objetivo.
    duplicado_en_pagos = False
    pago_existente_id: Optional[int] = None
    prestamo_existente_id: Optional[int] = None
    prestamo_objetivo_id: Optional[int] = None
    if len(prestamos_aprob) == 1:
        prestamo_objetivo_id = int(prestamos_aprob[0])
    t_post0 = time.perf_counter()
    num_op_trim = (num_op or "").strip()
    if num_op_trim:
        pr_scan = SimpleNamespace(
            numero_operacion=num_op_trim[:100],
            referencia_interna="",
        )
        duplicado_en_pagos = pago_reportado_colisiona_tabla_pagos(db, pr_scan)
        if duplicado_en_pagos:
            pago_existente_id = primer_pago_id_si_existe_para_claves_reportado(db, pr_scan)
            if pago_existente_id is not None:
                p_exist = db.execute(select(Pago).where(Pago.id == pago_existente_id)).scalars().first()
                if p_exist is not None:
                    prestamo_existente_id = getattr(p_exist, "prestamo_id", None)
    post_gemini_ms = int((time.perf_counter() - t_post0) * 1000)

    logger.info(
        "[ESCANER_TIMING] ok=True gemini_ms=%s post_gemini_ms=%s bytes=%s filename=%r dup=%s",
        gemini_ms,
        post_gemini_ms,
        len(content) if content else 0,
        filename[:80] if filename else "",
        duplicado_en_pagos,
    )

    return {
        "ok": True,
        "error": None,
        "sugerencia": sugerencia,
        "validacion_campos": validacion_campos,
        "validacion_reglas": validacion_reglas,
        "duplicado_en_pagos": duplicado_en_pagos,
        "pago_existente_id": pago_existente_id,
        "prestamo_existente_id": prestamo_existente_id,
        "prestamo_objetivo_id": prestamo_objetivo_id,
    }


def _extraer_folder_id_drive(raw: str) -> str:
    txt = (raw or "").strip()
    if not txt:
        return ""
    m = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", txt)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", txt):
        return txt
    return ""


@router.post("/escaner/lote/drive-digitalizar")
async def escaner_lote_drive_digitalizar(
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    drive_folder: str = Form(...),
    max_archivos: int = Form(15),
):
    """
    Escáner lote desde carpeta compartida de Drive:
    - toma hasta `max_archivos` (tope duro 15),
    - digitaliza y valida cada comprobante como el escáner unitario,
    - elimina de Drive los archivos leídos para dejar la carpeta lista.
    """
    max_items = max(1, min(int(max_archivos or 15), 15))
    folder_id = _extraer_folder_id_drive(drive_folder)
    if not folder_id:
        raise HTTPException(status_code=400, detail="Carpeta de Drive inválida.")

    cedula_input = f"{(tipo_cedula or '').strip()}{(numero_cedula or '').strip()}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        raise HTTPException(status_code=400, detail=val.get("error", "Cédula inválida."))
    cedula_lookup = (val.get("valor_formateado") or "").replace("-", "")
    if not cedula_lookup:
        raise HTTPException(status_code=400, detail="Formato de cédula no reconocido.")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        raise HTTPException(status_code=400, detail="La cédula no está registrada.")
    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        raise HTTPException(status_code=400, detail=err_pres)

    creds = get_pagos_gmail_credentials()
    if not creds:
        raise HTTPException(status_code=503, detail="Google Drive no está configurado.")
    drive_svc, _ = build_drive_service(creds)

    q = (
        f"'{folder_id}' in parents and trashed=false "
        "and mimeType!='application/vnd.google-apps.folder'"
    )
    try:
        listed = (
            drive_svc.files()
            .list(
                q=q,
                spaces="drive",
                fields="files(id,name,mimeType,size,createdTime)",
                orderBy="createdTime asc",
                pageSize=max_items,
            )
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo leer la carpeta de Drive: {str(e)[:180]}") from e

    files = listed.get("files", []) or []
    if not files:
        return {
            "ok": True,
            "items": [],
            "total_leidos": 0,
            "total_eliminados": 0,
            "mensaje": "La carpeta de Drive no tiene imágenes para procesar.",
        }

    tipo = (tipo_cedula or "").strip().upper()[:2]
    numero = (numero_cedula or "").strip()
    ctx_ced = f"{tipo}{numero}".replace("-", "")
    prestamo_objetivo_id: Optional[int] = int(prestamos_aprob[0]) if len(prestamos_aprob) == 1 else None

    items = []
    delete_ok = 0
    for f in files:
        fid = str(f.get("id") or "").strip()
        fname = str(f.get("name") or "comprobante")
        mime_drive = str(f.get("mimeType") or "")
        if not fid:
            continue
        content = b""
        try:
            req = drive_svc.files().get_media(fileId=fid)
            out = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload

            dl = MediaIoBaseDownload(out, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
            content = out.getvalue()
        except Exception:
            items.append(
                {
                    "drive_file_id": fid,
                    "nombre_archivo": fname,
                    "mime_type": mime_drive,
                    "archivo_b64": None,
                    "ok": False,
                    "error": "No se pudo descargar desde Drive.",
                    "sugerencia": None,
                    "validacion_campos": None,
                    "validacion_reglas": None,
                    "duplicado_en_pagos": False,
                    "pago_existente_id": None,
                    "prestamo_existente_id": None,
                    "prestamo_objetivo_id": prestamo_objetivo_id,
                }
            )
            continue

        ctype = cpr.mime_efectivo_comprobante_web(mime_drive, fname)
        archivo_b64 = base64.b64encode(content).decode("ascii")
        err_file, filename = cpr.validar_adjunto_comprobante_bytes(
            content,
            ctype,
            fname,
            mensaje_excel_largo=False,
        )
        if err_file:
            items.append(
                {
                    "drive_file_id": fid,
                    "nombre_archivo": fname,
                    "mime_type": ctype,
                    "archivo_b64": archivo_b64,
                    "ok": False,
                    "error": err_file,
                    "sugerencia": None,
                    "validacion_campos": None,
                    "validacion_reglas": None,
                    "duplicado_en_pagos": False,
                    "pago_existente_id": None,
                    "prestamo_existente_id": None,
                    "prestamo_objetivo_id": prestamo_objetivo_id,
                }
            )
        else:
            gem = extract_infopagos_campos_desde_comprobante(ctx_ced, content, filename)
            if not gem.get("ok"):
                items.append(
                    {
                        "drive_file_id": fid,
                        "nombre_archivo": fname,
                        "mime_type": ctype,
                        "archivo_b64": archivo_b64,
                        "ok": False,
                        "error": gem.get("error") or "No se pudo leer el comprobante.",
                        "sugerencia": None,
                        "validacion_campos": None,
                        "validacion_reglas": None,
                        "duplicado_en_pagos": False,
                        "pago_existente_id": None,
                        "prestamo_existente_id": None,
                        "prestamo_objetivo_id": prestamo_objetivo_id,
                    }
                )
            else:
                fecha_d = gem.get("fecha_pago")
                fecha_iso = fecha_d.isoformat() if isinstance(fecha_d, date) else None
                monto = gem.get("monto")
                inst = gem.get("institucion_financiera") or ""
                num_op = gem.get("numero_operacion") or ""
                moneda = gem.get("moneda") or "BS"
                validacion_campos = None
                validacion_reglas = None
                if monto is not None and inst.strip() and num_op.strip():
                    err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
                        tipo_cedula=tipo,
                        numero_cedula=numero,
                        institucion_financiera=inst,
                        numero_operacion=num_op,
                        monto=float(monto),
                        moneda=moneda,
                        observacion=None,
                    )
                    validacion_campos = err_campos
                    if not err_campos and isinstance(fecha_d, date):
                        validacion_reglas = cpr.validar_reglas_bs_tasa_monto_fecha(
                            db,
                            cedula_lookup=cedula_lookup,
                            fecha_pago=fecha_d,
                            monto=float(monto),
                            mon=mon_norm,
                        )
                    elif not err_campos and not isinstance(fecha_d, date):
                        validacion_reglas = (
                            "Indique la fecha de pago (no se detectó con claridad en la imagen)."
                        )
                elif monto is None:
                    validacion_reglas = "Complete el monto (no se detectó con claridad en la imagen)."
                elif not inst.strip():
                    validacion_reglas = "Complete la institución financiera."
                elif not num_op.strip():
                    validacion_reglas = "Complete el número de operación o referencia."

                duplicado_en_pagos = False
                pago_existente_id: Optional[int] = None
                prestamo_existente_id: Optional[int] = None
                num_op_trim = (num_op or "").strip()
                if num_op_trim:
                    pr_scan = SimpleNamespace(
                        numero_operacion=num_op_trim[:100],
                        referencia_interna="",
                    )
                    duplicado_en_pagos = pago_reportado_colisiona_tabla_pagos(db, pr_scan)
                    if duplicado_en_pagos:
                        pago_existente_id = primer_pago_id_si_existe_para_claves_reportado(
                            db, pr_scan
                        )
                        if pago_existente_id is not None:
                            p_exist = (
                                db.execute(select(Pago).where(Pago.id == pago_existente_id))
                                .scalars()
                                .first()
                            )
                            if p_exist is not None:
                                prestamo_existente_id = getattr(p_exist, "prestamo_id", None)

                items.append(
                    {
                        "drive_file_id": fid,
                        "nombre_archivo": fname,
                        "mime_type": ctype,
                        "archivo_b64": archivo_b64,
                        "ok": True,
                        "error": None,
                        "sugerencia": {
                            "fecha_pago": fecha_iso,
                            "institucion_financiera": inst,
                            "numero_operacion": num_op,
                            "monto": monto,
                            "moneda": moneda if moneda in ("BS", "USD") else "BS",
                            "cedula_pagador_en_comprobante": gem.get("cedula_pagador_en_comprobante") or "",
                            "notas_modelo": gem.get("notas") or "",
                        },
                        "validacion_campos": validacion_campos,
                        "validacion_reglas": validacion_reglas,
                        "duplicado_en_pagos": duplicado_en_pagos,
                        "pago_existente_id": pago_existente_id,
                        "prestamo_existente_id": prestamo_existente_id,
                        "prestamo_objetivo_id": prestamo_objetivo_id,
                    }
                )

        try:
            drive_svc.files().delete(fileId=fid).execute()
            delete_ok += 1
        except Exception:
            logger.warning("[ESCANER_LOTE_DRIVE] No se pudo eliminar file_id=%s", fid)

    return {
        "ok": True,
        "items": items,
        "total_leidos": len(items),
        "total_eliminados": delete_ok,
        "mensaje": f"Se procesaron {len(items)} archivo(s) desde Drive.",
    }