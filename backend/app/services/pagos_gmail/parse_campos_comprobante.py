"""
Parsers compartidos de monto y fecha desde texto Gemini / OCR (escáner Infopagos y Gmail).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

PAGOS_NA = "NA"

# Anti-duplicado comprobantes: misma longitud, R > 70% y Hamming acotado (error OCR, no serial distinto).
UMBRAL_SIMILITUD_DIGITOS_DUPLICADO = 0.70
MAX_HAMMING_DUPLICADO_OCR_SERIAL_LARGO = 1  # n >= 10: solo 1 dígito OCR (ej. 12/13)
MAX_HAMMING_DUPLICADO_OCR_SERIAL_CORTO = 1  # n < 10
MIN_LONGITUD_DUPLICADO_SIMILITUD = 3

REGLA_DUPLICADO_NUMERO_OPERACION_PROMPT = """
REGLA SISTEMA — DUPLICADO DE NÚMERO DE OPERACIÓN / SERIAL / REFERENCIA (solo al COMPARAR dos valores ya extraídos; nunca para inventar dígitos al transcribir):
  Dos valores se consideran EL MISMO documento — duplicado — si el backend verifica **todas** estas condiciones:
  (1) Misma longitud de dígitos (n ≥ 3).
  (2) Tasa de coincidencia posición a posición R = (coincidencias / n) **estrictamente** > 0,70.
  (3) Distancia de Hamming H = (dígitos distintos) ≤ 1 (un solo dígito OCR dudoso; nunca dos o más).
  (4) Si hay monto, cédula o fecha en ambos lados y alguno difiere → NO duplicado.
  Ejemplo duplicado: 7400874101194 y 7400874101195 (n=13, R=12/13, H=1).
  Ejemplo NO duplicado: 7400874101194 y 7400874101284 (H=2).
  Al transcribir: copia fiel al papel; no completes dígitos dudosos para “acercarte” al 70%.
