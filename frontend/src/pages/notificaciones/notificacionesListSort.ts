import type { ClienteRetrasadoItem } from '../../services/notificacionService'

export function textoTotalPendientePagar(row: ClienteRetrasadoItem): string {
  const v =
    row.total_pendiente_pagar != null
      ? Number(row.total_pendiente_pagar)
      : row.monto != null
        ? Number(row.monto)
        : null
  return v != null && Number.isFinite(v) ? v.toLocaleString('es') : '-'
}

/** Mismo id de préstamo que usa estado de cuenta / revisión (BD). */
export function textoNumeroCreditoNotif(row: ClienteRetrasadoItem): string {
  const pid = row.prestamo_id
  if (pid == null) return '-'
  const n = Number(pid)
  return Number.isFinite(n) ? String(n) : '-'
}

/** Valor numérico para ordenar (misma prioridad que el texto mostrado). */
export function numericTotalPendienteSort(row: ClienteRetrasadoItem): number | null {
  if (row.total_pendiente_pagar != null) {
    const n = Number(row.total_pendiente_pagar)
    return Number.isFinite(n) ? n : null
  }
  if (row.monto != null) {
    const n = Number(row.monto)
    return Number.isFinite(n) ? n : null
  }
  return null
}

/** Timestamp para ordenar fechas de vencimiento; vacío al final en orden ascendente. */
export function fechaVencSortValue(s: string | undefined): number {
  if (s == null || String(s).trim() === '') return Number.POSITIVE_INFINITY
  const t = Date.parse(s)
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t
}

export function cuotasAtrasadasSortValue(row: ClienteRetrasadoItem): number {
  const n = row.cuotas_atrasadas ?? row.total_cuotas_atrasadas
  if (n == null || Number.isNaN(Number(n))) return Number.POSITIVE_INFINITY
  return Number(n)
}

/** Diferencia ABONOS (hoja) − total pagado en cuotas; desde caché en fila (General). */
export function numericDiferenciaAbonoSort(row: ClienteRetrasadoItem): number | null {
  const d = row.comparar_abonos_drive_cuotas?.diferencia
  if (d == null || Number.isNaN(Number(d))) return null
  return Number(d)
}
