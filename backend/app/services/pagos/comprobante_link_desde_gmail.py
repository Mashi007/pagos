# -*- coding: utf-8 -*-
"""
Resuelve URL de comprobante (Drive) desde pagos_gmail_sync_item cuando pagos.link_comprobante es NULL.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pagos_gmail_sync import PagosGmailSyncItem
from app.services.pagos_gmail.helpers import normalizar_referencia


def drive_raw_a_url(dlink: Any) -> str:
    s = (str(dlink) if dlink is not None else "").strip()
    if not s:
        return ""
    if not s.lower().startswith(("http://", "https://")):
        return "https://drive.google.com/file/d/" + s + "/view"
    return s


def comprobante_url_para_enlace_publico(
    value: Optional[str],
    *,
    base_url: str = "",
) -> str:
    """
    URL usable en PDF/HTML (estado de cuenta «Pagos realizados»): ya http(s),
    ruta absoluta con base_url, o ID de archivo Google Drive (no numeros puros).
    """
    s = (str(value) if value is not None else "").strip()
    if not s:
        return ""
    low = s.lower()
    if low.startswith(("http://", "https://")):
        return s
    bu = (base_url or "").strip()
    if s.startswith("/") and bu:
        return bu.rstrip("/") + s
    # Gmail/Drive a veces persisten solo el file id (letras, digitos, -, _)
    if (
        len(s) >= 20
        and not s.isdigit()
        and "/" not in s
        and "\\" not in s
        and re.match(r"^[a-zA-Z0-9_-]+$", s)
    ):
        return drive_raw_a_url(s)
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
            url = drive_raw_a_url(dlink)
            if not url:
                continue
            ref_s = ref or ""
            n = normalize_documento(ref_s)
            if n and n not in by_norm:
                by_norm[n] = url
            # Pipeline guarda referencia con ceros recortados (solo digitos); Excel puede traer ceros a la izquierda.
            n2 = normalize_documento(normalizar_referencia(ref_s))
            if n2 and n2 not in by_norm:
                by_norm[n2] = url

    missing_norms: set[str] = set()
    for it, nd in need:
        if nd in by_norm:
            continue
        missing_norms.add(nd)
        doc_raw = (it.get("numero_documento") or "").strip()
        if doc_raw:
            na = normalize_documento(normalizar_referencia(doc_raw))
            if na:
                missing_norms.add(na)
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
            url = drive_raw_a_url(dlink)
            if not url:
                continue
            ref_s = ref or ""
            n = normalize_documento(ref_s)
            if n and n in missing_norms and n not in by_norm:
                by_norm[n] = url
            n2 = normalize_documento(normalizar_referencia(ref_s))
            if n2 and n2 in missing_norms and n2 not in by_norm:
                by_norm[n2] = url

    for it, nd in need:
        doc_raw = (it.get("numero_documento") or "").strip()
        nd_alt = normalize_documento(normalizar_referencia(doc_raw)) if doc_raw else None
        url = by_norm.get(nd) or (by_norm.get(nd_alt) if nd_alt else None)
        if url:
            it["link_comprobante"] = url
