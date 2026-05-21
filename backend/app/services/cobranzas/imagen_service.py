"""Imagenes de evidencia por caso de cobranza (max 10)."""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cobranza import CobranzaCaso, CobranzaImagen

logger = logging.getLogger(__name__)

MAX_IMAGENES_POR_CASO = 10
_MAX_BYTES = 10 * 1024 * 1024
_MIME_PERMITIDOS = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
        "application/pdf",
    }
)


def _normalizar_mime(mime: Optional[str]) -> str:
    if not mime:
        return ""
    s = mime.split(";")[0].strip().lower()
    if s == "image/jpg":
        return "image/jpeg"
    return s


def url_cobranza_imagen_api(imagen_id: str) -> str:
    from app.core.config import get_effective_api_public_base_url

    base = get_effective_api_public_base_url()
    path = f"{settings.API_V1_STR}/cobranzas/imagenes/{imagen_id}"
    return f"{base}{path}" if base else path


def contar_imagenes_caso(db: Session, caso_id: int) -> int:
    return (
        db.query(CobranzaImagen)
        .filter(CobranzaImagen.caso_id == caso_id)
        .count()
    )


def persistir_imagen_cobranza(
    db: Session,
    caso: CobranzaCaso,
    content: bytes,
    mime_type: Optional[str],
    *,
    descripcion: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Tuple[str, str]:
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 10 MB).")
    ct = _normalizar_mime(mime_type)
    if ct not in _MIME_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Use JPEG, PNG, WebP o PDF.",
        )
    n = contar_imagenes_caso(db, caso.id)
    if n >= MAX_IMAGENES_POR_CASO:
        raise HTTPException(
            status_code=400,
            detail=f"Maximo {MAX_IMAGENES_POR_CASO} imagenes por caso.",
        )
    img_id = uuid.uuid4().hex
    row = CobranzaImagen(
        id=img_id,
        caso_id=caso.id,
        content_type=ct,
        imagen_data=content,
        descripcion=(descripcion or "").strip()[:255] or None,
        user_id=user_id,
    )
    db.add(row)
    db.flush()
    return img_id, url_cobranza_imagen_api(img_id)


def leer_imagen_cobranza(
    db: Session, imagen_id: str
) -> Tuple[Optional[bytes], Optional[str]]:
    row = db.get(CobranzaImagen, imagen_id)
    if row is None or not row.imagen_data:
        return None, None
    body = bytes(row.imagen_data)
    if len(body) < 12:
        return None, None
    ct = (row.content_type or "application/octet-stream").split(";")[0].strip()
    return body, ct
