"""Pipeline Gmail: adjuntos Word (.docx) con foto del recibo embebida."""
from __future__ import annotations

import io
import zipfile

MAGIC_JPEG = bytes([0xFF, 0xD8, 0xFF]) + b"\x00" * 200


def _docx_con_imagen(path: str = "word/media/recibo.jpeg", data: bytes = MAGIC_JPEG) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?>')
        zf.writestr("word/document.xml", '<?xml version="1.0"?>')
        zf.writestr(path, data)
    return buf.getvalue()


def test_helpers_docx_es_candidato_vision():
    from app.services.pagos_gmail.helpers import (
        is_allowed_attachment,
        is_vision_attachment_candidate,
        is_word_docx_attachment,
    )

    assert is_allowed_attachment("recibo pago 1 de 3.docx")
    assert is_word_docx_attachment(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "recibo.docx",
    )
    assert is_vision_attachment_candidate(
        "application/octet-stream",
        "recibo pago 1 de 3.docx",
    )
    assert is_word_docx_attachment("application/msword", "recibo.doc")
    assert is_vision_attachment_candidate("application/msword", "cuota.doc")
    assert is_vision_attachment_candidate("image/heic", "IMG_1234.HEIC")
    assert is_vision_attachment_candidate("image/heif", "")
    assert is_vision_attachment_candidate("image/jpeg", "")
    assert is_vision_attachment_candidate("image/png", "image.png")
    assert not is_vision_attachment_candidate("image/svg+xml", "logo.svg")
    assert not is_vision_attachment_candidate("text/plain", "nota.txt")


def test_clasificar_y_normalizar_foto_iphone_y_pdf():
    from app.services.pagos_gmail.helpers import (
        clasificar_binario_comprobante,
        normalizar_candidato_descargado,
    )

    jpeg = b"\xff\xd8\xff" + b"\x00" * 20
    assert clasificar_binario_comprobante(jpeg) == ("image/jpeg", "jpg")
    heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8
    assert clasificar_binario_comprobante(heic) == ("image/heic", "heic")
    pdf = b"%PDF-1.4\n"
    assert clasificar_binario_comprobante(pdf) == ("application/pdf", "pdf")

    unnamed_jpeg = normalizar_candidato_descargado("", jpeg, "application/octet-stream")
    assert unnamed_jpeg is not None
    assert unnamed_jpeg[0] == "inline_body.jpg"
    assert unnamed_jpeg[2] == "image/jpeg"

    unnamed_heic = normalizar_candidato_descargado("", heic, "application/octet-stream")
    assert unnamed_heic is not None
    assert unnamed_heic[2] == "image/heic"

    junk = normalizar_candidato_descargado("", b"not-a-photo!!", "application/octet-stream")
    assert junk is None


def test_expand_word_docx_a_imagen_para_gemini():
    from app.services.pagos_gmail.gmail_service import _expand_word_docx_pipeline_candidates

    docx = _docx_con_imagen()
    rows = [
        (
            "recibo pago 1 de 3.docx",
            docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "adjunta",
        )
    ]
    out = _expand_word_docx_pipeline_candidates(rows)
    assert len(out) == 1
    fn, raw, mime, origen = out[0]
    assert raw == MAGIC_JPEG
    assert mime == "image/jpeg"
    assert origen == "adjunta_docx"
    assert "recibo pago 1 de 3" in fn


def test_expand_word_sin_imagen_omite_candidato():
    from app.services.pagos_gmail.gmail_service import _expand_word_docx_pipeline_candidates

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", '<?xml version="1.0"?>')
    docx_vacio = buf.getvalue()
    rows = [
        (
            "sin_foto.docx",
            docx_vacio,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "adjunta",
        )
    ]
    assert _expand_word_docx_pipeline_candidates(rows) == []
