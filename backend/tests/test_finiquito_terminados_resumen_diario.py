# -*- coding: utf-8 -*-
"""Resumen diario finiquito: ingresos + terminados por dia."""

from datetime import date, datetime, timezone

from app.api.v1.endpoints.finiquito.routes import (
    _fecha_historial_a_date_caracas,
)


def test_fecha_historial_a_date_caracas_utc_naive():
    dt = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
    d = _fecha_historial_a_date_caracas(dt)
    assert isinstance(d, date)


def test_fecha_historial_a_date_caracas_naive_utc_medianoche_caracas():
    """04:00 UTC = 00:00 Caracas (misma fecha calendario)."""
    dt = datetime(2026, 6, 13, 4, 0, 0)
    d = _fecha_historial_a_date_caracas(dt)
    assert d == date(2026, 6, 13)


def test_finiquito_terminados_dia_out_schema_fields():
    from app.schemas.finiquito import FiniquitoTerminadosDiaOut

    row = FiniquitoTerminadosDiaOut(
        fecha="2026-06-12",
        etiqueta="Hoy",
        cantidad=3,
        cantidad_ingresos=5,
    )
    assert row.cantidad == 3
    assert row.cantidad_ingresos == 5


def test_resumen_diario_response_total_ingresos():
    from app.schemas.finiquito import (
        FiniquitoTerminadosDiaOut,
        FiniquitoTerminadosResumenDiarioResponse,
    )

    resp = FiniquitoTerminadosResumenDiarioResponse(
        dias=[
            FiniquitoTerminadosDiaOut(
                fecha="2026-06-11",
                etiqueta="Ayer",
                cantidad=2,
                cantidad_ingresos=4,
            ),
            FiniquitoTerminadosDiaOut(
                fecha="2026-06-12",
                etiqueta="Hoy",
                cantidad=1,
                cantidad_ingresos=0,
            ),
        ],
        total_terminados=10,
        total_en_ventana=3,
        total_ingresos_en_ventana=4,
    )
    assert resp.total_ingresos_en_ventana == 4
    assert len(resp.dias) == 2
