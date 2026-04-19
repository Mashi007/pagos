# -*- coding: utf-8 -*-
"""
Resuelve bytes de comprobante guardados en BD (tabla pago_comprobante_imagen)
a partir de pagos.link_comprobante / documento_ruta (rutas con .../comprobante-imagen/{id}).
Usado por recibo PDF de cartera y otros consumidores server-side.
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


def comprobante_blob_para_pdf_desde_pago(db: "Session", pago) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Devuelve (bytes, content_type, nombre) para embebido en PDF, o (None, None, None).
    Prioriza el primer ID encontrado en link_comprobante y documento_ruta.
    """
    from app.models.pago_comprobante_imagen import PagoComprobanteImagen

    link = (getattr(pago, "link_comprobante", None) or "").strip()
    doc_r = (getattr(pago, "documento_ruta", None) or "").strip()
    nombre = (getattr(pago, "documento_nombre", None) or "").strip() or None
    for cid in ids_comprobante_imagen_desde_texto(link, doc_r):
        row = db.get(PagoComprobanteImagen, cid)
        if row is None or not row.imagen_data:
            continue
        body = bytes(row.imagen_data)
        if len(body) < 12:
            continue
        ct = (row.content_type or "").strip() or None
        return body, ct, nombre
    return None, None, None
