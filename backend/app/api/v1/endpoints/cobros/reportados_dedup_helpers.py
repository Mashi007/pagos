"""Cobros: dedup documentos, cedulas y armado de items."""
"""Helpers internos cobros: validadores, dedup, payloads listado/KPIs."""
"""
Endpoints de administración del módulo Cobros (requieren autenticación).
Listado de pagos reportados, detalle, aprobar, rechazar, histórico por cédula.
"""
import io
import logging
import base64
import hashlib
import json
import re
import threading
import time
from collections import Counter, defaultdict
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional, List, Tuple, Any, Dict, Iterable, Set

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, case, delete, text, update
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from app.core.database import get_db
from app.core.db_transient import run_db_with_transient_retry
from app.core.documento import normalize_documento
from app.core.deps import get_current_user
from app.services.cobros import infopagos_escaner_borrador_service as ieb
from app.core.rate_limit_store import get_redis_client
from app.api.v1.endpoints.pagos.pago_integridad_db import _integridad_error_pgcode_y_constraint
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
    pago_reportado_colisiona_tabla_pagos_documento_base,
    primer_pago_id_si_existe_para_claves_reportado,
    primer_reportado_id_por_norm_batch,
    primer_reportado_id_por_norm_peer_first_map,
    reportado_toca_claves_canonicas_en_pagos,
)
from app.services.cobros.cedula_reportar_bs_service import (
    load_autorizados_bs_claves,
    cedula_coincide_autorizados_bs,
    fuente_tasa_bs_efectiva_para_cedula,
)
from app.services.tasa_cambio_service import (
    convertir_bs_a_usd,
    normalizar_fuente_tasa,
    obtener_tasa_por_fecha,
    obtener_tasas_por_fechas,
    tasa_y_equivalente_usd_excel,
    valor_tasa_para_fuente,
)
from app.services.pagos_gmail.gemini_async import (
    compare_form_with_image_async,
    extract_infopagos_campos_desde_comprobante_async,
    extract_infopagos_campos_desde_comprobante_con_rescate_plantilla_async,
)
from app.services.pagos_gmail.gemini_service import (
    _canonical_institucion_escaner,
    compare_form_with_image,
)
from app.services.pagos.comprobante_adjunto_pago import comprobante_blob_para_pdf_desde_pago
from app.services.cobros import cobros_publico_reporte_service as cpr
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar
from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import build_drive_service
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.cobros.pago_reportado_comprobante_unico import (
    comprobante_bytes_y_content_type_desde_reportado,
    nombre_adjunto_email_desde_reportado,
)

logger = logging.getLogger(__name__)
from .listado_kpis_cache import (
    _cobros_listado_kpis_cache_get,
    _cobros_listado_kpis_cache_get_stale,
    _cobros_listado_kpis_cache_set,
    _cobros_listado_kpis_release_singleflight,
    _cobros_listado_kpis_try_acquire_singleflight,
    _drop_pago_from_listado_kpis_cache,
    _drop_pagos_from_listado_kpis_cache,
    _invalidate_cobros_listado_kpis_cache,
)
from .schemas import (
    MENSAJE_RECHAZO_GENERICO,
    PagoReportadoDuplicadoDiagnostico,
    PagoReportadoListItem,
)
from .schemas import PagoReportadoListItem

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


def _gemini_coincide_exacto_ok(val: Optional[str]) -> bool:
    """True si Gemini indico coincidencia exacta (valores habituales en BD: true, 1)."""
    g = (val or "").strip().lower()
    return g in ("true", "1")


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
_REGULARIZA_MAX_IDS_PER_RUN = 4
_regulariza_last_run_monotonic = 0.0
_regulariza_lock = threading.Lock()
_REGULARIZA_COLD_START_GRACE_SEC = 45.0
_process_start_monotonic = time.monotonic()


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


