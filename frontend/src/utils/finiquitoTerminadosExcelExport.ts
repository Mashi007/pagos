import { createAndDownloadExcel } from '../types/exceljs'

import type { FiniquitoTerminadoItem } from '../services/finiquitoService'
import { formatCurrency, formatDate } from './index'

function segmentoNombreArchivo(s: string): string {
  return s
    .replace(/[/\\:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 64)
}

function textoFecha(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return ''
  try {
    return formatDate(String(iso))
  } catch {
    return String(iso)
  }
}

/**
 * Excel de casos terminados (mismas columnas que la tabla de resumen).
 */
export async function descargarTerminadosExcel(
  items: FiniquitoTerminadoItem[],
  opts?: { cedulaFiltro?: string }
): Promise<void> {
  if (!items.length) {
    throw new Error('No hay casos terminados para exportar')
  }
  const rows = items.map(row => ({
    Cedula: row.cedula,
    Nombre: row.nombre,
    'Total financiamiento': formatCurrency(Number(row.total_financiamiento)),
    'Fecha aprobacion': textoFecha(row.fecha_aprobacion),
    'Fecha termino pago': textoFecha(row.fecha_termino_pago),
    'Fecha terminado': textoFecha(row.fecha_terminado),
    'Prestamo ID': row.prestamo_id,
    'Caso ID': row.id,
  }))
  const ced = segmentoNombreArchivo(opts?.cedulaFiltro || 'todos')
  const filename = `Finiquito_terminados_${ced}_${new Date().toISOString().slice(0, 10)}.xlsx`
  await createAndDownloadExcel(rows, 'Terminados', filename)
}
