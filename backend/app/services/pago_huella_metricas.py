"""
Metricas en memoria (proceso) para rechazos por huella funcional de pagos.
Se reinician al reiniciar el servidor; sirven para monitoreo operativo junto al KPI en BD.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_rechazos_huella_funcional = 0
_ultimo_rechazo_utc: str | None = None


def registrar_rechazo_huella_funcional() -> None:
    global _rechazos_huella_funcional, _ultimo_rechazo_utc
    with _lock:
        _rechazos_huella_funcional += 1
        _ultimo_rechazo_utc = datetime.now(timezone.utc).isoformat()


def snapshot_rechazos_huella_funcional() -> dict[str, Any]:
    with _lock:
        return {
            "rechazos_409_huella_funcional_desde_arranque": _rechazos_huella_funcional,
            "ultimo_rechazo_huella_utc": _ultimo_rechazo_utc,
        }
