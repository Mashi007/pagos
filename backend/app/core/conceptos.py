"""
Conceptos de negocio unificados (Backend).

PAGO VENCIDO Y MOROSO:
- Pago vencido = cuotas vencidas y no pagadas (fecha_vencimiento < hoy).
- Vencido: si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb.
  Desde el 24 = vencido (1-89 días de atraso).
- Moroso: se declara desde el dia siguiente de cumplir 4 meses calendario de atraso.

Condición técnica: fecha_vencimiento < fecha_referencia AND fecha_pago IS NULL
"""

# Meses calendario para declarar MOROSO (desde el dia siguiente al mes 4)
MESES_MOROSO_DESDE = 4
