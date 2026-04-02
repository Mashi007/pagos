"""
Fechas de referencia para filtros y agregados (SQLAlchemy). No usa fecha_registro.

Hay dos criterios legitimos que no se pueden unificar en un solo COALESCE cuando
en legado `fecha_base_calculo` (inicio de cuotas) != `date(fecha_aprobacion)`:

1) **Cuotas / cartera / listados por “inicio operacion” en BD**:
   priorizar `fecha_base_calculo`, luego aprobacion, luego requerimiento.

2) **Conteos por “mes de aprobacion” administrativa**:
   priorizar `date(fecha_aprobacion)`, luego base, luego requerimiento.

En altas y actualizaciones vigentes, `fecha_base_calculo` solo se rellena copiando el dia de
`fecha_aprobacion` (ingreso manual); no se usa `fecha_registro` como sustituto.

Los endpoints que importaban `prestamo_fecha_referencia_negocio` siguen el criterio (1)
para alinear con la tabla de amortizacion existente cuando en legado base y aprobacion difieren.
"""

from sqlalchemy import func

from app.models.prestamo import Prestamo


def prestamo_fecha_referencia_negocio():
    """
    Coalesce para alinear con **amortizacion ya generada** (fecha_base_calculo primero).
    """
    return func.coalesce(
        Prestamo.fecha_base_calculo,
        func.date(Prestamo.fecha_aprobacion),
        Prestamo.fecha_requerimiento,
    )


def prestamo_fecha_referencia_por_aprobacion():
    """
    Coalesce por **fecha de aprobacion** cuando el reporte debe ser por mes de aprobacion,
    no por el inicio de cuotas legado.
    """
    return func.coalesce(
        func.date(Prestamo.fecha_aprobacion),
        Prestamo.fecha_base_calculo,
        Prestamo.fecha_requerimiento,
    )
