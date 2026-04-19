# -*- coding: utf-8 -*-
"""
Resuelve bytes de comprobante en BD (pago_comprobante_imagen) para un pago.

Misma regla que listas/API (`enriquecer_items_link_comprobante_desde_gmail`): si
`link_comprobante` y `documento_ruta` vienen vacíos, se intenta la URL en
`pagos_gmail_sync_item.drive_link` por `numero_documento`, que puede ser ruta
`/pagos/comprobante-imagen/{id}` guardada por el pipeline Gmail.

Punto único server-side para embebido en PDF (recibos cartera/cuota, etc.).
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_COMPROBANTE_IMAGEN_RE = re.compile(
    r"comprobante-imagen[/\\]+([0-9a-fA-F]{32})\b",
    re.IGNORECASE,
)


def _normalizar_id_comprobante_32(raw: str) -> Optional[str]:
    s = (raw or "").strip().lower()
    if not s:
        return None
    s = s.split(".")[0].replace("-", "")
    if len(s) == 32 and all(c in "0123456789abcdef" for c in s):
        return s
    return None


def ids_comprobante_imagen_desde_texto(*textos: Optional[str]) -> list[str]:
    """Extrae IDs (32 hex) de enlaces tipo .../comprobante-imagen/{id}."""
    out: list[str] = []
    seen: set[str] = set()
    for t in textos:
        s = (t or "").strip()
        if not s:
            continue
        for m in _COMPROBANTE_IMAGEN_RE.finditer(s):
            cid = _normalizar_id_comprobante_32(m.group(1))
            if cid and cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def _blob_primera_coincidencia(
    db: "Session",
    cids: list[str],
    nombre: Optional[str],
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    from app.models.pago_comprobante_imagen import PagoComprobanteImagen

    for cid in cids:
        row = db.get(PagoComprobanteImagen, cid)
        if row is None or not row.imagen_data:
            continue
        body = bytes(row.imagen_data)
        if len(body) < 12:
            continue
        ct = (row.content_type or "").strip() or None
        return body, ct, nombre
    return None, None, None


def comprobante_blob_para_pdf_desde_pago(db: "Session", pago) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Devuelve (bytes, content_type, nombre) para embebido en PDF, o (None, None, None).

    Orden: IDs en columnas del pago; si no hay coincidencia y ambas columnas de
    enlace/ruta están vacías, mismo backfill Gmail que el API de pagos/estado de cuenta.
    """
    link = (getattr(pago, "link_comprobante", None) or "").strip()
    doc_r = (getattr(pago, "documento_ruta", None) or "").strip()
    nombre = (getattr(pago, "documento_nombre", None) or "").strip() or None

    hit = _blob_primera_coincidencia(db, ids_comprobante_imagen_desde_texto(link, doc_r), nombre)
    if hit[0] is not None:
        return hit

    if link or doc_r:
        return None, None, None

    nd = (getattr(pago, "numero_documento", None) or "").strip()
    if not nd:
        return None, None, None

    from app.services.pagos.comprobante_link_desde_gmail import (
        enriquecer_items_link_comprobante_desde_gmail,
    )

    pseudo: dict = {
        "link_comprobante": "",
        "documento_ruta": "",
        "numero_documento": nd,
    }
    enriquecer_items_link_comprobante_desde_gmail(db, [pseudo])
    gl = (pseudo.get("link_comprobante") or "").strip()
    if not gl:
        return None, None, None
    return _blob_primera_coincidencia(
        db,
        ids_comprobante_imagen_desde_texto(gl, doc_r),
        nombre,
    )
