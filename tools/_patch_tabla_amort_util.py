# -*- coding: utf-8 -*-
path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx"
text = open(path, encoding="utf-8").read()
if "clasificarEstadoCuotaCaracas" in text:
    print("already has import")
    raise SystemExit(0)
needle = "import { formatDate } from '../../utils'"
if needle not in text:
    raise SystemExit("needle missing")
text = text.replace(
    needle,
    needle + "\n\nimport { clasificarEstadoCuotaCaracas } from '../../utils/cuotaEstadoCaracas'",
)
old = """  // Estados de cuota: misma regla que backend (America/Caracas). Conciliacion no cambia el estado mostrado.

  const parseIsoDateOnly = (iso: string): Date => {
    const part = iso.slice(0, 10)
    const [y, m, d] = part.split('-').map(x => parseInt(x, 10))
    return new Date(y, m - 1, d)
  }

  const hoyCaracas = (): Date => {
    const s = new Date().toLocaleDateString('en-CA', {
      timeZone: 'America/Caracas',
    })
    const [y, m, d] = s.split('-').map(x => parseInt(x, 10))
    return new Date(y, m - 1, d)
  }

  const clasificarEstadoRespaldo = (cuota: Cuota): string => {
    const montoCuota = Number(cuota.monto_cuota) || 0
    // Misma regla que backend (cuota_estado): solo abonos aplicados a la cuota.
    // La conciliacion bancaria no cambia el estado mostrado.
    const paid = Number(cuota.total_pagado) || 0
    const fvIso = cuota.fecha_vencimiento || ''
    const fv = fvIso ? parseIsoDateOnly(fvIso) : null
    const hoy = hoyCaracas()
    if (montoCuota > 0 && paid >= montoCuota - 0.01) {
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
    if (diasRet >= 92) return 'MORA'
    return 'VENCIDO'
  }

  /** Siempre recalcular con fecha hoy en Caracas (Intl). Evita badges desalineados si la API devolviera estado obsoleto. */
  const estadoCuotaParaBadge = (cuota: Cuota): string =>
    clasificarEstadoRespaldo(cuota)"""
new = """  // Estado en badge: siempre recalculado (Caracas + total_pagado), alineado con backend/cuota_estado.

  const estadoCuotaParaBadge = (cuota: Cuota): string =>
    clasificarEstadoCuotaCaracas(cuota)"""
if old not in text:
    raise SystemExit("old block missing")
text = text.replace(old, new)
open(path, "w", encoding="utf-8", newline="").write(text)
print("ok")
