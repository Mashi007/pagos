# -*- coding: utf-8 -*-
"""Lectura del comprobante de `pagos_reportados` vía tabla única `pago_comprobante_imagen`."""
from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.pago_comprobante_imagen import PagoComprobanteImagen
from app.models.pago_reportado import PagoReportado


def comprobante_bytes_y_content_type_desde_reportado(
    db: Session, pr: PagoReportado
) -> Tuple[Optional[bytes], Optional[str]]:
    iid = (getattr(pr, "comprobante_imagen_id", None) or "").strip()
    if not iid:
        return None, None
    row = db.get(PagoComprobanteImagen, iid)
    if row is None or not row.imagen_data:
        return None, None
    body = bytes(row.imagen_data)
    if len(body) < 12:
        return None, None
    ct = (row.content_type or "application/octet-stream").split(";")[0].strip()
    return body, ct


def nombre_adjunto_email_desde_reportado(
    pr: PagoReportado, content_type: Optional[str]
) -> str:
    nombre_adj = (getattr(pr, "comprobante_nombre", None) or "comprobante").strip() or "comprobante"
    if not nombre_adj or "." not in nombre_adj:
        ext = "pdf" if (content_type or "").lower().find("pdf") >= 0 else "jpg"
        ref = (getattr(pr, "referencia_interna", None) or "comprobante").strip() or "comprobante"
        nombre_adj = f"comprobante_{ref}.{ext}"
    return nombre_adj
