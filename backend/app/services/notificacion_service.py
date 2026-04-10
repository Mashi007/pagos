"""
Servicios para notificaciones de cuotas vencidas y en mora.
Centraliza la lógica de serialización y filtrado de cuotas.
Listados por pestaña: get_cuotas_pendientes_por_vencimientos (filtra en SQL por fechas);
build_cuotas_pendiente_2_dias_antes_items (solo estado PENDIENTE, vence en 2 días).
"""
import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.serializers import to_finite_float
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.utils.cliente_emails import emails_destino_desde_objeto
from app.services.cuota_estado import (
    clasificar_estado_cuota,
    dias_retraso_desde_vencimiento,
    hoy_negocio,
)

logger = logging.getLogger(__name__)

_MESES_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def fecha_cuota_a_texto_es(fv: Optional[date]) -> str:
    """
    Fecha de cuota en español (sin depender de locale), p. ej. '5 de abril de 2026'.
    Para plantillas: clave en el item `fecha_vencimiento_display` y {{fecha_vencimiento_display}} en BD.
    """
    if fv is None:
        return ""
    d = fv
    if hasattr(d, "date") and not isinstance(d, date):
        try:
            d = d.date()
        except Exception:
            return str(fv)
    if not isinstance(d, date):
        return str(fv)
    return f"{d.day} de {_MESES_ES[d.month - 1]} de {d.year}"


# Misma tolerancia que clasificación de cuota pagada (cuota_estado): evita notificar si ya está cubierta al 100%.
TOL_SALDO_CUOTA_NOTIFICACION = 0.01
SALDO_PENDIENTE_CUOTA = func.coalesce(Cuota.monto, 0) - func.coalesce(Cuota.total_pagado, 0)

# Estados que marcan cuota pagada (columna cuotas.estado); no notificar aunque falte fecha_pago.
_ESTADOS_CUOTA_PAGADA = ("PAGADO", "PAGO_ADELANTADO", "PAGADA")
# NULL en estado sigue permitiendo notificar (se filtra por saldo y fecha_pago).
CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF = or_(
    Cuota.estado.is_(None),
    ~Cuota.estado.in_(_ESTADOS_CUOTA_PAGADA),
)

# Prejudicial (submenu Notificaciones «Atraso 5 cuotas»): solo cuotas con columna estado VENCIDO o MORA
# (clasificar_estado_cuota en cuota_estado.py; MORA = morosidad por calendario).
ESTADOS_CUOTA_VENCIDO_Y_MORA = ("VENCIDO", "MORA")
# Clientes con al menos esta cantidad de cuotas VENCIDO/MORA vencidas (saldo > tol) entran al listado prejudicial.
PREJUDICIAL_MIN_CUOTAS_VENCIDO_MORA = 5


def _select_cuotas_pendientes_con_cliente():
    """Query base: cuota pendiente + cliente vía préstamo (sin filtro de fecha de vencimiento)."""
    return (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
        .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
        .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
    )


