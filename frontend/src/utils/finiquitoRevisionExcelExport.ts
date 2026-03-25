import { createAndDownloadExcel } from '../types/exceljs'

import { formatCurrency, formatDate } from './index'

function segmentoNombreArchivo(s: string): string {
  return s
    .replace(/[/\\:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 64)
}

/**
 * Exporta las cuotas mostradas en la revisión finiquito (mismos campos que la tabla UI).
 */
export async function descargarRevisionCuotasExcel(
  cuotas: Record<string, unknown>[],
  opts: {
    casoId: number | null
    cedula?: string
    prestamoId?: number | null
  }
): Promise<void> {
  if (!cuotas.length) {
    throw new Error('No hay cuotas para exportar')
  }
  const rows = cuotas.map(c => ({
    Nº: c.numero_cuota ?? '',
    Vencimiento: c.fecha_vencimiento
      ? formatDate(String(c.fecha_vencimiento))
      : '',
    'Fecha pago': c.fecha_pago ? formatDate(String(c.fecha_pago)) : '',
    'Monto cuota': formatCurrency(Number(c.monto_cuota ?? 0)),
    Capital: formatCurrency(Number(c.monto_capital ?? 0)),
    Interés: formatCurrency(Number(c.monto_interes ?? 0)),
    Pagado: formatCurrency(Number(c.total_pagado ?? 0)),
    'Saldo cap. final': formatCurrency(Number(c.saldo_capital_final ?? 0)),
    Estado: String(c.estado ?? ''),
    'Pago ID': c.pago_id != null ? String(c.pago_id) : '',
  }))
  const cid = opts.casoId != null ? String(opts.casoId) : 'sin_caso'
  const pid = opts.prestamoId != null ? String(opts.prestamoId) : 'sin_prestamo'
  const ced = segmentoNombreArchivo(opts.cedula || 'cedula')
  const filename = `Finiquito_cuotas_caso_${cid}_prestamo_${pid}_${ced}.xlsx`
  await createAndDownloadExcel(rows, 'Cuotas', filename)
}

/**
 * Exporta los pagos visibles en la revisión (página actual, tope API).
 */
export async function descargarRevisionPagosExcel(
  pagos: Record<string, unknown>[],
  opts: { casoId: number | null; cedula?: string }
): Promise<void> {
  if (!pagos.length) {
    throw new Error('No hay pagos para exportar')
  }
  const rows = pagos.map(p => ({
    ID: p.id ?? '',
    Cédula: String(p.cedula_cliente ?? ''),
    'Préstamo ID': p.prestamo_id != null ? String(p.prestamo_id) : '',
    Estado: String(p.estado ?? ''),
    Notas: p.notas != null ? String(p.notas) : '',
    Monto: formatCurrency(Number(p.monto_pagado ?? 0)),
    'Fecha pago': p.fecha_pago ? formatDate(String(p.fecha_pago)) : '',
    Documento: String(p.numero_documento ?? ''),
    Conciliado: p.conciliado ? 'Sí' : 'No',
  }))
  const cid = opts.casoId != null ? String(opts.casoId) : 'sin_caso'
  const ced = segmentoNombreArchivo(opts.cedula || 'cedula')
  const filename = `Finiquito_pagos_caso_${cid}_${ced}.xlsx`
  await createAndDownloadExcel(rows, 'Pagos', filename)
}