""".strip()


def hamming_digitos_misma_longitud(ca: str, cb: str) -> int:
    """Cantidad de posiciones con dígito distinto (misma longitud)."""
    if not ca or not cb or len(ca) != len(cb):
        return max(len(ca or ""), len(cb or ""))
    return sum(1 for i in range(len(ca)) if ca[i] != cb[i])


def _diferencias_solo_en_sufijo(ca: str, cb: str, *, tail: int) -> bool:
    """True si cada posición distinta está en el sufijo de longitud `tail`."""
    n = len(ca)
    if n != len(cb) or n == 0:
        return False
    tail = min(n, max(1, tail))
    start = n - tail
    for i in range(n):
        if ca[i] != cb[i] and i < start:
            return False
    return True


def ratio_digitos_misma_secuencia(ca: str, cb: str) -> float:
    """Proporción de dígitos iguales en la misma posición (0..1). Requiere misma longitud."""
    if not ca or not cb or len(ca) != len(cb):
        return 0.0
    return sum(1 for i in range(len(ca)) if ca[i] == cb[i]) / len(ca)


def duplicado_digitos_misma_longitud_mas_umbral(
    ca: str,
    cb: str,
    *,
    umbral: float = UMBRAL_SIMILITUD_DIGITOS_DUPLICADO,
) -> bool:
    """
    True si misma longitud, R > umbral y H acotado (OCR 1–2 dígitos en sufijo, no seriales distintos).

    Con solo R > 0,70 y n=13 se permitirían H=3 (falsos positivos); por eso H ≤ 2 y sufijo si H ≥ 2.
    """
    if not ca or not cb or len(ca) != len(cb) or len(ca) < MIN_LONGITUD_DUPLICADO_SIMILITUD:
        return False
    n = len(ca)
    ratio = ratio_digitos_misma_secuencia(ca, cb)
    if ratio <= umbral:
        return False
    hamming = hamming_digitos_misma_longitud(ca, cb)
    max_h = (
        MAX_HAMMING_DUPLICADO_OCR_SERIAL_LARGO
        if n >= 10
        else MAX_HAMMING_DUPLICADO_OCR_SERIAL_CORTO
    )
    if hamming > max_h:
        return False
    return True


# OCR legibilidad dígito a dígito (fecha 8 dígitos, serial/ref longitud variable n).
UMBRAL_CONFIANZA_DIGITO_OCR = 0.90
MIN_PROP_DIGITOS_INEQUIVOCOS_OCR = 0.875  # L ≥ 0,875 → máx. ⌊(1−0,875)·n⌋ dígitos ambiguos

# Alias fecha (8 dígitos DDMMYYYY)
UMBRAL_CONFIANZA_DIGITO_FECHA_OCR = UMBRAL_CONFIANZA_DIGITO_OCR
MIN_PROP_DIGITOS_INEQUIVOCOS_FECHA = MIN_PROP_DIGITOS_INEQUIVOCOS_OCR
MIN_DIGITOS_INEQUIVOCOS_FECHA = 7


def min_digitos_inequivocos_ocr(total_digitos: int) -> int:
    """Mínimo de dígitos con cᵢ ≥ umbral para no declarar borroso (⌈n·0,875⌉)."""
    if total_digitos < 1:
        return 1
    import math

    return max(1, math.ceil(total_digitos * MIN_PROP_DIGITOS_INEQUIVOCOS_OCR))


def digitos_ocr_legibilidad_insuficiente(
    digitos_inequivocos: int,
    total_digitos: int,
    *,
    dos_lecturas_distintas_plausibles: bool = False,
) -> bool:
    """
    True si L = digitos_inequivocos/n < 0,875 o hay dos lecturas plausibles distintas.
    Usado por fecha (n=8) y serial/ref (n variable).
    """
    if total_digitos < 1:
        return True
    if dos_lecturas_distintas_plausibles:
        return True
    return (digitos_inequivocos / total_digitos) < MIN_PROP_DIGITOS_INEQUIVOCOS_OCR


REGLA_FECHA_BORROSA_REVISION_MANUAL_PROMPT = """
CRITERIO MATEMÁTICO — FECHA BORROSA (revisión manual; NO inventar):
  La fecha DD/MM/AAAA = 8 dígitos d₁…d₈. Para cada posición i, confianza visual cᵢ ∈ [0,1] (solo evaluación interna; no reportes cᵢ en JSON).

  Definiciones:
  - Dígito inequívoco: cᵢ ≥ 0,90.
  - A = {{ i | cᵢ < 0,90 }}, L = (8 − |A|) / 8.

  BORROSA → vacía/NA si **cualquiera**:
    (a) L < 0,875  (|A| ≥ 2)
    (b) |A| ≥ 1 y ≥2 candidatos distintos dan fechas calendario válidas diferentes
    (c) Dos lecturas completas D₁ ≠ D₂ válidas y plausibles
    (d) DD/MM vs MM/DD ambos válidos y distintos

  Si no borrosa: devuelve la **única** fecha con los 8 dígitos inequívocos.

  **Anti-alucinación (obligatorio):**
  - Prohibido inferir desde correo, metadata, hoy o serial 740087… sin bloque DCME.
  - Si declaras borrosa en `notas`, `fecha_pago`/`fecha_deposito` debe ir vacía/NA (nunca rellenar después).
  - El backend **rechaza** fechas con ambigüedad DD/MM vs MM/DD y **no** infiere si `notas` indican borrosura.
  - Inferencia automática solo desde bloque DCME con regex fija …-YYYYMMDD-… (8 dígitos inequívocos en texto).

  Salida: escáner/compare → ""; Gmail/cobranza → "NA". Monto/ref legibles: no bajar a "ninguno" solo por fecha borrosa.
""".strip()


REGLA_MONTO_BORROSO_REVISION_MANUAL_PROMPT = """
CRITERIO MATEMÁTICO — MONTO BORROSO (revisión manual; NO inventar ni truncar):
  El monto impreso se modela dígito a dígito (parte entera + decimales si aparecen). Para cada posición i, confianza visual cᵢ ∈ [0,1] (no reportes cᵢ en JSON).

  Definiciones (mismas que fecha/serial):
  - Dígito inequívoco: cᵢ ≥ 0,90.
  - A = {{ i | cᵢ < 0,90 }}, L = (n − |A|) / n (n = cantidad de dígitos del monto leído).

  BORROSO → null/NA si **cualquiera**:
    (a) L < 0,875
    (b) |A| ≥ 1 y ≥2 lecturas plausibles distintas del mismo monto (ej. 600 vs 60 por cero final dudoso; 96 vs 66)
    (c) Orientación lateral/boca abajo impide contar dígitos con certeza tras rotar mentalmente
    (d) Rasgos similares (0/O, 6/8, 1/7, 5/S) dejan ambiguo el valor

  **Ceros finales (obligatorio):**
  - Prohibido omitir ceros finales del entero: `600,00` / `600 $` / `600.00` → **600**, nunca **60** ni **6**.
  - `60,00` solo si en el papel hay **exactamente dos** cifras antes de la coma/punto decimal.

  Si declaras monto borroso en `notas`, `monto` = null o "NA". El backend no “corrige” multiplicando por 10.
