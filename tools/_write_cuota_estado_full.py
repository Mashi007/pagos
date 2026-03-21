# -*- coding: utf-8 -*-
path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/utils/cuotaEstadoCaracas.ts"
content = r'''/**
 * Clasificacion de estado de cuota alineada con backend `app.services.cuota_estado`
 * (America/Caracas, umbral mora 92 d, dia de vencimiento al corriente).
 * Usa solo `total_pagado` (abonos aplicados); la conciliacion bancaria no cambia el estado.
 */

const TOL_MONTO = 0.01
const MORA_DESDE_DIAS = 92

export function parseIsoDateOnly(iso: string): Date {
  const part = iso.slice(0, 10)
  const [y, m, d] = part.split('-').map(x => parseInt(x, 10))
  return new Date(y, m - 1, d)
}

export function hoyCaracasDate(): Date {
  const s = new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/Caracas',
  })
  const [y, m, d] = s.split('-').map(x => parseInt(x, 10))
  return new Date(y, m - 1, d)
}

export type CuotaEstadoInput = {
  monto_cuota?: number | null
  total_pagado?: number | null
  fecha_vencimiento?: string | Date | null
}

function ymdFechaVencimiento(
  fecha: string | Date | null | undefined
): string {
  if (fecha == null) return ''
  if (fecha instanceof Date) {
    const y = fecha.getFullYear()
    const m = fecha.getMonth() + 1
    const d = fecha.getDate()
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  }
  const s = String(fecha)
  return s.length >= 10 ? s.slice(0, 10) : s
}

/**
 * Devuelve: PAGADO | PAGO_ADELANTADO | PENDIENTE | PARCIAL | VENCIDO | MORA
 */
export function clasificarEstadoCuotaCaracas(c: CuotaEstadoInput): string {
  const montoCuota = Number(c.monto_cuota) || 0
  const paid = Number(c.total_pagado) || 0
  const fvIso = ymdFechaVencimiento(c.fecha_vencimiento)
  const fv = fvIso ? parseIsoDateOnly(fvIso) : null
  const hoy = hoyCaracasDate()

  if (montoCuota > 0 && paid >= montoCuota - TOL_MONTO) {
    if (fv && fv > hoy) return 'PAGO_ADELANTADO'
    return 'PAGADO'
  }
  if (!fv) return 'PENDIENTE'

  const diasRet = Math.max(
    0,
    Math.round((hoy.getTime() - fv.getTime()) / 86400000)
  )
  if (diasRet === 0) {
    return paid > 0.001 ? 'PARCIAL' : 'PENDIENTE'
  }
  if (diasRet >= MORA_DESDE_DIAS) return 'MORA'
  return 'VENCIDO'
}
'''
open(path, "w", encoding="utf-8", newline="\n").write(content)
print("written", path)
