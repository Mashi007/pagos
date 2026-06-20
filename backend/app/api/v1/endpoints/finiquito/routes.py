"""
Finiquito: casos materializados solo para prestamos LIQUIDADO con cuotas = financiamiento
(jobs lun-sab 01:00 y 13:00 Caracas), bandejas internas, admin.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import Date, cast, func, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import false as sql_false

from app.core.config import settings
from app.core.cobros_public_rate_limit import (
    check_rate_limit_finiquito_registro,
    check_rate_limit_finiquito_verificar_codigo,
    get_client_ip,
)
from app.core.database import get_db
from app.core.deps import (
    get_finiquito_usuario_acceso,
    require_admin,
    require_admin_or_operator,
)
from app.core.security import create_access_token
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.finiquito import (
    FiniquitoAreaTrabajoAuditoria,
    FiniquitoCaso,
    FiniquitoEstadoHistorial,
    FiniquitoLoginCodigo,
    FiniquitoUsuarioAcceso,
)
from app.models.prestamo import Prestamo
from app.core.user_utils import user_is_administrator
from app.schemas.auth import UserResponse
from app.schemas.finiquito import (
    FiniquitoFlujoDiaOut,
    FiniquitoFlujoResumenDiarioResponse,
    FiniquitoAdminResumenEstadoResponse,
    FiniquitoConciliacionPasarATrabajoResponse,
    FiniquitoConciliacionRecrearOcrItem,
    FiniquitoConciliacionRecrearOcrResponse,
    FiniquitoConciliacionVistoIniciarRequest,
    FiniquitoConciliacionVistoIniciarResponse,
    FiniquitoConteoRevisionNuevosResponse,
    FiniquitoCasoListaResponse,
    FiniquitoCasoOut,
    FiniquitoDetalleResponse,
    FiniquitoEliminarCasoResponse,
    FiniquitoLiberarProcesosNormalesResponse,
    FiniquitoPatchEstadoRequest,
    FiniquitoPatchEstadoResponse,
    FiniquitoTerminadoItemOut,
    FiniquitoTerminadosListaResponse,
    FiniquitoTerminadosResumenDiarioResponse,
    FiniquitoTerminadosResumenSemanalResponse,
    FiniquitoTerminadosDiaOut,
    FiniquitoTerminadosSemanaOut,
    FiniquitoRegistroRequest,
    FiniquitoRegistroResponse,
    FiniquitoSolicitarCodigoRequest,
    FiniquitoSolicitarCodigoResponse,
    FiniquitoVerificarCodigoRequest,
    FiniquitoVerificarCodigoResponse,
)
from app.services.finiquito_conciliacion_visto_service import (
    iniciar_visto_reserva,
    map_conciliacion_visto_activa_por_caso,
    purgar_reserva_conciliacion_caso,
    recrear_pagos_y_ocr_lote,
)
from app.services.finiquito_prestamo_gestion_sync import (
    limpiar_estado_gestion_finiquito_prestamos,
    sincronizar_prestamo_estado_gestion_finiquito,
)
from app.utils.dias_laborales_caracas import TZ_CARACAS, fecha_hoy_caracas
from app.services.finiquito_db_schema import (
    finiquito_casos_has_contacto_para_siguientes,
    finiquito_has_area_trabajo_auditoria_table,
)
from app.services.finiquito_otp_metrics import (
    finiquito_otp_bump,
    finiquito_otp_snapshot,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

router = APIRouter()


def _json_safe_revision_subpayload(obj: Any) -> Any:
    """
    Convierte salidas de listar_prestamos / listar_pagos (Pydantic, Decimal, fechas)
    a estructura serializable; evita fallos de jsonable_encoder en revision-datos.
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if hasattr(obj, "dict") and callable(getattr(obj, "dict", None)):
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, list):
        return [_json_safe_revision_subpayload(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe_revision_subpayload(v) for k, v in obj.items()}
    return obj

_ADMIN_CASOS_DEFAULT_LIMIT = 500
_ADMIN_CASOS_MAX_LIMIT = 2000

ESTADOS_VALIDOS = frozenset(
    {
        "REVISION",
        "ACEPTADO",
        "REVISION_CONTABLE",
        "RECHAZADO",
        "EN_PROCESO",
        "TERMINADO",
    }
)
FINIQUITO_PORTAL_PUBLICO_ACTIVO = False


def _require_portal_publico_activo() -> None:
    if not FINIQUITO_PORTAL_PUBLICO_ACTIVO:
        raise HTTPException(
            status_code=404,
            detail="Portal publico de finiquitos no disponible.",
        )


def _cedula_portal_token_normalizada(fu: FiniquitoUsuarioAcceso) -> str:
    """Cedula canonica del colaborador portal (mayusculas, trim). Vacio si no aplica."""
    return (normalizar_cedula_almacenamiento(fu.cedula) or "").strip()


def _query_casos_solo_cedula_portal(q: Any, fu: FiniquitoUsuarioAcceso) -> Any:
    """Restringe un query de FiniquitoCaso al documento del usuario portal."""
    ced = _cedula_portal_token_normalizada(fu)
    if not ced:
        return q.filter(sql_false())
    col_doc = func.upper(func.trim(FiniquitoCaso.cedula))
    return q.filter(col_doc == ced)


def _caso_pertenece_a_portal(fu: FiniquitoUsuarioAcceso, caso: FiniquitoCaso) -> bool:
    u = _cedula_portal_token_normalizada(fu)
    if not u:
        return False
    c = (normalizar_cedula_almacenamiento(caso.cedula) or "").strip()
    return c == u


def _ultima_fecha_pago_date_prestamo(db: Session, prestamo_id: int) -> Optional[date]:
    """Fecha calendario de MAX(pagos.fecha_pago) para el prestamo, o None."""
    mx = (
        db.query(func.max(Pago.fecha_pago))
        .filter(Pago.prestamo_id == int(prestamo_id))
        .scalar()
    )
    if mx is None:
        return None
    if hasattr(mx, "date"):
        return mx.date()
    if isinstance(mx, date):
        return mx
    return None


def _map_ultima_fecha_pago_por_prestamo(db: Session, prestamo_ids: List[int]) -> dict[int, Any]:
    """MAX(fecha_pago) en pagos agrupado por prestamo_id."""
    seen: set[int] = set()
    uniq: List[int] = []
    for i in prestamo_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(Pago.prestamo_id, func.max(Pago.fecha_pago).label("mx"))
        .filter(Pago.prestamo_id.in_(uniq))
        .group_by(Pago.prestamo_id)
        .all()
    )
    out: dict[int, Any] = {}
    for r in rows:
        if r.prestamo_id is not None and r.mx is not None:
            out[int(r.prestamo_id)] = r.mx
    return out


def _map_clientes_por_id(db: Session, cliente_ids: List[int]) -> dict[int, Cliente]:
    seen: set[int] = set()
    uniq: List[int] = []
    for i in cliente_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = db.query(Cliente).filter(Cliente.id.in_(uniq)).all()
    return {int(cl.id): cl for cl in rows}


def _map_finiquito_tramite_fecha_limite_por_prestamo(
    db: Session, prestamo_ids: List[int]
) -> dict[int, Any]:
    """finiquito_tramite_fecha_limite en prestamos por prestamo_id."""
    seen: set[int] = set()
    uniq: List[int] = []
    for i in prestamo_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(Prestamo.id, Prestamo.finiquito_tramite_fecha_limite)
        .filter(Prestamo.id.in_(uniq))
        .all()
    )
    return {int(r[0]): r[1] for r in rows}


def _map_fecha_estado_historial_por_caso(
    db: Session, caso_ids: List[int], estado_nuevo: str
) -> Dict[int, Any]:
    """MAX(creado_en) en historial para un estado_nuevo dado, por caso_id."""
    target = (estado_nuevo or "").strip().upper()
    if not target:
        return {}
    seen: set[int] = set()
    uniq: List[int] = []
    for i in caso_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(
            FiniquitoEstadoHistorial.caso_id,
            func.max(FiniquitoEstadoHistorial.creado_en).label("mx"),
        )
        .filter(
            FiniquitoEstadoHistorial.caso_id.in_(uniq),
            FiniquitoEstadoHistorial.estado_nuevo == target,
        )
        .group_by(FiniquitoEstadoHistorial.caso_id)
        .all()
    )
    return {int(r.caso_id): r.mx for r in rows if r.mx is not None}


def _map_fecha_terminado_por_caso(db: Session, caso_ids: List[int]) -> Dict[int, Any]:
    """Fecha calendario Caracas del cierre TERMINADO (historial > auditoria > actualizado_en)."""
    return _map_fecha_cierre_terminado_por_caso(db, caso_ids)


def _map_fecha_auditoria_terminado_por_caso(
    db: Session, caso_ids: List[int]
) -> Dict[int, Any]:
    """MAX(creado_en) en auditoria area trabajo con accion TERMINADO."""
    seen: set[int] = set()
    uniq: List[int] = []
    for i in caso_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(
            FiniquitoAreaTrabajoAuditoria.caso_id,
            func.max(FiniquitoAreaTrabajoAuditoria.creado_en).label("mx"),
        )
        .filter(
            FiniquitoAreaTrabajoAuditoria.caso_id.in_(uniq),
            FiniquitoAreaTrabajoAuditoria.accion == "TERMINADO",
        )
        .group_by(FiniquitoAreaTrabajoAuditoria.caso_id)
        .all()
    )
    return {int(r.caso_id): r.mx for r in rows if r.mx is not None}


