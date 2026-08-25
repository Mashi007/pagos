"""
Segmentos de mora:
- Dia siguiente no recorta 2 Cuotas ni 1 Cuota (pueden enviarse juntos).
- 2 Cuotas si recorta 1 Cuota.
"""
from app.services import notificaciones_dedup_segmentos as dedup


class _DbFake:
    """Solo actua como marcador no-None; la consulta se sustituye en el test."""


def _patch_claves_prej(monkeypatch, cliente_ids, cedulas):
    monkeypatch.setattr(
        dedup,
        "clientes_en_regla_prejudicial",
        lambda db, fecha_referencia=None: (set(cliente_ids), set(cedulas)),
    )


def _patch_claves_dia(monkeypatch, cliente_ids, cedulas):
    monkeypatch.setattr(
        dedup,
        "clientes_en_regla_dia_siguiente",
        lambda db, fecha_referencia=None: (set(cliente_ids), set(cedulas)),
    )


def test_excluye_1_cuota_por_cliente_id_en_2_cuotas(monkeypatch):
    _patch_claves_prej(monkeypatch, {7}, set())
    items = [
        {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100},
        {"cliente_id": 8, "cedula": "V-2", "prestamo_id": 200},
    ]
    res = dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), items)
    assert [it["cliente_id"] for it in res] == [8]


def test_excluye_1_cuota_por_cedula_cuando_falta_cliente_id(monkeypatch):
    _patch_claves_prej(monkeypatch, set(), {"V-1"})
    items = [
        {"cliente_id": None, "cedula": " V-1 ", "prestamo_id": 100},
        {"cliente_id": None, "cedula": "V-2", "prestamo_id": 200},
    ]
    res = dedup.filtrar_items_menor_60_sin_prejudicial(_DbFake(), items)
    assert [it["cedula"] for it in res] == ["V-2"]


def test_sin_titulares_prejudicial_no_toca_la_lista(monkeypatch):
    _patch_claves_prej(monkeypatch, set(), set())
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
        _DbFake(), items, claves=({7}, set()), etiqueta="menor-60"
    )
    assert [it["cliente_id"] for it in res] == [8]


def test_filtrar_dia_siguiente_sigue_disponible_pero_envio_no_recorta(monkeypatch):
    """El filtro por titular existe; el envio ya no excluye 2 Cuotas / 1 Cuota."""
    _patch_claves_dia(monkeypatch, {7}, set())
    items = [
        {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100},
        {"cliente_id": 8, "cedula": "V-2", "prestamo_id": 200},
    ]
    res = dedup.filtrar_items_sin_dia_siguiente(
        _DbFake(), items, claves=({7}, set()), etiqueta="prejudicial"
    )
    assert [it["cliente_id"] for it in res] == [8]


def test_item_excluido_envio_dia_siguiente_no_recorta_otras_reglas():
    assert dedup.item_excluido_por_dia_siguiente_en_envio(
        "PREJUDICIAL", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_dia_siguiente_en_envio(
        "PAGO_10_DIAS_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_dia_siguiente_en_envio(
        "PAGO_1_DIA_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_dia_siguiente_en_envio(
        "PAGO_2_DIAS_ANTES_PENDIENTE", {"cliente_id": 7}, {7}, set()
    ) is False

    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_1_DIA_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_10_DIAS_ATRASADO", {"cliente_id": 7}, {7}, set()
    ) is True
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PREJUDICIAL", {"cliente_id": 7}, {7}, set()
    ) is False
    assert dedup.item_excluido_por_prejudicial_en_envio(
        "PAGO_2_DIAS_ANTES_PENDIENTE", {"cliente_id": 7}, {7}, set()
    ) is False


def test_tipos_excluidos_constantes():
    assert "PAGO_1_DIA_ATRASADO" not in dedup.TIPOS_EXCLUIDOS_SI_PREJUDICIAL
    assert "PAGO_10_DIAS_ATRASADO" in dedup.TIPOS_EXCLUIDOS_SI_PREJUDICIAL
    assert dedup.TIPOS_EXCLUIDOS_SI_DIA_SIGUIENTE == frozenset()


def test_titulares_y_filtro_mismo_titular():
    items_d1 = [
        {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100},
        {"cliente_id": 8, "cedula": "V-2", "prestamo_id": 200},
    ]
    ids, ceds = dedup.titulares_desde_items(items_d1)
    assert ids == {7, 8}
    assert ceds == {"V-1", "V-2"}
    extras = [
        {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 101},
        {"cliente_id": 9, "cedula": "V-3", "prestamo_id": 300},
    ]
    solo = dedup.filtrar_items_de_titulares(extras, ids, ceds)
    assert [it["cliente_id"] for it in solo] == [7]


def test_envio_dia_siguiente_despacha_otras_reglas_del_mismo_titular(monkeypatch):
    """Al enviar dia siguiente, se disparan 2 Cuotas / 1 Cuota / 3d del mismo titular."""
    from app.api.v1.endpoints.notificaciones_tabs import routes as tabs

    llamados = []

    def _fake_enviar(items, asunto, cuerpo, config, get_tipo, db, **kwargs):
        llamados.append(get_tipo({}))
        return {
            "enviados": len(items),
            "sin_email": 0,
            "fallidos": 0,
            "omitidos_config": 0,
            "omitidos_desistimiento": 0,
            "omitidos_paquete_incompleto": 0,
            "omitidos_ya_enviado": 0,
            "procesados": len(items),
        }

    monkeypatch.setattr(tabs, "_enviar_correos_items", _fake_enviar)
    monkeypatch.setattr(
        tabs,
        "build_prejudicial_items",
        lambda db, fecha_referencia=None: [
            {
                "cliente_id": 7,
                "cedula": "V-1",
                "prestamo_id": 100,
                "total_cuotas_atrasadas": 2,
                "dias_atraso": 10,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.notificacion_service.build_cuotas_pendiente_2_dias_antes_items",
        lambda db, fecha_referencia=None: [
            {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100}
        ],
    )
    monkeypatch.setattr(
        "app.services.notificacion_service.item_cumple_regla_prejudicial_estricta",
        lambda item, fecha_referencia=None: True,
    )
    monkeypatch.setattr(
        "app.services.notificacion_service.item_cumple_regla_menor_60_estricta",
        lambda item, fecha_referencia=None: True,
    )
    monkeypatch.setattr(
        "app.services.notificaciones_dedup_segmentos.filtrar_items_menor_60_sin_prejudicial",
        lambda db, items, fecha_referencia=None: items,
    )

    res = tabs._enviar_dia_siguiente_y_otras_reglas(
        db=object(),
        items_dia_siguiente=[{"cliente_id": 7, "cedula": "V-1", "prestamo_id": 100}],
        items_10_retraso=[
            {"cliente_id": 7, "cedula": "V-1", "prestamo_id": 200, "cuotas_atrasadas": 1}
        ],
        fecha_referencia=None,
        config_raw={},
        respetar_toggle_envio=False,
        on_progress=None,
        omitir_exitos_desde=None,
        asunto_ret="a",
        cuerpo_ret="b",
        asunto_prej="c",
        cuerpo_prej="d",
    )
    assert llamados == [
        "PAGO_1_DIA_ATRASADO",
        "PREJUDICIAL",
        "PAGO_10_DIAS_ATRASADO",
        "PAGO_2_DIAS_ANTES_PENDIENTE",
    ]
    assert res["enviados"] == 4
    assert res["detalles_casos_adicionales"] == {
        "dia_siguiente": 1,
        "prejudicial": 1,
        "una_cuota": 1,
        "tres_dias_antes": 1,
    }
