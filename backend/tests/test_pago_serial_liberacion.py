# -*- coding: utf-8 -*-
"""Serial único solo en pagos operativos; al borrar/editar se libera."""

from app.models.pago import pago_estado_ocupa_serial
from app.services.pago_numero_documento import numero_documento_ya_registrado


class _FakeDb:
    def scalar(self, _q):
        return None

    def execute(self, _q, *a, **k):
        class _R:
            rowcount = 0

            def all(self):
                return []

            def first(self):
                return None

        return _R()

    def flush(self):
        return None


def test_estados_inactivos_no_ocupan_serial():
    assert pago_estado_ocupa_serial("PAGADO") is True
    assert pago_estado_ocupa_serial("PENDIENTE") is True
    assert pago_estado_ocupa_serial(None) is True
    assert pago_estado_ocupa_serial("ANULADO_IMPORT") is False
    assert pago_estado_ocupa_serial("ANULADO") is False
    assert pago_estado_ocupa_serial("DUPLICADO") is False
    assert pago_estado_ocupa_serial("REVERSADO") is False


def test_ya_registrado_sin_filas_operativas_permite_reingreso(monkeypatch):
    monkeypatch.setattr(
        "app.services.pago_numero_documento.documento_colisiona_evasion_registrado",
        lambda *_a, **_k: False,
    )
    assert numero_documento_ya_registrado(_FakeDb(), "740087401373233") is False
