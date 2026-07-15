"""
Motor único de elegibilidad para listados de mora por calendario (1 y 10+ días de atraso).

Misma regla de negocio para:
- GET /notificaciones/clientes-retrasados (serialización ``_item``)
- ``get_notificaciones_tabs_data`` / envíos por pestaña (serialización ``_item_tab``)

Así se evita divergencia futura entre la vista y el armado de listas en el servidor al enviar.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Literal, Tuple

from sqlalchemy.orm import Session

from app.services.notificacion_service import (
    MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS,
    contar_cuotas_atraso_por_prestamos,
    cuota_aplica_listado_10_dias_por_dias_atraso,
    enriquecer_items_notificacion_revision_manual,
    get_cuotas_pendientes_por_vencimientos,
    get_cuotas_pendientes_vencidas_hasta,
    prestamo_aplica_listado_10_dias_por_cuotas_atrasadas,
    sum_saldo_pendiente_total_por_prestamos,
    _item,
    _item_tab,
)


def build_items_retraso_uno_y_diez_dias(
    db: Session,
    fecha_referencia: date,
    *,
    formato: Literal["item", "item_tab"] = "item_tab",
    con_enriquecimiento_revision_manual: bool = True,
) -> Tuple[List[dict], List[dict]]:
    """
    Devuelve (lista_1_dia_atraso, lista_10_dias_atraso) según fecha de referencia (Caracas).

    - 1 día: cuota con vencimiento = ayer (exactamente 1 día de atraso).
    - 10+ días: exactamente 1 cuota en mora en el préstamo y atraso >= 10 días
      (permanece hasta que esa cuota se pague).

    ``formato``:
      - ``item_tab``: mismas filas que ``get_notificaciones_tabs_data`` (envío / tabs).
      - ``item``: mismas filas que GET ``/clientes-retrasados`` (claves dias_*_atraso).
    """
    fv_ayer = fecha_referencia - timedelta(days=1)
    fv_max_10 = fecha_referencia - timedelta(days=MIN_DIAS_ATRASO_PARA_LISTADO_10_DIAS)

    rows_1 = get_cuotas_pendientes_por_vencimientos(db, (fv_ayer,))
    rows_10 = get_cuotas_pendientes_vencidas_hasta(db, fv_max_10)

    pids = [c.prestamo_id for c, _ in rows_1] + [c.prestamo_id for c, _ in rows_10]
    counts = contar_cuotas_atraso_por_prestamos(
        db, pids, fecha_referencia=fecha_referencia
    )
    totales = sum_saldo_pendiente_total_por_prestamos(db, pids)

    dias_1: List[dict] = []
    dias_10: List[dict] = []

    for cuota, cliente in rows_1:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - fecha_referencia).days
        if delta >= 0:
            continue
        dias_atraso = -delta
        if dias_atraso != 1:
            continue
        ca = counts.get(cuota.prestamo_id, 0)
        tp = totales.get(cuota.prestamo_id)
        if formato == "item_tab":
            dias_1.append(
                _item_tab(
                    cliente,
                    cuota,
                    dias_atraso=1,
                    cuotas_atrasadas=ca,
                    total_pendiente_pagar=tp,
                )
            )
        else:
            dias_1.append(
                _item(
                    cliente,
                    cuota,
                    dias_atraso=1,
                    cuotas_atrasadas=ca,
                    total_pendiente_pagar=tp,
                )
            )

    for cuota, cliente in rows_10:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - fecha_referencia).days
        if delta >= 0:
            continue
        dias_atraso = -delta
        if not cuota_aplica_listado_10_dias_por_dias_atraso(dias_atraso):
            continue
        ca = counts.get(cuota.prestamo_id, 0)
        if not prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(ca):
            continue
        tp = totales.get(cuota.prestamo_id)
        if formato == "item_tab":
            dias_10.append(
                _item_tab(
                    cliente,
                    cuota,
                    dias_atraso=dias_atraso,
                    cuotas_atrasadas=ca,
                    total_pendiente_pagar=tp,
                )
            )
        else:
            dias_10.append(
                _item(
                    cliente,
                    cuota,
                    dias_atraso=dias_atraso,
                    cuotas_atrasadas=ca,
                    total_pendiente_pagar=tp,
                )
            )

    if con_enriquecimiento_revision_manual:
        enriquecer_items_notificacion_revision_manual(db, dias_1 + dias_10)
    return dias_1, dias_10
