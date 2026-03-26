"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)

# Alineado con notificacion_service (lista mora / clientes-retrasados)
_TOL_SALDO_NOTIF = 0.01
_ESTADOS_CUOTA_PAGADA = ("PAGADO", "PAGO_ADELANTADO", "PAGADA")
_SALDO_PEND_CUOTA = func.coalesce(Cuota.monto, 0) - func.coalesce(Cuota.total_pagado, 0)
_CUOTA_NO_PAGADA_NOTIF = or_(
    Cuota.estado.is_(None),
    ~Cuota.estado.in_(_ESTADOS_CUOTA_PAGADA),
)


def _prestamo_ids_con_cuotas_pendientes_para_notif(db: Session) -> List[int]:
    """Prestamos con al menos una cuota que entraria en get_cuotas_pendientes_con_cliente (sin sync)."""
    q = (
        select(Cuota.prestamo_id)
        .distinct()
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(Cuota.fecha_pago.is_(None))
        .where(_CUOTA_NO_PAGADA_NOTIF)
        .where(_SALDO_PEND_CUOTA > _TOL_SALDO_NOTIF)
        .where(Prestamo.estado != "LIQUIDADO")
    )
    rows = db.execute(q).scalars().all()
    return sorted({int(x) for x in rows if x is not None})


def sincronizar_pagos_pendientes_a_prestamos(
    db: Session,
    prestamo_ids: List[int],
    *,
    ejecutar_cascada: bool = True,
) -> int:
    """
    Por cada prestamo:
    1) Aplica pagos conciliados que aun no tienen fila en cuota_pagos.
    2) Si ejecutar_cascada=True y la integridad total_pagado vs cuota_pagos falla,
       reaplica en cascada (misma logica que POST reaplicar-cascada-aplicacion).

    ejecutar_cascada=False acelera GET clientes-retrasados: solo aplica huérfanos incrementales;
    la cascada completa sigue ocurriendo al abrir GET /prestamos/{id}/cuotas o estado de cuenta.

    Hace commit si hubo aplicacion incremental o reaplicacion en cascada.
    Retorna cuantos pagos recibieron aplicacion incremental (compatibilidad con llamadas existentes).
    """
    if not prestamo_ids:
        return 0
    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo

    if ejecutar_cascada:
        from app.services.pagos_cuotas_reaplicacion import (
            prestamo_requiere_correccion_cascada,
            reset_y_reaplicar_cascada_prestamo,
        )

    n = 0
    cascadas = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
        db.flush()
        if ejecutar_cascada and prestamo_requiere_correccion_cascada(db, pid):
            r = reset_y_reaplicar_cascada_prestamo(db, pid)
            if r.get("ok"):
                cascadas += 1
                logger.info(
                    "reaplicacion cascada auto prestamo_id=%s pagos_reaplicados=%s",
                    pid,
                    r.get("pagos_reaplicados"),
                )
            else:
                logger.warning(
                    "reaplicacion cascada auto omitida prestamo_id=%s error=%s",
                    pid,
                    r.get("error"),
                )
    if n > 0 or cascadas > 0:
        db.commit()
    return n


def sincronizar_pagos_pendientes_para_listado_notificaciones(db: Session) -> int:
    """
    Antes de armar listas de mora/envíos, aplica pagos conciliados que aún no tienen
    fila en cuota_pagos, solo en préstamos que tienen cuotas pendientes según la misma
    regla que la lista de notificaciones.

    La version anterior sincronizaba *todos* los préstamos con pagos huérfanos en la BD,
    lo que en produccion podia superar el timeout HTTP (60s) en GET clientes-retrasados.

    No ejecuta reaplicacion en cascada por préstamo (muy costosa en CPU/BD); solo aplica
    pagos conciliados sin fila en cuota_pagos. La cascada sigue al consultar cuotas del préstamo.
    """
    candidatos = _prestamo_ids_con_cuotas_pendientes_para_notif(db)
    if not candidatos:
        return 0

    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    conciliado_o_si = or_(
        Pago.conciliado.is_(True),
        func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
    )

    # Evitar IN gigantes en PostgreSQL
    chunk_size = 400
    total_incremental = 0
    for i in range(0, len(candidatos), chunk_size):
        chunk = candidatos[i : i + chunk_size]
        raw = db.execute(
            select(Pago.prestamo_id)
            .where(
                Pago.prestamo_id.in_(chunk),
                conciliado_o_si,
                Pago.monto_pagado > 0,
                ~Pago.id.in_(subq),
            )
            .distinct()
        ).scalars().all()
        ids = sorted({int(x) for x in raw if x is not None})
        if ids:
            total_incremental += sincronizar_pagos_pendientes_a_prestamos(
                db, ids, ejecutar_cascada=False
            )
    return total_incremental
