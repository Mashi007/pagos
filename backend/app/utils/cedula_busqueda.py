"""
Normalización de cédula para búsquedas (alineado con frontend/src/utils/cedulaConsultaPublica.ts).
Solo dígitos 6–11 sin letra → se asume prefijo V.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

_CEDULA_COMPLETA = re.compile(r"^[VEGJ]\d{6,11}$", re.IGNORECASE)
_SOLO_DIGITOS = re.compile(r"^\d{6,11}$")
_LETRA_DIGITOS = re.compile(r"^[VEGJ]?\d+$", re.IGNORECASE)


def extraer_caracteres_cedula_busqueda(raw: str) -> str:
    try:
        s = unicodedata.normalize("NFKC", raw)
    except (TypeError, ValueError):
        s = raw
    s = s.strip().upper()
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    return re.sub(r"[^VEGJ0-9]", "", s)


def cedula_busqueda_canonica(raw: str) -> Optional[str]:
    """
    Si el texto completo (tras trim) es una cédula reconocible, devuelve forma canónica (ej. V30081920).
    Si no, None (búsqueda por nombre u otros campos).
    """
    t = (raw or "").strip()
    if not t:
        return None
    s = extraer_caracteres_cedula_busqueda(t)
    if not s:
        return None
    if not _LETRA_DIGITOS.match(s):
        return None
    if _SOLO_DIGITOS.match(s):
        return "V" + s
    if _CEDULA_COMPLETA.match(s):
        return s.upper()
    return None
