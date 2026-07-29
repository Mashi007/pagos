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


def test_cron_2_dias_antes_no_envia():
    out = ejecutar_cron_pago_2_dias_antes(db=None)
    assert out["omitido"] is True
    assert out["motivo"] == "politica_solo_manual"


def test_cobranzas_excel_independiente_de_prejudicial_exclusion():
    """COBRANZAS_EXCEL no se bloquea por la exclusion de PREJUDICIAL."""
    from app.services.notificaciones_dedup_segmentos import (
        TIPOS_EXCLUIDOS_SI_PREJUDICIAL,
        TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL,
        item_excluido_por_prejudicial_en_envio,
        item_excluido_por_cobranzas_excel_en_envio,
    )

    assert "COBRANZAS_EXCEL" not in TIPOS_EXCLUIDOS_SI_PREJUDICIAL
    assert "COBRANZAS_EXCEL" not in TIPOS_EXCLUIDOS_SI_COBRANZAS_EXCEL
    item = {"cliente_id": 1, "cedula": "V123"}
    assert item_excluido_por_prejudicial_en_envio(
        "COBRANZAS_EXCEL", item, {1}, {"V123"}
    ) is False
    assert item_excluido_por_cobranzas_excel_en_envio(
        "COBRANZAS_EXCEL", item, {1}, {"V123"}
    ) is False
    # Otros si se recortan cuando el titular esta en Cobranzas
    assert item_excluido_por_cobranzas_excel_en_envio(
        "PREJUDICIAL", item, {1}, {"V123"}
    ) is True
