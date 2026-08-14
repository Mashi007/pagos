"""Digitalización incompleta → revisión manual."""
from datetime import date

from app.services.cobros.digitalizacion_revision_manual import (
    digitalizacion_requiere_revision_manual,
    campos_criticos_faltantes_digitalizacion,
)


def test_completo_no_requiere_revision():
    assert (
        digitalizacion_requiere_revision_manual(
            fecha_pago=date(2026, 7, 21),
            institucion_financiera="Mercantil",
            numero_operacion="740087408543435",
            monto=96.0,
        )
        is None
    )


def test_faltan_campos_requiere_revision():
    msg = digitalizacion_requiere_revision_manual(
        fecha_pago=None,
        institucion_financiera="",
        numero_operacion="",
        monto=None,
    )
    assert msg is not None
    assert "revisión manual" in msg.lower()
    faltan = campos_criticos_faltantes_digitalizacion(
        fecha_pago=None,
        institucion_financiera="RAPICREDIT",
        numero_operacion="00939",
        monto=10.0,
    )
    assert "institución bancaria" in faltan
    assert "fecha" in faltan


def test_serial_rpc_o_vacio_requiere_revision():
    faltan = campos_criticos_faltantes_digitalizacion(
        fecha_pago=date(2026, 7, 21),
        institucion_financiera="Mercantil",
        numero_operacion="RPC-20260807-00091",
        monto=135.0,
    )
    assert "número de operación" in faltan
    msg = digitalizacion_requiere_revision_manual(
        fecha_pago=date(2026, 7, 21),
        institucion_financiera="Mercantil",
        numero_operacion="",
        monto=135.0,
    )
    assert msg is not None
    assert "número de operación" in msg.lower() or "campos no digitalizados" in msg.lower()
