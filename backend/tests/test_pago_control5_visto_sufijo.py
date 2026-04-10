"""Tests unitarios: sufijo admin y excepcion Visto control 5 (sin BD)."""

from app.services.pago_control5_visto_service import (
    extraer_token_sufijo_visto_desde_documento,
    numero_documento_tiene_sufijo_visto_admin,
)


def test_numero_documento_tiene_sufijo_visto_admin_positivo() -> None:
    assert numero_documento_tiene_sufijo_visto_admin("REF123_A0042") is True
    assert numero_documento_tiene_sufijo_visto_admin("  x_p9999 ") is True


def test_numero_documento_tiene_sufijo_visto_admin_negativo() -> None:
    assert numero_documento_tiene_sufijo_visto_admin("") is False
    assert numero_documento_tiene_sufijo_visto_admin("REF123") is False
    assert numero_documento_tiene_sufijo_visto_admin("REF_A123") is False
    assert numero_documento_tiene_sufijo_visto_admin("REF_A12345") is False


def test_extraer_token_sufijo_visto_desde_documento() -> None:
    assert extraer_token_sufijo_visto_desde_documento("BNC/1_A0042") == "A0042"
    assert extraer_token_sufijo_visto_desde_documento("z_p0001") == "P0001"
    assert extraer_token_sufijo_visto_desde_documento("sin_sufijo") is None
