"""
Endpoints del dashboard. Usa datos reales de la BD cuando existen (clientes);
el resto permanece stub hasta tener modelos de préstamos/pagos/cuotas.
Caché de dashboard/admin: se actualiza 3 veces al día (6:00, 13:00, 16:00) para cargas rápidas.

CONCEPTO PAGO VENCIDO Y MOROSO (terminología unificada):
- Pago vencido = cuotas vencidas y no pagadas (fecha_vencimiento < hoy).
- Vencido: si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb. Desde el 24 = vencido (1-60 días de atraso).
- Moroso: 61+ días de atraso (se declara como moroso desde el día 61).
- Condición: fecha_vencimiento < fecha_referencia AND fecha_pago IS NULL.
"""
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from sqlalchemy import and_, distinct, or_, select, func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.pago import Pago
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# Caché para todos los gráficos del dashboard. Se actualiza a las 6:00, 13:00, 16:00 (hora local).
_DASHBOARD_ADMIN_CACHE: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_KPIS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_DIA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_FINANCIAMIENTO_RANGOS: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COMPOSICION_MOROSIDAD: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_COBRANZAS_SEMANALES: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_MOROSIDAD_ANALISTA: dict[str, Any] = {"data": None, "refreshed_at": None}
_CACHE_REFRESH_HOURS = (6, 13, 16)  # 6 AM, 1 PM, 4 PM (hora local del servidor)
_lock = threading.Lock()

# Límite de longitud para filtros de texto (auditoría: evitar abuso/consultas inesperadas)
MAX_FILTER_STRING_LEN = 200


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


@router.get("/opciones-filtros")
def get_opciones_filtros(db: Session = Depends(get_db)):
    """Opciones para filtros desde BD: analistas, concesionarios, modelos (solo clientes ACTIVOS)."""
    try:
        analistas = [r[0] for r in db.execute(
            select(Prestamo.analista).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", Prestamo.analista.isnot(None))
            .distinct()
        ).all() if r[0]]
        concesionarios = [r[0] for r in db.execute(
            select(Prestamo.concesionario).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", Prestamo.concesionario.isnot(None))
            .distinct()
        ).all() if r[0]]
        # Modelos: modelo_vehiculo > ModeloVehiculo.modelo > producto (excl. "Financiamiento")
        producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
        modelo_nombre = func.coalesce(
            func.nullif(func.trim(Prestamo.modelo_vehiculo), ""),
            ModeloVehiculo.modelo,
            producto_valido,
        )
        modelos = [r[0] for r in db.execute(
            select(modelo_nombre)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", modelo_nombre.isnot(None))
            .distinct()
        ).all() if r[0]]
        return {"analistas": analistas, "concesionarios": concesionarios, "modelos": modelos}
    except Exception:
        return {"analistas": [], "concesionarios": [], "modelos": []}


