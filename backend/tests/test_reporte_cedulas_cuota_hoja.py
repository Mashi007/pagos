from datetime import date
from decimal import Decimal
from io import BytesIO

from app.services.reporte_cedulas_cuota_hoja import (
    FECHA_CORTE_JUNIO,
    conteo_cuotas_en_mora,
    cuota_unica_de_prestamos,
    estado_actual_de_prestamos,
    filas_cedula_cuota,
    generar_excel_cedulas_cuota,
    metricas_corte_mora,
    parsear_cedulas_csv,
    pendiente_vencido,
    saldo_vencido_credito,
    _items_cuotas_para_informe,
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


def test_cuota_unica_usa_estado_en_revision():
    assert cuota_unica_de_prestamos(
        [("EN_REVISION", Decimal("160.00"))]
    ) == Decimal("160.00")


def test_cuota_unica_usa_desistimiento_si_no_hay_aprobado():
    assert cuota_unica_de_prestamos(
        [("DESISTIMIENTO", Decimal("175.00"))]
    ) == Decimal("175.00")


def test_estado_actual_prioriza_aprobado():
    assert estado_actual_de_prestamos(
        [("LIQUIDADO", Decimal("50")), ("APROBADO", Decimal("180"))]
    ) == "APROBADO"
    assert estado_actual_de_prestamos([("DESISTIMIENTO", 1)]) == "DESISTIMIENTO"
    assert estado_actual_de_prestamos([]) is None


def test_filas_cruza_prefijo_e_con_v_en_sistema():
    items = [
        (1, date(2025, 9, 1), Decimal("180"), Decimal("0"), None, 12),
        (2, date(2025, 10, 1), Decimal("180"), Decimal("0"), None, 12),
        (3, date(2025, 11, 1), Decimal("180"), Decimal("0"), None, 12),
        (4, date(2025, 12, 1), Decimal("180"), Decimal("0"), None, 12),
    ]
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"V84491751": [("LIQUIDADO", Decimal("180.00"))]},
        {"V84491751": items},
        fecha_hoy=date(2026, 8, 20),
    )
    assert filas[0]["cedula"] == "E84491751"
    assert filas[0]["estado"] == "LIQUIDADO"
    assert filas[0]["cuota"] == 180.0
    assert filas[0]["mora_hoy"] == 4
    assert filas[0]["saldo_hoy"] == 720.0


def test_filas_celda_vacia_si_no_hay_cuota():
    filas = filas_cedula_cuota(
        ["E84491751", "V999"],
        {"E84491751": [("LIQUIDADO", Decimal("180.5"))]},
        fecha_hoy=date(2026, 8, 20),
    )
    assert filas[0]["cuota"] == 180.5
    assert filas[0]["estado"] == "LIQUIDADO"
    assert filas[1]["cedula"] == "V999"
    assert filas[1]["cuota"] is None
    assert filas[1]["estado"] is None


def test_aprobado_sin_4_en_mora_oculta_conteo_pero_muestra_saldo():
    items = [
        (1, date(2026, 1, 15), Decimal("500"), Decimal("0"), None, 12),
        (2, date(2026, 2, 15), Decimal("500"), Decimal("0"), None, 12),
        (3, date(2026, 3, 15), Decimal("500"), Decimal("0"), None, 12),
        (4, date(2026, 6, 15), Decimal("500"), Decimal("100"), None, 12),  # VENCIDO parcial
    ]
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("500"))]},
        {"E84491751": items},
        fecha_hoy=date(2026, 8, 20),
    )
    assert conteo_cuotas_en_mora(items, date(2026, 8, 20)) == 3
    assert filas[0]["mora_junio"] is None
    assert filas[0]["mora_hoy"] is None
    # 3 MORA*500 + VENCIDO 400 = 1900
    assert filas[0]["saldo_hoy"] == 1900.0
    assert filas[0]["saldo_junio"] is not None


def test_aprobado_con_4_en_mora_muestra_junio_y_hoy():
    items = [
        (1, date(2025, 9, 1), Decimal("100"), Decimal("0"), None, 12),
        (2, date(2025, 10, 1), Decimal("100"), Decimal("0"), None, 12),
        (3, date(2025, 11, 1), Decimal("100"), Decimal("0"), None, 12),
        (4, date(2025, 12, 1), Decimal("100"), Decimal("0"), None, 12),
        (5, date(2026, 1, 1), Decimal("100"), Decimal("0"), None, 12),
    ]
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("100"))]},
        {"E84491751": items},
        fecha_junio=FECHA_CORTE_JUNIO,
        fecha_hoy=date(2026, 8, 20),
    )
    assert filas[0]["mora_junio"] == 5
    assert filas[0]["saldo_junio"] == 500.0
    assert filas[0]["mora_hoy"] == 5
    assert filas[0]["saldo_hoy"] == 500.0


