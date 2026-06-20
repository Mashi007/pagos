# -*- coding: utf-8 -*-
"""Resumen diario finiquito: entradas area trabajo + terminados por dia."""

from datetime import date, datetime, timezone

from app.api.v1.endpoints.finiquito.routes import (
    _coerce_a_fecha_caracas,
    _fecha_historial_a_date_caracas,
    _registrar_conteo_dia_caso,
)
from collections import Counter


def test_fecha_historial_a_date_caracas_utc_naive():
    dt = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
    d = _fecha_historial_a_date_caracas(dt)
    assert isinstance(d, date)


def test_fecha_historial_a_date_caracas_naive_utc_medianoche_caracas():
    """04:00 UTC = 00:00 Caracas (misma fecha calendario)."""
    dt = datetime(2026, 6, 13, 4, 0, 0)
    d = _fecha_historial_a_date_caracas(dt)
    assert d == date(2026, 6, 13)


def test_coerce_a_fecha_caracas_datetime_naive_utc():
    dt = datetime(2026, 6, 13, 4, 0, 0)
    assert _coerce_a_fecha_caracas(dt) == date(2026, 6, 13)


def test_registrar_conteo_dia_caso_acepta_datetime_fallback():
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    hoy = date(2026, 6, 13)
    _registrar_conteo_dia_caso(
        ctr,
        vistos,
        406,
        datetime(2026, 6, 13, 4, 0, 0),
        inicio=hoy,
        hoy=hoy,
    )
    assert ctr[hoy.isoformat()] == 1


def test_registrar_conteo_dia_caso_acepta_fecha_sql():
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    hoy = date(2026, 6, 12)
    for cid in (406, 409, 419):
        _registrar_conteo_dia_caso(
            ctr, vistos, cid, hoy, inicio=hoy, hoy=hoy
        )
    assert ctr[hoy.isoformat()] == 3
    assert len(vistos) == 3


def test_registrar_conteo_dia_caso_deduplica_mismo_caso_mismo_dia():
    ctr: Counter[str] = Counter()
    vistos: set[tuple[str, int]] = set()
    hoy = date(2026, 6, 12)
    _registrar_conteo_dia_caso(ctr, vistos, 406, hoy, inicio=hoy, hoy=hoy)
    _registrar_conteo_dia_caso(ctr, vistos, 406, hoy, inicio=hoy, hoy=hoy)
    assert ctr[hoy.isoformat()] == 1


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


def test_flujo_dia_out_schema_fields():
    from app.schemas.finiquito import FiniquitoFlujoDiaOut

    row = FiniquitoFlujoDiaOut(
        fecha="2026-06-12",
        etiqueta="Hoy",
        cantidad_ingresados=4,
        cantidad_revision=3,
        cantidad_trabajo=2,
        cantidad_terminados=1,
    )
    assert row.cantidad_ingresados == 4
    assert row.cantidad_revision == 3
    assert row.cantidad_trabajo == 2
    assert row.cantidad_terminados == 1


def test_flujo_resumen_diario_response_totals():
    from app.schemas.finiquito import (
        FiniquitoFlujoDiaOut,
        FiniquitoFlujoResumenDiarioResponse,
    )

    resp = FiniquitoFlujoResumenDiarioResponse(
        dias=[
            FiniquitoFlujoDiaOut(
                fecha="2026-06-11",
                etiqueta="Ayer",
                cantidad_ingresados=2,
                cantidad_revision=1,
                cantidad_trabajo=1,
                cantidad_terminados=0,
            ),
            FiniquitoFlujoDiaOut(
                fecha="2026-06-12",
                etiqueta="Hoy",
                cantidad_ingresados=3,
                cantidad_revision=2,
                cantidad_trabajo=1,
                cantidad_terminados=1,
            ),
        ],
        total_ingresados_en_ventana=5,
        total_revision_en_ventana=3,
        total_trabajo_en_ventana=2,
        total_terminados_en_ventana=1,
    )
    assert resp.total_ingresados_en_ventana == 5
    assert resp.total_revision_en_ventana == 3
    assert resp.total_trabajo_en_ventana == 2
    assert resp.total_terminados_en_ventana == 1
