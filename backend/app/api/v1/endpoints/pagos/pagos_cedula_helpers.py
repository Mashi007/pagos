"""Validación de cédula VEJ compartida entre rutas de pagos (Excel, import cobros)."""
from __future__ import annotations

import re


def looks_like_cedula_vej(cedula: str) -> bool:
    """Solo V, E o J + 6-11 dígitos (no se admite Z)."""
    return bool(re.match(r"^[VEJ]\d{6,11}$", (cedula or "").strip(), re.IGNORECASE))
