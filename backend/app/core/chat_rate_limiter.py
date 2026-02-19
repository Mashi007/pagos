"""
Rate limiter para el Chat AI: máximo N peticiones por minuto por usuario.
Evita abuso y controla costes de API OpenRouter.
"""
import threading
import time
from collections import deque
from typing import Optional

from fastapi import HTTPException

# Máximo de peticiones por ventana (1 minuto)
CHAT_RATE_LIMIT_REQUESTS = 10
CHAT_RATE_LIMIT_WINDOW_SEC = 60

# user_email -> deque de timestamps
_requests: dict[str, deque[float]] = {}
_lock = threading.Lock()


def check_rate_limit(user_email: str) -> None:
    """
    Verifica si el usuario ha excedido el límite.
    Lanza HTTPException 429 si excede.
    """
    now = time.monotonic()
    cutoff = now - CHAT_RATE_LIMIT_WINDOW_SEC
    with _lock:
        if user_email not in _requests:
            _requests[user_email] = deque()
        q = _requests[user_email]
        # Eliminar timestamps fuera de la ventana
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= CHAT_RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Límite de {CHAT_RATE_LIMIT_REQUESTS} consultas por minuto alcanzado. Espera unos segundos antes de intentar de nuevo.",
            )
        q.append(now)
