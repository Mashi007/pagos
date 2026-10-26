"""Filtros del reporte Por cédula: abonos operativos (ANULADO*/DUPLICADO)."""

from __future__ import annotations

from app.api.v1.endpoints.reportes.reportes_cedula import _expr_pago_operativo


def test_expr_pago_operativo_excluye_anulado_y_duplicado():
    expr = _expr_pago_operativo()
    sql = str(expr.compile(compile_kwargs={"literal_binds": False})).upper()
    assert "ANULADO" in sql
    assert "DUPLICADO" in sql
