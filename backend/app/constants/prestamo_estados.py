"""Codigos de estado de prestamo alineados con public.prestamos.estado y CHECK en BD."""

from typing import Optional

# Cliente / operacion desistio del credito antes de concluir; prestamo queda congelado (solo lectura).
ESTADO_PRESTAMO_DESISTIMIENTO = "DESISTIMIENTO"
# Alias legacy en datos antiguos; misma regla de exclusion que DESISTIMIENTO.
ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES = frozenset(
    {ESTADO_PRESTAMO_DESISTIMIENTO, "DESESTIMADO", "DESISTIDO"}
)


def prestamo_estado_es_desistimiento(estado: Optional[str]) -> bool:
    """True si el prestamo esta congelado por desistimiento (incluye alias legacy)."""
    return (estado or "").strip().upper() in ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES

# Prestamos que deben tener fecha_aprobacion persistida (no NULL).
ESTADOS_PRESTAMO_EXIGEN_FECHA_APROBACION = frozenset(
    {"APROBADO", "DESEMBOLSADO", "LIQUIDADO"}
)


def prestamo_estado_exige_fecha_aprobacion(estado: Optional[str]) -> bool:
    if not estado:
        return False
    return estado.strip().upper() in ESTADOS_PRESTAMO_EXIGEN_FECHA_APROBACION

# Prestamos excluidos de listas, mora/KPIs y CUALQUIER envio de notificacion al cliente.
ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF = (
    "LIQUIDADO",
    *sorted(ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES),
)

# Envio: corte por prestamo_id (LIQUIDADO/DESISTIMIENTO) + regla global por cliente
# (DESISTIMIENTO o sin cartera activa): app.services.notificaciones_exclusion_desistimiento
