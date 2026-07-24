# -*- coding: utf-8 -*-
"""
Ultimo resultado del envio masivo (API «Enviar todas»).
Persistido en configuracion para GET /notificaciones/envio-batch/ultimo sin depender de logs.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_ULTIMO_ENVIO_BATCH = "notificaciones_ultimo_envio_batch"


def persist_ultimo_envio_batch(
    db: Session,
    *,
    resultado: Dict[str, Any],
    origen: str,
    error: Optional[str] = None,
    inicio_utc: Optional[str] = None,
    omitido: bool = False,
    omitido_motivo: Optional[str] = None,
    en_proceso: bool = False,
) -> None:
    """Guarda resumen. El llamador hace commit.

    en_proceso=True: lote aún enviando (heartbeat); fin_utc queda null para que el
    cliente no trate el resumen como terminado.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    fin = None if en_proceso else ahora
    body: Dict[str, Any] = {
        "inicio_utc": inicio_utc or ahora,
        "fin_utc": fin,
        "heartbeat_utc": ahora,
        "estado": "en_proceso" if en_proceso else "finalizado",
        "origen": origen,
        "omitido": omitido,
        "omitido_motivo": omitido_motivo,
        "error": error,
        "enviados": int(resultado.get("enviados", 0) or 0),
        "fallidos": int(resultado.get("fallidos", 0) or 0),
        "sin_email": int(resultado.get("sin_email", 0) or 0),
        "omitidos_config": int(resultado.get("omitidos_config", 0) or 0),
        "omitidos_paquete_incompleto": int(resultado.get("omitidos_paquete_incompleto", 0) or 0),
        "enviados_whatsapp": int(resultado.get("enviados_whatsapp", 0) or 0),
        "fallidos_whatsapp": int(resultado.get("fallidos_whatsapp", 0) or 0),
        "detalles": resultado.get("detalles"),
    }
    # Campos opcionales (envío manual por caso: total en lista, tipo, exclusiones)
    if resultado.get("total_en_lista") is not None:
        try:
            body["total_en_lista"] = int(resultado.get("total_en_lista") or 0)
        except (TypeError, ValueError):
            pass
    raw_tc = resultado.get("tipo_caso")
    if raw_tc is not None:
        try:
            s = str(raw_tc).strip()
            if s:
                body["tipo_caso"] = s
        except (TypeError, ValueError):
            pass
    if resultado.get("omitidos_desistimiento") is not None:
        try:
            body["omitidos_desistimiento"] = int(resultado.get("omitidos_desistimiento") or 0)
        except (TypeError, ValueError):
            pass
    if resultado.get("omitidos_ya_enviado") is not None:
        try:
            body["omitidos_ya_enviado"] = int(resultado.get("omitidos_ya_enviado") or 0)
        except (TypeError, ValueError):
            pass
    try:
        valor = json.dumps(body, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning("persist_ultimo_envio_batch: detalles no serializables, omitiendo detalles: %s", e)
        body["detalles"] = None
        valor = json.dumps(body, ensure_ascii=False)
    row = db.get(Configuracion, CLAVE_ULTIMO_ENVIO_BATCH)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_ULTIMO_ENVIO_BATCH, valor=valor))


def get_ultimo_envio_batch_dict(db: Session) -> Optional[Dict[str, Any]]:
    """Devuelve el ultimo resumen o None si no hay."""
    try:
        row = db.get(Configuracion, CLAVE_ULTIMO_ENVIO_BATCH)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.warning("get_ultimo_envio_batch_dict: %s", e)
    return None


def envio_batch_sigue_activo(
    ultimo: Optional[Dict[str, Any]],
    *,
    tipo_caso: Optional[str] = None,
    stale_seconds: int = 600,
) -> bool:
    """True si hay un lote en_proceso con heartbeat reciente.

    Si tipo_caso se indica y el lote activo es de otro tipo, igual bloquea
    (un solo envio SMTP masivo a la vez). Tras stale_seconds se puede relanzar.
    """
    if not isinstance(ultimo, dict):
        return False
    estado = str(ultimo.get("estado") or "").strip().lower()
    det = ultimo.get("detalles")
    det_rec = det if isinstance(det, dict) else {}
    if estado == "finalizado":
        return False
    en_proc = estado == "en_proceso" or bool(det_rec.get("en_proceso"))
    if not en_proc and ultimo.get("fin_utc") not in (None, ""):
        return False
    if not en_proc and ultimo.get("fin_utc") in (None, ""):
        # Legacy / heartbeat sin estado: tratar como activo hasta stale.
        en_proc = True
    if not en_proc:
        return False
    hb = str(ultimo.get("heartbeat_utc") or ultimo.get("inicio_utc") or "").strip()
    if not hb:
        return True
    try:
        hb_norm = hb.replace("Z", "+00:00")
        hb_dt = datetime.fromisoformat(hb_norm)
        if hb_dt.tzinfo is None:
            hb_dt = hb_dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - hb_dt.astimezone(timezone.utc)).total_seconds()
        return age <= float(stale_seconds)
    except Exception:
        return True