def _map_fecha_cierre_terminado_por_caso(
    db: Session, caso_ids: List[int]
) -> Dict[int, Any]:
    """
    Fecha de cierre TERMINADO por caso_id.
    Prioridad: historial estado TERMINADO, auditoria area trabajo, actualizado_en del caso.
    """
    seen: set[int] = set()
    uniq: List[int] = []
    for i in caso_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}

    out: Dict[int, Any] = dict(
        _map_fecha_estado_historial_por_caso(db, uniq, "TERMINADO")
    )
    missing = [cid for cid in uniq if cid not in out]
    if missing and finiquito_has_area_trabajo_auditoria_table(db):
        for cid, raw in _map_fecha_auditoria_terminado_por_caso(db, missing).items():
            out[int(cid)] = raw
        missing = [cid for cid in missing if cid not in out]
    if missing:
        rows = (
            db.query(FiniquitoCaso.id, FiniquitoCaso.actualizado_en)
            .filter(
                FiniquitoCaso.id.in_(missing),
                FiniquitoCaso.estado == "TERMINADO",
            )
            .all()
        )
        for cid, upd in rows:
            if upd is not None:
                out[int(cid)] = upd
    return out


def _map_fecha_auditoria_en_proceso_por_caso(
    db: Session, caso_ids: List[int]
) -> Dict[int, Any]:
    """MAX(creado_en) en auditoria area trabajo con accion EN_PROCESO."""
    seen: set[int] = set()
    uniq: List[int] = []
    for i in caso_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(
            FiniquitoAreaTrabajoAuditoria.caso_id,
            func.max(FiniquitoAreaTrabajoAuditoria.creado_en).label("mx"),
        )
        .filter(
            FiniquitoAreaTrabajoAuditoria.caso_id.in_(uniq),
            FiniquitoAreaTrabajoAuditoria.accion == "EN_PROCESO",
        )
        .group_by(FiniquitoAreaTrabajoAuditoria.caso_id)
        .all()
    )
    return {int(r.caso_id): r.mx for r in rows if r.mx is not None}


def _map_fecha_entrada_area_trabajo_por_caso(
    db: Session, caso_ids: List[int]
) -> Dict[int, Any]:
    """
    Ultima entrada a EN_PROCESO por caso_id.
    Prioridad: historial, auditoria area trabajo, actualizado_en (solo EN_PROCESO).
    """
    seen: set[int] = set()
    uniq: List[int] = []
    for i in caso_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}

    out: Dict[int, Any] = dict(
        _map_fecha_estado_historial_por_caso(db, uniq, "EN_PROCESO")
    )
    missing = [cid for cid in uniq if cid not in out]
    if missing and finiquito_has_area_trabajo_auditoria_table(db):
        for cid, raw in _map_fecha_auditoria_en_proceso_por_caso(db, missing).items():
            out[int(cid)] = raw
        missing = [cid for cid in missing if cid not in out]
    if missing:
        rows = (
            db.query(FiniquitoCaso.id, FiniquitoCaso.actualizado_en)
            .filter(
                FiniquitoCaso.id.in_(missing),
                FiniquitoCaso.estado == "EN_PROCESO",
            )
            .all()
        )
        for cid, upd in rows:
            if upd is not None:
                out[int(cid)] = upd
    return out


def _expr_fecha_caracas_desde_utc_naive(column: Any) -> Any:
    """
    ((col AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date
    Misma regla que consultas DBeaver sobre creado_en naive UTC.
    """
    en_utc = column.op("AT TIME ZONE")(literal("UTC"))
    en_caracas = en_utc.op("AT TIME ZONE")(literal("America/Caracas"))
    return cast(en_caracas, Date)