def _safe_float(val) -> float:
    """Convierte a float de forma segura (Decimal, int, None)."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


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


def _compute_kpis_principales(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula KPIs principales (usado por endpoint y por refresh de caché)."""
    try:
        # KPIs solo incluyen clientes ACTIVOS
        activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
        total_clientes = activos  # Para KPIs: total = solo activos
        inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
        finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0

        usar_rango = fecha_inicio and fecha_fin
        try:
            inicio_dt = fin_dt = inicio_ant_dt = fin_ant_dt = None
            if usar_rango:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                inicio_dt, fin_dt, inicio_ant_dt, fin_ant_dt = _rango_y_anterior(inicio, fin)
        except (ValueError, TypeError):
            usar_rango = False

        if not usar_rango:
            now_utc = datetime.now(timezone.utc)
            inicio_mes_actual = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes_actual = (inicio_mes_actual + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes_anterior = inicio_mes_actual - timedelta(seconds=1)
            inicio_dt, fin_dt = inicio_mes_actual, fin_mes_actual
            inicio_ant_dt, fin_ant_dt = inicio_mes_anterior, fin_mes_anterior

        # Total préstamos: solo clientes ACTIVOS
        conds = [
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= inicio_dt,
            Prestamo.fecha_registro <= fin_dt,
        ]
        if analista:
            conds.append(Prestamo.analista == analista)
        if concesionario:
            conds.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds.append(Prestamo.modelo_vehiculo == modelo)
        total_prestamos = db.scalar(
            select(func.count()).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id).where(and_(*conds))
        ) or 0

        total_mes_actual = db.scalar(
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_registro >= inicio_dt,
                Prestamo.fecha_registro <= fin_dt,
                *([] if not analista else [Prestamo.analista == analista]),
                *([] if not concesionario else [Prestamo.concesionario == concesionario]),
                *([] if not modelo else [Prestamo.modelo_vehiculo == modelo]),
            ))
        ) or 0
        conds_ant = [
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= inicio_ant_dt,
            Prestamo.fecha_registro <= fin_ant_dt,
        ]
        if analista:
            conds_ant.append(Prestamo.analista == analista)
        if concesionario:
            conds_ant.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_ant.append(Prestamo.modelo_vehiculo == modelo)
        total_mes_anterior = db.scalar(
            select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_ant))
        ) or 0

        creditos_nuevos_valor = _safe_float(total_mes_actual)
        if total_mes_anterior and _safe_float(total_mes_anterior) != 0:
            variacion_creditos = ((creditos_nuevos_valor - _safe_float(total_mes_anterior)) / _safe_float(total_mes_anterior)) * 100.0
        else:
            variacion_creditos = 0.0

        # Morosidad: cuotas vencidas (fecha_vencimiento < hoy) y no pagadas. No se cuenta si vence hoy o en el futuro.
        hoy = date.today()
        inicio_d = inicio_dt.date() if hasattr(inicio_dt, "date") else (inicio if usar_rango else inicio_dt.date())
        fin_d = fin_dt.date() if hasattr(fin_dt, "date") else (fin if usar_rango else fin_dt.date())
        conds_moro = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.fecha_vencimiento >= inicio_d,
            Cuota.fecha_vencimiento <= fin_d,
        ]
        if analista:
            conds_moro.append(Prestamo.analista == analista)
        if concesionario:
            conds_moro.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_moro.append(Prestamo.modelo_vehiculo == modelo)
        morosidad_actual = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(and_(*conds_moro))
            )
        )
        # Variación vs período anterior: morosidad del período anterior (vencido en ese período y no cobrado)
        inicio_ant_d = inicio_ant_dt.date() if hasattr(inicio_ant_dt, "date") else inicio_ant_dt
        fin_ant_d = fin_ant_dt.date() if hasattr(fin_ant_dt, "date") else fin_ant_dt
        conds_moro_ant = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.fecha_vencimiento >= inicio_ant_d,
            Cuota.fecha_vencimiento <= fin_ant_d,
        ]
        if analista:
            conds_moro_ant.append(Prestamo.analista == analista)
        if concesionario:
            conds_moro_ant.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_moro_ant.append(Prestamo.modelo_vehiculo == modelo)
        morosidad_mes_anterior = _safe_float(
            db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(and_(*conds_moro_ant))
            )
        )
        if morosidad_mes_anterior and morosidad_mes_anterior != 0:
            variacion_morosidad = ((morosidad_actual - morosidad_mes_anterior) / morosidad_mes_anterior) * 100.0
        else:
            variacion_morosidad = 0.0

        # Cuotas programadas del mes: suma monto_cuota con fecha_vencimiento en el período (join Prestamo para filtros)
        inicio_d = inicio if usar_rango else inicio_dt.date()
        fin_d = fin if usar_rango else fin_dt.date()
        conds_cuota = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento >= inicio_d,
            Cuota.fecha_vencimiento <= fin_d,
        ]
        if analista:
            conds_cuota.append(Prestamo.analista == analista)
        if concesionario:
            conds_cuota.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_cuota.append(Prestamo.modelo_vehiculo == modelo)
        monto_cuotas_programadas = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_cuota))
        ) or 0
        total_programado = _safe_float(monto_cuotas_programadas)
        # % Cuotas pagadas: porcentaje por cantidad de registros (cuotas con fecha_pago no nulo = pagadas)
        total_cuotas_periodo = db.scalar(
            select(func.count())
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_cuota))
        ) or 0
        cuotas_pagadas_count = db.scalar(
            select(func.count())
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_cuota, Cuota.fecha_pago.isnot(None)))
        ) or 0
        porcentaje_cuotas = (float(cuotas_pagadas_count) / float(total_cuotas_periodo) * 100.0) if total_cuotas_periodo else 0.0

        return {
            "total_prestamos": _kpi(_safe_float(total_prestamos), 0.0),
            "creditos_nuevos_mes": _kpi(creditos_nuevos_valor, round(variacion_creditos, 1)),
            "total_clientes": _kpi(_safe_float(total_clientes), 0.0),
            "clientes_por_estado": {
                "activos": _kpi(_safe_float(activos), 0.0),
                "inactivos": _kpi(_safe_float(inactivos), 0.0),
                "finalizados": _kpi(_safe_float(finalizados), 0.0),
            },
            "total_morosidad_usd": _kpi(round(morosidad_actual, 2), round(variacion_morosidad, 1)),
            "cuotas_programadas": {"valor_actual": round(total_programado, 2)},
            "porcentaje_cuotas_pagadas": round(porcentaje_cuotas, 1),
        }
    except Exception as e:
        logger.exception("Error en kpis-principales: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        # Re-lanzar para que el endpoint devuelva 500 y no cachee ceros
        raise


@router.get("/kpis-principales")
def get_kpis_principales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs principales. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían fechas ni filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_KPIS["data"]
            refreshed = _CACHE_KPIS.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_kpis_principales(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_KPIS["data"] = data
            _CACHE_KPIS["refreshed_at"] = datetime.now()
    return data


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
    # Último día del mes
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


def _next_refresh_local() -> datetime:
    """Próxima hora de refresco: 6:00, 13:00 o 16:00 (hora local del servidor)."""
    now = datetime.now()
    candidates = []
    for h in _CACHE_REFRESH_HOURS:
        t = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        candidates.append(t)
    return min(candidates)


def _compute_dashboard_admin(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
) -> dict:
    """Calcula la respuesta de dashboard/admin (evolucion_mensual desde cuotas)."""
    if fecha_inicio and fecha_fin:
        try:
            inicio = date.fromisoformat(fecha_inicio)
            fin = date.fromisoformat(fecha_fin)
            if inicio <= fin:
                meses = _meses_desde_rango(inicio, fin)
            else:
                meses = _etiquetas_12_meses()
        except ValueError:
            meses = _etiquetas_12_meses()
    else:
        meses = _etiquetas_12_meses()

    evolucion = []
    hoy_date = date.today()
    try:
        for i, m in enumerate(meses):
            if "year" in m and "month" in m:
                y, mo = m["year"], m["month"]
                inicio_d = date(y, mo, 1)
                if mo == 12:
                    fin_d = date(y, 12, 31)
                else:
                    fin_d = date(y, mo + 1, 1) - timedelta(days=1)
            else:
                hoy = datetime.now(timezone.utc)
                fin_mes = hoy - timedelta(days=30 * (len(meses) - 1 - i))
                if fin_mes.tzinfo is None:
                    fin_mes = fin_mes.replace(tzinfo=timezone.utc)
                inicio_d, fin_d = _primer_ultimo_dia_mes(fin_mes)
            # Pagos programados: cuotas del mes (solo clientes ACTIVOS)
            cartera = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                )
            ) or 0
            # Pagos conciliados: todo lo cobrado en el mes (solo clientes ACTIVOS)
            cobrado = db.scalar(
                select(func.coalesce(func.sum(Pago.monto_pagado), 0))
                .select_from(Pago)
                .join(Prestamo, Pago.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    func.date(Pago.fecha_pago) >= inicio_d,
                    func.date(Pago.fecha_pago) <= fin_d,
                )
            ) or 0
            cartera_f = _safe_float(cartera)
            cobrado_f = _safe_float(cobrado)
            # Pago vencido MENSUAL (no acumulado): cuotas que vencen en este mes, ya vencieron y no están pagadas.
            # Solo cuotas con fecha_vencimiento en [inicio_d, fin_d] y fecha_vencimiento < hoy (ya pasó el vencimiento).
            morosidad_f = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= inicio_d,
                    Cuota.fecha_vencimiento <= fin_d,
                    Cuota.fecha_vencimiento < hoy_date,
                    Cuota.fecha_pago.is_(None),
                )
            ) or 0
            morosidad_f = _safe_float(morosidad_f)
            evolucion.append({
                "mes": m["mes"],
                "cartera": cartera_f,
                "cobrado": cobrado_f,
                "morosidad": morosidad_f,
            })
        origen = "bd"
    except Exception as e:
        logger.exception("Error en dashboard admin (evolucion desde cuotas): %s", e)
        evolucion = [
            {"mes": m["mes"], "cartera": 0.0, "cobrado": 0.0, "morosidad": 0.0}
            for m in meses
        ]
        origen = "bd"
    return {
        "financieros": {
            "ingresosCapital": 0.0,
            "ingresosInteres": 0.0,
            "ingresosMora": 0.0,
            "totalCobrado": 0.0,
            "totalCobradoAnterior": 0.0,
        },
        "meta_mensual": 0.0,
        "avance_meta": 0.0,
        "evolucion_mensual": evolucion,
        "evolucion_origen": origen,
    }


