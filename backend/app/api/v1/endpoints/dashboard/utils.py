"""
Shared helpers for dashboard endpoints.
"""
import calendar
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)

MAX_FILTER_STRING_LEN = 200

# Cache state (shared across dashboard endpoints)
_DASHBOARD_ADMIN_CACHE: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_KPIS: dict[str, Any] = {"data": None, "refreshed_at": None}
# Opciones de filtros: TTL corto (5 min) para evitar golpes repetidos al cargar dashboard
_OPCIONES_FILTROS_TTL_SEC = 360
_CACHE_OPCIONES_FILTROS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_DIA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_FINANCIAMIENTO_RANGOS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COMPOSICION_MOROSIDAD: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COBRANZAS_SEMANALES: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_ANALISTA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_REFRESH_HOURS = (1, 13)
_lock = threading.Lock()

# Préstamos por modelo / concesionario: el frontend suele enviar siempre fecha_inicio/fecha_fin;
# caché en memoria por clave de consulta (TTL corto) reduce golpes repetidos a la BD.
_PRESTAMOS_GRAFICOS_CACHE_TTL_SEC = 360
_CACHE_PRESTAMOS_POR_MODELO: dict[str, Any] = {"key": None, "data": None, "refreshed_at": None}
_CACHE_PRESTAMOS_POR_CONCESIONARIO: dict[str, Any] = {"key": None, "data": None, "refreshed_at": None}


def _prestamos_graficos_cache_key(
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> str:
    return "\x1e".join(
        [
            fecha_inicio or "",
            fecha_fin or "",
            analista or "",
            concesionario or "",
            modelo or "",
        ]
    )


def _prestamos_graficos_try_hit(cache_box: dict[str, Any], key: str) -> Optional[Any]:
    """Devuelve datos en caché si la clave coincide y no expiró el TTL."""
    now = datetime.now()
    with _lock:
        if cache_box.get("key") != key:
            return None
        refreshed = cache_box.get("refreshed_at")
        if refreshed is None:
            return None
        age = (now - refreshed).total_seconds()
        if age >= _PRESTAMOS_GRAFICOS_CACHE_TTL_SEC:
            return None
        return cache_box.get("data")


def _prestamos_graficos_store(cache_box: dict[str, Any], key: str, data: Any) -> None:
    with _lock:
        cache_box["key"] = key
        cache_box["data"] = data
        cache_box["refreshed_at"] = datetime.now()


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


def _date_minus_months(d: date, months: int) -> date:
    """Resta meses naturales a una fecha (clamp al último día del mes destino)."""
    y, m = d.year, d.month - months
    while m < 1:
        m += 12
        y -= 1
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last_day))


def _fechas_iso_desde_periodo_dashboard(periodo: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Alineado con frontend useDashboardFiltros.calcularFechasPorPeriodo:
    ultimos_12_meses, día/dia, semana (lun–vie), mes, año/año.
    Devuelve (fecha_inicio, fecha_fin) como YYYY-MM-DD.
    """
    if periodo is None:
        return None, None
    raw = str(periodo).strip()
    if not raw:
        return None, None
    key = raw.lower()
    hoy = date.today()

    def fmt(d: date) -> str:
        return d.isoformat()

    if key in ("día", "dia"):
        return fmt(hoy), fmt(hoy)

    if key == "semana":
        js_dow = (hoy.weekday() + 1) % 7
        diff = -6 if js_dow == 0 else 1 - js_dow
        lun = hoy + timedelta(days=diff)
        vie = lun + timedelta(days=4)
        return fmt(lun), fmt(vie)

    if key == "mes":
        inicio = date(hoy.year, hoy.month, 1)
        if hoy.month == 12:
            fin = date(hoy.year, 12, 31)
        else:
            fin = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)
        return fmt(inicio), fmt(fin)

    if key in ("año", "ano"):
        return fmt(date(hoy.year, 1, 1)), fmt(date(hoy.year, 12, 31))

    if key == "ultimos_12_meses":
        return fmt(_date_minus_months(hoy, 12)), fmt(hoy)

    return None, None


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


def _modelo_label_dashboard_expr(producto_expr, *, incluir_sin_modelo: bool = False):
    """
    Nombre de modelo unificado para gráficos y listas de filtro: catálogo (por id join),
    catálogo por coincidencia lower(trim) con texto del préstamo, texto crudo, producto.
    """
    _mv_texto = aliased(ModeloVehiculo)
    modelo_desde_catalogo_por_texto = (
        select(_mv_texto.modelo)
        .where(
            func.length(func.trim(Prestamo.modelo_vehiculo)) > 0,
            func.lower(func.trim(_mv_texto.modelo))
            == func.lower(func.trim(Prestamo.modelo_vehiculo)),
        )
        .order_by(_mv_texto.id)
        .limit(1)
        .correlate(Prestamo)
        .scalar_subquery()
    )
    parts = [
        ModeloVehiculo.modelo,
        modelo_desde_catalogo_por_texto,
        func.nullif(func.trim(Prestamo.modelo_vehiculo), ""),
        producto_expr,
    ]
    if incluir_sin_modelo:
        parts.append("Sin modelo")
    return func.coalesce(*parts)


def _rangos_financiamiento():
    """Bandas por total_financiamiento (tabla prestamos), cada $400 hasta $2,000 y cola abierta."""
    return [
        (0, 400, "$0 - $400"),
        (400, 800, "$400 - $800"),
        (800, 1200, "$800 - $1,200"),
        (1200, 1600, "$1,200 - $1,600"),
        (1600, 2000, "$1,600 - $2,000"),
        (2000, 999999999, "Más de $2,000"),
    ]
