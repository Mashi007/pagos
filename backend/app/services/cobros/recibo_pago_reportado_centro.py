"""
Fuente unica: armar el recibo PDF de un pago reportado (Cobros).

Todos los endpoints (autenticado, publico, guardado en recibo_pdf) deben usar
`generar_recibo_pdf_desde_pago_reportado` para que el PDF muestre la misma informacion.

Plantilla visual: `recibo_pdf.generar_recibo_pago_reportado`.
Ver `backend/docs/DOCUMENTOS_CLIENTE_CENTRO_UNICO.md`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.pago_reportado import PagoReportado
from app.services.cobros.recibo_cuotas_lookup import texto_cuotas_aplicadas_pago_reportado
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado
from app.services.tasa_cambio_service import obtener_tasa_hoy, obtener_tasa_por_fecha

logger = logging.getLogger(__name__)


def monto_texto_pago_reportado(pr: PagoReportado) -> str:
    monto = getattr(pr, "monto", "")
    moneda = (getattr(pr, "moneda", "") or "").strip()
    monto_str = str(monto).strip()
    return f"{monto_str} {moneda}".strip()


def tasa_bs_usd_para_recibo_pago_reportado(db: Session, pr: PagoReportado) -> Optional[float]:
    """
    Tasa oficial Bs/USD alineada con listados (dia fecha_pago); si no hay fecha, tasa de hoy.
    """
    moneda = (getattr(pr, "moneda", None) or "BS").strip().upper()
    if moneda != "BS":
        return None
    try:
        fp = getattr(pr, "fecha_pago", None)
        if fp:
            tasa_obj = obtener_tasa_por_fecha(db, fp)
        else:
            tasa_obj = obtener_tasa_hoy(db)
        return float(tasa_obj.tasa_oficial) if tasa_obj else None
    except Exception:
        logger.debug("Sin tasa BS/USD para recibo pago_reportado id=%s", getattr(pr, "id", None), exc_info=True)
        return None


def kwargs_recibo_pago_reportado(db: Session, pr: PagoReportado) -> Dict[str, Any]:
    """Argumentos canonicos para `generar_recibo_pago_reportado` (tests / inspeccion)."""
    cuotas_txt = texto_cuotas_aplicadas_pago_reportado(db, pr)
    saldo_init, saldo_fin, num_cuota = None, None, None
    try:
        from app.services.cobros.recibo_cuotas_lookup import obtener_saldos_cuota_aplicada

        saldo_init, saldo_fin, num_cuota = obtener_saldos_cuota_aplicada(db, pr)
    except Exception:
        pass
    fecha_pago_display = pr.fecha_pago.strftime("%d/%m/%Y") if pr.fecha_pago else None
    moneda = (pr.moneda or "BS").strip().upper()
    tasa_cambio = tasa_bs_usd_para_recibo_pago_reportado(db, pr)
    fecha_reporte_aprobacion_display = None
    u = getattr(pr, "updated_at", None)
    if u and hasattr(u, "strftime"):
        fecha_reporte_aprobacion_display = u.strftime("%d/%m/%Y %H:%M")
    return {
        "referencia_interna": pr.referencia_interna,
        "nombres": pr.nombres,
        "apellidos": pr.apellidos,
        "tipo_cedula": pr.tipo_cedula,
        "numero_cedula": pr.numero_cedula,
        "institucion_financiera": pr.institucion_financiera,
        "monto": monto_texto_pago_reportado(pr),
        "numero_operacion": pr.numero_operacion,
        "fecha_pago": pr.fecha_pago,
        "fecha_reporte_aprobacion_display": fecha_reporte_aprobacion_display,
        "aplicado_a_cuotas": cuotas_txt,
        "saldo_inicial": saldo_init,
        "saldo_final": saldo_fin,
        "numero_cuota": num_cuota,
        "fecha_pago_display": fecha_pago_display,
        "moneda": moneda,
        "tasa_cambio": tasa_cambio,
    }


def generar_recibo_pdf_desde_pago_reportado(db: Session, pr: PagoReportado) -> bytes:
    kw = kwargs_recibo_pago_reportado(db, pr)
    return generar_recibo_pago_reportado(**kw)