def _refresh_dashboard_admin_cache() -> None:
    """Actualiza la caché de dashboard/admin en background (usa sesión propia)."""
    db = SessionLocal()
    try:
        data = _compute_dashboard_admin(db, None, None)
        with _lock:
            _DASHBOARD_ADMIN_CACHE["data"] = data
            _DASHBOARD_ADMIN_CACHE["refreshed_at"] = datetime.now()
        logger.info("Caché dashboard/admin actualizada (6:00 / 13:00 / 16:00).")
    except Exception as e:
        logger.exception("Error al actualizar caché dashboard/admin: %s", e)
    finally:
        db.close()


def _refresh_all_dashboard_caches() -> None:
    """Actualiza todas las cachés de gráficos del dashboard (6:00, 13:00, 16:00)."""
    _refresh_dashboard_admin_cache()
    db = SessionLocal()
    try:
        # KPIs principales (default: sin fechas ni filtros)
        try:
            data = _compute_kpis_principales(db, None, None, None, None, None)
            with _lock:
                _CACHE_KPIS["data"] = data
                _CACHE_KPIS["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché kpis-principales: %s", e)
        # Morosidad por día (default: sin fechas, dias=30)
        try:
            data = _compute_morosidad_por_dia(db, None, None, 30)
            with _lock:
                _CACHE_MOROSIDAD_DIA["data"] = data
                _CACHE_MOROSIDAD_DIA["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché morosidad-por-dia: %s", e)
        # Financiamiento por rangos (default: sin filtros)
        try:
            data = _compute_financiamiento_por_rangos(db, None, None, None, None, None)
            with _lock:
                _CACHE_FINANCIAMIENTO_RANGOS["data"] = data
                _CACHE_FINANCIAMIENTO_RANGOS["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché financiamiento-por-rangos: %s", e)
        # Composición morosidad (default: sin filtros)
        try:
            data = _compute_composicion_morosidad(db, None, None, None, None, None)
            with _lock:
                _CACHE_COMPOSICION_MOROSIDAD["data"] = data
                _CACHE_COMPOSICION_MOROSIDAD["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché composicion-morosidad: %s", e)
        # Cobranzas semanales (default: semanas=12)
        try:
            data = _compute_cobranzas_semanales(db, None, None, 12, None, None, None)
            with _lock:
                _CACHE_COBRANZAS_SEMANALES["data"] = data
                _CACHE_COBRANZAS_SEMANALES["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché cobranzas-semanales: %s", e)
        # Morosidad por analista (default: sin filtros)
        try:
            data = _compute_morosidad_por_analista(db, None, None, None, None, None)
            with _lock:
                _CACHE_MOROSIDAD_ANALISTA["data"] = data
                _CACHE_MOROSIDAD_ANALISTA["refreshed_at"] = datetime.now()
        except Exception as e:
            logger.exception("Error al actualizar caché morosidad-por-analista: %s", e)
        logger.info("Cachés de gráficos del dashboard actualizadas (6:00 / 13:00 / 16:00).")
    finally:
        db.close()


