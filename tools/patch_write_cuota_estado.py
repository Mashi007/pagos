from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "app" / "services" / "cuota_estado.py"

TARGET.write_text(
    '''"""
Estado de cuota unificado (America/Caracas).

Reglas de negocio:
- Pagado: cuota cubierta al 100% y fecha de vencimiento <= fecha de referencia.
- Pago adelantado: cubierta al 100% y fecha de vencimiento > fecha de referencia.
- Pendiente: sin cubrir al 100%, sin retraso (el dia del vencimiento cuenta como al corriente).
- Parcial: sin cubrir al 100%, sin retraso, con abonos.
- Vencido: sin cubrir al 100%, 1..91 dias calendario despues del vencimiento.
- Mora: sin cubrir al 100%, 92+ dias calendario despues del vencimiento.

Conciliacion bancaria no altera el estado de cuota para el cliente.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ_NEGOCIO = "America/Caracas"
_TOL_MONTO = 0.01
_MORA_DESDE_DIAS_RETRASO = 92


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

    if dias_ret >= _MORA_DESDE_DIAS_RETRASO:
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
''',
    encoding="utf-8",
)
print("OK", TARGET)