def _pagos_canonicos_presentes_para_claves_reutilizando(
    db: Session,
    claves: Set[str],
    acum: Dict[str, Set[str]],
) -> frozenset:
    """
    Misma intersección (claves que ya están en cartera) que
    ``_pagos_canonicos_presentes_para_claves(db, claves)``, pero solo consulta
    claves aún no vistas en ``acum['queried']``. Reduce round-trips en el barrido
    por lotes de pagos reportados (listado / KPIs).
    """
    if not claves:
        return frozenset()
    present = acum.setdefault("present", set())
    queried = acum.setdefault("queried", set())
    nuevas = {x for x in claves if x} - queried
    if nuevas:
        encontrados = _pagos_canonicos_presentes_para_claves(db, nuevas)
        queried.update(nuevas)
        present.update(encontrados)
    return frozenset(present & claves)


PagoExistenteInfo = Tuple[int, Optional[int], Optional[str]]


def _pagos_existentes_info_por_clave(
    db: Session,
    claves: Set[str],
) -> Dict[str, PagoExistenteInfo]:
    """
    Mapa canonico -> (pago_id, prestamo_id, numero_documento) para claves ya presentes
    en cartera. Es la version con datos del set `_pagos_canonicos_presentes_para_claves`.
    """
    if not claves:
        return {}
    out: Dict[str, PagoExistenteInfo] = {}

    def _add(
        key: Optional[str],
        pago_id: int,
        prestamo_id: Optional[int],
        numero_documento: Optional[str],
    ) -> None:
        k = (key or "").strip()
        if not k or k in out:
            return
        out[k] = (
            int(pago_id),
            int(prestamo_id) if prestamo_id is not None else None,
            (numero_documento or "").strip() or None,
        )

    lst = [x for x in claves if x]
    chunk_size = 450
    for i in range(0, len(lst), chunk_size):
        part = lst[i : i + chunk_size]
        if not part:
            continue
        for key, pid, prestamo_id, numero_documento in db.execute(
            select(
                Pago.doc_canon_numero,
                Pago.id,
                Pago.prestamo_id,
                Pago.numero_documento,
            ).where(Pago.doc_canon_numero.in_(part))
        ).all():
            _add(key, pid, prestamo_id, numero_documento)
        for key, pid, prestamo_id, numero_documento in db.execute(
            select(
                Pago.doc_canon_referencia,
                Pago.id,
                Pago.prestamo_id,
                Pago.numero_documento,
            ).where(Pago.doc_canon_referencia.in_(part))
        ).all():
            _add(key, pid, prestamo_id, numero_documento)
        for raw, pid, prestamo_id, numero_documento in db.execute(
            select(
                Pago.numero_documento,
                Pago.id,
                Pago.prestamo_id,
                Pago.numero_documento,
            ).where(Pago.numero_documento.in_(part))
        ).all():
            _add(
                (normalize_documento(raw) or raw) if raw else None,
                pid,
                prestamo_id,
                numero_documento,
            )
        for raw, pid, prestamo_id, numero_documento in db.execute(
            select(
                Pago.referencia_pago,
                Pago.id,
                Pago.prestamo_id,
                Pago.numero_documento,
            ).where(Pago.referencia_pago.in_(part))
        ).all():
            _add(
                (normalize_documento(raw) or raw) if raw else None,
                pid,
                prestamo_id,
                numero_documento,
            )
    return out


def _pagos_existentes_info_por_clave_reutilizando(
    db: Session,
    claves: Set[str],
    acum: Dict[str, Any],
) -> Dict[str, PagoExistenteInfo]:
    if not claves:
        return {}
    queried: Set[str] = acum.setdefault("info_queried", set())
    by_key: Dict[str, PagoExistenteInfo] = acum.setdefault("info_by_key", {})
    nuevas = {x for x in claves if x} - queried
    if nuevas:
        by_key.update(_pagos_existentes_info_por_clave(db, nuevas))
        queried.update(nuevas)
    return {k: v for k, v in by_key.items() if k in claves}