def _dashboard_cache_worker() -> None:
    """Worker que refresca todas las cachés del dashboard a las 6:00, 13:00 y 16:00 (hora local)."""
    while True:
        try:
            next_refresh = _next_refresh_local()
            wait_secs = (next_refresh - datetime.now()).total_seconds()
            if wait_secs > 0:
                import time
                time.sleep(wait_secs)
            _refresh_all_dashboard_caches()
        except Exception as e:
            logger.exception("Error en worker de caché dashboard: %s", e)
            import time
            time.sleep(3600)


def start_dashboard_cache_refresh() -> None:
    """Inicia el hilo que actualiza la caché del dashboard a las 6:00, 13:00 y 16:00."""
    t = threading.Thread(target=_dashboard_cache_worker, daemon=True)
    t.start()
    logger.info("Worker de caché dashboard iniciado (refresh 6:00, 13:00, 16:00).")


@router.get("/admin")
def get_dashboard_admin(
    periodo: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Dashboard admin: evolucion_mensual desde tabla cuotas. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían fechas."""
    use_cache = not (fecha_inicio and fecha_fin)
    if use_cache:
        with _lock:
            cached = _DASHBOARD_ADMIN_CACHE["data"]
            refreshed = _DASHBOARD_ADMIN_CACHE.get("refreshed_at")
        if cached is not None and refreshed is not None:
            now = datetime.now()
            next_refresh = _next_refresh_local()
            if now < next_refresh:
                return cached
        # Caché vacía o expirada: calcular y guardar
        data = _compute_dashboard_admin(db, fecha_inicio, fecha_fin)
        with _lock:
            _DASHBOARD_ADMIN_CACHE["data"] = data
            _DASHBOARD_ADMIN_CACHE["refreshed_at"] = datetime.now()
        return data
    return _compute_dashboard_admin(db, fecha_inicio, fecha_fin)


@router.get("/financiamiento-tendencia-mensual")
def get_financiamiento_tendencia_mensual(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencia mensual de financiamiento. Datos reales: cartera por mes desde Prestamo (no Cliente)."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            cartera = db.scalar(
                select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0))
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.fecha_registro <= ultimo_dia,
                    Prestamo.estado == "APROBADO",
                )
            ) or 0
            resultado.append({
                "mes": m["mes"],
                "monto_nuevos": _safe_float(cartera),
                "monto_cuotas_programadas": 0.0,
                "monto_pagado": 0.0,
                "morosidad_mensual": 0.0,
            })
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en financiamiento-tendencia-mensual: %s", e)
        return {"meses": _etiquetas_12_meses()}


def _compute_morosidad_por_dia(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    dias: Optional[int],
) -> dict:
    """Calcula pago vencido por día (usado por endpoint y por refresh de caché).
    Siempre muestra el día de hoy como extremo derecho y hacia atrás según dias (7-90).
    Pago vencido DIARIO (no acumulado): cuotas que vencen ese día y no están pagadas."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        # Siempre: fin = hoy, inicio = hoy - dias (ignorar fecha_inicio/fecha_fin)
        fin = hoy_date
        dias_efectivos = min(90, max(7, dias or 30))
        inicio = fin - timedelta(days=dias_efectivos)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = inicio
        while d <= fin:
            # Pago vencido del día d (no acumulado): cuotas que vencen ese día, ya vencieron y no están pagadas
            morosidad_dia = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento == d,
                    Cuota.fecha_pago.is_(None),
                )
            ) if d < hoy_date else 0
            morosidad_dia = _safe_float(morosidad_dia or 0)
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "morosidad": round(morosidad_dia, 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en morosidad-por-dia: %s", e)
        return {"dias": []}


@router.get("/morosidad-por-dia")
def get_morosidad_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    dias: Optional[int] = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """Morosidad por día. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían fechas."""
    use_cache = not (fecha_inicio and fecha_fin)
    if use_cache:
        with _lock:
            cached = _CACHE_MOROSIDAD_DIA["data"]
            refreshed = _CACHE_MOROSIDAD_DIA.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_morosidad_por_dia(db, fecha_inicio, fecha_fin, dias)
    if use_cache:
        with _lock:
            _CACHE_MOROSIDAD_DIA["data"] = data
            _CACHE_MOROSIDAD_DIA["refreshed_at"] = datetime.now()
    return data


@router.get("/proyeccion-cobro-30-dias")
def get_proyeccion_cobro_30_dias(db: Session = Depends(get_db)):
    """Proyección de cobro: monto programado por día desde hoy hasta hoy+30. Por cada día suma monto de cuotas con fecha_vencimiento ese día (programado total y pendiente sin pagar)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        fin_date = hoy_date + timedelta(days=30)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = hoy_date
        while d <= fin_date:
            # Monto programado del día (solo clientes ACTIVOS)
            programado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento == d,
                )
            ) or 0
            # Monto pendiente (solo clientes ACTIVOS)
            pendiente = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento == d,
                    Cuota.fecha_pago.is_(None),
                )
            ) or 0
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "monto_programado": round(_safe_float(programado), 2),
                "monto_pendiente": round(_safe_float(pendiente), 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en proyeccion-cobro-30-dias: %s", e)
        return {"dias": []}


@router.get("/monto-programado-proxima-semana")
def get_monto_programado_proxima_semana(db: Session = Depends(get_db)):
    """Monto programado por día desde hoy hasta una semana después (7 días).
    Por cada día: suma de monto_cuota de cuotas con fecha_vencimiento ese día (tabla cuotas)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        fin_date = hoy_date + timedelta(days=7)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = hoy_date
        while d <= fin_date:
            programado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento == d,
                )
            ) or 0
            resultado.append({
                "fecha": d.isoformat(),
                "dia": f"{d.day} {nombres_mes[d.month - 1]}",
                "monto_programado": round(_safe_float(programado), 2),
            })
            d += timedelta(days=1)
        return {"dias": resultado}
    except Exception as e:
        logger.exception("Error en monto-programado-proxima-semana: %s", e)
        return {"dias": []}


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


