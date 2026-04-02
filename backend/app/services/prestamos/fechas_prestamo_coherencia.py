"""Coherencia entre fecha_aprobacion (datetime) y fecha_base_calculo (date).

Regla de negocio:
- La fecha de aprobacion/desembolso se ingresa manualmente (formularios / API explicita).
- fecha_base_calculo es siempre la misma fecha calendario que fecha_aprobacion (copia).
- Sin fecha_aprobacion no se inventa fecha_base_calculo (ni desde base legada, ni fecha_registro, ni hoy).
- No se usa fecha_registro como aprobacion ni como base de calculo.
"""

from __future__ import annotations

from datetime import datetime


def alinear_fecha_aprobacion_y_base_calculo(row: object) -> None:
    """Sincroniza fecha_base_calculo con el dia de fecha_aprobacion; limpia base si no hay aprobacion."""
    fa = getattr(row, "fecha_aprobacion", None)
    if fa is not None:
        ap_d = (
            fa.date()
            if hasattr(fa, "date") and callable(getattr(fa, "date", None))
            else fa
        )
        if getattr(row, "fecha_base_calculo", None) != ap_d:
            setattr(row, "fecha_base_calculo", ap_d)
        return
    if hasattr(row, "fecha_base_calculo"):
        setattr(row, "fecha_base_calculo", None)
