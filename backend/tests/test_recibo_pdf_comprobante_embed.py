"""Comprobante en recibo PDF: PDF rasterizado a imagen (página 1)."""
import io

import pytest

pytest.importorskip("fitz")

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    from app.services.cobros.recibo_pdf import (
        _bytes_pdf_desde_buffer,
        rasterizar_pdf_comprobante_primera_pagina_png,
    )
except ModuleNotFoundError as exc:  # p. ej. stack mínimo sin reportlab/psycopg2
    pytest.skip(str(exc), allow_module_level=True)


def _pdf_una_pagina_con_texto() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 14)
    c.drawString(72, 720, "Comprobante de prueba RapiCredit")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_rasterizar_pdf_primera_pagina_produce_png():
    pdf_b = _pdf_una_pagina_con_texto()
    png = rasterizar_pdf_comprobante_primera_pagina_png(pdf_b)
    assert png is not None
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_rasterizar_rechaza_no_pdf():
    assert rasterizar_pdf_comprobante_primera_pagina_png(b"not a pdf") is None
    assert rasterizar_pdf_comprobante_primera_pagina_png(b"") is None


def test_bytes_pdf_desde_buffer_bom_y_prefijo():
    core = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    assert _bytes_pdf_desde_buffer(b"\xef\xbb\xbf" + core) == core
    assert _bytes_pdf_desde_buffer(b"PREFIX\n" + core) == core


def test_rasterizar_pdf_con_prefijo_antes_de_cabecera():
    pdf_b = _pdf_una_pagina_con_texto()
    wrapped = b"<!--meta-->\n" + pdf_b
    png = rasterizar_pdf_comprobante_primera_pagina_png(wrapped)
    assert png is not None
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
