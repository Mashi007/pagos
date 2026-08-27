# -*- coding: utf-8 -*-
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.services.cobros.escaner_lote_contexto_revision import (
    cargar_filas_contexto_revision,
    modelo_contexto_revision,
    origen_es_pago_con_error,
    parse_ids_contexto_revision,
    tabla_contexto_revision,
)


def test_origen_default_es_tabla_pagos():
    assert origen_es_pago_con_error(None) is False
    assert origen_es_pago_con_error("") is False
    assert origen_es_pago_con_error("pagos") is False
    assert modelo_contexto_revision(None) is Pago
    assert tabla_contexto_revision("pagos") == "pagos"


def test_origen_pagos_con_errores_no_cruza_a_pagos():
    assert origen_es_pago_con_error("pagos_con_errores") is True
    assert origen_es_pago_con_error("pagos-con-errores") is True
    assert modelo_contexto_revision("pagos_con_errores") is PagoConError
    assert tabla_contexto_revision("pagos_con_errores") == "pagos_con_errores"
    assert modelo_contexto_revision("pagos") is Pago


def test_parse_ids_contexto_revision_max_10():
    raw = ",".join(str(i) for i in range(1, 20))
    ids = parse_ids_contexto_revision(raw, max_ids=10)
    assert ids == list(range(1, 11))
    assert parse_ids_contexto_revision("x,8842,0,-3,abc") == [8842]


def test_cargar_filas_usa_el_modelo_del_origen():
    class _Scalars:
        def all(self):
            return []

    class _Result:
        def scalars(self):
            return _Scalars()

    seen = {}

    class _Db:
        def execute(self, stmt):
            seen["entity"] = stmt.column_descriptions[0]["entity"]
            return _Result()

    db = _Db()
    tabla, by_id = cargar_filas_contexto_revision(
        db, [8842], origen="pagos_con_errores"
    )
    assert tabla == "pagos_con_errores"
    assert by_id == {}
    assert seen["entity"] is PagoConError

    tabla2, _ = cargar_filas_contexto_revision(db, [8842], origen="pagos")
    assert tabla2 == "pagos"
    assert seen["entity"] is Pago
