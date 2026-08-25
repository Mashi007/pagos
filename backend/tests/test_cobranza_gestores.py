# -*- coding: utf-8 -*-
"""Tests unitarios de constantes y utilidades de gestores de cobranza."""
from __future__ import annotations

import re
from datetime import date
from types import SimpleNamespace

from app.services.cobranzas.gestores_constantes import GESTORES, GESTOR_SLUGS
from app.services.cobranzas.gestores_service import (
    _agrupar_universo_por_cedula,
    _gestor_mayoria_en_grupo,
    _metricas_cuotas_atraso,
    listar_gestores,
)
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd


def test_hay_nueve_gestores():
    assert len(GESTORES) == 9
    assert len(GESTOR_SLUGS) == 9
    assert len(listar_gestores()) == 9
    assert GESTORES[0][1] == "Bisleida Aponte"
    assert GESTORES[-1][1] == "Glainet Dudamel"


def test_metricas_vencido_y_mora():
    cuotas = [
        SimpleNamespace(
            fecha_vencimiento=date(2026, 3, 15),
            estado="VENCIDO",
            monto=100,
            total_pagado=20,
        ),
        SimpleNamespace(
            fecha_vencimiento=date(2026, 4, 1),
            estado="MORA",
            monto=200,
            total_pagado=0,
        ),
        SimpleNamespace(
            fecha_vencimiento=date(2026, 2, 1),
            estado="VENCIDO",
            monto=50,
            total_pagado=0,
        ),  # fuera de rango (antes de marzo-2026)
        SimpleNamespace(
            fecha_vencimiento=date(2026, 5, 1),
            estado="PAGADO",
            monto=80,
            total_pagado=80,
        ),
    ]
    m = _metricas_cuotas_atraso(
        cuotas, desde=date(2026, 3, 1), hasta=date(2026, 8, 24)
    )
    assert m["cant_vencidas"] == 1
    assert m["usd_vencidas"] == 80.0
    assert m["cant_mora"] == 1
    assert m["usd_mora"] == 200.0
    assert m["carga_usd"] == 280.0
    assert m["total_pagado"] == 100.0


def test_fecha_inicio_cartera_gestores_es_marzo():
    from app.services.cobranzas.gestores_constantes import FECHA_INICIO_CARTERA_GESTORES

    assert FECHA_INICIO_CARTERA_GESTORES == date(2026, 3, 1)


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


def test_agrupar_universo_misma_cedula_un_bloque():
    items = [
        {
            "prestamo_id": 1,
            "cedula_clave": "V123",
            "carga_usd": 100.0,
            "carga_cuotas": 2.0,
        },
        {
            "prestamo_id": 2,
            "cedula_clave": "V123",
            "carga_usd": 50.0,
            "carga_cuotas": 1.0,
        },
        {
            "prestamo_id": 3,
            "cedula_clave": "V999",
            "carga_usd": 10.0,
            "carga_cuotas": 1.0,
        },
    ]
    grupos = _agrupar_universo_por_cedula(items)
    by_clave = {g["cedula_clave"]: g for g in grupos}
    assert len(grupos) == 2
    assert len(by_clave["V123"]["items"]) == 2
    assert by_clave["V123"]["carga_usd"] == 150.0
    assert len(by_clave["V999"]["items"]) == 1


def test_gestor_mayoria_consolida_cedula_partida():
    assert _gestor_mayoria_en_grupo(["a", "b", "a"]) == "a"
    assert _gestor_mayoria_en_grupo(["b", "a"]) == "a"  # empate 1-1 → slug menor


def test_cedula_v_guion_misma_clave():
    assert texto_cedula_comparable_bd("V-12345678") == texto_cedula_comparable_bd(
        "V12345678"
    )


def test_nombre_archivo_informe_diario():
    from datetime import date as date_cls

    nombre = "Bisleida Aponte"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", nombre).strip("_")
    hoy = date_cls(2026, 8, 24).isoformat()
    assert f"informe_diario_{safe}_{hoy}.xlsx" == "informe_diario_Bisleida_Aponte_2026-08-24.xlsx"
