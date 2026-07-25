# -*- coding: utf-8 -*-
"""
Cron «2 días antes» (PAGO_2_DIAS_ANTES_PENDIENTE): desactivado por política.

Toda la cobranza por segmento es solo manual (POST /enviar-caso-manual).
Esta función permanece como stub idempotente por si algún despliegue antiguo
aún registra el job o ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES=True.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

CLAVE_CRON_2_DIAS_ESTADO = "notificaciones_cron_2_dias_antes_estado"

_ESTADOS_TERMINALES_DIA = frozenset({"ok", "error", "omitido_tipo"})


def debe_omitir_cron_por_estado_persistido(estado: Dict[str, Any], hoy_iso: str) -> bool:
    """Compat: True si ya hubo resultado terminal ese día (API de tests legacy)."""
    return (
        (estado.get("fecha_referencia_caracas") or "") == hoy_iso
        and (estado.get("estado") or "") in _ESTADOS_TERMINALES_DIA
    )


def ejecutar_cron_pago_2_dias_antes(db: Session) -> Dict[str, Any]:
    """
    No envía correos. «3 días antes» solo vía POST /enviar-caso-manual.
    """
    del db  # firma estable para callers/tests
    hoy = hoy_negocio()
    logger.info(
        "[cron_2d] omitido: politica solo-manual fecha=%s",
        hoy.isoformat(),
    )
    return {
        "omitido": True,
        "motivo": "politica_solo_manual",
        "fecha_referencia_caracas": hoy.isoformat(),
    }


def job_cron_pago_2_dias_antes_scheduler() -> None:
    """Punto de entrada APScheduler (si se registrara): no envía."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        ejecutar_cron_pago_2_dias_antes(db)
    except Exception as e:
        logger.exception("[cron_2d] job no controlado: %s", e)
    finally:
        db.close()
