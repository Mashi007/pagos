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
from typing import Iterable, Optional, Set, Tuple

from sqlalchemy import delete, func, or_, select
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
        "image/tiff",
        "image/bmp",
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
    # No todos los modelos que referencian esta tabla declaran una relación ORM;
    # hacen FK por id escalar. Forzar el INSERT aquí evita que el unit of work
    # intente insertar primero la fila hija y PostgreSQL rechace la FK.
    db.flush([row])
    url = url_comprobante_imagen_absoluta(uid)
    if not url.lower().startswith("http"):
        logger.info(
            "[PAGOS_GMAIL] Sin URL pública de API (BACKEND_PUBLIC_URL / FRONTEND_PUBLIC_URL / "
            "origen de GOOGLE_REDIRECT_URI): link de comprobante sera relativo (%s…).",
            url[:48],
        )
    return (uid, url)


def id_comprobante_desde_url(link: Optional[str]) -> Optional[str]:
    """Extrae el id hex-32 de una URL …/comprobante-imagen/{id} (o id plano)."""
    from app.services.pagos.comprobante_adjunto_pago import ids_comprobante_imagen_desde_texto

    ids = ids_comprobante_imagen_desde_texto(link)
    return ids[0] if ids else None


def comprobante_tiene_referencias(
    db: Session,
    imagen_id: str,
    *,
    excluir_receipt_ids: Optional[Iterable[int]] = None,
) -> bool:
    """
    True si algún registro vivo aún apunta al binario.
    Usado al eliminar recibos de cola para no dejar basura en ``pago_comprobante_imagen``.
    """
    cid = (imagen_id or "").strip().lower()
    if len(cid) != 32 or any(c not in "0123456789abcdef" for c in cid):
        return True  # id raro: no borrar
    like = f"%comprobante-imagen/{cid}%"
    excl: Set[int] = {int(x) for x in (excluir_receipt_ids or []) if x is not None}

    from app.models.auditoria_email import AuditoriaEmailReceipt
    from app.models.infopagos_escaner_borrador import InfopagosEscanerBorrador
    from app.models.pago import Pago
    from app.models.pago_reportado import PagoReportado
    from app.models.pagos_gmail_sync import GmailTemporal, PagosGmailSyncItem
    from app.models.pagos_whatsapp import PagosWhatsapp

    q_rec = select(func.count()).select_from(AuditoriaEmailReceipt).where(
        AuditoriaEmailReceipt.image_url.isnot(None),
        AuditoriaEmailReceipt.image_url.ilike(like),
    )
    if excl:
        q_rec = q_rec.where(AuditoriaEmailReceipt.id.notin_(excl))
    if int(db.execute(q_rec).scalar() or 0) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(PagosGmailSyncItem)
            .where(
                or_(
                    PagosGmailSyncItem.drive_link.ilike(like),
                    PagosGmailSyncItem.drive_file_id == cid,
                )
            )
        ).scalar()
        or 0
    ) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(GmailTemporal)
            .where(
                or_(
                    GmailTemporal.drive_link.ilike(like),
                    GmailTemporal.drive_file_id == cid,
                )
            )
        ).scalar()
        or 0
    ) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(Pago)
            .where(
                or_(
                    Pago.link_comprobante.ilike(like),
                    Pago.documento_ruta.ilike(like),
                    Pago.documento_ruta == cid,
                )
            )
        ).scalar()
        or 0
    ) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(PagoReportado)
            .where(PagoReportado.comprobante_imagen_id == cid)
        ).scalar()
        or 0
    ) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(InfopagosEscanerBorrador)
            .where(InfopagosEscanerBorrador.comprobante_imagen_id == cid)
        ).scalar()
        or 0
    ) > 0:
        return True

    if int(
        db.execute(
            select(func.count())
            .select_from(PagosWhatsapp)
            .where(PagosWhatsapp.comprobante_imagen_id == cid)
        ).scalar()
        or 0
    ) > 0:
        return True

    return False


def borrar_comprobante_si_huerfano(
    db: Session,
    imagen_id: Optional[str],
    *,
    excluir_receipt_ids: Optional[Iterable[int]] = None,
) -> bool:
    """Borra fila de ``pago_comprobante_imagen`` si nadie la referencia. Return True si borró."""
    cid = (imagen_id or "").strip().lower()
    if len(cid) != 32:
        return False
    try:
        if comprobante_tiene_referencias(
            db, cid, excluir_receipt_ids=excluir_receipt_ids
        ):
            return False
        res = db.execute(
            delete(PagoComprobanteImagen).where(PagoComprobanteImagen.id == cid)
        )
        return int(res.rowcount or 0) > 0
    except Exception as e:
        logger.warning(
            "[COMPROBANTE_BD] no se pudo borrar huérfano id=%s: %s", cid[:8], e
        )
        return False
