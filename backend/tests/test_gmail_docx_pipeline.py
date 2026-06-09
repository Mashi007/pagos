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
