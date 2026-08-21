"""
Módulo centralizado para normalización de documentos de pago.

- El comprobante (texto del banco) puede repetirse entre pagos distintos si se añade un
  **código desambiguador** opcional; en BD se guarda un único `numero_documento` compuesto
  (ver `compose_numero_documento_almacenado`).
- Sin código: no puede haber dos pagos con el mismo documento normalizado (misma clave canónica).
- **Serial / Nº documento (base):** solo dígitos `0-9` en todos los bancos, **excepto Zelle**,
  que admite letras y números combinados (`A-Z`/`0-9`). Ejemplo no Zelle: `BNC54879263323` → `54879263323`.
- **Escrituras nuevas (autorizar serial duplicado, no Binance):** único contrato =
  `codigo_documento` con token `D####` → almacenado `base §CD:D####` (revisión / Excel / Cobros).
- **Legado (no migrar):** `§CD:A####` / `§CD:P####` y sufijos Control 5 `_A####` / `_P####`
  siguen parseándose y contando como clave distinta.
- **Control 5** (mismo día+monto) sigue escribiendo `_A####` / `_P####` (auditoría aparte).
- Límite columna 100 caracteres.
"""
import re
from typing import Any, Optional, Tuple

# Límite de la columna numero_documento en tabla pagos (String(100))
MAX_LEN_NUMERO_DOCUMENTO = 100

# Sufijo interno entre comprobante y código (evitar que el usuario lo use en el comprobante).
SUFIJO_CODIGO_DOCUMENTO = " §CD:"

# Prefijo de tokens nuevos al autorizar serial duplicado (humano / carga masiva).
PREFIJO_CODIGO_DESAMBIGUACION = "D"

# Longitud máxima del código tras normalizar (deja margen para base + sufijo dentro de 100).
_MAX_CODIGO_DOC = 24

# Control 5 Visto (legado carga): no formar parte del serial numérico del banco.
_SUFIJO_VISTO_ADMIN_RE = re.compile(r"(_[AP]\d{4})$", re.IGNORECASE)

MSG_SERIAL_SOLO_DIGITOS = (
    "El número de documento/serial solo admite dígitos (0-9). "
    "No se permiten letras ni signos (ej. escriba 54879263323, no BNC54879263323). "
    "Excepción: Zelle admite letras y números combinados."
)


def es_institucion_zelle(institucion: Optional[str]) -> bool:
    return "ZELLE" in (institucion or "").strip().upper()


def _extraer_solo_digitos_serial(base: str) -> str:
    """Quita letras, espacios y signos; deja únicamente 0-9."""
    return re.sub(r"\D", "", base or "")


def _extraer_alfanum_zelle(base: str) -> str:
    """Zelle: solo A-Z / 0-9 (mayúsculas); sin espacios ni signos."""
    return re.sub(r"[^A-Za-z0-9]", "", base or "").upper()


def normalize_documento(
    val: Any,
    *,
    institucion: Optional[str] = None,
    permitir_alfanumerico: Optional[bool] = None,
) -> Optional[str]:
    """
    Normaliza número de documento (serial) para guardado y comparación.

    Reglas:
    - Por defecto: solo dígitos en el serial base.
    - Zelle (`institucion` o `permitir_alfanumerico=True`): letras + dígitos (A-Z0-9).
    - Conserva sufijo Control 5 `_A####` / `_P####` si venía en el valor.
    - Notación científica de Excel → dígitos.
    - Vacío/NAN/None → None
    """
    if val is None or val == "":
        return None

    alfanum = (
        bool(permitir_alfanumerico)
        if permitir_alfanumerico is not None
        else es_institucion_zelle(institucion)
    )

    s = (str(val) or "").strip()
    s = re.sub(r"[\u200B-\u200D\uFEFF\r\n\t]", "", s).strip()
    if s.startswith("'"):
        s = s.lstrip("'").strip()

    if not s or s.upper() in ("NAN", "NONE", "UNDEFINED", "NA", "N/A"):
        return None

    # Marcador interno de reescaneo OCR: no convertir a solo dígitos.
    if re.match(r"^REOCR-PEND-\d+$", s, re.IGNORECASE):
        return s[:MAX_LEN_NUMERO_DOCUMENTO]

    # Valor ya compuesto con código: normalizar solo la base; rearmar §CD:.
    if SUFIJO_CODIGO_DOCUMENTO in s:
        base_raw, code_raw = s.rsplit(SUFIJO_CODIGO_DOCUMENTO, 1)
        base_n = normalize_documento(
            base_raw,
            institucion=institucion,
            permitir_alfanumerico=alfanum,
        )
        code_n = normalize_codigo_documento(code_raw)
        if not base_n:
            return None
        if not code_n:
            return base_n
        return compose_numero_documento_almacenado(
            base_n,
            code_n,
            institucion=institucion,
            permitir_alfanumerico=alfanum,
        )

    if re.match(r"^\d+\.?\d*[eE][+-]?\d+$", s):
        try:
            n = float(s)
            if n != n:
                return None
            s = str(int(round(n)))
        except (ValueError, OverflowError):
            pass

    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None

    visto_suf = ""
    m_visto = _SUFIJO_VISTO_ADMIN_RE.search(s)
    if m_visto:
        letra = m_visto.group(1)[1].upper()
        digs = m_visto.group(1)[2:]
        visto_suf = f"_{letra}{digs}"
        s = s[: m_visto.start()].rstrip()

    if alfanum:
        cuerpo = _extraer_alfanum_zelle(s)
    else:
        cuerpo = _extraer_solo_digitos_serial(s)
    if not cuerpo:
        return None

    out = cuerpo + visto_suf
    return out[:MAX_LEN_NUMERO_DOCUMENTO]


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


def compose_numero_documento_almacenado(
    base: Any,
    codigo: Any,
    *,
    institucion: Optional[str] = None,
    permitir_alfanumerico: Optional[bool] = None,
) -> Optional[str]:
    """
    Valor único a guardar en `pagos.numero_documento`.
    Sin código: igual a normalize_documento(base) (+ sufijo Visto si aplica).
    Con código: base truncada + sufijo + código (encaja en 100 caracteres).
    """
    base_norm = normalize_documento(
        base,
        institucion=institucion,
        permitir_alfanumerico=permitir_alfanumerico,
    )
    if not base_norm:
        return None
    code_norm = normalize_codigo_documento(codigo)
    if not code_norm:
        return base_norm
    base_para_codigo = base_norm
    visto_tail = ""
    m_visto = _SUFIJO_VISTO_ADMIN_RE.search(base_norm)
    if m_visto:
        visto_tail = m_visto.group(1)
        base_para_codigo = base_norm[: m_visto.start()]
    suf = SUFIJO_CODIGO_DOCUMENTO + code_norm + visto_tail
    max_base = MAX_LEN_NUMERO_DOCUMENTO - len(suf)
    if max_base < 1:
        return None
    bn = (
        base_para_codigo[:max_base]
        if len(base_para_codigo) > max_base
        else base_para_codigo
    )
    out = bn + SUFIJO_CODIGO_DOCUMENTO + code_norm + visto_tail
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
        m = _SUFIJO_VISTO_ADMIN_RE.search(code)
        if m:
            return (base or "").strip() + m.group(1), code[: m.start()].strip()
        return (base or "").strip(), (code or "").strip()
    return s, ""


def get_clave_canonica(
    val: Any,
    *,
    institucion: Optional[str] = None,
) -> Optional[str]:
    """Alias para normalize_documento. Obtiene la clave canónica para comparación de duplicados."""
    return normalize_documento(val, institucion=institucion)
