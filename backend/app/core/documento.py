"""

Módulo centralizado para normalización de documentos de pago.



- El comprobante (texto del banco) puede repetirse entre pagos distintos si se añade un

  **código desambiguador** opcional; en BD se guarda un único `numero_documento` compuesto

  (ver `compose_numero_documento_almacenado`).

- Sin código: no puede haber dos pagos con el mismo documento normalizado (misma clave canónica).

- Formato aceptado: BNC/, BINANCE, VE/, ZELLE/, numérico, BS., etc. Límite columna 100 caracteres.

"""

import re

from typing import Any, Optional, Tuple



# Límite de la columna numero_documento en tabla pagos (String(100))

MAX_LEN_NUMERO_DOCUMENTO = 100



# Sufijo interno entre comprobante y código (evitar que el usuario lo use en el comprobante).

SUFIJO_CODIGO_DOCUMENTO = " §CD:"



# Longitud máxima del código tras normalizar (deja margen para base + sufijo dentro de 100).

_MAX_CODIGO_DOC = 24





def normalize_documento(val: Any) -> Optional[str]:

    """

    Normaliza número de documento para guardado y comparación.



    Reglas:

    - Acepta cualquier formato: BNC/, BINANCE, VE/, ZELLE/, numérico, BS. BNC / REF., etc.

    - Normalización solo para comparación: trim, colapsar espacios internos, truncar 100

    - No se valida formato; no se rechaza por contenido

    - Vacío/NAN/None → None

    - Notación científica de Excel → string de dígitos (7.4e14 → "740087415441562")

    """

    if val is None or val == "":

        return None



    s = (str(val) or "").strip()

    # Quitar caracteres invisibles y BOM (alineado con frontend limpiarDocumento)

    s = re.sub(r"[\u200B-\u200D\uFEFF\r\n\t]", "", s).strip()

    # Excel a veces antepone comilla simple para forzar texto

    if s.startswith("'"):

        s = s.lstrip("'").strip()



    # Eliminar valores especiales que representan "vacío"

    if not s or s.upper() in ("NAN", "NONE", "UNDEFINED", "NA", "N/A"):

        return None



    # Normalizar notación científica de Excel a dígitos

    if re.match(r"^\d+\.?\d*[eE][+-]?\d+$", s):

        try:

            n = float(s)

            if n != n:  # Check for NaN

                return None

            s = str(int(round(n)))

        except (ValueError, OverflowError):

            pass



    # Colapsar espacios/tabs/saltos internos a un solo espacio

    s = re.sub(r"\s+", " ", s).strip()



    if not s:

        return None



    return s[:MAX_LEN_NUMERO_DOCUMENTO] if len(s) > MAX_LEN_NUMERO_DOCUMENTO else s





def normalize_codigo_documento(val: Any) -> Optional[str]:

    """Código opcional corto; no puede contener el marcador interno del sufijo."""

    if val is None or val == "":

        return None

    s = (str(val) or "").strip()

    s = re.sub(r"[\u200B-\u200D\uFEFF\r\n\t]", "", s).strip()

    if not s or s.upper() in ("NAN", "NONE", "UNDEFINED", "NA", "N/A"):

        return None

    if "§CD:" in s:

        return None

    s = re.sub(r"\s+", " ", s).strip()

    if not s:

        return None

    if len(s) > _MAX_CODIGO_DOC:

        s = s[:_MAX_CODIGO_DOC]

    return s





def compose_numero_documento_almacenado(base: Any, codigo: Any) -> Optional[str]:

    """

    Valor único a guardar en `pagos.numero_documento`.

    Sin código: igual a normalize_documento(base).

    Con código: base truncada + sufijo + código (encaja en 100 caracteres).

    """

    base_norm = normalize_documento(base)

    if not base_norm:

        return None

    code_norm = normalize_codigo_documento(codigo)

    if not code_norm:

        return base_norm

    suf = SUFIJO_CODIGO_DOCUMENTO + code_norm

    max_base = MAX_LEN_NUMERO_DOCUMENTO - len(suf)

    if max_base < 1:

        return None

    bn = base_norm[:max_base] if len(base_norm) > max_base else base_norm

    out = bn + suf

    return out[:MAX_LEN_NUMERO_DOCUMENTO]





def split_numero_documento_almacenado(stored: Any) -> Tuple[str, str]:

    """

    Parte el valor de BD en (comprobante visible, código).

    Filas antiguas sin sufijo → todo en comprobante, código vacío.

    """

    s = (str(stored) or "").strip()

    if not s:

        return "", ""

    sep = SUFIJO_CODIGO_DOCUMENTO

    if sep in s:

        base, code = s.rsplit(sep, 1)

        return (base or "").strip(), (code or "").strip()

    return s, ""





def get_clave_canonica(val: Any) -> Optional[str]:

    """Alias para normalize_documento. Obtiene la clave canónica para comparación de duplicados."""

    return normalize_documento(val)


