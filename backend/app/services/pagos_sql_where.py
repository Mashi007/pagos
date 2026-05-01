"""Fragmentos SQLAlchemy reutilizados en pagos y servicios de cascada (sin depender del paquete API)."""

from sqlalchemy import and_, func, not_, or_

from app.models.pago import Pago


def _where_pago_excluido_operacion():
    """
    Estados que no cuentan como pagos operativos (anulados, duplicado declarado, etc.).
    Reutilizado en elegibilidad de cascada y en resúmenes diagnósticos.
    """
    est = func.upper(func.coalesce(func.trim(Pago.estado), ""))
    est_lower = func.lower(func.coalesce(func.trim(Pago.estado), ""))
    return or_(
        est.in_(["ANULADO_IMPORT", "DUPLICADO", "CANCELADO", "RECHAZADO", "REVERSADO"]),
        est.like("%ANUL%"),
        est.like("%REVERS%"),
        est_lower.in_(["cancelado", "rechazado"]),
    )


def _where_pago_elegible_reaplicacion_cascada():
    """
    Condicion SQLAlchemy para pagos que deben articularse al reconstruir la cascada
    (reset cuota_pagos + aplicar_pagos_pendientes_prestamo).

    Antes solo entraban conciliado o verificado_concordancia SI; muchos registros en PAGADO
    (carga, migracion, revision manual) quedaban fuera y el control 15 marcaba huérfanos.

    Incluye: conciliado, verificado SI, o estado PAGADO.
    Excluye: mismo criterio que totales de cartera en auditoria (_sql_fragment_pago_excluido_cartera).
    """
    est = func.upper(func.coalesce(func.trim(Pago.estado), ""))
    incl = or_(
        Pago.conciliado.is_(True),
        func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
        est == "PAGADO",
    )
    return and_(incl, not_(_where_pago_excluido_operacion()))
