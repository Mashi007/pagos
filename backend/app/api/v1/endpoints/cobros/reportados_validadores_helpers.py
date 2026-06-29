"""Cobros: validadores Gemini y falla_validadores."""
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
from . import reportados_dedup_helpers as _dedup
from .reportados_dedup_helpers import (
    _cedula_lookup_variants,
    _collect_candidatos_canon_desde_reportados,
    _es_banco_mercantil,
    _gemini_coincide_exacto_ok,
    _normalize_cedula_for_client_lookup,
    _pago_existente_info_resuelto,
    _pago_reportado_list_items_from_rows,
    _pagos_existentes_info_por_clave,
    _referencia_display,
)

def _regularizar_reportados_gemini_ok_sin_falla_manual(
    db: Session, max_ids: int = 24, deadline_monotonic: Optional[float] = None
) -> None:
    """
    Al listar Cobros: si un reporte ya cumple validadores (misma regla que la cola), pasa a aprobado
    e intenta importar a `pagos` + cuotas como en el flujo público.

    Candidatos: estados pendiente/en_revision/aprobado con Gemini OK (`true`/`1`),
    Gemini `false` sin comentario (falso negativo frecuente), o sin Gemini (NULL/vacío).
    En todos los casos `reportado_falla_validadores_cobros` decide si pasa.
    Errores de API (`error`) no son candidatos (se excluyen por el OR).
    """
    from app.services.cobros import cobros_publico_reporte_service as cpr

    gem_col = func.lower(func.trim(func.coalesce(PagoReportado.gemini_coincide_exacto, "")))
    com_trim = func.trim(func.coalesce(PagoReportado.gemini_comentario, ""))
    candidatos_regularizar = or_(
        gem_col.in_(("true", "1")),
        and_(gem_col == "false", com_trim == ""),
        gem_col == "",
    )
    try:
        ids = list(
            db.execute(
                select(PagoReportado.id)
                .where(
                    PagoReportado.estado.in_(("pendiente", "aprobado")),
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
            # En revisión manual explícita: no auto-aprobar al listar Cobros.
            if (getattr(pr, "estado", None) or "").strip() == "en_revision":
                continue
            # Escáner / operador dejó falla_validadores_manual=True: no auto-aprobar al listar.
            if getattr(pr, "falla_validadores_manual", None) is True:
                continue
            if getattr(pr, "estado", None) in ("pendiente", "en_revision", "aprobado") and pago_reportado_colisiona_tabla_pagos(
                db, pr
            ):
                ids_colision_importado.append(pid)
                continue
            falla = reportado_falla_validadores_cobros(db, pr)
            pr.falla_validadores_manual = falla
            if falla:
                db.commit()
                continue
            ref = (pr.referencia_interna or "").strip() or str(pr.id)
            if getattr(pr, "estado", None) in ("pendiente", "en_revision"):
                pr.estado = "aprobado"
                pr.falla_validadores_manual = False
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
                .values(estado="importado", falla_validadores_manual=False, updated_at=func.now())
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
    - presupuesto de tiempo por request,
    - gracia post-cold-start para no bloquear los primeros requests.
    El backfill progresivo de falla_validadores_manual solo corre en los paths
    de cooldown/lock-miss para no bloquear el primer request post-cold-start.
    """
    now = time.monotonic()
    if now - _dedup._process_start_monotonic < _dedup._REGULARIZA_COLD_START_GRACE_SEC:
        return
    if now - _dedup._regulariza_last_run_monotonic < _dedup._REGULARIZA_MIN_INTERVAL_SEC:
        _backfill_falla_validadores_lote(db)
        return
    if not _dedup._regulariza_lock.acquire(blocking=False):
        _backfill_falla_validadores_lote(db)
        return
    try:
        now_inside = time.monotonic()
        if (
            now_inside - _dedup._regulariza_last_run_monotonic
            < _dedup._REGULARIZA_MIN_INTERVAL_SEC
        ):
            return
        _dedup._regulariza_last_run_monotonic = now_inside
        deadline = now_inside + (_dedup._REGULARIZA_TIME_BUDGET_MS / 1000.0)
        _regularizar_reportados_gemini_ok_sin_falla_manual(
            db,
            max_ids=_dedup._REGULARIZA_MAX_IDS_PER_RUN,
            deadline_monotonic=deadline,
        )
    finally:
        _dedup._regulariza_lock.release()


def _estado_label_estado_reportado(estado: str) -> str:
    m = {
        "pendiente": "Pendiente",
        "en_revision": "En revisión (manual)",
        "aprobado": "Aprobado",
        "rechazado": "Rechazado",
        "importado": "Importado a Pagos",
    }
    return m.get((estado or "").strip(), estado or "")


def _prestamo_objetivo_desde_cedula(
    db: Session,
    tipo_cedula: Optional[str],
    numero_cedula: Optional[str],
) -> Tuple[Optional[int], Optional[bool], Optional[str], Optional[int]]:
    cedula_norm = _normalize_cedula_for_client_lookup(
        ((tipo_cedula or "") + (numero_cedula or ""))
        .replace("-", "")
        .replace(" ", "")
        .strip()
        .upper()
    )
    variants = _cedula_lookup_variants(cedula_norm)
    if not variants:
        return None, None, "cedula_no_registrada", None

    cedula_lookup = func.upper(
        func.replace(func.replace(Cliente.cedula, "-", ""), " ", "")
    )
    cliente = db.execute(
        select(Cliente).where(cedula_lookup.in_(variants))
    ).scalars().first()
    if not cliente:
        return None, None, "cedula_no_registrada", None

    prestamos_aprob = db.execute(
        select(Prestamo.id)
        .where(
            Prestamo.cliente_id == cliente.id,
            func.upper(Prestamo.estado) == "APROBADO",
        )
        .order_by(Prestamo.id.desc())
    ).scalars().all()
    if prestamos_aprob:
        return int(prestamos_aprob[0]), len(prestamos_aprob) > 1, None, None

    prestamo_liquidado = db.execute(
        select(Prestamo.id)
        .where(
            Prestamo.cliente_id == cliente.id,
            func.upper(Prestamo.estado) == "LIQUIDADO",
        )
        .order_by(Prestamo.id.desc())
        .limit(1)
    ).scalars().first()
    if prestamo_liquidado is not None:
        return None, None, "liquidado", int(prestamo_liquidado)

    return None, None, "sin_aprobado", None


def _diagnostico_duplicado_reportado(
    db: Session,
    pr_like: Any,
    *,
    tipo_cedula: Optional[str],
    numero_cedula: Optional[str],
) -> PagoReportadoDuplicadoDiagnostico:
    pago_existente_info = _pago_existente_info_resuelto(
        db,
        pr_like,
        _pagos_existentes_info_por_clave(
            db,
            _collect_candidatos_canon_desde_reportados([pr_like]),
        ),
    )
    pago_existente_id: Optional[int] = (
        pago_existente_info[0] if pago_existente_info is not None else None
    )
    prestamo_existente_id: Optional[int] = None
    pago_existente_estado: Optional[str] = None
    pago_existente_fecha_pago: Optional[date] = None
    if pago_existente_id is not None:
        p_exist = db.execute(
            select(Pago).where(Pago.id == pago_existente_id)
        ).scalars().first()
        if p_exist:
            prestamo_existente_id = getattr(p_exist, "prestamo_id", None)
            pago_existente_estado = getattr(p_exist, "estado", None)
            fp = getattr(p_exist, "fecha_pago", None)
            if fp is not None:
                pago_existente_fecha_pago = (
                    fp.date() if isinstance(fp, datetime) else fp
                )

    try:
        (
            prestamo_objetivo_id,
            prestamo_objetivo_multiple,
            prestamo_objetivo_motivo,
            prestamo_referencia_id,
        ) = _prestamo_objetivo_desde_cedula(db, tipo_cedula, numero_cedula)
    except Exception:
        prestamo_objetivo_id = None
        prestamo_objetivo_multiple = None
        prestamo_objetivo_motivo = None
        prestamo_referencia_id = None

    prestamo_duplicado_es_objetivo: Optional[bool] = None
    if prestamo_existente_id is not None and prestamo_objetivo_id is not None:
        prestamo_duplicado_es_objetivo = int(prestamo_existente_id) == int(
            prestamo_objetivo_id
        )

    return PagoReportadoDuplicadoDiagnostico(
        duplicado_en_pagos=bool(pago_existente_id is not None),
        pago_existente_id=pago_existente_id,
        prestamo_existente_id=prestamo_existente_id,
        pago_existente_estado=pago_existente_estado,
        pago_existente_fecha_pago=pago_existente_fecha_pago,
        prestamo_objetivo_id=prestamo_objetivo_id,
        prestamo_objetivo_multiple=prestamo_objetivo_multiple,
        prestamo_duplicado_es_objetivo=prestamo_duplicado_es_objetivo,
        prestamo_objetivo_motivo=prestamo_objetivo_motivo,
        prestamo_referencia_id=prestamo_referencia_id,
    )


def _obs_sin_duplicado(obs: str) -> str:
    partes = [p.strip() for p in (obs or "").split("/") if p.strip()]
    partes = [p for p in partes if "DUPLICADO" not in p.upper()]
    return " / ".join(partes)


def _obs_efectiva_para_validadores(
    obs: str,
    institucion: str,
    *,
    duplicado_mismo_prestamo: bool = False,
) -> str:
    """
    Observación relevante para decidir cola manual.

    DUPLICADO de banco distinto a Mercantil → toda la observación se descarta (auto-desestimar).
    El pago original ya está siendo gestionado; revisar el duplicado no aporta valor.
    Mercantil mantiene duplicados en cola salvo que el pago existente sea del mismo
    préstamo objetivo; en ese caso "DUPLICADO" no cuenta como falla manual.
    """
    if not obs:
        return ""
    if "DUPLICADO" not in obs:
        return obs
    if duplicado_mismo_prestamo:
        return _obs_sin_duplicado(obs)
    if _es_banco_mercantil(institucion):
        return obs
    return ""


def _item_falla_validadores_cola_manual(it: PagoReportadoListItem) -> bool:
    """
    True = requiere análisis manual (cola en pantalla: no cumplen validadores).

    Los reportes en estado ``en_revision`` siempre entran en cola (p. ej. escáner Infopagos con
    confirmación humana): Cobros debe aprobar/rechazar aunque Gemini y las reglas automáticas cuadren.

    Excepciones de negocio (sin autoconciliar): bolivares (BS) o monto >= 500 en la moneda reportada.

    Si Gemini marcó coincidencia exacta (`true`/`1`), solo falla si queda observación de **reglas**
    (DUPLICADO, NO CLIENTES, etc.); el texto residual de Gemini no cuenta en ese caso (se omite al armar la observación).

    DUPLICADO de banco distinto a Mercantil se auto-desestima (no requiere revisión manual).

    Si Gemini respondió `false` pero la observación armada está vacía (sin reglas ni columnas
    deducidas del comentario), no se exige paso manual: suele ser falso negativo con comentario vacío
    cuando los validadores determinísticos ya cuadran.

    `error` (fallo de API / sin clave) sigue exigiendo revisión manual.
    """
    from app.services.pagos_gmail.parse_campos_comprobante import reportado_exento_autoconciliacion

    if (getattr(it, "estado", None) or "").strip() == "en_revision":
        return True
    if reportado_exento_autoconciliacion(
        getattr(it, "monto", None),
        moneda=getattr(it, "moneda", None),
    ):
        return True
    obs = _obs_efectiva_para_validadores(
        (it.observacion or "").strip(),
        getattr(it, "institucion_financiera", "") or "",
        duplicado_mismo_prestamo=getattr(
            it, "prestamo_duplicado_es_objetivo", None
        )
        is True,
    )
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
    True si el reportado NO cumple los mismos validadores que el listado de cola manual (Gemini + reglas de carga).
    Usado al registrar desde formulario público / Infopagos para no mandar a revisión manual lo que ya cumple.
    """
    from app.services.pagos_gmail.parse_campos_comprobante import reportado_exento_autoconciliacion

    if reportado_exento_autoconciliacion(
        getattr(pr, "monto", None),
        moneda=getattr(pr, "moneda", None),
    ):
        return True
    items = _pago_reportado_list_items_from_rows(db, [pr])
    if not items:
        return True
    return _item_falla_validadores_cola_manual(items[0])


def actualizar_flag_falla_validadores(db: Session, pr: PagoReportado, *, commit: bool = False) -> bool:
    """
    Recalcula y persiste ``pr.falla_validadores_manual``.

    Retorna el valor calculado.  No hace commit salvo que ``commit=True``.
    Para estados terminales no ejecuta la evaluación costosa.
    """
    if pr is None:
        return True
    estado = (getattr(pr, "estado", None) or "").strip()
    if estado in ("importado", "rechazado", "eliminado_duplicado"):
        pr.falla_validadores_manual = False
        if commit:
            db.commit()
        return False
    resultado = reportado_falla_validadores_cobros(db, pr)
    pr.falla_validadores_manual = resultado
    if commit:
        db.commit()
    return resultado


_BACKFILL_FLAG_BATCH = 5
_backfill_flag_last_run = 0.0
_BACKFILL_FLAG_COOLDOWN_SEC = 120.0
_BACKFILL_TIME_BUDGET_SEC = 2.0


def _backfill_falla_validadores_lote(db: Session) -> int:
    """
    Recalcula falla_validadores_manual para un lote pequeño de filas con flag NULL o
    potencialmente stale (gemini='true'/'1' en cola que la migracion pudo haber marcado
    false por heuristica).

    Retorna cuantas filas proceso.  Se auto-limita por cooldown + time budget para
    no bloquear requests de listado.
    """
    global _backfill_flag_last_run
    now = time.monotonic()
    if now - _backfill_flag_last_run < _BACKFILL_FLAG_COOLDOWN_SEC:
        return 0
    _backfill_flag_last_run = now

    gem_col = func.lower(func.trim(func.coalesce(PagoReportado.gemini_coincide_exacto, "")))
    ids = list(
        db.execute(
            select(PagoReportado.id).where(
                or_(
                    PagoReportado.falla_validadores_manual.is_(None),
                    and_(
                        PagoReportado.falla_validadores_manual == False,
                        PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado")),
                        gem_col.in_(("true", "1")),
                    ),
                ),
            )
            .order_by(PagoReportado.id.desc())
            .limit(_BACKFILL_FLAG_BATCH)
        ).scalars().all()
    )
    if not ids:
        return 0

    deadline = time.monotonic() + _BACKFILL_TIME_BUDGET_SEC
    updated = 0
    for pid in ids:
        if time.monotonic() > deadline:
            break
        try:
            pr = db.get(PagoReportado, pid)
            if pr is None:
                continue
            actualizar_flag_falla_validadores(db, pr)
            updated += 1
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    if updated:
        try:
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    logger.debug("[COBROS_FLAG] Backfill: %d/%d filas recalculadas.", updated, len(ids))
    return updated


_backfill_pre_listado_last_run = 0.0
_BACKFILL_PRE_LISTADO_COOLDOWN_SEC = 45.0
_BACKFILL_PRE_LISTADO_BATCH = 20
_BACKFILL_PRE_LISTADO_BUDGET_SEC = 2.0


def _backfill_falla_validadores_pre_listado(db: Session) -> int:
    """
    Antes del barrido del listado: rellena `falla_validadores_manual` en más filas
    que el backfill ligero (menos filas con NULL → menos validación Python en el scan).
    """
    global _backfill_pre_listado_last_run
    now = time.monotonic()
    if now - _backfill_pre_listado_last_run < _BACKFILL_PRE_LISTADO_COOLDOWN_SEC:
        return 0
    _backfill_pre_listado_last_run = now

    gem_col = func.lower(func.trim(func.coalesce(PagoReportado.gemini_coincide_exacto, "")))
    ids = list(
        db.execute(
            select(PagoReportado.id).where(
                or_(
                    PagoReportado.falla_validadores_manual.is_(None),
                    and_(
                        PagoReportado.falla_validadores_manual == False,
                        PagoReportado.estado.in_(("pendiente", "en_revision", "aprobado")),
                        gem_col.in_(("true", "1")),
                    ),
                ),
            )
            .order_by(PagoReportado.id.desc())
            .limit(_BACKFILL_PRE_LISTADO_BATCH)
        ).scalars().all()
    )
    if not ids:
        return 0

    deadline = time.monotonic() + _BACKFILL_PRE_LISTADO_BUDGET_SEC
    updated = 0
    for pid in ids:
        if time.monotonic() > deadline:
            break
        try:
            pr = db.get(PagoReportado, pid)
            if pr is None:
                continue
            actualizar_flag_falla_validadores(db, pr)
            updated += 1
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    if updated:
        try:
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    if updated:
        logger.info("[COBROS_FLAG] Pre-listado backfill: %d filas.", updated)
    return updated

