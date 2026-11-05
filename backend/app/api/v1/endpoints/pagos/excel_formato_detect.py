"""
Detección de formatos de fila para carga masiva de pagos (Excel).

Formato C (Cédula | ID Préstamo | Fecha | Monto | Documento) debe evaluarse
ANTES que Formato D (Cédula | Monto | Fecha | Documento): ambos tienen cédula
en col0 y fecha en col2; si D gana, el ID de préstamo se interpreta como monto.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

from .constants import _PRESTAMO_ID_MAX
from .pago_normalizacion import _celda_a_string_documento, _validar_monto


def looks_like_cedula_excel(v: Any) -> bool:
    """Cédula válida en carga: solo V, E o J + 6-11 dígitos (no se admite Z)."""
    if v is None:
        return False
    s = str(v).strip()
    return bool(re.match(r"^[VEJ]\d{6,11}$", s, re.IGNORECASE))


def looks_like_date_excel(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (datetime, date)):
        return True
    s = str(v).strip()
    return bool(re.search(r"\d{1,4}[-\/]\d{1,2}[-\/]\d{1,4}", s))


def parse_prestamo_id_cell(v: Any) -> Optional[int]:
    """Entero de ID de préstamo; None si no es un id plausible."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        pid = v
    elif isinstance(v, float):
        if v != v or v != int(v):  # NaN o decimal
            return None
        pid = int(v)
    else:
        s = str(v).strip()
        if not s or not s.isdigit():
            return None
        try:
            pid = int(s)
        except ValueError:
            return None
    if pid < 1 or pid > _PRESTAMO_ID_MAX:
        return None
    return pid


def _es_numero_plano(v: Any) -> bool:
    if v is None or isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return v == v  # not NaN
    s = str(v).strip().replace(",", ".")
    return bool(re.match(r"^[+-]?\d+(\.\d+)?$", s))


def parece_fila_formato_c(row: Any) -> bool:
    """
    True si la fila tiene la estructura de Formato C:
    Cédula | ID Préstamo | Fecha | Monto | Nº documento [| Código opcional]

    Criterio (sin BD): 5+ columnas, col1 = id entero, col3 = monto numérico,
    col4 = documento no vacío. Así no se confunde con D de 4 columnas.
    Filas D con código (col3 documento con letras/símbolos) no califican porque
    col3 debe ser número plano (monto).
    """
    if row is None or len(row) < 5:
        return False
    if not looks_like_cedula_excel(row[0]):
        return False
    if parse_prestamo_id_cell(row[1]) is None:
        return False
    if not looks_like_date_excel(row[2]):
        return False
    if not _es_numero_plano(row[3]):
        return False
    ok_m, monto, _ = _validar_monto(row[3])
    if not ok_m or monto <= 0:
        return False
    doc = _celda_a_string_documento(row[4]) if row[4] is not None else ""
    if not (doc or "").strip():
        return False
    return True
