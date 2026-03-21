# -*- coding: utf-8 -*-
path = r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/reportes/TablaAmortizacionCompleta.tsx"
text = open(path, encoding="utf-8").read()

old_import = "import { formatCurrency, formatDate } from '../../utils'"
if "clasificarEstadoCuotaCaracas" not in text:
    if old_import not in text:
        raise SystemExit("import anchor missing")
    text = text.replace(
        old_import,
        old_import
        + "\n\nimport { clasificarEstadoCuotaCaracas } from '../../utils/cuotaEstadoCaracas'",
    )

old_fn = """  // Función para determinar el estado correcto basado en los datos (igual que en Préstamos)

  const determinarEstadoReal = (cuota: Cuota): string => {
    const totalPagado = cuota.total_pagado || 0

    const montoCuota = cuota.monto_cuota || 0

    // Si total_pagado >= monto_cuota, debería ser PAGADO

    if (totalPagado >= montoCuota) {
      return 'PAGADO'
    }

    // Si tiene algún pago pero no completo

    if (totalPagado > 0) {
      // Verificar si está vencida

      const hoy = new Date()

      const fechaVencimiento = cuota.fecha_vencimiento
        ? new Date(cuota.fecha_vencimiento)
        : null

      if (fechaVencimiento && fechaVencimiento < hoy) {
        return 'ATRASADO'
      }

      return 'PARCIAL'
    }

    // Si no hay pago, devolver el estado original o PENDIENTE

    return cuota.estado || 'PENDIENTE'
  }

"""

if old_fn in text:
    text = text.replace(old_fn, "")

text = text.replace(
    """                                    const estadoReal =
                                      determinarEstadoReal(cuota)""",
    """                                    const estadoReal =
                                      clasificarEstadoCuotaCaracas(cuota)""",
)
text = text.replace(
    """                                          const estadoReal =
                                            determinarEstadoReal(c)""",
    """                                          const estadoReal =
                                            clasificarEstadoCuotaCaracas(c)""",
)

old_filter = """                                          return (
                                            estadoReal === 'PAGADO' ||
                                            estadoReal === 'PAGADA'
                                          )"""
new_filter = """                                          return (
                                            estadoReal === 'PAGADO' ||
                                            estadoReal === 'PAGADA' ||
                                            estadoReal === 'PAGO_ADELANTADO'
                                          )"""
if old_filter in text:
    text = text.replace(old_filter, new_filter)

old_badges = """    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',

      PAGADO: 'bg-green-100 text-green-800',

      PAGADA: 'bg-green-100 text-green-800',

      PAGO_ADELANTADO: 'bg-blue-100 text-blue-800',

      ATRASADO: 'bg-red-100 text-red-800',

      VENCIDA: 'bg-red-100 text-red-800',

      PARCIAL: 'bg-blue-100 text-blue-800',
    }"""

new_badges = """    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',

      PAGADO: 'bg-green-100 text-green-800',

      PAGADA: 'bg-green-100 text-green-800',

      PAGO_ADELANTADO: 'bg-blue-100 text-blue-800',

      VENCIDO: 'bg-orange-100 text-orange-800',

      MORA: 'bg-red-100 text-red-800',

      ATRASADO: 'bg-orange-100 text-orange-800',

      VENCIDA: 'bg-orange-100 text-orange-800',

      PARCIAL: 'bg-amber-100 text-amber-900',
    }"""

if old_badges in text:
    text = text.replace(old_badges, new_badges)

old_labels = """    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',

      PAGADO: 'Pagado',

      PAGADA: 'Pagada',

      PAGO_ADELANTADO: 'Pago adelantado',

      ATRASADO: 'Atrasado',

      VENCIDA: 'Vencida',

      PARCIAL: 'Parcial',
    }"""

new_labels = """    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',

      PAGADO: 'Pagado',

      PAGADA: 'Pagada',

      PAGO_ADELANTADO: 'Pago adelantado',

      VENCIDO: 'Vencido (1-91 d)',

      MORA: 'Mora (92+ d)',

      ATRASADO: 'Vencido (1-91 d)',

      VENCIDA: 'Vencido (1-91 d)',

      PARCIAL: 'Pendiente parcial',
    }"""

if old_labels in text:
    text = text.replace(old_labels, new_labels)

open(path, "w", encoding="utf-8", newline="").write(text)
print("ok")
