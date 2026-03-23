# -*- coding: utf-8 -*-
"""Normalizacion ligera de texto para plantillas (UTF-8, NFC)."""
import unicodedata
from typing import Optional


def normalizar_texto_plantilla(valor: Optional[str]) -> str:
    """
    Normaliza nombre/asunto visibles: strip y forma Unicode NFC.
    No intenta adivinar mojibake complejo (evita dependencias extra).
    """
    if valor is None:
        return ""
    s = valor if isinstance(valor, str) else str(valor)
    s = s.replace("\ufeff", "").strip()
    if not s:
        return ""
    return unicodedata.normalize("NFC", s)
