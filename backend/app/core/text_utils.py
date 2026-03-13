"""
Utilidad central para quitar BOM y caracteres invisibles en todo el sistema.
Usar al leer texto de Excel, API, Gmail, formularios, etc.
"""
import re
from typing import Any, Optional

# BOM (Byte Order Mark) UTF-8 y variantes
BOM_UTF8 = "\uFEFF"

# Caracteres invisibles / de formato que no se deben guardar en BD ni mostrar
# Incluye: zero-width space, zero-width non-joiner, zero-width joiner, word joiner,
# left-to-right/right-to-left marks, soft hyphen, y otros caracteres de control/formato
INVISIBLE_AND_FORMAT_CHARS = (
    "\u200B"  # ZERO WIDTH SPACE
    "\u200C"  # ZERO WIDTH NON-JOINER
    "\u200D"  # ZERO WIDTH JOINER
    "\u200E"  # LEFT-TO-RIGHT MARK
    "\u200F"  # RIGHT-TO-LEFT MARK
    "\u202A"  # LEFT-TO-RIGHT EMBEDDING
    "\u202B"  # RIGHT-TO-LEFT EMBEDDING
    "\u202C"  # POP DIRECTIONAL FORMATTING
    "\u202D"  # LEFT-TO-RIGHT OVERRIDE
    "\u202E"  # RIGHT-TO-LEFT OVERRIDE
    "\u2060"  # WORD JOINER (zero-width no-break space)
    "\u2061"  # FUNCTION APPLICATION
    "\u2062"  # INVISIBLE TIMES
    "\u2063"  # INVISIBLE SEPARATOR
    "\u2064"  # INVISIBLE PLUS
    "\uFEFF"  # ZERO WIDTH NO-BREAK SPACE (BOM)
    "\u00AD"  # SOFT HYPHEN (invisible)
)

# Patrón compilado para eliminar todos los caracteres invisibles de una vez
_RE_STRIP_INVISIBLE = re.compile(f"[{re.escape(INVISIBLE_AND_FORMAT_CHARS)}]+")


def strip_bom_and_invisible(value: Optional[str]) -> str:
    """
    Quita BOM (UTF-8) y caracteres invisibles/de formato del texto.
    Si value es None o no es str, se convierte a string y se limpia.
    Uso: cédulas, números de documento, nombres, campos de API, celdas Excel, etc.
    """
    if value is None:
        return ""
    s = value if isinstance(value, str) else str(value)
    # Quitar BOM al inicio (común en archivos guardados con BOM)
    if s.startswith(BOM_UTF8):
        s = s[1:]
    # Quitar todos los caracteres invisibles en cualquier posición
    s = _RE_STRIP_INVISIBLE.sub("", s)
    return s.strip()


def normalize_text(value: Any) -> str:
    """
    Normaliza un valor a string limpio: strip_bom_and_invisible + strip de espacios.
    Útil para celdas Excel y campos de texto en general.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value == int(value):
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    return strip_bom_and_invisible(str(value))
