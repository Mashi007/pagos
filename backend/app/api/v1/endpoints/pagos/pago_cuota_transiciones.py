"""Validación de transiciones de estado de cuota en cascada de pagos."""


def _validar_transicion_estado_cuota(estado_anterior: str, estado_nuevo: str) -> bool:
    """
    Valida transiciones permitidas entre estados de cuota.

    Transiciones permitidas:
    PENDIENTE -> PAGADO, PAGO_ADELANTADO, ...
    """
    transiciones_permitidas = {
        "PENDIENTE": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PENDIENTE",
            "PARCIAL",
        ],
        "PARCIAL": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PARCIAL",
            "PENDIENTE",
        ],
        "VENCIDO": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],
        "MORA": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],
        "PAGO_ADELANTADO": ["PAGADO", "PAGO_ADELANTADO"],
        "PAGADO": ["PAGADO"],
    }
    return estado_nuevo in transiciones_permitidas.get(estado_anterior, [])
