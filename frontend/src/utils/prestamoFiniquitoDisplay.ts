import { formatDate } from './index'

/** Campos minimos para texto de columna / detalle Finiquito. */
export type PrestamoFiniquitoCampos = {
  estado: string
  estado_gestion_finiquito?: string | null
  finiquito_tramite_fecha_limite?: string | null
}

const FINIQUITO_GESTION_ETIQUETAS: Record<string, string> = {
  REVISION: 'En revisión',
  ACEPTADO: 'Validado',
  REVISION_CONTABLE: 'Revisión contable',
  EN_PROCESO: 'En proceso',
  TERMINADO: 'Terminado',
  /** Legacy backfill (migracion 049); equivalente a REVISION. */
  ANTIGUO: 'En revisión',
}

/**
 * Texto "Liquidado / ..." y subtitulo opcional (fecha estimada).
 * null -> en UI mostrar "-" (solo aplica cuando el prestamo esta LIQUIDADO).
 */
export function lineasFiniquitoColumna(
  p: PrestamoFiniquitoCampos
): { primary: string; secondary?: string } | null {
  if ((p.estado || '').toUpperCase() !== 'LIQUIDADO') return null
  const g = (p.estado_gestion_finiquito || '').toUpperCase().trim()
  const sufijo = FINIQUITO_GESTION_ETIQUETAS[g]
  if (!sufijo) return null
  const primary = `Liquidado / ${sufijo}`
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
  const key = (g || '').toUpperCase().trim()
  const map: Record<string, string> = {
    REVISION: 'border-sky-200 bg-sky-50 text-sky-900',
    ANTIGUO: 'border-sky-200 bg-sky-50 text-sky-900',
    ACEPTADO: 'border-amber-200 bg-amber-50 text-amber-900',
    REVISION_CONTABLE: 'border-indigo-200 bg-indigo-50 text-indigo-900',
    EN_PROCESO: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    TERMINADO: 'border-violet-200 bg-violet-50 text-violet-900',
  }
  return map[key] || 'border-slate-200 bg-slate-50 text-slate-800'
}
