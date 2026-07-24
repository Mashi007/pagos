# -*- coding: utf-8 -*-
"""Ejecuta lotes de notificaciones en hilo independiente del ciclo HTTP."""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[str, threading.Thread] = {}


def job_activo(clave: str) -> bool:
    with _lock:
        t = _active.get(clave)
        return t is not None and t.is_alive()


def claves_activas() -> list[str]:
    with _lock:
        return [k for k, t in _active.items() if t is not None and t.is_alive()]


def spawn_envio_bg(
    clave: str,
    target: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> bool:
    clave = (clave or "").strip() or "default"

    def _runner() -> None:
        try:
            logger.info("[notif_bg] inicio clave=%s", clave)
            target(*args, **kwargs)
            logger.info("[notif_bg] fin ok clave=%s", clave)
        except Exception:
            logger.exception("[notif_bg] fin error clave=%s", clave)
        finally:
            with _lock:
                cur = _active.get(clave)
                if cur is threading.current_thread():
                    _active.pop(clave, None)

    with _lock:
        cur = _active.get(clave)
        if cur is not None and cur.is_alive():
            logger.warning("[notif_bg] omitido: ya activo clave=%s", clave)
            return False
        t = threading.Thread(
            target=_runner,
            name="notif-envio-" + clave,
            daemon=True,
        )
        _active[clave] = t
        t.start()
        return True
