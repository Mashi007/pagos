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

export type PrestamoObjetivoMotivoSinAprobado =
  | 'liquidado'
  | 'sin_aprobado'
  | 'cedula_no_registrada'

/** Campos mínimos para decidir si el duplicado es entre préstamos distintos. */
export type PrestamoDuplicadoCampos = {
  duplicado_en_pagos?: boolean | null
  pago_existente_id?: number | null
  numero_documento_pago_existente?: string | null
  prestamo_existente_id?: number | null
  prestamo_objetivo_id?: number | null
  prestamo_duplicado_es_objetivo?: boolean | null
}

/** El comprobante ya existe en tabla `pagos`. */
export function esDuplicadoEnCartera(row: PrestamoDuplicadoCampos): boolean {
  if (row.duplicado_en_pagos === true) return true
  const pid = row.pago_existente_id
  if (pid != null && Number(pid) > 0) return true
  return Boolean(String(row.numero_documento_pago_existente ?? '').trim())
}

/** Serial en cartera y destino del reporte apuntan al mismo préstamo. */
export function esDuplicadoMismoPrestamo(row: PrestamoDuplicadoCampos): boolean {
  if (!esDuplicadoEnCartera(row)) return false
  if (row.prestamo_duplicado_es_objetivo === true) return true
  const pe = row.prestamo_existente_id
  const po = row.prestamo_objetivo_id
  if (pe != null && po != null) return Number(pe) === Number(po)
  return false
}

/**
 * Duplicado con conflicto real: el serial está en un préstamo y el reporte iría a otro.
 * Ahí sí corresponde la tabla comparativa (Visto Mercantil / bloqueo otros bancos).
 */
export function esDuplicadoEntrePrestamosDistintos(
  row: PrestamoDuplicadoCampos
): boolean {
  if (!esDuplicadoEnCartera(row)) return false
  if (esDuplicadoMismoPrestamo(row)) return false
  if (row.prestamo_duplicado_es_objetivo === false) return true
  const pe = row.prestamo_existente_id
  const po = row.prestamo_objetivo_id
  if (pe != null && po != null) return Number(pe) !== Number(po)
  return false
}

export function debeMostrarComparacionPrestamosEnListado(
  row: PrestamoDuplicadoCampos & {
    institucion_financiera?: string | null
    observacion?: string | null
  },
  esMercantil: (institucion?: string | null) => boolean
): boolean {
  if (esDuplicadoEntrePrestamosDistintos(row)) return true
  if (
    esMercantil(row.institucion_financiera) &&
    /DUPLICADO/i.test(String(row.observacion ?? '')) &&
    !esDuplicadoMismoPrestamo(row)
  ) {
    return true
  }
  return false
}

/** Etiqueta de la columna «Este reporte iría a» cuando no hay APROBADO objetivo. */
export function etiquetaPrestamoObjetivoReportado(opts: {
  prestamoObjetivoId?: number | null
  prestamoObjetivoMotivo?: PrestamoObjetivoMotivoSinAprobado | string | null
  prestamoReferenciaId?: number | null
}): string {
  const prestObj =
    typeof opts.prestamoObjetivoId === 'number' ? opts.prestamoObjetivoId : null
  if (prestObj != null) return `#${prestObj}`

  const motivo = (opts.prestamoObjetivoMotivo || '').trim().toLowerCase()
  const ref =
    typeof opts.prestamoReferenciaId === 'number'
      ? opts.prestamoReferenciaId
      : null

  if (motivo === 'liquidado') {
    return ref != null
      ? `No aplica: LIQUIDADO #${ref}`
      : 'No aplica: préstamo LIQUIDADO'
  }
  if (motivo === 'cedula_no_registrada') {
    return 'Cédula no registrada'
  }
  if (motivo === 'sin_aprobado') {
    return 'Sin APROBADO'
  }
  return 'Sin APROBADO'
}

export type DuplicadoPrestamosResumenProps = {
  prestamoExistenteId?: number | null
  pagoExistenteId?: number | null
  prestamoObjetivoId?: number | null
  prestamoDuplicadoEsObjetivo?: boolean | null
  prestamoObjetivoMultiple?: boolean | null
  prestamoObjetivoMotivo?: PrestamoObjetivoMotivoSinAprobado | string | null
  prestamoReferenciaId?: number | null
  fechaPagoReporteIso?: string | null
  esMercantil?: boolean
}

/**
 * Tabla compacta en listado Cobros: préstamo donde ya está el serial vs préstamo
 * al que iría este reporte (decisión Visto).
 */
