"""
Aplica el monto ABONOS de la hoja CONCILIACIÓN al préstamo cuando ABONOS > sum(cuotas.total_pagado).

Pasos (reutiliza mecánica existente):
1. Valida comparación (misma lógica que comparar_abonos_drive_vs_cuotas).
2. eliminar_todos_pagos_prestamo: borra pagos, cuota_pagos y reinicia cuotas (solo préstamo APROBADO).
3. Crea un Pago único con monto = ABONOS (USD vía resolver_monto_registro_pago) y referencia única.
4. _aplicar_pago_a_cuotas_interno: cascada por numero_cuota ASC (mismo código que /pagos).

No hace commit: quien llama debe commit/rollback.
"""
from __future__ import annotations

import logging
from datetime import datetime, time as dt_time
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.comparar_abonos_drive_cuotas_service import (
    UMBRAL_CONFIRMO_ABONOS_USD,
    comparar_abonos_drive_vs_cuotas,
)
from app.services.cuota_estado import TZ_NEGOCIO
from app.services.cuota_pago_integridad import suma_monto_aplicado_pago
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.pago_registro_moneda import resolver_monto_registro_pago
from app.services.pagos_cuotas_reaplicacion import eliminar_todos_pagos_prestamo
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

_TOL = 0.02


def aplicar_abonos_drive_a_cuotas_prestamo(
    db: Session,
    *,
    cedula: str,
    prestamo_id: int,
    usuario_registro: str,
    lote: Optional[str] = None,
    confirmacion_montos_altos: Optional[str] = None,
) -> Dict[str, Any]:
    snap = comparar_abonos_drive_vs_cuotas(
        db,
        cedula=cedula,
        prestamo_id=prestamo_id,
        lote=lote,
        persist_cache=False,
    )
    if snap.get("requiere_seleccion_lote"):
        raise ValueError(
            "Hay varios lotes para esta cédula en la hoja. Elija el lote correcto y vuelva a confirmar."
        )
    abonos_drive = snap.get("abonos_drive")
    total_cuotas = float(snap.get("total_pagado_cuotas") or 0)

    if abonos_drive is None:
        raise ValueError(
            "No hay monto ABONOS en la hoja para esta cédula o faltan columnas. Sincronice CONCILIACIÓN."
        )
    if float(abonos_drive) <= total_cuotas + _TOL:
        raise ValueError(
            "Solo se aplica cuando ABONOS (hoja) es mayor que el total pagado en cuotas."
        )

    if float(abonos_drive) > UMBRAL_CONFIRMO_ABONOS_USD:
        conf = (confirmacion_montos_altos or "").strip().upper()
        if conf != "CONFIRMO":
            raise ValueError(
                "Monto ABONOS elevado: en el paso de confirmación debe escribir exactamente CONFIRMO "
                "antes de aplicar."
            )

    del_res = eliminar_todos_pagos_prestamo(db, prestamo_id)
    if not del_res.get("ok"):
        raise ValueError(del_res.get("error") or "No se pudieron eliminar los pagos del préstamo.")

    prestamo = db.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise ValueError("Préstamo no encontrado tras limpieza.")

    cedula_fk = normalizar_cedula_almacenamiento((prestamo.cedula or cedula or "").strip()) or ""

    fecha_pago = datetime.now(ZoneInfo(TZ_NEGOCIO))
    fecha_date = fecha_pago.date()
    monto_dec = Decimal(str(round(float(abonos_drive), 2)))

    suf = uuid4().hex[:10].upper()
    ref_pago = f"ABONOS-DRIVE-{prestamo_id}-{suf}"[:100]

    monto_usd_g, moneda_fin_g, monto_bs_g, tasa_g, fecha_tasa_g = resolver_monto_registro_pago(
        db,
        cedula_normalizada=(cedula_fk or "").strip().upper(),
        fecha_pago=fecha_date,
        monto_pagado=monto_dec,
        moneda_registro="USD",
        tasa_cambio_manual=None,
    )

    msg_h = conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo_id,
        fecha_pago=fecha_date,
        monto_pagado=monto_usd_g,
        numero_documento=ref_pago,
        referencia_pago=ref_pago,
    )
    if msg_h:
        raise ValueError(msg_h)

    ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))

    lote_aplicado_snap = snap.get("lote_aplicado")
    lote_txt = str(lote_aplicado_snap).strip() if lote_aplicado_snap else ""
    nota_base = "Alta automática desde ABONOS hoja CONCILIACIÓN (notificaciones)."
    if lote_txt:
        nota_base += f" Lote hoja: {lote_txt}."

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=prestamo_id,
        fecha_pago=datetime.combine(fecha_date, dt_time.min),
        monto_pagado=monto_usd_g,
        numero_documento=ref_pago[:100],
        estado="PAGADO",
        referencia_pago=ref_pago,
        conciliado=True,
        fecha_conciliacion=ahora_conciliacion,
        verificado_concordancia="SI",
        usuario_registro=(usuario_registro or "").strip()[:255] or None,
        moneda_registro=moneda_fin_g,
        monto_bs_original=monto_bs_g,
        tasa_cambio_bs_usd=tasa_g,
        fecha_tasa_referencia=fecha_tasa_g,
        notas=nota_base,
    )
    db.add(pago)
    db.flush()

    from app.api.v1.endpoints.pagos import (
        _aplicar_pago_a_cuotas_interno,
        _estado_conciliacion_post_cascada,
        _marcar_prestamo_liquidado_si_corresponde,
    )

    cuotas_completadas = 0
    cuotas_parciales = 0
    if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:
        cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)

    # Defensa: el pago debe quedar articulado en cuota_pagos hasta agotar cupo en cuotas (no solo «<= monto»).
    monto_f = float(monto_usd_g or 0)
    if monto_f > _TOL and pago.id is not None:
        sum_ap = float(suma_monto_aplicado_pago(db, int(pago.id)))
        sin_aplicar = round(monto_f - sum_ap, 2)
        if sin_aplicar > 0.05:
            cap_cuotas = 0.0
            for c in db.execute(
                select(Cuota)
                .where(Cuota.prestamo_id == prestamo_id)
                .order_by(Cuota.numero_cuota.asc())
            ).scalars().all():
                cap_cuotas += max(
                    0.0, float(c.monto or 0) - float(c.total_pagado or 0)
                )
            if cap_cuotas > 0.05:
                raise ValueError(
                    "La cascada no distribuyó todo el monto en las cuotas aunque hay cupo pendiente "
                    f"(pago USD {monto_f:.2f}, aplicado a cuotas {sum_ap:.2f}, cupo restante en cuotas ≈ {cap_cuotas:.2f}). "
                    "Reintente; si persiste, use reaplicación en cascada del préstamo en Pagos / préstamo."
                )

    pago.estado = _estado_conciliacion_post_cascada(pago, cuotas_completadas, cuotas_parciales)
    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

    cp_rows = db.execute(
        select(Cuota.numero_cuota, CuotaPago.id)
        .join(Cuota, Cuota.id == CuotaPago.cuota_id)
        .where(CuotaPago.pago_id == pago.id)
        .order_by(CuotaPago.id.asc())
    ).all()
    if cp_rows:
        partes_corr = []
        for idx, (num_cuota, _cpid) in enumerate(cp_rows, start=1):
            try:
                ncu = int(num_cuota)
            except (TypeError, ValueError):
                ncu = num_cuota
            partes_corr.append(f"EXCEL {idx} → cuota {ncu}")
        suf = "; ".join(partes_corr)
        prev = (pago.notas or "").strip()
        pago.notas = (prev + (" | " if prev else "") + f"Correlativo cascada (RM): {suf}").strip()

    logger.info(
        "[aplicar_abonos_drive] prestamo_id=%s pago_id=%s monto=%s cc=%s cp=%s",
        prestamo_id,
        pago.id,
        float(monto_usd_g or 0),
        cuotas_completadas,
        cuotas_parciales,
    )

    try:
        comparar_abonos_drive_vs_cuotas(
            db,
            cedula=cedula,
            prestamo_id=prestamo_id,
            lote=lote,
            persist_cache=True,
        )
    except Exception as cache_exc:
        logger.warning(
            "[aplicar_abonos_drive] no se pudo actualizar caché comparar tras aplicar: %s",
            cache_exc,
        )

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "pago_id": int(pago.id),
        "abonos_drive_origen": float(abonos_drive),
        "monto_pago_usd": float(monto_usd_g or 0),
        "pagos_eliminados": int(del_res.get("pagos_eliminados") or 0),
        "cuotas_completadas": int(cuotas_completadas),
        "cuotas_parciales": int(cuotas_parciales),
        "referencia_pago": ref_pago,
    }
