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

# Claves globales del JSON (no son filas por tipo de caso).
_GLOBAL_KEYS_ENVIOS = frozenset({"modo_pruebas", "email_pruebas", "emails_pruebas"})


def merge_notificaciones_envios(existing: Any, incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusiona el cuerpo del PUT sobre la config ya persistida.

    Independencia entre criterios: cada clave de tipo (PAGO_*, PREJUDICIAL, MASIVOS, …)
    se fusiona por separado. Un PUT que solo incluye, p. ej., PAGO_2_DIAS_ANTES_PENDIENTE
    no modifica plantillas, CCO ni toggles de otros casos; tampoco borra claves omitidas.

    Claves globales (modo_pruebas, email_pruebas, emails_pruebas): si vienen en incoming,
    sustituyen el valor en raíz y aplican a todos los envíos (comportamiento compartido).

    masivos_campanas: si la clave viene en incoming, sustituye el array completo; si se omite,
    se conserva el array ya persistido (permite guardar solo mora/prejudicial sin tocar masivos).

    cron_envio_pago_2_dias_antes: dict opcional { habilitado: bool }; solo lo escribe el submódulo «2 días antes».
    No afecta a otros criterios ni a la lógica de envío de otras pestañas.
    """
    base: Dict[str, Any] = {}
    if isinstance(existing, dict):
        base = dict(existing)
    if not isinstance(incoming, dict):
        return base
    out: Dict[str, Any] = dict(base)
    for key, value in incoming.items():
        if key in _GLOBAL_KEYS_ENVIOS:
            out[key] = value
        elif key == "masivos_campanas":
            out[key] = value
        elif isinstance(value, dict):
            prev = out.get(key)
            if isinstance(prev, dict):
                merged_row = dict(prev)
                merged_row.update(value)
                out[key] = merged_row
            else:
                out[key] = dict(value)
        else:
            out[key] = value
    return out


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
