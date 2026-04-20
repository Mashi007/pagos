"""
Comprobantes binarios de pago en BD: tabla única `pago_comprobante_imagen` (imagen o PDF).

Usado por: pipeline Gmail, alta manual `/pagos/comprobante-imagen`, informes web
(Infopagos / cobros público → `pagos_reportados.comprobante_imagen_id`), e imagen del
flujo WhatsApp informe (`pagos_whatsapp.comprobante_imagen_id`).

El enlace persistido en Gmail (drive_link / temporal) es URL al GET /pagos/comprobante-imagen/{id}.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pago_comprobante_imagen import PagoComprobanteImagen

logger = logging.getLogger(__name__)

_MAX_COMPROBANTE_BYTES = 10 * 1024 * 1024

# Alineado con helpers.MIME_IMAGE_OR_PDF (adjuntos Gmail) para no fallar tras Gemini OK.
_MIME_PERMITIDOS = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
        "application/pdf",
    }
)


def _normalizar_mime(mime: Optional[str]) -> str:
    if not mime:
        return ""
    s = mime.split(";")[0].strip().lower()
    if s == "image/jpg":
        return "image/jpeg"
    return s


def url_comprobante_imagen_absoluta(imagen_id: str) -> str:
    """Ruta API lista para guardar en drive_link (absoluta si hay URL pública resolvible)."""
    from app.core.config import get_effective_api_public_base_url

    base = get_effective_api_public_base_url()
    path = f"{settings.API_V1_STR}/pagos/comprobante-imagen/{imagen_id}"
    return f"{base}{path}" if base else path


def persistir_comprobante_gmail_en_bd(
    db: Session,
    content: bytes | bytearray,
    mime_type: Optional[str],
    *,
    sha256_hex: Optional[str] = None,
    reuse_por_sha256: Optional[dict[str, Tuple[str, str]]] = None,
) -> Optional[Tuple[str, str]]:
    """
    Inserta fila en pago_comprobante_imagen (sesión actual; el caller hace commit).

    Si ``reuse_por_sha256`` contiene ``sha256_hex`` (64 hex minúsculas), devuelve ese
    (id, url) sin insertar de nuevo. El caller debe registrar en el dict **solo tras**
    ``commit`` exitoso, para no reusar IDs revertidos por rollback.

    Returns:
        (id_hex_32, url_para_columna_link) o None si no se guardó (tamaño, MIME).
    """
    sh = (sha256_hex or "").strip().lower()
    if reuse_por_sha256 is not None and len(sh) == 64 and all(c in "0123456789abcdef" for c in sh):
        hit = reuse_por_sha256.get(sh)
        if hit is not None:
            return hit

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
    if not url.lower().startswith("http"):
        logger.info(
            "[PAGOS_GMAIL] Sin URL pública de API (BACKEND_PUBLIC_URL / FRONTEND_PUBLIC_URL / "
            "origen de GOOGLE_REDIRECT_URI): link de comprobante sera relativo (%s…).",
            url[:48],
        )
    return (uid, url)
