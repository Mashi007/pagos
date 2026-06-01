"""
Helpers: nombre de carpeta por fecha, mime types, extracción de email del remitente.
"""
import re
from datetime import date, datetime
from typing import Optional

MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

MIME_BY_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "heic": "image/heic",
    "pdf": "application/pdf",
}

EXTENSIONS_ALLOWED = set(MIME_BY_EXT.keys())

# Mime types que consideramos imagen o PDF para extracción (adjuntos + cuerpo)
MIME_IMAGE_OR_PDF = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/heic",
    "application/pdf",
}

def ext_for_mime(mime: str) -> str:
    """Extensión por defecto para un mime type (para nombres de archivo inline)."""
    m = (mime or "").lower()
    rev = {v: k for k, v in MIME_BY_EXT.items()}
    return rev.get(m, "jpg" if m.startswith("image/") else "bin")


def get_folder_name_from_date(d: datetime) -> str:
    """Nombre de carpeta: 8Marzo2026, 15Abril2026."""
    day = d.day
    month_name = MESES_ES[d.month - 1]
    year = d.year
    return f"{day}{month_name}{year}"


def get_sheet_name_for_date(d: datetime) -> str:
    """Nombre de hoja: Pagos_Cobros_8Marzo2026."""
    return f"Pagos_Cobros_{get_folder_name_from_date(d)}"


def parse_date_from_sheet_name(sheet_name: str) -> Optional[datetime]:
    """
    Inversa de get_sheet_name_for_date: 'Pagos_Cobros_9Marzo2026' → datetime(2026, 3, 9).
    Devuelve None si el formato no coincide.
    """
    prefix = "Pagos_Cobros_"
    if not sheet_name or not sheet_name.startswith(prefix):
        return None
    rest = sheet_name[len(prefix):]  # ej. "9Marzo2026"
    for i, mes in enumerate(MESES_ES, 1):
        if mes in rest:
            idx = rest.index(mes)
            day_str = rest[:idx]
            year_str = rest[idx + len(mes):]
            try:
                return datetime(int(year_str), i, int(day_str))
            except (ValueError, TypeError):
                return None
    return None


def get_mime_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def is_allowed_attachment(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in EXTENSIONS_ALLOWED


def subject_contains_email(subject: Optional[str]) -> bool:
    """True si el Asunto del correo contiene al menos una dirección de email (ej. para filtrar correos válidos)."""
    if not subject or not subject.strip():
        return False
    # Patrón: secuencia de caracteres + @ + secuencia + punto + dominio
    return bool(re.search(r"\S+@\S+\.\S+", subject.strip()))


def subject_acceptable_for_pipeline(subject: Optional[str], keywords_or: Optional[list[str]] = None) -> bool:
    """
    True si el correo debe procesarse según el asunto.
    Acepta si: (1) el asunto contiene un email, o (2) keywords_or está definido y el asunto contiene alguna de las frases (case-insensitive).
    NOTA: El pipeline actual NO usa esta función; la regla es únicamente correo NO LEÍDO.
    """
    if not subject or not subject.strip():
        return False
    s = subject.strip()
    if subject_contains_email(s):
        return True
    if keywords_or:
        lower = s.lower()
        for kw in keywords_or:
            if kw and kw.strip().lower() in lower:
                return True
    return False


def sender_acceptable_for_pipeline(sender: Optional[str], allowed_prefixes: Optional[list[str]] = None) -> bool:
    """
    True si el correo debe procesarse por remitente (siempre incluir estos correos).
    Acepta si el email del remitente (sender) empieza con alguno de allowed_prefixes (case-insensitive).
    NOTA: El pipeline actual NO usa esta función; la regla es únicamente correo NO LEÍDO.
    """
    if not sender or not sender.strip():
        return False
    if not allowed_prefixes:
        return False
    email = sender.strip().lower()
    for prefix in allowed_prefixes:
        p = (prefix or "").strip().lower()
        if p and email.startswith(p):
            return True
    return False


def normalizar_fecha_pago(fecha: Optional[str], ref_hoy: Optional[date] = None) -> str:
    """
    Normaliza cualquier formato de fecha a DD/MM/YYYY.
    Soporta: DD/MM/YYYY, YYYY/MM/DD, DD-MM-YYYY, YYYY-MM-DD,
             DD MMM YYYY (inglés/español, con o sin punto: '06 MAR. 2026', '05 MAY 2026').
    Rechaza fechas futuras o demasiado antiguas respecto a ref_hoy (Caracas por defecto).
    Si no se puede parsear devuelve el valor original sin modificar.
    """
    from datetime import date as _date
    from datetime import datetime as _dt

    from app.services.pagos_gmail.parse_campos_comprobante import (
        fecha_plausible,
        parse_fecha_comprobante,
    )

    if ref_hoy is None:
        from app.services.tasa_cambio_service import fecha_hoy_caracas

        ref_hoy = fecha_hoy_caracas()
    if not fecha:
        return fecha or ""
    v = fecha.strip()
    if not v or v.upper() == "NA":
        return v

    parsed = parse_fecha_comprobante(v, ref_hoy)
    if parsed:
        return parsed.strftime("%d/%m/%Y")

    for fmt in (
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
    ):
        try:
            d = _dt.strptime(v, fmt).date()
            if fecha_plausible(d, ref_hoy):
                return d.strftime("%d/%m/%Y")
        except ValueError:
            pass

    MESES_ABBR = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12,
        "jan": 1,
        "apr": 4,
        "aug": 8,
        "dec": 12,
    }
    clean = re.sub(r"\.", "", v).strip()
    parts = re.split(r"[\s/\-]+", clean)
    if len(parts) == 3:
        for i, j, k in [(0, 1, 2), (2, 1, 0)]:
            mes_key = parts[j].lower()[:3]
            if mes_key in MESES_ABBR:
                try:
                    day = int(parts[i])
                    year = int(parts[k])
                    d = _date(year, MESES_ABBR[mes_key], day)
                    if fecha_plausible(d, ref_hoy):
                        return d.strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    pass

    return v  # no reconocido: devolver sin modificar


