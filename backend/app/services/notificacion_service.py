"""
Servicios para notificaciones de cuotas vencidas y en mora.
Centraliza la lógica de serialización y filtrado de cuotas.
Listados por pestaña: get_cuotas_pendientes_por_vencimientos (filtra en SQL por fechas).
"""
from datetime import date, timedelta
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio

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
        return format_cuota_item(cliente, cuota, dias_atraso=dias, for_tab=True)

    if tipo == "PREJUDICIAL":
        subq = (
            select(Cuota.cliente_id, func.count(Cuota.id).label("total"))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(
                Cuota.fecha_pago.is_(None),
                CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
                Cuota.fecha_vencimiento < hoy,
                Cuota.cliente_id.isnot(None),
                SALDO_PENDIENTE_CUOTA > TOL_SALDO_CUOTA_NOTIFICACION,
                ~Prestamo.estado.in_(("LIQUIDADO", "DESISTIMIENTO")),
            )
            .group_by(Cuota.cliente_id)
            .having(func.count(Cuota.id) >= 3)
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
                CUOTA_ESTADO_NO_PAGADA_PARA_NOTIF,
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
        item = format_cuota_item(cliente, cuota_ref, for_tab=True)
        item["total_cuotas_atrasadas"] = total_cuotas
        return item

    return None


def format_cuota_item(
    cliente: Cliente, 
    cuota: Cuota, 
    dias_atraso: Optional[int] = None,
    dias_antes_vencimiento: Optional[int] = None,
    for_tab: bool = False
) -> dict:
    """
    Formatea un registro de cliente+cuota para la lista de notificaciones.
    
    Args:
        cliente: Objeto Cliente
        cuota: Objeto Cuota
        dias_atraso: Días de atraso (si aplica)
        dias_antes_vencimiento: Días antes del vencimiento (si aplica)
        for_tab: Si True, incluye campos adicionales para las pestañas del frontend
    
    Returns:
        Dict con datos formateados para el frontend
    """
    base_item = {
        "cliente_id": cliente.id,
        "nombre": cliente.nombres or "",
        "cedula": cliente.cedula or "",
        "prestamo_id": cuota.prestamo_id,
        "numero_cuota": cuota.numero_cuota,
        "fecha_vencimiento": cuota.fecha_vencimiento.isoformat() if cuota.fecha_vencimiento else None,
        "monto": float(cuota.monto) if cuota.monto is not None else None,
    }
    
    if dias_atraso is not None:
        base_item["dias_atraso"] = dias_atraso
    
    # Si es para pestañas, agregar campos adicionales
    if for_tab:
        base_item.update({
            "correo": (cliente.email or "").strip(),
            "telefono": (cliente.telefono or "").strip(),
            "modelo_vehiculo": None,
            "monto_cuota": float(cuota.monto) if cuota.monto is not None else None,
            "estado": "PENDIENTE",
        })
        
        if dias_antes_vencimiento is not None:
            base_item["dias_antes_vencimiento"] = dias_antes_vencimiento
    
    return base_item


# Funciones de compatibilidad (deprecated pero mantienen la API anterior)
def _item(cliente: Cliente, cuota: Cuota, dias_atraso: Optional[int] = None) -> dict:
    """
    Deprecated: usar format_cuota_item.
    Un registro para lista: nombre, cedula, y datos de cuota.
    """
    return format_cuota_item(cliente, cuota, dias_atraso=dias_atraso, for_tab=False)


def _item_tab(cliente: Cliente, cuota: Cuota, dias_atraso: Optional[int] = None, dias_antes: Optional[int] = None) -> dict:
    """
    Deprecated: usar format_cuota_item con for_tab=True.
    Item con forma esperada por el frontend (pestañas): correo, telefono, estado, etc.
    """
    return format_cuota_item(cliente, cuota, dias_atraso=dias_atraso, dias_antes_vencimiento=dias_antes, for_tab=True)
