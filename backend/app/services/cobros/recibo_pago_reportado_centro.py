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
from app.services.cobros.pago_reportado_comprobante_unico import (
    comprobante_bytes_y_content_type_desde_reportado,
)
from app.services.cobros.pago_reportado_documento import (
    texto_numero_documento_recibo_desde_reportado,
)
from app.services.cobros.recibo_cuotas_lookup import (
    obtener_saldos_cuota_aplicada,
    texto_cuotas_aplicadas_pago_reportado,
)
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado
from app.services.tasa_cambio_service import tasa_y_equivalente_usd_excel

logger = logging.getLogger(__name__)


def monto_texto_pago_reportado(pr: PagoReportado) -> str:
    monto = getattr(pr, "monto", "")
    moneda = (getattr(pr, "moneda", "") or "").strip()
    monto_str = str(monto).strip()
    return f"{monto_str} {moneda}".strip()


def tasa_bs_usd_para_recibo_pago_reportado(db: Session, pr: PagoReportado) -> Optional[float]:
    """
    Misma tasa Bs/USD que listado y detalle (`tasa_y_equivalente_usd_excel`): dia fecha_pago;
    si no hay tasa en BD para esa fecha, None (sin inventar tasa de otro dia).
    """
    try:
        tasa_x, _ = tasa_y_equivalente_usd_excel(
            db,
            getattr(pr, "fecha_pago", None),
            float(getattr(pr, "monto", 0) or 0),
            getattr(pr, "moneda", None) or "BS",
        )
        return tasa_x
    except Exception:
        logger.debug("Sin tasa BS/USD para recibo pago_reportado id=%s", getattr(pr, "id", None), exc_info=True)
        return None


def kwargs_recibo_pago_reportado(db: Session, pr: PagoReportado) -> Dict[str, Any]:
    """Argumentos canonicos para `generar_recibo_pago_reportado` (tests / inspeccion)."""
    cuotas_txt = texto_cuotas_aplicadas_pago_reportado(db, pr)
    saldo_init, saldo_fin, num_cuota = None, None, None
    try:
        saldo_init, saldo_fin, num_cuota = obtener_saldos_cuota_aplicada(db, pr)
    except Exception:
        logger.debug(
            "obtener_saldos_cuota_aplicada fallo pago_reportado id=%s",
            getattr(pr, "id", None),
            exc_info=True,
        )
    fecha_pago_display = pr.fecha_pago.strftime("%d/%m/%Y") if pr.fecha_pago else None
    moneda = (pr.moneda or "BS").strip().upper()
    tasa_cambio = tasa_bs_usd_para_recibo_pago_reportado(db, pr)
    fecha_reporte_aprobacion_display = None
    u = getattr(pr, "updated_at", None)
    if u and hasattr(u, "strftime"):
        fecha_reporte_aprobacion_display = u.strftime("%d/%m/%Y %H:%M")
    comp_bytes, comp_ct = comprobante_bytes_y_content_type_desde_reportado(db, pr)
    return {
        "referencia_interna": pr.referencia_interna,
        "nombres": pr.nombres,
        "apellidos": pr.apellidos,
        "tipo_cedula": pr.tipo_cedula,
        "numero_cedula": pr.numero_cedula,
        "institucion_financiera": pr.institucion_financiera,
        "monto": monto_texto_pago_reportado(pr),
        "numero_operacion": texto_numero_documento_recibo_desde_reportado(pr),
        "fecha_pago": pr.fecha_pago,
        "fecha_reporte_aprobacion_display": fecha_reporte_aprobacion_display,
        "aplicado_a_cuotas": cuotas_txt,
        "saldo_inicial": saldo_init,
        "saldo_final": saldo_fin,
        "numero_cuota": num_cuota,
        "fecha_pago_display": fecha_pago_display,
        "moneda": moneda,
        "tasa_cambio": tasa_cambio,
        "comprobante_bytes": comp_bytes,
        "comprobante_tipo": comp_ct,
        "comprobante_nombre": (getattr(pr, "comprobante_nombre", None) or "").strip() or None,
    }


def generar_recibo_pdf_desde_pago_reportado(db: Session, pr: PagoReportado) -> bytes:
    kw = kwargs_recibo_pago_reportado(db, pr)
    return generar_recibo_pago_reportado(**kw)
