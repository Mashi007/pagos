# -*- coding: utf-8 -*-
"""
Cron exclusivo: envío automático del caso PAGO_2_DIAS_ANTES_PENDIENTE («2 días antes»).

- No invoca otros tipos de notificación ni «Enviar todas».
- Se registra solo en app.core.scheduler (mismo interruptor ENABLE_AUTOMATIC_SCHEDULED_JOBS).
- Si en BD notificaciones_envios.cron_envio_pago_2_dias_antes.habilitado no es true, el job no hace nada.
- Usa la misma lógica que el envío manual (plantilla, CCO, modo prueba, PDF opcional) pero respeta
  el toggle «Envío» de la fila (respetar_toggle_envio=True).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.notificaciones_envios_store import get_notificaciones_envios_dict

logger = logging.getLogger(__name__)

CRON_CONFIG_KEY = "cron_envio_pago_2_dias_antes"


def _cron_pago_2_dias_habilitado(raw: Dict[str, Any]) -> bool:
    node = raw.get(CRON_CONFIG_KEY)
    if not isinstance(node, dict):
        return False
    v = node.get("habilitado", node.get("enabled"))
    if v is True:
        return True
    if isinstance(v, str) and v.strip().lower() in ("true", "1", "yes", "si", "sí", "on"):
        return True
    return False


def ejecutar_job_cron_pago_2_dias_antes_si_config(db: Session) -> None:
    """
    Invocado por APScheduler a las 03:00 America/Caracas.
    No debe llamarse desde otros jobs ni rutas HTTP.
    """
    raw = get_notificaciones_envios_dict(db)
    if not _cron_pago_2_dias_habilitado(raw):
        logger.info(
            "[%s] Omitido: deshabilitado en configuración (submódulo 2 días antes).",
            CRON_CONFIG_KEY,
        )
        return

    from app.api.v1.endpoints import notificaciones_tabs
    from app.services.notificaciones_envio_batch_resumen import persist_ultimo_envio_batch

    inicio = datetime.now(timezone.utc).isoformat()
    try:
        res = notificaciones_tabs.ejecutar_envio_caso_manual(
            db,
            "PAGO_2_DIAS_ANTES_PENDIENTE",
            fecha_referencia=None,
            respetar_toggle_envio=True,
        )
        para = {k: v for k, v in res.items() if k != "mensaje"}
        para["detalles"] = {
            "tipo_caso": "PAGO_2_DIAS_ANTES_PENDIENTE",
            "origen": CRON_CONFIG_KEY,
        }
        persist_ultimo_envio_batch(
            db,
            resultado=para,
            origen="cron_envio_pago_2_dias_antes_0300",
            inicio_utc=inicio,
        )
        db.commit()
        logger.info(
            "[%s] OK enviados=%s fallidos=%s sin_email=%s omitidos_config=%s",
            CRON_CONFIG_KEY,
            res.get("enviados"),
            res.get("fallidos"),
            res.get("sin_email"),
            res.get("omitidos_config"),
        )
    except Exception as e:
        logger.exception("[%s] Error: %s", CRON_CONFIG_KEY, e)
        try:
            db.rollback()
        except Exception:
            pass
        try:
            persist_ultimo_envio_batch(
                db,
                resultado={},
                origen="cron_envio_pago_2_dias_antes_0300",
                error=str(e)[:5000],
                inicio_utc=inicio,
            )
            db.commit()
        except Exception:
            logger.warning(
                "[%s] No se pudo persistir resumen de error", CRON_CONFIG_KEY, exc_info=True
            )


def job_wrapper_cron_pago_2_dias_antes() -> None:
    """Entrada APScheduler: sesión propia, sin compartir estado con otros jobs."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        ejecutar_job_cron_pago_2_dias_antes_si_config(db)
    finally:
        db.close()
