"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

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
