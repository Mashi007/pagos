# -*- coding: utf-8 -*-
"""
Envío diario idempotente de las 9 listas Excel de gestores (cron 18:00 Caracas).

Si el worker de Render estuvo dormido a las 18:00, reintenta a las 19:00, 20:00 y 21:00
y también al arrancar el scheduler (catch-up).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

CLAVE_GESTORES_EMAIL_ESTADO = "cobranza_gestores_email_estado_dia"
_TZ = ZoneInfo("America/Caracas")


def _ahora_caracas() -> datetime:
    return datetime.now(_TZ)


def leer_estado_email_gestores_dia(db: Session) -> Dict[str, Any]:
    row = db.get(Configuracion, CLAVE_GESTORES_EMAIL_ESTADO)
    if row is None or not (row.valor or "").strip():
        return {}
    try:
        data = json.loads(row.valor)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def guardar_estado_email_gestores_dia(db: Session, estado: Dict[str, Any]) -> None:
    payload = json.dumps(estado, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_GESTORES_EMAIL_ESTADO)
    if row is None:
        db.add(Configuracion(clave=CLAVE_GESTORES_EMAIL_ESTADO, valor=payload))
    else:
        row.valor = payload
    db.commit()


def ya_enviado_ok_hoy(db: Session, *, hoy_iso: Optional[str] = None) -> bool:
    hoy = hoy_iso or hoy_negocio().isoformat()
    st = leer_estado_email_gestores_dia(db)
    return (
        (st.get("fecha_referencia_caracas") or "") == hoy
        and (st.get("estado") or "") == "ok"
    )


def estado_email_gestores_para_ui(db: Session) -> Dict[str, Any]:
    """Resumen para dashboard (admin): último intento del día Caracas."""
    hoy = hoy_negocio().isoformat()
    st = leer_estado_email_gestores_dia(db)
    hora = _ahora_caracas().hour
    cron_habilitado = True  # caller puede enriquecer con settings
    return {
        "fecha_referencia_caracas": hoy,
        "estado_hoy": st if (st.get("fecha_referencia_caracas") or "") == hoy else {},
        "enviado_ok_hoy": ya_enviado_ok_hoy(db, hoy_iso=hoy),
        "ventana_cron_activa": 18 <= hora <= 21,
        "hora_caracas": _ahora_caracas().strftime("%H:%M"),
        "cron_habilitado": cron_habilitado,
        "destino": "operaciones@rapicreditca.com",
    }


def ejecutar_gestores_email_cron(db: Session, *, origen: str = "cron") -> Dict[str, Any]:
    """
    Cron / catch-up: no reenvía si ya hubo éxito hoy.
    Fallos (SMTP, etc.) permiten reintento en la siguiente hora.
    """
    from app.core.config import settings
    from app.services.cobranzas.gestores_service import enviar_listas_gestores_email

    if not getattr(settings, "ENABLE_COBRANZA_GESTORES_EMAIL_JOB", True):
        return {"omitido": True, "motivo": "ENABLE_COBRANZA_GESTORES_EMAIL_JOB=false"}

    hoy = hoy_negocio().isoformat()
    if ya_enviado_ok_hoy(db, hoy_iso=hoy):
        logger.info("[gestores] email diario omitido: ya enviado ok fecha=%s origen=%s", hoy, origen)
        return {"omitido": True, "motivo": "ya_enviado_hoy", "fecha_referencia_caracas": hoy}

    hora = _ahora_caracas().hour
    if origen == "cron" and hora < 18:
        return {"omitido": True, "motivo": "antes_de_18h", "hora_caracas": hora}

    logger.info("[gestores] email diario intento fecha=%s origen=%s hora=%s", hoy, origen, hora)
    res = enviar_listas_gestores_email(db, origen=origen)
    estado = {
        "fecha_referencia_caracas": hoy,
        "estado": "ok" if res.get("ok") else "error",
        "origen": origen,
        "hora_caracas": _ahora_caracas().strftime("%H:%M:%S"),
        "adjuntos": res.get("adjuntos"),
        "asunto": res.get("asunto"),
        "error": res.get("error"),
    }
    try:
        guardar_estado_email_gestores_dia(db, estado)
    except Exception:
        logger.exception("[gestores] no se pudo persistir estado email diario")
    return {**res, **estado}


def catch_up_gestores_email_si_pendiente() -> None:
    """Al iniciar scheduler: si pasaron las 18:00 y aún no se envió hoy, intenta una vez."""
    from app.core.config import settings
    from app.core.database import SessionLocal

    if not getattr(settings, "ENABLE_COBRANZA_GESTORES_EMAIL_JOB", True):
        return
    if not getattr(settings, "ENABLE_AUTOMATIC_SCHEDULED_JOBS", False):
        return
    hora = _ahora_caracas().hour
    if hora < 18:
        return
    db = SessionLocal()
    try:
        if ya_enviado_ok_hoy(db):
            return
        ejecutar_gestores_email_cron(db, origen="catch_up_startup")
    except Exception:
        logger.exception("[gestores] catch_up_startup falló")
    finally:
        db.close()
