# -*- coding: utf-8 -*-
"""Ejecuta lotes de notificaciones en hilo independiente del ciclo HTTP.

Controles anti-corte:
- daemon=False: el worker no descarta el hilo al salir de la request HTTP.
- wait_envios_activos: on_shutdown espera a terminar el lote (hasta graceful-timeout).
- marcar_lotes_interrumpidos_por_shutdown: si aun asi corta, cierra el resumen en BD.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[str, threading.Thread] = {}

# Tope de espera en shutdown (s). Alineado a --graceful-timeout 900 con margen.
SHUTDOWN_WAIT_ENVIO_BG_SEC = 850.0


def job_activo(clave: str) -> bool:
    with _lock:
        t = _active.get(clave)
        return t is not None and t.is_alive()


def claves_activas() -> list[str]:
    with _lock:
        return [k for k, t in _active.items() if t is not None and t.is_alive()]


def hay_envios_activos() -> bool:
    return bool(claves_activas())


def wait_envios_activos(timeout_sec: Optional[float] = None) -> bool:
    """
    Bloquea hasta que no queden hilos de envio vivos, o hasta timeout.
    Returns True si todos terminaron; False si agoto el tiempo.
    """
    limite = SHUTDOWN_WAIT_ENVIO_BG_SEC if timeout_sec is None else float(timeout_sec)
    if limite < 0:
        limite = 0.0
    deadline = time.monotonic() + limite
    while True:
        vivos = claves_activas()
        if not vivos:
            return True
        if time.monotonic() >= deadline:
            logger.warning(
                "[notif_bg] wait_envios_activos timeout=%.0fs claves_aun_vivas=%s",
                limite,
                vivos,
            )
            return False
        time.sleep(0.5)


def marcar_lotes_interrumpidos_por_shutdown() -> None:
    """
    Si queda un lote en_proceso en BD al morir el worker, lo cierra con error claro
    para que la UI no quede en «Enviando…» eterno.
    """
    try:
        from app.core.database import SessionLocal
        from app.services.notificaciones_envio_batch_resumen import (
            get_ultimo_envio_batch_dict,
            persist_ultimo_envio_batch,
            _lote_marca_en_proceso,
        )

        db = SessionLocal()
        try:
            ultimo = get_ultimo_envio_batch_dict(db)
            if not isinstance(ultimo, dict) or not _lote_marca_en_proceso(ultimo):
                return
            det = ultimo.get("detalles") if isinstance(ultimo.get("detalles"), dict) else {}
            detalles = dict(det)
            detalles["en_proceso"] = False
            detalles["cerrado_por_shutdown"] = True
            persist_ultimo_envio_batch(
                db,
                resultado={
                    "enviados": int(ultimo.get("enviados") or 0),
                    "fallidos": int(ultimo.get("fallidos") or 0),
                    "sin_email": int(ultimo.get("sin_email") or 0),
                    "omitidos_config": int(ultimo.get("omitidos_config") or 0),
                    "omitidos_paquete_incompleto": int(
                        ultimo.get("omitidos_paquete_incompleto") or 0
                    ),
                    "enviados_whatsapp": int(ultimo.get("enviados_whatsapp") or 0),
                    "fallidos_whatsapp": int(ultimo.get("fallidos_whatsapp") or 0),
                    "detalles": detalles,
                    "total_en_lista": ultimo.get("total_en_lista"),
                    "tipo_caso": ultimo.get("tipo_caso"),
                    "omitidos_desistimiento": ultimo.get("omitidos_desistimiento"),
                    "omitidos_ya_enviado": ultimo.get("omitidos_ya_enviado"),
                    "omitidos_ya_pagado": ultimo.get("omitidos_ya_pagado"),
                },
                origen=str(ultimo.get("origen") or "desconocido"),
                error="worker_shutdown_interrumpio_lote_notif",
                inicio_utc=str(ultimo.get("inicio_utc") or "") or None,
                en_proceso=False,
            )
            db.commit()
            logger.warning(
                "[notif_bg] lote cerrado por shutdown tipo=%s enviados=%s/%s",
                ultimo.get("tipo_caso"),
                ultimo.get("enviados"),
                ultimo.get("total_en_lista"),
            )
        except Exception:
            db.rollback()
            logger.exception("[notif_bg] no se pudo cerrar lote en shutdown")
        finally:
            db.close()
    except Exception:
        logger.exception("[notif_bg] marcar_lotes_interrumpidos_por_shutdown fallo")


def spawn_envio_bg(
    clave: str,
    target: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> bool:
    clave = (clave or "").strip() or "default"

    def _runner() -> None:
        try:
            logger.info("[notif_bg] inicio clave=%s", clave)
            target(*args, **kwargs)
            logger.info("[notif_bg] fin ok clave=%s", clave)
        except Exception:
            logger.exception("[notif_bg] fin error clave=%s", clave)
        finally:
            with _lock:
                cur = _active.get(clave)
                if cur is threading.current_thread():
                    _active.pop(clave, None)

    with _lock:
        cur = _active.get(clave)
        if cur is not None and cur.is_alive():
            logger.warning("[notif_bg] omitido: ya activo clave=%s", clave)
            return False
        # daemon=False: permite que on_shutdown / graceful-timeout esperen el lote.
        t = threading.Thread(
            target=_runner,
            name="notif-envio-" + clave,
            daemon=False,
        )
        _active[clave] = t
        t.start()
        return True