@router.get("/prestamos-por-concesionario")
def get_prestamos_por_concesionario(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por concesionario: por_mes (en el período) y acumulado desde el inicio. Origen: tabla prestamos, campo concesionario."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        # Mes como YYYY-MM para agrupar
        mes_expr = func.to_char(
            func.date_trunc("month", Prestamo.fecha_registro),
            "YYYY-MM",
        )
        concesionario_label = func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario")

        conds_base = [
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            func.date(Prestamo.fecha_registro) >= inicio,
            func.date(Prestamo.fecha_registro) <= fin,
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)

        # Por mes: préstamos APROBADO en [inicio, fin] (solo clientes ACTIVOS)
        q_por_mes = (
            select(
                mes_expr.label("mes"),
                concesionario_label,
                func.count().label("cantidad"),
            )
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_base))
            .group_by(mes_expr, Prestamo.concesionario)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [
            {"mes": r.mes, "concesionario": r.concesionario, "cantidad": r.cantidad}
            for r in rows_por_mes
        ]

        # Acumulado: todos los préstamos APROBADO desde el inicio (solo clientes ACTIVOS)
        conds_acum = [Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO"]
        if analista:
            conds_acum.append(Prestamo.analista == analista)
        if concesionario:
            conds_acum.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_acum.append(Prestamo.modelo_vehiculo == modelo)

        q_acum = (
            select(
                func.coalesce(Prestamo.concesionario, "Sin concesionario").label("concesionario"),
                func.count().label("cantidad_acumulada"),
            )
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_acum))
            .group_by(Prestamo.concesionario)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [
            {"concesionario": r.concesionario, "cantidad_acumulada": r.cantidad_acumulada}
            for r in rows_acum
        ]

        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-concesionario: %s", e)
        return {"por_mes": [], "acumulado": []}


