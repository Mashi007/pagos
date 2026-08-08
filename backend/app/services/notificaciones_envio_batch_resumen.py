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
    estado: Optional[str] = None,
) -> None:
    """Guarda resumen. El llamador hace commit.

    en_proceso=True: lote aún enviando (heartbeat); fin_utc queda null para que el
    cliente no trate el resumen como terminado.

    estado opcional: p. ej. pausado_limite_gmail (cupo diario; reanudar al dia siguiente).
    """
    ahora = datetime.now(timezone.utc).isoformat()
    fin = None if en_proceso else ahora
    if estado and str(estado).strip():
        estado_final = str(estado).strip()
    else:
        estado_final = "en_proceso" if en_proceso else "finalizado"
    body: Dict[str, Any] = {
        "inicio_utc": inicio_utc or ahora,
        "fin_utc": fin,
        "heartbeat_utc": ahora,
        "estado": estado_final,
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
    if estado in ("finalizado", "pausado_limite_gmail", "cancelado_usuario"):
        return False
    if bool(det_rec.get("pausado_limite_gmail") or det_rec.get("cancelado_usuario")) and estado != "en_proceso":
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


def _lote_marca_en_proceso(ultimo: Dict[str, Any]) -> bool:
    estado = str(ultimo.get("estado") or "").strip().lower()
    if estado in ("finalizado", "pausado_limite_gmail", "cancelado_usuario"):
        return False
    det = ultimo.get("detalles")
    det_rec = det if isinstance(det, dict) else {}
    if bool(det_rec.get("pausado_limite_gmail") or det_rec.get("cancelado_usuario")) and estado != "en_proceso":
        return False
    if estado == "en_proceso" or bool(det_rec.get("en_proceso")):
        return True
    # Legacy: sin fin_utc se consideraba activo
    return ultimo.get("fin_utc") in (None, "")


def finalizar_envio_batch_si_stale(
    db: Session,
    *,
    stale_seconds: int = 600,
) -> Optional[Dict[str, Any]]:
    """
    Cierra lotes en_proceso cuyo heartbeat supera stale_seconds (worker muerto,
    spin-down, deploy). Evita barra «Enviando X de Y» eterna en la UI.
    """
    ultimo = get_ultimo_envio_batch_dict(db)
    if not isinstance(ultimo, dict):
        return ultimo
    if not _lote_marca_en_proceso(ultimo):
        return ultimo
    # Activo con heartbeat reciente: no tocar
    if envio_batch_sigue_activo(ultimo, stale_seconds=stale_seconds):
        return ultimo
    # Marcado en_proceso pero stale -> cerrar
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio

    det = ultimo.get("detalles") if isinstance(ultimo.get("detalles"), dict) else {}
    detalles = dict(det)
    detalles["en_proceso"] = False
    detalles["cerrado_por_stale"] = True
    ini_iso = str(detalles.get("fecha_negocio_inicio") or "").strip()
    if not ini_iso:
        try:
            raw_ini = str(ultimo.get("inicio_utc") or "").strip().replace("Z", "+00:00")
            dt_ini = _dt.fromisoformat(raw_ini) if raw_ini else None
            if dt_ini is not None:
                if dt_ini.tzinfo is None:
                    dt_ini = dt_ini.replace(tzinfo=timezone.utc)
                ini_iso = dt_ini.astimezone(ZoneInfo(TZ_NEGOCIO)).date().isoformat()
        except ValueError:
            ini_iso = ""
    if not ini_iso:
        ini_iso = hoy_negocio().isoformat()
    detalles["fecha_negocio_inicio"] = ini_iso
    detalles["fecha_negocio_pausa"] = hoy_negocio().isoformat()
    try:
        total = int(ultimo.get("total_en_lista") or detalles.get("total_en_lista") or 0)
        procesados = int(detalles.get("procesados") or 0)
    except (TypeError, ValueError):
        total, procesados = 0, 0
    resultado = {
        "enviados": int(ultimo.get("enviados") or 0),
        "fallidos": int(ultimo.get("fallidos") or 0),
        "sin_email": int(ultimo.get("sin_email") or 0),
        "omitidos_config": int(ultimo.get("omitidos_config") or 0),
        "omitidos_paquete_incompleto": int(ultimo.get("omitidos_paquete_incompleto") or 0),
        "enviados_whatsapp": int(ultimo.get("enviados_whatsapp") or 0),
        "fallidos_whatsapp": int(ultimo.get("fallidos_whatsapp") or 0),
        "detalles": detalles,
        "total_en_lista": total or ultimo.get("total_en_lista"),
        "tipo_caso": ultimo.get("tipo_caso"),
        "omitidos_desistimiento": ultimo.get("omitidos_desistimiento"),
        "omitidos_ya_enviado": ultimo.get("omitidos_ya_enviado"),
    }
    persist_ultimo_envio_batch(
        db,
        resultado=resultado,
        origen=str(ultimo.get("origen") or "desconocido"),
        error=(
            "lote_interrumpido_worker_recycle_o_deploy: "
            "reenviar el caso; ya enviados desde el inicio del lote se omiten. "
            "Si se repite, quitar --max-requests del Start Command en Render"
        ),
        inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
        en_proceso=False,
    )
    tipo = str(ultimo.get("tipo_caso") or detalles.get("tipo_caso") or "").strip()
    if tipo and total > 0 and procesados < total:
        try:
            from app.services.notificaciones_lotes_continuar import upsert_lote_continuar

            upsert_lote_continuar(
                db,
                tipo_caso=tipo,
                total_en_lista=total,
                procesados=procesados,
                enviados=int(ultimo.get("enviados") or 0),
                fallidos=int(ultimo.get("fallidos") or 0),
                estado="incompleto",
                fecha_negocio_inicio=ini_iso,
                fecha_negocio_pausa=hoy_negocio().isoformat(),
                inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
                motivo="cerrado_por_stale",
            )
        except Exception:
            logger.warning(
                "finalizar_envio_batch_si_stale: upsert continuar fallo tipo=%s",
                tipo,
                exc_info=True,
            )
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("finalizar_envio_batch_si_stale: commit fallo", exc_info=True)
        return ultimo
    logger.info(
        "finalizar_envio_batch_si_stale: cerrado lote stale tipo=%s procesados~=%s/%s omitir_desde=%s",
        ultimo.get("tipo_caso"),
        detalles.get("procesados"),
        ultimo.get("total_en_lista"),
        ini_iso,
    )
    return get_ultimo_envio_batch_dict(db)