def build_cuotas_pendiente_2_dias_antes_items(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[dict]:
    """
    Cuotas con columna estado = PENDIENTE cuya fecha_vencimiento es exactamente
    hoy + 2 días (Caracas). Sin fecha_pago, saldo > tolerancia, préstamo no liquidado/desistimiento.
    Una fila por cuota (misma forma que otras pestañas de notificaciones).
    """
    hoy = fecha_referencia or hoy_negocio()
    fv_objetivo = hoy + timedelta(days=2)
    q = (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(Cuota.estado == "PENDIENTE")
        .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
        .where(Cuota.fecha_vencimiento == fv_objetivo)
        .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
    )
    rows = db.execute(q).all()
    if not rows:
        return []
    pids = [c.prestamo_id for c, _ in rows]
    counts = contar_cuotas_atraso_por_prestamos(db, pids, fecha_referencia=hoy)
    totales = sum_saldo_pendiente_total_por_prestamos(db, pids)
    out: List[dict] = []
    for cuota, cliente in rows:
        ca = counts.get(cuota.prestamo_id, 0)
        tp = totales.get(cuota.prestamo_id)
        out.append(
            format_cuota_item(
                cliente,
                cuota,
                cuotas_atrasadas=ca,
                dias_antes_vencimiento=2,
                for_tab=True,
                total_pendiente_pagar=tp,
            )
        )
    enriquecer_items_notificacion_revision_manual(db, out)
    return out


def get_cuotas_pendientes_por_vencimientos(
    db: Session, fechas_vencimiento: Sequence[date]
) -> List[Tuple[Cuota, Cliente]]:
    """
    Misma semántica que get_cuotas_pendientes_con_cliente pero solo filas cuya
    fecha_vencimiento está en el conjunto dado. Evita cargar todo el universo de mora
    (timeout en /clientes-retrasados y get_notificaciones_tabs_data).

    No ejecuta sincronización de pagos: el listado debe ser lectura rápida; la conciliación
    ocurre al registrar pagos o en jobs dedicados.
    """
    fechas = tuple({d for d in fechas_vencimiento if d is not None})
    if not fechas:
        return []
    q = _select_cuotas_pendientes_con_cliente().where(Cuota.fecha_vencimiento.in_(fechas))
    rows = db.execute(q).all()
    return [(row[0], row[1]) for row in rows]


def sum_saldo_pendiente_total_por_prestamos(
    db: Session, prestamo_ids: Sequence[int]
) -> Dict[int, float]:
    """
    Por préstamo: suma del saldo pendiente (monto - total_pagado) de todas las cuotas
    que siguen las mismas reglas que el listado de notificaciones (sin pagar, saldo > tol,
    préstamo no liquidado/desistimiento). Incluye cuotas futuras y vencidas: es el total
    que el cliente adeuda en ese crédito, no solo la cuota de la fila.
    """
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return {}
    pendiente_expr = func.coalesce(Cuota.monto, 0) - func.coalesce(Cuota.total_pagado, 0)
    q = (
        select(Cuota.prestamo_id, func.sum(pendiente_expr).label("total_pendiente"))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(Cuota.prestamo_id.in_(ids))
        .where(Cuota.fecha_pago.is_(None))
        .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
        .where(pendiente_expr > TOL_SALDO_CUOTA_NOTIFICACION)
        .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
        .group_by(Cuota.prestamo_id)
    )
    out: Dict[int, float] = {}
    for row in db.execute(q).all():
        pid = int(row[0])
        total = row[1]
        xf = to_finite_float(total)
        if xf is not None:
            out[pid] = xf
    return out


def sum_saldo_pendiente_cuotas_tabla_amortizacion_ui(
    db: Session, prestamo_ids: Sequence[int]
) -> Dict[int, float]:
    """
    Por préstamo: suma de GREATEST(0, monto_cuota - total_pagado) sobre todas las cuotas.

    Alineado con «Total pendiente pagar» en TablaAmortizacionPrestamo (cuando el monto
    efectivo abonado coincide con total_pagado; no usa heurísticas de notificaciones).

    Difiere de sum_saldo_pendiente_total_por_prestamos: ese solo suma cuotas «notificables»
    (sin fecha_pago, estado no marcado como pagado en columna, etc.). Este incluye todas
    las filas de amortización y excluye préstamos LIQUIDADO / DESISTIMIENTO del agregado
    (mismo criterio que el listado mostraba con saldo 0 en cartera cerrada).
    """
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return {}
    m = func.coalesce(Cuota.monto, 0)
    tp = func.coalesce(Cuota.total_pagado, 0)
    per_cuota = func.greatest(0, m - tp)
    q = (
        select(Cuota.prestamo_id, func.sum(per_cuota).label("total_pend"))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(Cuota.prestamo_id.in_(ids))
        .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
        .group_by(Cuota.prestamo_id)
    )
    out: Dict[int, float] = {}
    for row in db.execute(q).all():
        pid = int(row[0])
        total = row[1]
        xf = to_finite_float(total)
        if xf is not None:
            out[pid] = xf
    return out


def contar_cuotas_pagadas_tabla_amortizacion_ui(
    db: Session, prestamo_ids: Sequence[int]
) -> Dict[int, tuple[int, int]]:
    """
    Por préstamo: (cuotas_pagadas, cuotas_total) con la misma regla que el chip «Pagadas»
    en TablaAmortizacionPrestamo.tsx (estado PAGADO/PAGADA/PAGO_ADELANTADO o
    total_pagado >= monto - 0,01).
    """
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return {}
    est_u = func.upper(func.trim(func.coalesce(Cuota.estado, "")))
    es_pagada = or_(
        est_u.in_(["PAGADO", "PAGADA", "PAGO_ADELANTADO"]),
        func.coalesce(Cuota.total_pagado, 0) >= func.coalesce(Cuota.monto, 0) - TOL_SALDO_CUOTA_NOTIFICACION,
    )
    pagadas_expr = case((es_pagada, 1), else_=0)
    q = (
        select(
            Cuota.prestamo_id,
            func.count().label("n_total"),
            func.sum(pagadas_expr).label("n_pagadas"),
        )
        .select_from(Cuota)
        .where(Cuota.prestamo_id.in_(ids))
        .group_by(Cuota.prestamo_id)
    )
    out: Dict[int, tuple[int, int]] = {}
    for row in db.execute(q).all():
        pid = int(row[0])
        total = int(row[1] or 0)
        pag = int(row[2] or 0)
        out[pid] = (pag, total)
    return out


def contar_cuotas_atraso_por_prestamos(
    db: Session,
    prestamo_ids: Sequence[int],
    fecha_referencia: Optional[date] = None,
) -> dict[int, int]:
    """
    Por préstamo: cuotas en atraso con la misma regla que estado de cuenta / amortización
    (clasificar_estado_cuota + al menos 1 día de retraso desde vencimiento; Caracas).
    """
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return {}
    hoy = fecha_referencia or hoy_negocio()
    cuotas = (
        db.execute(select(Cuota).where(Cuota.prestamo_id.in_(ids))).scalars().all()
    )
    by_pid: Dict[int, List[Cuota]] = defaultdict(list)
    for c in cuotas:
        by_pid[c.prestamo_id].append(c)
    out: dict[int, int] = {}
    for pid in ids:
        n = 0
        for c in by_pid.get(pid, []):
            monto = float(c.monto or 0)
            paid = float(c.total_pagado or 0)
            fv = c.fecha_vencimiento
            estado = clasificar_estado_cuota(paid, monto, fv, hoy)
            if estado in ("PAGADO", "PAGO_ADELANTADO"):
                continue
            if dias_retraso_desde_vencimiento(fv, hoy) >= 1:
                n += 1
        out[pid] = n
    return out


def get_cuotas_pendientes_con_cliente(db: Session) -> List[Tuple[Cuota, Cliente]]:
    """
    Todas las cuotas pendientes de notificar (sin filtrar por día de vencimiento).
    Costoso en carteras grandes; preferir get_cuotas_pendientes_por_vencimientos para pestañas.
    """
    rows = db.execute(_select_cuotas_pendientes_con_cliente()).all()
    return [(row[0], row[1]) for row in rows]


def get_primer_item_ejemplo_paquete_prueba(db: Session, tipo: str) -> Optional[dict]:
    """
    Primer item real para prueba/diagnostico de paquete sin cargar todas las cuotas.
    Misma semantica que el primer elemento de get_notificaciones_tabs_data por criterio.
    """
    tipo = (tipo or "").strip()
    hoy = hoy_negocio()

    if tipo in (
        "PAGO_1_DIA_ATRASADO",
        "PAGO_3_DIAS_ATRASADO",
        "PAGO_5_DIAS_ATRASADO",
        "PAGO_30_DIAS_ATRASADO",
    ):
        dias_map = {
            "PAGO_1_DIA_ATRASADO": 1,
            "PAGO_3_DIAS_ATRASADO": 3,
            "PAGO_5_DIAS_ATRASADO": 5,
            "PAGO_30_DIAS_ATRASADO": 30,
        }
        dias = dias_map[tipo]
        target = hoy - timedelta(days=dias)
        q = (
            select(Cuota, Cliente)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cuota.fecha_pago.is_(None))
            .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
            .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
            .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
            .where(Cuota.fecha_vencimiento == target)
            .limit(1)
        )
        row = db.execute(q).first()
        if not row:
            return None
        cuota, cliente = row[0], row[1]
        ca = contar_cuotas_atraso_por_prestamos(db, [cuota.prestamo_id]).get(
            cuota.prestamo_id, 0
        )
        totales = sum_saldo_pendiente_total_por_prestamos(db, [cuota.prestamo_id])
        return format_cuota_item(
            cliente,
            cuota,
            dias_atraso=dias,
            cuotas_atrasadas=ca,
            for_tab=True,
            total_pendiente_pagar=totales.get(cuota.prestamo_id),
        )

    if tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
        target = hoy + timedelta(days=2)
        q = (
            select(Cuota, Cliente)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cuota.fecha_pago.is_(None))
            .where(Cuota.estado == "PENDIENTE")
            .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
            .where(~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")))
            .where(Cuota.fecha_vencimiento == target)
            .limit(1)
        )
        row = db.execute(q).first()
        if not row:
            return None
        cuota, cliente = row[0], row[1]
        ca = contar_cuotas_atraso_por_prestamos(db, [cuota.prestamo_id]).get(
            cuota.prestamo_id, 0
        )
        totales = sum_saldo_pendiente_total_por_prestamos(db, [cuota.prestamo_id])
        return format_cuota_item(
            cliente,
            cuota,
            cuotas_atrasadas=ca,
            dias_antes_vencimiento=2,
            for_tab=True,
            total_pendiente_pagar=totales.get(cuota.prestamo_id),
        )

    if tipo == "PREJUDICIAL":
        subq = (
            select(Cuota.cliente_id, func.count(Cuota.id).label("total"))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(
                Cuota.fecha_pago.is_(None),
                Cuota.estado.in_(ESTADOS_CUOTA_VENCIDO_Y_MORA),
                Cuota.fecha_vencimiento < hoy,
                Cuota.cliente_id.isnot(None),
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
                ~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")),
            )
            .group_by(Cuota.cliente_id)
            .having(func.count(Cuota.id) >= PREJUDICIAL_MIN_CUOTAS_VENCIDO_MORA)
            .limit(1)
        )
        row = db.execute(subq).first()
        if not row:
            return None
        cliente_id, total_cuotas = row[0], int(row[1] or 0)
        cliente = db.get(Cliente, cliente_id)
        if not cliente:
            return None
        primera = db.execute(
            select(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(
                Cuota.cliente_id == cliente_id,
                Cuota.fecha_pago.is_(None),
                Cuota.estado.in_(ESTADOS_CUOTA_VENCIDO_Y_MORA),
                Cuota.fecha_vencimiento < hoy,
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
                ~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")),
            )
            .order_by(Cuota.fecha_vencimiento.asc())
            .limit(1)
        ).scalars().first()
        cuota_ref = primera
        if not cuota_ref:
            cuota_ref = type(
                "DummyCuota",
                (),
                {
                    "fecha_vencimiento": hoy,
                    "numero_cuota": 0,
                    "monto": 0,
                    "prestamo_id": None,
                },
            )()
        pid = getattr(cuota_ref, "prestamo_id", None)
        totales_p = (
            sum_saldo_pendiente_total_por_prestamos(db, [pid]) if pid else {}
        )
        item = format_cuota_item(
            cliente,
            cuota_ref,
            for_tab=True,
            total_pendiente_pagar=totales_p.get(pid) if pid else None,
        )
        item["total_cuotas_atrasadas"] = total_cuotas
        return item

    return None


def format_cuota_item(
    cliente: Cliente,
    cuota: Cuota,
    dias_atraso: Optional[int] = None,
    cuotas_atrasadas: Optional[int] = None,
    dias_antes_vencimiento: Optional[int] = None,
    for_tab: bool = False,
    total_pendiente_pagar: Optional[float] = None,
) -> dict:
    """
    Formatea un registro de cliente+cuota para la lista de notificaciones.
    
    Args:
        cliente: Objeto Cliente
        cuota: Objeto Cuota
        dias_atraso: Días desde vencimiento de esta cuota (bucket 1/3/5/30; plantillas/tipo envío).
        cuotas_atrasadas: Total cuotas en atraso del préstamo (misma regla que estado de cuenta).
        dias_antes_vencimiento: Días antes del vencimiento (si aplica)
        for_tab: Si True, incluye campos adicionales para las pestañas del frontend
    
    Returns:
        Dict con datos formateados para el frontend
    """
    base_item: Dict[str, Any] = {
        "cliente_id": cliente.id,
        "nombre": cliente.nombres or "",
        "cedula": cliente.cedula or "",
        "prestamo_id": cuota.prestamo_id,
        "numero_cuota": cuota.numero_cuota,
        "fecha_vencimiento": cuota.fecha_vencimiento.isoformat() if cuota.fecha_vencimiento else None,
        "monto": to_finite_float(cuota.monto) if cuota.monto is not None else None,
    }
    if total_pendiente_pagar is not None:
        tp = to_finite_float(total_pendiente_pagar)
        if tp is not None:
            base_item["total_pendiente_pagar"] = tp

    if dias_atraso is not None:
        base_item["dias_atraso"] = dias_atraso
    if cuotas_atrasadas is not None:
        base_item["cuotas_atrasadas"] = cuotas_atrasadas

    # Si es para pestañas, agregar campos adicionales
    if for_tab:
        correos = emails_destino_desde_objeto(cliente)
        correo_prim = correos[0] if correos else (cliente.email or "").strip()
        base_item.update({
            "correo_1": correo_prim,
            "correo_2": correos[1] if len(correos) > 1 else None,
            "correo": correo_prim,
            "correos": correos,
            "telefono": (cliente.telefono or "").strip(),
            "modelo_vehiculo": None,
            "monto_cuota": to_finite_float(cuota.monto) if cuota.monto is not None else None,
            "estado": "PENDIENTE",
        })
        if cuota.fecha_vencimiento is not None:
            base_item["fecha_vencimiento_display"] = fecha_cuota_a_texto_es(
                cuota.fecha_vencimiento
            )

        if dias_antes_vencimiento is not None:
            base_item["dias_antes_vencimiento"] = dias_antes_vencimiento

    return base_item


def revision_manual_estado_por_prestamo_ids(
    db: Session, prestamo_ids: Sequence[int]
) -> Dict[int, Optional[str]]:
    """
    estado_revision desde revision_manual_prestamos (misma fuente que GET /prestamos).
    Claves normalizadas a minúsculas para alinear con PrestamosList / frontend.
    """
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return {}
    try:
        from app.models.revision_manual_prestamo import RevisionManualPrestamo

        q = select(
            RevisionManualPrestamo.prestamo_id,
            RevisionManualPrestamo.estado_revision,
        ).where(RevisionManualPrestamo.prestamo_id.in_(ids))
        out: Dict[int, Optional[str]] = {}
        for pid, est in db.execute(q).all():
            s = (est or "").strip().lower() if est else None
            out[int(pid)] = s if s else None
        return out
    except (ProgrammingError, OperationalError) as e:
        logger.warning(
            "revision_manual_prestamos no disponible al enriquecer notificaciones: %s",
            e,
        )
        return {}


def enriquecer_items_notificacion_revision_manual(
    db: Session, items: Sequence[dict]
) -> None:
    """Añade revision_manual_estado a cada ítem con prestamo_id (in-place)."""
    lst = [x for x in items if x]
    if not lst:
        return
    pids = [x.get("prestamo_id") for x in lst if x.get("prestamo_id") is not None]
    m = revision_manual_estado_por_prestamo_ids(db, pids)
    for it in lst:
        pid = it.get("prestamo_id")
        if pid is None:
            it["revision_manual_estado"] = None
        else:
            it["revision_manual_estado"] = m.get(int(pid))


# Funciones de compatibilidad (deprecated pero mantienen la API anterior)
def _item(
    cliente: Cliente,
    cuota: Cuota,
    dias_atraso: Optional[int] = None,
    cuotas_atrasadas: Optional[int] = None,
    total_pendiente_pagar: Optional[float] = None,
) -> dict:
    """
    Deprecated: usar format_cuota_item.
    Un registro para lista: nombre, cedula, y datos de cuota.
    """
    return format_cuota_item(
        cliente,
        cuota,
        dias_atraso=dias_atraso,
        cuotas_atrasadas=cuotas_atrasadas,
        for_tab=False,
        total_pendiente_pagar=total_pendiente_pagar,
    )


def _item_tab(
    cliente: Cliente,
    cuota: Cuota,
    dias_atraso: Optional[int] = None,
    dias_antes: Optional[int] = None,
    cuotas_atrasadas: Optional[int] = None,
    total_pendiente_pagar: Optional[float] = None,
) -> dict:
    """
    Deprecated: usar format_cuota_item con for_tab=True.
    Item con forma esperada por el frontend (pestañas): correo, telefono, estado, etc.
    """
    return format_cuota_item(
        cliente,
        cuota,
        dias_atraso=dias_atraso,
        cuotas_atrasadas=cuotas_atrasadas,
        dias_antes_vencimiento=dias_antes,
        for_tab=True,
        total_pendiente_pagar=total_pendiente_pagar,
    )
