"""
Servicios para notificaciones de cuotas vencidas y en mora.
Centraliza la lógica de serialización y filtrado de cuotas.
"""
from datetime import date
from typing import Optional
from app.models.cliente import Cliente
from app.models.cuota import Cuota


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
            "prestamo_id": cuota.prestamo_id,  # Corregir: usar prestamo_id, no cliente.id
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
