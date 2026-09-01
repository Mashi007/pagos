# -*- coding: utf-8 -*-
"""Pagos confirmados (modo solo Serial) y transición a préstamo."""
from datetime import date
from decimal import Decimal

import pytest

from app.services.importacion_extracto_service import (
    _buscar_igual_100_global,
    _evaluar_fila_serial_cartera,
    _lote_modo_confirmado,
)
from app.models.importacion_extracto import ImportacionExtractoLote


def test_lote_modo_confirmado_solo_serial():
    lote = ImportacionExtractoLote(modo_cedula=False, modo_serial=True)
    assert _lote_modo_confirmado(lote) is True
    lote2 = ImportacionExtractoLote(modo_cedula=True, modo_serial=True)
    assert _lote_modo_confirmado(lote2) is False
    lote3 = ImportacionExtractoLote(modo_cedula=True, modo_serial=False)
    assert _lote_modo_confirmado(lote3) is False


def test_evaluar_fila_serial_ausente_en_cartera():
    idx = {"pagos_global": {}, "confirmados_activos": {}}
    ev = _evaluar_fila_serial_cartera(
        idx,
        fecha=date(2026, 1, 15),
        serial_raw="740087402484647",
        monto=100.0,
    )
    assert ev["estado"] == "SE_PUEDE_IMPORTAR"
    assert ev["destino_importacion"] == "CONFIRMADO"
    assert ev["similitud_pct"] == 100.0


def test_evaluar_fila_serial_igual_100_en_cartera():
    idx = {
        "pagos_global": {"740087402484647": [(42, 7)]},
        "confirmados_activos": {},
    }
    ev = _evaluar_fila_serial_cartera(
        idx,
        fecha=date(2026, 1, 15),
        serial_raw="740087402484647",
        monto=50.0,
    )
    assert ev["estado"] == "IGUAL_100"
    assert ev.get("omitir_lista") is True
    assert ev["pago_id_match"] == 42


def test_evaluar_fila_serial_igual_confirmado_activo():
    idx = {
        "pagos_global": {},
        "confirmados_activos": {"12345678901": [99]},
    }
    ev = _evaluar_fila_serial_cartera(
        idx,
        fecha=date(2026, 2, 1),
        serial_raw="12345678901",
        monto=25.0,
    )
    assert ev["estado"] == "IGUAL_100"
    assert "confirmado_id=99" in (ev.get("detalle") or "")


def test_buscar_igual_100_global_prioriza_pago():
    idx = {
        "pagos_global": {"99988877766": [(1, 2)]},
        "confirmados_activos": {"99988877766": [5]},
    }
    m = _buscar_igual_100_global(idx, ["99988877766"])
    assert m is not None
    assert m[1] == 1
    assert m[3] is None


def test_confirmados_activos_para_seriales_partes():
    from app.services.importacion_extracto_service import (
        _confirmados_activos_para_seriales,
    )
    from app.models.importacion_extracto import ImportacionExtractoPagoConfirmado

    c = ImportacionExtractoPagoConfirmado(
        id=7,
        serial="740087402484647",
        serial_norm="740087402484647",
        monto_usd=100,
        fecha_deposito=date(2026, 1, 1),
        estado="ACTIVO",
    )
    found = _confirmados_activos_para_seriales([c], ["740087402484647"])
    assert len(found) == 1
    assert int(found[0].id) == 7
