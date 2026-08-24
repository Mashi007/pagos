# -*- coding: utf-8 -*-
"""
Cierre de revisión manual (Guardar y Cerrar).

Flujo estable:
1) Persiste cliente / préstamo / cuotas (o reconstruye cuotas si cambió fecha).
2) Aplica cascada de pagos → cuotas.
3) Marca estado_revision=revisado (solo al final, si todo OK).

El pipeline corre en el mismo HTTP request (no en un hilo huérfano). En Render
el recycle del worker mata hilos post-202 y deja pagos conciliados sin cuota_pagos.
La UI navega de inmediato; axios y el poller siguen el request hasta el 200.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[int, threading.Thread] = {}

CLAVE_CFG_PREFIX = "revision_manual_cerrar_bg:"


def job_activo(prestamo_id: int) -> bool:
    with _lock:
        t = _active.get(int(prestamo_id))
        return t is not None and t.is_alive()


def hay_cierres_activos() -> bool:
    """True si hay al menos un hilo de Guardar y cerrar vivo (keepalive Gunicorn)."""
    with _lock:
        return any(t is not None and t.is_alive() for t in _active.values())


def mark_en_proceso(
    db,
    prestamo_id: int,
    *,
    token: str,
    actor: str = "",
    fase: str = "aceptado",
) -> None:
    """Persiste en_proceso antes de devolver 202 (el hilo puede tardar en arrancar)."""
    _persist_status(
        db,
        int(prestamo_id),
        {
            "estado": "en_proceso",
            "en_proceso": True,
            "token": token,
            "fase": fase,
            "actor": actor or None,
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
            "[rev_cerrar_bg] no se pudo persistir status prestamo_id=%s", prestamo_id
        )


def _status_stale_en_proceso(data: Dict[str, Any], *, max_age_sec: int = 45 * 60) -> bool:
    """True si el job quedó marcado en_proceso demasiado tiempo (reinicio / crash)."""
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
        # También refleja hilo vivo sin fila aún.
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
        # No asumir interrupción solo porque este proceso no tiene el hilo
        # (otra instancia / worker puede estar ejecutándolo). Solo si está rancio.
        if _status_stale_en_proceso(data):
            data["estado"] = "interrumpido"
            data["en_proceso"] = False
            data["error"] = data.get("error") or (
                "El cierre en segundo plano se interrumpió (reinicio del servidor). "
                "Reabra la revisión y vuelva a Guardar y cerrar."
            )
        else:
            data["en_proceso"] = True
    else:
        data["en_proceso"] = False
    return data


def _run_pipeline(
    prestamo_id: int,
    *,
    payload: Dict[str, Any],
    actor: str,
    usuario_id: Optional[int],
    usuario_email: Optional[str],
) -> None:
    from app.core.database import SessionLocal
    from app.models.cliente import Cliente
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo
    from app.models.revision_manual_prestamo import RevisionManualPrestamo
    from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline
    from sqlalchemy import select

    db = SessionLocal()
    token = str(payload.get("token") or "")
    user = None
    try:
        if usuario_id is not None:
            from app.models.user import User

            user = db.get(User, int(usuario_id))
    except Exception:
        user = None
    try:
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "inicio",
                "actor": actor,
            },
        )

        from app.services.revision_manual_cascada_bg import esperar_fin_cascada_bg

        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "esperando_cascada_pagos",
                "actor": actor,
            },
        )
        esperar_fin_cascada_bg(int(prestamo_id))

        # --- Imports locales de helpers de revisión (evita ciclos al cargar). ---
        from app.api.v1.endpoints.revision_manual.routes import (
            ClienteUpdateData,
            CuotaUpdateData,
            PrestamoUpdateData,
            _aplicar_saldo_cero_si_corresponde,
            _commit_revision_seguro,
            _mutar_prestamo_desde_update_data_revision,
            _sincronizar_finiquito_tras_revision_manual,
            _sync_fecha_registro_con_aprobacion_en_revision,
        )
        from app.services.revision_manual.revision_manual_flags import (
            marcar_o_crear_prestamo_editado_en_revision_manual,
        )
        from app.constants.prestamo_estados import prestamo_estado_exige_fecha_aprobacion
        from app.services.prestamos.fechas_prestamo_coherencia import (
            alinear_fecha_aprobacion_y_base_calculo,
            rellenar_fecha_aprobacion_desde_base_si_falta,
        )
        from app.services.prestamos.prestamo_cedula_cliente_coherencia import (
            PrestamoCedulaClienteError,
            asegurar_prestamo_alineado_con_cliente,
        )

        prestamo = db.get(Prestamo, prestamo_id)
        if not prestamo:
            raise RuntimeError("Préstamo no encontrado")

        cliente_raw = payload.get("cliente") or {}
        prestamo_raw = payload.get("prestamo") or {}
        cuotas_raw = payload.get("cuotas") or []
        # reconstruir_cuotas: solo si el cliente lo pide explícitamente (raro).
        # Por defecto, al cambiar fecha de aprobación/base → solo vencimientos
        # (misma regla que PUT revisión / recalcular-fechas-amortizacion).
        reconstruir = bool(payload.get("reconstruir_cuotas"))
        forzar_recalc_fechas = bool(payload.get("recalcular_vencimientos"))
        aplicar_cascada = bool(payload.get("aplicar_cascada", True))
        cliente_id = payload.get("cliente_id")

        from app.services.prestamos.fechas_prestamo_coherencia import (
            fecha_para_amortizacion as _fecha_para_amortizacion,
        )
        from sqlalchemy import func

        # 1) Cliente
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "cliente",
            },
        )
        if cliente_id and isinstance(cliente_raw, dict) and cliente_raw:
            cliente = db.get(Cliente, int(cliente_id))
            if cliente and (
                prestamo.cliente_id is None or int(prestamo.cliente_id) == int(cliente_id)
            ):
                upd = ClienteUpdateData(**{
                    k: v
                    for k, v in cliente_raw.items()
                    if k
                    in (
                        "nombres",
                        "telefono",
                        "email",
                        "direccion",
                        "ocupacion",
                        "estado",
                        "fecha_nacimiento",
                        "notas",
                    )
                })
                # Reusar mutaciones del endpoint (inline mínimo, mismo criterio).
                if upd.nombres is not None and str(upd.nombres).strip():
                    cliente.nombres = upd.nombres
                if upd.telefono is not None and str(upd.telefono).strip():
                    cliente.telefono = upd.telefono
                if upd.email is not None and str(upd.email).strip():
                    cliente.email = upd.email
                if upd.direccion is not None and str(upd.direccion).strip():
                    cliente.direccion = upd.direccion
                if upd.ocupacion is not None and str(upd.ocupacion).strip():
                    cliente.ocupacion = upd.ocupacion
                if upd.estado is not None and str(upd.estado).strip():
                    cliente.estado = str(upd.estado).strip().upper()
                if upd.fecha_nacimiento is not None and str(upd.fecha_nacimiento).strip():
                    try:
                        cliente.fecha_nacimiento = datetime.strptime(
                            str(upd.fecha_nacimiento).strip()[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                if upd.notas is not None:
                    cliente.notas = upd.notas
                db.commit()

        # 2) Préstamo + vencimientos (recalcular fechas; no reconstruir montos)
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "prestamo_cuotas",
            },
        )
        stats_recalc_fechas: Dict[str, Any] = {}
        stats_reconstruccion: Dict[str, Any] = {}
        fecha_base_amort_antes = _fecha_para_amortizacion(prestamo)
        if isinstance(prestamo_raw, dict) and prestamo_raw:
            update_data = PrestamoUpdateData(**{
                k: v
                for k, v in prestamo_raw.items()
                if k in PrestamoUpdateData.model_fields
            })
            cambios_dict = _mutar_prestamo_desde_update_data_revision(
                db, prestamo, prestamo_id, update_data
            )
            if cambios_dict or reconstruir or forzar_recalc_fechas:
                rellenar_fecha_aprobacion_desde_base_si_falta(prestamo)
                alinear_fecha_aprobacion_y_base_calculo(prestamo)
                if cambios_dict:
                    _sync_fecha_registro_con_aprobacion_en_revision(
                        prestamo, cambios_dict
                    )
                if (
                    prestamo_estado_exige_fecha_aprobacion(prestamo.estado)
                    and prestamo.fecha_aprobacion is None
                ):
                    raise RuntimeError(
                        "Falta la fecha de aprobación; no se puede cerrar la revisión."
                    )
                try:
                    asegurar_prestamo_alineado_con_cliente(db, prestamo)
                except PrestamoCedulaClienteError as e:
                    raise RuntimeError(str(e)) from e
                prestamo.fecha_actualizacion = datetime.now()
                marcar_o_crear_prestamo_editado_en_revision_manual(db, prestamo_id)
                _sincronizar_finiquito_tras_revision_manual(
                    db, prestamo_id, "cerrar_bg_prestamo"
                )
                _commit_revision_seguro(
                    db,
                    operacion="cerrar_bg_prestamo",
                    actor=actor,
                    tabla_principal="prestamos",
                    id_principal=prestamo_id,
                    resumen_campos=list((cambios_dict or {}).keys()) or ["prestamo"],
                )

            fecha_base = _fecha_para_amortizacion(prestamo)
            existentes = (
                db.scalar(
                    select(func.count()).select_from(Cuota).where(
                        Cuota.prestamo_id == prestamo_id
                    )
                )
                or 0
            )
            debe_recalc = bool(
                existentes > 0
                and fecha_base
                and (
                    forzar_recalc_fechas
                    or (fecha_base != fecha_base_amort_antes)
                )
            )

            if reconstruir:
                from app.api.v1.endpoints.prestamos import (
                    _reconstruir_tabla_cuotas_desde_prestamo_en_sesion,
                )

                stats_reconstruccion = _reconstruir_tabla_cuotas_desde_prestamo_en_sesion(
                    db, prestamo_id
                )
                _sincronizar_finiquito_tras_revision_manual(
                    db, prestamo_id, "cerrar_bg_reconstruir"
                )
                _commit_revision_seguro(
                    db,
                    operacion="cerrar_bg_reconstruir",
                    actor=actor,
                    tabla_principal="prestamos",
                    id_principal=prestamo_id,
                    resumen_campos=["reconstruccion_cuotas"],
                )
                debe_recalc = False
            elif debe_recalc:
                from app.api.v1.endpoints.prestamos import (
                    _recalcular_fechas_vencimiento_cuotas,
                )

                _persist_status(
                    db,
                    prestamo_id,
                    {
                        "estado": "en_proceso",
                        "en_proceso": True,
                        "token": token,
                        "fase": "vencimientos",
                    },
                )
                stats_recalc_fechas = _recalcular_fechas_vencimiento_cuotas(
                    db, prestamo, fecha_base
                )
                db.commit()

        # 3) Cuotas puntuales (solo si NO se reconstruyó ni se recalcularon vencimientos)
        skip_cuotas_cliente = reconstruir or bool(stats_recalc_fechas)
        if not skip_cuotas_cliente and isinstance(cuotas_raw, list) and cuotas_raw:
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "en_proceso",
                    "en_proceso": True,
                    "token": token,
                    "fase": "cuotas",
                },
            )
            for item in cuotas_raw:
                if not isinstance(item, dict):
                    continue
                cid = item.get("cuota_id")
                try:
                    cid_i = int(cid)
                except (TypeError, ValueError):
                    continue
                cuota = db.get(Cuota, cid_i)
                if not cuota or int(cuota.prestamo_id) != int(prestamo_id):
                    continue
                upd_c = CuotaUpdateData(
                    **{
                        k: v
                        for k, v in item.items()
                        if k
                        in (
                            "fecha_pago",
                            "fecha_vencimiento",
                            "monto",
                            "total_pagado",
                            "estado",
                            "observaciones",
                        )
                    }
                )
                if upd_c.fecha_pago is not None:
                    try:
                        cuota.fecha_pago = datetime.strptime(
                            str(upd_c.fecha_pago)[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                if upd_c.fecha_vencimiento is not None:
                    try:
                        cuota.fecha_vencimiento = datetime.strptime(
                            str(upd_c.fecha_vencimiento)[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                if upd_c.monto is not None and float(upd_c.monto) >= 0:
                    cuota.monto = upd_c.monto
                if upd_c.total_pagado is not None and float(upd_c.total_pagado) >= 0:
                    cuota.total_pagado = upd_c.total_pagado
                if upd_c.estado is not None:
                    cuota.estado = str(upd_c.estado).upper()
                if upd_c.observaciones is not None:
                    cuota.observaciones = upd_c.observaciones
                cuota.actualizado_en = datetime.now()
            db.commit()

        # 4) Cascada (lock PG por préstamo; no marcar revisado si falla).
        # DESISTIMIENTO: guardar y cerrar sin cascada (congelado; fuera de mora/stats).
        cascada_out: Dict[str, Any] = {}
        try:
            db.refresh(prestamo)
        except Exception:
            prestamo = db.get(Prestamo, prestamo_id)
        estado_actual = (getattr(prestamo, "estado", None) if prestamo else None) or ""
        est_u = str(estado_actual).strip().upper()
        if est_u in ("DESISTIMIENTO", "DESESTIMADO", "DESISTIDO"):
            aplicar_cascada = False
            logger.info(
                "[rev_cerrar_bg] prestamo_id=%s omitir cascada: estado=%s",
                prestamo_id,
                est_u,
            )
        if aplicar_cascada:
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "en_proceso",
                    "en_proceso": True,
                    "token": token,
                    "fase": "cascada",
                },
            )
            cascada_out = (
                aplicar_cascada_prestamo_pipeline(int(prestamo_id), db, user=user)
                or {}
            )
            if cascada_out.get("ok") is False:
                raise RuntimeError(
                    str(
                        cascada_out.get("error")
                        or cascada_out.get("mensaje")
                        or "La cascada de pagos a cuotas no se completó."
                    )
                )
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "en_proceso",
                    "en_proceso": True,
                    "token": token,
                    "fase": "cascada_ok",
                },
            )
        else:
            _persist_status(
                db,
                prestamo_id,
                {
                    "estado": "en_proceso",
                    "en_proceso": True,
                    "token": token,
                    "fase": "cascada_omitida",
                    "motivo_omitir_cascada": est_u or "aplicar_cascada=false",
                },
            )

        # 5) Finalizar (revisado) — solo si llegamos aquí
        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "en_proceso",
                "en_proceso": True,
                "token": token,
                "fase": "finalizar",
            },
        )
        prestamo = db.get(Prestamo, prestamo_id)
        if not prestamo:
            raise RuntimeError("Préstamo no encontrado al finalizar")

        from app.constants.prestamo_estados import prestamo_estado_exige_fecha_aprobacion

        if (
            prestamo_estado_exige_fecha_aprobacion(prestamo.estado)
            and prestamo.fecha_aprobacion is None
        ):
            raise RuntimeError(
                "No se puede finalizar: falta la fecha de aprobación en el préstamo."
            )

        rev_manual = (
            db.execute(
                select(RevisionManualPrestamo).where(
                    RevisionManualPrestamo.prestamo_id == prestamo_id
                )
            )
            .scalars()
            .first()
        )
        if not rev_manual:
            rev_manual = RevisionManualPrestamo(
                prestamo_id=prestamo_id,
                estado_revision="revisado",
                usuario_revision_email=usuario_email,
                fecha_revision=datetime.now(),
            )
            db.add(rev_manual)
        else:
            rev_manual.estado_revision = "revisado"
            rev_manual.usuario_revision_email = usuario_email
            rev_manual.fecha_revision = datetime.now()

        _aplicar_saldo_cero_si_corresponde(db, prestamo)
        _sincronizar_finiquito_tras_revision_manual(
            db, prestamo_id, "cerrar_bg_finalizar"
        )
        _commit_revision_seguro(
            db,
            operacion="cerrar_bg_finalizar",
            actor=actor,
            tabla_principal="revision_manual_prestamos+prestamos",
            id_principal=prestamo_id,
            resumen_campos=["estado_revision=revisado"],
        )

        _persist_status(
            db,
            prestamo_id,
            {
                "estado": "ok",
                "en_proceso": False,
                "token": token,
                "fase": "listo",
                "recalc_vencimientos": stats_recalc_fechas or None,
                "reconstruccion_cuotas": stats_reconstruccion or None,
                "cascada": {
                    "pagos_con_aplicacion": cascada_out.get("pagos_con_aplicacion"),
                    "mensaje": cascada_out.get("mensaje"),
                }
                if cascada_out
                else None,
            },
        )
        logger.info(
            "[rev_cerrar_bg] ok prestamo_id=%s token=%s cascada=%s",
            prestamo_id,
            token,
            cascada_out.get("pagos_con_aplicacion"),
        )
    except Exception as e:
        logger.exception("[rev_cerrar_bg] error prestamo_id=%s", prestamo_id)
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
                    "error": str(e)[:800],
                },
            )
        except Exception:
            logger.exception(
                "[rev_cerrar_bg] no se pudo guardar error prestamo_id=%s", prestamo_id
            )
    finally:
        try:
            db.close()
        except Exception:
            pass


def run_cerrar_en_request(
    prestamo_id: int,
    *,
    payload: Dict[str, Any],
    actor: str,
    usuario_id: Optional[int],
    usuario_email: Optional[str],
) -> bool:
    """
    Ejecuta el pipeline en este request (misma idea que guardar pago + cascada).
    Returns False si ya hay un cierre activo para el préstamo.
    """
    pid = int(prestamo_id)
    with _lock:
        cur = _active.get(pid)
        if cur is not None and cur.is_alive() and cur is not threading.current_thread():
            logger.warning(
                "[rev_cerrar_bg] omitido in-request: ya activo prestamo_id=%s", pid
            )
            return False
        _active[pid] = threading.current_thread()
    try:
        _run_pipeline(
            pid,
            payload=payload,
            actor=actor,
            usuario_id=usuario_id,
            usuario_email=usuario_email,
        )
        return True
    finally:
        with _lock:
            if _active.get(pid) is threading.current_thread():
                _active.pop(pid, None)


def spawn_cerrar_bg(
    prestamo_id: int,
    *,
    payload: Dict[str, Any],
    actor: str,
    usuario_id: Optional[int],
    usuario_email: Optional[str],
) -> bool:
    """
    Arranca el worker. Returns False si ya hay uno activo para el préstamo.
    Preferir run_cerrar_en_request: el hilo no sobrevive al recycle de Render.
    """
    pid = int(prestamo_id)

    def _runner() -> None:
        try:
            _run_pipeline(
                pid,
                payload=payload,
                actor=actor,
                usuario_id=usuario_id,
                usuario_email=usuario_email,
            )
        finally:
            with _lock:
                cur = _active.get(pid)
                if cur is threading.current_thread():
                    _active.pop(pid, None)

    with _lock:
        cur = _active.get(pid)
        if cur is not None and cur.is_alive():
            logger.warning(
                "[rev_cerrar_bg] omitido: ya activo prestamo_id=%s", pid
            )
            return False
        t = threading.Thread(
            target=_runner,
            name=f"rev-cerrar-{pid}",
            daemon=False,
        )
        _active[pid] = t
        t.start()
        return True


def new_token() -> str:
    return uuid.uuid4().hex[:16]
