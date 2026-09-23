"""
Regresión: Formato C (Cédula|ID Préstamo|Fecha|Monto|Doc) no debe detectarse como Formato D.
"""
from datetime import date

from app.api.v1.endpoints.pagos.excel_formato_detect import (
    looks_like_cedula_excel,
    looks_like_date_excel,
    parse_prestamo_id_cell,
    parece_fila_formato_c,
)


def test_parece_formato_c_fila_tipica():
    row = ("V18000758", 4521, "31-10-2025", 100.0, "VE/505363358")
    assert parece_fila_formato_c(row) is True
    assert parse_prestamo_id_cell(row[1]) == 4521


def test_formato_d_4_cols_no_es_c():
    """D recomendado: Cédula | Monto | Fecha | Documento — sin 5ª col no es C."""
    row = ("V18000758", 96, "31-10-2025", "VE/505363358")
    assert parece_fila_formato_c(row) is False


def test_formato_d_con_codigo_doc_con_letras_no_es_c():
    """
    D + código: Cédula | Monto | Fecha | Doc | Código.
    col3 tiene letras → no es monto plano → no C.
    """
    row = ("V18000758", 96, "31-10-2025", "VE/505363358", "A0001")
    assert parece_fila_formato_c(row) is False


def test_formato_c_no_confundir_con_d_misma_fecha_col():
    """
    Misma firma superficial que D (cedula@0, fecha@2) pero con ID préstamo.
    Antes: D ganaba y monto:=4521, doc:=100.
    """
    row = ("V18000758", 4521, date(2025, 10, 31), 100, "BNC/123456")
    assert looks_like_cedula_excel(row[0])
    assert looks_like_date_excel(row[2])
    assert parece_fila_formato_c(row) is True
    # Si se aplicara D: monto sería row[1]
    assert float(row[1]) == 4521
    assert float(row[3]) == 100


def test_parse_prestamo_id_rechaza_decimal():
    assert parse_prestamo_id_cell(12.5) is None
    assert parse_prestamo_id_cell("12.5") is None
    assert parse_prestamo_id_cell(0) is None
    assert parse_prestamo_id_cell(-1) is None
