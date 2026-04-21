# -*- coding: utf-8 -*-
"""
Cron servidor: envío automático solo «2 días antes» (PAGO_2_DIAS_ANTES_PENDIENTE).

Requiere ENABLE_AUTOMATIC_SCHEDULED_JOBS + líder de scheduler, y ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES
(ver settings). Horario America/Caracas: CRON_2_DIAS_ANTES_HOUR / CRON_2_DIAS_ANTES_MINUTE.

Idempotencia: una ejecución «terminal» por fecha Caracas (clave configuracion
notificaciones_cron_2_dias_antes_estado): ok | error | omitido_tipo. Evita doble envío si el job
se re-dispara el mismo día y reintentos tras excepciones (varios intentos en la misma corrida).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.configuracion import Configuracion
from app.services.cuota_estado import hoy_negocio
from app.services.notificaciones_envios_store import get_notificaciones_envios_dict

logger = logging.getLogger(__name__)

CLAVE_CRON_2_DIAS_ESTADO = "notificaciones_cron_2_dias_antes_estado"

_ESTADOS_TERMINALES_DIA = frozenset({"ok", "error", "omitido_tipo"})


def debe_omitir_cron_por_estado_persistido(estado: Dict[str, Any], hoy_iso: str) -> bool:
    """True si ya se registró resultado terminal para esa fecha Caracas (idempotencia diaria)."""
    return (
        (estado.get("fecha_referencia_caracas") or "") == hoy_iso
        and (estado.get("estado") or "") in _ESTADOS_TERMINALES_DIA
    )


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


def ejecutar_cron_pago_2_dias_antes(db: Session) -> Dict[str, Any]:
    """
    Ejecuta el envío PAGO_2_DIAS_ANTES_PENDIENTE para hoy (Caracas) si aplica.

    Respeta habilitado=False en notificaciones_envios para esa fila (no envía; estado omitido_tipo).
    Reintenta ante excepciones CRON_2_DIAS_ANTES_INTENTOS_JOB veces con pausa configurable.
    """
    from app.api.v1.endpoints.notificaciones_tabs import ejecutar_envio_caso_manual

    hoy = hoy_negocio()
    hoy_s = hoy.isoformat()
    prev = _cargar_estado(db)
    if debe_omitir_cron_por_estado_persistido(prev, hoy_s):
        logger.info(
            "[cron_2d] omitido: ya hubo resultado terminal hoy (%s) estado=%s",
            hoy_s,
            prev.get("estado"),
        )
        return {
            "omitido": True,
            "motivo": "ya_resultado_terminal_hoy",
            "fecha_referencia_caracas": hoy_s,
            "estado_previo": prev.get("estado"),
        }

    cfg = get_notificaciones_envios_dict(db)
    tipo_cfg = cfg.get("PAGO_2_DIAS_ANTES_PENDIENTE")
    if isinstance(tipo_cfg, dict) and tipo_cfg.get("habilitado") is False:
        fin = datetime.now(timezone.utc).isoformat()
        _persistir_estado(
            db,
            {
                "fecha_referencia_caracas": hoy_s,
                "estado": "omitido_tipo",
                "fin_utc": fin,
                "motivo": "PAGO_2_DIAS_ANTES_PENDIENTE habilitado=false en notificaciones_envios",
            },
        )
        db.commit()
        logger.info("[cron_2d] omitido: envío desactivado para PAGO_2_DIAS_ANTES_PENDIENTE")
        return {
            "omitido": True,
            "motivo": "tipo_deshabilitado_config",
            "fecha_referencia_caracas": hoy_s,
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
                "PAGO_2_DIAS_ANTES_PENDIENTE",
                fecha_referencia=None,
                respetar_toggle_envio=True,
            )
            fin = datetime.now(timezone.utc).isoformat()
            _persistir_estado(
                db,
                {
                    "fecha_referencia_caracas": hoy_s,
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
                "[cron_2d] ok fecha=%s enviados=%s total_lista=%s fallidos=%s intento=%s/%s",
                hoy_s,
                out.get("enviados"),
                out.get("total_en_lista"),
                out.get("fallidos"),
                attempt,
                max_try,
            )
            return {"omitido": False, "fecha_referencia_caracas": hoy_s, **out}
        except Exception as e:
            last_exc = e
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(
                "[cron_2d] intento %s/%s falló: %s",
                attempt,
                max_try,
                e,
                exc_info=attempt == max_try,
            )
            if attempt < max_try:
                time.sleep(sleep_s)

    fin = datetime.now(timezone.utc).isoformat()
    err_msg = str(last_exc)[:2000] if last_exc else "error_desconocido"
    _persistir_estado(
        db,
        {
            "fecha_referencia_caracas": hoy_s,
            "estado": "error",
            "fin_utc": fin,
            "error": err_msg,
            "intentos": max_try,
        },
    )
    db.commit()
    logger.error("[cron_2d] error definitivo fecha=%s tras %s intentos", hoy_s, max_try)
    return {
        "omitido": False,
        "error": True,
        "fecha_referencia_caracas": hoy_s,
        "mensaje": err_msg,
        "intentos": max_try,
    }


def job_cron_pago_2_dias_antes_scheduler() -> None:
    """Punto de entrada APScheduler: sesión propia."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        ejecutar_cron_pago_2_dias_antes(db)
    except Exception as e:
        logger.exception("[cron_2d] job no controlado: %s", e)
    finally:
        db.close()
