# -*- coding: utf-8 -*-
"""
Cuotas y saldos para recibos de pagos reportados (Cobros).

Enlaza `pagos_reportados` con `pagos` por las mismas claves que importacion / estado de cuenta
(`claves_documento_pago_para_reportado`) y reutiliza el desglose canonico por pago
(`desglose_aplicacion_cuotas_por_pago` en estado_cuenta_datos).
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado
from app.services.cobros.pago_reportado_documento import claves_documento_pago_para_reportado
from app.services.cobros.recibo_pdf import _etiqueta_moneda, _formato_monto_venezolano
from app.services.estado_cuenta_datos import desglose_aplicacion_cuotas_por_pago

logger = logging.getLogger(__name__)


def _pago_id_vinculado_para_cuotas(db: Session, pr: PagoReportado) -> Optional[int]:
    """
    Pago enlazado al reporte por numero_documento.
    Prefiere estado PAGADO y el id mas reciente.
    """
    claves = claves_documento_pago_para_reportado(pr)
    if not claves:
        return None
    pid = db.execute(
        select(Pago.id)
        .where(
            Pago.numero_documento.in_(claves),
            func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
        )
        .order_by(Pago.id.desc())
        .limit(1)
    ).scalar()
    if pid is not None:
        return int(pid)
    pid2 = db.execute(
        select(Pago.id).where(Pago.numero_documento.in_(claves)).order_by(Pago.id.desc()).limit(1)
    ).scalar()
    return int(pid2) if pid2 is not None else None


def _fmt_capital_monto(pr: PagoReportado, saldo: float) -> str:
    mon = (getattr(pr, "moneda", None) or "BS").strip().upper()
    sym = _etiqueta_moneda(mon, mon)
    return f"{_formato_monto_venezolano(float(saldo))} {sym}"


def texto_cuotas_aplicadas_pago_reportado(db: Session, pr: PagoReportado) -> str:
    """
    Texto corto para recibo / API (cuotas tocadas por el pago enlazado).
    Cadena vacia si no hay pago o sin filas en cuota_pagos: el PDF usa el texto de revision por defecto.
    """
    pid = _pago_id_vinculado_para_cuotas(db, pr)
    if not pid:
        return ""
    desglose = desglose_aplicacion_cuotas_por_pago(db, pid)
    if not desglose:
        return ""
    partes: List[str] = []
    for d in desglose:
        n = int(d.get("numero_cuota") or 0)
        pct = (d.get("porcentaje_cuota") or "").strip()
        if n > 0 and pct:
            partes.append(f"cuota {n} ({pct})")
        elif n > 0:
            partes.append(f"cuota {n}")
    return ", ".join(partes) if partes else ""


def obtener_saldos_cuota_aplicada(
    db: Session, pr: PagoReportado
) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Saldos de capital en la fila de cuota prioritaria (mayor monto aplicado por este pago;
    empate: mayor numero_cuota) para la tabla opcional del recibo.

    Devuelve (saldo_inicial, saldo_final, numero_cuota) como texto con moneda del reporte,
    o (None, None, None) si no aplica.
    """
    pid = _pago_id_vinculado_para_cuotas(db, pr)
    if not pid:
        return None, None, None
    rows = db.execute(
        select(Cuota, CuotaPago.monto_aplicado)
        .join(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(CuotaPago.pago_id == pid)
    ).all()
    if not rows:
        return None, None, None
    best_c: Optional[Cuota] = None
    best_apl = -1.0
    best_num = -1
    for row in rows:
        c = row[0]
        apl = float(row[1] or 0)
        ncu = int(getattr(c, "numero_cuota", 0) or 0)
        if apl > best_apl + 1e-9:
            best_apl = apl
            best_c = c
            best_num = ncu
        elif abs(apl - best_apl) <= 1e-9 and ncu > best_num:
            best_c = c
            best_num = ncu
    if best_c is None:
        return None, None, None
    num = int(getattr(best_c, "numero_cuota", 0) or 0)
    if num <= 0:
        return None, None, None
    try:
        si = float(getattr(best_c, "saldo_capital_inicial", 0) or 0)
        sf = float(getattr(best_c, "saldo_capital_final", 0) or 0)
    except (TypeError, ValueError):
        logger.debug("Saldos no numericos en cuota id=%s", getattr(best_c, "id", None))
        return None, None, None
    return _fmt_capital_monto(pr, si), _fmt_capital_monto(pr, sf), num


def get_cuotas_por_pago(pago_id: int):
    """Stub historico: usar CuotaPago / desglose_aplicacion_cuotas_por_pago en codigo nuevo."""
    return []


def procesar_cuotas_en_lote(cuota_ids: list):
    """Stub historico."""
    return {"procesadas": 0, "errores": 0}
