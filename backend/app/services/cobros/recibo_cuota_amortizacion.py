"""
Generación del recibo PDF para una cuota de la tabla de amortización (préstamos).
Misma plantilla que el recibo de cobros (recibo_pdf): diseño, numeración de referencia y fechas.
"""
from datetime import date, datetime
from typing import Optional

from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado


def generar_recibo_cuota_amortizacion(
    referencia_interna: str,
    nombres_completos: str,
    cedula: str,
    institucion_financiera: str,
    monto: str,
    numero_operacion: str,
    fecha_recepcion: Optional[datetime] = None,
    fecha_pago: Optional[date] = None,
    aplicado_a_cuotas: Optional[str] = None,
    saldo_inicial: Optional[str] = None,
    saldo_final: Optional[str] = None,
    numero_cuota: Optional[int] = None,
    fecha_pago_display: Optional[str] = None,
    moneda: Optional[str] = None,
    estado_cuota: Optional[str] = None,
) -> bytes:
    """
    Genera el PDF del recibo para una cuota de la tabla de amortización.
    Misma plantilla que recibo de pago reportado (cobros): logo, fechas, cuerpo, número de referencia, pie.
    """
    cedula_clean = (cedula or "").strip().replace(" ", "")
    partes = cedula_clean.split("-")
    if len(partes) >= 2 and partes[0] in ("V", "E", "J", "G") and partes[1].isdigit():
        tipo_cedula, numero_cedula = partes[0], partes[1]
    elif cedula_clean.isdigit():
        tipo_cedula = "V"
        numero_cedula = cedula_clean
    else:
        tipo_cedula = "V"
        numero_cedula = cedula_clean[:20] if cedula_clean else ""

    return generar_recibo_pago_reportado(
        referencia_interna=referencia_interna,
        nombres=(nombres_completos or "").strip(),
        apellidos="",
        tipo_cedula=tipo_cedula,
        numero_cedula=numero_cedula,
        institucion_financiera=institucion_financiera or "N/A",
        monto=monto,
        numero_operacion=numero_operacion or referencia_interna,
        fecha_recepcion=fecha_recepcion,
        fecha_pago=fecha_pago,
        aplicado_a_cuotas=aplicado_a_cuotas,
        saldo_inicial=saldo_inicial,
        saldo_final=saldo_final,
        numero_cuota=numero_cuota,
        fecha_pago_display=fecha_pago_display,
        moneda=moneda,
        estado_cuota=estado_cuota,
    )
