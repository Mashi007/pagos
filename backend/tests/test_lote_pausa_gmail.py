# -*- coding: utf-8 -*-
from datetime import timedelta

import pytest

from app.core.database import SessionLocal
from app.core.email import es_limite_diario_gmail
from app.services.notificaciones_lote_watchdog import lote_reanudable
from app.services.cuota_estado import hoy_negocio
from app.services.notificaciones_lotes_continuar import (
    upsert_lote_continuar,
    listar_lotes_continuar,
    proximo_lote_reanudable_continuar,
    quitar_lote_continuar,
)


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_es_limite_diario_gmail():
    assert es_limite_diario_gmail(
        "Limite diario de envio de Gmail alcanzado (550 5.4.5)."
    )
    assert es_limite_diario_gmail("550 5.4.5 Daily user sending limit exceeded")
    assert not es_limite_diario_gmail("connection unexpectedly closed")
    assert not es_limite_diario_gmail(None)


def test_lote_reanudable_pausado_mismo_dia_no():
    hoy = hoy_negocio().isoformat()
    ultimo = {
        "origen": "api_enviar_caso_manual",
        "estado": "pausado_limite_gmail",
        "tipo_caso": "PREJUDICIAL",
        "inicio_utc": "2026-08-07T16:00:00+00:00",
        "total_en_lista": 100,
        "detalles": {
            "procesados": 40,
            "total_en_lista": 100,
            "pausado_limite_gmail": True,
            "fecha_negocio_pausa": hoy,
            "tipo_caso": "PREJUDICIAL",
        },
    }
    assert lote_reanudable(ultimo) is None


def test_lote_reanudable_pausado_dia_siguiente_si():
    hoy = hoy_negocio()
    ayer = (hoy - timedelta(days=1)).isoformat()
    ultimo = {
        "origen": "api_enviar_caso_manual",
        "estado": "pausado_limite_gmail",
        "tipo_caso": "PREJUDICIAL",
        "inicio_utc": "2026-08-06T16:00:00+00:00",
        "total_en_lista": 100,
        "detalles": {
            "procesados": 40,
            "total_en_lista": 100,
            "pausado_limite_gmail": True,
            "fecha_negocio_pausa": ayer,
            "tipo_caso": "PREJUDICIAL",
        },
    }
    out = lote_reanudable(ultimo)
    assert out is not None
    assert out[0] == "PREJUDICIAL"
    assert out[2] == 40
    assert out[3] == 100


def test_cola_continuar_proximo_solo_dia_siguiente(db):
    hoy = hoy_negocio()
    quitar_lote_continuar(db, "PREJUDICIAL")
    upsert_lote_continuar(
        db,
        tipo_caso="PREJUDICIAL",
        total_en_lista=3185,
        procesados=2000,
        enviados=1997,
        estado="pausado_limite_gmail",
        fecha_negocio_inicio=hoy.isoformat(),
        fecha_negocio_pausa=hoy.isoformat(),
    )
    db.flush()
    assert proximo_lote_reanudable_continuar(db) is None
    upsert_lote_continuar(
        db,
        tipo_caso="PREJUDICIAL",
        total_en_lista=3185,
        procesados=2000,
        enviados=1997,
        estado="pausado_limite_gmail",
        fecha_negocio_inicio=(hoy - timedelta(days=1)).isoformat(),
        fecha_negocio_pausa=(hoy - timedelta(days=1)).isoformat(),
    )
    db.flush()
    nxt = proximo_lote_reanudable_continuar(db)
    assert nxt is not None
    assert nxt["tipo_caso"] == "PREJUDICIAL"
    assert int(nxt["procesados"]) == 2000
    assert any(x["tipo_caso"] == "PREJUDICIAL" for x in listar_lotes_continuar(db))
    # no commit: rollback en fixture deja prod limpia... pero upsert ya pudo
    # haber leido prod. Restaurar PREJUDICIAL real no es responsabilidad del test;
    # rollback deshace si no commit.
