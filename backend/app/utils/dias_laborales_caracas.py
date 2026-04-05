"""Dias laborales (lunes a viernes) en calendario America/Caracas."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ_CARACAS = ZoneInfo("America/Caracas")


def fecha_hoy_caracas(ahora: datetime | None = None) -> date:
    """Fecha calendario actual en Caracas (negocio)."""
    if ahora is None:
        return datetime.now(TZ_CARACAS).date()
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=TZ_CARACAS)
    return ahora.astimezone(TZ_CARACAS).date()


def sumar_dias_laborales_lun_vie(fecha_inicio: date, n: int) -> date:
    """
    n-ésimo dia laboral (lun-vie) contando desde fecha_inicio: el dia de inicio
    cuenta como 1 si es laboral; fines de semana no cuentan en el conteo.
    """
    if n <= 0:
        return fecha_inicio
    cur = fecha_inicio
    counted = 0
    while counted < n:
        if cur.weekday() < 5:
            counted += 1
            if counted == n:
                return cur
        cur += timedelta(days=1)
    return cur
