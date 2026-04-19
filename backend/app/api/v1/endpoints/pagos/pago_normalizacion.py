"""Normalización y validación ligera de campos de pago (Excel, montos, huella)."""

import re
from typing import Any, Optional

from .constants import _MAX_MONTO_PAGADO, _MIN_MONTO_PAGADO


def _normalizar_ref_fingerprint(valor: Optional[str]) -> str:
    ref = (valor or "").strip().upper()
    patrones = (
        r"^(BS\.?\s*)?BNC\s*/\s*(REF\.?\s*)?",
        r"^BINANCE\s*/\s*",
        r"^BNC\s*/\s*",
        r"^VE\s*/\s*",
    )
    for pat in patrones:
        ref = re.sub(pat, "", ref)
    return ref.strip()


def _validar_monto(monto_raw: Any) -> tuple[bool, float, str]:
    """
    Valida que el monto esté dentro de los rangos permitidos para NUMERIC(14, 2).

    Retorna: (es_valido, monto_parseado, mensaje_error)
    """
    try:
        monto = float(monto_raw) if monto_raw is not None else 0.0
    except (TypeError, ValueError):
        return (False, 0.0, f"No se puede parsear el monto: {monto_raw}")

    if monto < _MIN_MONTO_PAGADO:
        return (False, monto, f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}")

    if monto > _MAX_MONTO_PAGADO:
        if monto < 100000:
            return (
                False,
                monto,
                f"Monto sospechosamente pequeño para ser una cantidad; parece ser una fecha o número de secuencia: {monto}",
            )
        return (False, monto, f"Monto excede límite máximo ({_MAX_MONTO_PAGADO}): {monto}")

    return (True, monto, "")


def _celda_a_string_documento(val: Any) -> str:
    """
    Convierte el valor de una celda Excel a string para Nº documento.

    Acepta cualquier tipo: str, int, float (evita notación científica para números largos).
    """
    if val is None:
        return ""
    if isinstance(val, float):
        if val != val:
            return ""  # NaN
        if val == int(val):
            return str(int(val))
        return str(val)
    if isinstance(val, int):
        return str(val)
    return str(val).strip()


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
