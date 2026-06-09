"""Tests extracción de imagen embebida en Word (.docx) para escaneo de comprobantes."""
from __future__ import annotations

import io
import zipfile

import pytest

MAGIC_JPEG = bytes([0xFF, 0xD8, 0xFF]) + b"\x00" * 200
MAGIC_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 200


def _docx_con_imagenes(*items: tuple[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        )
        for path, data in items:
            zf.writestr(path, data)
    return buf.getvalue()


def test_extraer_imagen_elige_la_mas_grande():
    from app.services.cobros.comprobante_docx import extraer_imagen_comprobante_desde_docx

    docx = _docx_con_imagenes(
        ("word/media/icon.png", MAGIC_PNG[:120]),
        ("word/media/recibo.jpeg", MAGIC_JPEG),
    )
    raw, fn, mime = extraer_imagen_comprobante_desde_docx(docx)
    assert raw == MAGIC_JPEG
    assert mime == "image/jpeg"
    assert fn.endswith(".jpeg")


def test_docx_sin_imagen_falla():
    from app.services.cobros.comprobante_docx import extraer_imagen_comprobante_desde_docx

    docx = _docx_con_imagenes()
    with pytest.raises(ValueError, match="No se encontró ninguna imagen"):
        extraer_imagen_comprobante_desde_docx(docx)


def test_preparar_adjunto_convierte_docx_a_imagen():
    from app.services.cobros.cobros_publico_reporte_service import (
        preparar_adjunto_comprobante_para_vision,
    )

    docx = _docx_con_imagenes(("word/media/image1.jpeg", MAGIC_JPEG))
    err, content, filename, ctype = preparar_adjunto_comprobante_para_vision(
        docx,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "recibo pago 1 de 3.docx",
        mensaje_excel_largo=False,
    )
    assert err is None
    assert content == MAGIC_JPEG
    assert ctype == "image/jpeg"
    assert "docx" not in filename.lower() or "desde_word" in filename


def test_doc_antiguo_rechazado_en_extraccion():
    from app.services.cobros.comprobante_docx import extraer_imagen_comprobante_desde_docx

    ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512
    with pytest.raises(ValueError, match=".doc antiguo"):
        extraer_imagen_comprobante_desde_docx(ole)
