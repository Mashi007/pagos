"""
Filas para GET /notificaciones/recibos/listado: pagos conciliados en la ventana del día Caracas
(``fecha_registro`` 00:00–23:45), con nombre/cédula, fecha de registro, monto pagado, comprobante
(misma resolución de URL que GET /pagos) y préstamo para PDF.

Se excluyen filas cuya cédula ya tiene envío Recibos registrado en ``recibos_email_envio`` para ese
``fecha_dia`` y slot de idempotencia (misma regla que el envío real): en pantalla solo queda lo
pendiente de enviar.
KPIs: histórico global en ``envios_notificacion`` (tipo_tab=recibos) y, por **día de corte** (fecha de
registro de pagos en ventana Caracas), olas de envío: cada ejecución manual hace un ``commit`` y en
PostgreSQL las filas nuevas de ``recibos_email_envio`` comparten el mismo ``creado_en`` de transacción;
``GROUP BY creado_en`` ordenado cronológicamente da el 1.er envío, 2.o envío, etc. Cambiar el día de
corte en la UI reinicia la serie (otro ``fecha_dia``).
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
from app.models.recibos_email_envio import RecibosEmailEnvio
from app.api.v1.endpoints.pagos.pago_serializacion_respuesta import (
    _enriquecer_pagos_pago_reportado_id,
    _pago_to_response,
)
from app.services.pagos.comprobante_link_desde_gmail import (
    enriquecer_items_link_comprobante_desde_gmail,
    enriquecer_items_link_comprobante_desde_pago_reportado,
)
from app.services.recibos_conciliacion_email_job import (
    RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA,
    bounds_fecha_registro_recibos_dia_caracas_00_2345,
    cedulas_recibos_ya_enviadas_en_fecha,
    _pago_aplicado_a_cuota_exists,
)
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def _fetch_pagos_recibos_ventana_orm(db: Session, *, fecha_dia: date) -> List[Pago]:
    start_naive, end_naive = bounds_fecha_registro_recibos_dia_caracas_00_2345(fecha_dia)
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


def _kpis_recibos_listado(
    db: Session,
    *,
    fecha_dia: date,
    pagos_en_ventana_total: int,
    cedulas_en_ventana_total: int,
) -> Dict[str, Any]:
    """
    ``correos_*``: histórico global (todos los días).

    ``olas_envio_recibos_dia``: por cada ``commit`` de envío real, un grupo de filas en
    ``recibos_email_envio`` con el mismo ``creado_en`` (PostgreSQL: ``now()`` estable por transacción).
    Orden cronológico = 1.er envío del día de corte, 2.o envío, …

    ``cedulas_registradas_envio_dia``: cédulas distintas ya registradas para este ``fecha_dia`` (techo
    útil frente a ``cedulas_en_ventana_total``).
    """
    base: Dict[str, Any] = {
        "correos_enviados": 0,
        "correos_rebotados": 0,
        "cedulas_registradas_envio_dia": 0,
        "registros_envio_dia_total": 0,
        "olas_envio_recibos_dia": [],
        "pagos_en_ventana_total": int(pagos_en_ventana_total),
        "cedulas_en_ventana_total": int(cedulas_en_ventana_total),
    }
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
        base["correos_enviados"] = int(env)
        base["correos_rebotados"] = int(reb)

        reg = (
            db.scalar(
                select(func.count(func.distinct(RecibosEmailEnvio.cedula_normalizada))).where(
                    RecibosEmailEnvio.fecha_dia == fecha_dia,
                    RecibosEmailEnvio.slot.in_(RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA),
                )
            )
            or 0
        )
        base["cedulas_registradas_envio_dia"] = int(reg)

        lotes = db.execute(
            select(RecibosEmailEnvio.creado_en, func.count(RecibosEmailEnvio.id))
            .where(
                RecibosEmailEnvio.fecha_dia == fecha_dia,
                RecibosEmailEnvio.slot.in_(RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA),
            )
            .group_by(RecibosEmailEnvio.creado_en)
            .order_by(RecibosEmailEnvio.creado_en.asc())
        ).all()

        olas: List[Dict[str, Any]] = []
        sum_registros = 0
        for i, row in enumerate(lotes, start=1):
            cre = row[0]
            cnt = int(row[1] or 0)
            sum_registros += cnt
            ts = cre.isoformat() if hasattr(cre, "isoformat") else str(cre)
            olas.append(
                {
                    "orden": i,
                    "creado_en": ts,
                    "correos_registrados_lote": cnt,
                }
            )
        base["olas_envio_recibos_dia"] = olas
        base["registros_envio_dia_total"] = int(sum_registros)
    except Exception:
        pass
    return base


def listar_recibos_ventana_con_ui(
    db: Session,
    *,
    fecha_dia: date,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], int, int]:
    """Devuelve (filas para tabla + KPIs, total_pagos, cedulas_distintas). Solo pendientes de envío Recibos."""
    pagos_orm_all = _fetch_pagos_recibos_ventana_orm(db, fecha_dia=fecha_dia)
    ced_ventana: set[str] = set()
    for p in pagos_orm_all:
        raw = (getattr(p, "cedula_cliente", None) or "").strip()
        nn = texto_cedula_comparable_bd(raw)
        if nn:
            ced_ventana.add(nn)
    pagos_en_ventana_total = len(pagos_orm_all)
    cedulas_en_ventana_total = len(ced_ventana)

    ya = cedulas_recibos_ya_enviadas_en_fecha(db, fecha_dia)
    pagos_orm = list(pagos_orm_all)
    if ya:
        pagos_orm = [
            p
            for p in pagos_orm
            if texto_cedula_comparable_bd((getattr(p, "cedula_cliente", None) or "").strip()) not in ya
        ]

    kpis = _kpis_recibos_listado(
        db,
        fecha_dia=fecha_dia,
        pagos_en_ventana_total=pagos_en_ventana_total,
        cedulas_en_ventana_total=cedulas_en_ventana_total,
    )

    if not pagos_orm:
        return [], kpis, 0, 0

    pago_ids = [int(p.id) for p in pagos_orm]
    cuotas_map = _cuotas_por_pago_id(db, pago_ids)

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

    snapshots = [_pago_to_response(p) for p in pagos_orm]
    _enriquecer_pagos_pago_reportado_id(db, snapshots)
    enriquecer_items_link_comprobante_desde_gmail(db, snapshots)
    enriquecer_items_link_comprobante_desde_pago_reportado(db, snapshots)

    filas: List[Dict[str, Any]] = []
    ced_norms: set[str] = set()

    for pg, snap in zip(pagos_orm, snapshots):
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

        cid_final = int(cliente_id) if cliente_id is not None else (int(cl.id) if cl is not None else 0)

        lc = (snap.get("link_comprobante") or "").strip() or None
        dr = (snap.get("documento_ruta") or "").strip() or None
        dn = (snap.get("documento_nombre") or "").strip() or None
        dt = (snap.get("documento_tipo") or "").strip() or None

        fila: Dict[str, Any] = {
            "pago_id": int(pg.id),
            "cedula": ced,
            "cedula_normalizada": ced_norm,
            "fecha_registro": pg.fecha_registro.isoformat() if pg.fecha_registro else None,
            "monto_pagado": float(getattr(pg, "monto_pagado", 0) or 0),
            "prestamo_id": pid,
            "cliente_id": cid_final,
            "nombre": nombre,
            "link_comprobante": lc,
            "documento_ruta": dr,
            "documento_nombre": dn,
            "documento_tipo": dt,
        }
        filas.append(fila)

    total = len(filas)
    cedulas_dist = len(ced_norms)
    return filas, kpis, total, cedulas_dist