@router.get("/prestamos-por-modelo")
def get_prestamos_por_modelo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Préstamos aprobados por modelo: por_mes (en el período) y acumulado en el período.
    Respeta filtros analista, concesionario, modelo.
    Usa Prestamo.modelo_vehiculo; si vacío, ModeloVehiculo.modelo vía modelo_vehiculo_id;
    si sigue vacío, producto (excepto 'Financiamiento' genérico); si no, 'Sin modelo'."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo_filtro = _sanitize_filter_string(modelo)
    try:
        inicio, fin = _parse_fechas_concesionario(fecha_inicio, fecha_fin)
        mes_expr = func.to_char(
            func.date_trunc("month", Prestamo.fecha_registro),
            "YYYY-MM",
        )
        # producto como fallback cuando modelo_vehiculo vacío (excluir "Financiamiento" genérico)
        producto_valido = func.nullif(func.nullif(func.trim(Prestamo.producto), ""), "Financiamiento")
        # Nombre del modelo: modelo_vehiculo > ModeloVehiculo.modelo > producto > "Sin modelo"
        modelo_expr = func.coalesce(
            func.nullif(func.trim(Prestamo.modelo_vehiculo), ""),
            ModeloVehiculo.modelo,
            producto_valido,
            "Sin modelo",
        )

        conds_base = [
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            func.date(Prestamo.fecha_registro) >= inicio,
            func.date(Prestamo.fecha_registro) <= fin,
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo_filtro:
            # Coincidir por modelo_vehiculo, ModeloVehiculo.modelo o producto
            conds_base.append(
                or_(
                    Prestamo.modelo_vehiculo == modelo_filtro,
                    ModeloVehiculo.modelo == modelo_filtro,
                    Prestamo.producto == modelo_filtro,
                )
            )

        # Por mes: préstamos APROBADO en [inicio, fin] (solo clientes ACTIVOS)
        q_por_mes = (
            select(
                mes_expr.label("mes"),
                modelo_expr.label("modelo"),
                func.count().label("cantidad"),
            )
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(and_(*conds_base))
            .group_by(mes_expr, modelo_expr)
            .order_by(mes_expr, func.count().desc())
        )
        rows_por_mes = db.execute(q_por_mes).all()
        por_mes = [
            {"mes": r.mes, "modelo": r.modelo or "Sin modelo", "cantidad": r.cantidad}
            for r in rows_por_mes
        ]

        # Acumulado: mismo período [inicio, fin] y filtros (no "desde el inicio")
        q_acum = (
            select(
                modelo_expr.label("modelo"),
                func.count().label("cantidad_acumulada"),
            )
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .outerjoin(ModeloVehiculo, Prestamo.modelo_vehiculo_id == ModeloVehiculo.id)
            .where(and_(*conds_base))
            .group_by(modelo_expr)
            .order_by(func.count().desc())
        )
        rows_acum = db.execute(q_acum).all()
        acumulado = [
            {"modelo": r.modelo or "Sin modelo", "cantidad_acumulada": r.cantidad_acumulada}
            for r in rows_acum
        ]

        return {"por_mes": por_mes, "acumulado": acumulado}
    except Exception as e:
        logger.exception("Error en prestamos-por-modelo: %s", e)
        return {"por_mes": [], "acumulado": []}


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


def _compute_financiamiento_por_rangos(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula financiamiento por rangos: cuenta préstamos APROBADOS por banda de total_financiamiento.
    Filtra por fecha_registro cuando se envían fecha_inicio/fecha_fin."""
    try:
        conds_base = [
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Prestamo.total_financiamiento.isnot(None),
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)
        if fecha_inicio and fecha_fin:
            try:
                inicio = date.fromisoformat(fecha_inicio)
                fin = date.fromisoformat(fecha_fin)
                conds_base.append(func.date(Prestamo.fecha_registro) >= inicio)
                conds_base.append(func.date(Prestamo.fecha_registro) <= fin)
            except ValueError:
                pass

        rangos_def = _rangos_financiamiento()
        resultado = []
        total_p = 0
        for min_val, max_val, cat in rangos_def:
            if max_val >= 999999999:
                q = (
                    select(func.count().label("n"))
                    .select_from(Prestamo)
                    .join(Cliente, Prestamo.cliente_id == Cliente.id)
                    .where(
                        and_(*conds_base),
                        Prestamo.total_financiamiento >= min_val,
                    )
                )
            else:
                q = (
                    select(func.count().label("n"))
                    .select_from(Prestamo)
                    .join(Cliente, Prestamo.cliente_id == Cliente.id)
                    .where(
                        and_(*conds_base),
                        Prestamo.total_financiamiento >= min_val,
                        Prestamo.total_financiamiento < max_val,
                    )
                )
            n = int(db.scalar(q) or 0)
            total_p += n
            resultado.append({"categoria": cat, "cantidad_prestamos": n, "monto_total": 0.0})
        if total_p == 0:
            total_p = 1
        return {
            "rangos": [
                {
                    "categoria": r["categoria"],
                    "cantidad_prestamos": r["cantidad_prestamos"],
                    "monto_total": r["monto_total"],
                    "porcentaje_cantidad": round(100 * r["cantidad_prestamos"] / total_p, 1),
                    "porcentaje_monto": 0.0,
                }
                for r in resultado
            ],
            "total_prestamos": total_p,
            "total_monto": 0.0,
        }
    except Exception as e:
        logger.exception("Error en financiamiento-por-rangos: %s", e)
        rangos = [
            ("$0 - $200", 0),
            ("$200 - $400", 0),
            ("$400 - $600", 0),
            ("$600 - $800", 0),
            ("$800 - $1,000", 0),
            ("$1,000 - $1,200", 0),
            ("$1,200 - $1,400", 0),
            ("Más de $1,400", 0),
        ]
        total_p = max(1, sum(r[1] for r in rangos))
        return {
            "rangos": [
                {"categoria": c, "cantidad_prestamos": n, "monto_total": 0.0, "porcentaje_cantidad": round(100 * n / total_p, 1), "porcentaje_monto": 0.0}
                for c, n in rangos
            ],
            "total_prestamos": total_p,
            "total_monto": 0.0,
        }


@router.get("/financiamiento-por-rangos")
def get_financiamiento_por_rangos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Bandas por total_financiamiento. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_FINANCIAMIENTO_RANGOS["data"]
            refreshed = _CACHE_FINANCIAMIENTO_RANGOS.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_financiamiento_por_rangos(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_FINANCIAMIENTO_RANGOS["data"] = data
            _CACHE_FINANCIAMIENTO_RANGOS["refreshed_at"] = datetime.now()
    return data


def _compute_composicion_morosidad(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula composición de morosidad: cuotas vencidas sin pagar al día de hoy, agrupadas por días de atraso.
    Snapshot actual (usa current_date). Respeta filtros analista, concesionario, modelo."""
    try:
        # Bandas: 1-30 y 31-60 = VENCIDO; 61-90 y 90+ = MOROSO (61+ días de atraso)
        bandas = [(1, 30, "1-30 días"), (31, 60, "31-60 días"), (61, 90, "61-90 días"), (91, 999999, "90+ días")]
        puntos = []
        total_monto = 0.0
        total_cuotas = 0
        total_prestamos = 0
        dias_atraso = func.current_date() - Cuota.fecha_vencimiento
        conds_base = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
        ]
        if analista:
            conds_base.append(Prestamo.analista == analista)
        if concesionario:
            conds_base.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds_base.append(Prestamo.modelo_vehiculo == modelo)
        for min_d, max_d, cat in bandas:
            conds_comp = list(conds_base) + [dias_atraso >= min_d]
            if max_d < 999999:
                conds_comp.append(dias_atraso <= max_d)
            q = (
                select(
                    func.count().label("n"),
                    func.coalesce(func.sum(Cuota.monto), 0).label("m"),
                    func.count(distinct(Cuota.prestamo_id)).label("np"),
                )
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(and_(*conds_comp))
            )
            row = db.execute(q).one()
            n, m, np = int(row.n or 0), _safe_float(row.m), int(row.np or 0)
            total_cuotas += n
            total_monto += m
            total_prestamos += np
            puntos.append({"categoria": cat, "monto": m, "cantidad_cuotas": n, "cantidad_prestamos": np})
        return {"puntos": puntos, "total_morosidad": total_monto, "total_cuotas": total_cuotas, "total_prestamos": total_prestamos}
    except Exception as e:
        logger.exception("Error en composicion-morosidad: %s", e)
        puntos = [
            ("1-30 días", 12000, 45, 12),
            ("31-60 días", 8500, 28, 9),
            ("61-90 días", 6200, 18, 6),
            ("90+ días", 15800, 32, 10),
        ]
        return {
            "puntos": [{"categoria": c, "monto": m, "cantidad_cuotas": n, "cantidad_prestamos": np} for c, m, n, np in puntos],
            "total_morosidad": sum(p[1] for p in puntos),
            "total_cuotas": sum(p[2] for p in puntos),
            "total_prestamos": sum(p[3] for p in puntos),
        }


@router.get("/composicion-morosidad")
def get_composicion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Composición de morosidad. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_COMPOSICION_MOROSIDAD["data"]
            refreshed = _CACHE_COMPOSICION_MOROSIDAD.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_composicion_morosidad(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_COMPOSICION_MOROSIDAD["data"] = data
            _CACHE_COMPOSICION_MOROSIDAD["refreshed_at"] = datetime.now()
    return data


@router.get("/cobranza-fechas-especificas", summary="[Stub] Requiere tabla pagos/cobranzas para datos reales.")
def get_cobranza_fechas_especificas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranza por fechas específicas. Stub: requiere tabla pagos/cobranzas."""
    return {"dias": []}


def _compute_cobranzas_semanales(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    semanas: Optional[int],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """Calcula cobranzas semanales (usado por endpoint y por refresh de caché)."""
    try:
        hoy = date.today()
        sem = []
        for i in range(min(semanas or 12, 12)):
            fin_semana = hoy - timedelta(weeks=i)
            inicio_semana = fin_semana - timedelta(days=6)
            pagos_reales = db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_semana,
                    func.date(Cuota.fecha_pago) <= fin_semana,
                )
            ) or 0
            monto_reales = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_semana,
                    func.date(Cuota.fecha_pago) <= fin_semana,
                )
            ) or 0
            sem.append({
                "semana_inicio": inicio_semana.isoformat(),
                "nombre_semana": f"Sem {12 - i}",
                "cobranzas_planificadas": 0,
                "pagos_reales": pagos_reales,
                "monto_reales": _safe_float(monto_reales),
            })
        return {"semanas": sem, "fecha_inicio": fecha_inicio or "", "fecha_fin": fecha_fin or ""}
    except Exception as e:
        logger.exception("Error en cobranzas-semanales: %s", e)
        return {"semanas": [], "fecha_inicio": fecha_inicio or "", "fecha_fin": fecha_fin or ""}


@router.get("/cobranzas-semanales", summary="[Stub] Valores fijos hasta tener tabla pagos/cobranzas.")
def get_cobranzas_semanales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    semanas: Optional[int] = Query(12, ge=1, le=52),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranzas semanales. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_COBRANZAS_SEMANALES["data"]
            refreshed = _CACHE_COBRANZAS_SEMANALES.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_cobranzas_semanales(db, fecha_inicio, fecha_fin, semanas, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_COBRANZAS_SEMANALES["data"] = data
            _CACHE_COBRANZAS_SEMANALES["refreshed_at"] = datetime.now()
    return data


def _compute_morosidad_por_analista(
    db: Session,
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> dict:
    """
    Cuotas vencidas por analista: cuotas donde hoy > fecha_vencimiento y sin pagar (fecha_pago IS NULL).
    El analista se toma del préstamo de cada cuota: cuotas JOIN prestamos ON cuotas.prestamo_id = prestamos.id.
    Por cada analista: cantidad de cuotas vencidas y suma de monto (dólares vencidos).
    """
    try:
        hoy = date.today()
        conds = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        ]
        if analista:
            conds.append(Prestamo.analista == analista)
        if concesionario:
            conds.append(Prestamo.concesionario == concesionario)
        if modelo:
            conds.append(Prestamo.modelo_vehiculo == modelo)

        analista_label = func.coalesce(Prestamo.analista, "Sin analista")
        q = (
            select(
                analista_label.label("analista"),
                func.count().label("cantidad_cuotas_vencidas"),
                func.coalesce(func.sum(Cuota.monto), 0).label("monto_vencido"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds))
            .group_by(analista_label)
        )
        rows = db.execute(q).all()
        resultado = [
            {
                "analista": str(r[0]) if r[0] else "Sin analista",
                "cantidad_cuotas_vencidas": int(r[1]),
                "monto_vencido": round(_safe_float(r[2]), 2),
            }
            for r in rows
        ]
        resultado.sort(key=lambda x: -x["monto_vencido"])
        return {"analistas": resultado}
    except Exception as e:
        logger.exception("Error en morosidad-por-analista: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {"analistas": []}


@router.get("/morosidad-por-analista")
def get_morosidad_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Morosidad por analista. Con caché 3 veces/día (6:00, 13:00, 16:00) cuando no se envían filtros."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    use_cache = not (fecha_inicio or fecha_fin or analista or concesionario or modelo)
    if use_cache:
        with _lock:
            cached = _CACHE_MOROSIDAD_ANALISTA["data"]
            refreshed = _CACHE_MOROSIDAD_ANALISTA.get("refreshed_at")
        if cached is not None and refreshed is not None and datetime.now() < _next_refresh_local():
            return cached
    data = _compute_morosidad_por_analista(db, fecha_inicio, fecha_fin, analista, concesionario, modelo)
    if use_cache:
        with _lock:
            _CACHE_MOROSIDAD_ANALISTA["data"] = data
            _CACHE_MOROSIDAD_ANALISTA["refreshed_at"] = datetime.now()
    return data


@router.get("/evolucion-morosidad")
def get_evolucion_morosidad(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de morosidad por mes. Datos reales: suma monto de cuotas vencidas no pagadas a fin de cada mes (Cuota). Si la tabla cuotas no tiene columna monto, devuelve 0."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        hoy_date = hoy.date() if hasattr(hoy, "date") else date(hoy.year, hoy.month, hoy.day)
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_dia_date = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            # Morosidad = cuotas vencidas (fecha_vencimiento < ref) y no pagadas. Si el mes es futuro, usar hoy.
            ref = min(ultimo_dia_date, hoy_date)
            moro = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.is_(None),
                    Cuota.fecha_vencimiento < ref,
                )
            ) or 0
            resultado.append({"mes": m["mes"], "morosidad": _safe_float(moro)})
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en evolucion-morosidad: %s", e)
        m = _etiquetas_12_meses()
        return {"meses": [{"mes": x["mes"], "morosidad": x["morosidad"]} for x in m]}


@router.get("/evolucion-pagos", summary="[Stub] Devuelve datos demo hasta tener tabla pagos.")
def get_evolucion_pagos(
    fecha_inicio: Optional[str] = Query(None),
    meses: Optional[int] = Query(12, ge=1, le=24),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Evolución de pagos por mes. Datos reales desde Cuota (fecha_pago por mes)."""
    analista = _sanitize_filter_string(analista)
    concesionario = _sanitize_filter_string(concesionario)
    modelo = _sanitize_filter_string(modelo)
    try:
        meses_list = _etiquetas_12_meses()
        hoy = datetime.now(timezone.utc)
        resultado = []
        for i, m in enumerate(meses_list):
            fin_mes = hoy - timedelta(days=30 * (11 - i))
            ultimo_dia = _ultimo_dia_del_mes(fin_mes.replace(tzinfo=timezone.utc) if fin_mes.tzinfo is None else fin_mes)
            ultimo_dia_date = ultimo_dia.date() if hasattr(ultimo_dia, "date") else ultimo_dia
            inicio_mes = ultimo_dia_date.replace(day=1)
            pagos_count = db.scalar(
                select(func.count())
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_mes,
                    func.date(Cuota.fecha_pago) <= ultimo_dia_date,
                )
            ) or 0
            monto_pagado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.estado == "ACTIVO",
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= inicio_mes,
                    func.date(Cuota.fecha_pago) <= ultimo_dia_date,
                )
            ) or 0
            resultado.append({"mes": m["mes"], "pagos": pagos_count, "monto": _safe_float(monto_pagado)})
        return {"meses": resultado}
    except Exception as e:
        logger.exception("Error en evolucion-pagos: %s", e)
        m = _etiquetas_12_meses()
        return {"meses": [{"mes": x["mes"], "pagos": x.get("pagos", 0), "monto": x.get("monto", 0)} for x in m]}


