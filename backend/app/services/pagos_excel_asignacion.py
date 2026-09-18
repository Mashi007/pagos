# -*- coding: utf-8 -*-
"""Asignación de préstamo en carga masiva Excel."""

from typing import Any, Optional, Sequence


def prestamo_id_unico_desde_activos(prestamos_activos: Sequence[Any]) -> Optional[int]:
    """Id when the cédula has exactly one APROBADO loan.

    ``select(Prestamo.id).scalars().all()`` yields ints. Treating the value as a
    Row (``activos[0][0]``) raises TypeError and the outer Excel upload handler
    rolls back the whole lote with HTTP 500.
    """
    if len(prestamos_activos) != 1:
        return None
    pid = prestamos_activos[0]
    if isinstance(pid, (tuple, list)):
        pid = pid[0]
    try:
        return int(pid)
    except (TypeError, ValueError):
        return None
