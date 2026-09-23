# -*- coding: utf-8 -*-
"""Excel carga masiva: auto-assign uses scalar loan ids, not Row tuples."""

from app.services.pagos_excel_asignacion import prestamo_id_unico_desde_activos


def test_scalars_all_int_id_does_not_index_as_row():
    """Formato D + 1 APROBADO: scalars().all() yields ints; [0][0] was HTTP 500."""
    assert prestamo_id_unico_desde_activos([2982]) == 2982


def test_legacy_row_tuple_still_unwraps():
    assert prestamo_id_unico_desde_activos([(2982,)]) == 2982


def test_cero_o_varios_activos_no_asigna():
    assert prestamo_id_unico_desde_activos([]) is None
    assert prestamo_id_unico_desde_activos([10, 11]) is None
