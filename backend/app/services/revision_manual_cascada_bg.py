# -*- coding: utf-8 -*-
"""
Cascada pagos → cuotas en revisión manual (editar / agregar pago) en segundo plano.

Tras persistir el pago en BD (commit HTTP), reconstruye la amortización en un hilo del worker.
El POST/PUT responde 202 con cascada_en_proceso + token; la UI hace poll
(GET …/cascada-bg/estado). Estado en configuracion + poller global (Layout).
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


def marcar_cascada_ok(
    db,
    prestamo_id: int,
    *,
    pago_id: Optional[int] = None,
) -> None:
    """Cierra el job BG en configuracion para que el poller no marque «interrumpido»."""
    _persist_status(
        db,
        int(prestamo_id),
        {
            "estado": "ok",
            "en_proceso": False,
            "fase": "listo_sync",
            "pago_id": int(pago_id) if pago_id is not None else None,
        },
    )


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
    # No pisar requeue al actualizar fase/token a mitad del job.
    if "requeue" not in body:
        row_prev = db.get(Configuracion, clave)
        if row_prev and row_prev.valor:
            try:
                prev = json.loads(row_prev.valor)
            except (TypeError, ValueError, json.JSONDecodeError):
                prev = None
            if isinstance(prev, dict) and prev.get("requeue"):
                for k in (
                    "requeue",
                    "requeue_prestamo_ids",
                    "requeue_pago_id",
                    "requeue_usuario_id",
                ):
                    if k in prev:
                        body[k] = prev[k]
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


# Sin hilo vivo en este worker: tras este margen se libera la edición (workers=1 en Render).
_GRACE_SIN_HILO_SEC = 3 * 60


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
        interrumpir = False
        if _status_stale_en_proceso(data):
            interrumpir = True
        elif _status_stale_en_proceso(
            data, max_age_sec=_GRACE_SIN_HILO_SEC
        ):
            # Hilo muerto sin actualizar estado (p. ej. crash tras guardar pago).
            interrumpir = True
        if interrumpir:
            data["estado"] = "interrumpido"
            data["en_proceso"] = False
            data["error"] = data.get("error") or (
                "La cascada en segundo plano se interrumpió (reinicio del servidor). "
                "Vuelva a guardar el pago o use «Aplicar pagos a cuotas» en amortización."
            )
            _persist_status(db, int(prestamo_id), data)
        else:
            data["en_proceso"] = True
    else:
        data["en_proceso"] = False
    return data


def esperar_fin_cascada_bg(
    prestamo_id: int,
    *,
    max_espera_sec: int = 3600,
    poll_sec: float = 2.0,
) -> bool:
    """Espera a que termine la cascada BG (p. ej. antes de Guardar y cerrar)."""
    import time

    t0 = time.monotonic()
    while time.monotonic() - t0 < max_espera_sec:
        if not job_activo(int(prestamo_id)):
            return True
        time.sleep(poll_sec)
    return not job_activo(int(prestamo_id))


def marcar_requeue_cascada(
    db,
    prestamo_id: int,
    *,
    prestamo_ids: Iterable[int],
    pago_id: Optional[int],
    usuario_id: Optional[int],
) -> None:
    """
    Si llega otro guardado mientras la cascada corre, marca re-ejecución al terminar.
    Evita pagos conciliados sin cuota_pagos (hueco ya_activo).
    """
    st = get_status(db, int(prestamo_id)) or {}
    prev_ids = st.get("requeue_prestamo_ids") or []
    if not isinstance(prev_ids, list):
        prev_ids = []
    merged = sorted(
        {
            int(x)
            for x in list(prev_ids) + list(prestamo_ids)
            if x is not None and str(x).strip() != ""
        }
    )
    body = dict(st)
    body["estado"] = "en_proceso"
    body["en_proceso"] = True
    body["requeue"] = True
    body["requeue_prestamo_ids"] = merged or sorted(
        {int(p) for p in prestamo_ids if p}
    )
    if pago_id is not None:
        body["requeue_pago_id"] = int(pago_id)
    if usuario_id is not None:
        body["requeue_usuario_id"] = int(usuario_id)
    body["fase"] = "requeue_pendiente"
    _persist_status(db, int(prestamo_id), body)


def _consumir_requeue(db, prestamo_id: int) -> Optional[Dict[str, Any]]:
    """Si hay requeue, lo limpia y devuelve args para un nuevo spawn (sin liberar en_proceso)."""
    st = get_status(db, int(prestamo_id)) or {}
    if not st.get("requeue"):
        return None
    ids_raw = st.get("requeue_prestamo_ids") or [prestamo_id]
    if not isinstance(ids_raw, list):
        ids_raw = [prestamo_id]
    ids = sorted({int(x) for x in ids_raw if x})
    if not ids:
        ids = [int(prestamo_id)]
    pago_rq = st.get("requeue_pago_id")
    user_rq = st.get("requeue_usuario_id")
    token = new_token()
    _persist_status(
        db,
        int(prestamo_id),
        {
            "estado": "en_proceso",
            "en_proceso": True,
            "token": token,
            "fase": "requeue_aceptado",
            "pago_id": int(pago_rq) if pago_rq is not None else None,
            "requeue": False,
        },
    )
    return {
        "prestamo_id": int(prestamo_id),
        "prestamo_ids": ids,
        "pago_id": int(pago_rq) if pago_rq is not None else None,
        "token": token,
        "usuario_id": int(user_rq) if user_rq is not None else None,
    }


def _run_pipeline(
    prestamo_id: int,
    *,
    prestamo_ids: Iterable[int],
    pago_id: Optional[int],
    token: str,
    usuario_id: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    Ejecuta la cascada. Si al final hay requeue (otro pago guardado durante el job),
    no marca ok: devuelve args para re-spawn (el poller sigue viendo en_proceso).
    """
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.services.pago_huella_funcional import (
        mensaje_409_huella_funcional_con_id,
        primer_par_huella_duplicada_prestamo,
    )
    from app.services.pagos_aplicacion_prestamo import (
        _restaurar_autoconciliacion_pagos_prestamo,
    )
    from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo

    db = SessionLocal()
    user = db.get(User, int(usuario_id)) if usuario_id is not None else None
    requeue_args: Optional[Dict[str, Any]] = None
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
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "en_proceso",
                    "en_proceso": True,
                    "token": token,
                    "fase": f"cascada_prestamo_{pid}",
                    "pago_id": pago_id,
                },
            )
            logger.info(
                "[rev_cascada_bg] cascada prestamo_id=%s pid=%s pago_id=%s",
                prestamo_id,
                pid,
                pago_id,
            )
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
        requeue_args = _consumir_requeue(db, prestamo_id)
        if requeue_args:
            logger.info(
                "[rev_cascada_bg] requeue prestamo_id=%s tras ok parcial pago_id=%s",
                prestamo_id,
                pago_id,
            )
            return requeue_args
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
        return None
    except Exception as e:
        logger.exception("[rev_cascada_bg] error prestamo_id=%s pago_id=%s", prestamo_id, pago_id)
        try:
            db.rollback()
        except Exception:
            pass
        # Si falló pero había requeue, igual reintentar con los pagos nuevos.
        try:
            requeue_args = _consumir_requeue(db, prestamo_id)
        except Exception:
            requeue_args = None
        if requeue_args:
            logger.warning(
                "[rev_cascada_bg] error pero requeue activo prestamo_id=%s; se reintenta",
                prestamo_id,
            )
            return requeue_args
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
        return None
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
        next_args: Optional[Dict[str, Any]] = {
            "prestamo_id": pid,
            "prestamo_ids": list(prestamo_ids),
            "pago_id": pago_id,
            "token": token,
            "usuario_id": usuario_id,
        }
        try:
            loops = 0
            max_loops = 8
            while next_args and loops < max_loops:
                loops += 1
                rq = _run_pipeline(
                    int(next_args["prestamo_id"]),
                    prestamo_ids=next_args["prestamo_ids"],
                    pago_id=next_args.get("pago_id"),
                    token=str(next_args["token"]),
                    usuario_id=next_args.get("usuario_id"),
                )
                next_args = rq
            if next_args:
                logger.error(
                    "[rev_cascada_bg] tope de requeue (%s) prestamo_id=%s; marcar error",
                    max_loops,
                    pid,
                )
                from app.core.database import SessionLocal

                db_err = SessionLocal()
                try:
                    _persist_status(
                        db_err,
                        pid,
                        {
                            "estado": "error",
                            "en_proceso": False,
                            "error": (
                                "Demasiadas re-aplicaciones seguidas de cascada. "
                                "Vuelva a guardar el pago o use «Aplicar pagos a cuotas»."
                            ),
                        },
                    )
                finally:
                    db_err.close()
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
        from app.services.pagos_eliminar_coordinacion import eliminacion_activa

        if eliminacion_activa(pid):
            logger.warning(
                "[rev_cascada_bg] omitido: eliminacion activa prestamo_id=%s", pid
            )
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