def _pago_existente_info_para_reportado(
    pr: PagoReportado,
    info_por_clave: Dict[str, PagoExistenteInfo],
) -> Optional[PagoExistenteInfo]:
    if not info_por_clave:
        return None
    for raw in claves_documento_pago_para_reportado(pr):
        c = (normalize_documento(raw) or raw) if raw else None
        if c and c in info_por_clave:
            return info_por_clave[c]
    return None


def _pago_existente_info_resuelto(
    db: Session,
    pr: PagoReportado,
    info_por_clave: Dict[str, PagoExistenteInfo],
) -> Optional[PagoExistenteInfo]:
    """
    Préstamo/pago en cartera que colisiona con este reporte.

    1) Claves canónicas indexadas (rápido, mismo criterio que ``claves_doc_en_pagos``).
    2) ``primer_pago_cartera_por_documento`` con evasión (serial base vs §CD:/P####).
       Necesario cuando ``documento_colisiona_evasion_registrado`` marca DUPLICADO pero el
       IN exacto no enlaza el serial del reporte con el valor almacenado en ``pagos``.
    """
    info = _pago_existente_info_para_reportado(pr, info_por_clave)
    if info is not None:
        return info
    from app.services.pago_numero_documento import primer_pago_cartera_por_documento

    seen_doc: Set[str] = set()
    for raw in claves_documento_pago_para_reportado(pr):
        r = (raw or "").strip()
        if not r or r in seen_doc:
            continue
        seen_doc.add(r)
        pid, prid = primer_pago_cartera_por_documento(db, r)
        if pid is not None:
            nd = db.scalar(select(Pago.numero_documento).where(Pago.id == int(pid)))
            return (
                int(pid),
                int(prid) if prid is not None else None,
                (nd or "").strip() or None,
            )
    return None


def _prestamo_objetivo_por_cedula_norm_batch(
    db: Session,
    cedulas_norm: Set[str],
) -> Tuple[Dict[str, int], Set[str]]:
    """
    Para cada cedula normalizada del lote, devuelve el prestamo APROBADO mas reciente.
    Se usa para saber si un duplicado de Mercantil ya pertenece al mismo prestamo.
    """
    if not cedulas_norm:
        return {}, set()

    variant_to_norms: Dict[str, Set[str]] = defaultdict(set)
    for norm in cedulas_norm:
        for variant in _cedula_lookup_variants(norm):
            variant_to_norms[variant].add(norm)
    if not variant_to_norms:
        return {}, set()

    cedula_lookup = func.upper(
        func.replace(func.replace(Cliente.cedula, "-", ""), " ", "")
    )
    client_ids_by_norm: Dict[str, Set[int]] = defaultdict(set)
    for cliente_id, cedula_raw in db.execute(
        select(Cliente.id, Cliente.cedula).where(
            cedula_lookup.in_(list(variant_to_norms.keys()))
        )
    ).all():
        ced_db = _normalize_cedula_for_client_lookup(str(cedula_raw or ""))
        matched_norms: Set[str] = set()
        for variant in _cedula_lookup_variants(ced_db):
            matched_norms.update(variant_to_norms.get(variant, set()))
        for norm in matched_norms:
            client_ids_by_norm[norm].add(int(cliente_id))

    client_ids = {cid for ids in client_ids_by_norm.values() for cid in ids}
    if not client_ids:
        return {}, set()

    target_by_client: Dict[int, int] = {}
    for cliente_id, prestamo_id in db.execute(
        select(Prestamo.cliente_id, Prestamo.id)
        .where(
            Prestamo.cliente_id.in_(client_ids),
            func.upper(Prestamo.estado) == "APROBADO",
        )
        .order_by(Prestamo.cliente_id.asc(), Prestamo.id.desc())
    ).all():
        cid = int(cliente_id)
        if cid not in target_by_client:
            target_by_client[cid] = int(prestamo_id)

    target_by_norm: Dict[str, int] = {}
    multiple_by_norm: Set[str] = set()
    for norm, ids in client_ids_by_norm.items():
        targets = [target_by_client[cid] for cid in ids if cid in target_by_client]
        if not targets:
            continue
        target_by_norm[norm] = max(targets)
        if len(set(targets)) > 1:
            multiple_by_norm.add(norm)
    return target_by_norm, multiple_by_norm


