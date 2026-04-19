# -*- coding: utf-8 -*-
"""
Recibos: ventanas fecha_registro, sin casos, y ejecutar con send_email mockeado.

Desde backend/:
  pytest tests/test_recibos_conciliacion_email_job.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.cuota_estado import hoy_negocio
from app.services.recibos_conciliacion_email_job import (
    bounds_fecha_registro_recibos_24h_hasta_15,
    ejecutar_recibos_envio_slot,
    listar_pagos_recibos_ventana,
)


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_bounds_recibos_24h_hasta_15_naive_caracas():
    d = date(2026, 4, 19)
    s, e = bounds_fecha_registro_recibos_24h_hasta_15(d)
    assert s == datetime(2026, 4, 18, 15, 0, 0)
    assert e == datetime(2026, 4, 19, 15, 0, 0)


def test_ejecutar_sin_casos_en_ventana():
    db = MagicMock()
    fixed = date(2026, 4, 19)
    with patch(
        "app.services.recibos_conciliacion_email_job.hoy_negocio",
        return_value=fixed,
    ), patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=[],
    ):
        out = ejecutar_recibos_envio_slot(db, fecha_dia=fixed, solo_simular=False)
    assert out["sin_casos_en_ventana"] is True
    assert out["pagos_en_ventana"] == 0
    assert out["enviados"] == 0


def test_ejecutar_simulacion_genera_pdf_sin_smtp_si_no_modo_pruebas():
    db = MagicMock()
    pagos = [
        {
            "pago_id": 900001,
            "cedula": "V-12345678",
            "cedula_normalizada": "V12345678",
            "fecha_registro": "2026-04-19T08:00:00",
            "monto_pagado": 1.0,
        }
    ]
    datos = {
        "cedula_display": "V-12345678",
        "nombre": "Cliente Prueba",
        "fecha_corte": date(2026, 4, 19),
        "prestamos_list": [{"id": 1, "producto": "X", "total_financiamiento": 100.0, "estado": "APROBADO"}],
        "amortizaciones_por_prestamo": [],
        "pagos_realizados": [],
        "emails": ["cliente@example.com"],
    }
    pdf_ok = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    fixed = date(2026, 4, 19)
    with patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=pagos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.get_email_activo_servicio",
        return_value=True,
    ), patch(
        "app.services.recibos_conciliacion_email_job._ya_enviado_recibo",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_datos_estado_cuenta_cliente",
        return_value=datos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.cliente_bloqueado_por_desistimiento",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_recibos_cliente_estado_cuenta",
        return_value=[],
    ), patch(
        "app.services.recibos_conciliacion_email_job.generar_pdf_estado_cuenta",
        return_value=pdf_ok,
    ) as m_pdf, patch(
        "app.services.recibos_conciliacion_email_job.get_modo_pruebas_email",
        return_value=(False, []),
    ), patch(
        "app.services.recibos_conciliacion_email_job.send_email",
    ) as m_send:
        out = ejecutar_recibos_envio_slot(db, fecha_dia=fixed, solo_simular=True)
    m_pdf.assert_called_once()
    m_send.assert_not_called()
    assert out["sin_casos_en_ventana"] is False
    assert out["cedulas_distintas"] == 1
    det = [x for x in out["detalles"] if x.get("motivo") == "simulacion_ok"]
    assert len(det) == 1
    assert det[0].get("emails") == ["cliente@example.com"]


def test_ejecutar_envio_mockea_smtp_y_pdf_valido():
    db = MagicMock()
    pagos = [
        {
            "pago_id": 900002,
            "cedula": "V-87654321",
            "cedula_normalizada": "V87654321",
            "fecha_registro": "2026-04-19T10:00:00",
            "monto_pagado": 2.5,
        }
    ]
    datos = {
        "cedula_display": "V-87654321",
        "nombre": "Otro Cliente",
        "fecha_corte": datetime(2026, 4, 19, 12, 0, 0),
        "prestamos_list": [{"id": 2, "producto": "Y", "total_financiamiento": 200.0, "estado": "APROBADO"}],
        "amortizaciones_por_prestamo": [],
        "pagos_realizados": [],
        "emails": ["otro@example.com"],
    }
    pdf_ok = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"

    fixed = date(2026, 4, 19)
    with patch(
        "app.services.recibos_conciliacion_email_job.hoy_negocio",
        return_value=fixed,
    ), patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=pagos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.get_email_activo_servicio",
        return_value=True,
    ), patch(
        "app.services.recibos_conciliacion_email_job._ya_enviado_recibo",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_datos_estado_cuenta_cliente",
        return_value=datos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.cliente_bloqueado_por_desistimiento",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_recibos_cliente_estado_cuenta",
        return_value=[],
    ), patch(
        "app.services.recibos_conciliacion_email_job.generar_pdf_estado_cuenta",
        return_value=pdf_ok,
    ), patch(
        "app.services.recibos_conciliacion_email_job.send_email",
        return_value=(True, None),
    ) as m_send:
        out = ejecutar_recibos_envio_slot(db, fecha_dia=fixed, solo_simular=False)

    assert out["enviados"] == 1
    assert out["fallidos"] == 0
    assert out.get("omitidos_error_estado_cuenta", 0) == 0
    m_send.assert_called_once()
    kwargs = m_send.call_args.kwargs
    assert kwargs.get("servicio") == "recibos"
    assert kwargs.get("tipo_tab") == "recibos"
    args = m_send.call_args.args
    assert args[1]  # asunto
    atts = kwargs.get("attachments") or []
    assert len(atts) == 1
    assert atts[0][1].startswith(b"%PDF")
    assert db.add.call_count == 2
    db.commit.assert_called_once()


def test_ejecutar_pasa_base_url_y_recibo_token_al_pdf_cuando_hay_base_publica():
    """El PDF adjunto debe poder incluir «Ver recibo» como en el portal (base + JWT)."""
    db = MagicMock()
    pagos = [
        {
            "pago_id": 900010,
            "cedula": "V-12345678",
            "cedula_normalizada": "V12345678",
            "fecha_registro": "2026-04-19T10:00:00",
            "monto_pagado": 1.0,
        }
    ]
    datos = {
        "cedula_display": "V-12345678",
        "nombre": "Cliente",
        "fecha_corte": date(2026, 4, 19),
        "prestamos_list": [{"id": 1, "producto": "X", "total_financiamiento": 100.0, "estado": "APROBADO"}],
        "amortizaciones_por_prestamo": [],
        "pagos_realizados": [],
        "emails": ["c@example.com"],
    }
    pdf_ok = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    fixed = date(2026, 4, 19)
    with patch(
        "app.services.recibos_conciliacion_email_job.hoy_negocio",
        return_value=fixed,
    ), patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=pagos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.get_email_activo_servicio",
        return_value=True,
    ), patch(
        "app.services.recibos_conciliacion_email_job._ya_enviado_recibo",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_datos_estado_cuenta_cliente",
        return_value=datos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.cliente_bloqueado_por_desistimiento",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.obtener_recibos_cliente_estado_cuenta",
        return_value=[],
    ), patch(
        "app.services.recibos_conciliacion_email_job._base_url_publico_recibos_pdf",
        return_value="https://api.example.com",
    ), patch(
        "app.services.recibos_conciliacion_email_job._recibo_token_para_pdf_recibos",
        return_value="jwt-recibo-test",
    ), patch(
        "app.services.recibos_conciliacion_email_job.generar_pdf_estado_cuenta",
        return_value=pdf_ok,
    ) as m_pdf, patch(
        "app.services.recibos_conciliacion_email_job.send_email",
        return_value=(True, None),
    ):
        ejecutar_recibos_envio_slot(db, fecha_dia=fixed, solo_simular=False)
    kw = m_pdf.call_args.kwargs
    assert kw.get("base_url") == "https://api.example.com"
    assert kw.get("recibo_token") == "jwt-recibo-test"


def test_ejecutar_email_recibos_desactivado_no_smtp():
    db = MagicMock()
    pagos = [
        {
            "pago_id": 900003,
            "cedula": "V-11111111",
            "cedula_normalizada": "V11111111",
            "fecha_registro": "2026-04-19T09:00:00",
            "monto_pagado": 1.0,
        }
    ]
    fixed = date(2026, 4, 19)
    with patch(
        "app.services.recibos_conciliacion_email_job.hoy_negocio",
        return_value=fixed,
    ), patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=pagos,
    ), patch(
        "app.services.recibos_conciliacion_email_job.get_email_activo_servicio",
        return_value=False,
    ), patch(
        "app.services.recibos_conciliacion_email_job.send_email",
    ) as m_send:
        out = ejecutar_recibos_envio_slot(db, fecha_dia=fixed, solo_simular=False)
    m_send.assert_not_called()
    assert out.get("error") == "email_activo_recibos_desactivado"
    assert out["pagos_en_ventana"] == 1


def test_ejecutar_real_rechaza_fecha_distinta_a_hoy_sin_consultar_bd():
    """Envío real si fecha_dia ≠ hoy Caracas: no listar pagos ni enviar (regla job programado)."""
    db = MagicMock()
    ayer = hoy_negocio() - timedelta(days=1)
    with patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
    ) as m_listar:
        out = ejecutar_recibos_envio_slot(db, fecha_dia=ayer, solo_simular=False)
    m_listar.assert_not_called()
    assert out.get("error") == "envio_real_solo_fecha_recepcion_hoy_caracas"
    assert out.get("hoy_negocio") == hoy_negocio().isoformat()
    assert out["enviados"] == 0


def test_ejecutar_real_fecha_pasada_con_permite_lista_pagos():
    """Envío real día pasado con flag admin: sí consulta ventana (mismo criterio que listado)."""
    db = MagicMock()
    fixed = date(2026, 4, 19)
    ayer = date(2026, 4, 18)
    with patch(
        "app.services.recibos_conciliacion_email_job.hoy_negocio",
        return_value=fixed,
    ), patch(
        "app.services.recibos_conciliacion_email_job.listar_pagos_recibos_ventana",
        return_value=[],
    ) as m_listar:
        out = ejecutar_recibos_envio_slot(
            db,
            fecha_dia=ayer,
            solo_simular=False,
            permite_envio_real_fecha_no_hoy=True,
        )
    m_listar.assert_called_once()
    assert out.get("error") is None
    assert out["sin_casos_en_ventana"] is True
    assert out["pagos_en_ventana"] == 0


def test_listar_pagos_recibos_ventana_estructura_si_hay_datos(db):
    """Integración ligera: si la BD tiene filas que cumplen el criterio, validar claves."""
    rows = listar_pagos_recibos_ventana(db, fecha_dia=date(2020, 1, 1))
    assert isinstance(rows, list)
    if not rows:
        pytest.skip("Sin pagos conciliados PAGADO en ventana de prueba (BD vacía o sin coincidencias)")
    r0 = rows[0]
    assert set(r0.keys()) >= {
        "pago_id",
        "cedula",
        "cedula_normalizada",
        "fecha_registro",
        "monto_pagado",
    }
    assert isinstance(r0["pago_id"], int)
