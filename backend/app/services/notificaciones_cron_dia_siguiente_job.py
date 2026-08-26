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
    """
    Ejecuta el envío PAGO_1_DIA_ATRASADO para el slot actual (o el indicado).

    Respeta habilitado=False en notificaciones_envios. Reintenta ante excepciones.
    """
    from app.api.v1.endpoints.notificaciones_tabs import ejecutar_envio_caso_manual

    ahora = datetime.now(_TZ)
    hoy = hoy_negocio()
    hoy_s = hoy.isoformat()
    if not slot:
        slot = _slot_key(ahora.hour, ahora.minute)
        # Si el job dispara a :15, alinear al slot configurado más cercano de esta hora.
        for h, m in horarios_cron_dia_siguiente():
            if h == ahora.hour and m == ahora.minute:
                slot = _slot_key(h, m)
                break
            if h == ahora.hour and abs(m - ahora.minute) <= 2:
                slot = _slot_key(h, m)
                break

    prev = _cargar_estado(db)
    if debe_omitir_cron_por_estado_persistido(prev, hoy_s, slot):
        logger.info(
            "[cron_dia_sig] omitido: ya hubo resultado terminal hoy (%s) slot=%s",
            hoy_s,
            slot,
        )
        return {
            "omitido": True,
            "motivo": "ya_resultado_terminal_slot_hoy",
            "fecha_referencia_caracas": hoy_s,
            "slot": slot,
        }

    cfg = get_notificaciones_envios_dict(db)
    tipo_cfg = cfg.get(TIPO_CASO)
    if isinstance(tipo_cfg, dict) and tipo_cfg.get("habilitado") is False:
        fin = datetime.now(timezone.utc).isoformat()
        _guardar_slot(
            db,
            hoy_s=hoy_s,
            slot=slot,
            payload={
                "estado": "omitido_tipo",
                "fin_utc": fin,
                "motivo": f"{TIPO_CASO} habilitado=false en notificaciones_envios",
            },
        )
        db.commit()
        logger.info("[cron_dia_sig] omitido: envío desactivado para %s slot=%s", TIPO_CASO, slot)
        return {
            "omitido": True,
            "motivo": "tipo_deshabilitado_config",
            "fecha_referencia_caracas": hoy_s,
            "slot": slot,
        }

    max_try = int(getattr(settings, "CRON_DIA_SIGUIENTE_INTENTOS_JOB", 3) or 3)
    max_try = max(1, min(max_try, 10))
    sleep_s = int(
        getattr(settings, "CRON_DIA_SIGUIENTE_SLEEP_ENTRE_INTENTOS_SEG", 60) or 60
    )
    sleep_s = max(5, min(sleep_s, 600))

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_try + 1):
        try:
            out = ejecutar_envio_caso_manual(
                db,
                TIPO_CASO,
                fecha_referencia=None,
                respetar_toggle_envio=True,
            )
            fin = datetime.now(timezone.utc).isoformat()
            _guardar_slot(
                db,
                hoy_s=hoy_s,
                slot=slot,
                payload={
                    "estado": "ok",
                    "fin_utc": fin,
                    "enviados": int(out.get("enviados", 0) or 0),
                    "total_en_lista": int(out.get("total_en_lista", 0) or 0),
                    "fallidos": int(out.get("fallidos", 0) or 0),
                    "sin_email": int(out.get("sin_email", 0) or 0),
                    "omitidos_config": int(out.get("omitidos_config", 0) or 0),
                    "intento": attempt,
                },
            )
            db.commit()
            logger.info(
                "[cron_dia_sig] ok fecha=%s slot=%s enviados=%s total_lista=%s fallidos=%s intento=%s/%s",
                hoy_s,
                slot,
                out.get("enviados"),
                out.get("total_en_lista"),
                out.get("fallidos"),
                attempt,
                max_try,
            )
            return {
                "omitido": False,
                "fecha_referencia_caracas": hoy_s,
                "slot": slot,
                **out,
            }
        except Exception as e:
            last_exc = e
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(
                "[cron_dia_sig] intento %s/%s falló slot=%s: %s",
                attempt,
                max_try,
                slot,
                e,
                exc_info=attempt == max_try,
            )
            if attempt < max_try:
                time.sleep(sleep_s)

    fin = datetime.now(timezone.utc).isoformat()
    err_msg = str(last_exc)[:2000] if last_exc else "error_desconocido"
    _guardar_slot(
        db,
        hoy_s=hoy_s,
        slot=slot,
        payload={
            "estado": "error",
            "fin_utc": fin,
            "error": err_msg,
            "intentos": max_try,
        },
    )
    db.commit()
    logger.error(
        "[cron_dia_sig] error definitivo fecha=%s slot=%s tras %s intentos",
        hoy_s,
        slot,
        max_try,
    )
    return {
        "omitido": False,
        "error": True,
        "fecha_referencia_caracas": hoy_s,
        "slot": slot,
        "mensaje": err_msg,
        "intentos": max_try,
    }


def job_cron_dia_siguiente_scheduler() -> None:
    """Punto de entrada APScheduler: sesión propia; slot = hora:minuto Caracas actual."""
    from app.core.database import SessionLocal

    ahora = datetime.now(_TZ)
    slot = None
    for h, m in horarios_cron_dia_siguiente():
        if h == ahora.hour and abs(m - ahora.minute) <= 2:
            slot = _slot_key(h, m)
            break
    if slot is None:
        slot = _slot_key(ahora.hour, ahora.minute)

    db = SessionLocal()
    try:
        ejecutar_cron_dia_siguiente(db, slot=slot)
    except Exception as e:
        logger.exception("[cron_dia_sig] job no controlado: %s", e)
    finally:
        db.close()
