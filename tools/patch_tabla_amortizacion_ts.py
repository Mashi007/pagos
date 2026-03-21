from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "frontend" / "src" / "components" / "prestamos" / "TablaAmortizacionPrestamo.tsx"
text = P.read_text(encoding="utf-8")
start = text.index("  // Funci")
end = text.index("  // Total pendiente por pagar", start)
new_block = r"""  // Estados de cuota: misma regla que backend (America/Caracas). Conciliacion no cambia el estado mostrado.

  const parseIsoDateOnly = (iso: string): Date => {
    const part = iso.slice(0, 10)
    const [y, m, d] = part.split('-').map((x) => parseInt(x, 10))
    return new Date(y, m - 1, d)
  }

  const hoyCaracas = (): Date => {
    const s = new Date().toLocaleDateString('en-CA', {
      timeZone: 'America/Caracas',
    })
    const [y, m, d] = s.split('-').map((x) => parseInt(x, 10))
    return new Date(y, m - 1, d)
  }

  const clasificarEstadoRespaldo = (cuota: Cuota): string => {
    const montoCuota = Number(cuota.monto_cuota) || 0
    const paid = Math.max(
      Number(cuota.total_pagado) || 0,
      Number(cuota.pago_monto_conciliado) || 0
    )
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

  const determinarEstadoReal = (cuota: Cuota): string => {
    const backend = (cuota.estado || '').trim().toUpperCase()
    const confianza = [
      'PENDIENTE',
      'PARCIAL',
      'VENCIDO',
      'MORA',
      'PAGADO',
      'PAGO_ADELANTADO',
      'PAGADA',
    ]
    if (confianza.includes(backend)) {
      if (backend === 'PAGADA') return 'PAGADO'
      return backend
    }
    return clasificarEstadoRespaldo(cuota)
  }

  const getEstadoBadge = (estado: string) => {
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',

      PAGADO: 'bg-green-100 text-green-800',

      PAGADA: 'bg-green-100 text-green-800',

      PAGO_ADELANTADO: 'bg-blue-100 text-blue-800',

      VENCIDO: 'bg-orange-100 text-orange-800',

      MORA: 'bg-red-100 text-red-800',

      PARCIAL: 'bg-amber-100 text-amber-900',
    }

    return badges[estadoNormalizado as keyof typeof badges] || badges.PENDIENTE
  }

  const getEstadoLabel = (estado: string) => {
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',

      PAGADO: 'Pagado',

      PAGADA: 'Pagada',

      PAGO_ADELANTADO: 'Pago adelantado',

      VENCIDO: 'Vencido (1-91 d)',

      MORA: 'Mora (92+ d)',

      PARCIAL: 'Pendiente parcial',
    }

    return labels[estadoNormalizado] || estado
  }


"""
text = text[:start] + new_block + text[end:]
text = text.replace(
    "                  ['PAGADO', 'PAGADA', 'CONCILIADO'].includes(estadoReal)",
    "                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(estadoReal)",
    1,
)
text = text.replace(
    "                  ['PAGADO', 'PAGADA', 'CONCILIADO'].includes(estadoReal) ||\n"
    "                  ['PAGADO', 'PAGADA', 'CONCILIADO'].includes(estadoBackend) ||",
    "                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(estadoReal) ||\n"
    "                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(estadoBackend) ||",
    1,
)
P.write_text(text, encoding="utf-8")
print("tsx ok")