def _coerce_a_fecha_caracas(raw: Any) -> date | None:
    """Normaliza date/datetime naive UTC a fecha calendario Caracas."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return _fecha_historial_a_date_caracas(raw)
    if isinstance(raw, date):
        return raw
    return _fecha_historial_a_date_caracas(raw)


def _registrar_conteo_dia_caso(
    ctr: Counter[str],
    vistos: set[tuple[str, int]],
    caso_id: int,
    raw: Any,
    *,
    inicio: date,
    hoy: date,
) -> None:
    d = _coerce_a_fecha_caracas(raw)
    if d is None or d < inicio or d > hoy:
        return
    key = d.isoformat()
    par = (key, int(caso_id))
    if par in vistos:
        return
    vistos.add(par)
    ctr[key] += 1


def _conteo_ingresos_area_trabajo_por_dia_caracas(
    db: Session,
    *,
    inicio: date,
    hoy: date,
    ced_filtro: Optional[str],
) -> Counter[str]:
    """
    Entradas al area de trabajo por dia calendario Caracas.
    Cuenta transiciones a EN_PROCESO (historial y auditoria) y completa casos
    EN_PROCESO/TERMINADO sin evento registrado.
    """
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    fec_hist = _expr_fecha_caracas_desde_utc_naive(FiniquitoEstadoHistorial.creado_en)

    def registrar(caso_id: int, raw: Any) -> None:
        _registrar_conteo_dia_caso(
            ctr, vistos, caso_id, raw, inicio=inicio, hoy=hoy
        )

    q_hist = db.query(
        fec_hist.label("dia"),
        FiniquitoEstadoHistorial.caso_id,
    ).filter(
        FiniquitoEstadoHistorial.estado_nuevo == "EN_PROCESO",
        fec_hist >= inicio,
        fec_hist <= hoy,
    )
    if ced_filtro:
        q_hist = q_hist.join(
            FiniquitoCaso, FiniquitoCaso.id == FiniquitoEstadoHistorial.caso_id
        ).filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    for dia, caso_id in q_hist.all():
        registrar(int(caso_id), dia)

    if finiquito_has_area_trabajo_auditoria_table(db):
        fec_aud = _expr_fecha_caracas_desde_utc_naive(
            FiniquitoAreaTrabajoAuditoria.creado_en
        )
        q_aud = db.query(
            fec_aud.label("dia"),
            FiniquitoAreaTrabajoAuditoria.caso_id,
        ).filter(
            FiniquitoAreaTrabajoAuditoria.accion == "EN_PROCESO",
            fec_aud >= inicio,
            fec_aud <= hoy,
        )
        if ced_filtro:
            q_aud = q_aud.join(
                FiniquitoCaso,
                FiniquitoCaso.id == FiniquitoAreaTrabajoAuditoria.caso_id,
            ).filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
        for dia, caso_id in q_aud.all():
            registrar(int(caso_id), dia)

    q_casos = db.query(FiniquitoCaso).filter(
        FiniquitoCaso.estado.in_(("EN_PROCESO", "TERMINADO"))
    )
    if ced_filtro:
        q_casos = q_casos.filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    casos = q_casos.all()
    if casos:
        fentrada = _map_fecha_entrada_area_trabajo_por_caso(db, [c.id for c in casos])
        for c in casos:
            cid = int(c.id)
            raw = fentrada.get(cid)
            if raw is None and c.estado == "EN_PROCESO":
                raw = c.actualizado_en
            if raw is not None:
                registrar(cid, raw)

    return ctr


def _conteo_ingresados_bandeja_por_dia_caracas(
    db: Session,
    *,
    inicio: date,
    hoy: date,
    ced_filtro: Optional[str],
) -> Counter[str]:
    """Casos creados en finiquito (bandeja principal) por día calendario Caracas."""
    ctr: Counter[str] = Counter()
    fec_caso = _expr_fecha_caracas_desde_utc_naive(FiniquitoCaso.creado_en)
    q = db.query(fec_caso.label("dia"), func.count(FiniquitoCaso.id)).filter(
        fec_caso >= inicio,
        fec_caso <= hoy,
    )
    if ced_filtro:
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    q = q.group_by(fec_caso)
    for dia, cantidad in q.all():
        if dia is None:
            continue
        ctr[str(dia)] = int(cantidad or 0)
    return ctr


def _conteo_ingresos_area_revision_por_dia_caracas(
    db: Session,
    *,
    inicio: date,
    hoy: date,
    ced_filtro: Optional[str],
) -> Counter[str]:
    """
    Entradas al área de revisión por día calendario Caracas.
    Cuenta transiciones a ACEPTADO y completa casos ya avanzados sin historial legado.
    """
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    fec_hist = _expr_fecha_caracas_desde_utc_naive(FiniquitoEstadoHistorial.creado_en)

    def registrar(caso_id: int, raw: Any) -> None:
        _registrar_conteo_dia_caso(
            ctr, vistos, caso_id, raw, inicio=inicio, hoy=hoy
        )

    q_hist = db.query(
        fec_hist.label("dia"),
        FiniquitoEstadoHistorial.caso_id,
    ).filter(
        FiniquitoEstadoHistorial.estado_nuevo == "ACEPTADO",
        fec_hist >= inicio,
        fec_hist <= hoy,
    )
    if ced_filtro:
        q_hist = q_hist.join(
            FiniquitoCaso, FiniquitoCaso.id == FiniquitoEstadoHistorial.caso_id
        ).filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    for dia, caso_id in q_hist.all():
        registrar(int(caso_id), dia)

    q_casos = db.query(FiniquitoCaso).filter(
        FiniquitoCaso.estado.in_(
            ("ACEPTADO", "REVISION_CONTABLE", "EN_PROCESO", "TERMINADO")
        )
    )
    if ced_filtro:
        q_casos = q_casos.filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    casos = q_casos.all()
    if casos:
        fentrada = _map_fecha_estado_historial_por_caso(
            db, [c.id for c in casos], "ACEPTADO"
        )
        for c in casos:
            cid = int(c.id)
            raw = fentrada.get(cid)
            if raw is None and c.estado == "ACEPTADO":
                raw = c.actualizado_en
            if raw is not None:
                registrar(cid, raw)

    return ctr


def _conteo_terminados_por_dia_caracas(
    db: Session,
    *,
    inicio: date,
    hoy: date,
    ced_filtro: Optional[str],
) -> Counter[str]:
    """
    Casos terminados por dia calendario Caracas.
    Cuenta eventos TERMINADO en historial y completa casos TERMINADO sin fecha en historial.
    """
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    fec_hist = _expr_fecha_caracas_desde_utc_naive(FiniquitoEstadoHistorial.creado_en)

    def registrar(caso_id: int, raw: Any) -> None:
        _registrar_conteo_dia_caso(
            ctr, vistos, caso_id, raw, inicio=inicio, hoy=hoy
        )

    q_hist = db.query(
        fec_hist.label("dia"),
        FiniquitoEstadoHistorial.caso_id,
    ).filter(
        FiniquitoEstadoHistorial.estado_nuevo == "TERMINADO",
        fec_hist >= inicio,
        fec_hist <= hoy,
    )
    if ced_filtro:
        q_hist = q_hist.join(
            FiniquitoCaso, FiniquitoCaso.id == FiniquitoEstadoHistorial.caso_id
        ).filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    for dia, caso_id in q_hist.all():
        registrar(int(caso_id), dia)

    if finiquito_has_area_trabajo_auditoria_table(db):
        fec_aud = _expr_fecha_caracas_desde_utc_naive(
            FiniquitoAreaTrabajoAuditoria.creado_en
        )
        q_aud = db.query(
            fec_aud.label("dia"),
            FiniquitoAreaTrabajoAuditoria.caso_id,
        ).filter(
            FiniquitoAreaTrabajoAuditoria.accion == "TERMINADO",
            fec_aud >= inicio,
            fec_aud <= hoy,
        )
        if ced_filtro:
            q_aud = q_aud.join(
                FiniquitoCaso,
                FiniquitoCaso.id == FiniquitoAreaTrabajoAuditoria.caso_id,
            ).filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
        for dia, caso_id in q_aud.all():
            registrar(int(caso_id), dia)

    q_casos = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "TERMINADO")
    if ced_filtro:
        q_casos = q_casos.filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    casos = q_casos.all()
    if casos:
        fcierre = _map_fecha_cierre_terminado_por_caso(db, [c.id for c in casos])
        for c in casos:
            cid = int(c.id)
            raw = fcierre.get(cid)
            if raw is None:
                raw = c.actualizado_en
            registrar(cid, raw)

    return ctr


def _map_prestamo_nombre_fecha_aprobacion(
    db: Session, prestamo_ids: List[int]
) -> Dict[int, Tuple[Optional[str], Optional[Any]]]:
    seen: set[int] = set()
    uniq: List[int] = []
    for i in prestamo_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(Prestamo.id, Prestamo.nombres, Prestamo.fecha_aprobacion)
        .filter(Prestamo.id.in_(uniq))
        .all()
    )
    return {int(r[0]): (r[1], r[2]) for r in rows}


def _semana_iso_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _etiqueta_semana_iso(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"Sem {w} · {y}"


def _fecha_historial_a_date_caracas(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ_CARACAS).date()
    if isinstance(raw, date):
        return raw
    return None


def _etiqueta_dia_terminado(d: date, hoy: date) -> str:
    if d == hoy:
        return "Hoy"
    if d == hoy - timedelta(days=1):
        return "Ayer"
    return d.strftime("%d/%m")


def _terminados_items_from_casos(
    db: Session, casos: List[FiniquitoCaso]
) -> List[FiniquitoTerminadoItemOut]:
    if not casos:
        return []
    caso_ids = [c.id for c in casos]
    prestamo_ids = [c.prestamo_id for c in casos]
    cliente_ids = [c.cliente_id for c in casos if c.cliente_id]
    mp = _map_ultima_fecha_pago_por_prestamo(db, prestamo_ids)
    ft = _map_fecha_terminado_por_caso(db, caso_ids)
    pr = _map_prestamo_nombre_fecha_aprobacion(db, prestamo_ids)
    clmap = _map_clientes_por_id(db, cliente_ids)
    has_contacto_col = finiquito_casos_has_contacto_para_siguientes(db)
    items: List[FiniquitoTerminadoItemOut] = []
    for c in casos:
        nombre = ""
        cl = clmap.get(int(c.cliente_id)) if c.cliente_id else None
        if cl and (cl.nombres or "").strip():
            nombre = (cl.nombres or "").strip()
        pr_row = pr.get(int(c.prestamo_id))
        if not nombre and pr_row and pr_row[0]:
            nombre = str(pr_row[0]).strip()
        fa = _dt_iso(pr_row[1]) if pr_row else None
        ufp_raw = mp.get(c.prestamo_id)
        ufp = _dt_iso(ufp_raw) if ufp_raw is not None else None
        if ufp and "T" in ufp:
            ufp = ufp.split("T", 1)[0]
        ft_raw = ft.get(c.id)
        fterm = _dt_iso(ft_raw) if ft_raw is not None else None
        cps: Optional[bool] = None
        if has_contacto_col:
            try:
                cps = c.contacto_para_siguientes
            except Exception:
                cps = None
        items.append(
            FiniquitoTerminadoItemOut(
                id=c.id,
                prestamo_id=c.prestamo_id,
                cedula=c.cedula or "",
                nombre=nombre,
                total_financiamiento=str(c.total_financiamiento),
                fecha_aprobacion=fa,
                fecha_termino_pago=ufp,
                fecha_terminado=fterm,
                contacto_para_siguientes=cps,
            )
        )
    return items


def _map_fecha_liquidado_por_prestamo(db: Session, prestamo_ids: List[int]) -> dict[int, Any]:
    seen: set[int] = set()
    uniq: List[int] = []
    for i in prestamo_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(Prestamo.id, Prestamo.fecha_liquidado)
        .filter(Prestamo.id.in_(uniq))
        .all()
    )
    return {int(r[0]): r[1] for r in rows}


def _admin_casos_to_items(db: Session, casos: List[FiniquitoCaso]) -> List[FiniquitoCasoOut]:
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(
        db, [c.prestamo_id for c in casos]
    )
    fmap = _map_fecha_liquidado_por_prestamo(db, [c.prestamo_id for c in casos])
    fepmap = _map_fecha_estado_historial_por_caso(
        db, [c.id for c in casos], "EN_PROCESO"
    )
    famap = _map_fecha_estado_historial_por_caso(
        db, [c.id for c in casos], "ACEPTADO"
    )
    frcmap = _map_fecha_estado_historial_por_caso(
        db, [c.id for c in casos], "REVISION_CONTABLE"
    )
    clmap = _map_clientes_por_id(db, [c.cliente_id for c in casos if c.cliente_id])
    visto_map = map_conciliacion_visto_activa_por_caso(db, [c.id for c in casos])
    items: List[FiniquitoCasoOut] = []
    for c in casos:
        base = _caso_to_out(
            c,
            mp.get(c.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(c.prestamo_id),
            fecha_liquidado=fmap.get(c.prestamo_id),
            fecha_entrada_en_proceso=fepmap.get(c.id),
            fecha_entrada_aceptado=famap.get(c.id),
            fecha_entrada_revision_contable=frcmap.get(c.id),
            conciliacion_visto_activa=visto_map.get(c.id, False),
        )
        cl = clmap.get(int(c.cliente_id)) if c.cliente_id else None
        items.append(
            base.model_copy(
                update={
                    "cliente_nombres": cl.nombres if cl else None,
                    "cliente_email": cl.email if cl else None,
                    "cliente_telefono": cl.telefono if cl else None,
                }
            )
        )
    return items


def _caso_to_out(
    c: FiniquitoCaso,
    ultima_fecha_pago: Optional[Any] = None,
    db: Optional[Session] = None,
    *,
    finiquito_tramite_fecha_limite: Optional[Any] = None,
    fecha_liquidado: Optional[Any] = None,
    fecha_entrada_en_proceso: Optional[Any] = None,
    fecha_entrada_aceptado: Optional[Any] = None,
    fecha_entrada_revision_contable: Optional[Any] = None,
    conciliacion_visto_activa: Optional[bool] = None,
) -> FiniquitoCasoOut:
    ufp: Optional[str] = None
    if ultima_fecha_pago is not None:
        ufp = (
            ultima_fecha_pago.isoformat()
            if hasattr(ultima_fecha_pago, "isoformat")
            else str(ultima_fecha_pago)
        )
    ftl: Optional[str] = None
    if finiquito_tramite_fecha_limite is not None:
        v = finiquito_tramite_fecha_limite
        ftl = v.isoformat() if hasattr(v, "isoformat") else str(v)
    flq: Optional[str] = None
    if fecha_liquidado is not None:
        v = fecha_liquidado
        flq = v.isoformat() if hasattr(v, "isoformat") else str(v)
    fep: Optional[str] = None
    if fecha_entrada_en_proceso is not None:
        v = fecha_entrada_en_proceso
        fep = v.isoformat() if hasattr(v, "isoformat") else str(v)
    fea: Optional[str] = None
    if fecha_entrada_aceptado is not None:
        v = fecha_entrada_aceptado
        fea = v.isoformat() if hasattr(v, "isoformat") else str(v)
    ferc: Optional[str] = None
    if fecha_entrada_revision_contable is not None:
        v = fecha_entrada_revision_contable
        ferc = v.isoformat() if hasattr(v, "isoformat") else str(v)
    creado_iso: Optional[str] = None
    if c.creado_en is not None:
        creado_iso = (
            c.creado_en.isoformat()
            if hasattr(c.creado_en, "isoformat")
            else str(c.creado_en)
        )
    cps: Optional[bool] = None
    if db is not None and finiquito_casos_has_contacto_para_siguientes(db):
        try:
            cps = c.contacto_para_siguientes
        except Exception:
            cps = None
    return FiniquitoCasoOut(
        id=c.id,
        prestamo_id=c.prestamo_id,
        cliente_id=c.cliente_id,
        cedula=c.cedula or "",
        total_financiamiento=str(c.total_financiamiento),
        sum_total_pagado=str(c.sum_total_pagado),
        estado=c.estado,
        ultimo_refresh_utc=c.ultimo_refresh_utc.isoformat() if c.ultimo_refresh_utc else None,
        ultima_fecha_pago=ufp,
        contacto_para_siguientes=cps,
        finiquito_tramite_fecha_limite=ftl,
        fecha_liquidado=flq,
        creado_en=creado_iso,
        fecha_entrada_en_proceso=fep,
        fecha_entrada_aceptado=fea,
        fecha_entrada_revision_contable=ferc,
        conciliacion_visto_activa=conciliacion_visto_activa,
    )


def _utc_naive_now() -> datetime:
    """Timestamp naive UTC alineado con Postgres now() en Render."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _registrar_historial(
    db: Session,
    *,
    caso: FiniquitoCaso,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    actor_tipo: str,
    user_id: Optional[int] = None,
    finiquito_usuario_id: Optional[int] = None,
    nota: Optional[str] = None,
) -> None:
    nota_val = (nota or "").strip() or None
    db.add(
        FiniquitoEstadoHistorial(
            caso_id=caso.id,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            user_id=user_id,
            finiquito_usuario_id=finiquito_usuario_id,
            actor_tipo=actor_tipo,
            nota=nota_val,
            creado_en=_utc_naive_now(),
        )
    )