def clave_orden_fecha_pago(fecha: Optional[str]) -> Optional[str]:
    """
    Devuelve clave de comparación YYYY-MM-DD a partir de un texto de fecha.
    - Mantiene la misma lógica de interpretación que `normalizar_fecha_pago`.
    - Si no se puede interpretar, devuelve None.
    """
    raw = (fecha or "").strip()
    if not raw or raw.upper() == "NA":
        return None
    normalizada = normalizar_fecha_pago(raw)
    if not normalizada or normalizada.upper() == "NA":
        return None
    try:
        return datetime.strptime(normalizada, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def fecha_drive_texto_y_clave(raw_fecha_drive: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Retorna:
    - texto_drive: valor textual original para trazabilidad (sin reinterpretar ni re-formatear).
    - clave_orden: YYYY-MM-DD para comparaciones seguras con fecha del sistema.

    Uso esperado:
    - Mostrar/exportar `texto_drive` tal como llegó del Drive.
    - Comparar por `clave_orden` contra la fecha de aprobación del sistema.
    """
    texto_drive = raw_fecha_drive if raw_fecha_drive is not None else ""
    return texto_drive, clave_orden_fecha_pago(raw_fecha_drive)


def normalizar_referencia(ref: Optional[str]) -> str:
    """
    Elimina ceros iniciales de la referencia.
    '000130611935' → '130611935', '001234' → '1234'.
    NA, vacío o valor no numérico → devuelve sin modificar.
    """
    v = (ref or "").strip()
    if not v or v.upper() == "NA":
        return v
    if re.match(r"^\d+$", v):
        return v.lstrip("0") or v[-1]  # si todo eran ceros, conservar el último
    # Alfanumérico (letras + números): no tocar
    return v


def format_monto_excel_pagos_gmail(monto: Optional[str]) -> str:
    """
    Columna Excel «Monto» (export Gmail): entero o decimal con punto y exactamente dos cifras decimales, sin unidad.
    Ej.: '96.00 USD' -> '96.00', '122 USDT' -> '122.00', '96,00' -> '96.00', '1.500' -> '1500.00'.
    Valor literal **NR** (no RapiCredit) se conserva tal cual.
    """
    from app.services.pagos_gmail.parse_campos_comprobante import monto_comprobante_a_excel

    if monto is None:
        return ""
    s = str(monto).strip()
    if s.upper() == "NR":
        return "NR"
    if not s or s.upper() == "NA":
        return ""
    t = re.sub(
        r"\s*(USD|USDT|U\$S|US\$|Bs\.?|BSS|BOLIVAR(?:ES)?|VES)\s*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r"^\s*(USD|USDT|U\$S|US\$|Bs\.?|BSS)\s+",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    return monto_comprobante_a_excel(t if t else s)


def formatear_cedula(cedula: Optional[str]) -> str:
    """
    Aplica formato venezolano a la cédula extraída por Gemini (sin guion entre letra y números):
    - Vacío / NA      → devuelve tal cual.
    - Solo dígitos    → quita ceros iniciales y antepone V  (ej. '030145077' → 'V30145077').
    - Prefijo E o J   → normaliza a EXXXXXXX / JXXXXXXX     (ej. 'E12345678' → 'E12345678').
    - Prefijo V       → normaliza quitando ceros            (ej. 'V-030145077' → 'V30145077').
    - Valor no reconocido → devuelve sin modificar.
    """
    v = (cedula or "").strip()
    if not v or v.upper() == "NA":
        return v
    m = re.match(r"^([VEJvej])-?(\d+)$", v)
    if m:
        prefix = m.group(1).upper()
        digits = m.group(2).lstrip("0") or "0"
        return f"{prefix}{digits}"
    if re.match(r"^\d+$", v):
        digits = v.lstrip("0") or "0"
        return f"V{digits}"
    return v


def extraer_cedula_desde_asunto_cuerpo_pipeline(
    subject: str,
    body_text: str,
    *,
    max_body_chars: int = 4000,
) -> str:
    """
    Intenta extraer una cédula venezolana desde asunto y cuerpo (p. ej. «Nombre Apellido 27832913»).
    Prioriza el asunto sobre el cuerpo. Solo acepta núcleos de 6 a 11 dígitos tras formatear_cedula.
    """
    blobs: list[str] = []
    s = (subject or "").strip()
    if s:
        blobs.append(s)
    b = (body_text or "").strip()
    if b:
        blobs.append(b[:max_body_chars])

    scored: list[tuple[int, int, str]] = []

    for bi, blob in enumerate(blobs):
        prio = bi
        for m in re.finditer(r"(?i)\b([VEGJ])[\s.\-]*(\d{5,12})\b", blob):
            raw = f"{m.group(1).upper()}{m.group(2)}"
            fc = formatear_cedula(raw)
            if not fc or fc.upper() == "NA":
                continue
            digits = re.sub(r"\D", "", fc)
            if 6 <= len(digits) <= 11:
                scored.append((prio, -len(fc), fc))
        for m in re.finditer(r"\b(\d{6,11})\b", blob):
            dig = m.group(1) or ""
            if len(dig) == 8 and dig[:4].isdigit() and 1900 <= int(dig[:4]) <= 2099:
                continue
            fc = formatear_cedula(dig)
            if not fc or fc.upper() == "NA":
                continue
            digits = re.sub(r"\D", "", fc)
            if 6 <= len(digits) <= 11:
                scored.append((prio, -len(fc), fc))

    if not scored:
        return ""
    scored.sort(key=lambda t: (t[0], t[1]))
    return scored[0][2]


def resolve_banco_para_excel_pagos_gmail(
    fmt: str,
    banco_gemini: Optional[str],
    *,
    default_a: str,
    default_b: str,
    default_c: str,
    default_d: str = "BDV",
    default_e: str = "Bancamiga",
    default_f: str = "Banco del Tesoro",
    max_len: int = 50,
) -> str:
    """
    Columna Excel \"Banco\": institucion que aparece en el comprobante (texto de Gemini)
    normalizado por palabras clave; si viene vacio o NA, usa el valor por plantilla A/B/C/D/E/F.
    """
    f = (fmt or "").strip().upper()
    if f == "NR":
        raw = (banco_gemini or "").strip()
        if not raw or raw.upper() == "NA":
            return "NR"
        low = raw.lower()
        one_line = re.sub(r"\s+", " ", raw).strip()
        if "mercantil" in low:
            return "Mercantil"
        if "nacional" in low and (
            "credito" in low or "crédito" in low or "credit" in low
        ):
            return "BNC"
        if re.search(r"\bbnc\b", low):
            return "BNC"
        if "banesco" in low:
            return "Banesco"
        if "bicentenario" in low:
            return "Bicentenario"
        if "banco de venezuela" in low or re.search(r"\b(bdv)\b", low):
            return "BDV"
        if "provincial" in low or "bbva" in low:
            return "BBVA Provincial"
        if "binance" in low:
            return "BINANCE"
        if "bancamiga" in low:
            return "Bancamiga"
        if "banco del tesoro" in low:
            return "Banco del Tesoro"
        out = one_line[:max_len].strip()
        return out if out else "NR"
    if f == "C":
        return (default_c or "")[:max_len]
    if f == "F":
        template_default = default_f
    elif f == "E":
        template_default = default_e
    elif f == "D":
        template_default = default_d
    elif f == "A":
        template_default = default_a
    elif f == "B":
        template_default = default_b
    else:
        template_default = default_a
    raw = (banco_gemini or "").strip()
    if not raw or raw.upper() == "NA":
        return (template_default or "")[:max_len]
    low = raw.lower()
    one_line = re.sub(r"\s+", " ", raw).strip()
    if "mercantil" in low:
        return "Mercantil"
    if "nacional" in low and (
        "credito" in low or "crédito" in low or "credit" in low
    ):
        return "BNC"
    if re.search(r"\bbnc\b", low):
        return "BNC"
    if "banesco" in low:
        return "Banesco"
    if "bicentenario" in low:
        return "Bicentenario"
    if "banco de venezuela" in low or re.search(r"\b(bdv)\b", low):
        return "BDV"
    if "provincial" in low or "bbva" in low:
        return "BBVA Provincial"
    if "binance" in low:
        return "BINANCE"
    if "bancamiga" in low:
        return "Bancamiga"
    if "banco del tesoro" in low:
        return "Banco del Tesoro"
    out = one_line[:max_len].strip()
    return out if out else (template_default or "")[:max_len]


def extract_sender_email(from_header_value: Optional[str]) -> str:
    """Extrae solo la dirección de email del campo From (sin nombre mostrado)."""
    if not from_header_value or not from_header_value.strip():
        return "desconocido"
    s = from_header_value.strip()
    match = re.search(r"<([^>]+)>", s)
    if match:
        return match.group(1).strip().lower()
    return s.split()[0].strip().lower() if s else "desconocido"
