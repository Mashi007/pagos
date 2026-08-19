from datetime import date
from decimal import Decimal

from app.services.reporte_cedulas_cuota_hoja import (
    cuota_unica_de_prestamos,
    filas_cedula_cuota,
    generar_excel_cedulas_cuota,
    parsear_cedulas_csv,
    pendiente_vencido,
)


def test_parsear_salta_encabezado_y_conserva_orden():
    raw = "Cédula\nE84491751\nV18739623\n".encode("utf-8")
    assert parsear_cedulas_csv(raw) == ["E84491751", "V18739623"]


def test_cuota_unica_un_aprobado():
    assert cuota_unica_de_prestamos([("APROBADO", Decimal("180.00"))]) == Decimal(
        "180.00"
    )


def test_cuota_unica_sin_prestamo_no_inventa():
    assert cuota_unica_de_prestamos([]) is None


def test_cuota_unica_montos_distintos_no_elige():
    assert (
        cuota_unica_de_prestamos(
            [("APROBADO", Decimal("180")), ("APROBADO", Decimal("200"))]
        )
        is None
    )


def test_cuota_unica_prioriza_aprobado():
    assert cuota_unica_de_prestamos(
        [("LIQUIDADO", Decimal("50")), ("APROBADO", Decimal("180"))]
    ) == Decimal("180.00")


def test_filas_celda_vacia_si_no_hay_cuota():
    filas = filas_cedula_cuota(
        ["E84491751", "V999"],
        {"E84491751": [("APROBADO", Decimal("180.5"))]},
    )
    assert filas[0]["cuota"] == 180.5
    assert filas[1]["cedula"] == "V999"
    assert filas[1]["cuota"] is None


def test_cuota_unica_usa_desistimiento_si_no_hay_aprobado():
    assert cuota_unica_de_prestamos(
        [("DESISTIMIENTO", Decimal("175.00"))]
    ) == Decimal("175.00")


def test_pendiente_vencido_solo_si_ya_vencio_y_hay_saldo():
    ref = date(2026, 8, 18)
    assert pendiente_vencido(
        Decimal("180"), Decimal("0"), date(2026, 1, 15), None, ref
    ) == Decimal("180.00")
    assert (
        pendiente_vencido(
            Decimal("180"), Decimal("180"), date(2026, 1, 15), date(2026, 1, 20), ref
        )
        is None
    )
    assert (
        pendiente_vencido(
            Decimal("180"), Decimal("0"), date(2026, 8, 18), None, ref
        )
        is None
    )


def test_filas_ponen_vencido_en_mes_de_vencimiento():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("180.00"), "2026-03": Decimal("90.00")}},
    )
    assert filas[0]["cuota"] == 180.0
    assert filas[0]["2026-01"] == 180.0
    assert filas[0]["2026-02"] is None
    assert filas[0]["2026-03"] == 90.0


def test_excel_no_escribe_cero_cuando_falta_cuota():
    import openpyxl
    from io import BytesIO

    content = generar_excel_cedulas_cuota(
        [
            {
                "cedula": "E1",
                "cuota": 180.0,
                "2026-01": 180.0,
                "2026-02": None,
            },
            {"cedula": "V2", "cuota": None},
        ]
    )
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active
    assert ws["A1"].value == "Cédula"
    assert ws["C1"].value == "Enero 2026"
    assert ws["J1"].value == "Agosto 2026"
    assert ws["B2"].value == 180.0
    assert ws["C2"].value == 180.0
    assert ws["D2"].value is None
    assert ws["A3"].value == "V2"
    assert ws["B3"].value is None
