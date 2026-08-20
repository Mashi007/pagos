"""
Conceptos de negocio unificados (Backend).

PAGO VENCIDO Y MOROSO:
- Pago vencido = cuotas vencidas y no pagadas (fecha_vencimiento < hoy).
- Vencido: si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb.
  Desde el 24 = vencido (1-89 días de atraso).
- Moroso: umbral oficial en app.services.cuota_estado (MORA_DESDE_MESES + MORA_BUFFER_DIAS).

Condición técnica: fecha_vencimiento < fecha_referencia AND fecha_pago IS NULL
"""

from app.services.cuota_estado import MORA_BUFFER_DIAS, MORA_DESDE_MESES

# Alias histórico. No duplicar números aquí.
MESES_MOROSO_DESDE = MORA_DESDE_MESES
DIAS_BUFFER_MOROSO = MORA_BUFFER_DIAS
