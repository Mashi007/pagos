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


def get_folder_name_from_date(d: datetime) -> str:
    """Nombre de carpeta: 8Marzo2026, 15Abril2026."""
    day = d.day
    month_name = MESES_ES[d.month - 1]
    year = d.year
    return f"{day}{month_name}{year}"


def get_sheet_name_for_date(d: datetime) -> str:
    """Nombre de hoja: Pagos_Cobros_8Marzo2026."""
    return f"Pagos_Cobros_{get_folder_name_from_date(d)}"


def get_mime_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def is_allowed_attachment(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in EXTENSIONS_ALLOWED


def extract_sender_email(from_header_value: Optional[str]) -> str:
    """Extrae solo la dirección de email del campo From (sin nombre mostrado)."""
    if not from_header_value or not from_header_value.strip():
        return "desconocido"
    s = from_header_value.strip()
    match = re.search(r"<([^>]+)>", s)
    if match:
        return match.group(1).strip().lower()
    return s.split()[0].strip().lower() if s else "desconocido"
