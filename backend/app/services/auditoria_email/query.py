"""
Filtros fuertes Auditoría Email: query Gmail + post-filtro local.
Siempre excluye ya analizados vía ``-label:ANALIZADOS`` (nombre configurable).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import settings

PRESETS = (
    "lote-comprobantes",
    "ultimos-7",
    "ultimos-30",
    "comprobantes-ocr",
    "comprobantes",
    "promesas",
    "reclamos",
    "legal",
    "rebotes",
    "sla",
    "adjuntos-fuertes",
)

ATTACHMENT_MODES = (
    "none",
    "any",
    "receipt_strong",
    "pdf_or_image",
    "pdf_only",
    "image_only",
)

SUBJECT_MODES = ("contains", "exact", "any_word")

_RECEIPT_EXTS = (".pdf", ".jpg", ".jpeg", ".png", ".webp")
_PDF = (".pdf",)
_IMG = (".jpg", ".jpeg", ".png", ".webp")

_PRESET_SUBJECT = {
    "lote-comprobantes": "comprobante OR pago OR transferencia OR captura",
    "comprobantes-ocr": "comprobante OR pago OR transferencia",
    "comprobantes": "comprobante OR pago",
    "promesas": "promesa OR compromet OR pagare OR pagaré",
    "reclamos": "reclamo OR queja OR inconform",
    "legal": "abogado OR demanda OR intimacion OR intimación OR tribunal",
    "rebotes": "undeliverable OR bounced OR \"mailer-daemon\" OR \"delivery status\"",
    "sla": "urgente OR vencid OR atraso",
    "adjuntos-fuertes": "comprobante OR pago OR transferencia",
}


def analizados_label_name() -> str:
    name = (
        getattr(settings, "AUDITORIA_EMAIL_LABEL_ANALIZADOS", None) or "ANALIZADOS"
    ).strip()
    return name or "ANALIZADOS"


def _ymd(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
    return m.group(1) if m else None


def criteria_from_preset(preset: str) -> Dict[str, Any]:
    """
    Criterios frescos al elegir un preset en la UI (reemplaza campos, no setdefault).
    Evita que attachments/newerThan previos pisen el preset.
    """
    p = str(preset or "").strip().lower()
    if p not in PRESETS:
        p = "ultimos-7"
    out: Dict[str, Any] = {"preset": p}
    if p == "ultimos-7":
        out["newerThanDays"] = 7
        out["attachments"] = "pdf_or_image"
    elif p == "ultimos-30":
        out["newerThanDays"] = 30
        out["attachments"] = "pdf_or_image"
    elif p == "lote-comprobantes":
        out["newerThanDays"] = 30
        out["attachments"] = "receipt_strong"
    elif p == "comprobantes-ocr":
        out["attachments"] = "pdf_or_image"
        out["newerThanDays"] = 30
    elif p == "comprobantes":
        out["attachments"] = "any"
        out["newerThanDays"] = 30
    elif p == "adjuntos-fuertes":
        out["attachments"] = "receipt_strong"
        out["attachmentMinKb"] = 40
        out["newerThanDays"] = 30
    elif p == "rebotes":
        out["from"] = "mailer-daemon"
        out["attachments"] = "none"
        out["newerThanDays"] = 30
    elif p in ("promesas", "reclamos", "legal", "sla"):
        out["newerThanDays"] = 30
        out["attachments"] = "any"
    else:
        out["newerThanDays"] = 7
        out["attachments"] = "pdf_or_image"
    subj = _PRESET_SUBJECT.get(p)
    if subj:
        out["subject"] = subj
        out["subjectMode"] = "contains"
    return out


def apply_preset(criteria: Dict[str, Any]) -> Dict[str, Any]:
    c = dict(criteria or {})
    preset = str(c.get("preset") or "").strip().lower()
    if preset not in PRESETS:
        return c
    if preset == "ultimos-7":
        c.setdefault("newerThanDays", 7)
    elif preset == "ultimos-30":
        c.setdefault("newerThanDays", 30)
    elif preset in ("lote-comprobantes", "comprobantes-ocr", "comprobantes", "adjuntos-fuertes"):
        if preset == "comprobantes":
            c.setdefault("attachments", "any")
        elif preset == "comprobantes-ocr":
            c.setdefault("attachments", "pdf_or_image")
        else:
            c.setdefault("attachments", "receipt_strong")
        if preset == "lote-comprobantes":
            c.setdefault("newerThanDays", 30)
        if preset == "adjuntos-fuertes":
            c.setdefault("attachmentMinKb", 40)
    elif preset == "rebotes":
        c.setdefault("from", "mailer-daemon")
    subj = _PRESET_SUBJECT.get(preset)
    if subj and not (c.get("subject") or "").strip():
        c["subject"] = subj
        c.setdefault("subjectMode", "contains")
    # Si hay rango de fechas, newer_than no aplica en Gmail: no lo dejamos colgado.
    if _ymd(c.get("dateFrom")) or _ymd(c.get("dateTo")):
        c.pop("newerThanDays", None)
    return c


def build_gmail_query(criteria: Dict[str, Any]) -> str:
    c = apply_preset(criteria)
    parts: List[str] = ["in:inbox"]
    date_from = _ymd(c.get("dateFrom"))
    date_to = _ymd(c.get("dateTo"))
    if date_from:
        parts.append(f"after:{date_from.replace('-', '/')}")
    if date_to:
        # Gmail before: is exclusive; add one day.
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            parts.append(f"before:{dt.strftime('%Y/%m/%d')}")
        except ValueError:
            parts.append(f"before:{date_to.replace('-', '/')}")
    days = c.get("newerThanDays")
    if days and not date_from and not date_to:
        try:
            n = max(1, min(int(days), 3650))
            parts.append(f"newer_than:{n}d")
        except (TypeError, ValueError):
            pass
    frm = (c.get("from") or "").strip()
    if frm:
        parts.append(f"from:{frm}")
    exf = (c.get("excludeFrom") or "").strip()
    if exf:
        parts.append(f"-from:{exf}")
    subj = (c.get("subject") or "").strip()
    mode = str(c.get("subjectMode") or "contains").strip().lower()
    if subj:
        if mode == "exact":
            parts.append(f'subject:"{subj}"')
        elif mode == "any_word":
            words = [w for w in re.split(r"\s+", subj) if w]
            if words:
                parts.append("(" + " OR ".join(f"subject:{w}" for w in words) + ")")
        else:
            parts.append(f"{{{subj}}}" if " OR " in subj.upper() else f"subject:({subj})")
    sex = (c.get("subjectExclude") or "").strip()
    if sex:
        parts.append(f"-subject:({sex})")
    att = str(c.get("attachments") or "").strip().lower()
    if att == "none":
        parts.append("-has:attachment")
    elif att in ("any", "receipt_strong", "pdf_or_image", "pdf_only", "image_only"):
        parts.append("has:attachment")
        if att == "pdf_only":
            parts.append("filename:pdf")
        elif att == "image_only":
            parts.append("(filename:jpg OR filename:jpeg OR filename:png OR filename:webp)")
        elif att in ("receipt_strong", "pdf_or_image"):
            parts.append(
                "(filename:pdf OR filename:jpg OR filename:jpeg OR filename:png OR filename:webp)"
            )
    fn = (c.get("filenamePattern") or "").strip()
    if fn and att != "none":
        parts.append(f"filename:{fn}")
    # Re-escaneo: no volver a bajar ya etiquetados ANALIZADOS (filtro en Gmail).
    label = analizados_label_name()
    if " " in label:
        parts.append(f'-label:"{label}"')
    else:
        parts.append(f"-label:{label}")
    return " ".join(parts)


def has_date_bound(criteria: Dict[str, Any]) -> bool:
    c = apply_preset(criteria)
    if _ymd(c.get("dateFrom")) or _ymd(c.get("dateTo")):
        return True
    try:
        return int(c.get("newerThanDays") or 0) > 0
    except (TypeError, ValueError):
        return False


def _names_from_row(row: Dict[str, Any]) -> List[str]:
    names = []
    joined = str(row.get("filename_joined") or "")
    if joined:
        names.extend([x.strip().lower() for x in joined.split("|") if x.strip()])
    for t in row.get("attachment_types") or []:
        names.append(str(t).lower())
    return names


def _ext_ok(names: List[str], allowed: tuple) -> bool:
    if not names:
        return False
    for n in names:
        if any(n.endswith(ext) or ext.lstrip(".") in n for ext in allowed):
            return True
    return False


def criteria_needs_payload_inspection(criteria: Dict[str, Any]) -> bool:
    """True si el post-filtro exige tamaño/nombre de archivo no garantizados por la query Gmail."""
    c = apply_preset(criteria)
    if c.get("attachmentMinKb"):
        try:
            if int(c.get("attachmentMinKb") or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    if (c.get("filenamePattern") or "").strip():
        return True
    return False


def matches_criteria(
    row: Dict[str, Any],
    criteria: Dict[str, Any],
    *,
    trust_gmail_attachment_q: bool = True,
) -> bool:
    """
    Post-filtro sobre metadatos.
    Si ``trust_gmail_attachment_q`` y la query Gmail ya acotó adjuntos (has:attachment /
    filename:), no rechaza por falta de filenames en metadata mínima (evita lotes vacíos).
    """
    c = apply_preset(criteria)
    subj = (row.get("subject") or "")
    frm = (row.get("from_email") or "")
    dt: Optional[datetime] = row.get("internal_date")
    date_from = _ymd(c.get("dateFrom"))
    date_to = _ymd(c.get("dateTo"))
    if date_from and dt and dt.strftime("%Y-%m-%d") < date_from:
        return False
    if date_to and dt and dt.strftime("%Y-%m-%d") > date_to:
        return False
    days = c.get("newerThanDays")
    if days and not date_from and not date_to and dt:
        try:
            n = int(days)
            if dt < datetime.utcnow() - timedelta(days=n):
                return False
        except (TypeError, ValueError):
            pass
    want_from = (c.get("from") or "").strip().lower()
    if want_from and want_from not in frm.lower():
        return False
    exf = (c.get("excludeFrom") or "").strip().lower()
    if exf and exf in frm.lower():
        return False
    needle = (c.get("subject") or "").strip()
    mode = str(c.get("subjectMode") or "contains").strip().lower()
    if needle:
        sl = subj.lower()
        if mode == "exact":
            if sl != needle.lower():
                return False
        elif mode == "any_word":
            words = [w.lower() for w in re.split(r"\s+", needle) if w]
            if words and not any(w in sl for w in words):
                return False
        else:
            tokens = [
                t.strip().lower()
                for t in re.split(r"\s+OR\s+", needle, flags=re.I)
                if t.strip()
            ]
            if tokens and not any(t.replace('"', "") in sl for t in tokens):
                return False
    sex = (c.get("subjectExclude") or "").strip().lower()
    if sex and sex in subj.lower():
        return False
    att = str(c.get("attachments") or "").strip().lower()
    has_att = bool(row.get("has_attachment"))
    names = _names_from_row(row)
    if att == "none" and has_att:
        return False
    if att in ("any", "receipt_strong", "pdf_or_image", "pdf_only", "image_only"):
        if names:
            if att == "receipt_strong" and not _ext_ok(names, _RECEIPT_EXTS):
                return False
            if att == "pdf_or_image" and not (
                _ext_ok(names, _PDF) or _ext_ok(names, _IMG)
            ):
                return False
            if att == "pdf_only" and not _ext_ok(names, _PDF):
                return False
            if att == "image_only" and not _ext_ok(names, _IMG):
                return False
        elif not trust_gmail_attachment_q:
            if att == "any" and not has_att:
                return False
            if att != "any":
                return False
    min_kb = c.get("attachmentMinKb")
    if min_kb:
        try:
            want = int(min_kb)
            got = int(row.get("attachment_max_kb") or 0)
            if got > 0 and got < want:
                return False
        except (TypeError, ValueError):
            return False
    fnp = (c.get("filenamePattern") or "").strip().lower()
    if fnp:
        blob = " ".join(names)
        if fnp not in blob and not (trust_gmail_attachment_q and not names):
            return False
    return True
