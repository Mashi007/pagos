"""Fecha de negocio y mora en zona America/Caracas."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.cuota_estado import dias_retraso_desde_vencimiento

from .constants import TZ_NEGOCIO


def _hoy_local() -> date:
    """
    Retorna la fecha actual en la zona horaria del negocio (America/Caracas).

    Usada para calcular dias_mora, detectar vencimientos, y acciones automáticas.
    """
    tz = ZoneInfo(TZ_NEGOCIO)
    return datetime.now(tz).date()


def _calcular_dias_mora(fecha_vencimiento: date) -> int:
    """Dias calendario desde fecha_vencimiento hasta hoy (America/Caracas), no negativos."""
    return dias_retraso_desde_vencimiento(fecha_vencimiento, _hoy_local())
