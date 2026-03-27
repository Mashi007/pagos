"""
Estado de cuota unificado (America/Caracas).

Reglas de negocio:
- Pagado: cuota cubierta al 100% y fecha de vencimiento <= fecha de referencia.
- Pago adelantado: cubierta al 100% y fecha de vencimiento > fecha de referencia.
- Pendiente: sin cubrir al 100%, sin retraso (el dia del vencimiento cuenta como al corriente).
- Parcial: sin cubrir al 100%, sin retraso, con abonos.
- Vencido: sin cubrir al 100%, desde 1 dia de retraso hasta antes del umbral de mora.
- Mora: sin cubrir al 100%, desde el dia siguiente de cumplir 4 meses calendario del vencimiento.

Conciliacion bancaria no altera el estado de cuota para el cliente.

Persistencia en BD:
- La columna `cuotas.estado` debe coincidir con `clasificar_estado_cuota(total_pagado, monto, vencimiento, hoy Caracas)`.
- GET `/prestamos/{id}/cuotas` y exportaciones llaman a `sincronizar_columna_estado_cuotas` para alinear la columna
  con el mismo codigo que se devuelve en JSON (`estado` / `estado_etiqueta`). Asi informes que lean solo la tabla
  ven el mismo estado que la API.

"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ_NEGOCIO = "America/Caracas"
_TOL_MONTO = 0.01
_MORA_DESDE_MESES = 4


def hoy_negocio() -> date:
    """Fecha calendario actual en America/Caracas."""
    return datetime.now(ZoneInfo(TZ_NEGOCIO)).date()


def _fecha_vencimiento_date(fecha_vencimiento: date | datetime | None) -> date | None:
    if fecha_vencimiento is None:
        return None
    if isinstance(fecha_vencimiento, datetime):
        return fecha_vencimiento.date()
    return fecha_vencimiento


def dias_retraso_desde_vencimiento(
    fecha_vencimiento: date | datetime | None,
    fecha_referencia: date | None = None,
) -> int:
    """
    Dias calendario desde fecha_vencimiento hasta fecha_referencia (no negativos).
    El dia del vencimiento devuelve 0; el dia siguiente, 1.
    """
    ref = fecha_referencia or hoy_negocio()
    fv = _fecha_vencimiento_date(fecha_vencimiento)
    if fv is None:
        return 0
    return max(0, (ref - fv).days)


def _sumar_meses_calendario(fecha_base: date, meses: int) -> date:
    """Suma meses calendario conservando dia, ajustando al ultimo dia valido del mes destino."""
    month_index = (fecha_base.month - 1) + meses
    year = fecha_base.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(fecha_base.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _es_mora_por_4_meses(fv: date | None, ref: date) -> bool:
    """
    Regla de mora por meses calendario:
    - Se cumplen 4 meses calendario exactos desde la fecha de vencimiento.
    - MORA aplica desde el dia siguiente.
    """
    if fv is None:
        return False
    fecha_cumple_4m = _sumar_meses_calendario(fv, _MORA_DESDE_MESES)
    inicio_mora = fecha_cumple_4m + timedelta(days=1)
    return ref >= inicio_mora


def clasificar_estado_cuota(
    total_pagado: float,
    monto_cuota: float,
    fecha_vencimiento: date | datetime | None,
    fecha_referencia: date | None = None,
) -> str:
    """
    Devuelve: PAGADO | PAGO_ADELANTADO | PENDIENTE | PARCIAL | VENCIDO | MORA
    """
    ref = fecha_referencia or hoy_negocio()
    paid = float(total_pagado or 0)
    monto = float(monto_cuota or 0)
    fv = _fecha_vencimiento_date(fecha_vencimiento)

    if monto > 0 and paid >= monto - _TOL_MONTO:
        if fv is not None and fv > ref:
            return "PAGO_ADELANTADO"
        return "PAGADO"

    dias_ret = dias_retraso_desde_vencimiento(fv, ref)
    if dias_ret == 0:
        if paid > 0.001:
            return "PARCIAL"
        return "PENDIENTE"

    if _es_mora_por_4_meses(fv, ref):
        return "MORA"
    return "VENCIDO"


def estado_cuota_para_mostrar(
    total_pagado: float,
    monto_cuota: float,
    fecha_vencimiento: date | datetime | None,
    fecha_referencia: date | None = None,
) -> str:
    """Alias para informes, API de cuotas y PDF."""
    return clasificar_estado_cuota(
        total_pagado, monto_cuota, fecha_vencimiento, fecha_referencia
    )


def etiqueta_estado_cuota(codigo: str) -> str:
    """Texto para UI/PDF (misma nomenclatura que la tabla de amortización en frontend)."""
    c = (codigo or "").strip().upper()
    labels = {
        "PENDIENTE": "Pendiente",
        "PARCIAL": "Pendiente parcial",
        "VENCIDO": "Vencido",
        "MORA": "Mora (4 meses+)",
        "PAGADO": "Pagado",
        "PAGO_ADELANTADO": "Pago adelantado",
        "PAGADA": "Pagado",
    }
    return labels.get(c, codigo.strip() if codigo else "-")


def calcular_estado_cuota_desde_fila(c: object, fecha_referencia: date | None = None) -> str:
    """Codigo alineado con GET /prestamos/{id}/cuotas (misma regla que `estado_cuota_para_mostrar`)."""
    ref = fecha_referencia or hoy_negocio()
    monto = float(getattr(c, "monto", None) or 0)
    total = float(getattr(c, "total_pagado", None) or 0)
    fv = getattr(c, "fecha_vencimiento", None)
    fv_date = fv.date() if fv is not None and hasattr(fv, "date") else fv
    return clasificar_estado_cuota(total, monto, fv_date, ref)


def sincronizar_columna_estado_cuotas(db: object, cuotas: list, *, commit: bool = False) -> int:
    """
    Actualiza `cuotas.estado` en la sesion si difiere del calculado.
    Si commit=True, hace commit (usar en endpoints que no hagan commit despues).
    """
    changed = 0
    for c in cuotas:
        nuevo = calcular_estado_cuota_desde_fila(c)
        cur = (getattr(c, "estado", None) or "").strip().upper()
        if cur != nuevo:
            setattr(c, "estado", nuevo)
            changed += 1
    if changed and commit:
        db.commit()
    return changed




# SQL PostgreSQL (misma regla que clasificar_estado_cuota).
# Version con SUM(cuota_pagos): util cuando se quiere verdad desde aplicaciones sin confiar en columna.
SQL_PG_ESTADO_CUOTA_CASE_CORRELATED = """CASE
  WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0)
       >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
END"""

# Misma logica que GET lista de cuotas / amortizacion (_listado_cuotas_prestamo_dicts usa c.total_pagado).
# Usar en reportes morosidad para que el conteo coincida con la UI.
# Comparaciones en numeric SIN ROUND: clasificar_estado_cuota usa paid >= monto - 0.01 (sin redondear antes).
# Redondear en SQL podia marcar PAGADO/VENCIDO distinto que Python y variar el conteo MORA.
SQL_PG_ESTADO_CUOTA_CASE_CORRELATED_TOTAL_PAGADO = """CASE
  WHEN COALESCE(c.total_pagado, 0)::numeric >= COALESCE(c.monto_cuota, 0)::numeric - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE(c.total_pagado, 0)::numeric > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
END"""

SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE = """CASE
  WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
END"""

