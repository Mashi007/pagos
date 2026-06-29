"""Cache KPIs listado cobros y rate limit escaner."""
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
_COBROS_LISTADO_KPIS_CACHE_TTL_SEC = 900  # 15 minutos
_COBROS_LISTADO_KPIS_CACHE_STALE_TTL_SEC = 7200  # 2 horas (fallback resiliente)
_COBROS_LISTADO_KPIS_SINGLEFLIGHT_WAIT_SEC = 28.0
_COBROS_LISTADO_KPIS_SINGLEFLIGHT_STALE_SEC = 30.0
_COBROS_LISTADO_KPIS_CACHE_PREFIX = "cobros:listado_y_kpis:v2:"
_COBROS_LISTADO_KPIS_CACHE_STALE_SUFFIX = ":stale"
_cobros_listado_kpis_mem_cache: Dict[str, Tuple[float, dict]] = {}
_cobros_listado_kpis_mem_stale_cache: Dict[str, Tuple[float, dict]] = {}
_cobros_listado_kpis_mem_lock = threading.Lock()
_cobros_listado_kpis_inflight: Dict[str, float] = {}
_ESCANER_RATE_LIMIT_WINDOW_SEC = 60
_ESCANER_RATE_LIMIT_MAX_COUNT = 20
_escaner_rate_limit_mem: Dict[str, Tuple[int, float]] = {}
_escaner_rate_limit_mem_lock = threading.Lock()


def _enforce_escaner_rate_limit(request: Request) -> None:
    """
    Limita llamadas al escáner por usuario (o IP fallback) para evitar picos de costo/latencia.
    Ventana fija de 60s: máx 20 solicitudes.
    """
    cur = getattr(request.state, "user", None)
    uid = getattr(cur, "id", None) if cur is not None else None
    actor = f"user:{uid}" if uid is not None else f"ip:{getattr(request.client, 'host', None) or 'unknown'}"
    detail_429 = "Demasiadas solicitudes al escáner. Espere un minuto e intente de nuevo."
    key = f"rate_limit:cobros_escaner:{actor}"
    now = time.time()

    client = get_redis_client()
    if client:
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            incr_result, ttl = pipe.execute()
            if ttl == -1:
                client.expire(key, _ESCANER_RATE_LIMIT_WINDOW_SEC)
            if int(incr_result or 0) > _ESCANER_RATE_LIMIT_MAX_COUNT:
                raise HTTPException(status_code=429, detail=detail_429)
            return
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("[ESCANER] Rate limit Redis error: %s", e)

    with _escaner_rate_limit_mem_lock:
        count, start_ts = _escaner_rate_limit_mem.get(key, (0, now))
        if now - start_ts >= _ESCANER_RATE_LIMIT_WINDOW_SEC:
            _escaner_rate_limit_mem[key] = (1, now)
            return
        count += 1
        _escaner_rate_limit_mem[key] = (count, start_ts)
        if count > _ESCANER_RATE_LIMIT_MAX_COUNT:
            raise HTTPException(status_code=429, detail=detail_429)