def _registrar_auditoria_area_trabajo(
    db: Session,
    *,
    caso_id: int,
    accion: str,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    contacto_para_siguientes: Optional[bool],
    user_id: Optional[int],
) -> None:
    db.add(
        FiniquitoAreaTrabajoAuditoria(
            caso_id=caso_id,
            accion=accion,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            contacto_para_siguientes=contacto_para_siguientes,
            user_id=user_id,
            creado_en=_utc_naive_now(),
        )
    )


def _num_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return str(v)


def _dt_iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v)


def _prestamo_caso_completo(p: Prestamo) -> dict[str, Any]:
    """Campos ampliados del préstamo vinculado al caso (lectura finiquito)."""
    return {
        "id": p.id,
        "cliente_id": p.cliente_id,
        "cedula": p.cedula,
        "nombres": p.nombres,
        "total_financiamiento": _num_str(p.total_financiamiento),
        "fecha_requerimiento": _dt_iso(p.fecha_requerimiento),
        "modalidad_pago": p.modalidad_pago,
        "numero_cuotas": p.numero_cuotas,
        "cuota_periodo": _num_str(p.cuota_periodo),
        "tasa_interes": _num_str(p.tasa_interes),
        "fecha_base_calculo": _dt_iso(p.fecha_base_calculo),
        "producto": p.producto,
        "estado": p.estado,
        "fecha_liquidado": _dt_iso(p.fecha_liquidado),
        "usuario_proponente": p.usuario_proponente,
        "usuario_aprobador": p.usuario_aprobador,
        "observaciones": p.observaciones,
        "fecha_registro": _dt_iso(p.fecha_registro),
        "fecha_aprobacion": _dt_iso(p.fecha_aprobacion),
        "fecha_actualizacion": _dt_iso(p.fecha_actualizacion),
        "concesionario": p.concesionario,
        "analista": p.analista,
        "modelo_vehiculo": p.modelo_vehiculo,
        "usuario_autoriza": p.usuario_autoriza,
        "valor_activo": _num_str(p.valor_activo),
        "requiere_revision": bool(p.requiere_revision)
        if p.requiere_revision is not None
        else False,
        "concesionario_id": p.concesionario_id,
        "analista_id": p.analista_id,
        "modelo_vehiculo_id": p.modelo_vehiculo_id,
        "estado_gestion_finiquito": getattr(p, "estado_gestion_finiquito", None),
        "finiquito_tramite_fecha_limite": _dt_iso(
            getattr(p, "finiquito_tramite_fecha_limite", None)
        ),
    }


def _cuota_to_dict(cu: Cuota) -> dict[str, Any]:
    return {
        "id": cu.id,
        "prestamo_id": cu.prestamo_id,
        "numero_cuota": cu.numero_cuota,
        "fecha_vencimiento": _dt_iso(cu.fecha_vencimiento),
        "fecha_pago": _dt_iso(cu.fecha_pago),
        "monto_cuota": _num_str(cu.monto),
        "saldo_capital_inicial": _num_str(cu.saldo_capital_inicial),
        "saldo_capital_final": _num_str(cu.saldo_capital_final),
        "monto_capital": _num_str(cu.monto_capital),
        "monto_interes": _num_str(cu.monto_interes),
        "total_pagado": _num_str(cu.total_pagado),
        "dias_mora": cu.dias_mora,
        "dias_morosidad": cu.dias_morosidad,
        "estado": cu.estado,
        "observaciones": cu.observaciones,
        "pago_id": cu.pago_id,
        "es_cuota_especial": cu.es_cuota_especial,
        "cliente_id": cu.cliente_id,
    }


def _user_interno_revision_datos() -> UserResponse:
    """Usuario sintético para listar_prestamos en contexto interno (sin sesión HTTP)."""
    return UserResponse(
        id=0,
        email="finiquito-interno@system",
        nombre="Finiquito",
        apellido="",
        rol="admin",
        is_active=True,
        created_at="1970-01-01T00:00:00",
    )


def _build_revision_datos_payload(
    db: Session,
    caso: FiniquitoCaso,
    *,
    current_user: Optional[UserResponse] = None,
) -> dict[str, Any]:
    """
    Datos de revisión: préstamo del caso (completo), plan de cuotas, listados
    /prestamos y /pagos por cédula; pagos sin filtrar por conciliado (tope API 100).
    """
    from app.api.v1.endpoints.pagos import listar_pagos
    from app.api.v1.endpoints.prestamos import listar_prestamos

    cedula = (caso.cedula or "").strip()
    panel_user = (
        current_user
        if isinstance(current_user, UserResponse)
        else _user_interno_revision_datos()
    )
    try:
        # Pasar valores reales (None/str), no omitir parametros: sus defaults son
        # objetos Query(...) y listar_* hacen .strip() → AttributeError → 500.
        # listar_prestamos exige UserResponse (filtro DESISTIMIENTO); no omitir current_user.
        prestamos_payload = listar_prestamos(
            page=1,
            per_page=100,
            cliente_id=None,
            estado=None,
            analista=None,
            concesionario=None,
            cedula=cedula,
            fecha_inicio=None,
            fecha_fin=None,
            requiere_revision=None,
            modelo=None,
            search=None,
            revision_manual_estado=None,
            current_user=panel_user,
            db=db,
        )
        pagos_payload = listar_pagos(
            page=1,
            per_page=100,
            cedula=cedula,
            estado=None,
            fecha_desde=None,
            fecha_hasta=None,
            analista=None,
            conciliado=None,
            sin_prestamo=None,
            prestamo_cartera="todos",
            db=db,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "finiquito revision-datos: fallo listar_prestamos/pagos cedula=%s caso_id=%s",
            cedula,
            caso.id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar listados por cedula: {type(e).__name__}: {e}",
        ) from e

    prestamos_payload = _json_safe_revision_subpayload(prestamos_payload)
    pagos_payload = _json_safe_revision_subpayload(pagos_payload)

    prestamo_caso: Optional[dict[str, Any]] = None
    cuotas_caso: List[dict[str, Any]] = []
    p = db.query(Prestamo).filter(Prestamo.id == caso.prestamo_id).first()
    if p:
        prestamo_caso = _prestamo_caso_completo(p)
        cuotas = (
            db.query(Cuota)
            .filter(Cuota.prestamo_id == caso.prestamo_id)
            .order_by(Cuota.numero_cuota.asc())
            .all()
        )
        cuotas_caso = [_cuota_to_dict(cu) for cu in cuotas]

    return {
        "caso_id": caso.id,
        "prestamo_id_finiquito": caso.prestamo_id,
        "cedula": cedula,
        "prestamo_caso": prestamo_caso,
        "cuotas_caso": cuotas_caso,
        "prestamos": prestamos_payload,
        "pagos": pagos_payload,
    }


@router.post("/public/registro", response_model=FiniquitoRegistroResponse)
def finiquito_public_registro(
    request: Request,
    body: FiniquitoRegistroRequest,
    db: Session = Depends(get_db),
):
    """Primera vez: cedula + email unicos en el modulo Finiquito."""
    _require_portal_publico_activo()
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    if not cedula or not email:
        raise HTTPException(status_code=400, detail="Cedula y correo son obligatorios.")

    por_cedula = db.query(FiniquitoUsuarioAcceso).filter(FiniquitoUsuarioAcceso.cedula == cedula).first()
    por_email = db.query(FiniquitoUsuarioAcceso).filter(FiniquitoUsuarioAcceso.email == email).first()

    if por_cedula and por_cedula.email != email:
        raise HTTPException(
            status_code=409,
            detail="Esta cedula ya esta registrada con otro correo.",
        )
    if por_email and por_email.cedula != cedula:
        raise HTTPException(
            status_code=409,
            detail="Este correo ya esta registrado con otra cedula.",
        )
    if por_cedula:
        return FiniquitoRegistroResponse(ok=True, message="Ya estaba registrado. Solicite codigo para ingresar.")

    ip = get_client_ip(request)
    try:
        check_rate_limit_finiquito_registro(ip)
    except HTTPException as e:
        if e.status_code == 429:
            finiquito_otp_bump("registro_rate_limit_429")
        raise

    db.add(FiniquitoUsuarioAcceso(cedula=cedula, email=email, is_active=True))
    db.commit()
    return FiniquitoRegistroResponse(ok=True, message="Registro exitoso. Solicite codigo para ingresar.")


