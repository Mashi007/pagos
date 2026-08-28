# -*- coding: utf-8 -*-
"""Helpers anti-limbo: bancos E/F sin auto-alta; listos ANALIZADOS sin temporal."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pagos_gmail.anti_limbo_post_lote import (
    _fmt_desde_banco,
    message_ids_listos_para_analizados,
)


def test_bancos_abcd_nr_mapean():
    assert _fmt_desde_banco("MERCANTIL") == "A"
    assert _fmt_desde_banco("BNC") == "B"
    assert _fmt_desde_banco("BINANCE") == "C"
    assert _fmt_desde_banco("BDV") == "D"
    assert _fmt_desde_banco("RECIBO") == "NR"


def test_bancamiga_tesoro_sin_auto_alta():
    assert _fmt_desde_banco("BANCAMIGA") is None
    assert _fmt_desde_banco("TESORO") is None
    assert _fmt_desde_banco("Banco del Tesoro") is None


def test_analizados_omite_ids_en_temporal(monkeypatch):
    class _FakeScalars:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return _FakeScalars(self._rows)

    class _FakeDb:
        def execute(self, _stmt):
            return _FakeResult(["m-limbo", "m-otro"])

    out = message_ids_listos_para_analizados(
        _FakeDb(),
        sync_id=1,
        candidate_message_ids=["m-ok", "m-limbo", "m-otro", ""],
    )
    assert out["listos"] == ["m-ok"]
    assert set(out["pendientes_temporal"]) == {"m-limbo", "m-otro"}
