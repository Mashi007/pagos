# -*- coding: utf-8 -*-
"""Convierte HEIC/HEIF (iPhone) a JPEG para vista previa en navegadores sin soporte nativo."""
from __future__ import annotations

import io
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

_HEIF_INIT_DONE = False


def _ensure_pillow_heif_opener() -> None:
    global _HEIF_INIT_DONE
    if _HEIF_INIT_DONE:
        return
    _HEIF_INIT_DONE = True
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception as exc:
        logger.debug("pillow-heif no disponible para vista web: %s", exc)


def _pil_a_jpeg_bytes(img) -> bytes:
    from PIL import Image

    if img.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        capa = img.convert("RGBA") if img.mode == "P" else img
        fondo.paste(capa, mask=capa.split()[-1])
        img = fondo
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def comprobante_bytes_para_vista_navegador(
    content: bytes,
    content_type: str = "",
    filename: str = "",
) -> Tuple[bytes, str]:
    """
    Devuelve bytes aptos para ``<img>`` en Chrome/Windows.
    HEIC/HEIF → JPEG; el resto sin cambios.
    """
    from app.services.cobros.cobros_publico_reporte_service import (
        _magic_heic_o_heif,
        mime_efectivo_con_firma_archivo,
    )

    ct = mime_efectivo_con_firma_archivo(
        content,
        content_type or "",
        filename or "comprobante",
    )
    ct_low = (ct or "").lower()
    head = content[:48] if len(content) >= 48 else content
    es_heic = ct_low in ("image/heic", "image/heif") or _magic_heic_o_heif(head)
    if not es_heic:
        return content, ct or "application/octet-stream"

    _ensure_pillow_heif_opener()
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(content))
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        return _pil_a_jpeg_bytes(img), "image/jpeg"
    except Exception as exc:
        logger.warning(
            "comprobante vista web: no se pudo convertir HEIC/HEIF (%s): %s",
            filename or "comprobante",
            exc,
        )
        return content, ct or "image/heic"
