# -*- coding: utf-8 -*-
"""
Resuelve bytes de comprobante en BD para un pago (recibos PDF server-side).

Orden típico cuando `link_comprobante` / `documento_ruta` están vacíos:
1. `pago_comprobante_imagen` vía URL …/comprobante-imagen/{id} (manual / Gmail).
2. Misma URL tras `enriquecer_items_link_comprobante_desde_gmail` (sync_item.drive_link).
3. Misma tabla `pago_comprobante_imagen` vía `pagos_reportados.comprobante_imagen_id` si el pago
   enlaza con un reporte (Infopagos / cobros) y aún no tiene link en columnas del `Pago`.

Todo el binario de comprobantes de pago vive en `pago_comprobante_imagen`.
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


def _comprobante_blob_desde_pago_reportado_vinculado(
    db: "Session",
    pago,
    nombre_pago: Optional[str],
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """Resuelve fila en `pago_comprobante_imagen` a través de `pagos_reportados.comprobante_imagen_id`."""
    from sqlalchemy import or_, select

    from app.core.documento import normalize_documento
    from app.models.pago_reportado import PagoReportado

    nd_raw = (getattr(pago, "numero_documento", None) or "").strip()
    if not nd_raw:
        return None, None, None

    cands: list[str] = []
    nd_norm = (normalize_documento(nd_raw) or "").strip()
    for x in (nd_raw, nd_norm):
        if x and x not in cands:
            cands.append(x)
    if nd_raw.upper().startswith("COB-"):
        suf = nd_raw[4:].strip()
        if suf and suf not in cands:
            cands.append(suf)

    ors = []
    for c in cands:
        ors.append(PagoReportado.numero_operacion == c)
        ors.append(PagoReportado.referencia_interna == c)

    pr = db.execute(
        select(PagoReportado)
        .where(
            PagoReportado.comprobante_imagen_id.isnot(None),
            or_(*ors),
        )
        .order_by(PagoReportado.id.desc())
        .limit(1)
    ).scalars().first()
    if not pr or not pr.comprobante_imagen_id:
        return None, None, None
    cid = str(pr.comprobante_imagen_id).strip().lower()
    if len(cid) != 32:
        return None, None, None
    nm = (getattr(pr, "comprobante_nombre", None) or "").strip() or nombre_pago
    return _blob_primera_coincidencia(db, [cid], nm or nombre_pago)


def comprobante_blob_para_pdf_desde_pago(db: "Session", pago) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Devuelve (bytes, content_type, nombre) para embebido en PDF, o (None, None, None).

    Orden: blob por URL comprobante-imagen en columnas del pago; si no hay y las
    columnas van vacías, Gmail sync; si aún no hay, FK en `pagos_reportados` → misma tabla
    `pago_comprobante_imagen` (histórico sin `link_comprobante` en `pagos`).
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
    if gl:
        ghit = _blob_primera_coincidencia(
            db,
            ids_comprobante_imagen_desde_texto(gl, doc_r),
            nombre,
        )
        if ghit[0] is not None:
            return ghit

    return _comprobante_blob_desde_pago_reportado_vinculado(db, pago, nombre)
