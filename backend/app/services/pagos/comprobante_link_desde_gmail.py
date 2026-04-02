# -*- coding: utf-8 -*-
"""
Resuelve URL de comprobante (Drive) desde pagos_gmail_sync_item cuando pagos.link_comprobante es NULL.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pagos_gmail_sync import PagosGmailSyncItem


def drive_raw_a_url(dlink: Any) -> str:
    s = (str(dlink) if dlink is not None else "").strip()
    if not s:
        return ""
    if not s.lower().startswith(("http://", "https://")):
        return "https://drive.google.com/file/d/" + s + "/view"
    return s


def enriquecer_items_link_comprobante_desde_gmail(db: Session, items: list) -> None:
    """
    Si un item no tiene link_comprobante ni documento_ruta, busca drive_link en
    pagos_gmail_sync_item por numero_referencia (mismo criterio que Excel Gmail).
    """
    if not items:
        return

    need: list[tuple[Any, str]] = []
    raw_strings: list[str] = []
    seen_raw: set[str] = set()

    for it in items:
        if (it.get("link_comprobante") or "").strip() or (
            it.get("documento_ruta") or ""
        ).strip():
            continue
        doc = (it.get("numero_documento") or "").strip()
        if not doc:
            continue
        nd = normalize_documento(doc)
        if not nd:
            continue
        need.append((it, nd))
        if doc not in seen_raw:
            seen_raw.add(doc)
            raw_strings.append(doc)

    if not need:
        return

    by_norm: dict[str, str] = {}

    if raw_strings:
        rows = db.execute(
            select(PagosGmailSyncItem.numero_referencia, PagosGmailSyncItem.drive_link)
            .where(
                PagosGmailSyncItem.numero_referencia.in_(raw_strings),
                PagosGmailSyncItem.drive_link.isnot(None),
                PagosGmailSyncItem.drive_link != "",
            )
            .order_by(PagosGmailSyncItem.id.desc())
        ).all()
        for ref, dlink in rows:
            n = normalize_documento(ref or "")
            url = drive_raw_a_url(dlink)
            if n and url and n not in by_norm:
                by_norm[n] = url

    missing_norms = {nd for _, nd in need if nd not in by_norm}
    if missing_norms:
        rows2 = db.execute(
            select(PagosGmailSyncItem.numero_referencia, PagosGmailSyncItem.drive_link)
            .where(
                PagosGmailSyncItem.drive_link.isnot(None),
                PagosGmailSyncItem.drive_link != "",
            )
            .order_by(PagosGmailSyncItem.id.desc())
            .limit(15000)
        ).all()
        for ref, dlink in rows2:
            n = normalize_documento(ref or "")
            if not n or n not in missing_norms or n in by_norm:
                continue
            url = drive_raw_a_url(dlink)
            if url:
                by_norm[n] = url

    for it, nd in need:
        url = by_norm.get(nd)
        if url:
            it["link_comprobante"] = url
