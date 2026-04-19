"""Estado del pago según articulación a cuotas (cascada)."""


def _estado_pago_tras_aplicar_cascada(cuotas_completadas: int, cuotas_parciales: int) -> str:
    """
    Estado del pago según articulación real a cuotas.

    Solo PAGADO si hubo aplicación (al menos un registro en cuota_pagos).

    Evita marcar PAGADO sin cuota_pagos (inconsistencia y bloqueo del job en cascada).
    """
    if cuotas_completadas > 0 or cuotas_parciales > 0:
        return "PAGADO"
    return "PENDIENTE"
