"""Aplicar pagos pendientes a cuotas por préstamo (lógica compartida API + tests sin FastAPI)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, func, not_, select
from sqlalchemy.exc import PendingRollbackError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.pago_autoconciliacion import (
    marcar_pago_autoconciliado,
    pago_preserva_autoconciliacion_sin_cuotas,
)
from app.services.pagos_cascada_aplicacion import _aplicar_pago_a_cuotas_interno
from app.services.pagos_sql_where import (
    _where_pago_elegible_reaplicacion_cascada,
    _where_pago_excluido_operacion,
)

logger = logging.getLogger(__name__)


def detalle_excepcion_db(exc: BaseException, max_len: int = 300) -> str:
    """Mensaje legible para UI/logs; prioriza la causa raíz psycopg/SQLAlchemy."""
    causa: BaseException | None = exc
    while getattr(causa, "__cause__", None) is not None:
        causa = causa.__cause__  # type: ignore[assignment]
    raiz = str(causa or exc).strip()
    envoltorio = str(exc).strip()
    if raiz and raiz != envoltorio and "rolled back" in envoltorio.lower():
        msg = f"{envoltorio[:100]} | Causa: {raiz}"
    else:
        msg = raiz or envoltorio
    return msg[:max_len]


def _db_error_aborta_transaccion(exc: BaseException) -> bool:
    """True si la sesión quedó inválida y no debe seguirse en la misma transacción."""
    if isinstance(exc, PendingRollbackError):
        return True
    if isinstance(exc, SQLAlchemyError):
        return True
    msg = str(exc).lower()
    if "rolled back" in msg and "previous exception" in msg:
        return True
    causa = getattr(exc, "__cause__", None)
    return isinstance(causa, SQLAlchemyError)


def aplicar_pagos_pendientes_prestamo_con_diagnostico(
    prestamo_id: int,
    db: Session,
    *,
    fail_fast: bool = False,
    marcar_liquidado: bool = True,
) -> dict[str, Any]:
    """
    Igual que aplicar_pagos_pendientes_prestamo pero devuelve diagnóstico para UI y soporte.

    diagnostico incluye conteos antes de aplicar y listas de pagos sin abono o con error.
    """
    vacio: dict[str, Any] = {
        "pagos_operativos_sin_cuota_pagos": 0,
        "pagos_elegibles_cascada_sin_cuota_pagos": 0,
        "pagos_no_elegibles_sin_cuota_pagos": 0,
        "pagos_con_intento_sin_abono_ids": [],
        "errores_por_pago": [],
    }
    prestamo_chk = db.get(Prestamo, prestamo_id)
    if prestamo_chk and (prestamo_chk.estado or "").strip().upper() == "DESISTIMIENTO":
        return {"pagos_con_aplicacion": 0, "diagnostico": vacio}

    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    base_operativo = and_(
        Pago.prestamo_id == prestamo_id,
        Pago.monto_pagado > 0,
        ~Pago.id.in_(subq),
        not_(_where_pago_excluido_operacion()),
    )
    n_oper = int(db.scalar(select(func.count()).select_from(Pago).where(base_operativo)) or 0)

    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            _where_pago_elegible_reaplicacion_cascada(),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
    ).scalars().all()

    n_eleg = len(rows)
    n_no_eleg = max(0, n_oper - n_eleg)

    n = 0
    sin_abono: list[int] = []
    errores: list[dict[str, Any]] = []

    for pago in rows:
        try:
            cc, cp = _aplicar_pago_a_cuotas_interno(
                pago, db, marcar_liquidado=marcar_liquidado
            )
            if cc > 0 or cp > 0:
                pago.estado = "PAGADO"
                n += 1
            elif pago_preserva_autoconciliacion_sin_cuotas(pago):
                marcar_pago_autoconciliado(pago)
            else:
                sin_abono.append(int(pago.id))
        except Exception as e:
            logger.warning(
                "aplicar_pagos_pendientes_prestamo prestamo_id=%s pago id=%s: %s",
                prestamo_id,
                pago.id,
                e,
            )
            if fail_fast or _db_error_aborta_transaccion(e):
                raise
            errores.append({"pago_id": int(pago.id), "error": str(e)})

    return {
        "pagos_con_aplicacion": n,
        "diagnostico": {
            "pagos_operativos_sin_cuota_pagos": n_oper,
            "pagos_elegibles_cascada_sin_cuota_pagos": n_eleg,
            "pagos_no_elegibles_sin_cuota_pagos": n_no_eleg,
            "pagos_con_intento_sin_abono_ids": sin_abono,
            "errores_por_pago": errores,
        },
    }


def aplicar_pagos_pendientes_prestamo(
    prestamo_id: int,
    db: Session,
    *,
    fail_fast: bool = False,
    marcar_liquidado: bool = True,
) -> int:
    """
    Aplica a cuotas los pagos del préstamo que aún no tienen enlaces en cuota_pagos.

    Criterio de elegibilidad: conciliado, verificado_concordancia SI, o estado PAGADO;
    excluye anulados/reversados/duplicado declarado.

    No hace commit. Retorna el número de pagos a los que se les aplicó algo (cc o cp > 0).
    """
    return int(
        aplicar_pagos_pendientes_prestamo_con_diagnostico(
            prestamo_id,
            db,
            fail_fast=fail_fast,
            marcar_liquidado=marcar_liquidado,
        )["pagos_con_aplicacion"]
    )


def aplicar_cascada_prestamo_pipeline(
    prestamo_id: int,
    db: Session,
    *,
    reconstruir_completa: bool = False,
) -> dict[str, Any]:
    """
    Pipeline de cascada reutilizable (POST aplicar-pagos-cuotas, finiquito Visto recrear-ocr).

    1) aplicar_pagos_pendientes_prestamo_con_diagnostico
    2) Si hace falta, reset_y_reaplicar_cascada_prestamo
    3) Reglas habituales de LIQUIDADO vía cascada / reset (no hace commit).

    Con reconstruir_completa=True (botón «Aplicar a cuotas (cascada)» en revisión manual)
    siempre reinicia cuota_pagos y reaplica todos los pagos en orden FIFO.
    """
    from app.services.pagos_cascada_mensajes import _mensaje_sin_aplicacion_cascada
    from app.services.pagos_cuotas_reaplicacion import (
        prestamo_requiere_correccion_cascada,
        reset_y_reaplicar_cascada_prestamo,
    )

    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {
            "ok": False,
            "prestamo_id": prestamo_id,
            "error": "Prestamo no encontrado",
        }

    diagnostico: dict[str, Any] = {}
    n = 0
    reaplicacion_completa = False
    detalle_reaplicacion: dict[str, Any] | None = None

    if reconstruir_completa:
        detalle_reaplicacion = reset_y_reaplicar_cascada_prestamo(db, prestamo_id)
        reaplicacion_completa = True
        if not detalle_reaplicacion.get("ok"):
            return {
                "ok": False,
                "prestamo_id": prestamo_id,
                "pagos_con_aplicacion": 0,
                "reaplicacion_completa": True,
                "detalle_reaplicacion": detalle_reaplicacion,
                "diagnostico": diagnostico,
                "error": str(
                    detalle_reaplicacion.get("error")
                    or "No se pudo reconstruir la cascada de cuotas."
                ),
            }
        n = int(detalle_reaplicacion.get("pagos_reaplicados") or 0)
    else:
        res_primera = aplicar_pagos_pendientes_prestamo_con_diagnostico(prestamo_id, db)
        n = int(res_primera.get("pagos_con_aplicacion") or 0)
        diagnostico = dict(res_primera.get("diagnostico") or {})

    if not reconstruir_completa and n == 0 and prestamo_requiere_correccion_cascada(db, prestamo_id):
        detalle_reaplicacion = reset_y_reaplicar_cascada_prestamo(db, prestamo_id)
        reaplicacion_completa = True
        if not detalle_reaplicacion.get("ok"):
            return {
                "ok": False,
                "prestamo_id": prestamo_id,
                "pagos_con_aplicacion": 0,
                "reaplicacion_completa": True,
                "detalle_reaplicacion": detalle_reaplicacion,
                "diagnostico": diagnostico,
                "error": str(
                    detalle_reaplicacion.get("error")
                    or "No se pudo reconstruir la cascada de cuotas."
                ),
            }
        n = int(detalle_reaplicacion.get("pagos_reaplicados") or 0)

    if n > 0:
        if reaplicacion_completa:
            mensaje = (
                f"Amortización recalculada: se reinició la aplicación a cuotas y "
                f"{n} pago(s) quedaron distribuidos (cascada)."
            )
        else:
            mensaje = f"Cascada aplicada: {n} pago(s) con abono efectivo en cuotas."
    elif reaplicacion_completa:
        mensaje = (
            "Tabla de amortización reiniciada; no había pagos elegibles para volver a aplicar "
            "(conciliado / verificado / PAGADO / PENDIENTE con crédito, monto > 0). "
            "Revise la conciliación de los pagos."
        )
    else:
        mensaje = _mensaje_sin_aplicacion_cascada(diagnostico)

    _restaurar_autoconciliacion_pagos_prestamo(prestamo_id, db)

    db.refresh(prestamo)
    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "pagos_con_aplicacion": n,
        "reaplicacion_completa": reaplicacion_completa,
        "detalle_reaplicacion": detalle_reaplicacion,
        "diagnostico": diagnostico,
        "mensaje": mensaje,
        "prestamo_estado": (prestamo.estado or "").strip().upper(),
    }


def _restaurar_autoconciliacion_pagos_prestamo(prestamo_id: int, db: Session) -> int:
    """Tras cascada: reafirma autoconciliación en ABONOS y asientos Conciliar sin cuota_pagos."""
    pagos = db.execute(
        select(Pago).where(Pago.prestamo_id == prestamo_id, Pago.monto_pagado > 0)
    ).scalars().all()
    n = 0
    for pago in pagos:
        if not pago_preserva_autoconciliacion_sin_cuotas(pago):
            continue
        prev = bool(pago.conciliado), str(pago.estado or "").strip().upper()
        marcar_pago_autoconciliado(pago)
        if (not prev[0]) or prev[1] != "PAGADO":
            n += 1
    if n:
        db.flush()
    return n
