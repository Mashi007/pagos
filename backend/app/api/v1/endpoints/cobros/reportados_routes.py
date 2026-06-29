"""Endpoints HTTP cobros: pagos reportados."""
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
    _COBROS_LISTADO_KPIS_SINGLEFLIGHT_WAIT_SEC,
    _cobros_listado_kpis_cache_get,
    _cobros_listado_kpis_cache_get_stale,
    _cobros_listado_kpis_cache_key_payload,
    _cobros_listado_kpis_cache_set,
    _cobros_listado_kpis_release_singleflight,
    _cobros_listado_kpis_storage_key,
    _cobros_listado_kpis_try_acquire_singleflight,
    _drop_pagos_from_listado_kpis_cache,
    _invalidate_cobros_listado_kpis_cache,
    _log_fase_aprobacion,
)
from .reportados_dedup_helpers import (
    _cedula_lookup_variants,
    _duplicados_reportados_por_numero_operacion,
    _es_banco_mercantil,
    _lock_numero_operacion_canonico,
    _normalize_cedula_for_client_lookup,
    _numero_operacion_canonico,
    _pago_reportado_list_items_from_rows,
    _query_reportados_falla_validadores_pendientes_exportar,
    _referencia_display,
    _rechazar_aprobacion_si_documento_ya_en_pagos,
)
from .reportados_listado_payload import (
    _kpis_pagos_reportados_payload,
    _list_pagos_reportados_payload,
    _persist_marcar_exportados_y_cola,
)
from .reportados_validadores_helpers import (
    _diagnostico_duplicado_reportado,
    _estado_label_estado_reportado,
    _item_falla_validadores_cola_manual,
    actualizar_flag_falla_validadores,
    reportado_falla_validadores_cobros,
)
from .schemas import (
    AprobarRechazarBody,
    CambiarEstadoBody,
    EditarPagoReportadoBody,
    MarcarExportadosBody,
    PagoReportadoDetalle,
    PagoReportadoDuplicadoDiagnostico,
    PagoReportadoHistorialItem,
    PagoReportadoListItem,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

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
        description="Si true, incluye filas ya exportadas en la corrección masiva (siguen gestionables en Cobranzas).",
    ),
):
    """
    Lista paginada de pagos reportados con filtros.

    Sin `estado` o con `pendiente` / `en_revision` / `aprobado`: filas de cola manual.
    `pendiente`: solo las que **no cumplen validadores** automáticos.
    `en_revision`: **todas** las de ese estado (p. ej. escáner Infopagos con confirmación humana).

    `estado=importado` o `rechazado`: listado completo de ese estado (sin filtro de validadores).

    `incluir_exportados=true`: incluye pendiente/en revisión/aprobado ya exportados en la corrección masiva.

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
        description="Alinear conteos con listado cuando se incluyen filas ya exportadas en corrección masiva.",
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
        description="Igual que GET /pagos-reportados: muestra filas ya exportadas en corrección masiva para seguir gestionándolas.",
    ),
    fresh: bool = Query(
        False,
        description="Si true, ignora caché Redis/memoria y recalcula listado+KPIs (usar con «Actualizar ahora» en UI).",
    ),
):
    """
    Listado paginado + KPIs en una sola petición (mismos query params que GET /pagos-reportados).

    KPIs alineados con el listado (con o sin filas ya exportadas en corrección masiva, según incluir_exportados).

    Sin filtro `estado`: un solo barrido de la cola manual alimenta listado + KPIs (mitad de trabajo BD vs antes).
    Con `estado` o pestaña filtrada: listado acotado + KPIs con barrido completo (misma semántica que antes).
    """
    try:
        db.execute(text("SET LOCAL statement_timeout = 240000"))
    except Exception:
        pass

    cache_payload = _cobros_listado_kpis_cache_key_payload(
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=cedula,
        institucion=institucion,
        page=page,
        per_page=per_page,
        incluir_exportados=incluir_exportados,
    )
    skip_cache = bool(
        fresh
        or (cedula and str(cedula).strip())
        or (institucion and str(institucion).strip())
    )
    if not skip_cache:
        cached = _cobros_listado_kpis_cache_get(cache_payload)
        if cached is not None:
            return cached
    else:
        cached = None

    acquired = False if skip_cache else _cobros_listado_kpis_try_acquire_singleflight(cache_payload)
    if not acquired:
        wait_deadline = time.monotonic() + _COBROS_LISTADO_KPIS_SINGLEFLIGHT_WAIT_SEC
        while time.monotonic() < wait_deadline:
            cached_wait = _cobros_listado_kpis_cache_get(cache_payload)
            if cached_wait is not None:
                return cached_wait
            time.sleep(0.1)
        stale_wait = _cobros_listado_kpis_cache_get_stale(cache_payload)
        if stale_wait is not None:
            logger.warning(
                "[COBROS_CACHE] listado-y-kpis devolviendo stale por single-flight en curso (key=%s)",
                _cobros_listado_kpis_storage_key(cache_payload),
            )
            return stale_wait

    try:
        def _compute_payload() -> dict:
            t0 = time.monotonic()
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
            t_lista = time.monotonic()
            manual_queue = (
                lista.pop("_manual_kpi_counts", None) if emit_kpi_from_list else None
            )
            kpis = _kpis_pagos_reportados_payload(
                db,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                cedula=cedula,
                institucion=institucion,
                incluir_exportados=incluir_exportados,
                manual_queue_counts=manual_queue,
            )
            logger.info(
                "[COBROS listado-y-kpis] listado_ms=%.0f kpis_ms=%.0f total_ms=%.0f page=%s per_page=%s",
                (t_lista - t0) * 1000,
                (time.monotonic() - t_lista) * 1000,
                (time.monotonic() - t0) * 1000,
                page,
                per_page,
            )
            return {**lista, "kpis": kpis}

        payload = run_db_with_transient_retry(
            db,
            _compute_payload,
            attempts=3,
            log_prefix="[COBROS listado-y-kpis]",
        )
        if not skip_cache:
            _cobros_listado_kpis_cache_set(cache_payload, payload)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        fallback = _cobros_listado_kpis_cache_get_stale(cache_payload)
        if fallback is not None:
            logger.warning(
                "[COBROS_CACHE] listado-y-kpis devolviendo stale cache por error de cálculo: %s",
                e,
            )
            return fallback
        logger.exception(
            "[COBROS listado-y-kpis] error sin cache stale (key=%s): %s",
            _cobros_listado_kpis_storage_key(cache_payload),
            e,
        )
        msg = str(e).lower()
        if "statement timeout" in msg or "query canceled" in msg or "canceling statement" in msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    "El listado tardó demasiado. Reduzca el rango de fechas o pulse "
                    "«Actualizar» en unos segundos (caché en servidor)."
                ),
            ) from e
        raise HTTPException(
            status_code=503,
            detail="No se pudo calcular el listado de pagos reportados. Intente de nuevo.",
        ) from e
    finally:
        if acquired:
            _cobros_listado_kpis_release_singleflight(cache_payload)


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
    "/pagos-reportados/exportar-aprobados-correccion",
    summary="Exportar filas que fallan validadores (XLSX) y marcarlas como exportadas",
)
@router.get(
    "/pagos-reportados/exportar-aprobados-excel",
    summary="[Compat] Igual que exportar-aprobados-correccion",
    include_in_schema=False,
)
def exportar_pagos_aprobados_correccion(
    db: Session = Depends(get_db),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
):
    """
    Solo filas que no cumplen validadores (Gemini NO/error u observación de reglas), pendiente, en revisión
    o aprobado (legacy), aún no exportadas. Al descargar: se entrega un XLSX y se marcan en pagos_reportados_exportados; entonces dejan
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
    items = [it for it in items if _item_falla_validadores_cola_manual(it)]
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
                _estado_label_estado_reportado(it.estado),
                round(eq_u, 2) if eq_u is not None else None,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    archivo_xlsx_bytes = buf.getvalue()

    ids = [it.id for it in items]
    stats = _persist_marcar_exportados_y_cola(db, ids)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pagos_reportados_falla_validadores_{ts}.xlsx"

    return Response(
        content=archivo_xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(archivo_xlsx_bytes)),
            "X-Export-Marcados": str(stats["marcados"]),
            "X-Export-Ya-Exportados": str(stats["ya_exportados"]),
            "X-Export-Quitados-Cola": str(stats["quitados_cola_temporal"]),
            "X-Export-Total-Filas": str(len(items)),
        },
    )


