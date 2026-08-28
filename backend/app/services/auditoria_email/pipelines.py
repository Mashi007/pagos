"""Pipelines de cobranza / auditoría sobre mensajes ya ingeridos."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_RE_CEDULA = re.compile(r"\b([VEJPvejp]?\d{6,10})\b")
_RE_MONTO = re.compile(
    r"(?:usd|\$|bs\.?|bolivares?)\s*[:#]?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
    re.I,
)

PIPELINE_CATALOG = [
    {"id": "cobranza.classify", "nombre": "Clasificar cobranza", "fase": "ingesta"},
    {"id": "cobranza.extract", "nombre": "Extraer cédula/monto", "fase": "ingesta"},
    {"id": "cobranza.extract_receipts", "nombre": "Detectar recibos", "fase": "ingesta"},
    {"id": "cobranza.ocr", "nombre": "OCR heurístico (demo)", "fase": "ingesta"},
    {"id": "revision.route", "nombre": "Enrutar revisión", "fase": "ruta"},
    {"id": "auditoria.sla", "nombre": "SLA de respuesta", "fase": "auditoria"},
    {"id": "auditoria.evidencia", "nombre": "Nivel de evidencia", "fase": "auditoria"},
    {"id": "auditoria.riesgo", "nombre": "Riesgo operativo", "fase": "auditoria"},
]

DEFAULT_PIPELINE_IDS = [p["id"] for p in PIPELINE_CATALOG]


def classify_subject(subject: str, snippet: str = "") -> str:
    text = f"{subject} {snippet}".lower()
    rules = (
        ("rebote", ("undeliverable", "mailer-daemon", "delivery status", "bounced")),
        ("legal", ("abogado", "demanda", "tribunal", "intimacion", "intimación")),
        ("reclamo", ("reclamo", "queja", "inconform")),
        ("promesa", ("promesa", "compromet", "pagare", "pagaré")),
        ("comprobante", ("comprobante", "pago", "transferencia", "captura", "voucher")),
    )
    for label, keys in rules:
        if any(k in text for k in keys):
            return label
    return "otro"


def extract_fields(subject: str, snippet: str = "") -> Dict[str, Any]:
    blob = f"{subject}\n{snippet}"
    ced = None
    m = _RE_CEDULA.search(blob)
    if m:
        ced = m.group(1).upper()
    monto = None
    mm = _RE_MONTO.search(blob)
    if mm:
        raw = mm.group(1).replace(".", "").replace(",", ".")
        try:
            monto = float(raw)
        except ValueError:
            monto = None
    return {"cedula": ced, "monto": monto}


def route_for(
    classify: str,
    *,
    has_receipt: bool,
    extract: Dict[str, Any],
) -> str:
    if classify == "rebote":
        return "revision_manual"
    if has_receipt and extract.get("cedula") and extract.get("monto"):
        return "autoconciliacion"
    if has_receipt and extract.get("cedula"):
        return "cargo_a_cuota"
    if has_receipt:
        return "cascada"
    return "revision_manual"


def sla_hours(classify: str) -> float:
    return {
        "legal": 4.0,
        "reclamo": 8.0,
        "rebote": 12.0,
        "promesa": 24.0,
        "comprobante": 6.0,
        "otro": 48.0,
    }.get(classify, 48.0)


def riesgo_for(classify: str, route: str) -> str:
    if classify in ("legal", "reclamo") or route == "revision_manual":
        return "alto"
    if classify == "rebote":
        return "medio"
    if route == "autoconciliacion":
        return "bajo"
    return "medio"


def evidencia_for(has_receipt: bool, ocr_ok: bool) -> str:
    if has_receipt and ocr_ok:
        return "fuerte"
    if has_receipt:
        return "media"
    return "debil"


def run_pipelines(
    *,
    subject: str,
    snippet: str,
    has_attachment: bool,
    attachment_types: Optional[List[str]] = None,
    pipeline_ids: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    ids = pipeline_ids or DEFAULT_PIPELINE_IDS
    ids_set = set(ids)
    types = [str(t).lower() for t in (attachment_types or [])]
    has_receipt_file = has_attachment and any(
        t.endswith(ext) or ext.lstrip(".") in t
        for t in types
        for ext in (".pdf", ".jpg", ".jpeg", ".png", ".webp")
    ) or (has_attachment and not types)

    classify = (
        classify_subject(subject, snippet) if "cobranza.classify" in ids_set else "otro"
    )
    extract = (
        extract_fields(subject, snippet) if "cobranza.extract" in ids_set else {}
    )
    receipts: List[Dict[str, Any]] = []
    if "cobranza.extract_receipts" in ids_set and has_receipt_file:
        receipts.append(
            {
                "filename": (types[0] if types else "adjunto"),
                "mime_type": None,
                "size_kb": None,
                "cedula": extract.get("cedula"),
                "monto": extract.get("monto"),
            }
        )
    ocr = {"ok": False, "texto": None, "motor": "heuristica_demo"}
    if "cobranza.ocr" in ids_set and has_receipt_file:
        ocr = {
            "ok": bool(extract.get("cedula") or extract.get("monto")),
            "texto": f"{extract.get('cedula') or ''} {extract.get('monto') or ''}".strip()
            or None,
            "motor": "heuristica_demo",
        }
    route = (
        route_for(classify, has_receipt=bool(receipts), extract=extract)
        if "revision.route" in ids_set
        else "revision_manual"
    )
    sla = sla_hours(classify) if "auditoria.sla" in ids_set else None
    evidencia = (
        evidencia_for(bool(receipts), bool(ocr.get("ok")))
        if "auditoria.evidencia" in ids_set
        else None
    )
    riesgo = (
        riesgo_for(classify, route) if "auditoria.riesgo" in ids_set else None
    )
    for r in receipts:
        r["route"] = route
        r["ocr_status"] = "heuristica"
    payload = {
        "classify": classify,
        "route": route,
        "sla_hours": sla,
        "evidencia": evidencia,
        "riesgo": riesgo,
        "extract": extract,
        "ocr": ocr,
        "pipelines": ids,
    }
    return payload, receipts
