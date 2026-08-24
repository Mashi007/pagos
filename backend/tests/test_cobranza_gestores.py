# -*- coding: utf-8 -*-
"""Tests unitarios de constantes y utilidades de gestores de cobranza."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.cobranzas.gestores_constantes import GESTORES, GESTOR_SLUGS
from app.services.cobranzas.gestores_service import _metricas_cuotas_atraso, listar_gestores


def test_hay_nueve_gestores():
    assert len(GESTORES) == 9
    assert len(GESTOR_SLUGS) == 9
    assert len(listar_gestores()) == 9
    assert GESTORES[0][1] == "Bisleida Aponte"
    assert GESTORES[-1][1] == "Glainet Dudamel"


def test_metricas_vencido_y_mora():
    cuotas = [
        SimpleNamespace(
            fecha_vencimiento=date(2026, 2, 1),
            estado="VENCIDO",
            monto=100,
            total_pagado=20,
        ),
        SimpleNamespace(
            fecha_vencimiento=date(2026, 3, 1),
            estado="MORA",
            monto=200,
            total_pagado=0,
        ),
        SimpleNamespace(
            fecha_vencimiento=date(2025, 12, 1),
            estado="VENCIDO",
            monto=50,
            total_pagado=0,
        ),  # fuera de rango ene-2026
        SimpleNamespace(
            fecha_vencimiento=date(2026, 4, 1),
            estado="PAGADO",
            monto=80,
            total_pagado=80,
        ),
    ]
    m = _metricas_cuotas_atraso(
        cuotas, desde=date(2026, 1, 1), hasta=date(2026, 8, 24)
    )
    assert m["cant_vencidas"] == 1
    assert m["usd_vencidas"] == 80.0
    assert m["cant_mora"] == 1
    assert m["usd_mora"] == 200.0
    assert m["carga_usd"] == 280.0
    assert m["total_pagado"] == 100.0


def test_asunto_y_cuerpo_email_gestores():
    from app.services.cobranzas.gestores_constantes import (
        EMAIL_GESTORES_BCC,
        EMAIL_GESTORES_TO,
    )

    hoy = "2026-08-24"
    assert EMAIL_GESTORES_TO == "operaciones@rapicreditca.com"
    assert EMAIL_GESTORES_BCC == "itmaster@rapicreditca.com"
    assert f"Listas actualizadas {hoy}" == "Listas actualizadas 2026-08-24"
    assert "Eduardo: Adjunto listas actualizadas" == "Eduardo: Adjunto listas actualizadas"
