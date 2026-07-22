"""Tests plantilla Recibo (formato G) — escáner y Excel Gmail."""


def test_canonical_institucion_recibo():
    from app.services.pagos_gmail.gemini_service import _canonical_institucion_escaner

    assert _canonical_institucion_escaner("Recibo") == "Recibo"
    assert _canonical_institucion_escaner("RECIBO") == "Recibo"
    assert _canonical_institucion_escaner("Recibos") == "Recibo"


def test_inferir_institucion_recibo_toro():
    from app.services.pagos_gmail.gemini_service import _inferir_institucion_heuristica_escaner

    assert _inferir_institucion_heuristica_escaner("plantilla G Recibo TORO MOTORCYCLES") == "Recibo"


def test_inferir_institucion_mercantil_serial_740087():
    from app.services.pagos_gmail.gemini_service import _inferir_institucion_heuristica_escaner

    assert (
        _inferir_institucion_heuristica_escaner("740087401050039")
        == "Mercantil"
    )


def test_resolve_banco_excel_formato_g():
    from app.services.pagos_gmail.helpers import resolve_banco_para_excel_pagos_gmail

    assert (
        resolve_banco_para_excel_pagos_gmail(
            "G",
            "NA",
            default_a="Mercantil",
            default_b="BNC",
            default_c="BINANCE",
            default_d="BDV",
            default_e="Bancamiga",
            default_f="Banco del Tesoro",
            default_g="Recibo",
        )
        == "Recibo"
    )


def test_etiqueta_gmail_recibo_label():
    from app.services.pagos_gmail.gmail_service import PAGOS_GMAIL_LABEL_RECIBO

    assert PAGOS_GMAIL_LABEL_RECIBO == "RECIBO"


def test_pagos_gmail_formatos_incluye_g():
    from app.services.pagos_gmail.gemini_service import PAGOS_GMAIL_FORMATOS_PLANTILLA

    assert "G" in PAGOS_GMAIL_FORMATOS_PLANTILLA


def test_parse_formato_g_no_se_descarta_como_ninguno():
    from app.services.pagos_gmail.gemini_service import _parse_formato_y_pagos_json

    raw = """
    {"formato":"G","fecha_pago":"08/06/2024","cedula":"18231931","monto":"200",
     "numero_referencia":"00972","email_cliente":"NA","banco":"Recibo"}
    """
    fmt, fields = _parse_formato_y_pagos_json(raw)
    assert fmt == "G"
    assert fields["numero_referencia"] == "00972"
    assert fields["cedula"] == "18231931"
    assert fields["monto"] == "200.00"
    assert fields["banco"] == "Recibo"


def test_guess_bank_hint_toro_recibo():
    from app.services.pagos_gmail.gemini_service import _guess_bank_hint_from_text

    hint = _guess_bank_hint_from_text(
        '{"formato":"ninguno","banco":"Recibo"} TORO MOTORCYCLES RECIBO',
        "recibo.jpg",
        "campos_incompletos_g",
    )
    assert hint == "G"

def test_canonical_rechaza_beneficiario_rapicredit():
    from app.services.pagos_gmail.gemini_service import (
        _canonical_institucion_escaner,
        _es_beneficiario_rapicredit_como_banco,
        _resolver_institucion_escaner,
    )

    for raw in (
        "RAPICREDIT",
        "RAPI-CREDIT",
        "Rapicredit",
        "RAPI CREDIT",
        "RAPI-CREDIT, C.A.",
        "BAPI-CREDIT",
        "Rapicredi",
    ):
        assert _es_beneficiario_rapicredit_como_banco(raw), raw
        assert _canonical_institucion_escaner(raw) == "", raw

    assert _canonical_institucion_escaner("Mercantil") == "Mercantil"
    assert _canonical_institucion_escaner("BNC") == "BNC"
    assert not _es_beneficiario_rapicredit_como_banco("credit")
    assert not _es_beneficiario_rapicredit_como_banco("Banco Nacional de Credito")

    # Rechaza RAPICREDIT y recupera banco por serial / patrón de operación
    assert (
        _resolver_institucion_escaner(
            "RAPICREDIT",
            notas="",
            numero_operacion="740087408543435",
        )
        == "Mercantil"
    )
    assert (
        _resolver_institucion_escaner(
            "RAPICREDIT",
            numero_operacion="444102322113560576",
        )
        == "BINANCE"
    )
    assert (
        _resolver_institucion_escaner("RAPI-CREDIT", numero_operacion="00939")
        == "Recibo"
    )
    # Sin número ni plantilla: vacio (API exige banco; no persistir RAPICREDIT)
    assert _resolver_institucion_escaner("RAPICREDIT", notas="", numero_operacion="") == ""


def test_inferir_no_mercantil_solo_por_rapicredit():
    from app.services.pagos_gmail.gemini_service import _inferir_institucion_heuristica_escaner

    assert _inferir_institucion_heuristica_escaner("beneficiario RAPI-CREDIT C.A.") == ""
    assert _inferir_institucion_heuristica_escaner("0105 RAPI-CREDIT") == "Mercantil"


def test_resolve_banco_excel_rechaza_rapicredit():
    from app.services.pagos_gmail.helpers import resolve_banco_para_excel_pagos_gmail

    assert (
        resolve_banco_para_excel_pagos_gmail(
            "A",
            "RAPICREDIT",
            default_a="Mercantil",
            default_b="BNC",
            default_c="BINANCE",
        )
        == "Mercantil"
    )
    assert (
        resolve_banco_para_excel_pagos_gmail(
            "NR",
            "RAPI-CREDIT",
            default_a="Mercantil",
            default_b="BNC",
            default_c="BINANCE",
        )
        == "NR"
    )


def test_inferir_institucion_desde_numero():
    from app.services.pagos_gmail.gemini_service import _inferir_institucion_desde_numero_operacion

    assert _inferir_institucion_desde_numero_operacion("740087408543435") == "Mercantil"
    assert _inferir_institucion_desde_numero_operacion("444102322113560576") == "BINANCE"
    assert _inferir_institucion_desde_numero_operacion("00939") == "Recibo"
    assert _inferir_institucion_desde_numero_operacion("") == ""
