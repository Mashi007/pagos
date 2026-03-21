# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx"
t = p.read_text(encoding="utf-8")

old = """  const determinarEstadoReal = (cuota: Cuota): string => {
    const totalPagado = cuota.total_pagado ? 0
    const montoConciliado = cuota.pago_monto_conciliado ? 0
    const montoPagado = Math.max(Number(totalPagado) || 0, Number(montoConciliado) || 0)
    const montoCuota = cuota.monto_cuota || 0
    const pagoConciliado = cuota.pago_conciliado === true

    // [MORA] Nuevas reglas de estado
    // Si monto pagado >= monto_cuota y el pago está conciliado → CONCILIADO
    if (montoPagado >= montoCuota - 0.01 && pagoConciliado) {
      return 'CONCILIADO'
    }
    // Si monto pagado >= monto_cuota → PAGADO
    if (montoPagado >= montoCuota - 0.01) {
      return 'PAGADO'
    }
    
    // Calcular días vencidos
    const hoy = new Date()
    const fechaVencimiento = cuota.fecha_vencimiento ? new Date(cuota.fecha_vencimiento) : null
    let diasMora = 0
    if (fechaVencimiento && fechaVencimiento < hoy) {
      diasMora = Math.floor((hoy.getTime() - fechaVencimiento.getTime()) / (1000 * 60 * 60 * 24))
    }
    
    // Si tiene pago parcial
    if (montoPagado > 0) {
      if (diasMora > 90) {
        return 'MORA'
      } else if (diasMora > 0) {
        return 'VENCIDO'
      }
      return 'PAGO_ADELANTADO'
    }
    
    // Sin pago
    if (diasMora > 90) {
      return 'MORA'
    } else if (diasMora > 0) {
      return 'VENCIDO'
    }
    
    return cuota.estado || 'PENDIENTE'
  }"""

new = """  const determinarEstadoReal = (cuota: Cuota): string => {
    const backend = (cuota.estado || '').trim().toUpperCase()
    const pagoConciliado = cuota.pago_conciliado === true
    // Prioridad: estado calculado en API (misma fuente que PDF / informes)
    if (backend === 'PAGADO' && pagoConciliado) {
      return 'CONCILIADO'
    }
    if (backend === 'PAGADO') {
      return 'PAGADO'
    }
    if (
      ['PENDIENTE', 'VENCIDO', 'MORA', 'PAGO_ADELANTADO', 'PARCIAL', 'CONCILIADO', 'PAGADA'].includes(
        backend,
      )
    ) {
      return backend
    }
    // Respaldo si el API no envía estado útil (versiones antiguas)
    const totalPagado = cuota.total_pagado ? 0
    const montoConciliado = cuota.pago_monto_conciliado ? 0
    const montoPagado = Math.max(Number(totalPagado) || 0, Number(montoConciliado) || 0)
    const montoCuota = cuota.monto_cuota || 0
    if (montoPagado >= montoCuota - 0.01 && pagoConciliado) {
      return 'CONCILIADO'
    }
    if (montoPagado >= montoCuota - 0.01) {
      return 'PAGADO'
    }
    const hoy = new Date()
    const fechaVencimiento = cuota.fecha_vencimiento ? new Date(cuota.fecha_vencimiento) : null
    let diasMora = 0
    if (fechaVencimiento && fechaVencimiento < hoy) {
      diasMora = Math.floor((hoy.getTime() - fechaVencimiento.getTime()) / (1000 * 60 * 60 * 24))
    }
    if (montoPagado > 0) {
      if (diasMora > 90) return 'MORA'
      if (diasMora > 0) return 'VENCIDO'
      return 'PAGO_ADELANTADO'
    }
    if (diasMora > 90) return 'MORA'
    if (diasMora > 0) return 'VENCIDO'
    return cuota.estado || 'PENDIENTE'
  }"""

if old not in t:
    raise SystemExit("old block not found in TablaAmortizacionPrestamo.tsx")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("patched TablaAmortizacionPrestamo.tsx")
