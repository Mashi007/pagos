"""
Servicios para notificaciones de cuotas vencidas y en mora.
Centraliza la lógica de serialización y filtrado de cuotas.
Listados por pestaña: get_cuotas_pendientes_por_vencimientos (filtra en SQL por fechas);
build_cuotas_pendiente_2_dias_antes_items (solo estado PENDIENTE, vence en 3 días; incluye
    clientes al corriente — es el recordatorio preventivo de la pestaña «3 días antes»).
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.serializers import to_finite_float, to_finite_float_or_zero
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.utils.cliente_emails import (
    lista_correo_principal_notificaciones_desde_objeto,
    secundario_distinto_del_principal,
)
from app.services.comparar_abonos_drive_cuotas_service import (
    conciliacion_sheet_sync_flags_actual,
    refrescar_cache_comparar_abonos_totales_cuotas_bd,
)
from app.services.comparar_fecha_entrega_q_aprobacion_service import fecha_q_desde_cache_json
from app.constants.prestamo_estados import (
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
)
from app.services.notificaciones_exclusion_desistimiento import (
    sql_cliente_sin_desistimiento,
)
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

# Prejudicial (submenu Notificaciones «60 días o más» / ruta a-2-cuotas):
# Condiciones innegociables:
# - atraso calendario >= 60 días (fecha_vencimiento <= hoy − 60; encaja con menor-60 = 6–59)
# - 2 o más cuotas impagas que cumplan ese atraso
# Excluye prestamos LIQUIDADO/DESISTIMIENTO y clientes con algun prestamo DESISTIMIENTO.
# Permanecen todos los días mientras cumplan; salen al ponerse al día.
ESTADOS_CUOTA_VENCIDO_Y_MORA = ("VENCIDO", "MORA")  # legado / diagnóstico
MIN_DIAS_ATRASO_PREJUDICIAL = 60
PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60 = 2
# Alias de compatibilidad (imports antiguos): umbral de conteo = 2 cuotas con ≥60 días.
PREJUDICIAL_MIN_CUOTAS_VENCIDO_MORA = PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60



def _prestamo_no_excluido_notif():
    """Prestamo.estado no es LIQUIDADO/DESISTIMIENTO (case-insensitive)."""
    est = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    excl = tuple(str(e).strip().upper() for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF)
    return est.notin_(excl)


def _select_cuotas_pendientes_con_cliente():
    """Query base: cuota pendiente + cliente vía préstamo (sin filtro de fecha de vencimiento)."""
    return (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
        .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
        .where(_prestamo_no_excluido_notif())
        .where(sql_cliente_sin_desistimiento())
    )


def build_cuotas_pendiente_2_dias_antes_items(
    db: Session, fecha_referencia: Optional[date] = None
) -> List[dict]:
    """
    Cuotas con columna estado = PENDIENTE cuya fecha_vencimiento es exactamente
    hoy + 3 días (Caracas). Sin fecha_pago, saldo > tolerancia, préstamo no liquidado/desistimiento.

    Incluye también clientes al corriente (cuotas_atrasadas = 0): el aviso «3 días antes»
    es preventivo; antes se excluían y el envío quedaba vacío la mayoría de los días.
    Una fila por cuota (misma forma que otras pestañas de notificaciones).

    Nota: el nombre de función/ruta conserva «2_dias» por compatibilidad de API y config
    (PAGO_2_DIAS_ANTES_PENDIENTE); el criterio de fecha es hoy + 3.
    """
    hoy = fecha_referencia or hoy_negocio()
    fv_objetivo = hoy + timedelta(days=3)
    q = (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(Cuota.estado == "PENDIENTE")
        .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
        .where(Cuota.fecha_vencimiento == fv_objetivo)
        .where(_prestamo_no_excluido_notif())
        .where(sql_cliente_sin_desistimiento())
    )
    rows = db.execute(q).all()
    if not rows:
        return []
    pids = [c.prestamo_id for c, _ in rows]
    counts = contar_cuotas_atraso_por_prestamos(db, pids, fecha_referencia=hoy)
    totales = sum_saldo_pendiente_total_por_prestamos(db, pids)
    out: List[dict] = []
    for cuota, cliente in rows:
        ca = int(counts.get(cuota.prestamo_id, 0) or 0)
        tp = totales.get(cuota.prestamo_id)
        out.append(
            format_cuota_item(
                cliente,
                cuota,
                cuotas_atrasadas=ca,
                dias_antes_vencimiento=3,
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


def get_cuotas_pendientes_vencidas_hasta(
    db: Session,
    fecha_vencimiento_max: date,
    fecha_vencimiento_min: Optional[date] = None,
) -> List[Tuple[Cuota, Cliente]]:
    """
    Cuotas pendientes notificables con fecha_vencimiento <= fecha_vencimiento_max
    (p. ej. hoy − 6 para atraso >= 6 días). Si se pasa fecha_vencimiento_min,
    también exige fecha_vencimiento >= ese valor (p. ej. hoy − 59 para atraso <= 59).
    """
    q = _select_cuotas_pendientes_con_cliente().where(
        Cuota.fecha_vencimiento <= fecha_vencimiento_max
    )
    if fecha_vencimiento_min is not None:
        q = q.where(Cuota.fecha_vencimiento >= fecha_vencimiento_min)
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
        .where(_prestamo_no_excluido_notif())
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
        .where(_prestamo_no_excluido_notif())
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


# Listado / envío «menor a 60 días» (ruta atraso-10-dias / PAGO_10_DIAS_ATRASADO):
# préstamo con exactamente 1 cuota en mora y esa cuota con atraso entre 6 y 59 días
# calendario (fecha_vencimiento en [hoy − 59, hoy − 6]). Permanecen en el listado
# hasta que la cuota se pague o salga del rango. Con 0 o con 2+ cuotas atrasadas no aplica.
MIN_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS = 1
MAX_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS = 1
MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS = 6
MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS = 59


def prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(cuotas_atrasadas: int) -> bool:
    """True si el préstamo puede aparecer en el listado de mora menor a 60 días."""
    try:
        n = int(cuotas_atrasadas or 0)
    except (TypeError, ValueError):
        n = 0
    return MIN_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS <= n <= MAX_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS


def cuota_aplica_listado_10_dias_por_dias_atraso(dias_atraso: int) -> bool:
    """True si la cuota lleva entre 6 y 59 días de atraso calendario (menor a 60)."""
    try:
        n = int(dias_atraso or 0)
    except (TypeError, ValueError):
        n = 0
    return MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS <= n <= MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS


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
        "PAGO_10_DIAS_ATRASADO",
    ):
        if tipo == "PAGO_1_DIA_ATRASADO":
            target = hoy - timedelta(days=1)
            q = (
                select(Cuota, Cliente)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(Cuota.fecha_pago.is_(None))
                .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
                .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
                .where(_prestamo_no_excluido_notif())
                .where(sql_cliente_sin_desistimiento())
                .where(Cuota.fecha_vencimiento == target)
                .order_by(Cuota.id)
                .limit(120)
            )
            rows = db.execute(q).all()
            if not rows:
                return None
            pids = sorted({int(r[0].prestamo_id) for r in rows if r and r[0] is not None})
            counts = contar_cuotas_atraso_por_prestamos(db, pids, fecha_referencia=hoy)
            totales = sum_saldo_pendiente_total_por_prestamos(db, pids)
            cuota, cliente = rows[0][0], rows[0][1]
            return format_cuota_item(
                cliente,
                cuota,
                dias_atraso=1,
                cuotas_atrasadas=counts.get(cuota.prestamo_id, 0),
                for_tab=True,
                total_pendiente_pagar=totales.get(cuota.prestamo_id),
            )

        # PAGO_10_DIAS_ATRASADO: 1 cuota en mora con atraso 6..59 días (menor a 60).
        fv_max = hoy - timedelta(days=MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS)
        fv_min = hoy - timedelta(days=MAX_DIAS_ATRASO_PARA_LISTADO_10_DIAS)
        q = (
            select(Cuota, Cliente)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cuota.fecha_pago.is_(None))
            .where(CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF)
            .where(SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION)
            .where(_prestamo_no_excluido_notif())
            .where(sql_cliente_sin_desistimiento())
            .where(Cuota.fecha_vencimiento <= fv_max)
            .where(Cuota.fecha_vencimiento >= fv_min)
            .order_by(Cuota.fecha_vencimiento.asc(), Cuota.id.asc())
            .limit(200)
        )
        rows = db.execute(q).all()
        if not rows:
            return None
        pids = sorted({int(r[0].prestamo_id) for r in rows if r and r[0] is not None})
        counts = contar_cuotas_atraso_por_prestamos(db, pids, fecha_referencia=hoy)
        totales = sum_saldo_pendiente_total_por_prestamos(db, pids)
        for row in rows:
            cuota, cliente = row[0], row[1]
            ca = counts.get(cuota.prestamo_id, 0)
            if not prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(ca):
                continue
            fv = cuota.fecha_vencimiento
            if not fv:
                continue
            dias_atraso = (hoy - fv).days
            if not cuota_aplica_listado_10_dias_por_dias_atraso(dias_atraso):
                continue
            return format_cuota_item(
                cliente,
                cuota,
                dias_atraso=dias_atraso,
                cuotas_atrasadas=ca,
                for_tab=True,
                total_pendiente_pagar=totales.get(cuota.prestamo_id),
            )
        return None

    if tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
        items = build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=hoy)
        return items[0] if items else None

    if tipo == "PREJUDICIAL":
        # Titular: prestamos.cliente_id. Al menos 2 cuotas impagas con atraso >= 60 días.
        fv_max = hoy - timedelta(days=MIN_DIAS_ATRASO_PREJUDICIAL)
        subq = (
            select(Prestamo.cliente_id, func.count(Cuota.id).label("total"))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(
                Cuota.fecha_pago.is_(None),
                CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
                Cuota.fecha_vencimiento.isnot(None),
                Cuota.fecha_vencimiento <= fv_max,
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
                _prestamo_no_excluido_notif(),
                sql_cliente_sin_desistimiento(),
            )
            .group_by(Prestamo.cliente_id)
            .having(func.count(Cuota.id) >= PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60)
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
                Prestamo.cliente_id == cliente_id,
                Cuota.fecha_pago.is_(None),
                CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
                Cuota.fecha_vencimiento.isnot(None),
                Cuota.fecha_vencimiento <= fv_max,
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
                _prestamo_no_excluido_notif(),
                sql_cliente_sin_desistimiento(),
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
        dias_atraso_prej = None
        fv_ref = getattr(cuota_ref, "fecha_vencimiento", None)
        if fv_ref is not None:
            dias_atraso_prej = (hoy - fv_ref).days
        item = format_cuota_item(
            cliente,
            cuota_ref,
            dias_atraso=dias_atraso_prej,
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
        # Política de dos emails:
        #   correo_1 / correo = email principal (campo `email` del cliente, NOT NULL). Es el destino
        #   del envío. El campo `correos` lo expone en lista para la lógica de despacho.
        #   correo_2 = email secundario (campo `email_secundario`, nullable). Solo para referencia
        #   en el listado y el UI; el envío de notificaciones usa únicamente correo_1.
        #   Si correo_2 coincide con correo_1 o está vacío, se retorna None.
        correos = lista_correo_principal_notificaciones_desde_objeto(cliente)
        correo_prim = correos[0] if correos else (cliente.email or "").strip()
        _, correo_sec = secundario_distinto_del_principal(
            getattr(cliente, "email", None),
            getattr(cliente, "email_secundario", None),
        )
        base_item.update({
            "correo_1": correo_prim if correo_prim and "@" in correo_prim else None,
            "correo_2": correo_sec if correo_sec and "@" in correo_sec else None,
            "correo": correo_prim if correo_prim and "@" in correo_prim else "",
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


def alinear_items_contacto_titular_prestamo(db: Session, items: Sequence[dict]) -> None:
    """
    Alinea en sitio nombre, cédula, correo y teléfono del ítem con el titular real del préstamo
    (prestamos.cliente_id). Si ``cuotas.cliente_id`` quedó denormalizado distinto del titular,
    el listado puede mostrar (y el envío usar) el contacto de una persona y los montos de otra.

    Se invoca antes del bucle de envío por lote; solo carga clientes cuando detecta divergencia.
    """
    lst = [it for it in items if it and it.get("prestamo_id")]
    if not lst:
        return
    pids_uniq: List[int] = []
    for it in lst:
        try:
            pids_uniq.append(int(it["prestamo_id"]))
        except (TypeError, ValueError):
            continue
    pids_uniq = sorted({p for p in pids_uniq})
    if not pids_uniq:
        return
    rows = db.execute(
        select(Prestamo.id, Prestamo.cliente_id).where(Prestamo.id.in_(pids_uniq))
    ).all()
    titular_por_pid: Dict[int, int] = {int(pid): int(cid) for pid, cid in rows if cid is not None}

    cids_needed: set[int] = set()
    for it in lst:
        try:
            ip = int(it["prestamo_id"])
        except (TypeError, ValueError):
            continue
        tid = titular_por_pid.get(ip)
        if tid is None:
            continue
        cur = it.get("cliente_id")
        try:
            cur_i = int(cur) if cur is not None else None
        except (TypeError, ValueError):
            cur_i = None
        if cur_i != tid:
            cids_needed.add(tid)

    if not cids_needed:
        return

    clientes = {
        c.id: c
        for c in db.scalars(select(Cliente).where(Cliente.id.in_(sorted(cids_needed)))).all()
    }

    for it in lst:
        try:
            ip = int(it["prestamo_id"])
        except (TypeError, ValueError):
            continue
        tid = titular_por_pid.get(ip)
        if tid is None:
            continue
        cur = it.get("cliente_id")
        try:
            cur_i = int(cur) if cur is not None else None
        except (TypeError, ValueError):
            cur_i = None
        if cur_i == tid:
            continue
        cli = clientes.get(tid)
        if not cli:
            continue
        logger.warning(
            "[notif_alineacion] prestamo_id=%s: cliente_id en fila=%s != titular del préstamo=%s; "
            "se corrige contacto al titular antes del envío.",
            ip,
            cur_i,
            tid,
        )
        it["cliente_id"] = cli.id
        it["nombre"] = cli.nombres or ""
        it["cedula"] = cli.cedula or ""
        correos = lista_correo_principal_notificaciones_desde_objeto(cli)
        correo_prim = correos[0] if correos else (cli.email or "").strip()
        _, correo_sec = secundario_distinto_del_principal(
            getattr(cli, "email", None),
            getattr(cli, "email_secundario", None),
        )
        it["correo_1"] = correo_prim if correo_prim and "@" in correo_prim else None
        it["correo_2"] = correo_sec if correo_sec and "@" in correo_sec else None
        it["correo"] = correo_prim if correo_prim and "@" in correo_prim else ""
        it["correos"] = correos
        it["telefono"] = (cli.telefono or "").strip()
        # El PDF/carta podría haberse armado con el titular incorrecto; se recalcula en el envío.
        it.pop("contexto_cobranza", None)
        it.pop("_correlativo_envio", None)


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


def enriquecer_items_abonos_drive_cuotas_cache(
    db: Session, items: Sequence[dict]
) -> None:
    """
    Adjunta comparar_abonos_drive_cuotas desde prestamos.abonos_drive_cuotas_cache (in-place).

    Ajusta en memoria el total pagado en cuotas y la diferencia con el total actual en BD (sin
    releer la hoja), y fusiona flags de antigüedad de sync de CONCILIACIÓN, para alinear listados
    y filtros con el GET en vivo del modal.
    """
    lst = [x for x in items if x]
    if not lst:
        return
    ids: List[int] = []
    for it in lst:
        pid = it.get("prestamo_id")
        if pid is None:
            continue
        try:
            ids.append(int(pid))
        except (TypeError, ValueError):
            continue
    uniq = sorted({i for i in ids})
    if not uniq:
        for it in lst:
            it["comparar_abonos_drive_cuotas"] = None
        return
    q = select(Prestamo.id, Prestamo.abonos_drive_cuotas_cache).where(Prestamo.id.in_(uniq))
    by_id: Dict[int, Any] = {}
    for pid, cache in db.execute(q).all():
        by_id[int(pid)] = cache

    tot_rows = db.execute(
        select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.total_pagado), 0))
        .where(Cuota.prestamo_id.in_(uniq))
        .group_by(Cuota.prestamo_id)
    ).all()
    tot_by_pid: Dict[int, float] = {}
    for pid, s in tot_rows:
        tot_by_pid[int(pid)] = to_finite_float_or_zero(s)

    sync_flags = conciliacion_sheet_sync_flags_actual(db)

    for it in lst:
        pid = it.get("prestamo_id")
        if pid is None:
            it["comparar_abonos_drive_cuotas"] = None
        else:
            try:
                ip = int(pid)
            except (TypeError, ValueError):
                it["comparar_abonos_drive_cuotas"] = None
                continue
            raw = by_id.get(ip)
            if raw is None:
                it["comparar_abonos_drive_cuotas"] = None
            else:
                total_fresh = float(tot_by_pid.get(ip, 0.0))
                adj = refrescar_cache_comparar_abonos_totales_cuotas_bd(raw, total_fresh)
                if isinstance(adj, dict):
                    adj.update(sync_flags)
                it["comparar_abonos_drive_cuotas"] = adj


def _fecha_aprob_solo_fecha(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _merge_comparar_fecha_cache_vivo(p_row: Prestamo, cache: Any) -> Any:
    """
    Ajusta en el dict de caché `puede_aplicar`, `diferencia_dias`, etc. según la fecha_aprobacion **actual**
    en BD (la hoja manda si Q difiere; no se usa fecha_requerimiento como bloqueo del indicador).
    """
    if not isinstance(cache, dict):
        return cache
    out = dict(cache)
    fq = fecha_q_desde_cache_json(out)
    if fq is None:
        return out
    fa = _fecha_aprob_solo_fecha(getattr(p_row, "fecha_aprobacion", None))
    if fa is None:
        return out
    if fq == fa:
        out["puede_aplicar"] = False
        out["diferencia_dias"] = 0
        out["correccion_desde_q_anterior_bd"] = False
        out["coincide_calendario"] = True
        out["coincide_aproximado"] = True
        out["indicador"] = "no"
        out["fecha_aprobacion_sistema"] = fa.isoformat()
        return out
    out["puede_aplicar"] = True
    out["diferencia_dias"] = int((fq - fa).days)
    out["correccion_desde_q_anterior_bd"] = fq < fa
    out["coincide_calendario"] = False
    out["coincide_aproximado"] = False
    out["fecha_aprobacion_sistema"] = fa.isoformat()
    out["indicador"] = "si"
    return out


def enriquecer_items_fecha_entrega_q_aprobacion_cache(
    db: Session, items: Sequence[dict]
) -> None:
    """Adjunta comparar_fecha_entrega_q_aprobacion desde caché, afinado con la aprobación actual en BD."""
    lst = [x for x in items if x]
    if not lst:
        return
    ids: List[int] = []
    for it in lst:
        pid = it.get("prestamo_id")
        if pid is None:
            continue
        try:
            ids.append(int(pid))
        except (TypeError, ValueError):
            continue
    uniq = sorted({i for i in ids})
    if not uniq:
        for it in lst:
            it["comparar_fecha_entrega_q_aprobacion"] = None
        return
    rows = list(db.execute(select(Prestamo).where(Prestamo.id.in_(uniq))).scalars().all() or [])
    by_row: Dict[int, Prestamo] = {int(p.id): p for p in rows}
    for it in lst:
        pid = it.get("prestamo_id")
        if pid is None:
            it["comparar_fecha_entrega_q_aprobacion"] = None
            continue
        try:
            ip = int(pid)
        except (TypeError, ValueError):
            it["comparar_fecha_entrega_q_aprobacion"] = None
            continue
        prow = by_row.get(ip)
        if prow is None:
            it["comparar_fecha_entrega_q_aprobacion"] = None
            continue
        raw_cache = getattr(prow, "fecha_entrega_q_aprobacion_cache", None)
        if raw_cache is None:
            it["comparar_fecha_entrega_q_aprobacion"] = None
        else:
            it["comparar_fecha_entrega_q_aprobacion"] = _merge_comparar_fecha_cache_vivo(prow, raw_cache)


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
    enriquecer_items_abonos_drive_cuotas_cache(db, lst)
    enriquecer_items_fecha_entrega_q_aprobacion_cache(db, lst)


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
