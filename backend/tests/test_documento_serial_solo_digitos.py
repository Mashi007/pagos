"""Serial / numero_documento: solo dígitos (cualquier banco)."""
from app.core.documento import (
    MSG_SERIAL_SOLO_DIGITOS,
    compose_numero_documento_almacenado,
    normalize_documento,
    split_numero_documento_almacenado,
)


def test_quita_letras_y_signos_bnc():
    assert normalize_documento("BNC54879263323") == "54879263323"
    assert normalize_documento("BNC/54879263323") == "54879263323"
    assert normalize_documento("BINANCE/419480309945163776") == "419480309945163776"
    assert normalize_documento("VE-123-456") == "123456"
    assert normalize_documento("  7400 8740 ") == "74008740"


def test_vacio_si_solo_letras():
    assert normalize_documento("BNC/") is None
    assert normalize_documento("REF.") is None


def test_conserva_sufijo_visto_admin():
    assert normalize_documento("419480309945163776_A1020") == "419480309945163776_A1020"
    assert normalize_documento("BNC419480309945163776_p0451") == "419480309945163776_P0451"


def test_compose_con_codigo_sigue_ok():
    doc = compose_numero_documento_almacenado("BNC740087401373233", "A2637")
    assert doc is not None
    assert "§CD:A2637" in doc
    base, code = split_numero_documento_almacenado(doc)
    assert base == "740087401373233"
    assert code == "A2637"


def test_mensaje_serial():
    assert "dígitos" in MSG_SERIAL_SOLO_DIGITOS.lower() or "digitos" in MSG_SERIAL_SOLO_DIGITOS.lower()
