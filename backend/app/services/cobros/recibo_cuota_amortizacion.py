"""
Generacion del recibo PDF para una cuota de la tabla de amortizacion (prestamos).
Reutiliza el mismo formato visual que el recibo de cobros (recibo_pdf.generar_recibo_pago_reportado).
"""
from datetime import datetime
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
) -> bytes:
    """
    Genera el PDF del recibo para una cuota de la tabla de amortizacion.
    Usa el mismo formato visual que el recibo de cobros (reporte de pago).
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
    )
