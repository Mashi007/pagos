"""
Estado de cuota para mostrar en reportes y tabla de amortización.
Centraliza la lógica PENDIENTE | VENCIDO | MORA | PAGADO para uso en
estado_cuenta_publico, prestamos (get_cuotas_prestamo) y consistencia con pagos.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ_NEGOCIO = "America/Caracas"


def _hoy_local() -> date:
    """Fecha actual en zona del negocio (America/Caracas)."""
    return datetime.now(ZoneInfo(TZ_NEGOCIO)).date()


def _calcular_dias_mora(fecha_vencimiento: date | None, fecha_referencia: date | None = None) -> int:
    """Días en mora desde fecha_vencimiento. Si fecha_referencia es None, usa hoy."""
    ref = fecha_referencia or _hoy_local()
    if not fecha_vencimiento:
        return 0
    dias = (ref - fecha_vencimiento).days
    return max(0, dias)


def _clasificar_nivel_mora(dias_mora: int, total_pagado: float, monto_cuota: float) -> str:
    """PAGADO | PENDIENTE | VENCIDO | MORA según días y cobertura."""
    if total_pagado >= monto_cuota - 0.01:
        return "PAGADO"
    if dias_mora == 0:
        return "PENDIENTE"
    if dias_mora > 90:
        return "MORA"
    return "VENCIDO"


def estado_cuota_para_mostrar(
    total_pagado: float,
    monto_cuota: float,
    fecha_vencimiento: date | None,
    fecha_referencia: date | None = None,
) -> str:
    """
    Devuelve el estado a mostrar para una cuota (reportes, tabla amortización).
    No modifica BD. Usar cuando total_pagado < monto_cuota o fecha_pago is None.
    """
    if total_pagado >= (monto_cuota - 0.01):
        return "PAGADO"
    dias_mora = _calcular_dias_mora(fecha_vencimiento, fecha_referencia)
    return _clasificar_nivel_mora(dias_mora, total_pagado, monto_cuota)
