"""
Rate limiting para endpoints públicos del módulo Cobros (formulario reporte de pago).
Evita abuso por IP sin requerir autenticación.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException

# Validar cédula: 30 solicitudes por minuto por IP
VALIDAR_CEDULA_WINDOW_SEC = 60
VALIDAR_CEDULA_MAX = 30

# Enviar reporte: 5 por hora por IP (evita spam de reportes)
ENVIAR_REPORTE_WINDOW_SEC = 3600
ENVIAR_REPORTE_MAX = 5

_validar_attempts: dict[str, list[float]] = defaultdict(list)
_enviar_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def get_client_ip(request: Request) -> str:
    """IP del cliente (respeta X-Forwarded-For si está detrás de proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit_validar_cedula(ip: str) -> None:
    """Lanza 429 si se supera el límite de validar-cedula por IP."""
    with _lock:
        now = time.time()
        attempts = _validar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < VALIDAR_CEDULA_WINDOW_SEC]
        if len(attempts) >= VALIDAR_CEDULA_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas consultas. Espere un minuto e intente de nuevo.",
            )
        attempts.append(now)


def check_rate_limit_enviar_reporte(ip: str) -> None:
    """Lanza 429 si se supera el límite de enviar-reporte por IP."""
    with _lock:
        now = time.time()
        attempts = _enviar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < ENVIAR_REPORTE_WINDOW_SEC]
        if len(attempts) >= ENVIAR_REPORTE_MAX:
            raise HTTPException(
                status_code=429,
                detail="Ha alcanzado el límite de envíos por hora. Intente más tarde.",
            )
        attempts.append(now)
