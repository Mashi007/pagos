"""
Comprobantes del pipeline Gmail: guardar imagen/PDF en BD (tabla pago_comprobante_imagen)
en lugar de subir el archivo del comprobante a Google Drive.

El enlace que se persiste en pagos_gmail_sync_item.drive_link / gmail_temporal.drive_link
es una URL al GET /pagos/comprobante-imagen/{id} (misma tabla que el alta manual de pago).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pago_comprobante_imagen import PagoComprobanteImagen

logger = logging.getLogger(__name__)

_MAX_COMPROBANTE_BYTES = 8 * 1024 * 1024

_MIME_PERMITIDOS = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
    }
)


def _normalizar_mime(mime: Optional[str]) -> str:
    if not mime:
        return ""
    return mime.split(";")[0].strip().lower()


def url_comprobante_imagen_absoluta(imagen_id: str) -> str:
    """Ruta API lista para guardar en drive_link (absoluta si hay BACKEND_PUBLIC_URL)."""
    base = (getattr(settings, "BACKEND_PUBLIC_URL", None) or "").strip().rstrip("/")
    path = f"{settings.API_V1_STR}/pagos/comprobante-imagen/{imagen_id}"
    return f"{base}{path}" if base else path


def persistir_comprobante_gmail_en_bd(
    db: Session,
    content: bytes | bytearray,
    mime_type: Optional[str],
) -> Optional[Tuple[str, str]]:
    """
    Inserta fila en pago_comprobante_imagen (sesión actual; el caller hace commit).

    Returns:
        (id_hex_32, url_para_columna_link) o None si no se guardó (tamaño, MIME).
    """
    body = bytes(content) if isinstance(content, bytearray) else content
    if len(body) > _MAX_COMPROBANTE_BYTES:
        logger.warning(
            "[PAGOS_GMAIL] Comprobante demasiado grande (%s bytes > %s); no se guarda en BD.",
            len(body),
            _MAX_COMPROBANTE_BYTES,
        )
        return None
    ct = _normalizar_mime(mime_type)
    if ct not in _MIME_PERMITIDOS:
        logger.warning(
            "[PAGOS_GMAIL] MIME no admitido para comprobante en BD (%r); no se guarda.",
            mime_type,
        )
        return None
    uid = uuid.uuid4().hex
    row = PagoComprobanteImagen(id=uid, content_type=ct, imagen_data=body)
    db.add(row)
    url = url_comprobante_imagen_absoluta(uid)
    if not (getattr(settings, "BACKEND_PUBLIC_URL", None) or "").strip():
        logger.info(
            "[PAGOS_GMAIL] BACKEND_PUBLIC_URL no definido: link de comprobante sera relativo (%s…); "
            "defina BACKEND_PUBLIC_URL en .env para hipervinculos absolutos en Excel.",
            url[:48],
        )
    return (uid, url)
