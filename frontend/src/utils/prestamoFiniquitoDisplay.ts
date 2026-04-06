import { formatDate } from './index'

/** Campos mínimos para texto de columna / detalle Finiquito. */
export type PrestamoFiniquitoCampos = {
  estado: string
  estado_gestion_finiquito?: string | null
  finiquito_tramite_fecha_limite?: string | null
}

/**
 * Texto "Liquidado / …" y subtítulo opcional (fecha estimada).
 * null → en UI mostrar "-" (solo aplica cuando el préstamo está LIQUIDADO).
 */
export function lineasFiniquitoColumna(
  p: PrestamoFiniquitoCampos
): { primary: string; secondary?: string } | null {
  if ((p.estado || '').toUpperCase() !== 'LIQUIDADO') return null
  const g = (p.estado_gestion_finiquito || '').toUpperCase().trim()
  const sufijo: Record<string, string> = {
    ANTIGUO: 'Antiguo',
    EN_PROCESO: 'En proceso',
    TERMINADO: 'Terminado',
  }
  if (!sufijo[g]) return null
  const primary = `Liquidado / ${sufijo[g]}`
  const lim = p.finiquito_tramite_fecha_limite
  if (g === 'EN_PROCESO' && lim != null && String(lim).trim() !== '') {
    const fd = formatDate(String(lim))
    if (fd && fd !== 'Fecha inválida') {
      return { primary, secondary: `Fin estimado: ${fd}` }
    }
  }
  return { primary }
}

export function finiquitoGestionBadgeClass(g: string): string {
  const map: Record<string, string> = {
    ANTIGUO: 'border-amber-200 bg-amber-50 text-amber-900',
    EN_PROCESO: 'border-sky-200 bg-sky-50 text-sky-900',
    TERMINADO: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  }
  return map[g] || 'border-slate-200 bg-slate-50 text-slate-800'
}
