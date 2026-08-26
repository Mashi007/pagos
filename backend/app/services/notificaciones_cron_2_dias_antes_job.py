# -*- coding: utf-8 -*-
"""
Cron servidor: envío automático «3 días antes» / d-2-antes
(PAGO_2_DIAS_ANTES_PENDIENTE / ruta /notificaciones/d-2-antes).

Requiere ENABLE_AUTOMATIC_SCHEDULED_JOBS + líder de scheduler, y
ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES (ver settings).
Horario America/Caracas: CRON_2_DIAS_ANTES_HOURS / CRON_2_DIAS_ANTES_MINUTE
(defecto 07:15 y 18:15, todos los días).

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

TIPO_CASO = "PAGO_2_DIAS_ANTES_PENDIENTE"
CLAVE_CRON_2_DIAS_ESTADO = "notificaciones_cron_2_dias_antes_estado"
_TZ = ZoneInfo("America/Caracas")

_ESTADOS_TERMINALES_DIA = frozenset({"ok", "error", "omitido_tipo"})


def _slot_key(hour: int, minute: int) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"


def horarios_cron_2_dias_antes() -> List[Tuple[int, int]]:
    """Lista de (hora, minuto) Caracas configurados (defecto 7:15 y 18:15)."""
    minute = int(getattr(settings, "CRON_2_DIAS_ANTES_MINUTE", 15) or 15)
    minute = max(0, min(59, minute))
    raw = getattr(settings, "CRON_2_DIAS_ANTES_HOURS", None)
    hours: List[int] = []
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        # Compat: un solo CRON_2_DIAS_ANTES_HOUR si no hay HOURS.
        try:
            hours = [int(getattr(settings, "CRON_2_DIAS_ANTES_HOUR", 7) or 7)]
        except (TypeError, ValueError):
            hours = [7, 18]
    elif isinstance(raw, (list, tuple)):
        for h in raw:
            try:
                hours.append(int(h))
            except (TypeError, ValueError):
                continue
    else:
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                hours.append(int(part))
            except ValueError:
                continue
    if not hours:
        hours = [7, 18]
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
    estado: Dict[str, Any], hoy_iso: str, slot: str = ""
) -> bool:
    """
    True si el slot HH:MM de hoy ya tiene resultado terminal.

    Compat legacy (estado plano sin ``slots``): si ``slot`` vacío, usa el estado diario;
    si hay slot y el JSON es legacy, no bloquea (permite migración a 2 disparos/día).
    """
    if (estado.get("fecha_referencia_caracas") or "") != hoy_iso:
        return False
    slots = estado.get("slots")
    if isinstance(slots, dict):
        if not slot:
            return False
        prev = slots.get(slot)
        if not isinstance(prev, dict):
            return False
        return (prev.get("estado") or "") in _ESTADOS_TERMINALES_DIA
    # Legacy: un solo estado diario (sin slots).
    if not slot:
        return (estado.get("estado") or "") in _ESTADOS_TERMINALES_DIA
    return False


def _cargar_estado(db: Session) -> Dict[str, Any]:
    try:
        row = db.get(Configuracion, CLAVE_CRON_2_DIAS_ESTADO)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError as e:
        logger.warning("[cron_2d] estado en BD no es JSON valido: %s", e)
    except Exception as e:
        logger.exception("[cron_2d] leer estado: %s", e)
    return {}


def _persistir_estado(db: Session, body: Dict[str, Any]) -> None:
    raw = json.dumps(body, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_CRON_2_DIAS_ESTADO)
    if row:
        row.valor = raw
    else:
        db.add(Configuracion(clave=CLAVE_CRON_2_DIAS_ESTADO, valor=raw))


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


def ejecutar_cron_pago_2_dias_antes(
    db: Session, *, slot: Optional[str] = None
) -> Dict[str, Any]:
    """Eliminado del producto: no envía PAGO_2_DIAS_ANTES_PENDIENTE."""
    logger.info("[cron_2d] omitido: tipo eliminado del producto slot=%s", slot)
    return {"omitido": True, "motivo": "tipo_eliminado_producto", "slot": slot}


def job_cron_pago_2_dias_antes_scheduler() -> None:
    """Eliminado: PAGO_2_DIAS_ANTES_PENDIENTE ya no se envía por cron."""
    logger.info("[cron_2d] omitido: tipo eliminado del producto")
