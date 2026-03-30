"""Codigos de estado de prestamo alineados con public.prestamos.estado y CHECK en BD."""

# Cliente / operacion desistio del credito antes de concluir; prestamo queda congelado (solo lectura).
ESTADO_PRESTAMO_DESISTIMIENTO = "DESISTIMIENTO"

# Prestamos que no deben entrar en listas de cobranza / notificaciones por cuota (misma idea que excluir LIQUIDADO).
ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF = ("LIQUIDADO", ESTADO_PRESTAMO_DESISTIMIENTO)

# Regla global adicional (cualquier prestamo DESISTIMIENTO): ver
# app.services.notificaciones_exclusion_desistimiento.cliente_tiene_prestamo_desistimiento