def _rechazar_aprobacion_si_documento_ya_en_pagos(db: Session, pr: PagoReportado) -> None:
    """
    No aprobar si el comprobante ya existe en cartera (`pagos`).

    Mercantil: colision por documento tal cual (sufijo _A#### / _P#### puede desambiguar).
    Otros bancos: colision por documento base sin sufijo; no se permite reaplicar.
    """
    mercantil = _es_banco_mercantil(getattr(pr, "institucion_financiera", None))
    colisiona = (
        pago_reportado_colisiona_tabla_pagos(db, pr)
        if mercantil
        else pago_reportado_colisiona_tabla_pagos_documento_base(db, pr)
    )
    if colisiona:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede aprobar: el número de documento / comprobante ya consta en la tabla de pagos."
                if mercantil
                else "DUPLICADO: ese comprobante ya está en cartera. Solo Mercantil permite revisión manual; en otros bancos no se puede reaplicar."
            ),
        )


def _numero_operacion_canonico(raw: Optional[str]) -> str:
    """Normaliza solo `numero_operacion` para regla estricta de duplicado."""
    from app.services.pagos_gmail.parse_campos_comprobante import (
        clave_numero_operacion_canonico,
    )

    return clave_numero_operacion_canonico(raw)


def _reportado_pasa_filtro_dedup_num_op(
    it: Any,
    primer_num_op: Dict[str, int],
) -> bool:
    """True si el reporte es el líder de su cadena de nº operación (misma regla que el listado paginado)."""
    num_key = _numero_operacion_canonico(getattr(it, "numero_operacion", None))
    num_raw = (getattr(it, "numero_operacion", None) or "").strip()
    first_id = None
    if num_key:
        first_id = primer_num_op.get(num_key)
    if first_id is None and num_raw:
        first_id = primer_num_op.get(num_raw)
    if first_id is not None and int(it.id) != int(first_id):
        return False
    return True


def _primer_id_por_numero_operacion_para_where(db: Session, wh: List[Any]) -> Dict[str, int]:
    """
    Mapa clave -> primer id por created_at/id dentro del WHERE dado.
    Agrupa por evasión (sufijo/prefijo), no solo igualdad canónica exacta.
    """
    from app.services.pagos_gmail.parse_campos_comprobante import (
        clave_numero_operacion_canonico,
        numeros_operacion_coinciden_o_evasion,
    )

    if not wh:
        return {}
    first: Dict[str, int] = {}
    grupos: list[tuple[int, str]] = []
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
            ipid = int(pid)
            rop = (numero_operacion or "").strip()
            if not rop:
                continue
            lider_id: Optional[int] = None
            for gid, gop in grupos:
                if numeros_operacion_coinciden_o_evasion(rop, gop):
                    lider_id = gid
                    break
            if lider_id is None:
                grupos.append((ipid, rop))
                lider_id = ipid
            k = clave_numero_operacion_canonico(rop)
            if k and k not in first:
                first[k] = lider_id
            if rop not in first:
                first[rop] = lider_id
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
        vals = run_db_with_transient_retry(
            db,
            lambda p=part: db.execute(
                select(Pago.doc_canon_numero).where(Pago.doc_canon_numero.in_(p))
            )
            .scalars()
            .all(),
            attempts=3,
            log_prefix="[COBROS doc_canon]",
        )
        for v in vals:
            if v:
                out.add(v)
    return out


