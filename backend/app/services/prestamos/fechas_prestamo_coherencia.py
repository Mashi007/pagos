"""Coherencia entre fecha_aprobacion (datetime) y fecha_base_calculo (date).

Regla de negocio:
- La fecha de aprobacion/desembolso se ingresa manualmente (formularios / API explicita).
- fecha_base_calculo es siempre la misma fecha calendario que fecha_aprobacion (copia).
- Sin fecha_aprobacion no se inventa fecha_base_calculo (ni desde fecha_registro, ni hoy).
- No se borra fecha_base_calculo solo por no tener aprobacion (datos legados); alinear solo copia el dia cuando hay aprobacion.
- No se usa fecha_registro como aprobacion ni como base de calculo.
- Al persistir fecha_aprobacion, fecha_registro es el inicio del día calendario **anterior** (alta lógica un día antes).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta


def rellenar_fecha_aprobacion_desde_base_si_falta(row: object) -> None:
    """Copia el día de fecha_base_calculo a fecha_aprobacion si esta sigue NULL (legado en BD).

    Permite persistir otros campos (p. ej. observaciones) sin 400 cuando el estado exige aprobación
    y solo existía base de cálculo histórica.
    """
    fa = getattr(row, "fecha_aprobacion", None)
    if fa is not None:
        return
    fb = getattr(row, "fecha_base_calculo", None)
    if fb is None:
        return
    if isinstance(fb, datetime):
        d = fb.date() if hasattr(fb, "date") else None
    elif isinstance(fb, date):
        d = fb
    else:
        return
    if d is None:
        return
    setattr(row, "fecha_aprobacion", datetime.combine(d, datetime.min.time()))


def alinear_fecha_aprobacion_y_base_calculo(row: object) -> None:
    """Sincroniza fecha_base_calculo con el dia de fecha_aprobacion.

    Si hay fecha_aprobacion, la base de calculo debe ser el mismo dia calendario.
    Si no hay fecha_aprobacion, no se modifica fecha_base_calculo: borrar la base en
    cada guardado rompia datos legados (solo base) y disparaba 400 al validar estados.
    """
    fa = getattr(row, "fecha_aprobacion", None)
    if fa is not None:
        ap_d = (
            fa.date()
            if hasattr(fa, "date") and callable(getattr(fa, "date", None))
            else fa
        )
        if getattr(row, "fecha_base_calculo", None) != ap_d:
            setattr(row, "fecha_base_calculo", ap_d)


def fecha_registro_naive_un_dia_antes_aprobacion(fecha_aprobacion: date | datetime) -> datetime:
    """Medianoche naive del día calendario previo a la fecha de aprobación."""
    if isinstance(fecha_aprobacion, datetime):
        d = fecha_aprobacion.date()
    elif isinstance(fecha_aprobacion, date):
        d = fecha_aprobacion
    else:
        raise TypeError("fecha_aprobacion debe ser date o datetime")
    prev = d - timedelta(days=1)
    return datetime.combine(prev, time.min)


def fecha_para_amortizacion(p: object) -> date | None:
    """
    Fecha calendario base para generar o recalcular cuotas (misma regla en API y AmortizacionService).

    - Prioridad: fecha_base_calculo (copia del día de fecha_aprobacion en flujos vigentes).
    - Si fecha_base_calculo es NULL (legado): parte fecha de fecha_aprobacion.
    - Sin ambas: None (no inventar desde fecha_registro ni hoy).
    """
    fb = getattr(p, "fecha_base_calculo", None)
    if fb is not None:
        if isinstance(fb, datetime):
            return fb.date()
        if isinstance(fb, date):
            return fb
    fa = getattr(p, "fecha_aprobacion", None)
    if not fa:
        return None
    if hasattr(fa, "date") and callable(getattr(fa, "date", None)):
        return fa.date()
    if isinstance(fa, date):
        return fa
    return None
