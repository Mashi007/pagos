"""
Sidecars del scheduler líder: caché dashboard + LIQUIDADO automático.

Solo deben correr en el proceso que tiene liderazgo APScheduler (multi-worker Gunicorn).
Arrancan al reclamar liderazgo; se detienen al perder heartbeat o en shutdown.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_sidecars_active = False


def start_scheduler_leader_sidecars_once() -> bool:
    """
    Arranca dashboard cache worker + liquidado_scheduler en este proceso (idempotente).
    Returns True si se activaron ahora; False si ya estaban activos.
    """
    global _sidecars_active
    with _lock:
        if _sidecars_active:
            return False
        try:
            from app.api.v1.endpoints.dashboard import start_dashboard_cache_refresh

            start_dashboard_cache_refresh()
        except Exception as e:
            logger.exception("[LeaderSidecars] No se pudo iniciar caché dashboard: %s", e)
        try:
            from app.services.liquidado_scheduler import liquidado_scheduler

            liquidado_scheduler.iniciar_scheduler()
        except Exception as e:
            logger.warning("[LeaderSidecars] No se pudo iniciar LIQUIDADO: %s", e)
        _sidecars_active = True
        logger.info(
            "[LeaderSidecars] Activos en este proceso (dashboard cache + LIQUIDADO 00:40 Caracas)"
        )
        return True


def stop_scheduler_leader_sidecars() -> None:
    """Detiene sidecars en este proceso (idempotente)."""
    global _sidecars_active
    with _lock:
        if not _sidecars_active:
            return
        try:
            from app.services.liquidado_scheduler import liquidado_scheduler

            liquidado_scheduler.detener_scheduler()
        except Exception as e:
            logger.warning("[LeaderSidecars] Al detener LIQUIDADO: %s", e)
        try:
            from app.api.v1.endpoints.dashboard import stop_dashboard_cache_refresh

            stop_dashboard_cache_refresh()
        except Exception as e:
            logger.warning("[LeaderSidecars] Al detener caché dashboard: %s", e)
        _sidecars_active = False
        logger.info("[LeaderSidecars] Detenidos en este proceso")


def scheduler_leader_sidecars_active() -> bool:
    with _lock:
        return _sidecars_active
