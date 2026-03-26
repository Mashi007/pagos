"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago

logger = logging.getLogger(__name__)


def sincronizar_pagos_pendientes_a_prestamos(db: Session, prestamo_ids: List[int]) -> int:
    """
    Por cada prestamo:
    1) Aplica pagos conciliados que aun no tienen fila en cuota_pagos.
    2) Si la integridad total_pagado vs cuota_pagos falla o quedan pagos conciliados
       sin articulacion, reaplica en cascada (misma logica que POST reaplicar-cascada-aplicacion).

    Hace commit si hubo aplicacion incremental o reaplicacion en cascada.
    Retorna cuantos pagos recibieron aplicacion incremental (compatibilidad con llamadas existentes).
    """
    if not prestamo_ids:
        return 0
    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo
    from app.services.pagos_cuotas_reaplicacion import (
        prestamo_requiere_correccion_cascada,
        reset_y_reaplicar_cascada_prestamo,
    )

    n = 0
    cascadas = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
        db.flush()
        if prestamo_requiere_correccion_cascada(db, pid):
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
    fila en cuota_pagos (mismo criterio que aplicar_pagos_pendientes_prestamo).

    GET /prestamos/{id}/cuotas ya hace esto por préstamo; sin este paso, notificaciones
    pueden mostrar cuotas en atraso mientras la amortización ya muestra Pagado.
    """
    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    raw = db.execute(
        select(Pago.prestamo_id)
        .where(
            Pago.prestamo_id.isnot(None),
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .distinct()
    ).scalars().all()
    ids = sorted({int(x) for x in raw if x is not None})
    if not ids:
        return 0
    return sincronizar_pagos_pendientes_a_prestamos(db, ids)
