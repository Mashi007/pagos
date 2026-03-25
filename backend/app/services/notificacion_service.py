"""
Servicios para notificaciones de cuotas vencidas y en mora.
Centraliza la lógica de serialización y filtrado de cuotas.
Una sola fuente de datos: get_cuotas_pendientes_con_cliente(db) para listado y envío.
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo


def get_cuotas_pendientes_con_cliente(db: Session) -> List[Tuple[Cuota, Cliente]]:
    """
    Fuente única: cuotas no pagadas (fecha_pago nula) con su cliente vía préstamo.
    Excluye préstamos en estado LIQUIDADO (alineado con tabla prestamos).

    Al registrar pagos que aplican a cuotas y fijan fecha_pago, esas cuotas dejan
    de aparecer aquí: las listas de notificaciones reflejan el estado actual de la BD
    en cada lectura (no dependen de un batch nocturno para “quitar” mora pagada).

    Usado por get_clientes_retrasados y get_notificaciones_tabs_data para evitar duplicar consulta.
    """
    q = (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(Prestamo.estado != "LIQUIDADO")
    )
    rows = db.execute(q).all()
    return [(row[0], row[1]) for row in rows]


def get_primer_item_ejemplo_paquete_prueba(db: Session, tipo: str) -> Optional[dict]:
    """
    Primer item real para prueba/diagnostico de paquete sin cargar todas las cuotas.
    Misma semantica que el primer elemento de get_notificaciones_tabs_data por criterio.
    """
    tipo = (tipo or "").strip()
    hoy = date.today()

    if tipo in ("PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO"):
        dias_map = {
            "PAGO_1_DIA_ATRASADO": 1,
            "PAGO_3_DIAS_ATRASADO": 3,
            "PAGO_5_DIAS_ATRASADO": 5,
        }
        dias = dias_map[tipo]
        target = hoy - timedelta(days=dias)
        q = (
            select(Cuota, Cliente)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cuota.fecha_pago.is_(None))
            .where(Prestamo.estado != "LIQUIDADO")
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
            .where(
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < hoy,
                Cuota.cliente_id.isnot(None),
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
            .where(
                Cuota.cliente_id == cliente_id,
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < hoy,
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
