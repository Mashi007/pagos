"""Contadores en memoria para OTP Finiquito (por proceso). Útil para operación y depuración."""

from __future__ import annotations

from threading import Lock
from typing import Any

_lock = Lock()

_counts: dict[str, int] = {
    "solicitudes_recibidas": 0,
    "usuario_no_encontrado": 0,
    "envio_bloqueado_config_email": 0,
    "envio_smtp_ok": 0,
    "envio_smtp_fallo": 0,
    "rate_limit_429": 0,
    "verificar_rate_limit_429": 0,
    "registro_rate_limit_429": 0,
}


def finiquito_otp_bump(key: str, n: int = 1) -> None:
    if n <= 0:
        return
    with _lock:
        _counts[key] = _counts.get(key, 0) + n


def finiquito_otp_snapshot() -> dict[str, Any]:
    with _lock:
        return dict(_counts)


def finiquito_otp_reset() -> None:
    """Tests o mantenimiento manual."""
    with _lock:
        for k in _counts:
            _counts[k] = 0