@router.get(
    "/pagos-reportados/{pago_id}/diagnostico-duplicado",
    response_model=PagoReportadoDuplicadoDiagnostico,
)
def diagnostico_duplicado_pago_reportado(
    pago_id: int,
    numero_operacion: Optional[str] = Query(None),
    tipo_cedula: Optional[str] = Query(None),
    numero_cedula: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Diagnóstico liviano para la pantalla de edición: evalúa el número actualmente
    escrito en el formulario, aunque todavía no se haya guardado.
    """
    pr = db.execute(
        select(PagoReportado).where(PagoReportado.id == pago_id)
    ).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")

    pr_like = SimpleNamespace(
        referencia_interna=getattr(pr, "referencia_interna", None),
        numero_operacion=(numero_operacion or getattr(pr, "numero_operacion", None)),
    )
    return _diagnostico_duplicado_reportado(
        db,
        pr_like,
        tipo_cedula=tipo_cedula or getattr(pr, "tipo_cedula", None),
        numero_cedula=numero_cedula or getattr(pr, "numero_cedula", None),
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
    duplicado_diag = _diagnostico_duplicado_reportado(
        db,
        pr,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
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
        duplicado_en_pagos=duplicado_diag.duplicado_en_pagos,
        pago_existente_id=duplicado_diag.pago_existente_id,
        prestamo_existente_id=duplicado_diag.prestamo_existente_id,
        pago_existente_estado=duplicado_diag.pago_existente_estado,
        pago_existente_fecha_pago=duplicado_diag.pago_existente_fecha_pago,
        prestamo_objetivo_id=duplicado_diag.prestamo_objetivo_id,
        prestamo_objetivo_multiple=duplicado_diag.prestamo_objetivo_multiple,
        prestamo_duplicado_es_objetivo=duplicado_diag.prestamo_duplicado_es_objetivo,
        prestamo_objetivo_motivo=duplicado_diag.prestamo_objetivo_motivo,
        prestamo_referencia_id=duplicado_diag.prestamo_referencia_id,
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
        .values(estado="eliminado_duplicado", motivo_rechazo=motivo, falla_validadores_manual=False)
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
    from app.services.cobros.cobros_publico_reporte_service import (
        error_si_no_puede_reportar_en_web,
        prestamos_aprobados_del_cliente,
    )

    prestamo_ids = prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = error_si_no_puede_reportar_en_web(prestamo_ids)
    if err_pres:
        raise HTTPException(status_code=400, detail=err_pres)
    prestamo = db.get(Prestamo, int(prestamo_ids[0]))
    if not prestamo:
        raise HTTPException(
            status_code=400,
            detail="No se encontró el crédito operativo del cliente.",
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
        fuente = fuente_tasa_bs_efectiva_para_cedula(
            db,
            f"{(pr.tipo_cedula or '').strip().upper()}{(pr.numero_cedula or '').strip()}".replace(
                "-", ""
            ).replace(" ", ""),
            fuente_almacenada=getattr(pr, "fuente_tasa_cambio", None),
        )
        if not fuente:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No hay tasa de cambio configurada para esta cédula en bolívares. "
                    "Verifique Pago Bs. antes de aprobar."
                ),
            )
        tasa_res = valor_tasa_para_fuente(tasa_obj, fuente)
        if tasa_res is None or float(tasa_res) <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No hay tasa {fuente.upper()} registrada para la fecha de pago "
                    f"{pr.fecha_pago.isoformat()}. Registre la tasa en Tasas de cambio antes de aprobar."
                ),
            )
        tasa_aplicada = float(tasa_res)
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
    msg_h = conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_ts.date(),
        monto_pagado=monto,
        numero_documento=num_doc,
        referencia_pago=ref_pago,
    )
    if msg_h:
        raise HTTPException(status_code=409, detail=msg_h[:500])
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
    try:
        db.flush()
    except IntegrityError as e:
        _pgcode, _cname = _integridad_error_pgcode_y_constraint(e)
        logger.warning(
            "[COBROS] Aprobar ref=%s: IntegrityError creando pago (pgcode=%s constraint=%s): %s",
            getattr(pr, "referencia_interna", None),
            _pgcode,
            _cname,
            e,
        )
        cname_l = (_cname or "").lower()
        if "ux_pagos_fingerprint_activos" in cname_l:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Pago duplicado por huella funcional: mismo préstamo, fecha, monto y referencia normalizada "
                    "que un pago ya registrado."
                ),
            ) from e
        raise
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
    # IDs a desalojar del cache listado-y-kpis tras el commit final (parche quirurgico
    # en lugar de invalidacion total: evita el recompute de 20-30s con 1 worker).
    # Capturamos `estado_inicial` para que el parche decremente kpis[estado_anterior]
    # incluso si el item esta en una pagina cacheada distinta de la actual.
    estado_inicial_aprobar = (pr.estado or "").strip()
    pago_ids_para_dropear_cache: Set[int] = {int(pago_id)}
    estados_previos_dropear_cache: Dict[int, str] = {int(pago_id): estado_inicial_aprobar}
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
                db, numero_operacion=getattr(pr, "numero_operacion", "") or "", excluir_id=pr.id
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
        pr.falla_validadores_manual = False
        pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

        try:
            fase_db_t0 = time.perf_counter()
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            # Doble envío del mismo comprobante (segundos): tras aprobar el primero, eliminar hermanos.
            num_key = _numero_operacion_canonico(getattr(pr, "numero_operacion", None))
            if num_key:
                dup_rows = _duplicados_reportados_por_numero_operacion(
                    db,
                    numero_operacion=getattr(pr, "numero_operacion", "") or "",
                    excluir_id=pr.id,
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
                # Hermanos marcados como `eliminado_duplicado` deben salir del cache
                # del listado por defecto junto con el aprobado (parche quirurgico).
                for _hid, _href, _hst in dup_rows:
                    if _hst in ("pendiente", "en_revision", "rechazado"):
                        pago_ids_para_dropear_cache.add(int(_hid))
                        estados_previos_dropear_cache[int(_hid)] = str(_hst)
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
    # Parche quirurgico (no invalidacion total): la aprobacion lleva la fila a un estado
    # que ya no esta en la cola por defecto (aprobado). Tras commit, removerla del cache
    # mantiene el listado-y-kpis caliente para los GET vecinos y la fila desaparece al
    # instante en el frontend del operador. `estados_previos` permite decrementar
    # kpis[pendiente|en_revision] aunque el item este en pagina >1 del cache.
    _drop_pagos_from_listado_kpis_cache(
        pago_ids_para_dropear_cache,
        estados_previos=estados_previos_dropear_cache,
    )
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
    pr.falla_validadores_manual = False
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
    # Parche quirurgico: el rechazo lleva la fila a `rechazado`, fuera de la cola por
    # defecto (pendiente/en_revision). Sacarla del cache evita el recompute completo
    # tras cada rechazo y permite que el frontend la vea desaparecer al instante.
    # `estados_previos` permite decrementar kpis[estado_anterior] aunque la fila viva
    # en una pagina cacheada distinta de la pagina 1 (causa real del bug "Pendiente=N
    # pero al hacer click no hay registros").
    _drop_pagos_from_listado_kpis_cache(
        [pago_id],
        estados_previos={int(pago_id): (estado_anterior or "").strip()}
        if estado_anterior
        else None,
    )
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
    estado_previo = (pr.estado or "").strip()
    db.delete(pr)
    db.commit()
    try:
        _drop_pagos_from_listado_kpis_cache(
            [pago_id],
            estados_previos={int(pago_id): estado_previo} if estado_previo else None,
        )
    except Exception as e:
        logger.warning(
            "[COBROS] parche cache tras eliminar id=%s falló (registro ya borrado en BD): %s",
            pago_id,
            e,
        )
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
    """Devuelve el archivo comprobante (imagen o PDF) desde BD.

    Cache-Control: `private, max-age=86400, immutable`. El binario del comprobante
    es inmutable mientras el reporte exista (no se reemplaza en el flujo actual),
    así que permitir caché por sesión del operador evita re-descargar el archivo
    cuando salta entre filas o reabre el visor. `private` impide que proxies
    compartidos lo cacheen; la petición sigue requiriendo Bearer.
    """
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
        headers={
            "Content-Disposition": f'inline; filename="{nombre}"',
            "Cache-Control": "private, max-age=86400, immutable",
        },
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
    _invalidate_cobros_listado_kpis_cache()
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
    _invalidate_cobros_listado_kpis_cache()
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
    """Misma regla que aprobar: colision con cartera segun banco (Mercantil vs resto)."""
    _rechazar_aprobacion_si_documento_ya_en_pagos(db, pr)


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
            from app.services.pagos_gmail.parse_campos_comprobante import (
                sanitizar_numero_operacion_comprobante,
            )

            limpio = sanitizar_numero_operacion_comprobante(body.numero_operacion)
            pr.numero_operacion = limpio[:100] if limpio else pr.numero_operacion
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
        actualizar_flag_falla_validadores(db, pr)
        db.commit()
        _invalidate_cobros_listado_kpis_cache()
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
                db, numero_operacion=getattr(pr, "numero_operacion", "") or "", excluir_id=pr.id
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
    if body.estado in ("aprobado", "rechazado", "importado"):
        pr.falla_validadores_manual = False
    elif body.estado in ("pendiente", "en_revision"):
        actualizar_flag_falla_validadores(db, pr)
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)

    # IDs a desalojar del cache listado-y-kpis con parche quirurgico (no invalidacion total)
    # cuando el nuevo estado deja al item fuera de la cola por defecto. Capturamos el
    # estado anterior para decrementar kpis[anterior] aunque la fila no este en la
    # pagina cacheada (evita el efecto "Pendiente=17 pero listado vacio al click").
    pago_ids_para_dropear_cache: Set[int] = {int(pago_id)}
    estados_previos_dropear_cache: Dict[int, str] = {
        int(pago_id): (estado_anterior or "").strip()
    }

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
                    db,
                    numero_operacion=getattr(pr, "numero_operacion", "") or "",
                    excluir_id=pr.id,
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
                for _hid, _href, _hst in dup_rows:
                    if _hst in ("pendiente", "en_revision", "rechazado"):
                        pago_ids_para_dropear_cache.add(int(_hid))
                        estados_previos_dropear_cache[int(_hid)] = str(_hst)
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
    # Parche quirurgico cuando el nuevo estado deja el item fuera de la cola por defecto
    # (aprobado / rechazado): el frontend ve la fila desaparecer al instante y el siguiente
    # listado-y-kpis no recompute toda la cola.
    # Si el item vuelve a pendiente/en_revision (raro, p. ej. reabrir tras rechazo), no
    # podemos parchear sin saber donde insertarlo: invalidamos para forzar recalculo fresco.
    if body.estado in ("aprobado", "rechazado"):
        _drop_pagos_from_listado_kpis_cache(
            pago_ids_para_dropear_cache,
            estados_previos=estados_previos_dropear_cache,
        )
    else:
        _invalidate_cobros_listado_kpis_cache()
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
    _invalidate_cobros_listado_kpis_cache()
    
    # Retornar el nuevo resultado
    return {
        "ok": True,
        "pago_id": pago_id,
        "referencia_interna": pr.referencia_interna,
        "gemini_coincide_exacto": pr.gemini_coincide_exacto,
        "gemini_comentario": pr.gemini_comentario,
        "mensaje": "Comprobante re-analizado. Verifica la observación antes de aprobar o rechazar.",
    }

