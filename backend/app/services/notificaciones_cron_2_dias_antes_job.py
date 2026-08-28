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


def _parse_hhmm_slots(raw: str) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    seen: set[Tuple[int, int]] = set()
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        h_s, m_s = part.split(":", 1)
        try:
            h = max(0, min(23, int(h_s.strip())))
            m = max(0, min(59, int(m_s.strip())))
        except ValueError:
            continue
        key = (h, m)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def horarios_cron_2_dias_antes() -> List[Tuple[int, int]]:
    """Lista de (hora, minuto) Caracas configurados (defecto 00:48 madrugada y 18:15 tarde)."""
    slots_raw = getattr(settings, "CRON_2_DIAS_ANTES_SLOTS", "0:48,18:15")
    parsed = _parse_hhmm_slots(str(slots_raw or ""))
    if parsed:
        return parsed
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
    """
    Ejecuta el envío PAGO_2_DIAS_ANTES_PENDIENTE para el slot actual (o el indicado).

    Respeta habilitado=False en notificaciones_envios. Reintenta ante excepciones.
    """
    from app.api.v1.endpoints.notificaciones_tabs import ejecutar_envio_caso_manual

    ahora = datetime.now(_TZ)
    hoy = hoy_negocio()
    hoy_s = hoy.isoformat()
    if not slot:
        slot = _slot_key(ahora.hour, ahora.minute)
        for h, m in horarios_cron_2_dias_antes():
            if h == ahora.hour and abs(m - ahora.minute) <= 2:
                slot = _slot_key(h, m)
                break

    prev = _cargar_estado(db)
    if debe_omitir_cron_por_estado_persistido(prev, hoy_s, slot):
        logger.info(
            "[cron_2d] omitido: ya hubo resultado terminal hoy (%s) slot=%s",
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
        logger.info("[cron_2d] omitido: envío desactivado para %s slot=%s", TIPO_CASO, slot)
        return {
            "omitido": True,
            "motivo": "tipo_deshabilitado_config",
            "fecha_referencia_caracas": hoy_s,
            "slot": slot,
        }

    max_try = int(getattr(settings, "CRON_2_DIAS_ANTES_INTENTOS_JOB", 3) or 3)
    max_try = max(1, min(max_try, 10))
    sleep_s = int(getattr(settings, "CRON_2_DIAS_ANTES_SLEEP_ENTRE_INTENTOS_SEG", 60) or 60)
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
                "[cron_2d] ok fecha=%s slot=%s enviados=%s total_lista=%s fallidos=%s intento=%s/%s",
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
                "[cron_2d] intento %s/%s falló slot=%s: %s",
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
        "[cron_2d] error definitivo fecha=%s slot=%s tras %s intentos",
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


def job_cron_pago_2_dias_antes_scheduler() -> None:
    """Punto de entrada APScheduler: sesión propia; slot = hora:minuto Caracas actual."""
    from app.core.database import SessionLocal

    ahora = datetime.now(_TZ)
    slot = None
    for h, m in horarios_cron_2_dias_antes():
        if h == ahora.hour and abs(m - ahora.minute) <= 2:
            slot = _slot_key(h, m)
            break
    if slot is None:
        slot = _slot_key(ahora.hour, ahora.minute)

    db = SessionLocal()
    try:
        ejecutar_cron_pago_2_dias_antes(db, slot=slot)
    except Exception as e:
        logger.exception("[cron_2d] job no controlado: %s", e)
    finally:
        db.close()