export function DuplicadoPrestamosResumen({
  prestamoExistenteId,
  pagoExistenteId,
  prestamoObjetivoId,
  prestamoDuplicadoEsObjetivo,
  prestamoObjetivoMultiple,
  prestamoObjetivoMotivo,
  prestamoReferenciaId,
  fechaPagoReporteIso,
  esMercantil = false,
}: DuplicadoPrestamosResumenProps) {
  if (prestamoDuplicadoEsObjetivo === true) {
    return null
  }
  const prestEx =
    typeof prestamoExistenteId === 'number' ? prestamoExistenteId : null
  const prestObj =
    typeof prestamoObjetivoId === 'number' ? prestamoObjetivoId : null
  const etiquetaObjetivo = etiquetaPrestamoObjetivoReportado({
    prestamoObjetivoId: prestObj,
    prestamoObjetivoMotivo,
    prestamoReferenciaId,
  })
  const esLiquidado =
    (prestamoObjetivoMotivo || '').trim().toLowerCase() === 'liquidado'
  const fechaReporteFmt = formatoFechaDdMmYyyy(fechaPagoReporteIso || undefined)

  if (prestEx == null && prestObj == null && !prestamoObjetivoMotivo) {
    return (
      <p className="mt-1.5 text-[11px] text-orange-900">
        No se pudo resolver préstamos (revise cédula en Editar).
      </p>
    )
  }

  return (
    <div className="mt-2 space-y-1.5">
      <div className="overflow-x-auto rounded border border-orange-400/60 bg-white/90">
        <table className="w-full min-w-[240px] border-collapse text-left text-[11px]">
          <caption className="caption-top border-b border-orange-200 bg-orange-100/80 px-2 py-1 text-left font-semibold text-orange-950">
            Compare préstamos antes de Visto
          </caption>
          <thead>
            <tr className="border-b border-orange-100 bg-orange-50/80">
              <th className="p-1.5 font-semibold">Situación</th>
              <th className="p-1.5 font-semibold">Préstamo</th>
              <th className="hidden p-1.5 font-semibold sm:table-cell">Pago</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-orange-50">
              <td className="p-1.5 align-top font-medium text-orange-950">
                Serial ya en cartera
              </td>
              <td className="p-1.5 align-top font-mono font-semibold">
                {prestEx != null ? `#${prestEx}` : '—'}
              </td>
              <td className="hidden p-1.5 align-top font-mono sm:table-cell">
                {typeof pagoExistenteId === 'number'
                  ? `#${pagoExistenteId}`
                  : '—'}
              </td>
            </tr>
            <tr>
              <td className="p-1.5 align-top font-medium text-orange-950">
                Este reporte iría a
              </td>
              <td
                className={`p-1.5 align-top font-mono font-semibold ${
                  esLiquidado ? 'text-rose-800' : 'text-emerald-800'
                }`}
              >
                {etiquetaObjetivo}
              </td>
              <td className="hidden whitespace-nowrap p-1.5 align-top sm:table-cell">
                {fechaReporteFmt}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {prestamoObjetivoMultiple ? (
        <p className="text-[10px] text-amber-800">
          Varias cédulas con préstamo APROBADO: se usa el más reciente.
        </p>
      ) : null}

      {esLiquidado ? (
        <p className="text-[11px] font-semibold text-rose-800">
          No se aplica a cartera: el crédito del cliente está LIQUIDADO en BD
          {typeof prestamoReferenciaId === 'number'
            ? ` (#${prestamoReferenciaId})`
            : ''}
          .
        </p>
      ) : null}

      {typeof prestamoDuplicadoEsObjetivo === 'boolean' ? (
        <p className="text-[11px] font-semibold">
          {prestamoDuplicadoEsObjetivo ? (
            <span className="text-amber-800">
              Mismo préstamo: el serial ya está aplicado ahí.
            </span>
          ) : (
            <span className="text-emerald-800">
              Otro préstamo: puede valorar Visto (_P####) en Editar.
            </span>
          )}
        </p>
      ) : prestEx != null && prestObj != null ? (
        <p className="text-[11px] font-semibold text-muted-foreground">
          {prestEx === prestObj
            ? 'Mismo préstamo.'
            : 'Préstamos distintos.'}
        </p>
      ) : null}

      {esMercantil ? (
        <p className="text-[10px] leading-snug text-amber-900">
          Excepción Mercantil: abra Editar, confirme la tabla y pulse Visto solo
          si corresponde aplicar a otro préstamo.
        </p>
      ) : (
        <p className="text-[10px] font-semibold leading-snug text-rose-800">
          No se puede reaplicar (solo Mercantil admite Visto).
        </p>
      )}
    </div>
  )
}

export type DuplicadoPrestamosComparacionProps = {
  prestamoExistenteId?: number | null
  pagoExistenteId?: number | null
  pagoExistenteEstado?: string | null
  pagoExistenteFechaPago?: string | null
  prestamoObjetivoId?: number | null
  prestamoObjetivoMotivo?: PrestamoObjetivoMotivoSinAprobado | string | null
  prestamoReferenciaId?: number | null
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
  prestamoObjetivoMotivo,
  prestamoReferenciaId,
  fechaPagoReporteIso,
  prestamoDuplicadoEsObjetivo,
  prestamoObjetivoMultiple,
}: DuplicadoPrestamosComparacionProps) {
  if (prestamoDuplicadoEsObjetivo === true) {
    return null
  }
  const prestEx =
    typeof prestamoExistenteId === 'number' ? `#${prestamoExistenteId}` : '-'
  const prestObj = etiquetaPrestamoObjetivoReportado({
    prestamoObjetivoId,
    prestamoObjetivoMotivo,
    prestamoReferenciaId,
  })
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

export type DuplicadoCarteraAvisoProps = DuplicadoPrestamosComparacionProps & {
  esMercantil: boolean
  numeroDocumentoExistente?: string | null
  /** Botones (abrir préstamo, eliminar, etc.) debajo del aviso. */
  footer?: React.ReactNode
}

/**
 * Aviso unificado en Editar/Detalle: informativo si mismo préstamo;
 * alerta + tabla solo si el serial está en otro préstamo que el destino del reporte.
 */
export function DuplicadoCarteraAviso({
  prestamoExistenteId,
  pagoExistenteId,
  pagoExistenteEstado,
  pagoExistenteFechaPago,
  prestamoObjetivoId,
  prestamoObjetivoMotivo,
  prestamoReferenciaId,
  fechaPagoReporteIso,
  prestamoDuplicadoEsObjetivo,
  prestamoObjetivoMultiple,
  esMercantil,
  numeroDocumentoExistente,
  footer,
}: DuplicadoCarteraAvisoProps) {
  const campos: PrestamoDuplicadoCampos = {
    duplicado_en_pagos: true,
    pago_existente_id: pagoExistenteId,
    numero_documento_pago_existente: numeroDocumentoExistente,
    prestamo_existente_id: prestamoExistenteId,
    prestamo_objetivo_id: prestamoObjetivoId,
    prestamo_duplicado_es_objetivo: prestamoDuplicadoEsObjetivo,
  }

  if (!esDuplicadoEnCartera(campos)) return null

  if (esDuplicadoMismoPrestamo(campos)) {
    const prestId = prestamoExistenteId ?? prestamoObjetivoId
    const doc = String(numeroDocumentoExistente ?? '').trim()
    return (
      <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
        <p>
          Este comprobante ya está registrado en cartera en el mismo préstamo
          {prestId != null ? (
            <>
              {' '}
              <strong>#{prestId}</strong>
            </>
          ) : null}
          {pagoExistenteId != null ? <> (pago #{pagoExistenteId})</> : null}
          {doc ? (
            <>
              {' '}
              · Nº <span className="font-mono">{doc}</span>
            </>
          ) : null}
          .
        </p>
        {footer ? <div className="mt-2 flex flex-wrap gap-2">{footer}</div> : null}
      </div>
    )
  }

  return (
    <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
      <p className="font-medium text-rose-950">
        Hay un pago en cartera que coincide con esta referencia u operación, en
        un <strong>préstamo distinto</strong> al que iría este reporte. Revise
        la tabla antes de usar sufijos o «Visto».
      </p>
      {!esMercantil ? (
        <p className="mt-2 text-xs font-semibold text-rose-800">
          En bancos distintos a Mercantil no se puede reaplicar este comprobante
          (Visto y aprobación bloqueados).
        </p>
      ) : (
        <p className="mt-2 text-xs text-amber-900">
          Excepción Mercantil: compare préstamos y use Visto solo si corresponde
          aplicar a otro préstamo o desambiguar el serial.
        </p>
      )}
      <DuplicadoPrestamosComparacion
        prestamoExistenteId={prestamoExistenteId}
        pagoExistenteId={pagoExistenteId}
        pagoExistenteEstado={pagoExistenteEstado}
        pagoExistenteFechaPago={pagoExistenteFechaPago}
        prestamoObjetivoId={prestamoObjetivoId}
        prestamoObjetivoMotivo={prestamoObjetivoMotivo}
        prestamoReferenciaId={prestamoReferenciaId}
        fechaPagoReporteIso={fechaPagoReporteIso}
        prestamoDuplicadoEsObjetivo={prestamoDuplicadoEsObjetivo}
        prestamoObjetivoMultiple={prestamoObjetivoMultiple}
      />
      {footer ? <div className="mt-2 flex flex-wrap gap-2">{footer}</div> : null}
    </div>
  )
}

/** Texto para tooltip cuando la fila no es seleccionable en aprobación masiva. */
export function tituloDuplicadoNoSeleccionableLote(
  row: PrestamoDuplicadoCampos & { institucion_financiera?: string | null },
  esMercantil: (institucion?: string | null) => boolean
): string | undefined {
  if (!esDuplicadoEnCartera(row)) return undefined
  if (esDuplicadoMismoPrestamo(row)) {
    return 'No seleccionable en lote: el serial ya está aplicado en este préstamo.'
  }
  if (esDuplicadoEntrePrestamosDistintos(row)) {
    return esMercantil(row.institucion_financiera)
      ? 'No seleccionable en lote: serial en otro préstamo (Mercantil: use Aprobar por fila tras Visto si corresponde).'
      : 'No seleccionable en lote: serial en otro préstamo; en este banco no se puede reaplicar.'
  }
  return 'No seleccionable en lote: duplicado en cartera.'
}