def _duplicados_reportados_por_numero_operacion(
    db: Session,
    *,
    numero_operacion: str,
    excluir_id: Optional[int] = None,
) -> List[Tuple[int, str, str]]:
    """
    Devuelve reportados (id, referencia, estado) con el mismo numero_operacion
    (exacto, sufijo truncado o prefijo OCR). Prefiltra con LIKE antes de comparar.
    """
    from app.services.pagos_gmail.parse_campos_comprobante import (
        _condiciones_sql_numero_operacion,
        numeros_operacion_coinciden_o_evasion,
    )
    op = (numero_operacion or "").strip()
    if not op:
        return []
    conds = _condiciones_sql_numero_operacion(PagoReportado.numero_operacion, op)
    if not conds:
        return []
    stmt = (
        select(
            PagoReportado.id,
            PagoReportado.referencia_interna,
            PagoReportado.estado,
            PagoReportado.numero_operacion,
        )
        .where(
            PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado", "rechazado")),
            or_(*conds),
        )
        .order_by(PagoReportado.created_at.asc(), PagoReportado.id.asc())
        .limit(200)
    )
    if excluir_id is not None:
        stmt = stmt.where(PagoReportado.id != excluir_id)
    rows = db.execute(stmt).all()
    out: List[Tuple[int, str, str]] = []
    seen: set[int] = set()
    for rid, rref, rstate, rnum in rows:
        ipid = int(rid)
        if ipid in seen:
            continue
        if not numeros_operacion_coinciden_o_evasion(op, rnum):
            continue
        seen.add(ipid)
        out.append((ipid, str(rref or ""), str(rstate or "")))
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
        if not dup_pagos and (getattr(r, "numero_operacion", None) or "").strip():
            from app.services.pago_numero_documento import documento_colisiona_evasion_registrado

            dup_pagos = documento_colisiona_evasion_registrado(
                db,
                r.numero_operacion,
                incluir_reportados_activos=False,
            )
        n_doc_eff = documento_numero_desde_pago_reportado(r)[1]
        dup_entre_reportados = False
        if n_doc_eff:
            pid = primer_id_por_norm.get(n_doc_eff)
            if pid is not None:
                dup_entre_reportados = r.id != pid
            elif conteo_norm_en_pagina.get(n_doc_eff, 0) > 1:
                dup_entre_reportados = True
        if not dup_entre_reportados and (getattr(r, "numero_operacion", None) or "").strip():
            from app.services.pagos_gmail.parse_campos_comprobante import (
                numeros_operacion_coinciden_o_evasion,
            )

            op_r = r.numero_operacion
            for other in rows:
                if other.id == r.id:
                    continue
                other_ced = _normalize_cedula_for_client_lookup(
                    ((other.tipo_cedula or "") + (other.numero_cedula or ""))
                    .replace("-", "")
                    .replace(" ", "")
                    .strip()
                    .upper()
                )
                if numeros_operacion_coinciden_o_evasion(
                    op_r,
                    other.numero_operacion,
                    monto_a=getattr(r, "monto", None),
                    monto_b=getattr(other, "monto", None),
                    cedula_a=cedula_norm,
                    cedula_b=other_ced,
                    fecha_a=getattr(r, "fecha_pago", None),
                    fecha_b=getattr(other, "fecha_pago", None),
                ):
                    dup_entre_reportados = True
                    break
        if dup_pagos or dup_entre_reportados:
            # DUPLICADO en observacion: excepcion Mercantil (cartera o entre reportados).
            # Otros bancos con comprobante en cartera: bloqueo via duplicado_en_pagos (sin reaplicar).
            if dup_pagos and not _es_banco_mercantil(
                getattr(r, "institucion_financiera", None)
            ):
                pass
            else:
                partes.append("DUPLICADO")
        result.append(partes)
    return result