@router.post("/public/solicitar-codigo", response_model=FiniquitoSolicitarCodigoResponse)
def finiquito_public_solicitar_codigo(
    request: Request,
    body: FiniquitoSolicitarCodigoRequest,
    db: Session = Depends(get_db),
):
    """Portal publico deshabilitado: no genera codigos ni envia correos."""
    _require_portal_publico_activo()
    return FiniquitoSolicitarCodigoResponse(
        ok=False,
        message="El acceso publico de finiquitos esta deshabilitado.",
    )


@router.get("/admin/otp-email-metricas")
def finiquito_admin_otp_email_metricas(
    _: UserResponse = Depends(require_admin),
):
    """
    Contadores en memoria desde el arranque del proceso (OTP y límites Finiquito).
    Se reinician al reiniciar el servidor; con varios workers cada uno tiene su propio contador.
    """
    return finiquito_otp_snapshot()


@router.post("/public/verificar-codigo", response_model=FiniquitoVerificarCodigoResponse)
def finiquito_public_verificar_codigo(
    request: Request,
    body: FiniquitoVerificarCodigoRequest,
    db: Session = Depends(get_db),
):
    _require_portal_publico_activo()
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    codigo = (body.codigo or "").strip()
    if not cedula or not email or not codigo:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Cedula, correo y codigo son obligatorios.")

    ip = get_client_ip(request)
    try:
        check_rate_limit_finiquito_verificar_codigo(ip)
    except HTTPException as e:
        if e.status_code == 429:
            finiquito_otp_bump("verificar_rate_limit_429")
        raise

    u = (
        db.query(FiniquitoUsuarioAcceso)
        .filter(
            FiniquitoUsuarioAcceso.cedula == cedula,
            FiniquitoUsuarioAcceso.email == email,
            FiniquitoUsuarioAcceso.is_active.is_(True),
        )
        .first()
    )
    if not u:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Credenciales invalidas.")

    now_utc = datetime.utcnow()
    row = (
        db.query(FiniquitoLoginCodigo)
        .filter(
            FiniquitoLoginCodigo.finiquito_usuario_id == u.id,
            FiniquitoLoginCodigo.codigo == codigo,
            FiniquitoLoginCodigo.usado.is_(False),
            FiniquitoLoginCodigo.expira_en > now_utc,
        )
        .order_by(FiniquitoLoginCodigo.creado_en.desc())
        .first()
    )
    if not row:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Codigo invalido o expirado.")

    row.usado = True
    db.commit()

    fini_min = int(settings.FINIQUITO_ACCESS_TOKEN_EXPIRE_MINUTES)
    access = create_access_token(
        subject=u.id,
        extra={"scope": "finiquito", "cedula": u.cedula, "email": u.email},
        expire_minutes=fini_min,
    )
    return FiniquitoVerificarCodigoResponse(
        ok=True,
        access_token=access,
        token_type="bearer",
        expires_in=fini_min * 60,
    )


