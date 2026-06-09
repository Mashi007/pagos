"""
Extrae imágenes embebidas de comprobantes en Word (.docx) para OCR/Gemini.

Un .docx es un ZIP con imágenes en word/media/. Se elige la más grande (típico: foto del recibo).
"""
from __future__ import annotations

import io
import os
import zipfile
from typing import Optional, Tuple

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOC_MIME = "application/msword"

_MEDIA_IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"})
_EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def es_mime_word(content_type: str, filename: str = "") -> bool:
    base = (content_type or "").split(";")[0].strip().lower()
    if base in (_DOCX_MIME, _DOC_MIME):
        return True
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    return ext in (".docx", ".doc")


def es_docx_bytes(content: bytes) -> bool:
    """True si el binario parece un .docx (ZIP con word/)."""
    if len(content) < 4 or content[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return any(n.startswith("word/") for n in zf.namelist())
    except zipfile.BadZipFile:
        return False


def es_doc_ole_bytes(content: bytes) -> bool:
    """Word 97-2003 (.doc) binario OLE — no soportado para extracción automática."""
    return len(content) >= 8 and content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def extraer_imagen_comprobante_desde_docx(content: bytes) -> Tuple[bytes, str, str]:
    """
    Devuelve (bytes_imagen, nombre_archivo, mime_imagen) de la imagen embebida más grande.
    """
    if es_doc_ole_bytes(content):
        raise ValueError(
            "El archivo .doc antiguo no es compatible. Guarde como .docx, PDF o imagen (JPG/PNG)."
        )
    if not es_docx_bytes(content):
        raise ValueError("El archivo Word no es un .docx válido.")

    candidatos: list[tuple[int, str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            norm = name.replace("\\", "/")
            if not norm.startswith("word/media/"):
                continue
            ext = os.path.splitext(norm)[1].lower()
            if ext not in _MEDIA_IMAGE_EXT:
                continue
            raw = zf.read(name)
            if len(raw) >= 100:
                candidatos.append((len(raw), ext, raw))

    if not candidatos:
        raise ValueError(
            "No se encontró ninguna imagen del comprobante dentro del Word. "
            "Pegue la foto del recibo en el documento o suba JPG, PNG o PDF."
        )

    candidatos.sort(key=lambda t: t[0], reverse=True)
    _size, ext, raw = candidatos[0]
    mime = _EXT_TO_MIME.get(ext, "image/jpeg")
    base = f"comprobante_desde_word{ext}"
    return raw, base, mime


def inferir_mime_docx_desde_extension(filename_raw: str) -> Optional[str]:
    ext = (os.path.splitext(filename_raw or "")[1] or "").lower()
    if ext == ".docx":
        return _DOCX_MIME
    if ext == ".doc":
        return _DOC_MIME
    return None
