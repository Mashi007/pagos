"""
Dashboard package: KPIs, gráficos, opciones de filtros.
Main router includes all sub-routers; endpoints keep /api/v1/dashboard/* paths.
"""
import logging
import threading
import time
from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.database import SessionLocal
from app.core.deps import get_current_user

from . import graficos, kpis
from .utils import (
    _CACHE_COBRANZAS_SEMANALES,
    _CACHE_COMPOSICION_MOROSIDAD,
    _CACHE_FINANCIAMIENTO_RANGOS,
    _CACHE_KPIS,
    _CACHE_MOROSIDAD_ANALISTA,
    _CACHE_MOROSIDAD_DIA,
    _DASHBOARD_ADMIN_CACHE,
    _lock,
    _next_refresh_local,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

# Include sub-routers (no prefix - all routes are at /dashboard/*)
router.include_router(kpis.router, tags=["dashboard-kpis"])
router.include_router(graficos.router, tags=["dashboard-graficos"])


def _refresh_dashboard_admin_cache() -> None:
    """Actualiza la caché de dashboard/admin en background."""
    db = SessionLocal()
    try:
        data = kpis._compute_dashboard_admin(db, None, None)
        with _lock:
            _DASHBOARD_ADMIN_CACHE["data"] = data
            _DASHBOARD_ADMIN_CACHE["refreshed_at"] = datetime.now()
        logger.info("Caché dashboard/admin actualizada (1:00 / 13:00).")
    except Exception as e:
        logger.exception("Error al actualizar caché dashboard/admin: %s", e)
    finally:
        db.close()


def _refresh_all_dashboard_caches() -> None:
    """Actualiza todas las cachés de gráficos del dashboard (1:00, 13:00)."""
    _refresh_dashboard_admin_cache()
    db = SessionLocal()
    try:
        try:
            data = kpis._compute_kpis_principales(db, None, None, None, None, None)
            with _lock:
                _CACHE_KPIS["data"] = data
                _CACHE_KPIS["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché kpis-principales: %s", e)
        try:
            data = graficos._compute_morosidad_por_dia(db, None, None, 30)
            with _lock:
                _CACHE_MOROSIDAD_DIA["data"] = data
                _CACHE_MOROSIDAD_DIA["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché morosidad-por-dia: %s", e)
        try:
            data = graficos._compute_financiamiento_por_rangos(db, None, None, None, None, None)
            with _lock:
                _CACHE_FINANCIAMIENTO_RANGOS["data"] = data
                _CACHE_FINANCIAMIENTO_RANGOS["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché financiamiento-por-rangos: %s", e)
        try:
            data = graficos._compute_composicion_morosidad(db, None, None, None, None, None)
            with _lock:
                _CACHE_COMPOSICION_MOROSIDAD["data"] = data
                _CACHE_COMPOSICION_MOROSIDAD["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché composicion-morosidad: %s", e)
        try:
            data = graficos._compute_cobranzas_semanales(db, None, None, 12, None, None, None)
            with _lock:
                _CACHE_COBRANZAS_SEMANALES["data"] = data
                _CACHE_COBRANZAS_SEMANALES["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché cobranzas-semanales: %s", e)
        try:
            data = graficos._compute_morosidad_por_analista(db, None, None, None, None, None)
            with _lock:
                _CACHE_MOROSIDAD_ANALISTA["data"] = data
                _CACHE_MOROSIDAD_ANALISTA["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché morosidad-por-analista: %s", e)
        logger.info("Cachés de gráficos del dashboard actualizadas (1:00 / 13:00).")
    finally:
        db.close()


def _dashboard_cache_worker() -> None:
    """Worker que refresca todas las cachés del dashboard a las 1:00 y 13:00 (hora local)."""
    while True:
        try:
            next_refresh = _next_refresh_local()
            wait_secs = (next_refresh - datetime.now()).total_seconds()
            if wait_secs > 0:
                time.sleep(wait_secs)
            _refresh_all_dashboard_caches()
        except Exception as e:
            logger.exception("Error en worker de caché dashboard: %s", e)
            time.sleep(3600)


def start_dashboard_cache_refresh() -> None:
    """Inicia el hilo que actualiza la caché del dashboard a las 1:00 y 13:00."""
    t = threading.Thread(target=_dashboard_cache_worker, daemon=True)
    t.start()
    logger.info("Worker de caché dashboard iniciado (refresh 1:00, 13:00).")
