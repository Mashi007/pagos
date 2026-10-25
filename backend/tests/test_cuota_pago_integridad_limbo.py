# -*- coding: utf-8 -*-
"""Anti-limbo: PAGADO sin cuota_pagos con cupo pendiente no debe regenerarse."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.cuota_pago_integridad import (
    demotar_pago_sin_aplicacion,
    pago_quedaria_limbo_pagado_sin_cuotas,
)


def test_demotar_pago_sin_aplicacion_limpia_marcas():
    p = SimpleNamespace(
        estado="PAGADO",
        conciliado=True,
        fecha_conciliacion="x",
        verificado_concordancia="SI",
    )
    demotar_pago_sin_aplicacion(p)
    assert p.estado == "PENDIENTE"
    assert p.conciliado is False
    assert p.fecha_conciliacion is None
    assert p.verificado_concordancia == "NO"


def test_limbo_false_si_ya_tiene_aplicaciones(monkeypatch):
    db = MagicMock()
    p = SimpleNamespace(id=1, prestamo_id=10, numero_documento="X", notas="")
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: True,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(db, p) is False


def test_limbo_false_si_preserva_abonos(monkeypatch):
    db = MagicMock()
    p = SimpleNamespace(
        id=2,
        prestamo_id=10,
        numero_documento="ABONOS-NOTIF-1812-AABB",
        notas="",
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: False,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(db, p) is False


def test_limbo_true_sin_aplicacion_con_cupo(monkeypatch):
    db = MagicMock()
    p = SimpleNamespace(id=3, prestamo_id=10, numero_documento="REF-1", notas="")
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.prestamo_tiene_cupo_aplicable_en_cuotas",
        lambda *_a, **_k: True,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(db, p) is True


def test_limbo_true_si_alta_ya_conciliada_con_cupo(monkeypatch):
    """Excel/Cobros nacen conciliado+SI+fecha; eso no debe apagar el anti-limbo."""
    from datetime import datetime

    db = MagicMock()
    p = SimpleNamespace(
        id=5,
        prestamo_id=10,
        numero_documento="88442211",
        referencia_pago="88442211",
        notas="",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=datetime(2026, 10, 20, 12, 0, 0),
        estado="PAGADO",
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.prestamo_tiene_cupo_aplicable_en_cuotas",
        lambda *_a, **_k: True,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(db, p) is True


def test_limbo_false_sin_aplicacion_sin_cupo_remanente(monkeypatch):
    db = MagicMock()
    p = SimpleNamespace(id=4, prestamo_id=10, numero_documento="REF-2", notas="")
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.prestamo_tiene_cupo_aplicable_en_cuotas",
        lambda *_a, **_k: False,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(db, p) is False
