"""
Helpers: nombre de carpeta por fecha, mime types, extracción de email del remitente.
"""
import re
from datetime import datetime
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


def formatear_cedula(cedula: Optional[str]) -> str:
    """
    Aplica formato venezolano a la cédula extraída por Gemini:
    - Vacío / NA      → devuelve tal cual.
    - Solo dígitos    → quita ceros iniciales y antepone V-  (ej. '030145077' → 'V-30145077').
    - Prefijo E o J   → normaliza a E-XXXXXXX / J-XXXXXXX   (ej. 'E12345678' → 'E-12345678').
    - Prefijo V       → normaliza quitando ceros             (ej. 'V-030145077' → 'V-30145077').
    - Valor no reconocido → devuelve sin modificar.
    """
    v = (cedula or "").strip()
    if not v or v.upper() == "NA":
        return v
    m = re.match(r"^([VEJvej])-?(\d+)$", v)
    if m:
        prefix = m.group(1).upper()
        digits = m.group(2).lstrip("0") or "0"
        return f"{prefix}-{digits}"
    if re.match(r"^\d+$", v):
        digits = v.lstrip("0") or "0"
        return f"V-{digits}"
    return v


def extract_sender_email(from_header_value: Optional[str]) -> str:
    """Extrae solo la dirección de email del campo From (sin nombre mostrado)."""
    if not from_header_value or not from_header_value.strip():
        return "desconocido"
    s = from_header_value.strip()
    match = re.search(r"<([^>]+)>", s)
    if match:
        return match.group(1).strip().lower()
    return s.split()[0].strip().lower() if s else "desconocido"
