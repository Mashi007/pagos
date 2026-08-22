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


def test_documento_numero_desde_pago_reportado_zelle_conserva_letras():
    """Cobros → cartera must not strip Zelle confirmation letters."""
    from types import SimpleNamespace

    from app.services.cobros.pago_reportado_documento import (
        claves_documento_pago_para_reportado,
        documento_numero_desde_pago_reportado,
    )

    pr = SimpleNamespace(
        numero_operacion="Ab12-Cd34",
        referencia_interna="RPC-20260821-00001",
        institucion_financiera="Zelle",
    )
    raw, norm = documento_numero_desde_pago_reportado(pr)
    assert raw == "Ab12-Cd34"
    assert norm == "AB12CD34"
    claves = claves_documento_pago_para_reportado(pr)
    assert "AB12CD34" in claves
    assert "1234" not in claves


def test_documento_numero_desde_pago_reportado_bnc_sigue_solo_digitos():
    from types import SimpleNamespace

    from app.services.cobros.pago_reportado_documento import (
        documento_numero_desde_pago_reportado,
    )

    pr = SimpleNamespace(
        numero_operacion="BNC54879263323",
        referencia_interna="RPC-20260821-00002",
        institucion_financiera="BNC",
    )
    _raw, norm = documento_numero_desde_pago_reportado(pr)
    assert norm == "54879263323"
