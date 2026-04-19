# -*- coding: utf-8 -*-
"""
Resuelve URL de comprobante desde pagos_gmail_sync_item cuando pagos.link_comprobante es NULL.

La columna drive_link puede ser enlace de Google Drive o URL del API (/pagos/comprobante-imagen/…)
cuando el comprobante se guardó en BD (pipeline Gmail).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago_reportado import PagoReportado
from app.models.pagos_gmail_sync import PagosGmailSyncItem
from app.services.cobros.pago_reportado_documento import claves_documento_pago_para_reportado
from app.services.pagos_gmail.helpers import normalizar_referencia


def drive_raw_a_url(dlink: Any) -> str:
    s = (str(dlink) if dlink is not None else "").strip()
    if not s:
        return ""
    low = s.lower()
    if low.startswith(("http://", "https://")):
        return s
    # drive_link a veces guarda la ruta del comprobante en API, no un id de archivo Drive.
    if "comprobante-imagen" in low or low.startswith("/api/") or low.startswith("api/"):
        return s
    return "https://drive.google.com/file/d/" + s + "/view"


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


def enriquecer_items_link_comprobante_desde_pago_reportado(db: Session, items: list) -> None:
    """
    Si `link_comprobante` y `documento_ruta` siguen vacíos, resuelve URL desde `pagos_reportados`
    vinculado por Nº documento: `comprobante_imagen_id` → …/pagos/comprobante-imagen/{id},
    o `ruta_comprobante` cuando ya es http(s).
    """
    from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta

    if not items:
        return

    cands: set[str] = set()
    for it in items:
        if (it.get("link_comprobante") or "").strip() or (it.get("documento_ruta") or "").strip():
            continue
        d = (it.get("numero_documento") or "").strip()
        if not d:
            continue
        cands.add(d)
        nd0 = normalize_documento(d)
        if nd0:
            cands.add(nd0)
    if not cands:
        return
    cands_list = sorted(cands)
    _max_c = 500
    if len(cands_list) > _max_c:
        cands_list = cands_list[:_max_c]

    rows = db.execute(
        select(PagoReportado)
        .where(
            or_(
                PagoReportado.numero_operacion.in_(cands_list),
                PagoReportado.referencia_interna.in_(cands_list),
            )
        )
        .order_by(PagoReportado.id.desc())
    ).scalars().all()

    best: dict[str, tuple[str, Optional[str]]] = {}

    def _url_desde_pr(pr: PagoReportado) -> str:
        img_id = (getattr(pr, "comprobante_imagen_id", None) or "").strip()
        if img_id and len(img_id) == 32:
            return url_comprobante_imagen_absoluta(img_id)
        ruta = (getattr(pr, "ruta_comprobante", None) or "").strip()
        low = ruta.lower()
        if ruta and low.startswith(("http://", "https://")):
            return ruta
        return ""

    for pr in rows:
        u = _url_desde_pr(pr)
        if not u:
            continue
        nm = (getattr(pr, "comprobante_nombre", None) or "").strip() or None
        for k in claves_documento_pago_para_reportado(pr):
            nk = normalize_documento(k) or k
            for variant in (k, nk):
                if variant and variant not in best:
                    best[variant] = (u, nm)

    def _buscar_url(it: dict) -> tuple[str, Optional[str]]:
        doc = (it.get("numero_documento") or "").strip()
        if not doc:
            return "", None
        cands_try = [doc, normalize_documento(doc) or doc]
        if doc.upper().startswith("COB-"):
            suf = doc[4:].strip()
            if suf:
                cands_try.append(suf)
                cands_try.append(normalize_documento(suf) or suf)
        seen: set[str] = set()
        for k in cands_try:
            if not k or k in seen:
                continue
            seen.add(k)
            hit = best.get(k)
            if hit:
                return hit
        return "", None

    for it in items:
        if (it.get("link_comprobante") or "").strip() or (it.get("documento_ruta") or "").strip():
            continue
        url, nm = _buscar_url(it)
        if url:
            it["link_comprobante"] = url
            if nm and not (it.get("documento_nombre") or "").strip():
                it["documento_nombre"] = nm
