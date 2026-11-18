# -*- coding: utf-8 -*-
"""Duplicado de serial en cartera (listado /pagos): una sola consulta por página."""
from types import SimpleNamespace

from app.api.v1.endpoints.pagos.pago_serializacion_respuesta import (
    _enriquecer_items_duplicado_serial_cartera,
)


class _Db:
    def __init__(self, filas):
        self.filas = filas
        self.llamadas = 0

    def execute(self, q):
        self.llamadas += 1
        return iter(self.filas)


def _row(i, nd):
    return SimpleNamespace(id=i, numero_documento=nd, prestamo_id=500 + i)


def test_una_consulta_y_detecta_exacto_y_canonico():
    rows = [
        _row(1, "740087400000003"),
        _row(2, "740087400000009"),
        _row(3, "740087400000005"),
        _row(4, "740087400000777"),
    ]
    items = [{} for _ in rows]
    db = _Db(
        [
            (1, 501, "740087400000003"),  # el propio pago 1: se ignora
            (2, 502, "740087400000009"),
            (10, 900, "740087400000003"),  # exacto de 1
            (11, 901, "0740087400000009 §CD:abc"),  # canónico de 2
            (12, 902, "740087400000006"),  # vecino: no es duplicado de 3
        ]
    )
    _enriquecer_items_duplicado_serial_cartera(db, rows, items)

    assert db.llamadas == 1
    assert items[0]["duplicado_en_cartera_pago_id"] == 10
    assert items[0]["duplicado_en_cartera_prestamo_id"] == 900
    assert items[1]["duplicado_en_cartera_pago_id"] == 11
    assert items[1]["duplicado_en_cartera_numero_documento"] == "0740087400000009"
    assert items[2]["duplicado_serial_en_cartera"] is False
    assert items[3]["duplicado_serial_en_cartera"] is False


def test_documento_con_codigo_solo_coincidencia_exacta():
    rows = [_row(1, "740087400000003 §CD:X1")]
    items = [{}]
    db = _Db([(10, 900, "740087400000003")])
    _enriquecer_items_duplicado_serial_cartera(db, rows, items)
    assert items[0]["duplicado_serial_en_cartera"] is False


def test_sin_documentos_no_consulta():
    rows = [_row(1, None), _row(2, "")]
    items = [{}, {}]
    db = _Db([])
    _enriquecer_items_duplicado_serial_cartera(db, rows, items)
    assert db.llamadas == 0
    assert all(it["duplicado_serial_en_cartera"] is False for it in items)
