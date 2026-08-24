"""Reglas sábado/domingo: copia del viernes anterior, sin ingreso obligatorio."""
from datetime import date

import pytest

from app.services.tasa_cambio_service import (
    debe_ingresar_tasa,
    es_fin_de_semana_caracas,
    ultimo_viernes_anterior,
)


def test_es_fin_de_semana_solo_sabado_y_domingo():
    assert es_fin_de_semana_caracas(date(2026, 6, 20)) is True  # sábado
    assert es_fin_de_semana_caracas(date(2026, 6, 21)) is True  # domingo
    assert es_fin_de_semana_caracas(date(2026, 6, 19)) is False  # viernes
    assert es_fin_de_semana_caracas(date(2026, 6, 22)) is False  # lunes


def test_ultimo_viernes_anterior():
    assert ultimo_viernes_anterior(date(2026, 6, 20)) == date(2026, 6, 19)
    assert ultimo_viernes_anterior(date(2026, 6, 21)) == date(2026, 6, 19)


def test_ultimo_viernes_anterior_rechaza_dia_laboral():
    with pytest.raises(ValueError):
        ultimo_viernes_anterior(date(2026, 6, 19))


def test_debe_ingresar_nunca_bloquea(monkeypatch):
    import app.services.tasa_cambio_service as svc

    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: date(2026, 6, 19))  # viernes
    assert es_fin_de_semana_caracas() is False
    assert debe_ingresar_tasa() is False


def test_bloqueo_manual_solo_itmaster_tarde_si_bcv_auto_fallo():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services.tasa_cambio_service import debe_bloquear_carga_manual_tasa

    tz = ZoneInfo("America/Caracas")
    tarde = datetime(2026, 6, 18, 19, 0, tzinfo=tz)  # jueves
    manana = datetime(2026, 6, 18, 12, 0, tzinfo=tz)

    assert (
        debe_bloquear_carga_manual_tasa(
            email="otro@rapicreditca.com",
            bcv_siguiente_ok=False,
            fin_de_semana=False,
            ahora=tarde,
        )
        is False
    )
    assert (
        debe_bloquear_carga_manual_tasa(
            email="itmaster@rapicreditca.com",
            bcv_siguiente_ok=False,
            fin_de_semana=False,
            ahora=manana,
        )
        is False
    )
    assert (
        debe_bloquear_carga_manual_tasa(
            email="itmaster@rapicreditca.com",
            bcv_siguiente_ok=True,
            fin_de_semana=False,
            ahora=tarde,
        )
        is False
    )
    assert (
        debe_bloquear_carga_manual_tasa(
            email="ITMASTER@rapicreditca.com",
            bcv_siguiente_ok=False,
            fin_de_semana=False,
            ahora=tarde,
        )
        is True
    )


def test_modo_carga_un_dia_antes():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services.tasa_cambio_service import modo_carga_un_dia_antes

    tz = ZoneInfo("America/Caracas")
    assert (
        modo_carga_un_dia_antes(
            fin_de_semana=False,
            bcv_siguiente_ok=True,
            ahora=datetime(2026, 6, 18, 10, 0, tzinfo=tz),
        )
        == "automatico_ok"
    )
    assert (
        modo_carga_un_dia_antes(
            fin_de_semana=True,
            bcv_siguiente_ok=False,
            ahora=datetime(2026, 6, 20, 19, 0, tzinfo=tz),
        )
        == "fin_de_semana"
    )
    assert (
        modo_carga_un_dia_antes(
            fin_de_semana=False,
            bcv_siguiente_ok=False,
            ahora=datetime(2026, 6, 18, 12, 0, tzinfo=tz),
        )
        == "pendiente_ventana"
    )
    assert (
        modo_carga_un_dia_antes(
            fin_de_semana=False,
            bcv_siguiente_ok=False,
            ahora=datetime(2026, 6, 18, 17, 0, tzinfo=tz),
        )
        == "en_curso"
    )
    assert (
        modo_carga_un_dia_antes(
            fin_de_semana=False,
            bcv_siguiente_ok=False,
            ahora=datetime(2026, 6, 18, 18, 40, tzinfo=tz),
        )
        == "requiere_manual"
    )


def test_siguiente_dia_habil_salta_fin_de_semana():
    from app.services.tasa_cambio_service import siguiente_dia_habil_caracas

    assert siguiente_dia_habil_caracas(date(2026, 6, 19)) == date(2026, 6, 22)  # vie -> lun
    assert siguiente_dia_habil_caracas(date(2026, 6, 22)) == date(2026, 6, 23)  # lun -> mar
    assert siguiente_dia_habil_caracas(date(2026, 6, 20)) == date(2026, 6, 22)  # sab -> lun
