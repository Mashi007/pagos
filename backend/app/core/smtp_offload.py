# -*- coding: utf-8 -*-
"""SMTP (smtplib) fuera del hilo que atiende HTTP / el event loop de uvicorn.

Un solo worker serializa conexiones a Gmail y evita que connect+login bloquee
el ciclo asyncio o el threadpool de FastAPI.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Un hilo: Gmail tolera mal muchos login simultáneos; además no hay deadlock
# si _smtp_deliver se llama anidado (copia itmaster) — se ejecuta inline.
_SMTP_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="smtp-io")
_tls = threading.local()

# connect 25s × 4 reintentos + sleeps + copia itmaster.
SMTP_OFFLOAD_TIMEOUT_SEC = 180.0


def _en_hilo_smtp() -> bool:
    return bool(getattr(_tls, "en_smtp", False))


def run_in_smtp_thread(fn: Callable[..., T], *args, **kwargs) -> T:
    """Ejecuta fn en el hilo smtp-io. Si ya estamos en ese hilo, llama inline."""
    if _en_hilo_smtp():
        return fn(*args, **kwargs)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        logger.warning(
            "[smtp_offload] smtplib invocado desde el event loop; "
            "se mueve a hilo smtp-io (el awaitante no debe ser una ruta async)"
        )

    def _wrap() -> T:
        _tls.en_smtp = True
        try:
            return fn(*args, **kwargs)
        finally:
            _tls.en_smtp = False

    fut = _SMTP_POOL.submit(_wrap)
    return fut.result(timeout=SMTP_OFFLOAD_TIMEOUT_SEC)
