# -*- coding: utf-8 -*-
"""Cancelacion cooperativa de lotes de notificaciones en curso."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_CANCEL_LOTE = "notificaciones_envio_cancel_flag"


def _leer(db: Session) -> Dict[str, Any]:
    row = db.get(Configuracion, CLAVE_CANCEL_LOTE)
    if not row or not row.valor:
        return {}
    try:
        data = json.loads(row.valor)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _guardar(db: Session, data: Dict[str, Any]) -> None:
    valor = json.dumps(data, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_CANCEL_LOTE)
    if row is None:
        for obj in list(db.new):
            if isinstance(obj, Configuracion) and obj.clave == CLAVE_CANCEL_LOTE:
                row = obj
                break
    if row is None:
        row = (
            db.query(Configuracion)
            .filter(Configuracion.clave == CLAVE_CANCEL_LOTE)
            .first()
        )
    if row is not None:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_CANCEL_LOTE, valor=valor))


def solicitar_cancelacion_lote(
    db: Session,
    *,
    tipo_caso: Optional[str] = None,
    token_seguimiento: Optional[str] = None,
) -> Dict[str, Any]:
    """Marca cancelacion; el pipeline la lee entre items y corta el lote."""
    body = {
        "solicitado_utc": datetime.now(timezone.utc).isoformat(),
        "tipo_caso": (tipo_caso or "").strip() or None,
        "token_seguimiento": (token_seguimiento or "").strip() or None,
        "activo": True,
    }
    _guardar(db, body)
    logger.warning(
        "[notif_cancel] solicitado tipo=%s token=%s",
        body.get("tipo_caso"),
        (body.get("token_seguimiento") or "")[:12],
    )
    return body


def cancelacion_lote_activa(
    db: Session,
    *,
    tipo_caso: Optional[str] = None,
    token_seguimiento: Optional[str] = None,
) -> bool:
    data = _leer(db)
    if not data.get("activo"):
        return False
    tok = (token_seguimiento or "").strip()
    tipo = (tipo_caso or "").strip()
    flag_tok = str(data.get("token_seguimiento") or "").strip()
    flag_tipo = str(data.get("tipo_caso") or "").strip()
    # Sin filtro en el flag: cancela cualquier lote activo.
    if not flag_tok and not flag_tipo:
        return True
    if flag_tok and tok and flag_tok == tok:
        return True
    if flag_tipo and tipo and flag_tipo == tipo:
        return True
    # Flag con tipo/token pero el llamador no pasa match: igual cancelar
    # el lote en curso (un solo SMTP masivo a la vez).
    if not tok and not tipo:
        return True
    return bool(flag_tok or flag_tipo)


def limpiar_cancelacion_lote(db: Session) -> None:
    _guardar(db, {"activo": False, "limpiado_utc": datetime.now(timezone.utc).isoformat()})
