"""
Aplicación de pagos a cuotas en cascada y marcado de préstamo LIQUIDADO.

Extraído desde endpoints de pagos para reutilización (Cobros, Gmail, scripts, tests vía `app.api.v1.endpoints.pagos`).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.cuota_estado import clasificar_estado_cuota, dias_retraso_desde_vencimiento, hoy_negocio
from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas, validar_suma_aplicada_vs_monto_pago
from app.services.prestamo_db_compat import prestamos_tiene_columna_fecha_liquidado

from app.services.cuota_transiciones_pago import validar_transicion_estado_cuota

logger = logging.getLogger(__name__)


def _estado_cuota_por_cobertura(total_pagado: float, monto_cuota: float, fecha_vencimiento: date) -> str:
    """
    Delega en app.services.cuota_estado (Caracas; VENCIDO hasta umbral de mora; MORA desde 4 meses + 1 dia).
    """
    return clasificar_estado_cuota(total_pagado, monto_cuota, fecha_vencimiento, hoy_negocio())


def _marcar_prestamo_liquidado_si_corresponde(prestamo_id: int, db: Session) -> None:
    """
    Alinea prestamos.estado (APROBADO / LIQUIDADO) con la cobertura real de cuotas.

    Criterio: misma tolerancia que cartera (0.01) sobre cuotas.total_pagado vs monto_cuota.
    Equivale a que la suma aplicada en cuotas cubra el financiamiento; no usa sum(pagos)
    porque puede haber montos duplicados o sobrantes sin cupo en cuotas.

    Opcional (settings.LIQUIDACION_REQUIERE_CUADRE_PAGOS_VS_CUOTAS): ademas exige que la suma de
    pagos operativos cuadre con el total aplicado en cuota_pagos (tol 0.02 USD, misma regla que auditoria).

    - Todas las cuotas cubiertas y estado APROBADO -> LIQUIDADO (+ fecha_liquidado).
    - Alguna cuota con saldo y estado LIQUIDADO -> APROBADO (fecha_liquidado NULL).

    No hace commit.
    """
    cuotas = db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_id)).scalars().all()

    if not cuotas:
        return

    pendientes = sum(1 for c in cuotas if (c.total_pagado or 0) < (float(c.monto) if c.monto else 0) - 0.01)

    prestamo = db.execute(select(Prestamo).where(Prestamo.id == prestamo_id)).scalars().first()

    if not prestamo:
        return

    est = (prestamo.estado or "").upper()

    if est == "DESISTIMIENTO":
        return

    if pendientes == 0:
        if est == "APROBADO":
            if settings.LIQUIDACION_REQUIERE_CUADRE_PAGOS_VS_CUOTAS:
                from app.services.prestamo_cartera_auditoria import (
                    prestamo_cuadrado_pagos_operativos_vs_aplicado,
                    totales_pagos_operativos_y_aplicado_cuotas_prestamo,
                )

                if not prestamo_cuadrado_pagos_operativos_vs_aplicado(db, prestamo_id):
                    sp_t, sa_t = totales_pagos_operativos_y_aplicado_cuotas_prestamo(db, prestamo_id)
                    logger.warning(
                        "Prestamo id=%s: cuotas cubiertas pero pagos operativos no cuadran con aplicado "
                        "(sum_pagos=%s sum_aplicado=%s). No se marca LIQUIDADO "
                        "(LIQUIDACION_REQUIERE_CUADRE_PAGOS_VS_CUOTAS=true).",
                        prestamo_id,
                        sp_t,
                        sa_t,
                    )
                    return

            prestamo.estado = "LIQUIDADO"

            if prestamos_tiene_columna_fecha_liquidado(db):
                prestamo.fecha_liquidado = hoy_negocio()

            logger.info("Prestamo id=%s marcado como LIQUIDADO (todas las cuotas pagadas).", prestamo_id)

            try:
                from app.services.finiquito_refresh import refrescar_finiquito_caso_prestamo_si_aplica

                fin_res = refrescar_finiquito_caso_prestamo_si_aplica(db, prestamo_id)
                logger.info(
                    "Prestamo id=%s finiquito_casos tras liquidar: %s",
                    prestamo_id,
                    fin_res.get("accion"),
                )
            except Exception:
                logger.exception(
                    "Prestamo id=%s: error refrescando finiquito_casos al liquidar",
                    prestamo_id,
                )

    elif est == "LIQUIDADO":
        prestamo.estado = "APROBADO"

        if prestamos_tiene_columna_fecha_liquidado(db):
            prestamo.fecha_liquidado = None

        logger.info("Prestamo id=%s vuelto a APROBADO (quedan cuotas con saldo pendiente).", prestamo_id)

        from app.services.finiquito_caso_cleanup import eliminar_finiquito_casos_por_prestamo

        eliminar_finiquito_casos_por_prestamo(db, prestamo_id)


def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:
    """
    Aplica el monto del pago a cuotas del préstamo. Reglas de negocio.

    Crea registros en cuota_pagos para historial completo (no solo sobrescribe pago_id).

    Retorna (cuotas_completadas, cuotas_parciales). No hace commit.
    """
    prestamo_id = pago.prestamo_id

    if not prestamo_id:
        return 0, 0

    monto_restante = float(pago.monto_pagado) if pago.monto_pagado else 0

    if monto_restante <= 0:
        return 0, 0

    if pago_tiene_aplicaciones_cuotas(db, pago.id):
        logger.info(
            "Omitiendo aplicacion en cascada: pago id=%s ya tiene filas en cuota_pagos "
            "(idempotencia). Use POST reaplicar-cascada-aplicacion en el prestamo si debe reconstruirse.",
            pago.id,
        )
        return 0, 0

    prestamo_row = db.execute(select(Prestamo).where(Prestamo.id == prestamo_id)).scalars().first()

    if prestamo_row and (prestamo_row.estado or "").strip().upper() == "DESISTIMIENTO":
        return 0, 0

    fecha_pago_date = (
        pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") and pago.fecha_pago else date.today()
    )

    hoy = hoy_negocio()

    with db.begin_nested():
        cuotas_stmt = (
            select(Cuota)
            .where(
                Cuota.prestamo_id == prestamo_id,
                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto - 0.01),
            )
            .order_by(Cuota.numero_cuota.asc())
            .with_for_update()
        )

        cuotas_pendientes = db.execute(cuotas_stmt).scalars().all()

        cuotas_completadas = 0
        cuotas_parciales = 0
        orden_aplicacion = 0

        for c in cuotas_pendientes:
            monto_cuota = float(c.monto) if c.monto is not None else 0
            total_pagado_actual = float(c.total_pagado or 0)
            monto_necesario = monto_cuota - total_pagado_actual

            if monto_restante <= 0 or monto_cuota <= 0:
                break

            dup = db.scalar(
                select(func.count())
                .select_from(CuotaPago)
                .where(CuotaPago.cuota_id == c.id, CuotaPago.pago_id == pago.id)
            )
            if dup and int(dup) > 0:
                logger.warning(
                    "Aplicacion en cascada detenida: ya existe cuota_pagos para cuota_id=%s pago_id=%s. "
                    "Use POST /prestamos/{id}/reaplicar-cascada-aplicacion (compat: .../reaplicar-fifo-aplicacion) para reconstruir.",
                    c.id,
                    pago.id,
                )
                break

            a_aplicar = min(monto_restante, monto_necesario)

            if a_aplicar <= 0:
                continue

            nuevo_total = total_pagado_actual + a_aplicar

            c.total_pagado = Decimal(str(round(nuevo_total, 2)))

            c.pago_id = pago.id

            es_pago_completo = nuevo_total >= monto_cuota - 0.01

            cuota_pago = CuotaPago(
                cuota_id=c.id,
                pago_id=pago.id,
                monto_aplicado=Decimal(str(round(a_aplicar, 2))),
                fecha_aplicacion=datetime.now(),
                orden_aplicacion=orden_aplicacion,
                es_pago_completo=es_pago_completo,
            )

            db.add(cuota_pago)

            orden_aplicacion += 1

            fecha_venc = c.fecha_vencimiento

            if fecha_venc is not None and hasattr(fecha_venc, "date"):
                fecha_venc = fecha_venc.date()

            fecha_venc = fecha_venc or hoy

            if nuevo_total >= monto_cuota - 0.01:
                c.fecha_pago = fecha_pago_date

                if isinstance(fecha_venc, date) and fecha_venc > hoy:
                    estado_nuevo = "PAGO_ADELANTADO"
                else:
                    estado_nuevo = "PAGADO"

                if not validar_transicion_estado_cuota(c.estado, estado_nuevo):
                    logger.warning(
                        "Transición de estado inválida en cuota %s: %s -> %s",
                        c.id,
                        c.estado,
                        estado_nuevo,
                    )
                    c.estado = estado_nuevo
                else:
                    c.estado = estado_nuevo

                c.dias_mora = 0
                cuotas_completadas += 1

            else:
                c.fecha_pago = None

                estado_nuevo = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)

                if not validar_transicion_estado_cuota(c.estado, estado_nuevo):
                    logger.warning(
                        "Transición de estado inválida en cuota %s: %s -> %s",
                        c.id,
                        c.estado,
                        estado_nuevo,
                    )

                c.estado = estado_nuevo

                c.dias_mora = dias_retraso_desde_vencimiento(fecha_venc, hoy)

                cuotas_parciales += 1

            monto_restante -= a_aplicar

        _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

        if cuotas_completadas == 0 and cuotas_parciales == 0:
            num_cuotas = db.scalar(
                select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)
            ) or 0

            if num_cuotas > 0:
                logger.warning(
                    "Pago id=%s (prestamo_id=%s): no se aplicó a ninguna cuota; el préstamo tiene %s cuotas. "
                    "Puede deberse a que las cuotas se generaron después del pago; use aplicar-cuotas o generar cuotas (aplica pendientes automático).",
                    pago.id,
                    prestamo_id,
                    num_cuotas,
                )

        db.flush()
        validar_suma_aplicada_vs_monto_pago(db, pago.id, pago.monto_pagado)

    return cuotas_completadas, cuotas_parciales
