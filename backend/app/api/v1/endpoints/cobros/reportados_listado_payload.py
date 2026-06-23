"""Cobros: payloads listado/KPIs y caches primer-maps."""
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
from .listado_kpis_cache import (
    _cobros_listado_kpis_cache_get,
    _cobros_listado_kpis_cache_get_stale,
    _cobros_listado_kpis_cache_set,
    _cobros_listado_kpis_release_singleflight,
    _cobros_listado_kpis_try_acquire_singleflight,
)
from .reportados_dedup_helpers import *
from .reportados_validadores_helpers import (
    _item_falla_validadores_cola_manual,
    _regularizar_reportados_guarded,
    reportado_falla_validadores_cobros,
)
from .schemas import PagoReportadoListItem

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
    _invalidate_cobros_listado_kpis_cache()

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


def _reencolar_escaner_infopagos_aprobado_sin_gestion_por_cedula(
    db: Session,
    *,
    cedula: Optional[str],
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
) -> int:
    """
    Escaneos Infopagos auto-aprobados (sin usuario Cobros) vuelven a en_revision al buscar por cédula.

    Cubre reportes que quedaron en `aprobado` por regularización o flujo viejo del escáner y ya no
    aparecen en la cola manual aunque el operador espera revisarlos.
    """
    if not cedula or not str(cedula).strip():
        return 0
    filtros = _filtros_fecha_cedula_institucion_reportados(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=None,
    )
    wh = [
        PagoReportado.canal_ingreso == "infopagos",
        PagoReportado.estado == "aprobado",
        PagoReportado.usuario_gestion_id.is_(None),
    ] + filtros
    rows = (
        db.execute(
            select(PagoReportado)
            .where(*wh)
            .order_by(PagoReportado.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0
    n = 0
    for pr in rows:
        pr.estado = "en_revision"
        pr.falla_validadores_manual = True
        obs = (pr.observacion or "").strip()
        nota = "[COBROS] Reencolado a revision manual (busqueda escaner Infopagos)."
        pr.observacion = nota if not obs else f"{obs} / {nota}"
        db.add(pr)
        n += 1
    if n:
        db.commit()
        _invalidate_cobros_listado_kpis_cache()
        logger.info(
            "[COBROS] Reencolados %s reportes Infopagos a en_revision (cedula=%s)",
            n,
            (cedula or "").strip().upper(),
        )
    return n


def _where_clauses_cola_reportados(
    estado: Optional[str],
    incluir_exportados: bool,
    exportados_subq: Any,
    filtros: List[Any],
) -> List[Any]:
    """Predicados WHERE compartidos: cola pendiente / en_revision (+ exportados + filtros fecha/cedula/banco).

    El estado `aprobado` ya no entra en la cola por defecto: cuando un reporte queda en
    `aprobado` el pago ya fue creado en cartera y aplicado a cuotas; conservarlo en la
    cola manual era ruido visual y forzaba un barrido extra de filas que no requieren
    accion humana. Para auditoria de aprobados usar el historico o el filtro explicito
    `estado=aprobado` (que sigue funcionando aqui por compatibilidad de URL/permaview).
    """
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
        wh.append(PagoReportado.estado.in_(("pendiente", "en_revision")))
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
    if cedula and str(cedula).strip():
        _reencolar_escaner_infopagos_aprobado_sin_gestion_por_cedula(
            db,
            cedula=cedula,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
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

    # Cola manual: pendiente / en_revision que NO cumplen validadores.
    # `aprobado` ya no entra en la cola por defecto (se accede solo via filtro explicito).
    wh = _where_clauses_cola_reportados(estado, incluir_exportados, exportados_subq, filtros)
    wh_primer_scope = (
        _where_clauses_cola_reportados(None, incluir_exportados, exportados_subq, filtros)
        if estado in ("pendiente", "en_revision")
        else wh
    )
    primer_scope_key = _primer_maps_scope_key(
        incluir_exportados=incluir_exportados,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
    )
    primer_precalc, primer_num_op, _ = _get_primer_triple_cached(
        db, wh_primer_scope, primer_scope_key
    )
    # Fast path: filtrar el barrido por la columna persistida `falla_validadores_manual`
    # (indexada). Las filas con `falla=False` ya cumplen validadores y el bucle Python las
    # descartaria igualmente con `_item_falla_validadores_cola_manual`; ahorrar leerlas y
    # iterarlas reduce el escaneo de O(filas_en_estado) a O(filas_que_realmente_van_a_cola).
    # `IS NULL` (filas no backfilled todavia) se incluye para preservar correctness — el
    # validador Python se ejecutara igual sobre ellas. El mapa de dedup (`primer_num_op`)
    # se sigue calculando sobre `wh_primer_scope` SIN este filtro, para que un duplicado
    # "lider" con `falla=False` siga liderando su cadena y los "seguidores" se descarten
    # por dedup como hoy (semantica preservada).
    wh_scan = list(wh) + [
        or_(
            PagoReportado.estado == "en_revision",
            PagoReportado.falla_validadores_manual.is_(True),
            PagoReportado.falla_validadores_manual.is_(None),
        )
    ]
    q = select(PagoReportado).where(*wh_scan).order_by(
        case((PagoReportado.estado == "rechazado", 1), else_=0),
        PagoReportado.created_at.asc(),
    )

    emit_counts = bool(emit_manual_estado_counts_for_kpis and estado is None)
    by_estado_manual: Dict[str, int] = {"pendiente": 0, "en_revision": 0}

    batch = _COBROS_LISTADO_SCAN_BATCH
    offset_scan = 0
    skip_need = (page - 1) * per_page
    take_need = per_page
    page_ids_ordered: List[int] = []
    total = 0
    pagos_canon_acum: Dict[str, Set[str]] = {"queried": set(), "present": set()}
    pagos_info_acum: Dict[str, Any] = {"info_queried": set(), "info_by_key": {}}
    while True:
        rows = db.execute(q.offset(offset_scan).limit(batch)).scalars().all()
        if not rows:
            break
        for it in _pago_reportado_list_items_from_rows(
            db,
            rows,
            primer_id_por_norm_precalc=primer_precalc,
            include_financial_fields=False,
            pagos_canon_acum=pagos_canon_acum,
            pagos_info_acum=pagos_info_acum,
        ):
            if not _reportado_pasa_filtro_dedup_num_op(it, primer_num_op):
                continue
            if not _item_falla_validadores_cola_manual(it):
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
                pagos_canon_acum=pagos_canon_acum,
                pagos_info_acum=pagos_info_acum,
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
    Conteos por estado con mismos filtros fecha/cedula/institucion que el listado.
    pendiente / en_revision: solo los que NO cumplen validadores (cola de analisis manual).
    importado / rechazado: totales SQL (estados terminales).

    `aprobado` ya no se computa: el pago aprobado ya esta en cartera (tabla pagos) y no
    requiere accion. Mantenerlo costaba un barrido extra de la cola y un KPI confuso
    ("aprobado" pero con observacion DUPLICADO en una pantalla de cola por gestionar).

    Si `manual_queue_counts` viene del listado (mismo barrido), no se vuelve a escanear la cola.
    """
    filtros = _filtros_fecha_cedula_institucion_reportados(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
    )
    counts = {"pendiente": 0, "en_revision": 0, "rechazado": 0, "importado": 0}

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
        primer_kpi, primer_num_op_kpi, _ = _get_primer_triple_cached(db, wh_kpi, kpi_scope_key)
        # Fast path simetrico al listado: el barrido KPI itera solo filas que pueden caer en
        # cola (`falla=True` o NULL pendiente de backfill). El precalc de dedup (primer_kpi)
        # se calcula sobre el scope completo `wh_kpi` SIN filtro, para que un duplicado
        # "lider" con `falla=False` siga liderando y sus "seguidores" se descarten igual.
        wh_kpi_scan = list(wh_kpi) + [
            or_(
                PagoReportado.estado == "en_revision",
                PagoReportado.falla_validadores_manual.is_(True),
                PagoReportado.falla_validadores_manual.is_(None),
            )
        ]
        q_scan = select(PagoReportado).where(*wh_kpi_scan).order_by(PagoReportado.created_at.asc())

        batch = _COBROS_LISTADO_SCAN_BATCH
        offset_scan = 0
        pagos_canon_acum_kpi: Dict[str, Set[str]] = {"queried": set(), "present": set()}
        pagos_info_acum_kpi: Dict[str, Any] = {"info_queried": set(), "info_by_key": {}}
        while True:
            rows_b = db.execute(q_scan.offset(offset_scan).limit(batch)).scalars().all()
            if not rows_b:
                break
            for it in _pago_reportado_list_items_from_rows(
                db,
                rows_b,
                primer_id_por_norm_precalc=primer_kpi,
                include_financial_fields=False,
                pagos_canon_acum=pagos_canon_acum_kpi,
                pagos_info_acum=pagos_info_acum_kpi,
            ):
                if not _reportado_pasa_filtro_dedup_num_op(it, primer_num_op_kpi):
                    continue
                if not _item_falla_validadores_cola_manual(it):
                    continue
                st = (it.estado or "").strip()
                if st in ("pendiente", "en_revision"):
                    counts[st] += 1
            offset_scan += len(rows_b)

    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "rechazado", "importado"))
    return counts


