# -*- coding: utf-8 -*-
"""Cola de aprobación Auditoría Email / filtros."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auditoria_email.query import (
    apply_preset,
    build_gmail_query,
    criteria_from_preset,
)
from app.services.pagos_gmail.anti_limbo_post_lote import _fmt_desde_banco


def test_comprobantes_ocr_preset_attachments():
    c = apply_preset({"preset": "comprobantes-ocr"})
    assert c.get("attachments") == "pdf_or_image"


def test_criteria_from_preset_replaces_not_setdefault():
    c = criteria_from_preset("lote-comprobantes")
    assert c["attachments"] == "receipt_strong"
    assert c["newerThanDays"] == 30
    assert "comprobante" in (c.get("subject") or "")
    c2 = criteria_from_preset("comprobantes-ocr")
    assert c2["attachments"] == "pdf_or_image"


def test_lote_comprobantes_receipt_strong_when_empty():
    c = apply_preset({"preset": "lote-comprobantes"})
    assert c.get("attachments") == "receipt_strong"
    assert c.get("newerThanDays") == 30


def test_apply_preset_clears_newer_when_dates():
    c = apply_preset(
        {"preset": "ultimos-7", "newerThanDays": 7, "dateFrom": "2026-01-01"}
    )
    assert "newerThanDays" not in c or c.get("newerThanDays") is None


def test_pdf_or_image_query_includes_webp():
    q = build_gmail_query({"attachments": "pdf_or_image", "newerThanDays": 7})
    assert "filename:webp" in q


def test_ef_banco_sin_auto_alta():
    assert _fmt_desde_banco("BANCAMIGA") is None
    assert _fmt_desde_banco("MERCANTIL") == "A"