""".strip()


REGLA_SERIAL_BORROSO_REVISION_MANUAL_PROMPT = """
CRITERIO MATEMÁTICO — SERIAL / REF / Nº OPERACIÓN BORROSO (revisión manual; NO inventar):
  El serial (solo dígitos, longitud n ≥ 3) se modela como d₁…dₙ. Para cada posición i, confianza visual cᵢ ∈ [0,1] (no reportes cᵢ en JSON).

  Definiciones (mismas que fecha):
  - Dígito inequívoco: cᵢ ≥ 0,90.
  - A = {{ i | cᵢ < 0,90 }}, L = (n − |A|) / n.

  BORROSO → vacío/NA si **cualquiera**:
    (a) L < 0,875  (equivalente: digitos_inequivocos < ⌈n × 0,875⌉)
    (b) |A| ≥ 1 y ≥2 candidatos distintos por dígito producen **dos seriales plausibles distintos** (lecturas D₁ ≠ D₂)
    (c) Longitud esperada del formato no alcanzable sin adivinar (ej. Mercantil Serial **740087** incompleto: n < 15 con dígitos dudosos)
    (d) Mezcla dígitos de Ref y Serial, repetición concatenada, o fragmento DCME usado como serial

  Si no borroso: devuelve la **única** ristra de n dígitos inequívocos, conservando ceros a la izquierda.

  **Anti-alucinación (obligatorio):**
  - Prohibido completar dígitos faltantes, truncar o alargar para “llegar” a 15/8/9 cifras.
  - Si declaras serial borroso en `notas`, `numero_operacion`/`numero_referencia` = "" o "NA".
  - El backend **no** aplica correcciones Mercantil/BNC ni rescate desde texto auxiliar si `notas` indican serial borroso.
  - Duplicado (>70% + H≤1) aplica solo al **comparar** dos valores ya leídos; no para rellenar huecos.

  Salida: escáner/compare → ""; Gmail/cobranza → "NA". Monto/fecha legibles: no bajar a "ninguno" solo por serial borroso.
