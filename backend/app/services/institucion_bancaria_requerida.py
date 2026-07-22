"""
Regla básica: no guardar pago/reporte sin institución bancaria emisora.

Rechaza vacío, placeholders (Otros, N/A) y RAPICREDIT (beneficiario, no banco).
"""
from __future__ import annotations

import re
from typing import Optional

MSG_INSTITUCION_REQUERIDA = (
    "La institución bancaria es obligatoria. Indique el banco emisor del comprobante."
)

_PLACEHOLDERS = frozenset(
    {
        "",
        "otros",
        "otro",
        "n/a",
        "na",
        "pendiente",
        "sin especificar",
        "__sin_especificar__",
        "excel",
        "deposito",
        "depósito",
    }
)

_RE_RAPICREDIT = re.compile(
    r"^(?:bapi|raph|rapi)[\s\-_.]*credi(?:t)?(?:[\s\-_,.]*c\.?\s*a\.?)?$"
    r"|^rapicredit(?:[\s\-_,.]*c\.?\s*a\.?)?$"
    r"|^soft[\s\-_.]*credit(?:[\s\-_,.]*c\.?\s*a\.?)?$",
    re.IGNORECASE,
)


def _compact(s: str) -> str:
    return re.sub(r"[\s\-_,.]+", "", (s or "").lower())


def es_institucion_bancaria_valida(valor: Optional[str]) -> bool:
    """True si el texto es un banco/emisor usable para guardar."""
    t = (valor or "").strip()
    if not t:
        return False
    low = t.lower()
    if low in _PLACEHOLDERS:
        return False
    compact = _compact(t)
    if compact in {
        "rapicredit",
        "rapicreditca",
        "rapcredit",
        "rapicredi",
        "bapicredit",
        "raphcredit",
        "softcredit",
    }:
        return False
    if _RE_RAPICREDIT.match(t):
        return False
    return True


def error_si_falta_institucion(valor: Optional[str]) -> Optional[str]:
    """None si OK; mensaje de error si no se puede guardar."""
    if es_institucion_bancaria_valida(valor):
        return None
    t = (valor or "").strip()
    es_rapi = bool(
        t
        and (
            _compact(t)
            in {
                "rapicredit",
                "rapicreditca",
                "rapcredit",
                "rapicredi",
                "bapicredit",
                "raphcredit",
                "softcredit",
            }
            or _RE_RAPICREDIT.match(t)
        )
    )
    if es_rapi:
        return (
            "RapiCredit es el beneficiario, no el banco. "
            "Indique la institución emisora (Mercantil, BNC, Binance, Recibo, etc.)."
        )
    return MSG_INSTITUCION_REQUERIDA


def normalizar_institucion_bancaria_requerida(valor: Optional[str], *, max_len: int = 255) -> str:
    """
    Devuelve institución lista para persistir.
    Raises ValueError con mensaje claro si falta o es inválida.
    """
    err = error_si_falta_institucion(valor)
    if err:
        raise ValueError(err)
    return (valor or "").strip()[:max_len]
