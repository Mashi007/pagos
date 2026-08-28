"""
Utilidades para detectar columnas en cabeceras de la hoja CONCILIACIÓN (snapshot BD).

Compartidas por comparación ABONOS vs cuotas (Notificaciones / revisión manual).
"""
from __future__ import annotations

import re
from typing import Any, List, Optional


def as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def norm_header_cell(h: str) -> str:
    if not h:
        return ""
    normalized = (h or "").strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    return normalized


def pick_cedula_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula identidad" in hl or hl == "cedula" or hl == "cédula":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula" in hl or "cédula" in hl:
            return h
    if len(headers) > 4:
        return headers[4]
    return headers[0] if headers else None


def pick_lote_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if hl == "lote":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if "lote" in hl:
            return h
    return None


def norm_lote_celda(v: Any) -> Optional[str]:
    """Valor de celda LOTE comparable con enteros del filtro (70, '70', '70.0' → '70')."""
    s = as_text(v)
    if not s:
        return None
    t = s.replace(" ", "").replace(",", ".")
    try:
        if "." in t:
            return str(int(float(t)))
        return str(int(t))
    except ValueError:
        u = s.strip()
        return u if u else None


def pick_total_financiamiento_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = norm_header_cell(h)
        if "total" in hl and "financiam" in hl:
            return h
    for h in headers:
        hl = norm_header_cell(h)
        if "financiamiento" in hl or hl in ("monto", "monto total"):
            return h
    return None


def pick_abonos_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = norm_header_cell(h)
        if hl == "abonos" or "abono" in hl:
            return h
    return None


def pick_modalidad_pago_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = norm_header_cell(h)
        if "modalidad" in hl and "pago" in hl:
            return h
        if "modalidad" in hl and "financiam" in hl:
            return h
    for h in headers:
        hl = norm_header_cell(h)
        if hl == "modalidad" or "forma de pago" in hl or "forma pago" in hl:
            return h
    return None


def pick_numero_cuotas_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = norm_header_cell(h)
        if "cuota" in hl and (
            "num" in hl
            or "nro" in hl
            or "núm" in hl
            or "#" in (h or "")
            or "cantidad" in hl
        ):
            return h
        if hl in ("cuotas", ".", "numero cuotas", "número cuotas", "nro cuotas", "# cuotas"):
            return h
    return None