@router.get("/public/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_public_listar_casos(
    bandeja: Optional[str] = Query(
        None,
        description=(
            "entrada = solo REVISION; desk = ACEPTADO, EN_PROCESO o TERMINADO; "
            "todos o omitir = todos los casos (solo prestamos LIQUIDADO materializados por el job)"
        ),
    ),
    db: Session = Depends(get_db),
    fu: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    _require_portal_publico_activo()
    b = (bandeja or "").lower().strip()
    if b in ("", "todos", "todas", "all"):
        q = db.query(FiniquitoCaso).order_by(FiniquitoCaso.id.desc())
    elif b == "entrada":
        q = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "REVISION").order_by(FiniquitoCaso.id.desc())
    elif b == "desk":
        q = (
            db.query(FiniquitoCaso)
            .filter(FiniquitoCaso.estado.in_(["ACEPTADO", "EN_PROCESO", "TERMINADO"]))
            .order_by(FiniquitoCaso.id.desc())
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="bandeja debe ser entrada, desk, todos u omitirse",
        )
    q = _query_casos_solo_cedula_portal(q, fu)
    casos = q.all()
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(
        db, [c.prestamo_id for c in casos]
    )
    items: List[FiniquitoCasoOut] = [
        _caso_to_out(
            c,
            mp.get(c.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(c.prestamo_id),
        )
        for c in casos
    ]
    n = len(items)
    return FiniquitoCasoListaResponse(items=items, total=n, limit=n, offset=0)


@router.get("/public/casos/{caso_id}/detalle", response_model=FiniquitoDetalleResponse)
def finiquito_public_detalle(
    caso_id: int,
    db: Session = Depends(get_db),
    fu: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    _require_portal_publico_activo()
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso or not _caso_pertenece_a_portal(fu, caso):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    prestamo = db.query(Prestamo).filter(Prestamo.id == caso.prestamo_id).first()
    cuotas = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == caso.prestamo_id)
        .order_by(Cuota.numero_cuota.asc())
        .all()
    )
    prestamo_d: Optional[dict[str, Any]] = None
    if prestamo:
        prestamo_d = _prestamo_caso_completo(prestamo)
    cuotas_l = [_cuota_to_dict(cu) for cu in cuotas]
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoDetalleResponse(
        caso=_caso_to_out(
            caso,
            mp.get(caso.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(caso.prestamo_id),
        ),
        prestamo=prestamo_d,
        cuotas=cuotas_l,
    )


@router.get("/public/revision-datos/{caso_id}")
def finiquito_public_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    fu: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    """
    Detalle del caso: préstamo vinculado (campos ampliados), plan de cuotas,
    listado /prestamos por cédula y /pagos por cédula (todos los pagos, tope 100 por API).
    """
    _require_portal_publico_activo()
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso or not _caso_pertenece_a_portal(fu, caso):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    cedula = (caso.cedula or "").strip()
    if not cedula:
        raise HTTPException(status_code=400, detail="Caso sin cedula")
    return jsonable_encoder(_build_revision_datos_payload(db, caso))


@router.patch("/public/casos/{caso_id}/estado", response_model=FiniquitoPatchEstadoResponse)
def finiquito_public_patch_estado(
    caso_id: int,
    body: FiniquitoPatchEstadoRequest,
    db: Session = Depends(get_db),
    fu: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    """Usuario portal: solo desde REVISION a ACEPTADO o RECHAZADO."""
    _require_portal_publico_activo()
    nuevo = (body.estado or "").upper().strip()
    if nuevo not in ("ACEPTADO", "RECHAZADO"):
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error="Solo puede aceptar o rechazar desde la bandeja de entrada (REVISION).",
        )
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso or not _caso_pertenece_a_portal(fu, caso):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if caso.estado != "REVISION":
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error="Solo puede cambiar casos en estado REVISION.",
        )
    anterior = (caso.estado or "").upper().strip()
    if nuevo == anterior:
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)
    caso.estado = nuevo
    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        actor_tipo="finiquito_externo",
        finiquito_usuario_id=fu.id,
    )
    sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
    db.commit()
    db.refresh(caso)
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoPatchEstadoResponse(
        ok=True,
        caso=_caso_to_out(
            caso,
            mp.get(caso.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(caso.prestamo_id),
        ),
    )


@router.get("/admin/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_admin_listar(
    estado: Optional[str] = Query(
        None,
        description="Un solo estado (REVISION, ACEPTADO, RECHAZADO, EN_PROCESO, TERMINADO)",
    ),
    estado_in: Optional[str] = Query(
        None,
        description="Varios estados separados por coma (ej. ACEPTADO,EN_PROCESO,TERMINADO). Tiene prioridad sobre estado.",
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial, sin distinguir mayusculas)",
    ),
    limit: int = Query(
        _ADMIN_CASOS_DEFAULT_LIMIT,
        ge=1,
        le=_ADMIN_CASOS_MAX_LIMIT,
        description="Tamano de pagina (max 2000).",
    ),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginacion."),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    # Filtros reutilizables: no usar .count() y luego el mismo Query con order_by
    # (en SQLAlchemy eso puede dejar el objeto en estado invalido y producir 500).
    filters: List[Any] = []
    if estado_in and estado_in.strip():
        parts = [p.strip().upper() for p in estado_in.split(",") if p.strip()]
        if not parts:
            raise HTTPException(status_code=400, detail="estado_in vacio")
        bad = [p for p in parts if p not in ESTADOS_VALIDOS]
        if bad:
            raise HTTPException(status_code=400, detail="Estado invalido en estado_in")
        filters.append(FiniquitoCaso.estado.in_(parts))
    elif estado:
        e = estado.upper().strip()
        if e not in ESTADOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Estado invalido")
        filters.append(FiniquitoCaso.estado == e)
    if cedula and cedula.strip():
        filters.append(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))

    count_q = db.query(func.count(FiniquitoCaso.id))
    list_q = db.query(FiniquitoCaso)
    if filters:
        count_q = count_q.filter(*filters)
        list_q = list_q.filter(*filters)
    total_raw = count_q.scalar()
    total = int(total_raw or 0)
    casos = (
        list_q.order_by(FiniquitoCaso.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = _admin_casos_to_items(db, casos)
    return FiniquitoCasoListaResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get(
    "/admin/casos/conteo-revision-nuevos",
    response_model=FiniquitoConteoRevisionNuevosResponse,
)
def finiquito_admin_conteo_revision_nuevos(
    horas: int = Query(
        72,
        ge=1,
        le=720,
        description=(
            "Ventana en horas: cuenta casos nuevos en bandeja principal cuyo creado_en (materializacion) "
            "cae en ese intervalo hacia atras desde ahora (UTC)."
        ),
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos.",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """
    KPI alarma: préstamos recién ingresados a finiquito (REVISION / bandeja principal) al catalogarse como
    LIQUIDADO elegibles en el job / refresco materializado.
    """
    cutoff = datetime.utcnow() - timedelta(hours=int(horas))
    q = db.query(func.count(FiniquitoCaso.id)).filter(
        FiniquitoCaso.estado == "REVISION",
        FiniquitoCaso.creado_en >= cutoff,
    )
    if cedula and cedula.strip():
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))
    total_raw = q.scalar()
    total = int(total_raw or 0)
    return FiniquitoConteoRevisionNuevosResponse(
        total=total, ventana_horas=int(horas)
    )


@router.get(
    "/admin/casos/resumen-estado",
    response_model=FiniquitoAdminResumenEstadoResponse,
)
def finiquito_admin_resumen_estado(
    cedula: Optional[str] = Query(
        None,
        description=(
            "Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos. "
            "Se usa para polling liviano sin cargar listas completas."
        ),
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    q = db.query(FiniquitoCaso)
    if cedula and cedula.strip():
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))

    rows = (
        q.with_entities(FiniquitoCaso.estado, func.count(FiniquitoCaso.id))
        .group_by(FiniquitoCaso.estado)
        .all()
    )
    counts: Dict[str, int] = {str(r[0] or "").upper(): int(r[1] or 0) for r in rows}
    total = int(sum(counts.values()))

    max_refresh = q.with_entities(func.max(FiniquitoCaso.ultimo_refresh_utc)).scalar()
    max_creado = q.with_entities(func.max(FiniquitoCaso.creado_en)).scalar()

    return FiniquitoAdminResumenEstadoResponse(
        total=total,
        revision=int(counts.get("REVISION", 0)),
        aceptado=int(counts.get("ACEPTADO", 0)),
        revision_contable=int(counts.get("REVISION_CONTABLE", 0)),
        rechazado=int(counts.get("RECHAZADO", 0)),
        en_proceso=int(counts.get("EN_PROCESO", 0)),
        terminado=int(counts.get("TERMINADO", 0)),
        max_ultimo_refresh_utc=max_refresh.isoformat() if max_refresh else None,
        max_creado_en_utc=max_creado.isoformat() if max_creado else None,
    )


@router.get(
    "/admin/casos/terminados/resumen-semanal",
    response_model=FiniquitoTerminadosResumenSemanalResponse,
)
def finiquito_admin_terminados_resumen_semanal(
    semanas: int = Query(
        16,
        ge=4,
        le=52,
        description="Cantidad maxima de semanas ISO recientes a devolver en el grafico.",
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos.",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """Conteo de casos TERMINADO agrupados por semana ISO de la fecha de cierre (historial)."""
    q = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "TERMINADO")
    if cedula and cedula.strip():
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))
    casos = q.all()
    ft = _map_fecha_terminado_por_caso(db, [c.id for c in casos])
    ctr: Counter[str] = Counter()
    for c in casos:
        raw = ft.get(c.id)
        if raw is None:
            continue
        d = raw.date() if hasattr(raw, "date") else raw
        if not isinstance(d, date):
            continue
        ctr[_semana_iso_key(d)] += 1
    keys_sorted = sorted(ctr.keys())
    if len(keys_sorted) > int(semanas):
        keys_sorted = keys_sorted[-int(semanas) :]
    semanas_out: List[FiniquitoTerminadosSemanaOut] = []
    for key in keys_sorted:
        y_str, w_str = key.split("-W", 1)
        try:
            y_i = int(y_str)
            w_i = int(w_str)
            d0 = date.fromisocalendar(y_i, w_i, 1)
            etiqueta = _etiqueta_semana_iso(d0)
        except (ValueError, TypeError):
            etiqueta = key
        semanas_out.append(
            FiniquitoTerminadosSemanaOut(
                semana=key,
                etiqueta=etiqueta,
                cantidad=int(ctr[key]),
            )
        )
    return FiniquitoTerminadosResumenSemanalResponse(
        semanas=semanas_out,
        total_terminados=len(casos),
    )


@router.get(
    "/admin/casos/terminados/resumen-diario",
    response_model=FiniquitoTerminadosResumenDiarioResponse,
)
def finiquito_admin_terminados_resumen_diario(
    dias: int = Query(
        21,
        ge=2,
        le=90,
        description=(
            "Ventana en dias calendario Caracas: incluye hoy y (dias - 1) dias anteriores. "
            "Por defecto 21 = hoy + 20 dias previos."
        ),
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos.",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """Conteo diario Caracas: entradas a area de trabajo (EN_PROCESO) y cierres TERMINADO."""
    hoy = fecha_hoy_caracas()
    inicio = hoy - timedelta(days=int(dias) - 1)

    ced_filtro = cedula.strip() if cedula and cedula.strip() else None

    ctr_ing = _conteo_ingresos_area_trabajo_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )

    q = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "TERMINADO")
    if ced_filtro:
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{ced_filtro}%"))
    casos = q.all()
    ctr = _conteo_terminados_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )

    dias_out: List[FiniquitoTerminadosDiaOut] = []
    cur = inicio
    while cur <= hoy:
        key = cur.isoformat()
        dias_out.append(
            FiniquitoTerminadosDiaOut(
                fecha=key,
                etiqueta=_etiqueta_dia_terminado(cur, hoy),
                cantidad=int(ctr.get(key, 0)),
                cantidad_ingresos=int(ctr_ing.get(key, 0)),
            )
        )
        cur += timedelta(days=1)

    total_en_ventana = sum(d.cantidad for d in dias_out)
    total_ingresos_en_ventana = sum(d.cantidad_ingresos for d in dias_out)
    return FiniquitoTerminadosResumenDiarioResponse(
        dias=dias_out,
        total_terminados=len(casos),
        total_en_ventana=total_en_ventana,
        total_ingresos_en_ventana=total_ingresos_en_ventana,
    )


@router.get(
    "/admin/casos/resumen-flujo-diario",
    response_model=FiniquitoFlujoResumenDiarioResponse,
)
def finiquito_admin_resumen_flujo_diario(
    dias: int = Query(
        21,
        ge=2,
        le=365,
        description=(
            "Ventana en dias calendario Caracas: incluye hoy y (dias - 1) dias anteriores."
        ),
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos.",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """
    Serie diaria del flujo finiquito:
    - ingresados a bandeja principal (creado_en)
    - procesados a área de revisión (ACEPTADO)
    - enviados a área de trabajo (EN_PROCESO)
    - terminados (TERMINADO)
    """
    hoy = fecha_hoy_caracas()
    inicio = hoy - timedelta(days=int(dias) - 1)
    ced_filtro = cedula.strip() if cedula and cedula.strip() else None

    ctr_bandeja = _conteo_ingresados_bandeja_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )
    ctr_revision = _conteo_ingresos_area_revision_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )
    ctr_trabajo = _conteo_ingresos_area_trabajo_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )
    ctr_terminados = _conteo_terminados_por_dia_caracas(
        db, inicio=inicio, hoy=hoy, ced_filtro=ced_filtro
    )

    dias_out: List[FiniquitoFlujoDiaOut] = []
    cur = inicio
    while cur <= hoy:
        key = cur.isoformat()
        dias_out.append(
            FiniquitoFlujoDiaOut(
                fecha=key,
                etiqueta=_etiqueta_dia_terminado(cur, hoy),
                cantidad_ingresados=int(ctr_bandeja.get(key, 0)),
                cantidad_revision=int(ctr_revision.get(key, 0)),
                cantidad_trabajo=int(ctr_trabajo.get(key, 0)),
                cantidad_terminados=int(ctr_terminados.get(key, 0)),
            )
        )
        cur += timedelta(days=1)

    return FiniquitoFlujoResumenDiarioResponse(
        dias=dias_out,
        total_ingresados_en_ventana=sum(d.cantidad_ingresados for d in dias_out),
        total_revision_en_ventana=sum(d.cantidad_revision for d in dias_out),
        total_trabajo_en_ventana=sum(d.cantidad_trabajo for d in dias_out),
        total_terminados_en_ventana=sum(d.cantidad_terminados for d in dias_out),
    )


@router.get(
    "/admin/casos/terminados",
    response_model=FiniquitoTerminadosListaResponse,
)
def finiquito_admin_listar_terminados(
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial).",
    ),
    limit: int = Query(
        _ADMIN_CASOS_MAX_LIMIT,
        ge=1,
        le=_ADMIN_CASOS_MAX_LIMIT,
        description="Tamano de pagina (max 2000).",
    ),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """Listado de casos TERMINADO con fechas de aprobacion, ultimo pago y cierre."""
    filters: List[Any] = [FiniquitoCaso.estado == "TERMINADO"]
    if cedula and cedula.strip():
        filters.append(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))
    count_q = db.query(func.count(FiniquitoCaso.id)).filter(*filters)
    list_q = db.query(FiniquitoCaso).filter(*filters)
    total = int(count_q.scalar() or 0)
    casos = (
        list_q.order_by(FiniquitoCaso.id.desc()).offset(offset).limit(limit).all()
    )
    items = _terminados_items_from_casos(db, casos)
    return FiniquitoTerminadosListaResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/admin/casos/{caso_id}/revision-datos")
def finiquito_admin_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """Misma carga que GET public/revision-datos (préstamo caso, cuotas, préstamos/pagos por cédula)."""
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    cedula = (caso.cedula or "").strip()
    if not cedula:
        raise HTTPException(status_code=400, detail="Caso sin cedula")
    return jsonable_encoder(
        _build_revision_datos_payload(db, caso, current_user=panel_user)
    )


@router.delete("/admin/casos/{caso_id}", response_model=FiniquitoEliminarCasoResponse)
def finiquito_admin_eliminar_caso(
    caso_id: int,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """Quita el caso de finiquito desde la bandeja principal (solo estado REVISION)."""
    err_perm = _error_gestion_bandeja_finiquito_si_no_admin(panel_user)
    if err_perm:
        return FiniquitoEliminarCasoResponse(ok=False, error=err_perm)
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if (caso.estado or "").upper().strip() != "REVISION":
        return FiniquitoEliminarCasoResponse(
            ok=False,
            error="Solo puede eliminar casos en Revision (bandeja principal).",
        )
    prestamo_id = int(caso.prestamo_id)
    db.delete(caso)
    limpiar_estado_gestion_finiquito_prestamos(db, [prestamo_id])
    db.commit()
    return FiniquitoEliminarCasoResponse(ok=True)


@router.post(
    "/admin/casos/{caso_id}/liberar-procesos-normales",
    response_model=FiniquitoLiberarProcesosNormalesResponse,
)
def finiquito_admin_liberar_procesos_normales(
    caso_id: int,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """
    Quita el caso de finiquito y deja el préstamo en cartera operativa (pagos, cuotas).
    Bandeja principal (REVISION), area de revision (ACEPTADO) o revision contable.
    """
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    est_caso = (caso.estado or "").strip().upper()
    if est_caso != "REVISION_CONTABLE":
        err_perm = _error_gestion_bandeja_finiquito_si_no_admin(panel_user)
        if err_perm:
            return FiniquitoLiberarProcesosNormalesResponse(ok=False, error=err_perm)
    from app.services.finiquito_liberar_procesos_normales_service import (
        ejecutar_liberar_finiquito_a_procesos_normales,
    )

    try:
        r = ejecutar_liberar_finiquito_a_procesos_normales(db, caso_id)
        if not r.get("ok"):
            status = int(r.get("http_status") or 400)
            if status == 404:
                raise HTTPException(status_code=404, detail=str(r.get("error")))
            return FiniquitoLiberarProcesosNormalesResponse(
                ok=False,
                error=str(r.get("error") or "No se pudo liberar"),
            )
        db.commit()
        return FiniquitoLiberarProcesosNormalesResponse(
            ok=True,
            prestamo_id=r.get("prestamo_id"),
            estado_prestamo_antes=r.get("estado_prestamo_antes"),
            estado_prestamo_despues=r.get("estado_prestamo_despues"),
            forzado_aprobado=r.get("forzado_aprobado"),
            mensaje=r.get("mensaje"),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("liberar-procesos-normales caso_id=%s", caso_id)
        return FiniquitoLiberarProcesosNormalesResponse(
            ok=False,
            error="Error interno al liberar el préstamo",
        )


def _usuario_registro_panel(panel_user: UserResponse) -> str:
    return (
        (getattr(panel_user, "email", None) or getattr(panel_user, "username", None) or "admin")
    )[:255]


def _traslado_finiquito_requiere_admin(estado_anterior: str, estado_nuevo: str) -> bool:
    """Bandeja -> revision, revision -> contable, contable -> trabajo."""
    ant = (estado_anterior or "").upper().strip()
    nue = (estado_nuevo or "").upper().strip()
    if nue == "ACEPTADO" and ant == "REVISION":
        return True
    if nue == "REVISION_CONTABLE" and ant == "ACEPTADO":
        return True
    return False


def _panel_usuario_finiquito_gestion_habilitado(panel_user: UserResponse) -> bool:
    """Admin, operario y gerente: mismos botones y traslados en /finiquitos/gestion."""
    from app.core.rol_normalization import canonical_rol

    return canonical_rol(getattr(panel_user, "rol", None)) in (
        "admin",
        "operator",
        "manager",
    )


def _error_traslado_finiquito_si_no_admin(
    panel_user: UserResponse,
    estado_anterior: str,
    estado_nuevo: str,
) -> Optional[str]:
    if not _traslado_finiquito_requiere_admin(estado_anterior, estado_nuevo):
        return None
    if _panel_usuario_finiquito_gestion_habilitado(panel_user):
        return None
    return (
        "Solo administradores pueden trasladar casos entre bandeja principal, "
        "area de revision, revision contable y area de trabajo."
    )


def _error_gestion_bandeja_finiquito_si_no_admin(
    panel_user: UserResponse,
) -> Optional[str]:
    """Rechazar, eliminar o liberar a procesos normales: panel interno (no solo admin)."""
    if _panel_usuario_finiquito_gestion_habilitado(panel_user):
        return None
    return (
        "Solo administradores pueden rechazar, eliminar o liberar casos "
        "desde la bandeja principal o el area de revision."
    )


def _mensaje_error_integridad_estado_finiquito(exc: IntegrityError, estado: str) -> str:
    det = str(getattr(exc, "orig", exc) or exc).lower()
    if "ck_finiquito_casos_estado" in det or "check constraint" in det:
        if (estado or "").upper().strip() == "REVISION_CONTABLE":
            return (
                "La base de datos aun no admite el estado REVISION_CONTABLE. "
                "Ejecute la migracion 075_finiquito_estado_revision_contable "
                "(alembic upgrade head o backend/sql/075_finiquito_estado_revision_contable.sql)."
            )
        return (
            "El estado solicitado no esta permitido por la base de datos (constraint ck_finiquito_casos_estado). "
            "Revise migraciones pendientes de finiquito."
        )
    return "No se pudo guardar el cambio de estado del caso finiquito."


def _commit_finiquito_patch_estado(
    db: Session, *, estado_nuevo: str
) -> Optional[FiniquitoPatchEstadoResponse]:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.exception("patch estado finiquito commit estado=%s", estado_nuevo)
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error=_mensaje_error_integridad_estado_finiquito(exc, estado_nuevo),
        )
    return None


def _admin_pasar_caso_a_en_proceso(
    db: Session,
    caso: FiniquitoCaso,
    panel_user: UserResponse,
    *,
    estado_anterior: str,
) -> Tuple[FiniquitoCasoOut, int]:
    """Transicion ACEPTADO -> EN_PROCESO y purga reserva temporal."""
    purgadas = purgar_reserva_conciliacion_caso(db, caso.id)
    caso.estado = "EN_PROCESO"
    if finiquito_casos_has_contacto_para_siguientes(db):
        caso.contacto_para_siguientes = None
    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=estado_anterior,
        estado_nuevo="EN_PROCESO",
        actor_tipo="admin",
        user_id=panel_user.id,
    )
    if finiquito_has_area_trabajo_auditoria_table(db):
        _registrar_auditoria_area_trabajo(
            db,
            caso_id=caso.id,
            accion="EN_PROCESO",
            estado_anterior=estado_anterior,
            estado_nuevo="EN_PROCESO",
            contacto_para_siguientes=None,
            user_id=panel_user.id,
        )
    sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
    db.commit()
    db.refresh(caso)
    return _admin_casos_to_items(db, [caso])[0], purgadas


@router.post(
    "/admin/casos/{caso_id}/conciliacion/visto-iniciar",
    response_model=FiniquitoConciliacionVistoIniciarResponse,
)
def finiquito_admin_conciliacion_visto_iniciar(
    caso_id: int,
    body: FiniquitoConciliacionVistoIniciarRequest = Body(
        default_factory=FiniquitoConciliacionVistoIniciarRequest
    ),
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """Primer Visto: reserva comprobantes en temporal y luego borra todos los pagos del prestamo."""
    err_perm = _error_gestion_bandeja_finiquito_si_no_admin(panel_user)
    if err_perm:
        return FiniquitoConciliacionVistoIniciarResponse(
            ok=False, error=err_perm
        )
    try:
        r = iniciar_visto_reserva(
            db,
            caso_id,
            confirmar_sin_comprobantes=bool(body.confirmar_sin_comprobantes),
        )
        if not r.get("ok"):
            db.rollback()
            return FiniquitoConciliacionVistoIniciarResponse(
                ok=False, error=str(r.get("error") or "Error")
            )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("visto-iniciar caso_id=%s: %s", caso_id, e)
        raise HTTPException(status_code=500, detail=str(e)[:300]) from e
    return FiniquitoConciliacionVistoIniciarResponse(
        ok=True,
        ya_iniciado=bool(r.get("ya_iniciado")),
        reservas=int(r.get("reservas") or 0),
        pagos_eliminados=r.get("pagos_eliminados"),
        mensaje=str(r.get("mensaje") or ""),
    )


@router.post(
    "/admin/casos/{caso_id}/conciliacion/recrear-ocr",
    response_model=FiniquitoConciliacionRecrearOcrResponse,
)
async def finiquito_admin_conciliacion_recrear_ocr(
    caso_id: int,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """Paso 4: recrea pagos desde reserva, OCR Gemini y cascada (reglas habituales + LIQUIDADO)."""
    usuario = _usuario_registro_panel(panel_user)
    try:
        r = await recrear_pagos_y_ocr_lote(db, caso_id, usuario)
        if not r.get("ok") and r.get("error"):
            db.rollback()
            return FiniquitoConciliacionRecrearOcrResponse(
                ok=False, error=str(r.get("error"))
            )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("recrear-ocr finiquito caso_id=%s: %s", caso_id, e)
        raise HTTPException(status_code=500, detail=str(e)[:300]) from e

    detalle_raw = r.get("detalle") or []
    detalle = [
        FiniquitoConciliacionRecrearOcrItem(
            reserva_id=int(d.get("reserva_id") or 0),
            ok=bool(d.get("ok")),
            error=d.get("error"),
            pago_id=d.get("pago_id"),
        )
        for d in detalle_raw
    ]
    return FiniquitoConciliacionRecrearOcrResponse(
        ok=bool(r.get("ok")),
        total=r.get("total"),
        ocr_ok=r.get("ocr_ok"),
        ocr_fallidos=r.get("ocr_fallidos"),
        pagos_recriados=r.get("pagos_recriados"),
        mensaje=r.get("mensaje"),
        detalle=detalle,
        cascada=r.get("cascada"),
    )


@router.post(
    "/admin/casos/{caso_id}/pasar-a-trabajo",
    response_model=FiniquitoConciliacionPasarATrabajoResponse,
)
def finiquito_admin_pasar_a_trabajo(
    caso_id: int,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """
    Boton X en area de revision: pasa a EN_PROCESO y elimina reserva temporal.
  """
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    anterior = (caso.estado or "").upper().strip()
    if anterior == "EN_PROCESO":
        purgadas = purgar_reserva_conciliacion_caso(db, caso.id)
        db.commit()
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoConciliacionPasarATrabajoResponse(
            ok=True,
            caso=caso_out,
            reservas_eliminadas=purgadas,
        )
    if anterior not in ("REVISION_CONTABLE", "ACEPTADO"):
        return FiniquitoConciliacionPasarATrabajoResponse(
            ok=False,
            error=(
                "Solo desde area de revision (ACEPTADO), revision contable "
                "(REVISION_CONTABLE) o ya en area de trabajo."
            ),
        )
    err_perm = _error_traslado_finiquito_si_no_admin(panel_user, anterior, "EN_PROCESO")
    if err_perm:
        return FiniquitoConciliacionPasarATrabajoResponse(ok=False, error=err_perm)
    if not finiquito_casos_has_contacto_para_siguientes(db):
        return FiniquitoConciliacionPasarATrabajoResponse(
            ok=False,
            error=(
                "Aplique la migracion de finiquito area de trabajo en la base de datos."
            ),
        )
    try:
        caso_out, purgadas = _admin_pasar_caso_a_en_proceso(
            db, caso, panel_user, estado_anterior=anterior
        )
    except Exception as e:
        db.rollback()
        logger.exception("pasar-a-trabajo caso_id=%s: %s", caso_id, e)
        raise HTTPException(status_code=500, detail=str(e)[:300]) from e
    return FiniquitoConciliacionPasarATrabajoResponse(
        ok=True,
        caso=caso_out,
        reservas_eliminadas=purgadas,
    )


@router.patch("/admin/casos/{caso_id}/estado", response_model=FiniquitoPatchEstadoResponse)
def finiquito_admin_patch_estado(
    caso_id: int,
    body: FiniquitoPatchEstadoRequest,
    db: Session = Depends(get_db),
    panel_user: UserResponse = Depends(require_admin_or_operator),
):
    """Panel interno (admin, operario o gerente): bandejas y area de trabajo (REVISION desde area, EN_PROCESO, TERMINADO)."""
    nuevo = (body.estado or "").upper().strip()
    if nuevo not in ESTADOS_VALIDOS:
        return FiniquitoPatchEstadoResponse(ok=False, error="Estado invalido")
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    anterior = (caso.estado or "").upper().strip()
    if nuevo == anterior:
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)

    err_perm = _error_traslado_finiquito_si_no_admin(panel_user, anterior, nuevo)
    if err_perm:
        return FiniquitoPatchEstadoResponse(ok=False, error=err_perm)

    if nuevo == "RECHAZADO":
        err_gestion = _error_gestion_bandeja_finiquito_si_no_admin(panel_user)
        if err_gestion:
            return FiniquitoPatchEstadoResponse(ok=False, error=err_gestion)

    if nuevo == "REVISION":
        if anterior not in ("ACEPTADO", "EN_PROCESO", "TERMINADO", "RECHAZADO"):
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error=(
                    "Solo puede devolver a Revision desde el area de trabajo "
                    "o desde Rechazado."
                ),
            )
        caso.estado = nuevo
        if finiquito_casos_has_contacto_para_siguientes(db):
            caso.contacto_para_siguientes = None
        _registrar_historial(
            db,
            caso=caso,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            actor_tipo="admin",
            user_id=panel_user.id,
        )
        if finiquito_has_area_trabajo_auditoria_table(db):
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="REVISION",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=None,
                user_id=panel_user.id,
            )
        sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
        err_commit = _commit_finiquito_patch_estado(db, estado_nuevo=nuevo)
        if err_commit:
            return err_commit
        db.refresh(caso)
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)

    if nuevo == "ACEPTADO":
        if anterior not in ("REVISION", "EN_PROCESO"):
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Validado (Aceptado) solo desde Revision o al volver desde En proceso.",
            )

    if nuevo == "REVISION_CONTABLE":
        if anterior != "ACEPTADO":
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Revision contable solo desde el area de revision (Validado).",
            )

    if nuevo == "RECHAZADO":
        if anterior != "REVISION":
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Rechazado solo desde la bandeja principal (Revision).",
            )

    if nuevo in ("EN_PROCESO", "TERMINADO") and not finiquito_casos_has_contacto_para_siguientes(db):
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error=(
                "Aplique la migracion de finiquito area de trabajo en la base de datos "
                "(backend/sql/2026-03-24_finiquito_area_trabajo_auditoria.sql o alembic upgrade head / 025_finiquito_area_trabajo)."
            ),
        )

    if nuevo == "TERMINADO":
        if anterior != "EN_PROCESO":
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Terminado solo desde En proceso (area de trabajo).",
            )
        if body.contacto_para_siguientes is None:
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Debe indicar si contacto al cliente para pasos siguientes (Si o No).",
            )
    elif nuevo == "EN_PROCESO":
        if anterior not in ("REVISION_CONTABLE", "ACEPTADO"):
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="En proceso solo desde area de revision o revision contable.",
            )
        purgar_reserva_conciliacion_caso(db, caso.id)

    caso.estado = nuevo
    if finiquito_casos_has_contacto_para_siguientes(db):
        if nuevo == "TERMINADO":
            caso.contacto_para_siguientes = body.contacto_para_siguientes
        else:
            caso.contacto_para_siguientes = None

    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        actor_tipo="admin",
        user_id=panel_user.id,
    )
    if finiquito_has_area_trabajo_auditoria_table(db):
        if nuevo == "EN_PROCESO":
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="EN_PROCESO",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=None,
                user_id=panel_user.id,
            )
        elif nuevo == "TERMINADO":
            _cps_aud = body.contacto_para_siguientes
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="TERMINADO",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=_cps_aud,
                user_id=panel_user.id,
            )

    sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
    err_commit = _commit_finiquito_patch_estado(db, estado_nuevo=nuevo)
    if err_commit:
        return err_commit
    db.refresh(caso)
    caso_out = _admin_casos_to_items(db, [caso])[0]
    return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)


@router.post("/admin/refresh-materializado")
def finiquito_admin_refresh_manual(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """Uso operativo: ejecutar el mismo refresco que los jobs programados de finiquito (sin esperar al cron)."""
    from app.services.finiquito_refresh import ejecutar_refresh_finiquito_casos

    return ejecutar_refresh_finiquito_casos(db)


@router.post("/admin/refresh-materializado-cedula")
def finiquito_admin_refresh_por_cedula(
    cedula: str = Query(..., min_length=1, max_length=20),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """
    Recuperacion operativa: liquida prestamos elegibles de una cedula y materializa
    finiquito_casos solo para esos prestamo_id (no borra casos de otras cedulas).
    """
    from app.services.finiquito_refresh import (
        persistir_liquidaciones_efectivas_para_finiquito,
        refrescar_finiquito_caso_prestamo_si_aplica,
    )

    cedula_norm = cedula.strip().upper()
    persistir_liquidaciones_efectivas_para_finiquito(db)
    prestamos = (
        db.execute(
            select(Prestamo).where(func.upper(func.trim(Prestamo.cedula)) == cedula_norm)
        )
        .scalars()
        .all()
    )
    if not prestamos:
        raise HTTPException(status_code=404, detail=f"Sin prestamos para cedula {cedula_norm}")

    detalle: List[dict[str, Any]] = []
    insertados = 0
    actualizados = 0
    eliminados = 0
    for p in prestamos:
        r = refrescar_finiquito_caso_prestamo_si_aplica(db, int(p.id))
        detalle.append(r)
        acc = (r.get("accion") or "").strip()
        if acc == "insertado":
            insertados += 1
        elif acc == "actualizado":
            actualizados += 1
        elif acc == "eliminado":
            eliminados += 1

    db.commit()
    casos = (
        db.query(FiniquitoCaso)
        .filter(func.upper(func.trim(FiniquitoCaso.cedula)) == cedula_norm)
        .order_by(FiniquitoCaso.id.asc())
        .all()
    )
    return {
        "cedula": cedula_norm,
        "prestamos": len(prestamos),
        "insertados": insertados,
        "actualizados": actualizados,
        "eliminados": eliminados,
        "detalle": detalle,
        "casos_actuales": [
            {
                "id": c.id,
                "prestamo_id": c.prestamo_id,
                "estado": c.estado,
            }
            for c in casos
        ],
    }


@router.post("/admin/reconciliar-gestion-cedula")
def finiquito_admin_reconciliar_gestion_cedula(
    cedula: str = Query(..., min_length=1, max_length=20),
    promover_caso_a_trabajo: bool = Query(
        False,
        description=(
            "False (default): el caso manda; baja prestamo si quedo EN_PROCESO sin terminar revision. "
            "True: sube caso a EN_PROCESO solo si el prestamo ya esta en trabajo."
        ),
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_operator),
):
    """
    Alinea finiquito_casos.estado con prestamos.estado_gestion_finiquito cuando quedaron
    desincronizados.
    """
    from app.services.finiquito_prestamo_gestion_sync import (
        reconciliar_gestion_finiquito_por_cedula,
    )

    out = reconciliar_gestion_finiquito_por_cedula(
        db, cedula, promover_caso_a_trabajo=promover_caso_a_trabajo
    )
    db.commit()
    return out
