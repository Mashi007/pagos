"""Cobertura sync CONCILIACIÓN: cola del rango A:S (no solo columna A)."""
from app.services.conciliacion_sheet_cobertura import (
    last_row_with_data_in_column_a,
    last_row_with_data_in_grid,
    row_has_cell_data,
    row_has_column_a_data,
)


def test_last_row_grid_incluye_fila_sin_columna_a():
    values = [
        ["1", "x"],
        ["", "", "", "Nombre", "V123", "0412", "a@b.com"],
        ["", "", "", "", "", "", ""],
    ]
    assert last_row_with_data_in_column_a(values) == 1
    assert last_row_with_data_in_grid(values) == 2
    assert row_has_column_a_data(values[1]) is False
    assert row_has_cell_data(values[1]) is True


def test_last_row_grid_ignora_cola_vacia():
    values = [
        ["1", "LOTE"],
        ["2", "dato"],
        ["", ""],
    ]
    assert last_row_with_data_in_grid(values) == 2


def test_slice_helper_last_row_multicolumn():
    from app.services.conciliacion_sheet_cobertura import _last_nonempty_sheet_row_in_column_values

    values = [
        [""],
        ["", "x", "", "cliente"],
    ]
    assert _last_nonempty_sheet_row_in_column_values(values, row_start_1based=100) == 101
