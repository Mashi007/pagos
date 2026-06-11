"""Marcas y reglas de autoconciliación persistente (ABONOS, Conciliar cartera, etc.)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.models.pago import Pago
from app.services.cuota_estado import TZ_NEGOCIO

_PREFIJOS_REF_AUTOCONCILIADO = (
    "ABONOS-NOTIF-",
    "ABONOS-DRIVE-",
    "CONC-IMG-",
)

_MARCADOR_NOTAS_CONCILIAR_CARTERA = "Conciliar cartera:"


def _ref_o_doc(pago: Pago) -> str:
    for attr in ("numero_documento", "referencia_pago"):
        raw = getattr(pago, attr, None)
        if raw:
            return str(raw).strip().upper()
    return ""


def pago_preserva_autoconciliacion_sin_cuotas(pago: Pago) -> bool:
    """
    Pagos que deben permanecer conciliados aunque la cascada no genere cuota_pagos.

    Casos típicos: asiento ABONOS (Notificaciones / hoja CONCILIACIÓN) y comprobantes
  de «Conciliar cartera» cuando el cupo en cuotas ya está cubierto por otro asiento.
    """
    ref = _ref_o_doc(pago)
    if ref and any(ref.startswith(p) for p in _PREFIJOS_REF_AUTOCONCILIADO):
        return True

    notas = str(getattr(pago, "notas", "") or "")
    if _MARCADOR_NOTAS_CONCILIAR_CARTERA in notas:
        return True

    # Alta manual / carga ya validada: conciliado + verificado SI con fecha de conciliación.
    if (
        bool(getattr(pago, "conciliado", False))
        and str(getattr(pago, "verificado_concordancia", "") or "").strip().upper() == "SI"
        and getattr(pago, "fecha_conciliacion", None) is not None
    ):
        return True

    return False


def marcar_pago_autoconciliado(pago: Pago, ahora: Optional[datetime] = None) -> None:
    """Fija banderas de cartera conciliada (cumple chk_pagos_conciliado_pendiente_inconsistente)."""
    ts = ahora or datetime.now(ZoneInfo(TZ_NEGOCIO))
    pago.conciliado = True
    pago.verificado_concordancia = "SI"
    if getattr(pago, "fecha_conciliacion", None) is None:
        pago.fecha_conciliacion = ts
    est_u = str(getattr(pago, "estado", "") or "").strip().upper()
    if est_u not in (
        "PAGADO",
        "PAGO_ADELANTADO",
        "DUPLICADO",
        "ANULADO_IMPORT",
        "CANCELADO",
        "RECHAZADO",
        "REVERSADO",
    ) and "ANUL" not in est_u and "REVERS" not in est_u:
        pago.estado = "PAGADO"
