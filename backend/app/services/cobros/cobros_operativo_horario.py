"""Horario operativo Cobros (America/Caracas): límites de exportación en pico."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings

TZ_CARACAS = ZoneInfo("America/Caracas")


def ahora_caracas() -> datetime:
    return datetime.now(TZ_CARACAS)


def cobros_export_peak_enabled() -> bool:
    return bool(getattr(settings, "COBROS_EXPORT_PEAK_LIMIT_ENABLED", True))


def cobros_export_peak_hour_start() -> int:
    return int(getattr(settings, "COBROS_EXPORT_PEAK_HOUR_START", 7))


def cobros_export_peak_hour_end() -> int:
    return int(getattr(settings, "COBROS_EXPORT_PEAK_HOUR_END", 22))


def cobros_export_peak_max_rows() -> int:
    return max(1, int(getattr(settings, "COBROS_EXPORT_PEAK_MAX_ROWS", 400)))


def en_horario_pico_export_cobros(now: Optional[datetime] = None) -> bool:
    """
    True entre COBROS_EXPORT_PEAK_HOUR_START y COBROS_EXPORT_PEAK_HOUR_END (inclusive, hora Caracas).
    """
    if not cobros_export_peak_enabled():
        return False
    dt = now if now is not None else ahora_caracas()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_CARACAS)
    else:
        dt = dt.astimezone(TZ_CARACAS)
    h = dt.hour
    start = cobros_export_peak_hour_start()
    end = cobros_export_peak_hour_end()
    if start <= end:
        return start <= h <= end
    # Ventana nocturna (p. ej. 22–6): pico fuera del tramo diurno.
    return h >= start or h <= end


def mensaje_limite_export_pico(*, filas: int, max_filas: int) -> str:
    end = cobros_export_peak_hour_end()
    return (
        f"En horario pico ({cobros_export_peak_hour_start():02d}:00–{end:02d}:00 Caracas) "
        f"el Excel de corrección masiva admite hasta {max_filas} filas por descarga "
        f"(esta consulta devolvería {filas}). "
        "Acote con cédula o institución, repita en varias descargas, "
        f"o intente después de las {end:02d}:00."
    )
