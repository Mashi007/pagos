# -*- coding: utf-8 -*-
"""Comparar lotes Conciliacion Bancos en hilo fuera del ciclo HTTP (evita timeout proxy/cliente)."""
from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[int, threading.Thread] = {}


def comparar_activo(lote_id: int) -> bool:
    with _lock:
        t = _active.get(int(lote_id))
        return t is not None and t.is_alive()


def spawn_comparar_lote(
    lote_id: int,
    *,
    bancos_filtro: list[str],
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> bool:
    """Lanza comparar en background. False si ya hay uno activo para el lote."""
    lid = int(lote_id)

    def _runner() -> None:
        from app.core.database import SessionLocal
        from app.services import conciliacion_bancos_service as svc

        db = SessionLocal()
        try:
            logger.info("[conciliacion-bancos-bg] inicio lote_id=%s", lid)
            svc.comparar_lote(
                db,
                lid,
                bancos_filtro=bancos_filtro,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
            logger.info("[conciliacion-bancos-bg] fin ok lote_id=%s", lid)
        except Exception as e:
            logger.exception("[conciliacion-bancos-bg] fin error lote_id=%s", lid)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                from app.models.conciliacion_banco_ocr import ConciliacionBancoOcrLote
                import json

                lote = db.get(ConciliacionBancoOcrLote, lid)
                if lote:
                    payload: dict[str, Any] = {}
                    raw = (lote.notas or "").strip()
                    if raw:
                        try:
                            data = json.loads(raw)
                            if isinstance(data, dict):
                                payload = data
                        except Exception:
                            payload = {}
                    payload["comparar_error"] = str(e)[:500]
                    lote.notas = json.dumps(payload, ensure_ascii=True)
                    lote.estado = "ERROR_COMPARAR"
                    db.commit()
            except Exception:
                logger.exception(
                    "[conciliacion-bancos-bg] no se pudo marcar ERROR_COMPARAR lote_id=%s",
                    lid,
                )
        finally:
            try:
                db.close()
            except Exception:
                pass
            with _lock:
                cur = _active.get(lid)
                if cur is threading.current_thread():
                    _active.pop(lid, None)

    with _lock:
        cur = _active.get(lid)
        if cur is not None and cur.is_alive():
            logger.warning(
                "[conciliacion-bancos-bg] omitido: ya activo lote_id=%s", lid
            )
            return False
        t = threading.Thread(
            target=_runner,
            name=f"conciliacion-bancos-comparar-{lid}",
            daemon=True,
        )
        _active[lid] = t
        t.start()
        return True
