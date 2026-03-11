"""
Rate limiting para endpoints públicos del módulo Cobros (formulario reporte de pago).
Evita abuso por IP sin requerir autenticación.
Si REDIS_URL está configurada, usa Redis para límites distribuidos entre instancias;
si no, usa memoria por proceso.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException

try:
    from app.core.rate_limit_store import get_redis_client, check_rate_limit_redis
except ImportError:
    get_redis_client = None
    check_rate_limit_redis = None

# Validar cédula: 30 solicitudes por minuto por IP
VALIDAR_CEDULA_WINDOW_SEC = 60
VALIDAR_CEDULA_MAX = 30

# Enviar reporte: 5 por hora por IP (evita spam de reportes)
ENVIAR_REPORTE_WINDOW_SEC = 3600
ENVIAR_REPORTE_MAX = 5

# Estado de cuenta público: validar 30/min, solicitar PDF 5/hora por IP
ESTADO_CUENTA_VALIDAR_WINDOW_SEC = 60
ESTADO_CUENTA_VALIDAR_MAX = 30
ESTADO_CUENTA_SOLICITAR_WINDOW_SEC = 3600
ESTADO_CUENTA_SOLICITAR_MAX = 5
ESTADO_CUENTA_VERIFICAR_WINDOW_SEC = 900
ESTADO_CUENTA_VERIFICAR_MAX = 15

_validar_attempts: dict[str, list[float]] = defaultdict(list)
_enviar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_validar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_verificar_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()



def check_rate_limit_estado_cuenta_verificar(ip: str) -> None:
    if check_rate_limit_redis is not None:
        try:
            check_rate_limit_redis(
                "ec_verificar",
                ip,
                ESTADO_CUENTA_VERIFICAR_WINDOW_SEC,
                ESTADO_CUENTA_VERIFICAR_MAX,
                "Demasiados intentos. Espere 15 minutos e intente de nuevo.",
            )
            return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _estado_cuenta_verificar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < ESTADO_CUENTA_VERIFICAR_WINDOW_SEC]
        if len(attempts) >= ESTADO_CUENTA_VERIFICAR_MAX:
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espere 15 minutos e intente de nuevo.")
        attempts.append(now)

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


def check_rate_limit_estado_cuenta_validar(ip: str) -> None:
    """Lanza 429 si se supera el límite de validar cédula (estado de cuenta) por IP."""
    if check_rate_limit_redis is not None:
        try:
            check_rate_limit_redis(
                "ec_validar",
                ip,
                ESTADO_CUENTA_VALIDAR_WINDOW_SEC,
                ESTADO_CUENTA_VALIDAR_MAX,
                "Demasiadas consultas. Espere un minuto e intente de nuevo.",
            )
            return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _estado_cuenta_validar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < ESTADO_CUENTA_VALIDAR_WINDOW_SEC]
        if len(attempts) >= ESTADO_CUENTA_VALIDAR_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas consultas. Espere un minuto e intente de nuevo.",
            )
        attempts.append(now)


def check_rate_limit_estado_cuenta_solicitar(ip: str) -> None:
    """Lanza 429 si se supera el límite de solicitar estado de cuenta (PDF) por IP."""
    if check_rate_limit_redis is not None:
        try:
            check_rate_limit_redis(
                "ec_solicitar",
                ip,
                ESTADO_CUENTA_SOLICITAR_WINDOW_SEC,
                ESTADO_CUENTA_SOLICITAR_MAX,
                "Ha alcanzado el límite de consultas por hora. Intente más tarde.",
            )
            return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _estado_cuenta_solicitar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < ESTADO_CUENTA_SOLICITAR_WINDOW_SEC]
        if len(attempts) >= ESTADO_CUENTA_SOLICITAR_MAX:
            raise HTTPException(
                status_code=429,
                detail="Ha alcanzado el límite de consultas por hora. Intente más tarde.",
            )
        attempts.append(now)
