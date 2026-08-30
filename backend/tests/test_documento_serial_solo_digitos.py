"""Serial / numero_documento: solo dígitos (cualquier banco)."""
from app.core.documento import (
    MSG_SERIAL_SOLO_DIGITOS,
    compose_numero_documento_almacenado,
    normalize_documento,
    split_numero_documento_almacenado,
)


def test_quita_cualquier_letra_y_signo():
    """Al comparar: solo números. Cualquier letra/signo (antes o en medio) no cuenta."""
    digitos = "740087403151598"
    equivalentes = [
        digitos,
        f"MER/{digitos}",
        f"BNC/{digitos}",
        f"BNC{digitos}",
        f"BINANCE/{digitos}",
        f"REF.{digitos}",
        f"Nro:{digitos}",
        f"VE-{digitos}",
        f"***{digitos}***",
        f"  {digitos}  ",
        f"{digitos[:5]}-{digitos[5:]}",
    ]
    for raw in equivalentes:
        assert normalize_documento(raw) == digitos, raw
        assert normalize_documento(raw) == normalize_documento(digitos)


def test_quita_letras_y_signos_bnc():
    assert normalize_documento("BNC54879263323") == "54879263323"
    assert normalize_documento("BNC/54879263323") == "54879263323"
    assert normalize_documento("BINANCE/419480309945163776") == "419480309945163776"
    assert normalize_documento("VE-123-456") == "123456"
    assert normalize_documento("  7400 8740 ") == "74008740"
    assert normalize_documento("MER/740087403151598") == "740087403151598"


def test_vacio_si_solo_signos():
    assert normalize_documento("///") is None
    assert normalize_documento("...") is None


def test_solo_letras_se_conservan():
    assert normalize_documento("BNC/") == "BNC"
    assert normalize_documento("REF.") == "REF"
    assert normalize_documento("ABCXYZ") == "ABCXYZ"


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


def test_compose_token_d_nuevo_contrato():
    from app.core.documento import PREFIJO_CODIGO_DESAMBIGUACION

    assert PREFIJO_CODIGO_DESAMBIGUACION == "D"
    doc = compose_numero_documento_almacenado("54879263323", "D1020")
    assert doc == "54879263323 §CD:D1020"
    base, code = split_numero_documento_almacenado(doc)
    assert base == "54879263323"
    assert code == "D1020"
    # Legado _A/_P sigue normalizándose
    assert normalize_documento("54879263323_A9999") == "54879263323_A9999"


def test_zelle_conserva_letras_y_numeros():
    assert normalize_documento("Ab12-Cd34", institucion="Zelle") == "AB12CD34"
    assert normalize_documento("zelle-ref-9x", institucion="ZELLE PAY") == "ZELLEREF9X"
    # Sin institución Zelle: se quitan letras
    assert normalize_documento("Ab12Cd34") == "1234"


def test_compose_zelle_con_codigo():
    doc = compose_numero_documento_almacenado(
        "Ab12Cd", "D1020", institucion="Zelle"
    )
    assert doc == "AB12CD §CD:D1020"
    base, code = split_numero_documento_almacenado(doc)
    assert base == "AB12CD"
    assert code == "D1020"


def test_mensaje_serial():
    assert "dígitos" in MSG_SERIAL_SOLO_DIGITOS.lower() or "digitos" in MSG_SERIAL_SOLO_DIGITOS.lower()
