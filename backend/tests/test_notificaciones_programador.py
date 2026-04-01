"""Tests para hora programador (parseo y clave de deduplicacion)."""

from unittest.mock import MagicMock

from app.services.notificaciones_programador import (
    _slot_key,
    parse_programador_hm,
    snap_hm_to_cron_slot,
    formato_hm_programador,
    normalizar_payload_envios_programadores,
)


def test_parse_programador_default():
    assert parse_programador_hm(None) == (1, 0)
    assert parse_programador_hm("") == (1, 0)
    assert parse_programador_hm("   ") == (1, 0)


def test_parse_programador_hh_mm():
    assert parse_programador_hm("19:00") == (19, 0)
    assert parse_programador_hm("01:30") == (1, 30)
    assert parse_programador_hm("7:05") == (7, 5)


def test_parse_programador_wrap():
    assert parse_programador_hm("25:00") == (1, 0)
    assert parse_programador_hm("10:99") == (10, 39)


def test_slot_key():
    assert _slot_key("2026-03-24", (19, 5)) == "2026-03-24|19:05"


def test_snap_hm_to_cron_slot():
    # Sin snap, 10:07 != ningun slot del cron (:00,:15,:30,:45) y no se envia.
    # Redondeo al cuarto mas cercano: 10:07 -> 10:00; 10:08 -> 10:15
    assert snap_hm_to_cron_slot((10, 7)) == (10, 0)
    assert snap_hm_to_cron_slot((10, 8)) == (10, 15)
    assert snap_hm_to_cron_slot((9, 7)) == (9, 0)
    assert snap_hm_to_cron_slot((9, 8)) == (9, 15)
    assert snap_hm_to_cron_slot((23, 52)) == (23, 45)
    assert snap_hm_to_cron_slot((23, 58)) == (0, 0)  # 23:59... redondea a 24:00 -> 00:00


def test_normalizar_payload_envios_programadores():
    p = {
        "PAGO_1_DIA_ATRASADO": {"programador": "10:07", "habilitado": True},
        "masivos_campanas": [{"programador": "11:08", "id": "x"}],
    }
    normalizar_payload_envios_programadores(p)
    assert p["PAGO_1_DIA_ATRASADO"]["programador"] == "10:00"
    assert p["masivos_campanas"][0]["programador"] == "11:15"


def test_formato_hm_programador():
    assert formato_hm_programador((4, 0)) == "04:00"


def test_ejecutar_envios_por_programador_omitido_sin_flag(monkeypatch):
    """Sin NOTIFICACIONES_ENVIO_PROGRAMADO no se envia por cron (solo manual API)."""
    import app.services.notificaciones_programador as np

    mock_s = MagicMock()
    mock_s.NOTIFICACIONES_ENVIO_PROGRAMADO = False
    monkeypatch.setattr(np, "settings", mock_s)
    out = np.ejecutar_envios_por_programador(MagicMock())
    assert out.get("skipped") is True
    assert out.get("motivo") == "solo_disparo_manual"
    assert "hm_caracas" in out
