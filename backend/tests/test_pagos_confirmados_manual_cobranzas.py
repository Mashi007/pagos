"""Override manual fila Pagos confirmados."""
from datetime import date
from unittest.mock import MagicMock

from app.services.cobranzas.pagos_confirmados_manual_service import (
    aplicar_manual_a_lecturas_pagos_confirmados,
)


class _FakeRow:
    def __init__(self, fd, cantidad, monto_usd):
        self.fecha_lectura = fd
        self.cantidad = cantidad
        self.monto_usd = monto_usd


def test_aplicar_manual_sustituye_valores(monkeypatch):
    fd = date(2026, 9, 1)
    monkeypatch.setattr(
        "app.services.cobranzas.pagos_confirmados_manual_service.load_manual_pagos_confirmados_map",
        lambda _db: {fd: _FakeRow(fd, 9, 123.45)},
    )
    lecturas = [{"fecha": "2026-09-01", "cantidad": 2, "monto_usd": 50.0}]
    aplicar_manual_a_lecturas_pagos_confirmados(MagicMock(), lecturas)
    assert lecturas[0]["cantidad_automatica"] == 2
    assert lecturas[0]["monto_usd_automatico"] == 50.0
    assert lecturas[0]["cantidad"] == 9
    assert lecturas[0]["monto_usd"] == 123.45
    assert lecturas[0]["manual_override"] is True


def test_aplicar_manual_idempotente_con_automatico_guardado(monkeypatch):
    fd = date(2026, 9, 1)
    monkeypatch.setattr(
        "app.services.cobranzas.pagos_confirmados_manual_service.load_manual_pagos_confirmados_map",
        lambda _db: {fd: _FakeRow(fd, 9, 123.45)},
    )
    lecturas = [
        {
            "fecha": "2026-09-01",
            "cantidad": 9,
            "monto_usd": 123.45,
            "cantidad_automatica": 2,
            "monto_usd_automatico": 50.0,
            "manual_override": True,
        }
    ]
    aplicar_manual_a_lecturas_pagos_confirmados(MagicMock(), lecturas)
    assert lecturas[0]["cantidad"] == 9
    assert lecturas[0]["monto_usd"] == 123.45
    assert lecturas[0]["cantidad_automatica"] == 2
