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
