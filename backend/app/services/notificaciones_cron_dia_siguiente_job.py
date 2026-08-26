# -*- coding: utf-8 -*-
"""
Cron servidor: envío automático «día siguiente al vencimiento»
(PAGO_1_DIA_ATRASADO / ruta /notificaciones).

Requiere ENABLE_AUTOMATIC_SCHEDULED_JOBS + líder de scheduler, y
ENABLE_CRON_NOTIFICACIONES_DIA_SIGUIENTE (ver settings).
Horario America/Caracas: CRON_DIA_SIGUIENTE_HOURS / CRON_DIA_SIGUIENTE_MINUTE
(defecto 09:15 y 17:15, todos los días).

Idempotencia: un resultado terminal por (fecha Caracas, slot HH:MM).
Así el envío de la mañana y el de la tarde no se bloquean entre sí.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.configuracion import Configuracion
from app.services.cuota_estado import hoy_negocio
from app.services.notificaciones_envios_store import get_notificaciones_envios_dict

logger = logging.getLogger(__name__)

TIPO_CASO = "PAGO_1_DIA_ATRASADO"
CLAVE_CRON_DIA_SIGUIENTE_ESTADO = "notificaciones_cron_dia_siguiente_estado"
_TZ = ZoneInfo("America/Caracas")

_ESTADOS_TERMINALES_DIA = frozenset({"ok", "error", "omitido_tipo"})


def _slot_key(hour: int, minute: int) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"


def horarios_cron_dia_siguiente() -> List[Tuple[int, int]]:
    """Lista de (hora, minuto) Caracas configurados (defecto 9:15 y 17:15)."""
    minute = int(getattr(settings, "CRON_DIA_SIGUIENTE_MINUTE", 15) or 15)
    minute = max(0, min(59, minute))
    raw = getattr(settings, "CRON_DIA_SIGUIENTE_HOURS", "9,17")
    hours: List[int] = []
    if isinstance(raw, (list, tuple)):
        for h in raw:
            try:
                hours.append(int(h))
            except (TypeError, ValueError):
                continue
    else:
        for part in str(raw or "9,17").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                hours.append(int(part))
            except ValueError:
                continue
    if not hours:
        hours = [9, 17]
    out: List[Tuple[int, int]] = []
    seen = set()
    for h in hours:
        h = max(0, min(23, int(h)))
        key = (h, minute)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def debe_omitir_cron_por_estado_persistido(
    estado: Dict[str, Any], hoy_iso: str, slot: str
) -> bool:
    """True si el slot HH:MM de hoy ya tiene resultado terminal."""
    if (estado.get("fecha_referencia_caracas") or "") != hoy_iso:
        return False
    slots = estado.get("slots")
    if not isinstance(slots, dict):
        # Compat legacy (un solo estado diario): no bloquea slots nuevos.
        return False
    prev = slots.get(slot)
    if not isinstance(prev, dict):
        return False
    return (prev.get("estado") or "") in _ESTADOS_TERMINALES_DIA


def _cargar_estado(db: Session) -> Dict[str, Any]:
    try:
        row = db.get(Configuracion, CLAVE_CRON_DIA_SIGUIENTE_ESTADO)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError as e:
        logger.warning("[cron_dia_sig] estado en BD no es JSON valido: %s", e)
    except Exception as e:
        logger.exception("[cron_dia_sig] leer estado: %s", e)
    return {}


def _persistir_estado(db: Session, body: Dict[str, Any]) -> None:
    raw = json.dumps(body, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_CRON_DIA_SIGUIENTE_ESTADO)
    if row:
        row.valor = raw
    else:
        db.add(Configuracion(clave=CLAVE_CRON_DIA_SIGUIENTE_ESTADO, valor=raw))


def _guardar_slot(
    db: Session,
    *,
    hoy_s: str,
    slot: str,
    payload: Dict[str, Any],
) -> None:
    prev = _cargar_estado(db)
    slots = prev.get("slots") if isinstance(prev.get("slots"), dict) else {}
    if (prev.get("fecha_referencia_caracas") or "") != hoy_s:
        slots = {}
    slots = dict(slots)
    slots[slot] = payload
    _persistir_estado(
        db,
        {
            "fecha_referencia_caracas": hoy_s,
            "slots": slots,
            "ultimo_slot": slot,
            "fin_utc": payload.get("fin_utc"),
        },
    )


def ejecutar_cron_dia_siguiente(db: Session, *, slot: Optional[str] = None) -> Dict[str, Any]:
    """Eliminado del producto: no envía PAGO_1_DIA_ATRASADO."""
    logger.info("[cron_dia_sig] omitido: tipo eliminado del producto slot=%s", slot)
    return {"omitido": True, "motivo": "tipo_eliminado_producto", "slot": slot}


def job_cron_dia_siguiente_scheduler() -> None:
    """Eliminado: PAGO_1_DIA_ATRASADO ya no se envía por cron."""
    logger.info("[cron_dia_sig] omitido: tipo eliminado del producto")

