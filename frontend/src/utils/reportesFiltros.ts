import type { FiltrosReporte } from '../components/reportes/DialogReporteFiltros'
import type { FiltrosReporteContable } from '../components/reportes/DialogReporteContableFiltros'

import { REPORTE_ANIO_MAX, REPORTE_ANIO_MIN } from '../constants/reportes'

function validarAniosMeses(anios: number[], meses: number[]): string | null {
  if (!anios.length) {
    return 'Selecciona al menos un año.'
  }
  if (!meses.length) {
    return 'Selecciona al menos un mes.'
  }
  for (const y of anios) {
    if (!Number.isFinite(y) || !Number.isInteger(y)) {
      return 'Año inválido en el filtro.'
    }
    if (y < REPORTE_ANIO_MIN || y > REPORTE_ANIO_MAX) {
      return `Los años deben estar entre ${REPORTE_ANIO_MIN} y ${REPORTE_ANIO_MAX}.`
    }
  }
  for (const m of meses) {
    if (!Number.isFinite(m) || !Number.isInteger(m)) {
      return 'Mes inválido en el filtro.'
    }
    if (m < 1 || m > 12) {
      return 'Los meses deben estar entre 1 y 12.'
    }
  }
  return null
}

export function validateFiltrosReporte(filtros: FiltrosReporte): string | null {
  return validarAniosMeses(filtros.años, filtros.meses)
}

function parseYMD(s: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((s || '').trim())
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  const dt = new Date(Date.UTC(y, mo - 1, d))
  if (
    dt.getUTCFullYear() !== y ||
    dt.getUTCMonth() !== mo - 1 ||
    dt.getUTCDate() !== d
  ) {
    return null
  }
  return dt
}

/** Filtro fecha desde / hasta (reporte Pagos Gmail). */
export function validateFiltrosRangoFechasReporte(
  filtros: FiltrosReporte
): string | null {
  const a = (filtros.fecha_desde || '').trim()
  const b = (filtros.fecha_hasta || '').trim()
  if (!a || !b) {
    return 'Indique fecha desde y fecha hasta.'
  }
  const da = parseYMD(a)
  const db = parseYMD(b)
  if (!da) return 'Fecha desde inválida; use el formato AAAA-MM-DD.'
  if (!db) return 'Fecha hasta inválida; use el formato AAAA-MM-DD.'
  if (da > db) return 'La fecha desde no puede ser posterior a la fecha hasta.'
  const maxDays = 366
  const diff = (db.getTime() - da.getTime()) / (24 * 60 * 60 * 1000)
  if (diff > maxDays) {
    return `El rango no puede superar ${maxDays} días.`
  }
  return null
}

const LOTE_MIN = 0

const LOTE_MAX = 999_999

/** Filtro por columna LOTE: Clientes (hoja) y Préstamos Drive. */
export function validateLotesClientesHoja(
  lotes: number[] | undefined
): string | null {
  if (!lotes?.length) {
    return 'Indique al menos un número de lote.'
  }
  for (const n of lotes) {
    if (!Number.isFinite(n) || !Number.isInteger(n)) {
      return 'Cada lote debe ser un número entero.'
    }
    if (n < LOTE_MIN || n > LOTE_MAX) {
      return `Los lotes deben estar entre ${LOTE_MIN} y ${LOTE_MAX}.`
    }
  }
  return null
}

export function validateFiltrosReporteContable(
  filtros: FiltrosReporteContable
): string | null {
  const base = validarAniosMeses(filtros.años, filtros.meses)
  if (base) {
    return base
  }
  if (filtros.cedulas !== 'todas') {
    if (!filtros.cedulas?.length) {
      return 'Selecciona cédulas o la opción de todas las cédulas.'
    }
  }
  return null
}

function validateCuotasImpagasRango(
  filtros: FiltrosReporte,
  maxPermitido = 15,
  etiqueta = 'cuotas impagas'
): string | null {
  const minN = filtros.cuotas_impagas_min
  const maxN = filtros.cuotas_impagas_max
  if (minN == null || maxN == null) {
    return `Indique el rango de ${etiqueta} (1 a ${maxPermitido}).`
  }
  if (
    !Number.isInteger(minN) ||
    !Number.isInteger(maxN) ||
    minN < 1 ||
    maxN > maxPermitido ||
    minN > maxN
  ) {
    return `${etiqueta[0].toUpperCase()}${etiqueta.slice(1)} debe ser un rango entero entre 1 y ${maxPermitido}.`
  }
  if (
    filtros.formato &&
    filtros.formato !== 'excel' &&
    filtros.formato !== 'pdf'
  ) {
    return 'Formato invalido; use excel o pdf.'
  }
  return null
}

/** Filtros Cuentas por cobrar: corte hasta + cuotas en mora 1-99 (99 = todas). */
export function validateFiltrosCarteraCorteReporte(
  filtros: FiltrosReporte
): string | null {
  const hasta = (filtros.fecha_hasta || '').trim()
  if (!hasta) {
    return 'Indique la fecha de corte hasta.'
  }
  if (!parseYMD(hasta)) {
    return 'Fecha de corte invalida; use el formato AAAA-MM-DD.'
  }
  return validateCuotasImpagasRango(filtros, 99, 'cuotas en mora')
}

/** Filtros Impagas cedula (dos cortes) + cuotas impagas 1-15. */
export function validateFiltrosCarteraReporte(
  filtros: FiltrosReporte
): string | null {
  const base = validateFiltrosRangoFechasReporte(filtros)
  if (base) return base
  return validateCuotasImpagasRango(filtros)
}

/** Aseguradora: sin fechas ni rango de cuotas (fijos en backend). */
export function validateFiltrosAseguradoraReporte(
  filtros: FiltrosReporte
): string | null {
  if (
    filtros.formato &&
    filtros.formato !== 'excel' &&
    filtros.formato !== 'pdf'
  ) {
    return 'Formato invalido; use excel o pdf.'
  }
  return null
}
