"""Persistencia de snapshot de correo (cuerpo + adjuntos + comprobante PDF) tras un envío."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto
from app.services.envio_notificacion_comprobante_pdf import generar_comprobante_envio_pdf_bytes

if TYPE_CHECKING:
    from app.models.envio_notificacion import EnvioNotificacion

logger = logging.getLogger(__name__)


def persistir_snapshot_envio_notificacion(
    db: Session,
    envio: "EnvioNotificacion",
    adjuntos: Optional[List[Tuple[str, bytes]]],
) -> None:
    """
    Tras db.add(envio): hace flush, genera comprobante PDF y guarda adjuntos.
    No hace commit (el llamador hace commit del lote).
    """
    db.flush()
    try:
        pdf = generar_comprobante_envio_pdf_bytes(envio)
        envio.comprobante_pdf = pdf
    except Exception as e:
        logger.warning(
            "[ENVIO_SNAPSHOT] No se pudo generar comprobante PDF envio_id=%s: %s",
            getattr(envio, "id", None),
            e,
        )
        envio.comprobante_pdf = None

    orden = 0
    for pair in adjuntos or []:
        if not pair or len(pair) < 2:
            continue
        nombre, contenido = pair[0], pair[1]
        if not contenido:
            continue
        nombre_safe = (nombre or f"adjunto_{orden}.bin").strip()[:255]
        db.add(
            EnvioNotificacionAdjunto(
                envio_notificacion_id=envio.id,
                nombre_archivo=nombre_safe,
                contenido=bytes(contenido),
                orden=orden,
            )
        )
        orden += 1
