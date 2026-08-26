# -*- coding: utf-8 -*-
"""Politica: segmentos de cobranza solo manual (sin cron ni enviar-todas)."""
from app.api.v1.endpoints.notificaciones_tabs.routes import (
    TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL,
    tipo_permite_envio_automatico_o_lote,
)
from app.services.notificaciones_cron_2_dias_antes_job import (
    ejecutar_cron_pago_2_dias_antes,
)


def test_tipos_mora_solo_manual():
    for tipo in (
        "PAGO_2_DIAS_ANTES_PENDIENTE",
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
        "PREJUDICIAL",
        "COBRANZAS_EXCEL",
    ):
        assert tipo in TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL
        assert tipo_permite_envio_automatico_o_lote(tipo) is False


def test_masivos_no_esta_en_solo_manual_lote():
    """MASIVOS puede ir en enviar-todas (sigue siendo POST manual de admin)."""
    assert "MASIVOS" not in TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL
    assert tipo_permite_envio_automatico_o_lote("MASIVOS") is True


def test_cron_2_dias_antes_permite_envio_automatico_dedicado():
    """El job dedicado (cron) envía; SOLO_MANUAL aplica a /enviar-todas, no a este cron."""
    assert callable(ejecutar_cron_pago_2_dias_antes)
    assert "PAGO_2_DIAS_ANTES_PENDIENTE" in TIPOS_NOTIFICACION_SOLO_ENVIO_MANUAL
    assert tipo_permite_envio_automatico_o_lote("PAGO_2_DIAS_ANTES_PENDIENTE") is False


def test_cobranzas_excel_retirado_no_recorta_segmentos_activos():
    """COBRANZAS_EXCEL retirado: no excluye PREJUDICIAL / dia siguiente / 1 Cuota."""
    from app.services.notificaciones_dedup_segmentos import (
        TIPOS_EXCLUIDOS_SI_PREJUDICIAL,
        TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL,
        TIPOS_EXCLUIDOS_SI_CUOTAS_4_MAS,
        item_excluido_por_prejudicial_en_envio,
        item_excluido_por_cobranzas_excel_en_envio,
    )

    assert TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL == frozenset()
    assert TIPOS_EXCLUIDOS_SI_CUOTAS_4_MAS == frozenset()
    assert "COBRANZAS_EXCEL" not in TIPOS_EXCLUIDOS_SI_PREJUDICIAL
    item = {"cliente_id": 1, "cedula": "V123"}
    assert item_excluido_por_prejudicial_en_envio(
        "COBRANZAS_EXCEL", item, {1}, {"V123"}
    ) is False
    assert item_excluido_por_cobranzas_excel_en_envio(
        "PREJUDICIAL", item, {1}, {"V123"}
    ) is False
    assert item_excluido_por_cobranzas_excel_en_envio(
        "PAGO_1_DIA_ATRASADO", item, {1}, {"V123"}
    ) is False
