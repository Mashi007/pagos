"""
Filas enriquecidas para GET /notificaciones/recibos/listado: misma forma operativa que
listados de notificaciones (crédito, nombre, cuota, vencimiento, atrasos, total pendiente,
revisión manual, KPI correos desde envios_notificacion tipo_tab=recibos).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.envio_notificacion import EnvioNotificacion
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.notificacion_service import (
    contar_cuotas_atraso_por_prestamos,
    enriquecer_items_notificacion_revision_manual,
    sum_saldo_pendiente_total_por_prestamos,
)
from app.services.recibos_conciliacion_email_job import (
    RecibosSlot,
    _bounds_fecha_registro_caracas,
    _pago_aplicado_a_cuota_exists,
)
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def _fetch_pagos_recibos_ventana_orm(
    db: Session, *, fecha_dia: date, slot: RecibosSlot
) -> List[Pago]:
    start_naive, end_naive = _bounds_fecha_registro_caracas(fecha_dia, slot)
    return list(
        db.execute(
            select(Pago)
            .where(
                Pago.conciliado.is_(True),
                func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
                Pago.fecha_registro >= start_naive,
                Pago.fecha_registro <= end_naive,
                Pago.cedula_cliente.isnot(None),
                func.length(func.trim(Pago.cedula_cliente)) > 0,
                _pago_aplicado_a_cuota_exists(),
            )
            .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
        )
        .scalars()
        .all()
    )


def _dedupe_cuotas(cuotas: List[Cuota]) -> List[Cuota]:
    seen: set[int] = set()
    out: List[Cuota] = []
    for c in cuotas:
        if c.id in seen:
            continue
        seen.add(c.id)
        out.append(c)
    return out


def _cuotas_por_pago_id(
    db: Session, pago_ids: List[int]
) -> Dict[int, List[Cuota]]:
    if not pago_ids:
        return {}
    by_pid: Dict[int, List[Cuota]] = defaultdict(list)
    direct = db.execute(select(Cuota).where(Cuota.pago_id.in_(pago_ids))).scalars().all()
    for c in direct:
        if c.pago_id is not None:
            by_pid[int(c.pago_id)].append(c)
    pairs = db.execute(
        select(CuotaPago.pago_id, CuotaPago.cuota_id).where(CuotaPago.pago_id.in_(pago_ids))
    ).all()
    extra_ids = sorted({int(cid) for _, cid in pairs if cid is not None})
    cu_by_id: Dict[int, Cuota] = {}
    if extra_ids:
        for c in db.execute(select(Cuota).where(Cuota.id.in_(extra_ids))).scalars().all():
            cu_by_id[int(c.id)] = c
    for pid, cid in pairs:
        cu = cu_by_id.get(int(cid))
        if cu:
            by_pid[int(pid)].append(cu)
    return {k: _dedupe_cuotas(v) for k, v in by_pid.items()}


def _pick_cuota_representativa(pg: Pago, cuotas: List[Cuota]) -> Optional[Cuota]:
    if not cuotas:
        return None
    pid_prest = getattr(pg, "prestamo_id", None)
    pool = cuotas
    if pid_prest is not None:
        filt = [c for c in cuotas if c.prestamo_id == int(pid_prest)]
        if filt:
            pool = filt
    return max(pool, key=lambda c: (c.numero_cuota or 0, c.id))


def _kpis_recibos_correo(db: Session) -> Dict[str, int]:
    try:
        env = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.tipo_tab == "recibos",
                    EnvioNotificacion.exito.is_(True),
                )
            )
            or 0
        )
        reb = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.tipo_tab == "recibos",
                    EnvioNotificacion.exito.is_(False),
                )
            )
            or 0
        )
        return {"correos_enviados": int(env), "correos_rebotados": int(reb)}
    except Exception:
        return {"correos_enviados": 0, "correos_rebotados": 0}


def listar_recibos_ventana_con_ui(
    db: Session,
    *,
    fecha_dia: date,
    slot: RecibosSlot,
) -> Tuple[List[Dict[str, Any]], Dict[str, int], int, int]:
    """
    Devuelve (filas para tabla + KPIs, total_pagos, cedulas_distintas).
    Cada fila incluye campos compatibles con enriquecer_items_notificacion_revision_manual
    y con el listado de notificaciones en frontend (prestamo_id, nombre, cuotas_atrasadas, …).
    """
    pagos_orm = _fetch_pagos_recibos_ventana_orm(db, fecha_dia=fecha_dia, slot=slot)
    if not pagos_orm:
        return [], _kpis_recibos_correo(db), 0, 0

    pago_ids = [int(p.id) for p in pagos_orm]
    cuotas_map = _cuotas_por_pago_id(db, pago_ids)

    prestamos_ids: List[int] = []
    for pg in pagos_orm:
        cuotas = cuotas_map.get(int(pg.id), [])
        ref = _pick_cuota_representativa(pg, cuotas)
        pid = int(ref.prestamo_id) if ref else None
        if pid is None and getattr(pg, "prestamo_id", None):
            pid = int(pg.prestamo_id)
        if pid is not None:
            prestamos_ids.append(pid)

    ca_map = contar_cuotas_atraso_por_prestamos(
        db, sorted({p for p in prestamos_ids}), fecha_referencia=fecha_dia
    )
    tp_map = sum_saldo_pendiente_total_por_prestamos(db, sorted({p for p in prestamos_ids}))

    cedulas_display = sorted(
        {(p.cedula_cliente or "").strip() for p in pagos_orm if (p.cedula_cliente or "").strip()}
    )
    cliente_por_cedula: Dict[str, Cliente] = {}
    if cedulas_display:
        for cl in db.scalars(select(Cliente).where(Cliente.cedula.in_(cedulas_display))).all():
            k = (cl.cedula or "").strip().upper()
            if k:
                cliente_por_cedula[k] = cl

    cliente_ids_needed: set[int] = set()
    for pg in pagos_orm:
        cuotas = cuotas_map.get(int(pg.id), [])
        ref = _pick_cuota_representativa(pg, cuotas)
        pid = int(ref.prestamo_id) if ref else None
        if pid is None and getattr(pg, "prestamo_id", None):
            pid = int(pg.prestamo_id)
        if ref and ref.cliente_id:
            cliente_ids_needed.add(int(ref.cliente_id))
        elif pid is not None:
            pr = db.get(Prestamo, pid)
            if pr and pr.cliente_id:
                cliente_ids_needed.add(int(pr.cliente_id))

    clientes: Dict[int, Cliente] = {}
    if cliente_ids_needed:
        for cl in db.scalars(select(Cliente).where(Cliente.id.in_(sorted(cliente_ids_needed)))).all():
            clientes[int(cl.id)] = cl

    filas: List[Dict[str, Any]] = []
    ced_norms: set[str] = set()

    for pg in pagos_orm:
        ced = (getattr(pg, "cedula_cliente", None) or "").strip()
        ced_norm = texto_cedula_comparable_bd(ced)
        if ced_norm:
            ced_norms.add(ced_norm)
        cuotas = cuotas_map.get(int(pg.id), [])
        ref = _pick_cuota_representativa(pg, cuotas)
        pid = int(ref.prestamo_id) if ref else None
        if pid is None and getattr(pg, "prestamo_id", None):
            pid = int(pg.prestamo_id)

        cliente_id: Optional[int] = None
        if ref and ref.cliente_id:
            cliente_id = int(ref.cliente_id)
        elif pid is not None:
            pr = db.get(Prestamo, pid)
            if pr and pr.cliente_id:
                cliente_id = int(pr.cliente_id)

        cl = clientes.get(cliente_id) if cliente_id is not None else None
        if cl is None and ced:
            cl = cliente_por_cedula.get(ced.strip().upper())
            if cl is not None:
                cliente_id = int(cl.id)
        nombre = (cl.nombres or "").strip() if cl else ""
        if not nombre and ced:
            nombre = ced

        n_cuota = int(ref.numero_cuota) if ref and ref.numero_cuota is not None else None
        fv = ref.fecha_vencimiento.isoformat() if ref and ref.fecha_vencimiento else None
        monto_cuota = float(ref.monto) if ref and ref.monto is not None else None

        ca = ca_map.get(pid, 0) if pid is not None else 0
        tp = tp_map.get(pid) if pid is not None else None

        cid_final = int(cliente_id) if cliente_id is not None else (int(cl.id) if cl is not None else 0)

        fila: Dict[str, Any] = {
            "pago_id": int(pg.id),
            "cedula": ced,
            "cedula_normalizada": ced_norm,
            "fecha_registro": pg.fecha_registro.isoformat() if pg.fecha_registro else None,
            "monto_pagado": float(getattr(pg, "monto_pagado", 0) or 0),
            "prestamo_id": pid,
            "cliente_id": cid_final,
            "nombre": nombre,
            "numero_cuota": n_cuota,
            "fecha_vencimiento": fv,
            "monto": monto_cuota,
            "cuotas_atrasadas": int(ca) if ca is not None else 0,
        }
        if tp is not None:
            fila["total_pendiente_pagar"] = float(tp)
        filas.append(fila)

    enriquecer_items_notificacion_revision_manual(db, filas)
    kpis = _kpis_recibos_correo(db)
    total = len(filas)
    cedulas_dist = len(ced_norms)
    return filas, kpis, total, cedulas_dist
