"""
Motor único de elegibilidad para listados de mora por calendario (1 y 10 días de atraso).

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
    contar_cuotas_atraso_por_prestamos,
    enriquecer_items_notificacion_revision_manual,
    get_cuotas_pendientes_por_vencimientos,
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

    ``formato``:
      - ``item_tab``: mismas filas que ``get_notificaciones_tabs_data`` (envío / tabs).
      - ``item``: mismas filas que GET ``/clientes-retrasados`` (claves dias_*_atraso).
    """
    fechas_retraso = (
        fecha_referencia - timedelta(days=1),
        fecha_referencia - timedelta(days=10),
    )
    rows = get_cuotas_pendientes_por_vencimientos(db, fechas_retraso)
    pids = [c.prestamo_id for c, _ in rows]
    counts = contar_cuotas_atraso_por_prestamos(
        db, pids, fecha_referencia=fecha_referencia
    )
    totales = sum_saldo_pendiente_total_por_prestamos(db, pids)

    dias_1: List[dict] = []
    dias_10: List[dict] = []

    for cuota, cliente in rows:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - fecha_referencia).days
        if delta >= 0:
            continue
        dias_atraso = -delta
        ca = counts.get(cuota.prestamo_id, 0)
        tp = totales.get(cuota.prestamo_id)
        if dias_atraso == 1:
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
        elif dias_atraso == 10:
            if not prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(ca):
                continue
            if formato == "item_tab":
                dias_10.append(
                    _item_tab(
                        cliente,
                        cuota,
                        dias_atraso=10,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )
            else:
                dias_10.append(
                    _item(
                        cliente,
                        cuota,
                        dias_atraso=10,
                        cuotas_atrasadas=ca,
                        total_pendiente_pagar=tp,
                    )
                )

    if con_enriquecimiento_revision_manual:
        enriquecer_items_notificacion_revision_manual(db, dias_1 + dias_10)
    return dias_1, dias_10
