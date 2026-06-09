"""Tests plantilla Recibo (formato G) — escáner y Excel Gmail."""


def test_canonical_institucion_recibo():
    from app.services.pagos_gmail.gemini_service import _canonical_institucion_escaner

    assert _canonical_institucion_escaner("Recibo") == "Recibo"
    assert _canonical_institucion_escaner("RECIBO") == "Recibo"
    assert _canonical_institucion_escaner("Recibos") == "Recibo"


def test_inferir_institucion_recibo_toro():
    from app.services.pagos_gmail.gemini_service import _inferir_institucion_heuristica_escaner

    assert _inferir_institucion_heuristica_escaner("plantilla G Recibo TORO MOTORCYCLES") == "Recibo"


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
