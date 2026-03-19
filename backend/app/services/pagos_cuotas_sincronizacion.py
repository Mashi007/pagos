"""Sincroniza pagos conciliados pendientes con filas en cuotas (misma regla que GET /prestamos/{id}/cuotas)."""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session


def sincronizar_pagos_pendientes_a_prestamos(db: Session, prestamo_ids: List[int]) -> int:
    """
    Por cada préstamo, aplica a cuotas los pagos que aún no tienen fila en cuota_pagos.
    Hace commit si al menos un pago fue procesado. Retorna cuántos pagos recibieron aplicación (suma de retornos internos).
    """
    if not prestamo_ids:
        return 0
    from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo

    n = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
    if n > 0:
        db.commit()
    return n
