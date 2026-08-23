# -*- coding: utf-8 -*-
"""
Cascada pagos → cuotas en revisión manual (editar / agregar pago) en segundo plano.

Tras persistir el pago en BD, reconstruye la amortización en un hilo del worker.
Estado en configuracion (misma idea que revision_manual_cerrar_bg) + poller en la UI.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[int, threading.Thread] = {}

CLAVE_CFG_PREFIX = "revision_manual_cascada_bg:"


def job_activo(prestamo_id: int) -> bool:
    with _lock:
        t = _active.get(int(prestamo_id))
        return t is not None and t.is_alive()


def hay_cascadas_activas() -> bool:
    with _lock:
        return any(t is not None and t.is_alive() for t in _active.values())


def mark_en_proceso(
    db,
    prestamo_id: int,
    *,
    token: str,
    pago_id: Optional[int] = None,
    fase: str = "aceptado",
) -> None:
    _persist_status(
        db,
        int(prestamo_id),
        {
            "estado": "en_proceso",
            "en_proceso": True,
            "token": token,
            "fase": fase,
            "pago_id": int(pago_id) if pago_id is not None else None,
        },
    )


def _clave_cfg(prestamo_id: int) -> str:
    return f"{CLAVE_CFG_PREFIX}{int(prestamo_id)}"


def _persist_status(db, prestamo_id: int, body: Dict[str, Any]) -> None:
    from app.models.configuracion import Configuracion

    clave = _clave_cfg(prestamo_id)
    body = dict(body)
    body["prestamo_id"] = int(prestamo_id)
    body["actualizado_en"] = datetime.utcnow().isoformat() + "Z"
    try:
        valor = json.dumps(body, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        body.pop("detalle_error", None)
        valor = json.dumps(body, ensure_ascii=False, default=str)
    row = db.get(Configuracion, clave)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=clave, valor=valor))
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "[rev_cascada_bg] no se pudo persistir status prestamo_id=%s", prestamo_id
        )


def _status_stale_en_proceso(data: Dict[str, Any], *, max_age_sec: int = 45 * 60) -> bool:
    raw = data.get("actualizado_en")
    if not raw or not isinstance(raw, str):
        return True
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00").replace("+00:00", ""))
    except ValueError:
        return True
    age = (datetime.utcnow() - ts.replace(tzinfo=None)).total_seconds()
    return age > max_age_sec


def get_status(db, prestamo_id: int) -> Optional[Dict[str, Any]]:
    from app.models.configuracion import Configuracion

    row = db.get(Configuracion, _clave_cfg(prestamo_id))
    if not row or not row.valor:
        if job_activo(prestamo_id):
            return {
                "prestamo_id": int(prestamo_id),
                "estado": "en_proceso",
                "en_proceso": True,
            }
        return None
    try:
        data = json.loads(row.valor)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    est = str(data.get("estado") or "").strip().lower()
    if job_activo(prestamo_id):
        data["en_proceso"] = True
        if est not in ("en_proceso",):
            data["estado"] = "en_proceso"
    elif est == "en_proceso":
        if _status_stale_en_proceso(data):
            data["estado"] = "interrumpido"
            data["en_proceso"] = False
            data["error"] = data.get("error") or (
                "La cascada en segundo plano se interrumpió (reinicio del servidor). "
                "Vuelva a guardar el pago o use «Aplicar pagos a cuotas» en amortización."
            )
        else:
            data["en_proceso"] = True
    else:
        data["en_proceso"] = False
    return data


def _run_pipeline(
    prestamo_id: int,
    *,
    prestamo_ids: Iterable[int],
    pago_id: Optional[int],
    token: str,
    usuario_id: Optional[int],
) -> None:
    from app.core.database import SessionLocal
    from app.services.pago_huella_funcional import (
        mensaje_409_huella_funcional_con_id,
        primer_par_huella_duplicada_prestamo,
    )
    from app.services.pagos_aplicacion_prestamo import (
        _restaurar_autoconciliacion_pagos_prestamo,
    )
    from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo
    from app.models.usuario import Usuario

    db = SessionLocal()
    user = db.get(Usuario, int(usuario_id)) if usuario_id is not None else None
    try:
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "cascada",
                "pago_id": pago_id,
            },
        )
        ids = sorted({int(p) for p in prestamo_ids if p})
        resultados: List[Dict[str, Any]] = []
        for pid in ids:
            par_dup = primer_par_huella_duplicada_prestamo(db, pid)
            if par_dup is not None:
                raise RuntimeError(
                    f"{mensaje_409_huella_funcional_con_id(par_dup[0])} "
                    f"Duplicado con pagos.id={par_dup[1]}."
                )
            r = reset_y_reaplicar_cascada_prestamo(db, pid, user=user)
            if not r.get("ok"):
                err_sync = str(r.get("error") or "error desconocido")
                raise RuntimeError(
                    f"No se pudo sincronizar amortización del préstamo {pid}: {err_sync}."
                )
            _restaurar_autoconciliacion_pagos_prestamo(int(pid), db)
            resultados.append(
                {
                    "prestamo_id": pid,
                    "pagos_con_aplicacion": r.get("pagos_con_aplicacion"),
                }
            )
        db.commit()
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "ok",
                "en_proceso": False,
                "token": token,
                "fase": "listo",
                "pago_id": pago_id,
                "resultados": resultados,
            },
        )
        logger.info(
            "[rev_cascada_bg] ok prestamo_id=%s pago_id=%s prestamos=%s",
            prestamo_id,
            pago_id,
            ids,
        )
    except Exception as e:
        logger.exception("[rev_cascada_bg] error prestamo_id=%s pago_id=%s", prestamo_id, pago_id)
        try:
            db.rollback()
        except Exception:
            pass
        try:
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "error",
                    "en_proceso": False,
                    "token": token,
                    "pago_id": pago_id,
                    "error": str(e)[:800],
                },
            )
        except Exception:
            logger.exception(
                "[rev_cascada_bg] no se pudo guardar error prestamo_id=%s", prestamo_id
            )
    finally:
        try:
            db.close()
        except Exception:
            pass


def spawn_cascada_bg(
    prestamo_id: int,
    *,
    prestamo_ids: Iterable[int],
    pago_id: Optional[int],
    token: str,
    usuario_id: Optional[int],
) -> bool:
    """Arranca cascada BG. False si ya hay un job activo para ese préstamo."""
    pid = int(prestamo_id)

    def _runner() -> None:
        try:
            _run_pipeline(
                pid,
                prestamo_ids=prestamo_ids,
                pago_id=pago_id,
                token=token,
                usuario_id=usuario_id,
            )
        finally:
            with _lock:
                cur = _active.get(pid)
                if cur is threading.current_thread():
                    _active.pop(pid, None)

    with _lock:
        cur = _active.get(pid)
        if cur is not None and cur.is_alive():
            logger.warning("[rev_cascada_bg] omitido: ya activo prestamo_id=%s", pid)
            return False
        t = threading.Thread(
            target=_runner,
            name=f"rev-cascada-{pid}",
            daemon=False,
        )
        _active[pid] = t
        t.start()
        return True


def new_token() -> str:
    return uuid.uuid4().hex[:16]


def _usuario_id_desde_current_user(current_user) -> Optional[int]:
    if current_user is None:
        return None
    if isinstance(current_user, dict):
        uid = current_user.get("id")
    else:
        uid = getattr(current_user, "id", None)
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def iniciar_cascada_revision_manual(
    db,
    *,
    prestamo_id: int,
    prestamo_ids: Iterable[int],
    pago_id: Optional[int],
    current_user,
) -> Dict[str, Any]:
    """
    Marca en_proceso, arranca hilo. Devuelve {ok, token?, error?, estado?}.
    """
    pid = int(prestamo_id)
    st_prev = get_status(db, pid) or {}
    if job_activo(pid) or st_prev.get("en_proceso"):
        return {
            "ok": False,
            "codigo": "ya_activo",
            "mensaje": "Ya hay una cascada en segundo plano para este préstamo.",
            "estado": st_prev,
        }
    token = new_token()
    mark_en_proceso(db, pid, token=token, pago_id=pago_id, fase="aceptado")
    ok = spawn_cascada_bg(
        pid,
        prestamo_ids=prestamo_ids,
        pago_id=pago_id,
        token=token,
        usuario_id=_usuario_id_desde_current_user(current_user),
    )
    if not ok:
        return {
            "ok": False,
            "codigo": "spawn_fallo",
            "mensaje": "No se pudo iniciar la cascada en segundo plano.",
        }
    return {"ok": True, "token": token, "prestamo_id": pid, "pago_id": pago_id}
