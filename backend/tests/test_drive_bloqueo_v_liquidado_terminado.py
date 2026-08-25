# -*- coding: utf-8 -*-
"""Drive: cédula V solo alta nueva si cartera está Liquidado / Terminado."""

from app.services.prestamo_candidatos_drive_validadores import (
    MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO,
    cedula_v_bloqueada_por_no_liquidado_terminado,
    prestamo_esta_liquidado_terminado,
)


def test_prestamo_esta_liquidado_terminado():
    assert prestamo_esta_liquidado_terminado("LIQUIDADO", "TERMINADO") is True
    assert prestamo_esta_liquidado_terminado("liquidado", "terminado") is True
    assert prestamo_esta_liquidado_terminado("LIQUIDADO", "REVISION") is False
    assert prestamo_esta_liquidado_terminado("LIQUIDADO", "EN_PROCESO") is False
    assert prestamo_esta_liquidado_terminado("LIQUIDADO", None) is False
    assert prestamo_esta_liquidado_terminado("APROBADO", "TERMINADO") is False


def test_cedula_v_bloqueada_por_no_liquidado_terminado():
    assert (
        cedula_v_bloqueada_por_no_liquidado_terminado(
            es_v=True, n_no_liquidado_terminado=0
        )
        is False
    )
    assert (
        cedula_v_bloqueada_por_no_liquidado_terminado(
            es_v=True, n_no_liquidado_terminado=1
        )
        is True
    )
    # E / no-V: la regla no aplica
    assert (
        cedula_v_bloqueada_por_no_liquidado_terminado(
            es_v=False, n_no_liquidado_terminado=5
        )
        is False
    )


def test_motivos_no_100_bloquea_v_en_liquidado_revision(monkeypatch):
    from app.services import prestamo_candidatos_drive_guardar as g

    payload = {
        "cedula_valida": True,
        "cedula_cmp": "V30771164",
        "col_n_total_financiamiento": "1000",
        "col_r_numero_cuotas": "12",
        "col_q_fecha": "2026-08-01",
        "col_s_modalidad_pago": "MENSUAL",
        "col_j_analista": "Ana",
    }

    monkeypatch.setattr(g, "_cliente_id_por_cedula_normalizada", lambda *_a, **_k: 99)
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *_a, **_k: None,
    )

    ok, motivos, pc = g._motivos_no_100(
        payload,
        db=object(),
        prestamo_counts_aprob={},
        prestamo_counts_desist={},
        prestamo_counts_no_liq_term={"V30771164": 1},
    )
    assert ok is False
    assert pc is None
    assert any(MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO[:40] in m for m in motivos)


def test_motivos_no_100_permite_v_si_solo_liquidado_terminado(monkeypatch):
    from app.services import prestamo_candidatos_drive_guardar as g

    payload = {
        "cedula_valida": True,
        "cedula_cmp": "V30771164",
        "col_n_total_financiamiento": "1000",
        "col_r_numero_cuotas": "12",
        "col_q_fecha": "2026-08-01",
        "col_s_modalidad_pago": "MENSUAL",
        "col_j_analista": "Ana",
        "col_i_modelo_vehiculo": "X",
        "col_k_concesionario": "Y",
    }

    monkeypatch.setattr(g, "_cliente_id_por_cedula_normalizada", lambda *_a, **_k: 99)
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *_a, **_k: None,
    )

    ok, motivos, pc = g._motivos_no_100(
        payload,
        db=object(),
        prestamo_counts_aprob={},
        prestamo_counts_desist={},
        prestamo_counts_no_liq_term={"V30771164": 0},
    )
    # Puede fallar por otros campos; no debe mencionar Liquidado/Terminado
    assert not any("Liquidado / Terminado" in m for m in motivos)
    if not ok:
        assert MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO not in motivos


def test_motivos_no_100_no_aplica_regla_a_cedula_e(monkeypatch):
    from app.services import prestamo_candidatos_drive_guardar as g

    payload = {
        "cedula_valida": True,
        "cedula_cmp": "E12345678",
        "col_n_total_financiamiento": "1000",
        "col_r_numero_cuotas": "12",
        "col_q_fecha": "2026-08-01",
        "col_s_modalidad_pago": "MENSUAL",
        "col_j_analista": "Ana",
    }

    monkeypatch.setattr(g, "_cliente_id_por_cedula_normalizada", lambda *_a, **_k: 99)
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *_a, **_k: None,
    )

    ok, motivos, pc = g._motivos_no_100(
        payload,
        db=object(),
        prestamo_counts_aprob={},
        prestamo_counts_desist={},
        prestamo_counts_no_liq_term={"E12345678": 2},
    )
    assert not any("Liquidado / Terminado" in m for m in motivos)
