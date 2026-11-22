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


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


def test_auditoria_detecta_hueco_y_cedula_duplicada():
    from app.services.conciliacion_sheet_cobertura import audit_drive_sheet_row_continuity

    # sheet_row: 10,12 (falta 11); cédula V1 en 10 y 12; sin vacías
    class _DbSeq:
        def __init__(self):
            self.i = 0

        def execute(self, q):
            self.i += 1
            # 1) todos los sheet_row_number  2) vacías  3) pares (fila, col_e)
            if self.i == 1:
                return _FakeResult([(10,), (12,)])
            if self.i == 2:
                return _FakeResult([])
            return _FakeResult([(10, "V1"), (12, "V1")])

    out = audit_drive_sheet_row_continuity(_DbSeq())
    assert out["huecos_numeracion"] == 1
    assert out["huecos_muestra"] == [11]
    assert out["cedulas_duplicadas"] == 1
    assert out["ok"] is False


def test_auditoria_continua_sin_problemas():
    from app.services.conciliacion_sheet_cobertura import audit_drive_sheet_row_continuity

    class _Db:
        def __init__(self):
            self.n = 0

        def execute(self, q):
            self.n += 1
            if self.n == 1:
                return _FakeResult([(5,), (6,)])
            if self.n == 2:
                return _FakeResult([])  # vacías
            return _FakeResult([(5, "V100"), (6, "V200")])

    out = audit_drive_sheet_row_continuity(_Db())
    assert out["ok"] is True
    assert out["huecos_numeracion"] == 0
    assert out["cedulas_duplicadas"] == 0
    assert "Continuo OK" in out["mensaje"]
