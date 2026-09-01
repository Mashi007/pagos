# -*- coding: utf-8 -*-
"""Comparar lotes Importación extracto en hilo fuera del ciclo HTTP."""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[int, threading.Thread] = {}


def comparar_activo(lote_id: int) -> bool:
    with _lock:
        t = _active.get(int(lote_id))
        return t is not None and t.is_alive()


def spawn_comparar_extracto(
    lote_id: int,
    parsed: list[dict[str, Any]],
    *,
    solo_serial: bool,
) -> bool:
    """Lanza comparación en background. False si ya hay uno activo para el lote."""
    lid = int(lote_id)
    payload = list(parsed)

    def _runner() -> None:
        from app.core.database import SessionLocal
        from app.services import importacion_extracto_service as svc

        db = SessionLocal()
        try:
            logger.info(
                "[IMPORT_EXTRACTO_BG] inicio lote_id=%s filas=%s solo_serial=%s",
                lid,
                len(payload),
                solo_serial,
            )
            svc.comparar_filas_lote(
                db,
                lid,
                payload,
                solo_serial=solo_serial,
                raise_on_empty=False,
            )
            logger.info("[IMPORT_EXTRACTO_BG] fin ok lote_id=%s", lid)
        except Exception as e:
            logger.exception("[IMPORT_EXTRACTO_BG] fin error lote_id=%s", lid)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                from app.models.importacion_extracto import ImportacionExtractoLote

                lote = db.get(ImportacionExtractoLote, lid)
                if lote:
                    lote.estado = "ERROR"
                    lote.notas = str({"error": str(e)[:500]})
                    db.commit()
            except Exception:
                logger.exception(
                    "[IMPORT_EXTRACTO_BG] no se pudo marcar ERROR lote_id=%s", lid
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
            logger.warning("[IMPORT_EXTRACTO_BG] omitido: ya activo lote_id=%s", lid)
            return False
        t = threading.Thread(
            target=_runner,
            name=f"importacion-extracto-comparar-{lid}",
            daemon=True,
        )
        _active[lid] = t
        t.start()
        return True
