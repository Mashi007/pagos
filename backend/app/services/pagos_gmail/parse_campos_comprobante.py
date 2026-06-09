"""
Parsers compartidos de monto y fecha desde texto Gemini / OCR (escáner Infopagos y Gmail).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

PAGOS_NA = "NA"

# Montos escaneados/reportados por encima de este valor van a revisión manual (cualquier moneda/medio).
MONTO_UMBRAL_REVISION_MANUAL = 3000.0

_RANGO_CUOTA_USD_MIN = 30.0
_RANGO_CUOTA_USD_MAX = 500.0


def _parece_contexto_divisa_usd(raw: str) -> bool:
    if re.search(r"(?i)\b(usd|usdt|u\$s|us\$|dolar(?:es)?|divisa)\b", raw or ""):
        return True
    if re.search(r"[*#]{3,}", raw or ""):
        return True
    return False


def _parece_contexto_bs(raw: str) -> bool:
    return bool(re.search(r"(?i)\b(bs\.?|bss|bolivar(?:es)?|ves|veb)\b", raw or ""))


def _normalizar_separadores_punto_monto(
    s: str, *, ctx_usd: bool, ctx_bs: bool
) -> str:
    """Distingue miles VE (1.500) de decimales USD/OCR (135.00, 135.000)."""
    if "." not in s:
        return s
    parts = s.split(".")
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        return s

    last = parts[-1]

    if len(parts) == 2:
        if len(last) <= 2:
            return f"{parts[0]}.{last}"
        if len(last) == 3:
            if last == "000":
                if ctx_bs and len(parts[0]) <= 2:
                    return "".join(parts)
                return f"{parts[0]}.{last[:2]}"
            if not ctx_usd and len(parts[0]) <= 2:
                return "".join(parts)
            if ctx_usd or int(parts[0]) >= 30:
                return f"{parts[0]}.{last[:2]}"
            return "".join(parts)
        return "".join(parts)

    if len(last) <= 2:
        return "".join(parts[:-1]) + "." + last
    if len(last) == 3:
        return "".join(parts)
    return s


def _corregir_monto_ocr_exceso_digitos(
    n: float, *, ctx_usd: bool = False, moneda: Optional[str] = None
) -> float:
    """
    USD: Gemini/OCR a veces pierde el punto (135.00 → 135000 o 13500).
    Solo corrige cuando la moneda/contexto es divisa fuerte y el cociente cae en rango de cuota.
    """
    prefer_usd = ctx_usd or (moneda or "").strip().upper() in ("USD", "USDT")
    if not prefer_usd or n != int(n):
        return n
    ni = int(n)
    if ni < 1000:
        return n

    candidates: List[float] = []
    if ni >= 10000 and ni % 1000 == 0:
        candidates.append(ni / 1000)
    if ni >= 1000 and ni % 100 == 0:
        candidates.append(ni / 100)

    for cand in candidates:
        if _RANGO_CUOTA_USD_MIN <= cand <= _RANGO_CUOTA_USD_MAX:
            return float(cand)
    return n


_ASTERISCO_MONTO_BNC_RE = re.compile(r"([*#]{4,})(\d+)\.(\d{2})\b")


def _corregir_monto_linea_asteriscos_bnc(s: str) -> Optional[str]:
    """
    BNC cajero (Depósito US$): la línea ``****114.00`` a veces llega como ``****14.00``
    porque el primer dígito queda pegado a los asteriscos. Solo corrige con patrón visible.
    """
    compact = (s or "").replace(" ", "")
    m = _ASTERISCO_MONTO_BNC_RE.search(compact)
    if not m:
        return None
    stars, int_part, frac = m.group(1), m.group(2), m.group(3)
    n_stars = len(stars)
    if len(int_part) >= 3:
        return f"{int_part}.{frac}"
    if len(int_part) == 2 and 10 <= int(int_part) <= 19 and n_stars >= 6:
        return f"1{int_part}.{frac}"
    if len(int_part) == 2 and 20 <= int(int_part) <= 99 and n_stars >= 12:
        return f"1{int_part}.{frac}"
    return f"{int_part}.{frac}"


def _corregir_monto_bnc_usd_entero_perdio_cientos(
    n: float, *, institucion: Optional[str] = None, ctx_usd: bool = False
) -> float:
    """
    Respaldo cuando Gemini devuelve solo el entero (14) sin asteriscos en el string,
    pero la institución ya es BNC y el depósito en USD suele ser 1XX.
    Solo 10-19 → 110-119; no tocar 96, 135 parseados correctamente, etc.
    """
    if not ctx_usd or "BNC" not in (institucion or "").upper():
        return n
    if n != int(n):
        return n
    ni = int(n)
    if 10 <= ni <= 19:
        return float(100 + ni)
    return n


def _corregir_monto_ocr_tres_digitos(n: float) -> float:
    """
    Mercantil / ventanilla: OCR a veces lee ``96,00`` como ``969`` o ``965`` (coma+ceros).
    Cola 5/9: corrige si la base XX (30-250) es plausible de cuota.
    Cola 0: solo si n>=900 (ej. ``980``→``98``); no tocar montos reales como ``580`` USDT Binance.
    """
    if n != int(n) or n < 100 or n >= 1000:
        return n
    s = str(int(n))
    if len(s) != 3:
        return n
    base = int(s[:2])
    if not (30 <= base <= 250):
        return n
    trailing = s[2]
    if trailing in "59":
        return float(base)
    if trailing == "0" and n >= 900:
        return float(base)
    return n


def parse_monto_comprobante(
    val: Any,
    *,
    moneda: Optional[str] = None,
    institucion: Optional[str] = None,
) -> Optional[float]:
    if val is None:
        return None
    raw = str(val).strip() if not isinstance(val, (int, float)) else ""
    ctx_usd = _parece_contexto_divisa_usd(raw) or (moneda or "").strip().upper() in (
        "USD",
        "USDT",
    )
    ctx_bs = _parece_contexto_bs(raw) or (moneda or "").strip().upper() in ("BS", "VES")

    if isinstance(val, (int, float)):
        if isinstance(val, float) and (val != val or val == float("inf")):
            return None
        n = round(float(val), 2)
        n = _corregir_monto_ocr_tres_digitos(n)
        n = _corregir_monto_ocr_exceso_digitos(n, ctx_usd=ctx_usd, moneda=moneda)
        n = _corregir_monto_bnc_usd_entero_perdio_cientos(
            n, institucion=institucion, ctx_usd=ctx_usd
        )
        return round(n, 2)

    aster_monto = _corregir_monto_linea_asteriscos_bnc(raw)
    s = aster_monto if aster_monto else raw
    s = re.sub(
        r"(?i)\s*(usd|usdt|u\$s|us\$|bs\.?|bss|bolivar(?:es)?|ves)\s*$",
        "",
        s,
    ).strip()
    s = re.sub(
        r"(?i)^\s*(usd|usdt|u\$s|us\$|bs\.?|bss)\s+",
        "",
        s,
    ).strip()
    s = re.sub(r"(?i)\b(bs\.?|usd|usdt|u\$s|\$|ves)\b", "", s)
    s = re.sub(r"[*#]+", "", s)
    s = s.replace(" ", "")
    if not s or s.lower() in ("na", "n/a", "-"):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2 and parts[0].replace(".", "").isdigit():
            s = parts[0].replace(".", "") + "." + parts[1]
        else:
            s = s.replace(",", ".")
    elif "." in s:
        s = _normalizar_separadores_punto_monto(s, ctx_usd=ctx_usd, ctx_bs=ctx_bs)
    try:
        n = float(s)
        if n != n or n == float("inf"):
            return None
        n = _corregir_monto_ocr_tres_digitos(n)
        n = _corregir_monto_ocr_exceso_digitos(n, ctx_usd=ctx_usd, moneda=moneda)
        n = _corregir_monto_bnc_usd_entero_perdio_cientos(
            n, institucion=institucion, ctx_usd=ctx_usd
        )
        return round(n, 2)
    except (TypeError, ValueError):
        return None


def _year_from_two_digits(yy: int) -> int:
    return 2000 + yy if yy < 70 else 1900 + yy


def fecha_plausible(f: date, ref_hoy: date) -> bool:
    if f > ref_hoy:
        return False
    if f.year < ref_hoy.year - 4:
        return False
    return True


def _pick_fecha_candidata(candidates: List[Optional[date]], ref_hoy: date) -> Optional[date]:
    valid = [c for c in candidates if c is not None and fecha_plausible(c, ref_hoy)]
    if not valid:
        return None
    # Venezuela: DD/MM/YYYY primero; no elegir MM/DD por cercania al dia de hoy.
    return valid[0]


def _parse_fecha_dmy_parts(d: int, mo: int, y: int, ref_hoy: date) -> Optional[date]:
    opts: List[Optional[date]] = []
    try:
        opts.append(date(y, mo, d))
    except ValueError:
        pass
    if d != mo and d <= 12 and mo <= 12:
        try:
            opts.append(date(y, d, mo))
        except ValueError:
            pass
    return _pick_fecha_candidata(opts, ref_hoy)


def _parse_fecha_compacta_6(digits: str, ref_hoy: date) -> Optional[date]:
    if len(digits) != 6 or not digits.isdigit():
        return None
    dd, mm, yy = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    cand_ddmmyy = _parse_fecha_dmy_parts(dd, mm, _year_from_two_digits(yy), ref_hoy)
    yy2, mo2, d2 = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    cand_yymmdd: Optional[date] = None
    try:
        cand_yymmdd = date(_year_from_two_digits(yy2), mo2, d2)
    except ValueError:
        cand_yymmdd = None
    if cand_yymmdd and not fecha_plausible(cand_yymmdd, ref_hoy):
        cand_yymmdd = None
    return _pick_fecha_candidata([cand_ddmmyy, cand_yymmdd], ref_hoy)


def parse_fecha_comprobante(val: Any, ref_hoy: Optional[date] = None) -> Optional[date]:
    if ref_hoy is None:
        from app.services.tasa_cambio_service import fecha_hoy_caracas

        ref_hoy = fecha_hoy_caracas()
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("na", "n/a", "-", ""):
        return None
    if "T" in s[:29] and re.match(r"^\d{4}-\d{2}-\d{2}T", s):
        s = s.split("T", 1)[0].strip()
    s10 = s[:10]
    try:
        if len(s10) >= 10 and s10[4] in "-/" and s10[7] in "-/" and s10[4] == s10[7]:
            y, m, d = int(s10[0:4]), int(s10[5:7]), int(s10[8:10])
            parsed = _parse_fecha_dmy_parts(d, m, y, ref_hoy)
            if parsed:
                return parsed
    except (ValueError, TypeError):
        pass
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
    if m:
        parsed = _parse_fecha_dmy_parts(
            int(m.group(1)), int(m.group(2)), int(m.group(3)), ref_hoy
        )
        if parsed:
            return parsed
    m2 = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$", s)
    if m2:
        parsed = _parse_fecha_dmy_parts(
            int(m2.group(1)),
            int(m2.group(2)),
            _year_from_two_digits(int(m2.group(3))),
            ref_hoy,
        )
        if parsed:
            return parsed
    digits_only = re.sub(r"\D", "", s)
    if len(digits_only) == 6:
        parsed = _parse_fecha_compacta_6(digits_only, ref_hoy)
        if parsed:
            return parsed
    m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m_iso:
        parsed = _parse_fecha_dmy_parts(
            int(m_iso.group(3)), int(m_iso.group(2)), int(m_iso.group(1)), ref_hoy
        )
        if parsed:
            return parsed
    m_merc_ref = re.search(r"-(\d{4})(\d{2})(\d{2})-", s)
    if m_merc_ref:
        parsed = _parse_fecha_dmy_parts(
            int(m_merc_ref.group(3)),
            int(m_merc_ref.group(2)),
            int(m_merc_ref.group(1)),
            ref_hoy,
        )
        if parsed:
            return parsed
    m_lat = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s)
    if m_lat:
        parsed = _parse_fecha_dmy_parts(
            int(m_lat.group(1)), int(m_lat.group(2)), int(m_lat.group(3)), ref_hoy
        )
        if parsed:
            return parsed
    return None


def monto_comprobante_a_excel(val: Any) -> str:
    s = str(val).strip() if val is not None else ""
    if s.upper() == "NR":
        return "NR"
    if not s or s.upper() == PAGOS_NA:
        return ""
    n = parse_monto_comprobante(val)
    if n is None:
        return ""
    return f"{n:.2f}"


def _monto_numerico_para_revision(val: Any, *, moneda: Optional[str] = None) -> Optional[float]:
    if isinstance(val, (int, float)):
        n = float(val)
        if n != n or n == float("inf"):
            return None
        return round(n, 2)
    return parse_monto_comprobante(val, moneda=moneda)


def monto_requiere_revision_manual(val: Any, *, moneda: Optional[str] = None) -> bool:
    """True si el monto parseado es estrictamente mayor al umbral de revisión manual."""
    n = _monto_numerico_para_revision(val, moneda=moneda)
    if n is None:
        return False
    return n > MONTO_UMBRAL_REVISION_MANUAL


def mensaje_monto_revision_manual(val: Any, *, moneda: Optional[str] = None) -> str:
    n = _monto_numerico_para_revision(val, moneda=moneda) or 0.0
    return (
        f"El monto ({n:,.2f}) supera {MONTO_UMBRAL_REVISION_MANUAL:,.0f}; "
        "requiere revisión manual antes de guardar o aplicar."
    )


def fusionar_validacion_reglas_monto_alto_escaneo(
    validacion_reglas: Optional[str],
    monto: Any,
    *,
    moneda: Optional[str] = None,
) -> Optional[str]:
    """Añade observación de revisión manual al escaneo Infopagos/lote si el monto supera el umbral."""
    if not monto_requiere_revision_manual(monto, moneda=moneda):
        return validacion_reglas
    msg = mensaje_monto_revision_manual(monto, moneda=moneda)
    prev = (validacion_reglas or "").strip()
    if not prev:
        return msg
    if msg in prev:
        return prev
    return f"{prev} {msg}"


def fecha_comprobante_a_ddmmyyyy(val: Any, ref_hoy: Optional[date] = None) -> str:
    parsed = parse_fecha_comprobante(val, ref_hoy)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return ""


def inferir_fecha_pago_desde_numero_operacion(
    num_op: Any,
    ref_hoy: Optional[date] = None,
) -> str:
    """
    Infiere fecha solo desde patrones embebidos en serial/ref (p. ej. DCME …-YYYYMMDD-…).
    No inventa fechas desde contexto externo ni serial 7400… sin bloque de fecha.
    """
    nr = (str(num_op).strip() if num_op is not None else "")
    if not nr or nr.upper() == PAGOS_NA:
        return ""
    return fecha_comprobante_a_ddmmyyyy(nr, ref_hoy)


_LABEL_NUM_OP_PREFIX_RE = re.compile(
    r"^(?:(?:serial|ref(?:\.|\s|:)?|referencia|operaci[oó]n|secuencial|"
    r"n[ºo°°]\.?\s*(?:operaci[oó]n|documento|control|ref)?)\s*[:.]?\s*)+",
    re.IGNORECASE,
)

_MERCANTIL_SERIAL_LARGO_RE = re.compile(r"7400\d{9,}")
_SERIAL_ETIQUETADO_RE = re.compile(r"(?i)\bserial\s*[:.]?\s*(\d{6,30})")
_REF_ETIQUETADO_RE = re.compile(r"(?i)\bref(?:\.|\s|:)?\s*(\d{6,18})")
_MERCANTIL_DCME_GUIONADO_RE = re.compile(
    r"^\d{3,5}-\d{8}-\d{6}-DCME-\d{3,5}-[A-Z]$",
    re.IGNORECASE,
)


def _es_institucion_mercantil(institucion: str) -> bool:
    return "mercantil" in (institucion or "").strip().lower()


def es_codigo_dcme_mercantil(s: str) -> bool:
    """Código de validador Mercantil (ej. 9276-20260424-140259-DCME-7819-A), no es el Serial."""
    t = (s or "").strip()
    if not t:
        return False
    if _MERCANTIL_DCME_GUIONADO_RE.match(t):
        return True
    return bool(re.search(r"-\d{8}-\d{6}-DCME-", t, re.IGNORECASE))


def _deduplicar_digitos_repetidos(digits: str) -> str:
    """OCR/Gemini a veces repite el mismo serial pegado (740087…740087…)."""
    d = (digits or "").strip()
    while len(d) >= 12 and len(d) % 2 == 0:
        half = len(d) // 2
        if d[:half] == d[half:]:
            d = d[:half]
        else:
            break
    return d


def _normalizar_serial_tras_etiqueta(captured: str) -> str:
    t = (captured or "").strip()
    if not t:
        return ""
    if t.startswith("7400"):
        merc = extraer_serial_mercantil_7400(t)
        return merc or t[:15]
    return t[:18]


def extraer_serial_etiquetado_bnc(texto: str) -> str:
    """Valor junto a «Serial:» en recibo BNC cajero o Mercantil (ej. 105137674 / 740087…)."""
    m = _SERIAL_ETIQUETADO_RE.search(texto or "")
    if not m:
        return ""
    return _normalizar_serial_tras_etiqueta(m.group(1))


def extraer_ref_etiquetado_bnc(texto: str) -> str:
    """Valor junto a «Ref:» en recibo BNC (no usar si hay Serial legible)."""
    m = _REF_ETIQUETADO_RE.search(texto or "")
    return m.group(1) if m else ""


def _es_institucion_bnc(institucion: str) -> bool:
    t = (institucion or "").strip().lower()
    return t == "bnc" or "banco nacional" in t or t.startswith("bnc ")


def corregir_numero_operacion_bnc(
    num_op: str,
    *,
    institucion: str = "",
    texto_auxiliar: str = "",
) -> str:
    """
    Recibo BNC cajero: el número de operación es el valor de **Serial:**,
    no Ref ni RIF ni cuenta 0191.
    """
    blob = f"{num_op}\n{texto_auxiliar}"
    serial = extraer_serial_etiquetado_bnc(blob)
    if not serial:
        return num_op
    op_norm = sanitizar_numero_operacion_comprobante(num_op) if num_op else ""
    if op_norm == serial:
        return op_norm
    ref_lbl = extraer_ref_etiquetado_bnc(blob)
    if not op_norm or op_norm == ref_lbl or op_norm != serial:
        return serial[:100]
    return op_norm


def extraer_serial_mercantil_7400(texto: str) -> str:
    """Serial Mercantil (740087…, 15 dígitos típicos) desde cualquier fragmento OCR."""
    if not texto:
        return ""
    compact = _deduplicar_digitos_repetidos(re.sub(r"\D", "", texto))
    if not compact:
        return ""
    runs = _MERCANTIL_SERIAL_LARGO_RE.findall(compact)
    if not runs:
        return ""
    quince = [r for r in runs if len(r) == 15]
    if quince:
        return quince[0]
    candidatos: List[str] = []
    for r in sorted(set(runs), key=len):
        norm = _deduplicar_digitos_repetidos(r)
        if norm and norm not in candidatos:
            candidatos.append(norm)
    if not candidatos:
        return ""
    return min(candidatos, key=len)


def numero_operacion_mercantil_solo_dcme(num_op: str) -> bool:
    """True si el valor parece solo código DCME guionado, sin Serial 7400…."""
    t = (num_op or "").strip()
    if not t:
        return False
    if extraer_serial_mercantil_7400(t):
        return False
    return es_codigo_dcme_mercantil(t)


def corregir_numero_operacion_mercantil(
    num_op: str,
    *,
    institucion: str = "",
    texto_auxiliar: str = "",
) -> str:
    """
    Mercantil DEPÓSITO DIVISAS: el número de operación es el Serial largo 740087…
    (etiqueta «Serial:» en la tira), no el código guionado DCME del validador.
    """
    op_norm = sanitizar_numero_operacion_comprobante(num_op) if num_op else ""
    serial_op = extraer_serial_mercantil_7400(op_norm) if op_norm else ""
    serial_aux = extraer_serial_mercantil_7400(texto_auxiliar) if texto_auxiliar else ""
    serial = serial_op or serial_aux
    if serial_op and serial_aux and len(serial_aux) > len(serial_op):
        if _deduplicar_digitos_repetidos(serial_aux) == serial_op:
            serial = serial_op
    if serial and (not op_norm or op_norm != serial):
        if op_norm and serial_op == op_norm:
            return op_norm
        return serial[:100]
    if op_norm and numero_operacion_mercantil_solo_dcme(op_norm):
        return ""
    return op_norm if op_norm else num_op


def _prefijo_comun_digitos(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x == y:
            n += 1
        else:
            break
    return n


def _parecen_ref_serial_bnc_concatenados(digits_only: str) -> bool:
    """
    True si parece Ref+Serial BNC pegados por OCR (ej. 113907169113907166).
    No aplica a IDs largos únicos (Binance Pay suele 15-19 dígitos sin prefijo común).
    """
    if len(digits_only) % 2 != 0:
        return False
    half = len(digits_only) // 2
    if not (16 <= len(digits_only) <= 18):
        return False
    left, right = digits_only[:half], digits_only[half:]
    if not (left.isdigit() and right.isdigit()):
        return False
    if not (8 <= len(left) <= 9 and 8 <= len(right) <= 9):
        return False
    if left == right:
        return True
    common = _prefijo_comun_digitos(left, right)
    min_len = min(len(left), len(right))
    return common >= 6 and common >= min_len - 3


def _preferir_serial_mercantil_largo(s: str) -> str:
    """
    Si coexisten código DCME guionado y Serial largo 7400…, prioriza el Serial (regla Gmail A1).
    Si el OCR repite el mismo serial pegado, deja una sola copia.
    """
    if not s:
        return s
    compact_digits = re.sub(r"\D", "", s)
    if compact_digits.startswith("7400") and len(compact_digits) > 15:
        canon = extraer_serial_mercantil_7400(compact_digits)
        if canon:
            return canon
    serial_runs = _MERCANTIL_SERIAL_LARGO_RE.findall(compact_digits)
    if not serial_runs:
        return s
    best = extraer_serial_mercantil_7400(compact_digits)
    low = s.lower()
    if "dcme" in low or re.search(r"\d{4}-\d{8}-", s) or len(compact_digits) > 15:
        return best
    return s


def sanitizar_numero_operacion_comprobante(raw: Any) -> str:
    """
    Limpia OCR/Gemini sin inventar dígitos: quita etiquetas, deduplica repeticiones
    obvias y evita concatenar Ref+Serial; conserva ceros a la izquierda del comprobante.
    """
    from app.core.documento import normalize_documento

    s = normalize_documento(raw) or (str(raw or "")).strip()
    s = re.sub(r"[\u200B-\u200D\uFEFF\r\n\t]", "", s).strip()
    if not s or s.upper() in ("NA", "N/A", "NONE"):
        return ""

    serial_etiquetado = extraer_serial_etiquetado_bnc(s)
    if serial_etiquetado and re.search(r"(?i)\bserial\b", s):
        return serial_etiquetado[:100]

    parts = [p.strip() for p in re.split(r"[\s,;|/]+", s) if p.strip()]
    if len(parts) >= 2 and len(set(parts)) == 1:
        s = parts[0]
    elif len(parts) >= 2:
        digit_parts = [p for p in parts if re.fullmatch(r"\d+", p)]
        if len(digit_parts) >= 2 and all(8 <= len(p) <= 13 for p in digit_parts[:2]):
            a, b = digit_parts[0], digit_parts[1]
            pref = min(len(a), len(b), 7)
            if a[:pref] == b[:pref]:
                s = b
            else:
                s = a

    s2 = _LABEL_NUM_OP_PREFIX_RE.sub("", s).strip()
    if s2:
        s = s2

    compact = s.replace(" ", "")
    digits_only = re.sub(r"\D", "", compact)
    es_codigo_guionado = bool(
        re.search(r"[A-Za-z]", compact) or "dcme" in s.lower()
    )
    if digits_only and not es_codigo_guionado and len(digits_only) % 2 == 0:
        half = len(digits_only) // 2
        left, right = digits_only[:half], digits_only[half:]
        if left == right:
            s = left if re.fullmatch(r"\d+", compact) else s[: max(half, len(s) // 2)]
        elif _parecen_ref_serial_bnc_concatenados(digits_only):
            s = right if re.fullmatch(r"\d+", compact) else s[half:]

    s = _preferir_serial_mercantil_largo(s)
    return s[:100]


def clave_numero_operacion_canonico(raw: Any) -> str:
    """
    Clave para anti-duplicado entre Infopagos, Gmail y cartera.
    Normaliza espacios; en referencias solo numéricas ignora ceros a la izquierda.
    """
    from app.core.documento import normalize_documento

    s = sanitizar_numero_operacion_comprobante(raw)
    if not s:
        return ""
    norm = normalize_documento(s) or s
    compact = norm.replace(" ", "")
    if re.fullmatch(r"\d+", compact):
        d = compact.lstrip("0") or compact[-1:]
        return d
    return norm


def digitos_operacion_compacto(raw: Any) -> str:
    """Solo dígitos del comprobante, conservando ceros a la izquierda (sin inventar)."""
    s = sanitizar_numero_operacion_comprobante(raw).replace(" ", "")
    return s if s.isdigit() else ""


def _montos_coherentes_duplicado(a: Any, b: Any) -> bool:
    """False solo si ambos montos son parseables y difieren."""
    ma = parse_monto_comprobante(a)
    mb = parse_monto_comprobante(b)
    if ma is None or mb is None:
        return True
    return abs(ma - mb) < 0.015


def _cedulas_coherentes_duplicado(a: Any, b: Any) -> bool:
    """False solo si ambas cédulas tienen dígitos y difieren."""
    da = re.sub(r"\D", "", str(a or ""))
    db = re.sub(r"\D", "", str(b or ""))
    if not da or not db:
        return True
    na = da.lstrip("0") or da
    nb = db.lstrip("0") or db
    return na == nb


def _condiciones_sql_numero_operacion(column: Any, numero_operacion: str) -> list[Any]:
    """OR de condiciones SQL acotadas para prefiltrar candidatos a duplicado."""
    from app.services.pago_numero_documento import _candidatos_evasion_columna

    op = (numero_operacion or "").strip()
    compact = digitos_operacion_compacto(op)
    conds: list[Any] = []
    if op:
        conds.append(column == op)
    if compact:
        for cond, _tag in _candidatos_evasion_columna(column, compact):
            conds.append(cond)
    return conds


def _fechas_coherentes_duplicado(a: Any, b: Any) -> bool:
    fa = (str(a or "").strip()[:10] if a else "")
    fb = (str(b or "").strip()[:10] if b else "")
    if not fa or not fb:
        return True
    return fa == fb


def _contexto_coherente_duplicado(
    *,
    monto_a: Any = None,
    monto_b: Any = None,
    cedula_a: Any = None,
    cedula_b: Any = None,
    fecha_a: Any = None,
    fecha_b: Any = None,
) -> bool:
    if not _montos_coherentes_duplicado(monto_a, monto_b):
        return False
    if not _cedulas_coherentes_duplicado(cedula_a, cedula_b):
        return False
    if not _fechas_coherentes_duplicado(fecha_a, fecha_b):
        return False
    return True


def numeros_operacion_coinciden_o_evasion(
    a: Any,
    b: Any,
    *,
    monto_a: Any = None,
    monto_b: Any = None,
    cedula_a: Any = None,
    cedula_b: Any = None,
    fecha_a: Any = None,
    fecha_b: Any = None,
    exigir_contexto_sufijo_corto: bool = True,
) -> bool:
    """
    True si es el mismo comprobante: igualdad, sufijo truncado (0993 vs …0993)
    o prefijo/sufijo largo (7400874101194 vs 740087410119497).

    Para sufijos cortos (≤6 dígitos) exige coherencia de monto/cédula/fecha cuando
    ambos lados aportan el dato (reduce falsos positivos).
    """
    ca = digitos_operacion_compacto(a)
    cb = digitos_operacion_compacto(b)
    if ca and cb:
        if ca == cb:
            return _contexto_coherente_duplicado(
                monto_a=monto_a,
                monto_b=monto_b,
                cedula_a=cedula_a,
                cedula_b=cedula_b,
                fecha_a=fecha_a,
                fecha_b=fecha_b,
            )
        ca_canon = ca.lstrip("0") or ca[-1:]
        cb_canon = cb.lstrip("0") or cb[-1:]
        if ca_canon == cb_canon:
            return _contexto_coherente_duplicado(
                monto_a=monto_a,
                monto_b=monto_b,
                cedula_a=cedula_a,
                cedula_b=cedula_b,
                fecha_a=fecha_a,
                fecha_b=fecha_b,
            )
        short, long = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
        short_c, long_c = (
            (ca_canon, cb_canon) if len(ca_canon) <= len(cb_canon) else (cb_canon, ca_canon)
        )
        matched = False
        if len(short) < len(long):
            min_suffix = 4 if len(long) >= 12 else 5
            if (
                len(short) >= min_suffix
                and len(short) <= len(long) - 6
                and long.endswith(short)
            ):
                matched = True
            elif (
                len(long) >= 12
                and len(short) >= 3
                and len(short) <= len(long) - 6
                and long_c.endswith(short_c)
            ):
                matched = True
            elif len(short) >= 10 and (
                long.startswith(short) or long_c.startswith(short_c)
            ):
                matched = True
        if matched:
            if (
                exigir_contexto_sufijo_corto
                and len(short) <= 6
                and not _contexto_coherente_duplicado(
                    monto_a=monto_a,
                    monto_b=monto_b,
                    cedula_a=cedula_a,
                    cedula_b=cedula_b,
                    fecha_a=fecha_a,
                    fecha_b=fecha_b,
                )
            ):
                return False
            return True
        return False
    ka = clave_numero_operacion_canonico(a)
    kb = clave_numero_operacion_canonico(b)
    if not (ka and kb and ka == kb):
        return False
    return _contexto_coherente_duplicado(
        monto_a=monto_a,
        monto_b=monto_b,
        cedula_a=cedula_a,
        cedula_b=cedula_b,
        fecha_a=fecha_a,
        fecha_b=fecha_b,
    )


def referencia_duplicada_en_memoria_o_bd(
    referencia: str,
    *,
    monto: Any = None,
    cedula: Any = None,
    fecha: Any = None,
    lote_previo: Optional[list[dict]] = None,
    db: Any = None,
) -> bool:
    """
    True si la referencia ya apareció en el lote en curso (evasión) o en cartera/reportados.
    ``lote_previo`` es lista de dicts con claves r, m, c, f.
    """
    ref = (referencia or "").strip()
    if not ref:
        return False
    for prev in lote_previo or []:
        if numeros_operacion_coinciden_o_evasion(
            ref,
            prev.get("r"),
            monto_a=monto,
            monto_b=prev.get("m"),
            cedula_a=cedula,
            cedula_b=prev.get("c"),
            fecha_a=fecha,
            fecha_b=prev.get("f"),
        ):
            return True
    if db is not None:
        from app.services.pago_numero_documento import numero_documento_ya_registrado

        if numero_documento_ya_registrado(db, ref):
            return True
        from app.services.cobros.pago_reportado_documento import (
            numero_operacion_colisiona_reportado_activo,
        )

        if numero_operacion_colisiona_reportado_activo(db, ref):
            return True
    return False


def normalizar_campos_gemini_gmail(fields: Dict[str, str]) -> Dict[str, str]:
    """Normaliza monto/fecha/referencia extraidos por Gemini antes de validar plantillas Gmail."""
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    ref = fecha_hoy_caracas()
    out = dict(fields)
    nr = (out.get("numero_referencia") or "").strip()
    nr_raw_para_fecha = nr
    if nr and nr.upper() != PAGOS_NA:
        banco = (out.get("banco") or "").strip()
        inst = "" if banco.upper() == PAGOS_NA else banco
        cleaned = sanitizar_numero_operacion_comprobante(nr)
        cleaned = corregir_numero_operacion_mercantil(
            cleaned,
            institucion=inst,
            texto_auxiliar=nr,
        )
        cleaned = corregir_numero_operacion_bnc(
            cleaned,
            institucion=inst,
            texto_auxiliar=nr,
        )
        out["numero_referencia"] = cleaned if cleaned else PAGOS_NA
        nr = out["numero_referencia"]
    fp = (out.get("fecha_pago") or "").strip()
    if fp and fp.upper() != PAGOS_NA:
        norm = fecha_comprobante_a_ddmmyyyy(fp, ref)
        out["fecha_pago"] = norm if norm else PAGOS_NA
    elif (not fp or fp.upper() == PAGOS_NA) and nr_raw_para_fecha and nr_raw_para_fecha.upper() != PAGOS_NA:
        inferida = inferir_fecha_pago_desde_numero_operacion(nr_raw_para_fecha, ref)
        if inferida:
            out["fecha_pago"] = inferida
    mo = (out.get("monto") or "").strip()
    if mo and mo.upper() not in (PAGOS_NA, "NR"):
        fm = monto_comprobante_a_excel(mo)
        out["monto"] = fm if fm else PAGOS_NA
    return out
