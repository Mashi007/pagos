# -*- coding: utf-8 -*-
"""Drive: cédula con DESISTIMIENTO no puede alta nueva."""

from app.services.prestamo_candidatos_drive_validadores import (
    MSG_DRIVE_BLOQUEO_DESISTIMIENTO,
    cedula_bloqueada_por_desistimiento_drive,
)


def test_cedula_bloqueada_por_desistimiento():
    assert cedula_bloqueada_por_desistimiento_drive(0) is False
    assert cedula_bloqueada_por_desistimiento_drive(1) is True
    assert cedula_bloqueada_por_desistimiento_drive(3) is True


def test_motivos_no_100_bloquea_desistimiento(monkeypatch):
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
        prestamo_counts_desist={"V30771164": 1},
    )
    assert ok is False
    assert pc is None
    assert any(MSG_DRIVE_BLOQUEO_DESISTIMIENTO[:50] in m for m in motivos)
