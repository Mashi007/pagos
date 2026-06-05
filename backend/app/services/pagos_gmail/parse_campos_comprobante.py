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


def _corregir_monto_ocr_tres_digitos(n: float) -> float:
    """
    Mercantil / ventanilla: OCR a veces lee ``96,00`` como ``969`` o ``965`` (coma+ceros).
    Solo aplica a enteros de 3 cifras con cola 0/5/9 y base XX plausible de cuota (30-250).
    """
    if n != int(n) or n < 100 or n >= 1000:
        return n
    s = str(int(n))
    if len(s) != 3 or s[2] not in "059":
        return n
    base = int(s[:2])
    if 30 <= base <= 250:
        return float(base)
    return n


def parse_monto_comprobante(
    val: Any, *, moneda: Optional[str] = None
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
        return round(n, 2)

    s = raw
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


def normalizar_campos_gemini_gmail(fields: Dict[str, str]) -> Dict[str, str]:
    """Normaliza monto/fecha extraidos por Gemini antes de validar plantillas Gmail."""
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    ref = fecha_hoy_caracas()
    out = dict(fields)
    fp = (out.get("fecha_pago") or "").strip()
    if fp and fp.upper() != PAGOS_NA:
        norm = fecha_comprobante_a_ddmmyyyy(fp, ref)
        out["fecha_pago"] = norm if norm else PAGOS_NA
    mo = (out.get("monto") or "").strip()
    if mo and mo.upper() not in (PAGOS_NA, "NR"):
        fm = monto_comprobante_a_excel(mo)
        out["monto"] = fm if fm else PAGOS_NA
    return out
