"""
Rate limiting para endpoints públicos (Cobros, Estado de cuenta, Finiquito).
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

# Finiquito: solicitar código OTP (público, sin auth)
FINIQUITO_SOLICITAR_CODIGO_WINDOW_SEC = 3600
FINIQUITO_SOLICITAR_CODIGO_MAX = 15

# Finiquito: verificar código OTP (fuerza bruta por IP)
FINIQUITO_VERIFICAR_CODIGO_WINDOW_SEC = 900
FINIQUITO_VERIFICAR_CODIGO_MAX = 15

# Finiquito: registro público cédula+correo (spam / enumeración)
FINIQUITO_REGISTRO_WINDOW_SEC = 3600
FINIQUITO_REGISTRO_MAX = 40

_validar_attempts: dict[str, list[float]] = defaultdict(list)
_enviar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_validar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)
_estado_cuenta_verificar_attempts: dict[str, list[float]] = defaultdict(list)
_finiquito_solicitar_codigo_attempts: dict[str, list[float]] = defaultdict(list)
_finiquito_verificar_codigo_attempts: dict[str, list[float]] = defaultdict(list)
_finiquito_registro_attempts: dict[str, list[float]] = defaultdict(list)
_cobros_public_solicitar_attempts: dict[str, list[float]] = defaultdict(list)
_cobros_public_verificar_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()

# Reporte de pago publico: solicitar codigo OTP al correo
COBROS_PUBLIC_SOLICITAR_WINDOW_SEC = 3600
COBROS_PUBLIC_SOLICITAR_MAX = 12

# Verificar codigo (misma ventana que estado de cuenta)
COBROS_PUBLIC_VERIFICAR_WINDOW_SEC = 900
COBROS_PUBLIC_VERIFICAR_MAX = 15



def check_rate_limit_estado_cuenta_verificar(ip: str) -> None:
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "ec_verificar",
                ip,
                ESTADO_CUENTA_VERIFICAR_WINDOW_SEC,
                ESTADO_CUENTA_VERIFICAR_MAX,
                "Demasiados intentos. Espere 15 minutos e intente de nuevo.",
            ):
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
            if check_rate_limit_redis(
                "ec_validar",
                ip,
                ESTADO_CUENTA_VALIDAR_WINDOW_SEC,
                ESTADO_CUENTA_VALIDAR_MAX,
                "Demasiadas consultas. Espere un minuto e intente de nuevo.",
            ):
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
            if check_rate_limit_redis(
                "ec_solicitar",
                ip,
                ESTADO_CUENTA_SOLICITAR_WINDOW_SEC,
                ESTADO_CUENTA_SOLICITAR_MAX,
                "Ha alcanzado el límite de consultas por hora. Intente más tarde.",
            ):
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


def check_rate_limit_cobros_public_solicitar(ip: str) -> None:
    """Limite solicitudes de codigo OTP reporte publico por IP."""
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "cobros_pub_solicitar",
                ip,
                COBROS_PUBLIC_SOLICITAR_WINDOW_SEC,
                COBROS_PUBLIC_SOLICITAR_MAX,
                "Demasiadas solicitudes de codigo. Intente de nuevo en una hora.",
            ):
                return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _cobros_public_solicitar_attempts[ip]
        attempts[:] = [
            t for t in attempts if now - t < COBROS_PUBLIC_SOLICITAR_WINDOW_SEC
        ]
        if len(attempts) >= COBROS_PUBLIC_SOLICITAR_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes de codigo. Intente de nuevo en una hora.",
            )
        attempts.append(now)


def check_rate_limit_cobros_public_verificar(ip: str) -> None:
    """Limite intentos de verificacion OTP reporte publico por IP."""
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "cobros_pub_verificar",
                ip,
                COBROS_PUBLIC_VERIFICAR_WINDOW_SEC,
                COBROS_PUBLIC_VERIFICAR_MAX,
                "Demasiados intentos. Espere 15 minutos e intente de nuevo.",
            ):
                return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _cobros_public_verificar_attempts[ip]
        attempts[:] = [
            t for t in attempts if now - t < COBROS_PUBLIC_VERIFICAR_WINDOW_SEC
        ]
        if len(attempts) >= COBROS_PUBLIC_VERIFICAR_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Espere 15 minutos e intente de nuevo.",
            )
        attempts.append(now)


def check_rate_limit_finiquito_solicitar_codigo(ip: str) -> None:
    """Lanza 429 si se supera el límite de solicitudes de código OTP Finiquito por IP."""
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "finiquito_otp",
                ip,
                FINIQUITO_SOLICITAR_CODIGO_WINDOW_SEC,
                FINIQUITO_SOLICITAR_CODIGO_MAX,
                "Demasiadas solicitudes de codigo. Intente de nuevo en una hora.",
            ):
                return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _finiquito_solicitar_codigo_attempts[ip]
        attempts[:] = [
            t for t in attempts if now - t < FINIQUITO_SOLICITAR_CODIGO_WINDOW_SEC
        ]
        if len(attempts) >= FINIQUITO_SOLICITAR_CODIGO_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes de codigo. Intente de nuevo en una hora.",
            )
        attempts.append(now)


def check_rate_limit_finiquito_verificar_codigo(ip: str) -> None:
    """Límite de intentos de verificación OTP Finiquito por IP (mitiga fuerza bruta del código de 6 cifras)."""
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "finiquito_verificar",
                ip,
                FINIQUITO_VERIFICAR_CODIGO_WINDOW_SEC,
                FINIQUITO_VERIFICAR_CODIGO_MAX,
                "Demasiados intentos de verificacion. Espere 15 minutos e intente de nuevo.",
            ):
                return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _finiquito_verificar_codigo_attempts[ip]
        attempts[:] = [
            t for t in attempts if now - t < FINIQUITO_VERIFICAR_CODIGO_WINDOW_SEC
        ]
        if len(attempts) >= FINIQUITO_VERIFICAR_CODIGO_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos de verificacion. Espere 15 minutos e intente de nuevo.",
            )
        attempts.append(now)


def check_rate_limit_finiquito_registro(ip: str) -> None:
    """Límite de altas nuevas en portal Finiquito por IP y hora."""
    if check_rate_limit_redis is not None:
        try:
            if check_rate_limit_redis(
                "finiquito_registro",
                ip,
                FINIQUITO_REGISTRO_WINDOW_SEC,
                FINIQUITO_REGISTRO_MAX,
                "Demasiados registros desde su red. Intente de nuevo en una hora.",
            ):
                return
        except HTTPException:
            raise
        except Exception:
            pass
    with _lock:
        now = time.time()
        attempts = _finiquito_registro_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < FINIQUITO_REGISTRO_WINDOW_SEC]
        if len(attempts) >= FINIQUITO_REGISTRO_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiados registros desde su red. Intente de nuevo en una hora.",
            )
        attempts.append(now)
