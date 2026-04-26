import React from 'react'

function formatoFechaDdMmYyyy(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '-'
  const d = String(iso).trim().slice(0, 10)
  const parts = d.split('-')
  if (parts.length === 3 && parts[0].length === 4) {
    const [y, m, day] = parts
    return `${day}-${m}-${y}`
  }
  return d
}

function esMismaFechaQueHoyLocal(iso: string | null | undefined): boolean {
  if (!iso) return false
  const d = String(iso).trim().slice(0, 10)
  const hoy = new Date()
  const y = hoy.getFullYear()
  const m = String(hoy.getMonth() + 1).padStart(2, '0')
  const day = String(hoy.getDate()).padStart(2, '0')
  return d === `${y}-${m}-${day}`
}

export type DuplicadoPrestamosComparacionProps = {
  prestamoExistenteId?: number | null
  pagoExistenteId?: number | null
  pagoExistenteEstado?: string | null
  pagoExistenteFechaPago?: string | null
  prestamoObjetivoId?: number | null
  fechaPagoReporteIso?: string | null
  prestamoDuplicadoEsObjetivo?: boolean | null
  prestamoObjetivoMultiple?: boolean | null
}

/**
 * Tabla comparativa: pago ya en cartera vs préstamo/fecha de este reporte.
 * Texto guía alineado con ejemplos tipo «#647 / 12-10-2025» vs «#5432 / hoy».
 */
export function DuplicadoPrestamosComparacion({
  prestamoExistenteId,
  pagoExistenteId,
  pagoExistenteEstado,
  pagoExistenteFechaPago,
  prestamoObjetivoId,
  fechaPagoReporteIso,
  prestamoDuplicadoEsObjetivo,
  prestamoObjetivoMultiple,
}: DuplicadoPrestamosComparacionProps) {
  const prestEx =
    typeof prestamoExistenteId === 'number' ? `#${prestamoExistenteId}` : '-'
  const prestObj =
    typeof prestamoObjetivoId === 'number' ? `#${prestamoObjetivoId}` : '-'
  const pagoTxt =
    typeof pagoExistenteId === 'number'
      ? `#${pagoExistenteId}${
          pagoExistenteEstado ? ` (${pagoExistenteEstado})` : ''
        }`
      : '-'

  const fechaReporteFmt = formatoFechaDdMmYyyy(fechaPagoReporteIso || undefined)
  const hoyReporte = esMismaFechaQueHoyLocal(fechaPagoReporteIso)

  return (
    <div className="mt-2 space-y-2">
      <div className="overflow-x-auto rounded-md border border-rose-300/70 bg-white">
        <table className="w-full min-w-[300px] border-collapse text-left text-xs sm:text-sm">
          <caption className="caption-top border-b border-rose-200/80 bg-rose-100/60 px-2 py-1.5 text-left text-xs font-medium text-rose-950">
            Compare préstamo y fecha antes de sufijo o «Visto»
          </caption>
          <thead>
            <tr className="border-b border-rose-200/80 bg-rose-50/90">
              <th className="p-2 font-semibold">Situación</th>
              <th className="p-2 font-semibold">Préstamo</th>
              <th className="p-2 font-semibold">Pago en cartera</th>
              <th className="p-2 font-semibold">Fecha</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-rose-100">
              <td className="max-w-[9rem] p-2 align-top font-medium text-rose-950 sm:max-w-none">
                Ya aplicado en cartera
                <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">
                  Ej.: préstamo <span className="font-mono">#647</span>, fecha{' '}
                  <span className="whitespace-nowrap">12-10-2025</span>
                </span>
              </td>
              <td className="p-2 align-top font-mono">{prestEx}</td>
              <td className="p-2 align-top font-mono text-[11px] sm:text-sm">
                {pagoTxt}
              </td>
              <td className="whitespace-nowrap p-2 align-top">
                {formatoFechaDdMmYyyy(pagoExistenteFechaPago)}
                <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">
                  del pago que ya existe
                </span>
              </td>
            </tr>
            <tr>
              <td className="max-w-[9rem] p-2 align-top font-medium text-rose-950 sm:max-w-none">
                Ahora: iría a aplicar (este reporte)
                <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">
                  Ej.: préstamo <span className="font-mono">#5432</span>, fecha
                  de hoy en el comprobante
                </span>
              </td>
              <td className="p-2 align-top font-mono">{prestObj}</td>
              <td className="p-2 align-top text-muted-foreground">-</td>
              <td className="whitespace-nowrap p-2 align-top">
                {fechaReporteFmt}
                {hoyReporte ? (
                  <span className="ml-1 text-[11px] font-semibold text-emerald-700">
                    (hoy)
                  </span>
                ) : null}
                <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">
                  fecha de pago de este reporte
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      {prestamoObjetivoMultiple ? (
        <p className="text-xs text-amber-800">
          Hay más de un préstamo APROBADO para esta cédula: la columna «Ahora»
          usa el préstamo más reciente; confirme en la ficha de préstamos si no
          es el esperado.
        </p>
      ) : null}
      {typeof prestamoExistenteId === 'number' &&
      typeof prestamoObjetivoId === 'number' ? (
        <p className="text-xs">
          <span className="font-medium">Diagnóstico:</span>{' '}
          {prestamoDuplicadoEsObjetivo ? (
            <strong className="text-emerald-700">
              el pago duplicado está en el mismo préstamo que el actual.
            </strong>
          ) : (
            <strong className="text-amber-800">
              el pago duplicado está en otro préstamo (distinto al actual).
            </strong>
          )}
        </p>
      ) : null}
    </div>
  )
}