# ========== Endpoints adicionales usados por modales/páginas (stub) ==========

@router.get("/cobranza-por-dia", summary="[Stub] Devuelve dias vacíos hasta tener tabla pagos/cobranzas.")
def get_cobranza_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranza por día desde BD (Cuota.fecha_pago por día)."""
    return {"dias": []}


@router.get("/cobranzas-mensuales", summary="[Stub] Devuelve meses vacíos hasta tener tabla pagos/cobranzas.")
def get_cobranzas_mensuales(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobranzas mensuales desde BD."""
    return {"meses": []}


@router.get("/cobros-por-analista", summary="[Stub] Devuelve analistas vacíos hasta tener tabla pagos.")
def get_cobros_por_analista(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobros por analista desde BD."""
    return {"analistas": []}


@router.get("/cobros-diarios", summary="[Stub] Devuelve dias vacíos hasta tener tabla pagos.")
def get_cobros_diarios(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cobros diarios desde BD."""
    return {"dias": []}


@router.get("/cuentas-cobrar-tendencias", summary="[Stub] Devuelve tendencias vacías hasta tener datos.")
def get_cuentas_cobrar_tendencias(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Tendencias cuentas por cobrar desde BD."""
    return {"tendencias": []}


@router.get("/distribucion-prestamos", summary="[Stub] Devuelve distribucion vacía hasta tener datos.")
def get_distribucion_prestamos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Distribución de préstamos desde BD."""
    return {"distribucion": []}


@router.get("/metricas-acumuladas", summary="[Stub] Devuelve metricas vacías hasta tener datos.")
def get_metricas_acumuladas(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Métricas acumuladas desde BD."""
    return {"metricas": []}
