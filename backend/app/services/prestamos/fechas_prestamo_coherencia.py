"""Coherencia entre fecha_aprobacion (datetime) y fecha_base_calculo (date).

Regla de negocio:
- La fecha de aprobacion/desembolso se ingresa manualmente (formularios / API explicita).
- fecha_base_calculo es siempre la misma fecha calendario que fecha_aprobacion (copia).
- Sin fecha_aprobacion no se inventa fecha_base_calculo (ni desde fecha_registro, ni hoy).
- No se borra fecha_base_calculo solo por no tener aprobacion (datos legados); alinear solo copia el dia cuando hay aprobacion.
- No se usa fecha_registro como aprobacion ni como base de calculo.
"""

from __future__ import annotations

from datetime import date, datetime


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
