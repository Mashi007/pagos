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
from app.services.desempeno_1_cuota_stock import (
    compute_desempeno_1_cuota_stock,
    compute_desempeno_2_cuotas_stock,
    compute_desempeno_3_cuotas_stock,
    compute_desempeno_4plus_cuotas_stock,
)

from . import financiamiento_inicial, graficos, kpis, pagos_inicial
from .utils import (
    _CACHE_COBRANZAS_SEMANALES,
    _CACHE_COMPOSICION_MOROSIDAD,
    _CACHE_FINANCIAMIENTO_RANGOS,
    _CACHE_KPIS,
    _CACHE_MOROSIDAD_ANALISTA,
    _CACHE_MOROSIDAD_DIA,
    _DASHBOARD_ADMIN_CACHE,
    _DASHBOARD_MENU_CACHE_REFRESH_SEC,
    _fechas_iso_desde_periodo_dashboard,
    _lock,
    menu_grafico_cache_key,
    menu_grafico_cache_set,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

# Include sub-routers (no prefix - all routes are at /dashboard/*)
router.include_router(kpis.router, tags=["dashboard-kpis"])
router.include_router(graficos.router, tags=["dashboard-graficos"])
router.include_router(pagos_inicial.router, tags=["dashboard-pagos-inicial"])
router.include_router(financiamiento_inicial.router, tags=["dashboard-financiamiento-inicial"])


def _refresh_dashboard_admin_cache() -> None:
    """Actualiza la caché legacy dashboard/admin (sin fechas) + clave menú por defecto."""
    db = SessionLocal()
    try:
        fi, ff = _fechas_iso_desde_periodo_dashboard("ultimos_12_meses")
        data = kpis._compute_dashboard_admin(db, fi, ff)
        with _lock:
            _DASHBOARD_ADMIN_CACHE["data"] = data
            _DASHBOARD_ADMIN_CACHE["refreshed_at"] = datetime.now()
        menu_grafico_cache_set(
            menu_grafico_cache_key(
                "admin",
                periodo="ultimos_12_meses",
                fecha_inicio=fi or "",
                fecha_fin=ff or "",
            ),
            data,
        )
        logger.info("Caché dashboard/admin (menú 10 min) actualizada.")
    except Exception as e:
        logger.exception("Error al actualizar caché dashboard/admin: %s", e)
    finally:
        db.close()


def _warm_menu_chart_caches(db) -> None:
    """Precalienta los gráficos del menú con los defaults del frontend."""
    fi, ff = _fechas_iso_desde_periodo_dashboard("ultimos_12_meses")
    jobs = [
        (
            "cobranzas-semanales",
            lambda: graficos._compute_cobranzas_semanales(
                db, fi, ff, 12, None, None, None
            ),
            {
                "fecha_inicio": fi or "",
                "fecha_fin": ff or "",
                "semanas": 12,
                "analista": "",
                "concesionario": "",
                "modelo": "",
            },
        ),
        (
            "pagos-ingresados-por-dia",
            lambda: graficos._compute_pagos_ingresados_por_dia(
                db, 60, solo_moneda_bs=False
            ),
            {"dias": 60},
        ),
        (
            "pagos-bs-ingresados-por-dia",
            lambda: graficos._compute_pagos_ingresados_por_dia(
                db, 60, solo_moneda_bs=True
            ),
            {"dias": 60},
        ),
        (
            "notificaciones-envios-por-dia",
            lambda: graficos._compute_notificaciones_envios_por_dia(
                db, "dias_1_retraso", 90
            ),
            {"tipo_tab": "dias_1_retraso", "dias": 90},
        ),
        (
            "desempeno-1-cuota-stock",
            lambda: compute_desempeno_1_cuota_stock(db, 20),
            {"dias": 20},
        ),
        (
            "desempeno-2-cuotas-stock",
            lambda: compute_desempeno_2_cuotas_stock(db, 20),
            {"dias": 20},
        ),
        (
            "desempeno-3-cuotas-stock",
            lambda: compute_desempeno_3_cuotas_stock(db, 20),
            {"dias": 20},
        ),
        (
            "desempeno-4plus-cuotas-stock",
            lambda: compute_desempeno_4plus_cuotas_stock(db, 20),
            {"dias": 20},
        ),
    ]
    for endpoint, compute, params in jobs:
        try:
            data = compute()
            menu_grafico_cache_set(menu_grafico_cache_key(endpoint, **params), data)
        except Exception as e:
            logger.exception("Error al precalentar caché menú %s: %s", endpoint, e)


def _refresh_all_dashboard_caches() -> None:
    """Actualiza cachés del dashboard (cada 10 min): menú + gráficos legacy."""
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
            fi, ff = _fechas_iso_desde_periodo_dashboard("ultimos_12_meses")
            data = graficos._compute_cobranzas_semanales(db, fi, ff, 12, None, None, None)
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

        _warm_menu_chart_caches(db)
        logger.info(
            "Cachés del dashboard actualizadas (ciclo %ss).",
            _DASHBOARD_MENU_CACHE_REFRESH_SEC,
        )
    finally:
        db.close()


def _dashboard_cache_worker() -> None:
    """Worker: refresca cachés del menú cada 10 minutos (snapshots estáticos)."""
    # Primer warm al arrancar (sin esperar el primer ciclo completo).
    try:
        _refresh_all_dashboard_caches()
    except Exception as e:
        logger.exception("Error en warm inicial caché dashboard: %s", e)

    while True:
        try:
            time.sleep(_DASHBOARD_MENU_CACHE_REFRESH_SEC)
            _refresh_all_dashboard_caches()
        except Exception as e:
            logger.exception("Error en worker de caché dashboard: %s", e)
            time.sleep(60)


def start_dashboard_cache_refresh() -> None:
    """Inicia el hilo que actualiza la caché del dashboard cada 10 minutos."""
    t = threading.Thread(target=_dashboard_cache_worker, daemon=True)
    t.start()
    logger.info(
        "Worker de caché dashboard iniciado (refresh cada %ss).",
        _DASHBOARD_MENU_CACHE_REFRESH_SEC,
    )
