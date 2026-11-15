"""Filtros del reporte Por cédula: abonos operativos (ANULADO*/DUPLICADO)."""

from __future__ import annotations

from app.api.v1.endpoints.reportes.reportes_cedula import _expr_pago_operativo


def test_expr_pago_operativo_excluye_anulado_y_duplicado():
    expr = _expr_pago_operativo()
    sql = str(expr.compile(compile_kwargs={"literal_binds": True})).upper()
    assert "ANULADO" in sql
    assert "DUPLICADO" in sql


def test_monto_atrasado_usa_saldo_pendiente():
    """Un abono parcial debe reducir el monto atrasado (monto − total_pagado)."""
    from app.api.v1.endpoints.reportes.reportes_cedula import _expr_saldo_cuota

    sql = str(_expr_saldo_cuota().compile()).lower()
    assert "greatest" in sql
    assert "total_pagado" in sql
    assert "monto" in sql


def test_excel_incluye_hora_de_generacion():
    import io

    import openpyxl

    from app.api.v1.endpoints.reportes.reportes_cedula import _generar_excel_por_cedula

    contenido = _generar_excel_por_cedula(
        [
            {
                "id_prestamo": 1,
                "cedula": "V1",
                "nombre": "A",
                "email": "",
                "total_financiamiento": 100,
                "total_abono": 40,
                "cuotas_totales": 2,
                "cuotas_pagadas": 0,
                "cuotas_atrasadas": 1,
                "monto_cuotas_atrasadas": 10,
            }
        ],
        "2026-11-15 02:50:00",
    )
    ws = openpyxl.load_workbook(io.BytesIO(contenido)).active
    assert "2026-11-15 02:50:00" in str(ws.cell(row=2, column=1).value)
    encabezados = [c.value for c in ws[5]]
    assert "Saldo atrasado ($)" in encabezados
