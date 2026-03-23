# -*- coding: utf-8 -*-
"""
Unica fuente de lectura/escritura del JSON notificaciones_envios en tabla configuracion.
Evita duplicar logica entre configuracion.py (REST), notificaciones.py (batch) y
email_config_holder._load_notificaciones_envios (SMTP/modo prueba).
"""
import json
import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"


def get_notificaciones_envios_dict(db: Session) -> Dict[str, Any]:
    """Devuelve el dict guardado en BD o {} si ausente o invalido."""
    try:
        row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError as e:
        logger.warning("notificaciones_envios: valor en BD no es JSON valido: %s", e)
    except Exception as e:
        logger.exception("get_notificaciones_envios_dict: %s", e)
    return {}


def put_notificaciones_envios_dict(db: Session, payload: Dict[str, Any]) -> None:
    """Persiste el dict completo. El llamador hace commit/rollback."""
    valor = json.dumps(payload, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_NOTIFICACIONES_ENVIOS, valor=valor))


def coerce_modo_pruebas_notificaciones(raw) -> bool:
    """
    Alineado con get_modo_pruebas_servicio('notificaciones') en email_config_holder.
    """
    if raw is True:
        return True
    if isinstance(raw, str):
        s = raw.strip().lower()
        return s in ("true", "1", "yes", "si", "sí", "on")
    return False
