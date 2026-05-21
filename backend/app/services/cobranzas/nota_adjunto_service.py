"""Adjuntos por nota de cobranza (max 4: PDF, JPG, PNG)."""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cobranza import CobranzaNotaAdjunto

MAX_ADJUNTOS_POR_NOTA = 4
_MAX_BYTES = 10 * 1024 * 1024
_MIME_PERMITIDOS = frozenset(
    {
        "image/jpeg",
        "image/png",
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


def url_nota_adjunto_api(adjunto_id: str) -> str:
    from app.core.config import get_effective_api_public_base_url

    base = get_effective_api_public_base_url()
    path = f"{settings.API_V1_STR}/cobranzas/notas-adjuntos/{adjunto_id}"
    return f"{base}{path}" if base else path


def contar_adjuntos_nota(db: Session, acuerdo_id: int) -> int:
    return (
        db.query(CobranzaNotaAdjunto)
        .filter(CobranzaNotaAdjunto.acuerdo_id == acuerdo_id)
        .count()
    )


def persistir_adjuntos_nota(
    db: Session,
    acuerdo_id: int,
    archivos: List[Tuple[bytes, Optional[str], Optional[str]]],
    *,
    user_id: Optional[int] = None,
) -> List[Tuple[str, str, str]]:
    """
    archivos: lista de (content, content_type, filename).
    Devuelve [(id, url, content_type), ...]
    """
    if len(archivos) > MAX_ADJUNTOS_POR_NOTA:
        raise HTTPException(
            status_code=400,
            detail=f"Maximo {MAX_ADJUNTOS_POR_NOTA} archivos por nota.",
        )
    existentes = contar_adjuntos_nota(db, acuerdo_id)
    if existentes + len(archivos) > MAX_ADJUNTOS_POR_NOTA:
        raise HTTPException(
            status_code=400,
            detail=f"Maximo {MAX_ADJUNTOS_POR_NOTA} archivos por nota.",
        )
    out: List[Tuple[str, str, str]] = []
    for content, mime_type, nombre in archivos:
        if len(content) > _MAX_BYTES:
            raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 10 MB).")
        ct = _normalizar_mime(mime_type)
        if ct not in _MIME_PERMITIDOS:
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten PDF, JPG y PNG.",
            )
        adj_id = uuid.uuid4().hex
        row = CobranzaNotaAdjunto(
            id=adj_id,
            acuerdo_id=acuerdo_id,
            nombre_archivo=(nombre or "").strip()[:255] or None,
            content_type=ct,
            archivo_data=content,
            user_id=user_id,
        )
        db.add(row)
        out.append((adj_id, url_nota_adjunto_api(adj_id), ct))
    db.flush()
    return out


async def leer_uploads_nota(
    files: List[UploadFile],
) -> List[Tuple[bytes, Optional[str], Optional[str]]]:
    if len(files) > MAX_ADJUNTOS_POR_NOTA:
        raise HTTPException(
            status_code=400,
            detail=f"Maximo {MAX_ADJUNTOS_POR_NOTA} archivos por nota.",
        )
    out: List[Tuple[bytes, Optional[str], Optional[str]]] = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        if not content:
            continue
        out.append((content, f.content_type, f.filename))
    return out


def leer_adjunto_nota(
    db: Session, adjunto_id: str
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    row = db.get(CobranzaNotaAdjunto, adjunto_id)
    if row is None or not row.archivo_data:
        return None, None, None
    body = bytes(row.archivo_data)
    ct = (row.content_type or "application/octet-stream").split(";")[0].strip()
    nombre = row.nombre_archivo
    return body, ct, nombre
