"""Regla: sin institución bancaria no se guarda."""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.pago import PagoCreate, PagoUpdate
from app.services.institucion_bancaria_requerida import (
    error_si_falta_institucion,
    es_institucion_bancaria_valida,
    normalizar_institucion_bancaria_requerida,
)


def test_es_institucion_valida():
    assert es_institucion_bancaria_valida("Mercantil")
    assert es_institucion_bancaria_valida("BNC")
    assert not es_institucion_bancaria_valida("")
    assert not es_institucion_bancaria_valida(None)
    assert not es_institucion_bancaria_valida("Otros")
    assert not es_institucion_bancaria_valida("RAPICREDIT")
    assert not es_institucion_bancaria_valida("RAPI-CREDIT, C.A.")


def test_error_si_falta():
    assert error_si_falta_institucion("Mercantil") is None
    assert "obligatoria" in (error_si_falta_institucion("") or "").lower()
    assert "beneficiario" in (error_si_falta_institucion("RAPICREDIT") or "").lower()


def test_normalizar_requiere():
    assert normalizar_institucion_bancaria_requerida("  BNC  ") == "BNC"
    with pytest.raises(ValueError):
        normalizar_institucion_bancaria_requerida("")


def test_pago_create_exige_institucion():
    with pytest.raises(ValidationError):
        PagoCreate(
            cedula_cliente="V123",
            fecha_pago=date(2026, 7, 21),
            monto_pagado=Decimal("10"),
            numero_documento="12345",
            institucion_bancaria="",
        )
    with pytest.raises(ValidationError):
        PagoCreate(
            cedula_cliente="V123",
            fecha_pago=date(2026, 7, 21),
            monto_pagado=Decimal("10"),
            numero_documento="12345",
            institucion_bancaria="RAPICREDIT",
        )
    p = PagoCreate(
        cedula_cliente="V123",
        fecha_pago=date(2026, 7, 21),
        monto_pagado=Decimal("10"),
        numero_documento="12345",
        institucion_bancaria="Mercantil",
    )
    assert p.institucion_bancaria == "Mercantil"


def test_pago_update_no_permite_vaciar():
    with pytest.raises(ValidationError):
        PagoUpdate(institucion_bancaria="")
    with pytest.raises(ValidationError):
        PagoUpdate(institucion_bancaria="Otros")
    u = PagoUpdate(institucion_bancaria="BNC")
    assert u.institucion_bancaria == "BNC"
    assert PagoUpdate().institucion_bancaria is None