def normalizar_resultado_iniciar_cascada(cascada_bg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trata requeue (hilo vivo o DELETE en curso) como éxito para no hacer
    fallback síncrono de reset_y_reaplicar a mitad de una eliminación.
    """
    if cascada_bg.get("ok"):
        return cascada_bg
    codigo = str(cascada_bg.get("codigo") or "")
    if codigo in ("ya_activo", "eliminacion_en_proceso") or cascada_bg.get("requeue"):
        st = cascada_bg.get("estado") or {}
        token = cascada_bg.get("token") or st.get("token")
        return {"ok": True, "token": token, "requeue": True}
    return cascada_bg


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
    forzar_spawn: bool = False,
) -> Dict[str, Any]:
    """
    Marca en_proceso, arranca hilo. Devuelve {ok, token?, error?, estado?}.
    Si ya hay job activo, encola requeue (otro pago no queda sin cascada).

    ``forzar_spawn``: arranca aunque configuracion tenga ``en_proceso`` (lock
    fantasma tras DELETE, que marca requeue bajo el mutex de eliminación y
    nunca crea hilo). No ignora un hilo vivo ni una eliminación en curso.
    """
    pid = int(prestamo_id)
    ids = sorted({int(p) for p in prestamo_ids if p}) or [pid]
    uid = _usuario_id_desde_current_user(current_user)
    from app.services.pagos_eliminar_coordinacion import eliminacion_activa

    if eliminacion_activa(pid):
        marcar_requeue_cascada(
            db,
            pid,
            prestamo_ids=ids,
            pago_id=pago_id,
            usuario_id=uid,
        )
        st_now = get_status(db, pid) or {}
        return {
            "ok": False,
            "codigo": "eliminacion_en_proceso",
            "mensaje": (
                "Hay una eliminación de pago en curso; la cascada se encolará al terminar."
            ),
            "estado": st_now,
            "requeue": True,
        }
    st_prev = get_status(db, pid) or {}
    lock_fantasma = bool(st_prev.get("en_proceso")) and not job_activo(pid)
    if job_activo(pid) or (st_prev.get("en_proceso") and not forzar_spawn):
        marcar_requeue_cascada(
            db,
            pid,
            prestamo_ids=ids,
            pago_id=pago_id,
            usuario_id=uid,
        )
        st_now = get_status(db, pid) or st_prev
        return {
            "ok": False,
            "codigo": "ya_activo",
            "mensaje": (
                "Ya hay una cascada en segundo plano; este pago se incluirá "
                "al terminar (requeue)."
            ),
            "estado": st_now,
            "requeue": True,
        }
    if forzar_spawn and lock_fantasma:
        logger.info(
            "[rev_cascada_bg] forzar_spawn: lock fantasma en_proceso sin hilo "
            "prestamo_id=%s requeue=%s",
            pid,
            bool(st_prev.get("requeue")),
        )
    token = new_token()
    mark_en_proceso(db, pid, token=token, pago_id=pago_id, fase="aceptado")
    ok = spawn_cascada_bg(
        pid,
        prestamo_ids=ids,
        pago_id=pago_id,
        token=token,
        usuario_id=uid,
    )
    if not ok:
        # Carrera: otro hilo ganó entre el check y el spawn → requeue.
        marcar_requeue_cascada(
            db,
            pid,
            prestamo_ids=ids,
            pago_id=pago_id,
            usuario_id=uid,
        )
        st_now = get_status(db, pid) or {}
        return {
            "ok": False,
            "codigo": "ya_activo",
            "mensaje": "Cascada concurrente; pago encolado en requeue.",
            "estado": st_now,
            "requeue": True,
        }
    return {"ok": True, "token": token, "prestamo_id": pid, "pago_id": pago_id}
