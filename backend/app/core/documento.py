"""
Módulo centralizado para normalización de documentos de pago.

REGLA GENERAL: documento acepta TODOS los formatos sin distinción.
ÚNICA RESTRICCIÓN: nunca duplicados (en archivo ni en BD).

- Cualquier formato: BNC/, BINANCE, VE/, ZELLE/, numérico, BS., € $, REF., etc.
- No se valida formato; no se rechaza por contenido
- Vacío permitido en varias filas
- Duplicado → rechazo
"""
import re
from typing import Any, Optional

# Límite de la columna numero_documento en tabla pagos (String(100))
MAX_LEN_NUMERO_DOCUMENTO = 100


def normalize_documento(val: Any) -> Optional[str]:
    """
    Normaliza número de documento para guardado y comparación.
    
    Reglas:
    - Acepta cualquier formato: BNC/, BINANCE, VE/, ZELLE/, numérico, BS. BNC / REF., etc.
    - Normalización solo para comparación: trim, colapsar espacios internos, truncar 100
    - No se valida formato; no se rechaza por contenido
    - Vacío/NAN/None → None
    - Notación científica de Excel → string de dígitos (7.4e14 → "740087415441562")
    
    Args:
        val: Valor a normalizar (str, int, float, None, etc.)
    
    Returns:
        String normalizado o None si está vacío
    """
    if val is None or val == "":
        return None
    
    s = (str(val) or "").strip()
    
    # Eliminar valores especiales que representan "vacío"
    if not s or s.upper() in ("NAN", "NONE", "UNDEFINED", "NA", "N/A"):
        return None
    
    # Normalizar notación científica de Excel a dígitos
    # Evitar que 7.4e14 y 740087415441562 sean claves distintas
    if re.match(r"^\d+\.?\d*[eE][+-]?\d+$", s):
        try:
            n = float(s)
            if n != n:  # Check for NaN
                return None
            s = str(int(round(n)))
        except (ValueError, OverflowError):
            pass
    
    # Colapsar espacios/tabs/saltos internos a un solo espacio
    # Esto asegura que "BNC / REF" y "BNC/REF" sean la misma clave
    s = re.sub(r"\s+", " ", s).strip()
    
    if not s:
        return None
    
    # Truncar a 100 caracteres para no exceder la columna BD
    return s[:MAX_LEN_NUMERO_DOCUMENTO] if len(s) > MAX_LEN_NUMERO_DOCUMENTO else s


def get_clave_canonica(val: Any) -> Optional[str]:
    """
    Alias para normalize_documento. Obtiene la clave canónica para comparación de duplicados.
    
    Args:
        val: Valor a normalizar
    
    Returns:
        String normalizado o None si está vacío
    """
    return normalize_documento(val)
