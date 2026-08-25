# -*- coding: utf-8 -*-
"""Coordina DELETE de pagos con cascada BG de revisión manual (evita contención en BD)."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Optional

_lock = threading.Lock()
_eliminacion_por_prestamo: dict[int, int] = {}


def eliminacion_activa(prestamo_id: int) -> bool:
    with _lock:
        return int(_eliminacion_por_prestamo.get(int(prestamo_id), 0)) > 0


@contextmanager
def eliminacion_context(prestamo_id: Optional[int]):
    """Marca eliminación en curso para que no arranque cascada BG concurrente."""
    if prestamo_id is None:
        yield
        return
    pid = int(prestamo_id)
    with _lock:
        _eliminacion_por_prestamo[pid] = _eliminacion_por_prestamo.get(pid, 0) + 1
    try:
        yield
    finally:
        with _lock:
            n = _eliminacion_por_prestamo.get(pid, 0) - 1
            if n <= 0:
                _eliminacion_por_prestamo.pop(pid, None)
            else:
                _eliminacion_por_prestamo[pid] = n