def test_mismo_filtro_4_en_junio_y_hoy_independiente():
    """En junio aún no llega a 4; hoy sí."""
    items = [
        (1, date(2025, 12, 1), Decimal("100"), Decimal("0"), None, 12),
        (2, date(2026, 1, 1), Decimal("100"), Decimal("0"), None, 12),
        (3, date(2026, 2, 1), Decimal("100"), Decimal("0"), None, 12),
        (4, date(2026, 3, 1), Decimal("100"), Decimal("0"), None, 12),
    ]
    # 1 jun 2026: cuota 1 MORA (dic+4m+6d = ~7 jun), 2-4 aún no
    # Ajust: dic 1 + 4m = abr 1 + 6d = abr 7 → MORA from abr 7
    # ene 1 + 4m = may 1 + 6 = may 7
    # feb 1 + 4m = jun 1 + 6 = jun 7 → on jun 1 still VENCIDO
    # mar 1 + 4m = jul 1 + 6 = jul 7
    # On jun 1: cuota 1 and 2 are MORA (2 < 4) → vacío
    # On aug 20: all 4 MORA → muestra 4
    filas = filas_cedula_cuota(
        ["E84491751"],
        {"E84491751": [("APROBADO", Decimal("100"))]},
        {"E84491751": items},
        fecha_junio=date(2026, 6, 1),
        fecha_hoy=date(2026, 8, 20),
    )
    assert conteo_cuotas_en_mora(items, date(2026, 6, 1)) == 2
    assert filas[0]["mora_junio"] is None
    assert filas[0]["saldo_junio"] == 400.0  # 2 MORA + 2 VENCIDO
    assert filas[0]["mora_hoy"] == 4
    assert filas[0]["saldo_hoy"] == 400.0


def test_aprobado_informe_solo_cuotas_del_prestamo_aprobado():
    ref = date(2026, 8, 20)
    items_aprob = [
        (1, date(2026, 1, 15), Decimal("500"), Decimal("0"), None, 12),
        (2, date(2026, 2, 15), Decimal("500"), Decimal("0"), None, 12),
        (3, date(2026, 3, 15), Decimal("500"), Decimal("0"), None, 12),
    ]
    items_liq = [
        (1, date(2024, 1, 15), Decimal("200"), Decimal("0"), None, 12),
        (2, date(2024, 2, 15), Decimal("200"), Decimal("0"), None, 12),
        (3, date(2024, 3, 15), Decimal("200"), Decimal("0"), None, 12),
    ]
    items_all = items_aprob + items_liq
    items = _items_cuotas_para_informe(
        "25133615",
        {"25133615": items_all},
        {"25133615": items_aprob},
        {"25133615": {"APROBADO", "LIQUIDADO"}},
    )
    assert conteo_cuotas_en_mora(items, ref) == 3
    assert conteo_cuotas_en_mora(items_all, ref) == 6


def test_saldo_vencido_es_todo_el_credito_vencido():
    """Cuotas en mora = solo MORA; saldo = VENCIDO + MORA del crédito."""
    ref = date(2026, 8, 20)
    items = [
        (1, date(2026, 1, 15), Decimal("100"), Decimal("0"), None, 12),  # MORA
        (2, date(2026, 2, 15), Decimal("100"), Decimal("0"), None, 12),  # MORA
        (3, date(2026, 3, 15), Decimal("100"), Decimal("0"), None, 12),  # MORA
        (4, date(2026, 6, 15), Decimal("100"), Decimal("0"), None, 12),  # VENCIDO
        (5, date(2026, 9, 15), Decimal("100"), Decimal("0"), None, 12),  # PENDIENTE
    ]
    assert conteo_cuotas_en_mora(items, ref) == 3
    assert saldo_vencido_credito(items, ref) == Decimal("400.00")


def test_saldo_vencido_resta_total_pagado_de_cada_cuota():
    ref = date(2026, 8, 20)
    items = [
        (1, date(2026, 1, 15), Decimal("100"), Decimal("40"), None, 12),  # MORA parcial
        (2, date(2026, 6, 15), Decimal("100"), Decimal("0"), None, 12),  # VENCIDO
    ]
    assert saldo_vencido_credito(items, ref) == Decimal("160.00")


def test_metricas_corte_aprobado_exige_4_solo_en_conteo():
    items = [
        (1, date(2026, 1, 15), Decimal("100"), Decimal("0"), None, 12),
        (2, date(2026, 2, 15), Decimal("100"), Decimal("0"), None, 12),
        (3, date(2026, 3, 15), Decimal("100"), Decimal("0"), None, 12),
        (4, date(2026, 6, 15), Decimal("100"), Decimal("0"), None, 12),  # VENCIDO
    ]
    n, s = metricas_corte_mora(items, date(2026, 8, 20), es_aprobado=True)
    assert n is None
    assert s == Decimal("400.00")
    n2, s2 = metricas_corte_mora(items, date(2026, 8, 20), es_aprobado=False)
    assert n2 == 3
    assert s2 == Decimal("400.00")


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


def test_excel_dos_cortes_junio_y_hoy():
    import openpyxl

    content = generar_excel_cedulas_cuota(
        [
            {
                "cedula": "E1",
                "estado": "APROBADO",
                "cuota": 180.0,
                "fecha_junio": date(2026, 6, 1),
                "fecha_hoy": date(2026, 8, 20),
                "mora_junio": 4,
                "saldo_junio": 720.0,
                "mora_hoy": 5,
                "saldo_hoy": 900.0,
            },
            {"cedula": "V2", "estado": None, "cuota": None},
        ]
    )
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active
    assert ws["A1"].value == "Cédula"
    assert ws["B1"].value == "Estado"
    assert ws["C1"].value == "Cuota"
    assert ws["D1"].value == "1 jun 2026"
    assert ws["F1"].value == "Hoy (2026-08-20)"
    assert ws["D2"].value == "Cuotas en mora"
    assert ws["E2"].value == "Saldo vencido"
    assert ws["F2"].value == "Cuotas en mora"
    assert ws["G2"].value == "Saldo vencido"
    assert ws["B3"].value == "APROBADO"
    assert ws["C3"].value == 180.0
    assert ws["D3"].value == 4
    assert ws["E3"].value == 720.0
    assert ws["F3"].value == 5
    assert ws["G3"].value == 900.0
    assert ws["A4"].value == "V2"
