"""Hamming/truncado vs cartera no debe auto-crear un segundo pago."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/pagos-test-serial-ambiguo.db")
os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.cobros.cobros_publico_reporte_service import (
    intentar_importar_reportado_automatico,
)
from app.services.cobros.pago_reportado_documento import (
    reportado_serial_ambiguo_para_autoimport,
)
from app.services.pago_numero_documento import documento_serial_ambiguo_en_cartera
from app.services.pagos_gmail.parse_campos_comprobante import (
    seriales_banco_ambiguos_para_revision,
)


SERIAL_A = "7400874101194"
SERIAL_B = "7400874101195"  # Hamming 1


def test_seriales_hamming_1_son_ambiguos_no_iguales():
    assert seriales_banco_ambiguos_para_revision(SERIAL_A, SERIAL_B) is True
    assert seriales_banco_ambiguos_para_revision(SERIAL_A, SERIAL_A) is False


def test_documento_serial_ambiguo_en_cartera_mismo_cliente():
    db = MagicMock()
    db.execute.return_value = [
        (10, SERIAL_A, SERIAL_A, "V12345678"),
    ]
    assert documento_serial_ambiguo_en_cartera(
        db, SERIAL_B, cedula_cliente="V12345678"
    ) is True


def test_documento_serial_ambiguo_otro_cliente_no_bloquea():
    db = MagicMock()
    db.execute.return_value = [
        (10, SERIAL_A, SERIAL_A, "V99999999"),
    ]
    assert documento_serial_ambiguo_en_cartera(
        db, SERIAL_B, cedula_cliente="V12345678"
    ) is False


def test_documento_serial_ambiguo_exacto_no_es_ambiguo():
    db = MagicMock()
    db.execute.return_value = [
        (10, SERIAL_A, SERIAL_A, "V12345678"),
    ]
    assert documento_serial_ambiguo_en_cartera(
        db, SERIAL_A, cedula_cliente="V12345678"
    ) is False


def test_reportado_ambiguo_por_otro_reportado_activo():
    db = MagicMock()
    pr = SimpleNamespace(
        id=2,
        numero_operacion=SERIAL_B,
        referencia_interna="RPC-2",
        tipo_cedula="V",
        numero_cedula="12345678",
    )
    db.execute.return_value = [
        (1, SERIAL_A, "V", "12345678"),
    ]
    with patch(
        "app.services.pago_numero_documento.documento_serial_ambiguo_en_cartera",
        return_value=False,
    ):
        assert reportado_serial_ambiguo_para_autoimport(db, pr) is True


def test_autoimport_hamming_cartera_va_a_revision():
    pr = SimpleNamespace(
        id=9,
        estado="aprobado",
        moneda="USD",
        monto=50.0,
        numero_operacion=SERIAL_B,
        referencia_interna="RPC-9",
        institucion_financiera="MERCANTIL",
        tipo_cedula="V",
        numero_cedula="12345678",
        fecha_pago=date(2026, 8, 1),
        gemini_comentario="",
        falla_validadores_manual=False,
    )
    db = MagicMock()
    with patch(
        "app.services.cobros.cobros_publico_reporte_service.pago_reportado_colisiona_tabla_pagos",
        create=True,
        return_value=False,
    ), patch(
        "app.services.cobros.pago_reportado_documento.pago_reportado_colisiona_tabla_pagos",
        return_value=False,
    ), patch(
        "app.services.cobros.pago_reportado_documento.reportado_serial_ambiguo_para_autoimport",
        return_value=True,
    ):
        res = intentar_importar_reportado_automatico(db, pr, "RPC-9", "TEST")
    assert pr.estado == "en_revision"
    assert pr.falla_validadores_manual is True
    assert res.error == "serial_ambiguo_revision"
    db.commit.assert_called()
