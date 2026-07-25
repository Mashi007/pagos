"""
No duplicar notificaciones entre segmentos: si el titular esta en «2 Cuotas»
(prejudicial) no debe listarse ni enviarse en «1 Cuota» (menor a 60).
"""
from app.services import notificaciones_dedup_segmentos as dedup


class _DbFake:
    """Solo actua como marcador no-None; la consulta se sustituye en el test."""


def _patch_claves(monkeypatch, cliente_ids, cedulas):
    monkeypatch.setattr(
        dedup,
        "clientes_en_regla_prejudicial",
        lambda db, fecha_referencia=None: (set(cliente_ids), set(cedulas)),
    )


def test_excluye_por_cliente_id(monkeypatch):
    _patch_claves(monkeypatch, {7}, set())
    items = [
        {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100},
        {"cliente_id": 8, "cedula": "V-2", "prestamo_id": 200},
    ]
    res = dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), items)
    assert [it["cliente_id"] for it in res] == [8]


def test_excluye_por_cedula_cuando_falta_cliente_id(monkeypatch):
    _patch_claves(monkeypatch, set(), {"V-1"})
    items = [
        {"cliente_id": None, "cedula": " V-1 ", "prestamo_id": 100},
        {"cliente_id": None, "cedula": "V-2", "prestamo_id": 200},
    ]
    res = dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), items)
    assert [it["cedula"] for it in res] == ["V-2"]


def test_sin_titulares_prejudicial_no_toca_la_lista(monkeypatch):
    _patch_claves(monkeypatch, set(), set())
    items = [{"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100}]
    assert dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), items) == items


def test_lista_vacia_o_sin_db():
    assert dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), []) == []
    items = [{"cliente_id": 7, "cedula": "V-1"}]
    assert dedup.filtrar_items_menor_60_sin_prejudicial(None, items) == items


def test_claves_precomputadas_no_reconsultan(monkeypatch):
    """Con claves ya calculadas no se vuelve a consultar la BD (una sola pasada)."""

    def _explota(db, fecha_referencia=None):
        raise AssertionError("no debe consultarse cuando se pasan claves")

    monkeypatch.setattr(dedup, "clientes_en_regla_prejudicial", _explota)
    items = [
        {"cliente_id": 7, "cedula": "V-1"},
        {"cliente_id": 8, "cedula": "V-2"},
    ]
    res = dedup.filtrar_items_sin_prejudicial(
        _DbFake(), items, claves=({7}, set()), etiqueta="dia-siguiente"
    )
    assert [it["cliente_id"] for it in res] == [8]


def test_item_excluido_envio_solo_tipos_1_y_dia_siguiente():
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_1_DIA_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is True
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_10_DIAS_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is True
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PREJUDICIAL", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_2_DIAS_ANTES_PENDIENTE", {"cliente_id": 7}, {7}, set()
    ) is False
