from datetime import date
from decimal import Decimal

from app.services.reporte_cedulas_cuota_hoja import (
    clave_mes_con_arrastre,
    cuota_unica_de_prestamos,
    estado_actual_de_prestamos,
    filas_cedula_cuota,
    generar_excel_cedulas_cuota,
    nros_ultima_cuota_vencida,
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


def test_filas_cruza_prefijo_e_con_v_en_sistema():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"V84491751": [("APROBADO", Decimal("180.00"))]},
        {"V84491751": {"2026-01": Decimal("180.00")}},
    )
    assert filas[0]["cedula"] == "E84491751"
    assert filas[0]["estado"] == "APROBADO"
    assert filas[0]["cuota"] == 180.0
    assert filas[0]["2026-01"] == 180.0


def test_cuota_unica_usa_estado_en_revision():
    assert cuota_unica_de_prestamos(
        [("EN_REVISION", Decimal("160.00"))]
    ) == Decimal("160.00")


def test_estado_actual_prioriza_aprobado():
    assert estado_actual_de_prestamos(
        [("LIQUIDADO", Decimal("50")), ("APROBADO", Decimal("180"))]
    ) == "APROBADO"
    assert estado_actual_de_prestamos([("DESISTIMIENTO", 1)]) == "DESISTIMIENTO"
    assert estado_actual_de_prestamos([]) is None


def test_filas_celda_vacia_si_no_hay_cuota():
    filas = filas_cedula_cuota(
        ["E84491751", "V999"],
        {"E84491751": [("APROBADO", Decimal("180.5"))]},
    )
    assert filas[0]["cuota"] == 180.5
    assert filas[0]["estado"] == "APROBADO"
    assert filas[1]["cedula"] == "V999"
    assert filas[1]["cuota"] is None
    assert filas[1]["estado"] is None


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


def test_arrastre_vencidos_anteriores_a_enero_van_a_enero():
    assert clave_mes_con_arrastre(date(2025, 11, 15)) == "2026-01"
    assert clave_mes_con_arrastre(date(2024, 6, 1)) == "2026-01"
    assert clave_mes_con_arrastre(date(2026, 2, 10)) == "2026-02"
    assert clave_mes_con_arrastre(date(2026, 9, 1)) is None
    ref = date(2026, 8, 18)
    assert pendiente_vencido(
        Decimal("200"), Decimal("0"), date(2025, 12, 5), None, ref
    ) == Decimal("200.00")
    assert (
        pendiente_vencido(
            Decimal("200"), Decimal("200"), date(2025, 12, 5), date(2026, 1, 2), ref
        )
        is None
    )


def test_nros_todas_vencidas_antes_de_diciembre_ponen_ultima_en_todos_los_meses():
    ref = date(2026, 8, 18)
    items = [
        (n, date(2025, n, 5), Decimal("100"), Decimal("0"), None, 12)
        for n in range(1, 13)
    ]
    nros = nros_ultima_cuota_vencida(items, ref)
    assert nros["2026-01"] == 12
    assert nros["2026-08"] == 12
    assert set(nros.values()) == {12}


def test_filas_ponen_nro_cuota_antes_de_vencido():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("180.00")}},
        {},
        {"E84491751": {k: 12 for k in (
            "2026-01", "2026-02", "2026-03", "2026-04",
            "2026-05", "2026-06", "2026-07", "2026-08",
        )}},
    )
    assert filas[0]["nro_2026-01"] == 12
    assert filas[0]["nro_2026-08"] == 12


def test_filas_acumulan_arrastre_desde_enero():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("200.00"), "2026-02": Decimal("180.00")}},
    )
    assert filas[0]["2026-01"] == 200.0
    assert filas[0]["2026-02"] == 380.0


def test_filas_acumulan_vencidos_hasta_cada_mes():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("180.00"), "2026-03": Decimal("90.00")}},
        {"E84491751": {"2026-01": Decimal("50.00"), "2026-02": Decimal("40.00")}},
    )
    assert filas[0]["cuota"] == 180.0
    assert filas[0]["2026-01"] == 180.0
    assert filas[0]["2026-02"] == 130.0
    assert filas[0]["2026-03"] == 180.0
    assert filas[0]["2026-04"] == 180.0
    assert filas[0]["pagos_2026-01"] == 50.0
    assert filas[0]["pagos_2026-02"] == 40.0
    assert filas[0]["pagos_2026-03"] is None
    assert filas[0]["saldo_2026-01"] == 130.0
    assert filas[0]["saldo_2026-02"] == 90.0
    assert filas[0]["saldo_2026-03"] == 180.0


def test_amortizacion_sin_pago_traslada_deuda_mas_nueva_cuota():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("80"))]},
        {"E84491751": {"2026-01": Decimal("720.00"), "2026-02": Decimal("80.00")}},
        {},
    )
    assert filas[0]["2026-01"] == 720.0
    assert filas[0]["saldo_2026-01"] == 720.0
    assert filas[0]["2026-02"] == 800.0
    assert filas[0]["saldo_2026-02"] == 800.0


def test_amortizacion_pago_mayor_no_deja_vencido_negativo():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("80"))]},
        {"E84491751": {"2026-01": Decimal("100.00")}},
        {"E84491751": {"2026-01": Decimal("884.00")}},
    )
    assert filas[0]["2026-01"] == 100.0
    assert filas[0]["saldo_2026-01"] == 0.0
    assert filas[0]["2026-08"] == 0.0
    assert filas[0]["saldo_2026-08"] == 0.0


def test_saldo_sin_pagos_del_mes_igual_al_vencido():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("720.00")}},
        {},
    )
    assert filas[0]["pagos_2026-01"] is None
    assert filas[0]["saldo_2026-01"] == 720.0


def test_saldo_no_resta_pagos_anteriores_a_enero():
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("180"))]},
        {"E84491751": {"2026-01": Decimal("720.00")}},
        {"E84491751": {"2025-12": Decimal("900.00")}},
    )
    assert filas[0]["pagos_2026-01"] is None
    assert filas[0]["saldo_2026-01"] == 720.0


def test_excel_no_escribe_cero_cuando_falta_cuota():
    import openpyxl
    from io import BytesIO

    content = generar_excel_cedulas_cuota(
        [
            {
                "cedula": "E1",
                "estado": "APROBADO",
                "cuota": 180.0,
                "2026-01": 180.0,
                "pagos_2026-01": 50.0,
                "saldo_2026-01": 130.0,
                "nro_2026-01": 12,
                "2026-02": None,
            },
            {"cedula": "V2", "estado": None, "cuota": None},
        ]
    )
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active
    assert ws["A1"].value == "Cédula"
    assert ws["B1"].value == "Estado"
    assert ws["C1"].value == "Cuota"
    assert ws["D1"].value == "Enero 2026"
    assert ws["D2"].value == "N° cuota"
    assert ws["E2"].value == "Vencido"
    assert ws["F2"].value == "Pagos"
    assert ws["G2"].value == "Saldo"
    assert ws["B3"].value == "APROBADO"
    assert ws["C3"].value == 180.0
    assert ws["D3"].value == 12
    assert ws["E3"].value == 180.0
    assert ws["F3"].value == 50.0
    assert ws["G3"].value == 130.0
    assert ws["A4"].value == "V2"