""".strip()


_FECHA_BORROSA_NOTAS_RE = re.compile(
    r"(?i)(fecha\s+borros|L\s*<\s*0[,.]875|no\s+distinguible|revisi[oó]n\s+manual.*fecha|fecha.*revisi[oó]n\s+manual)"
)

_SERIAL_BORROSO_NOTAS_RE = re.compile(
    r"(?i)(serial\s+borros|referencia\s+borros|n[uú]mero\s+de\s+operaci[oó]n\s+borros|"
    r"ref\s+borros|numero_referencia\s+borros|L\s*<\s*0[,.]875.*serial|"
    r"serial.*L\s*<\s*0[,.]875|revisi[oó]n\s+manual.*serial|serial.*revisi[oó]n\s+manual)"
)

_MONTO_BORROSO_NOTAS_RE = re.compile(
    r"(?i)(monto\s+borros|importe\s+borros|cantidad\s+borros|"
    r"L\s*<\s*0[,.]875.*monto|monto.*L\s*<\s*0[,.]875|"
    r"revisi[oó]n\s+manual.*monto|monto.*revisi[oó]n\s+manual|"
    r"cero\s+final\s+dudoso|600\s+vs\s+60|truncad[oa].*monto)"
)


def gemini_indico_fecha_borrosa(fecha_raw: Any, notas: Any) -> bool:
    """True si Gemini marcó borrosura: descartar su fecha y no inferir desde texto libre."""
    notas_s = str(notas or "").strip()
    if notas_s and _FECHA_BORROSA_NOTAS_RE.search(notas_s):
        return True
    return False


def gemini_indico_serial_borroso(serial_raw: Any, notas: Any) -> bool:
    """True si Gemini marcó serial/ref borroso: no usar ni corregir desde texto auxiliar."""
    notas_s = str(notas or "").strip()
    if notas_s and _SERIAL_BORROSO_NOTAS_RE.search(notas_s):
        return True
    return False


def gemini_indico_monto_borroso(monto_raw: Any, notas: Any) -> bool:
    """True si Gemini marcó monto borroso o ambiguo (ej. 600 vs 60): no usar el valor."""
    notas_s = str(notas or "").strip()
    if notas_s and _MONTO_BORROSO_NOTAS_RE.search(notas_s):
        return True
    return False


def monto_ocr_borrosa_revision_manual(
    *,
    digitos_inequivocos: int,
    total_digitos: int,
    dos_montos_plausibles_distintos: bool = False,
) -> bool:
    """True si el monto debe dejarse vacío/NA (mismo criterio L < 0,875 que fecha/serial)."""
    return digitos_ocr_legibilidad_insuficiente(
        digitos_inequivocos,
        total_digitos,
        dos_lecturas_distintas_plausibles=dos_montos_plausibles_distintos,
    )


def parse_fecha_comprobante_escaner(
    val: Any, ref_hoy: Optional[date] = None
) -> Optional[date]:
    """Parseo de fecha post-Gemini: rechaza ambigüedad DD/MM vs MM/DD."""
    return parse_fecha_comprobante(val, ref_hoy, conservador=True)


def fecha_ocr_borrosa_revision_manual(
    *,
    digitos_inequivocos: int,
    total_digitos: int = 8,
    dos_fechas_validas_distintas: bool = False,
    digitos_ambiguos_afectan_calendario: bool = False,
) -> bool:
    """True si la fecha debe dejarse vacía/NA (L < 0,875 u ambigüedad calendario)."""
    return digitos_ocr_legibilidad_insuficiente(
        digitos_inequivocos,
        total_digitos,
        dos_lecturas_distintas_plausibles=(
            dos_fechas_validas_distintas or digitos_ambiguos_afectan_calendario
        ),
    )


def serial_ocr_borrosa_revision_manual(
    *,
    digitos_inequivocos: int,
    total_digitos: int,
    dos_seriales_plausibles_distintos: bool = False,
) -> bool:
    """True si el serial debe dejarse vacío/NA (mismo criterio L < 0,875 que fecha)."""
    return digitos_ocr_legibilidad_insuficiente(
        digitos_inequivocos,
        total_digitos,
        dos_lecturas_distintas_plausibles=dos_seriales_plausibles_distintos,
    )


def ocr_borroso_indicado_en_texto(texto: Any) -> bool:
    """True si un comentario/notas menciona fecha, serial o monto borroso (revisión manual)."""
    t = str(texto or "").strip()
    if not t:
        return False
    return bool(
        _FECHA_BORROSA_NOTAS_RE.search(t)
        or _SERIAL_BORROSO_NOTAS_RE.search(t)
        or _MONTO_BORROSO_NOTAS_RE.search(t)
    )


def _procesar_serial_ocr_post_gemini(
    raw: Any,
    *,
    notas: str,
    institucion: str,
) -> str:
    """Sanitiza y corrige serial/ref si no está marcado borroso."""
    s = str(raw or "").strip()
    if not s or s.upper() in ("", PAGOS_NA, "N/A"):
        return ""
    cleaned = sanitizar_numero_operacion_comprobante(s)[:100]
    aux = f"{s}\n{notas}"
    inst = (institucion or "").strip()
    cleaned = corregir_numero_operacion_mercantil(
        cleaned, institucion=inst, texto_auxiliar=aux
    )[:100]
    cleaned = corregir_numero_operacion_bnc(
        cleaned, institucion=inst, texto_auxiliar=aux
    )[:100]
    return cleaned


def _inferir_fecha_desde_dcme_blob(blob_dcme: str, ref_hoy: date) -> Optional[date]:
    """Fecha Mercantil desde bloque DCME …-YYYYMMDD-… en texto auxiliar."""
    dcme = extraer_codigo_dcme_mercantil_en_texto(blob_dcme)
    if not dcme:
        return None
    f_inf = inferir_fecha_pago_mercantil_desde_texto(dcme, ref_hoy)
    if not f_inf:
        return None
    return parse_fecha_comprobante(f_inf, ref_hoy)


def _resolver_fecha_ocr_post_gemini(
    fecha_raw: Any,
    *,
    notas: str,
    ref_hoy: date,
    blob_dcme: str,
    inferir_fecha_dcme: bool,
    rechazar_fecha_hoy_sospechosa: bool = False,
) -> Optional[date]:
    """Fecha conservadora + inferencia DCME; escáner rechaza «hoy» sin DCME (alucinación Gemini)."""
    if gemini_indico_fecha_borrosa(fecha_raw, notas):
        return None

    f_dcme: Optional[date] = None
    if inferir_fecha_dcme:
        f_dcme = _inferir_fecha_desde_dcme_blob(blob_dcme, ref_hoy)
        if f_dcme is None and fecha_raw and str(fecha_raw).strip():
            f_dcme = _inferir_fecha_desde_dcme_blob(str(fecha_raw), ref_hoy)
    if f_dcme is not None:
        return f_dcme

    parsed: Optional[date] = None
    if fecha_raw and str(fecha_raw).strip():
        parsed = parse_fecha_comprobante_escaner(fecha_raw, ref_hoy)

    if parsed is None:
        return None
    if rechazar_fecha_hoy_sospechosa and parsed == ref_hoy:
        return None
    return parsed


def aplicar_reglas_ocr_post_gemini(
    datos: Dict[str, Any],
    *,
    perfil: str = "escaner",
    ref_hoy: Optional[date] = None,
    institucion: str = "",
    inferir_fecha_dcme: bool = True,
) -> Dict[str, Any]:
    """
    Post-proceso unificado tras Gemini: borrosura fecha/serial (L < 0,875), parse conservador,
    sin corrección de serial si notas indican borrosura, inferencia de fecha solo por DCME.

    Perfiles:
    - escaner: fecha_pago → date|None, numero_operacion → str
    - gmail: fecha_pago → dd/mm/yyyy|NA, numero_referencia → str|NA
    - cobranza: fecha_deposito, numero_deposito, numero_documento → str|NA
    """
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    if ref_hoy is None:
        ref_hoy = fecha_hoy_caracas()

    out = dict(datos)
    notas = str(datos.get("notas") or "").strip()
    perfil_norm = (perfil or "escaner").strip().lower()

    if perfil_norm == "cobranza":
        inst = institucion or str(datos.get("nombre_banco") or "")
        fd_raw = datos.get("fecha_deposito")
        if gemini_indico_fecha_borrosa(fd_raw, notas):
            out["fecha_deposito"] = PAGOS_NA
        elif fd_raw and str(fd_raw).strip().upper() not in ("", PAGOS_NA, "N/A"):
            fd = _resolver_fecha_ocr_post_gemini(
                fd_raw,
                notas=notas,
                ref_hoy=ref_hoy,
                blob_dcme=notas,
                inferir_fecha_dcme=False,
            )
            out["fecha_deposito"] = fd.strftime("%d/%m/%Y") if fd else PAGOS_NA
        for key in ("numero_deposito", "numero_documento"):
            raw = str(datos.get(key) or "").strip()
            if gemini_indico_serial_borroso(raw, notas):
                out[key] = PAGOS_NA
            elif raw and raw.upper() not in (PAGOS_NA, "N/A"):
                cleaned = _procesar_serial_ocr_post_gemini(
                    raw, notas=notas, institucion=inst
                )
                out[key] = cleaned if cleaned else PAGOS_NA
        out["_ocr_serial_borroso"] = any(
            gemini_indico_serial_borroso(datos.get(k), notas)
            for k in ("numero_deposito", "numero_documento")
        )
        out["_ocr_fecha_borroso"] = gemini_indico_fecha_borrosa(
            datos.get("fecha_deposito"), notas
        )
        return out

    if perfil_norm == "gmail":
        serial_key = "numero_referencia"
        inst = institucion or str(datos.get("banco") or "")
        vacio_serial = PAGOS_NA
    else:
        serial_key = "numero_operacion"
        inst = institucion or str(datos.get("institucion_financiera") or "")
        vacio_serial = ""

    raw_serial = str(datos.get(serial_key) or "").strip()
    serial_borroso = gemini_indico_serial_borroso(raw_serial, notas)
    if serial_borroso:
        out[serial_key] = vacio_serial
        cleaned_serial = ""
    elif raw_serial and raw_serial.upper() not in (PAGOS_NA, "N/A"):
        cleaned_serial = _procesar_serial_ocr_post_gemini(
            raw_serial, notas=notas, institucion=inst
        )
        out[serial_key] = (
            cleaned_serial if cleaned_serial else vacio_serial or PAGOS_NA
        )
    else:
        cleaned_serial = ""

    fecha_raw = datos.get("fecha_pago")
    blob_dcme = f"{raw_serial}\n{notas}\n{fecha_raw or ''}"
    fecha_parsed = _resolver_fecha_ocr_post_gemini(
        fecha_raw,
        notas=notas,
        ref_hoy=ref_hoy,
        blob_dcme=blob_dcme,
        inferir_fecha_dcme=inferir_fecha_dcme and not serial_borroso,
        rechazar_fecha_hoy_sospechosa=perfil_norm == "escaner",
    )
    if perfil_norm == "gmail":
        if gemini_indico_fecha_borrosa(fecha_raw, notas):
            out["fecha_pago"] = PAGOS_NA
        elif fecha_parsed:
            out["fecha_pago"] = fecha_parsed.strftime("%d/%m/%Y")
        elif fecha_raw and str(fecha_raw).strip().upper() not in ("", PAGOS_NA, "N/A"):
            out["fecha_pago"] = PAGOS_NA
    else:
        out["fecha_pago"] = fecha_parsed

    monto_raw = datos.get("monto")
    monto_borroso = gemini_indico_monto_borroso(monto_raw, notas)
    if monto_borroso:
        out["monto"] = vacio_serial if perfil_norm == "gmail" else None
    elif monto_raw is not None and str(monto_raw).strip():
        out["monto"] = monto_raw

    out["_ocr_serial_borroso"] = serial_borroso
    out["_ocr_fecha_borroso"] = gemini_indico_fecha_borrosa(fecha_raw, notas)
    out["_ocr_monto_borroso"] = monto_borroso
    return out


# Montos escaneados/reportados >= este valor van a revisión manual (cualquier moneda/medio).
MONTO_UMBRAL_REVISION_MANUAL = 1000.0

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


def _fecha_ambigua_dd_mm(d: int, mo: int, y: int) -> bool:
    """True si día y mes intercambiables producen dos fechas calendario válidas distintas."""
    if d == mo or d > 12 or mo > 12:
        return False
    ok_dmy = ok_mdy = False
    try:
        date(y, mo, d)
        ok_dmy = True
    except ValueError:
        pass
    try:
        date(y, d, mo)
        ok_mdy = True
    except ValueError:
        pass
    return ok_dmy and ok_mdy


def _parse_fecha_dmy_parts(
    d: int, mo: int, y: int, ref_hoy: date, *, conservador: bool = False
) -> Optional[date]:
    if conservador and _fecha_ambigua_dd_mm(d, mo, y):
        return None
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


def _parse_fecha_compacta_6(digits: str, ref_hoy: date, *, conservador: bool = False) -> Optional[date]:
    if len(digits) != 6 or not digits.isdigit():
        return None
    dd, mm, yy = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    cand_ddmmyy = _parse_fecha_dmy_parts(
        dd, mm, _year_from_two_digits(yy), ref_hoy, conservador=conservador
    )
    yy2, mo2, d2 = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    cand_yymmdd: Optional[date] = None
    try:
        cand_yymmdd = date(_year_from_two_digits(yy2), mo2, d2)
    except ValueError:
        cand_yymmdd = None
    if cand_yymmdd and not fecha_plausible(cand_yymmdd, ref_hoy):
        cand_yymmdd = None
    return _pick_fecha_candidata([cand_ddmmyy, cand_yymmdd], ref_hoy)


def parse_fecha_comprobante(
    val: Any, ref_hoy: Optional[date] = None, *, conservador: bool = False
) -> Optional[date]:
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
            parsed = _parse_fecha_dmy_parts(d, m, y, ref_hoy, conservador=conservador)
            if parsed:
                return parsed
    except (ValueError, TypeError):
        pass
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
    if m:
        parsed = _parse_fecha_dmy_parts(
            int(m.group(1)), int(m.group(2)), int(m.group(3)), ref_hoy, conservador=conservador
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
            conservador=conservador,
        )
        if parsed:
            return parsed
    digits_only = re.sub(r"\D", "", s)
    if len(digits_only) == 6:
        parsed = _parse_fecha_compacta_6(digits_only, ref_hoy, conservador=conservador)
        if parsed:
            return parsed
    m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m_iso:
        parsed = _parse_fecha_dmy_parts(
            int(m_iso.group(3)),
            int(m_iso.group(2)),
            int(m_iso.group(1)),
            ref_hoy,
            conservador=conservador,
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
            conservador=conservador,
        )
        if parsed:
            return parsed
    m_lat = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s)
    if m_lat:
        parsed = _parse_fecha_dmy_parts(
            int(m_lat.group(1)),
            int(m_lat.group(2)),
            int(m_lat.group(3)),
            ref_hoy,
            conservador=conservador,
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
    """True si el monto parseado es >= umbral de revisión manual (sin distinguir moneda)."""
    n = _monto_numerico_para_revision(val, moneda=moneda)
    if n is None:
        return False
    return n >= MONTO_UMBRAL_REVISION_MANUAL


def mensaje_monto_revision_manual(val: Any, *, moneda: Optional[str] = None) -> str:
    n = _monto_numerico_para_revision(val, moneda=moneda) or 0.0
    return (
        f"El monto ({n:,.2f}) es igual o superior a {MONTO_UMBRAL_REVISION_MANUAL:,.0f}; "
        "requiere revisión manual antes de guardar o aplicar."
    )


def fecha_pago_es_futura_revision_manual(fecha_pago: date) -> bool:
    """True si la fecha de pago es posterior a hoy (America/Caracas)."""
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    return fecha_pago > fecha_hoy_caracas()


def mensaje_fecha_futura_revision_manual(fecha_pago: date) -> str:
    return (
        f"Fecha de pago ({fecha_pago.isoformat()}) es futura; "
        "requiere revisión manual antes de autoconciliar o aplicar."
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


def extraer_codigo_dcme_mercantil_en_texto(texto: str) -> str:
    """Código del recuadro superior Mercantil (ej. 9264-20260618-115409-DCME-5574-A)."""
    m = _MERCANTIL_DCME_EN_TEXTO_RE.search((texto or "").strip())
    return m.group(0) if m else ""


def inferir_fecha_pago_mercantil_desde_texto(
    texto: str,
    ref_hoy: Optional[date] = None,
) -> str:
    """
    Fecha operación Mercantil: 2º bloque YYYYMMDD del código DCME en el recuadro
  superior de la tira (no del Serial 740087…).
    """
    dcme = extraer_codigo_dcme_mercantil_en_texto(texto)
    if dcme:
        return inferir_fecha_pago_desde_numero_operacion(dcme, ref_hoy)
    return ""


_LABEL_NUM_OP_PREFIX_RE = re.compile(
    r"^(?:(?:serial|ref(?:\.|\s|:)?|referencia|operaci[oó]n|secuencial|"
    r"n[ºo°°]\.?\s*(?:operaci[oó]n|documento|control|ref)?)\s*[:.]?\s*)+",
    re.IGNORECASE,
)

_MERCANTIL_SERIAL_LARGO_RE = re.compile(r"7400\d{9,}")
_MERCANTIL_SERIAL_15_RE = re.compile(r"740087\d{9}")
MERCANTIL_SERIAL_DIGITOS = 15
_SERIAL_ETIQUETADO_RE = re.compile(r"(?i)\bserial\s*[:.]?\s*(\d{6,30})")
_REF_ETIQUETADO_RE = re.compile(r"(?i)\bref(?:\.|\s|:)?\s*(\d{6,18})")
_MERCANTIL_DCME_GUIONADO_RE = re.compile(
    r"^\d{3,5}-\d{8}-\d{6}-DCME-\d{3,5}-[A-Z]$",
    re.IGNORECASE,
)
_MERCANTIL_DCME_EN_TEXTO_RE = re.compile(
    r"\d{3,5}-\d{8}-\d{6}-DCME-\d{3,5}-[A-Z]",
    re.IGNORECASE,
)


def _es_institucion_mercantil(institucion: str) -> bool:
    return "mercantil" in (institucion or "").strip().lower()


def digitos_serial_mercantil(num_op: str) -> str:
    return re.sub(r"\D", "", (num_op or "").strip())


def es_serial_mercantil_740087(num_op: str) -> bool:
    """True si parece serial Mercantil (prefijo 740087, longitud plausible)."""
    d = digitos_serial_mercantil(num_op)
    return bool(d.startswith("740087") and len(d) >= 12)


def longitud_serial_mercantil_valida(num_op: str) -> bool:
    """Serial Mercantil canónico: exactamente 15 dígitos empezando por 740087."""
    d = digitos_serial_mercantil(num_op)
    return len(d) == MERCANTIL_SERIAL_DIGITOS and d.startswith("740087")


def serial_mercantil_requiere_rescate(num_op: str) -> bool:
    """
    OCR truncó o mezcló dígitos (típ. 13-14 cifras en tira vertical).
    Dispara segunda pasada Gemini con plantilla Mercantil.
    """
    d = digitos_serial_mercantil(num_op)
    if not d.startswith("740087"):
        return False
    return len(d) != MERCANTIL_SERIAL_DIGITOS


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
    """Serial Mercantil (740087 + 9 dígitos = 15) desde cualquier fragmento OCR."""
    if not texto:
        return ""
    compact = _deduplicar_digitos_repetidos(re.sub(r"\D", "", texto))
    if not compact:
        return ""
    m15 = _MERCANTIL_SERIAL_15_RE.search(compact)
    if m15:
        return m15.group(0)
    runs = _MERCANTIL_SERIAL_LARGO_RE.findall(compact)
    if not runs:
        return ""
    quince = [r for r in runs if longitud_serial_mercantil_valida(r)]
    if quince:
        return quince[0]
    # No devolver 13-14 dígitos truncados: provocan rescate o revisión manual.
    return ""


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
    if (
        op_norm
        and es_serial_mercantil_740087(op_norm)
        and not longitud_serial_mercantil_valida(op_norm)
    ):
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


# Sufijo admin Visto (carga masiva / Cobros): _A#### / _P#### — misma convención que control 5.
_SUFIJO_VISTO_ADMIN_NUM_OP_RE = re.compile(r"_([AP]\d{4})$", re.IGNORECASE)


def _separar_sufijo_visto_admin_num_op(s: str) -> tuple[str, str]:
    """Devuelve (base, sufijo) donde sufijo es '' o '_A0042' / '_P1234'."""
    t = (s or "").strip()
    m = _SUFIJO_VISTO_ADMIN_NUM_OP_RE.search(t)
    if not m:
        return t, ""
    return t[: m.start()].rstrip(), m.group(0)


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

    # Visto admin: no aplicar extracción Mercantil 740087… sobre el token _A####/_P####.
    s, sufijo_visto_admin = _separar_sufijo_visto_admin_num_op(s)

    serial_etiquetado = extraer_serial_etiquetado_bnc(s)
    if serial_etiquetado and re.search(r"(?i)\bserial\b", s):
        out = serial_etiquetado[:100]
        if sufijo_visto_admin:
            max_base = max(0, 100 - len(sufijo_visto_admin))
            if len(out) > max_base:
                out = out[:max_base]
            out = f"{out}{sufijo_visto_admin}"
        return out[:100]

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
    if sufijo_visto_admin:
        max_base = max(0, 100 - len(sufijo_visto_admin))
        if len(s) > max_base:
            s = s[:max_base]
        s = f"{s}{sufijo_visto_admin}"
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
    True si es el mismo comprobante: igualdad, >70% dígitos en misma longitud/secuencia,
    sufijo truncado (0993 vs …0993) o prefijo/sufijo largo (7400874101194 vs 740087410119497).

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
        if duplicado_digitos_misma_longitud_mas_umbral(ca, cb):
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
    out = aplicar_reglas_ocr_post_gemini(dict(fields), perfil="gmail")
    out.pop("_ocr_serial_borroso", None)
    out.pop("_ocr_fecha_borroso", None)
    out.pop("_ocr_monto_borroso", None)
    mo = (out.get("monto") or "").strip()
    if mo and mo.upper() not in (PAGOS_NA, "NR"):
        fm = monto_comprobante_a_excel(mo)
        out["monto"] = fm if fm else PAGOS_NA
    return out
