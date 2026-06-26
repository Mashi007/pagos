"""Marcadores y reglas de re-escaneo OCR en cartera (revision manual)."""

from __future__ import annotations

import re

MARCADOR_DOC_PENDIENTE_REOCR_PREFIX = "REOCR-PEND-"

_RE_MARCADOR_REOCR = re.compile(r"^REOCR-PEND-\d+$", re.I)


def documento_marcador_pendiente_reocr(pago_id: int) -> str:
    """Documento placeholder unico por pago; cumple CHECK sin conservar DCME/ABONOS."""
    return f"{MARCADOR_DOC_PENDIENTE_REOCR_PREFIX}{int(pago_id)}"


def es_documento_marcador_pendiente_reocr(valor: str | None) -> bool:
    return bool(_RE_MARCADOR_REOCR.match((valor or "").strip()))


def sin_documento_real_tras_reocr(valor: str | None) -> bool:
    t = (valor or "").strip()
    return not t or es_documento_marcador_pendiente_reocr(t)
