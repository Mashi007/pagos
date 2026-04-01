# -*- coding: utf-8 -*-
"""
Ultimo resultado del envio masivo (API «Enviar todas»).
Persistido en configuracion para GET /notificaciones/envio-batch/ultimo sin depender de logs.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_ULTIMO_ENVIO_BATCH = "notificaciones_ultimo_envio_batch"


def persist_ultimo_envio_batch(
    db: Session,
    *,
    resultado: Dict[str, Any],
    origen: str,
    error: Optional[str] = None,
    inicio_utc: Optional[str] = None,
    omitido: bool = False,
    omitido_motivo: Optional[str] = None,
) -> None:
    """Guarda resumen. El llamador hace commit."""
    fin = datetime.now(timezone.utc).isoformat()
    body: Dict[str, Any] = {
        "inicio_utc": inicio_utc or fin,
        "fin_utc": fin,
        "origen": origen,
        "omitido": omitido,
        "omitido_motivo": omitido_motivo,
        "error": error,
        "enviados": int(resultado.get("enviados", 0) or 0),
        "fallidos": int(resultado.get("fallidos", 0) or 0),
        "sin_email": int(resultado.get("sin_email", 0) or 0),
        "omitidos_config": int(resultado.get("omitidos_config", 0) or 0),
        "omitidos_paquete_incompleto": int(resultado.get("omitidos_paquete_incompleto", 0) or 0),
        "enviados_whatsapp": int(resultado.get("enviados_whatsapp", 0) or 0),
        "fallidos_whatsapp": int(resultado.get("fallidos_whatsapp", 0) or 0),
        "detalles": resultado.get("detalles"),
    }
    try:
        valor = json.dumps(body, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning("persist_ultimo_envio_batch: detalles no serializables, omitiendo detalles: %s", e)
        body["detalles"] = None
        valor = json.dumps(body, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_ULTIMO_ENVIO_BATCH)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_ULTIMO_ENVIO_BATCH, valor=valor))


def get_ultimo_envio_batch_dict(db: Session) -> Optional[Dict[str, Any]]:
    """Devuelve el ultimo resumen o None si no hay."""
    try:
        row = db.get(Configuracion, CLAVE_ULTIMO_ENVIO_BATCH)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.warning("get_ultimo_envio_batch_dict: %s", e)
    return None