def _cobros_listado_kpis_cache_key_payload(
    *,
    estado: Optional[str],
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    cedula: Optional[str],
    institucion: Optional[str],
    page: int,
    per_page: int,
    incluir_exportados: bool,
) -> str:
    payload = {
        "estado": (estado or "").strip().lower(),
        "fecha_desde": fecha_desde.isoformat() if isinstance(fecha_desde, date) else "",
        "fecha_hasta": fecha_hasta.isoformat() if isinstance(fecha_hasta, date) else "",
        "cedula": (cedula or "").strip().upper(),
        "institucion": (institucion or "").strip().upper(),
        "page": int(page),
        "per_page": int(per_page),
        "incluir_exportados": bool(incluir_exportados),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _cobros_listado_kpis_storage_key(cache_payload: str) -> str:
    digest = hashlib.sha1(cache_payload.encode("utf-8")).hexdigest()
    return f"{_COBROS_LISTADO_KPIS_CACHE_PREFIX}{digest}"


def _cobros_listado_kpis_stale_storage_key(cache_payload: str) -> str:
    return f"{_cobros_listado_kpis_storage_key(cache_payload)}{_COBROS_LISTADO_KPIS_CACHE_STALE_SUFFIX}"


def _cobros_listado_kpis_cache_get(cache_payload: str) -> Optional[dict]:
    key = _cobros_listado_kpis_storage_key(cache_payload)
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            raw = redis_client.get(key)
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception as e:
            logger.warning("[COBROS_CACHE] Redis get listado-y-kpis falló: %s", e)

    now = time.time()
    with _cobros_listado_kpis_mem_lock:
        hit = _cobros_listado_kpis_mem_cache.get(key)
        if not hit:
            return None
        exp_ts, payload = hit
        if exp_ts > now:
            return payload
        _cobros_listado_kpis_mem_cache.pop(key, None)
    return None


def _cobros_listado_kpis_cache_get_stale(cache_payload: str) -> Optional[dict]:
    key = _cobros_listado_kpis_stale_storage_key(cache_payload)
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            raw = redis_client.get(key)
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception as e:
            logger.warning("[COBROS_CACHE] Redis get stale listado-y-kpis falló: %s", e)

    now = time.time()
    with _cobros_listado_kpis_mem_lock:
        hit = _cobros_listado_kpis_mem_stale_cache.get(key)
        if not hit:
            return None
        exp_ts, payload = hit
        if exp_ts > now:
            return payload
        _cobros_listado_kpis_mem_stale_cache.pop(key, None)
    return None


def _cobros_listado_kpis_cache_set(cache_payload: str, data: dict) -> None:
    key = _cobros_listado_kpis_storage_key(cache_payload)
    stale_key = _cobros_listado_kpis_stale_storage_key(cache_payload)
    encoded = jsonable_encoder(data)
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(
                key,
                _COBROS_LISTADO_KPIS_CACHE_TTL_SEC,
                json.dumps(encoded, ensure_ascii=False, default=str),
            )
            redis_client.setex(
                stale_key,
                _COBROS_LISTADO_KPIS_CACHE_STALE_TTL_SEC,
                json.dumps(encoded, ensure_ascii=False, default=str),
            )
            return
        except Exception as e:
            logger.warning("[COBROS_CACHE] Redis set listado-y-kpis falló: %s", e)

    with _cobros_listado_kpis_mem_lock:
        _cobros_listado_kpis_mem_cache[key] = (
            time.time() + _COBROS_LISTADO_KPIS_CACHE_TTL_SEC,
            encoded,
        )
        _cobros_listado_kpis_mem_stale_cache[stale_key] = (
            time.time() + _COBROS_LISTADO_KPIS_CACHE_STALE_TTL_SEC,
            encoded,
        )


def _invalidate_cobros_listado_kpis_cache() -> None:
    with _cobros_listado_kpis_mem_lock:
        _cobros_listado_kpis_mem_cache.clear()
        # Mantener stale cache para fallback resiliente durante picos/redeploy.

    redis_client = get_redis_client()
    if redis_client is None:
        return
    try:
        keys = list(redis_client.scan_iter(match=f"{_COBROS_LISTADO_KPIS_CACHE_PREFIX}*"))
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.warning("[COBROS_CACHE] Redis invalidate listado-y-kpis falló: %s", e)


def _drop_pagos_from_listado_kpis_cache(
    pago_ids: Iterable[int],
    *,
    estados_previos: Optional[Dict[int, str]] = None,
) -> None:
    """
    Parche quirurgico multi-id: quita TODOS los `pago_ids` de TODAS las entradas vivas del cache
    listado-y-kpis (Redis + memoria + stale), ajusta `total`, `kpis[estado]` y `kpis['total']`
    en sitio. Evita la recomputacion BD completa (20-30s con 1 worker) tras DELETE/APROBAR/RECHAZAR,
    que es la causa real de la cascada de 502 y de la sensacion "no borra/aprueba rapido".

    `estados_previos` opcional (id -> estado_anterior, p.ej. "pendiente"/"en_revision"):
    si el id NO esta en la pagina cacheada (paginacion: cache de page=1 no contiene
    items de page>=2) pero la entry pertenece a la misma cola por defecto, igual se
    decrementa `kpis[estado_anterior]` y `total`. Es la causa real del bug "card
    Pendiente=17 pero al hacer click no hay registros": antes el contador solo se
    decrementaba si el item era visible en la pagina, dejando el KPI inflado tras
    aprobar/eliminar filas de paginas posteriores.

    Disenio:
    - Un solo barrido del cache (Redis + memoria) para todo el conjunto de ids: tras
      aprobar, ademas del pago aprobado tambien se marcan los hermanos duplicados como
      `eliminado_duplicado`; resolverlos en una sola pasada vale mas que repetir el scan.
    - **Preserva el TTL original** (con `redis_client.ttl(key)`); un parche no debe
      diferir el siguiente recalculo natural.
    - Si la deserializacion JSON o el TTL falla, esa entry se invalida (delete) y se
      sigue con el resto: nunca dejar contadores corruptos visibles.
    - El stale cache (sufijo `:stale`) tambien se parchea para que el fallback
      resiliente no resucite filas mutadas en picos / redeploy.

    No reemplaza a `_invalidate_cobros_listado_kpis_cache` para mutaciones que afectan
    muchas filas a la vez (marcar-exportados, recibo regenerado, reanalisis Gemini que
    cambia la observacion): alli seguir invalidando.
    """
    ids: Set[int] = {int(x) for x in pago_ids if x is not None}
    if not ids:
        return
    prev_states: Dict[int, str] = {
        int(k): (v or "").strip()
        for k, v in (estados_previos or {}).items()
        if v
    }
    redis_client = get_redis_client()

    def _patch_entry(payload: dict) -> Optional[dict]:
        try:
            items = payload.get("items")
            if not isinstance(items, list):
                return None
            removed_items: List[dict] = []
            removed_ids_in_items: Set[int] = set()
            new_items: List[Any] = []
            for it in items:
                if isinstance(it, dict):
                    try:
                        it_id = int(it.get("id"))
                    except (TypeError, ValueError):
                        it_id = None
                    if it_id is not None and it_id in ids:
                        removed_items.append(it)
                        removed_ids_in_items.add(it_id)
                        continue
                new_items.append(it)
            # IDs que no estan en la pagina cacheada pero que sabemos pertenecian
            # al scope contado por esta entry (kpis incluyen todas las paginas).
            ghost_ids = ids - removed_ids_in_items
            ghost_decrement_by_estado: Dict[str, int] = {}
            ghost_total_decrement = 0
            for gid in ghost_ids:
                est = prev_states.get(gid)
                if not est:
                    continue
                ghost_decrement_by_estado[est] = (
                    ghost_decrement_by_estado.get(est, 0) + 1
                )
                ghost_total_decrement += 1
            if not removed_items and not ghost_decrement_by_estado:
                return None
            if removed_items:
                payload["items"] = new_items
            try:
                page_total_dec = len(removed_items) + ghost_total_decrement
                payload["total"] = max(
                    0, int(payload.get("total", 0)) - page_total_dec
                )
            except (TypeError, ValueError):
                pass
            kpis = payload.get("kpis")
            if isinstance(kpis, dict):
                for ri in removed_items:
                    est = ri.get("estado") if isinstance(ri, dict) else None
                    if isinstance(est, str):
                        est_key = est.strip()
                        if est_key and isinstance(
                            kpis.get(est_key), (int, float)
                        ):
                            kpis[est_key] = max(0, int(kpis[est_key]) - 1)
                for est_key, dec in ghost_decrement_by_estado.items():
                    if est_key and isinstance(
                        kpis.get(est_key), (int, float)
                    ):
                        kpis[est_key] = max(0, int(kpis[est_key]) - dec)
                if isinstance(kpis.get("total"), (int, float)):
                    kpis["total"] = max(
                        0,
                        int(kpis["total"])
                        - (len(removed_items) + ghost_total_decrement),
                    )
                payload["kpis"] = kpis
            return payload
        except Exception:
            return None

    if redis_client is not None:
        try:
            keys = list(redis_client.scan_iter(match=f"{_COBROS_LISTADO_KPIS_CACHE_PREFIX}*"))
            for key in keys:
                try:
                    raw = redis_client.get(key)
                    if not raw:
                        continue
                    parsed = json.loads(raw)
                    if not isinstance(parsed, dict):
                        continue
                    patched = _patch_entry(parsed)
                    if patched is None:
                        continue
                    try:
                        ttl = redis_client.ttl(key)
                    except Exception:
                        ttl = None
                    if ttl is None or ttl < 0:
                        # TTL desconocido: no rejuvenecer la entry; mejor borrarla para
                        # que el próximo request vuelva a poblarla con datos frescos
                        # (la siguiente compleja la sirve singleflight + stale fallback).
                        try:
                            redis_client.delete(key)
                        except Exception:
                            pass
                        continue
                    try:
                        redis_client.setex(
                            key,
                            int(ttl),
                            json.dumps(patched, ensure_ascii=False, default=str),
                        )
                    except Exception:
                        try:
                            redis_client.delete(key)
                        except Exception:
                            pass
                except Exception as inner_e:
                    logger.debug(
                        "[COBROS_CACHE] parche delete entry %s falló (%s); borrando key",
                        key,
                        inner_e,
                    )
                    try:
                        redis_client.delete(key)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(
                "[COBROS_CACHE] parche delete Redis falló (%s); fallback a invalidación total.",
                e,
            )
            _invalidate_cobros_listado_kpis_cache()
            return

    now = time.time()
    with _cobros_listado_kpis_mem_lock:
        for cache_dict in (
            _cobros_listado_kpis_mem_cache,
            _cobros_listado_kpis_mem_stale_cache,
        ):
            for key in list(cache_dict.keys()):
                exp_ts, payload = cache_dict[key]
                if not isinstance(payload, dict):
                    continue
                # Trabajar sobre copia somera; los items y kpis se reasignan en el parche.
                patched = _patch_entry(dict(payload))
                if patched is None:
                    continue
                if exp_ts <= now:
                    cache_dict.pop(key, None)
                    continue
                cache_dict[key] = (exp_ts, patched)


def _drop_pago_from_listado_kpis_cache(pago_id: int) -> None:
    """Atajo single-id; conserva firma historica del call site del DELETE."""
    _drop_pagos_from_listado_kpis_cache([pago_id])


def _cobros_listado_kpis_try_acquire_singleflight(cache_payload: str) -> bool:
    """
    True si este request toma el cálculo de esta key; False si otro ya está calculando.
    TTL interno corto para no dejar bloqueo huérfano si un worker muere.
    """
    key = _cobros_listado_kpis_storage_key(cache_payload)
    now = time.time()
    with _cobros_listado_kpis_mem_lock:
        owner_ts = _cobros_listado_kpis_inflight.get(key)
        if owner_ts is not None and (now - owner_ts) < _COBROS_LISTADO_KPIS_SINGLEFLIGHT_STALE_SEC:
            return False
        _cobros_listado_kpis_inflight[key] = now
        return True


def _cobros_listado_kpis_release_singleflight(cache_payload: str) -> None:
    key = _cobros_listado_kpis_storage_key(cache_payload)
    with _cobros_listado_kpis_mem_lock:
        _cobros_listado_kpis_inflight.pop(key, None)


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