def _pago_reportado_list_items_from_rows(
    db: Session,
    rows: List[PagoReportado],
    *,
    primer_id_por_norm_precalc: Optional[Dict[str, int]] = None,
    include_financial_fields: bool = True,
    pagos_canon_acum: Optional[Dict[str, Set[str]]] = None,
    pagos_info_acum: Optional[Dict[str, Any]] = None,
) -> List[PagoReportadoListItem]:
    """Misma lógica de observaciones / tasa que el listado paginado.

    Si ``include_financial_fields`` es False, no calcula tasa Bs/USD ni equivalente (ahorra trabajo
    en barridos masivos donde solo se usa ``observacion`` + Gemini para ``_item_falla_validadores_cola_manual``).

    ``pagos_canon_acum``: opcional, mismo dict en todo un barrido por lotes; claves ``queried`` y ``present``.
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
    if pagos_canon_acum is None:
        claves_doc_en_pagos = _pagos_canonicos_presentes_para_claves(db, candidatos)
    else:
        claves_doc_en_pagos = _pagos_canonicos_presentes_para_claves_reutilizando(
            db, candidatos, pagos_canon_acum
        )
    if pagos_info_acum is None:
        pagos_info_por_clave = _pagos_existentes_info_por_clave(
            db, set(claves_doc_en_pagos)
        )
    else:
        pagos_info_por_clave = _pagos_existentes_info_por_clave_reutilizando(
            db, set(claves_doc_en_pagos), pagos_info_acum
        )
    pago_info_por_reportado: Dict[int, PagoExistenteInfo] = {}
    cedulas_para_prestamo_objetivo: Set[str] = set()
    for idx, r in enumerate(rows):
        info = _pago_existente_info_resuelto(db, r, pagos_info_por_clave)
        if info is not None:
            pago_info_por_reportado[int(r.id)] = info
        ced_norm = cedula_norms[idx] if idx < len(cedula_norms) else ""
        if ced_norm:
            cedulas_para_prestamo_objetivo.add(ced_norm)
    prestamo_objetivo_por_cedula, prestamo_objetivo_multiple_cedulas = (
        _prestamo_objetivo_por_cedula_norm_batch(db, cedulas_para_prestamo_objetivo)
        if cedulas_para_prestamo_objetivo
        else ({}, set())
    )
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
        pago_info = pago_info_por_reportado.get(int(r.id))
        dup_pagos = pago_info is not None
        pago_existente_id = pago_info[0] if pago_info is not None else None
        prestamo_existente_id = pago_info[1] if pago_info is not None else None
        numero_documento_pago_existente = (
            pago_info[2] if pago_info is not None else None
        )
        cedula_norm = cedula_norms[i] if i < len(cedula_norms) else ""
        prestamo_objetivo_id = prestamo_objetivo_por_cedula.get(cedula_norm)
        prestamo_objetivo_multiple = (
            cedula_norm in prestamo_objetivo_multiple_cedulas
            if prestamo_objetivo_id is not None
            else None
        )
        prestamo_duplicado_es_objetivo = (
            int(prestamo_existente_id) == int(prestamo_objetivo_id)
            if prestamo_existente_id is not None and prestamo_objetivo_id is not None
            else None
        )
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
            duplicado_en_pagos=bool(dup_pagos),
            pago_existente_id=pago_existente_id,
            prestamo_existente_id=prestamo_existente_id,
            numero_documento_pago_existente=numero_documento_pago_existente,
            prestamo_objetivo_id=prestamo_objetivo_id,
            prestamo_objetivo_multiple=prestamo_objetivo_multiple,
            prestamo_duplicado_es_objetivo=prestamo_duplicado_es_objetivo,
        ))
    return items


def _query_reportados_falla_validadores_pendientes_exportar(
    db: Session,
    cedula: Optional[str],
    institucion: Optional[str],
) -> List[PagoReportado]:
    """Pendiente, en revisión o aprobado (legacy), aún no marcados como exportados; sin fechas (mismos filtros opcionales que el front)."""
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


