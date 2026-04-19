"""Serialización de filas Pago y enriquecimiento para respuestas API."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento, split_numero_documento_almacenado
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado
from app.models.cuota_pago import CuotaPago
from app.services.cobros.pago_reportado_documento import claves_documento_pago_desde_campos
from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas
from app.services.pagos.comprobante_link_desde_gmail import (
    enriquecer_items_link_comprobante_desde_gmail,
)


def _pago_to_response(row: Pago, cuotas_atrasadas: Optional[int] = None) -> dict:
    """Convierte fila Pago a dict para el frontend (campos en snake_case; fechas ISO)."""
    fp = row.fecha_pago

    if fp is None:
        fecha_pago_str = ""
    elif isinstance(fp, datetime):
        fecha_pago_str = fp.date().isoformat()
    elif isinstance(fp, date):
        fecha_pago_str = fp.isoformat()
    elif hasattr(fp, "isoformat"):
        fecha_pago_str = fp.isoformat()
    else:
        fecha_pago_str = str(fp) if fp else ""

    _nd_base, _nd_code = split_numero_documento_almacenado(row.numero_documento)

    return {
        "id": row.id,
        "cedula_cliente": row.cedula_cliente or "",
        "prestamo_id": row.prestamo_id,
        "fecha_pago": fecha_pago_str,
        "monto_pagado": float(row.monto_pagado) if row.monto_pagado is not None else 0,
        "numero_documento": _nd_base or (row.numero_documento or ""),
        "codigo_documento": _nd_code or "",
        "institucion_bancaria": row.institucion_bancaria,
        "estado": row.estado or "PENDIENTE",
        "fecha_registro": row.fecha_registro.isoformat() if row.fecha_registro else None,
        "fecha_conciliacion": row.fecha_conciliacion.isoformat() if row.fecha_conciliacion else None,
        "conciliado": bool(row.conciliado),
        "verificado_concordancia": getattr(row, "verificado_concordancia", None) or None,
        "usuario_registro": row.usuario_registro or "",
        "notas": row.notas,
        "documento_nombre": getattr(row, "documento_nombre", None),
        "documento_tipo": getattr(row, "documento_tipo", None),
        "documento_ruta": getattr(row, "documento_ruta", None),
        "link_comprobante": getattr(row, "link_comprobante", None),
        "cuotas_atrasadas": cuotas_atrasadas,
        "moneda_registro": getattr(row, "moneda_registro", None),
        "monto_bs_original": float(row.monto_bs_original)
        if getattr(row, "monto_bs_original", None) is not None
        else None,
        "tasa_cambio_bs_usd": float(row.tasa_cambio_bs_usd)
        if getattr(row, "tasa_cambio_bs_usd", None) is not None
        else None,
        "fecha_tasa_referencia": row.fecha_tasa_referencia.isoformat()
        if getattr(row, "fecha_tasa_referencia", None)
        else None,
    }


def _enriquecer_items_tiene_aplicacion_cuotas(db: Session, items: list) -> None:
    """Añade tiene_aplicacion_cuotas (filas en cuota_pagos) a cada ítem con id de pago."""
    if not items:
        return
    ids: list[int] = []
    for it in items:
        pid = it.get("id")
        if pid is not None:
            try:
                ids.append(int(pid))
            except (TypeError, ValueError):
                pass
    if not ids:
        for it in items:
            it["tiene_aplicacion_cuotas"] = False
        return
    q = select(CuotaPago.pago_id).where(CuotaPago.pago_id.in_(ids)).distinct()
    has_ids = {int(x[0]) for x in db.execute(q).all() if x[0] is not None}
    for it in items:
        pid = it.get("id")
        try:
            it["tiene_aplicacion_cuotas"] = int(pid) in has_ids if pid is not None else False
        except (TypeError, ValueError):
            it["tiene_aplicacion_cuotas"] = False


def _enriquecer_pagos_pago_reportado_id(db: Session, items: list) -> None:
    """
    Si el Nº documento del pago coincide (normalizado) con alguna clave del reporte en Cobros
    (numero_operacion, referencia_interna, formatos legacy COB-+RPC), expone pago_reportado_id
    para enlazar al detalle / comprobante / recibo.

    Optimización: solo lee pagos_reportados cuyo numero_operacion o referencia_interna aparece
    en los documentos de la página (evita escanear toda la tabla en cada GET /pagos).
    """
    if not items:
        return
    cands: set[str] = set()
    for it in items:
        d = (it.get("numero_documento") or "").strip()
        if d:
            cands.add(d)
            nd0 = normalize_documento(d)
            if nd0:
                cands.add(nd0)
    by_nd: dict[str, int] = {}
    _MAX_CANDS = 500
    if not cands:
        for it in items:
            it["pago_reportado_id"] = None
        return
    cands_list = list(cands)
    if len(cands_list) > _MAX_CANDS:
        cands_list = cands_list[:_MAX_CANDS]
    rows = db.execute(
        select(
            PagoReportado.id,
            PagoReportado.referencia_interna,
            PagoReportado.numero_operacion,
        )
        .where(
            or_(
                PagoReportado.numero_operacion.in_(cands_list),
                PagoReportado.referencia_interna.in_(cands_list),
            )
        )
        .order_by(PagoReportado.id.asc())
    ).all()
    for rid, ref_int, num_op in rows:
        for k in claves_documento_pago_desde_campos(ref_int, num_op):
            nd = normalize_documento(k)
            if nd and nd not in by_nd:
                by_nd[nd] = int(rid)
    for it in items:
        nd = normalize_documento(it.get("numero_documento"))
        it["pago_reportado_id"] = by_nd.get(nd) if nd else None


def _pago_response_enriquecido(
    db: Session,
    row: Pago,
    cuotas_atrasadas: Optional[int] = None,
) -> dict:
    """Dict listo para API: base + enlace Cobros + link Gmail/Drive si aplica."""
    out = _pago_to_response(row, cuotas_atrasadas)
    out["tiene_aplicacion_cuotas"] = pago_tiene_aplicaciones_cuotas(db, row.id)
    _enriquecer_pagos_pago_reportado_id(db, [out])
    enriquecer_items_link_comprobante_desde_gmail(db, [out])
    return out
