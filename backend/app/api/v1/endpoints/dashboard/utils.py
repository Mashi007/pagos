"""
Shared helpers for dashboard endpoints.
"""
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_FILTER_STRING_LEN = 200

# Cache state (shared across dashboard endpoints)
_DASHBOARD_ADMIN_CACHE: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_KPIS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_DIA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_FINANCIAMIENTO_RANGOS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COMPOSICION_MOROSIDAD: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COBRANZAS_SEMANALES: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_ANALISTA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_REFRESH_HOURS = (1, 13)
_lock = threading.Lock()


def _next_refresh_local() -> datetime:
    """Próxima hora de refresco: 1:00 o 13:00 (hora local del servidor)."""
    now = datetime.now()
    candidates = []
    for h in _CACHE_REFRESH_HOURS:
        t = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        candidates.append(t)
    return min(candidates)


def _safe_float(val) -> float:
    """Convierte a float de forma segura (Decimal, int, None)."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _sanitize_filter_string(value: Optional[str]) -> Optional[str]:
    """Normaliza y trunca analista/concesionario/modelo para evitar strings excesivamente largos."""
    if value is None or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    return s[:MAX_FILTER_STRING_LEN] if len(s) > MAX_FILTER_STRING_LEN else s


def _kpi(valor: float = 0, variacion: float = 0) -> dict:
    return {"valor_actual": valor, "variacion_porcentual": variacion}


def _etiquetas_12_meses() -> list[dict]:
    """Solo etiquetas de los últimos 12 meses (sin datos demo). Valores en cero."""
    meses = []
    hoy = datetime.now()
    nombres = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    for i in range(11, -1, -1):
        d = hoy - timedelta(days=30 * i)
        mes = d.month
        año = d.year
        label = f"{nombres[mes - 1]} {año}"
        meses.append({
            "mes": label,
            "year": año,
            "month": mes,
            "cartera": 0,
            "cobrado": 0,
            "morosidad": 0,
            "cantidad_nuevos": 0,
            "monto_nuevos": 0,
            "total_acumulado": 0,
            "monto_cuotas_programadas": 0,
            "monto_pagado": 0,
            "morosidad_mensual": 0,
            "pagos": 0,
            "monto": 0,
        })
    return meses


def _rango_y_anterior(fecha_inicio: date, fecha_fin: date):
    """Dado un rango (inicio, fin), devuelve (inicio_dt, fin_dt, inicio_ant_dt, fin_ant_dt) para filtrar por fecha_registro.
    Período anterior = mismo número de días antes de fecha_inicio.
    """
    from datetime import time as dt_time
    inicio_dt = datetime.combine(fecha_inicio, dt_time(0, 0, 0, 0))
    fin_dt = datetime.combine(fecha_fin, dt_time(23, 59, 59, 999999))
    delta_dias = (fecha_fin - fecha_inicio).days + 1
    fin_ant = fecha_inicio - timedelta(days=1)
    inicio_ant = fin_ant - timedelta(days=delta_dias - 1)
    inicio_ant_dt = datetime.combine(inicio_ant, dt_time(0, 0, 0, 0))
    fin_ant_dt = datetime.combine(fin_ant, dt_time(23, 59, 59, 999999))
    return inicio_dt, fin_dt, inicio_ant_dt, fin_ant_dt


def _ultimo_dia_del_mes(d: datetime) -> datetime:
    """Último día del mes a las 23:59 UTC para comparar con fecha_registro (timezone-aware)."""
    siguiente = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo = siguiente - timedelta(seconds=1)
    if ultimo.tzinfo is None:
        ultimo = ultimo.replace(tzinfo=timezone.utc)
    return ultimo


def _primer_ultimo_dia_mes(d: datetime) -> tuple[date, date]:
    """Devuelve (primer_día, último_día) del mes de d como date."""
    y, m = d.year, d.month
    inicio = date(y, m, 1)
    if m == 12:
        fin = date(y, 12, 31)
    else:
        fin = date(y, m + 1, 1) - timedelta(days=1)
    return inicio, fin


def _meses_desde_rango(fecha_inicio: date, fecha_fin: date) -> list[dict]:
    """Genera lista de meses (label, año, mes) entre fecha_inicio y fecha_fin (por mes natural)."""
    nombres = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    meses = []
    y, m = fecha_inicio.year, fecha_inicio.month
    fin_y, fin_m = fecha_fin.year, fecha_fin.month
    while (y, m) <= (fin_y, fin_m):
        label = f"{nombres[m - 1]} {y}"
        meses.append({"mes": label, "year": y, "month": m})
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return meses


def _parse_fechas_concesionario(fecha_inicio: Optional[str], fecha_fin: Optional[str]):
    """Parsea fechas o devuelve rango últimos 12 meses."""
    hoy = datetime.now(timezone.utc)
    hoy_date = date(hoy.year, hoy.month, hoy.day)
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            return inicio, fin
        except ValueError:
            pass
    fin = hoy_date
    inicio = fin - timedelta(days=365)
    return inicio, fin


def _rangos_financiamiento():
    """Bandas por total_financiamiento (tabla prestamos). Incluye $1,200-$1,400 y Más de $1,400."""
    return [
        (0, 200, "$0 - $200"),
        (200, 400, "$200 - $400"),
        (400, 600, "$400 - $600"),
        (600, 800, "$600 - $800"),
        (800, 1000, "$800 - $1,000"),
        (1000, 1200, "$1,000 - $1,200"),
        (1200, 1400, "$1,200 - $1,400"),
        (1400, 999999999, "Más de $1,400"),
    ]
