/**





 * Tabla editable para preview de carga masiva de pagos.





 * Muestra errores de validación por celda (cédula, fecha, monto, documento).





 * La columna Crédito se rellena automáticamente cuando la cédula tiene un solo préstamo activo.





 */

import { useEffect, useMemo, useRef, useState } from 'react'

import { Save, Loader2, Search } from 'lucide-react'

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

import {
  cedulaLookupParaFila,
  convertirFechaParaBackendPago,
} from '../../utils/pagoExcelValidation'

import { pagoService } from '../../services/pagoService'

import { getTasaPorFecha } from '../../services/tasaCambioService'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

export interface FilaEditableProps {
  rows: PagoExcelRow[]

  prestamosPorCedula?: Record<string, Array<{ id: number; estado: string }>>

  onRowsChange?: (newRows: PagoExcelRow[]) => void

  onUpdateCell: (
    row: PagoExcelRow,
    field: string,
    value: string | number
  ) => void

  saveRowIfValid?: (row: PagoExcelRow) => Promise<boolean>

  /** Si se pasa, el botón Guardar muestra estado de carga y se deshabilita mientras guarda. */

  savingProgress?: Record<number, boolean>

  serviceStatus?: 'online' | 'offline' | 'checking' | 'unknown'

  /** Envía esta fila a Revisar Pagos (para filas que no cumplen validadores). */

  onSendToRevisarPagos?: (row: PagoExcelRow) => void

  isSendingRevisar?: boolean
}

function CeldaEditable({
  value,

  isValid,

  errorMsg,

  placeholder,

  type = 'text',

  onChange,
}: {
  value: string | number

  isValid: boolean | undefined

  errorMsg?: string

  placeholder?: string

  type?: 'text' | 'number'

  onChange: (val: string) => void
}) {
  const hasError = isValid === false

  return (
    <div className="relative">
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full rounded border p-1 text-sm ${
          hasError
            ? 'border-red-500 bg-red-50 text-red-900 focus:ring-red-300'
            : 'border-gray-300 focus:border-blue-400'
        } focus:outline-none focus:ring-1`}
      />

      {hasError && errorMsg && (
        <p className="mt-0.5 text-xs leading-tight text-red-600">{errorMsg}</p>
      )}
    </div>
  )
}

function normMoneda(v: unknown): 'USD' | 'BS' {
  const s = String(v ?? 'USD')
    .trim()
    .toUpperCase()
  return s === 'BS' ? 'BS' : 'USD'
}

/** Entrada de tasa manual (Bs/USD): texto para permitir decimales mientras se escribe. */
function TasaManualInput({
  row,
  onUpdateCell,
}: {
  row: PagoExcelRow
  onUpdateCell: (
    row: PagoExcelRow,
    field: string,
    value: string | number
  ) => void
}) {
  const [text, setText] = useState(() =>
    row.tasa_cambio_manual != null && typeof row.tasa_cambio_manual === 'number'
      ? String(row.tasa_cambio_manual)
      : ''
  )

  useEffect(() => {
    const v = row.tasa_cambio_manual
    if (v != null && typeof v === 'number' && Number.isFinite(v)) {
      setText(String(v))
    } else if (v == null || v === undefined) {
      setText('')
    }
  }, [row._rowIndex, row.tasa_cambio_manual])

  return (
    <div className="space-y-0.5">
      <input
        type="text"
        inputMode="decimal"
        autoComplete="off"
        className="w-full rounded border border-amber-300 p-1 text-xs"
        placeholder="Ej: 526.12"
        value={text}
        onChange={e => {
          let s = e.target.value.trim().replace(',', '.')
          if (s === '') {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
            return
          }
          if (!/^\d*\.?\d*$/.test(s)) return
          setText(s)
          if (s === '.' || s.endsWith('.')) {
            return
          }
          const n = parseFloat(s)
          if (Number.isFinite(n) && n > 0) {
            onUpdateCell(row, 'tasa_cambio_manual', n)
          }
        }}
        onBlur={() => {
          const s = text.trim().replace(',', '.')
          if (s === '' || s === '.') {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
            return
          }
          const n = parseFloat(s)
          if (Number.isFinite(n) && n > 0) {
            onUpdateCell(row, 'tasa_cambio_manual', n)
            setText(String(n))
          } else {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
          }
        }}
      />
      <p className="text-[10px] leading-tight text-amber-900/80">
        No se guarda en la tabla de tasas diarias; solo aplica a este pago.
      </p>
    </div>
  )
}

function prestamoIdVacio(v: unknown): boolean {
  return (
    v == null ||
    v === undefined ||
    v === '' ||
    v === 'none' ||
    v === 0 ||
    (typeof v === 'number' && Number.isNaN(v))
  )
}

/**





 * Crédito: si hay 1 préstamo activo por cédula se carga automáticamente;





 * si hay más de uno el usuario debe elegir en el selector;





 * si no hay (0) se muestra "Sin crédito" (solo aplica cuando el cliente está registrado pero sin créditos activos; si no hay cliente, la cédula ya marca error).





 */

function CreditoCell({
  row,

  prestamosPorCedula,

  onUpdateCell,
}: {
  row: PagoExcelRow

  prestamosPorCedula: Record<string, Array<{ id: number; estado: string }>>

  onUpdateCell: (
    row: PagoExcelRow,
    field: string,
    value: string | number
  ) => void
}) {
  const lookup = cedulaLookupParaFila(
    row.cedula || '',
    row.numero_documento || ''
  )

  const sinGuion = lookup.replace(/-/g, '')

  const prestamos =
    prestamosPorCedula[lookup] ||
    prestamosPorCedula[sinGuion] ||
    prestamosPorCedula[lookup?.toUpperCase()] ||
    prestamosPorCedula[lookup?.toLowerCase()] ||
    []

  // 0 créditos: cliente puede no existir (cedula inválida) o existir sin créditos activos

  if (prestamos.length === 0) {
    return <span className="text-xs italic text-gray-500">Sin crédito</span>
  }

  // 1 crédito: vacío en Excel = sin inventar ID; válido = verde; inválido = ámbar (corrección solo si no está vacío).

  if (prestamos.length === 1) {
    const correctId = prestamos[0].id
    const vacio = prestamoIdVacio(row.prestamo_id)
    const ok = Number(row.prestamo_id) === correctId

    if (vacio) {
      return (
        <input
          type="text"
          value=""
          readOnly
          className="w-full rounded border border-dashed border-gray-300 bg-white p-1 text-sm text-gray-500"
          title="Indique el ID de préstamo en el archivo; vacío genera error de validación"
        />
      )
    }

    if (ok) {
      return (
        <input
          type="text"
          value={String(correctId)}
          readOnly
          className="w-full rounded border border-gray-200 bg-green-50 p-1 text-sm font-medium text-green-800"
          title="ID de préstamo coincide con el único crédito activo"
        />
      )
    }

    return (
      <input
        type="text"
        value={String(row.prestamo_id ?? '')}
        readOnly
        className="w-full rounded border border-amber-300 bg-amber-50 p-1 text-sm text-amber-900"
        title="ID no coincide con el crédito; se ajustará al guardar si corresponde"
      />
    )
  }

  // 2+ créditos: el usuario debe elegir

  const valorActual = !prestamoIdVacio(row.prestamo_id)
    ? String(row.prestamo_id)
    : 'none'

  const esValido = prestamos.some(p => p.id === row.prestamo_id)

  return (
    <Select
      value={valorActual}
      onValueChange={v =>
        onUpdateCell(row, 'prestamo_id', v === 'none' ? 0 : Number(v))
      }
    >
      <SelectTrigger
        className={`h-8 w-full text-xs ${!esValido && valorActual === 'none' ? 'border-amber-500 bg-amber-50' : ''}`}
      >
        <SelectValue placeholder="Elegir crédito" />
      </SelectTrigger>

      <SelectContent>
        <SelectItem value="none">- Elegir crédito -</SelectItem>

        {prestamos.map(p => (
          <SelectItem key={p.id} value={String(p.id)}>
            Crédito #{p.id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function TablaEditablePagos({
  rows,

  prestamosPorCedula = {},

  onUpdateCell,

  saveRowIfValid,

  savingProgress = {},

  serviceStatus = 'online',

  onSendToRevisarPagos,

  isSendingRevisar = false,
}: FilaEditableProps) {
  const cedulaBsCacheRef = useRef<Map<string, boolean>>(new Map())

  const [localSaving, setLocalSaving] = useState<Set<number>>(new Set())

  const [autorizadoBsPorCedula, setAutorizadoBsPorCedula] = useState<
    Record<string, boolean | null>
  >({})

  const [tasaBdPorFila, setTasaBdPorFila] = useState<
    Record<number, number | null | undefined>
  >({})

  const cedulasFirma = useMemo(() => {
    const lookups = new Set<string>()
    for (const row of rows) {
      const lk = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )
        .trim()
        .replace(/-/g, '')
        .toUpperCase()
      if (lk.length >= 5) lookups.add(lk)
    }
    return [...lookups].sort().join('|')
  }, [rows])

  useEffect(() => {
    if (!cedulasFirma) return
    const lookups = cedulasFirma.split('|').filter(Boolean)
    let cancelled = false
    ;(async () => {
      const pendientes: string[] = []
      for (const lk of lookups) {
        if (cedulaBsCacheRef.current.has(lk)) {
          const cached = cedulaBsCacheRef.current.get(lk)!
          setAutorizadoBsPorCedula(prev =>
            prev[lk] === cached ? prev : { ...prev, [lk]: cached }
          )
        } else {
          pendientes.push(lk)
        }
      }
      if (pendientes.length === 0) return
      try {
        const batch =
          await pagoService.consultarCedulasReportarBsBatch(pendientes)
        if (cancelled) return
        const map = batch.por_cedula || {}
        for (const lk of pendientes) {
          const row = map[lk]
          const ok = row ? row.en_lista : false
          cedulaBsCacheRef.current.set(lk, ok)
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: ok }))
        }
      } catch {
        if (cancelled) return
        for (const lk of pendientes) {
          cedulaBsCacheRef.current.set(lk, false)
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: false }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [cedulasFirma])

  const tasaBsFirma = useMemo(() => {
    const parts: string[] = []
    for (const row of rows) {
      if (normMoneda(row.moneda_registro) !== 'BS') continue
      const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
      parts.push(`${row._rowIndex}:${iso || ''}`)
    }
    return parts.sort().join('|')
  }, [rows])

  useEffect(() => {
    let cancelled = false
    const bsRowIndexes = new Set<number>()
    const byIso = new Map<string, number[]>()
    const sinFechaIdx: number[] = []

    for (const row of rows) {
      if (normMoneda(row.moneda_registro) !== 'BS') continue
      bsRowIndexes.add(row._rowIndex)
      const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
      if (!iso) {
        sinFechaIdx.push(row._rowIndex)
        continue
      }
      const arr = byIso.get(iso) ?? []
      arr.push(row._rowIndex)
      byIso.set(iso, arr)
    }

    setTasaBdPorFila(prev => {
      const next = { ...prev }
      for (const key of Object.keys(next)) {
        const idx = Number(key)
        if (!bsRowIndexes.has(idx)) delete next[idx]
      }
      for (const idx of sinFechaIdx) {
        next[idx] = null
      }
      for (const idxs of byIso.values()) {
        for (const idx of idxs) {
          next[idx] = undefined
        }
      }
      return next
    })
    ;(async () => {
      for (const [iso, idxs] of byIso) {
        if (cancelled) return
        try {
          const t = await getTasaPorFecha(iso)
          if (cancelled) return
          const val = t?.tasa_oficial ?? null
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            for (const idx of idxs) next[idx] = val
            return next
          })
        } catch {
          if (cancelled) return
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            for (const idx of idxs) next[idx] = null
            return next
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tasaBsFirma])

  const isSaving = (rowIndex: number) =>
    !!savingProgress[rowIndex] || localSaving.has(rowIndex)

  // Solo corregir prestamo_id cuando hay valor incorrecto (p. ej. nº de documento en columna crédito); nunca rellenar vacío.

  useEffect(() => {
    if (!rows?.length || Object.keys(prestamosPorCedula).length === 0) return

    rows.forEach(row => {
      if (prestamoIdVacio(row.prestamo_id)) return

      const lookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const sinGuion = lookup.replace(/-/g, '')

      const prestamos =
        prestamosPorCedula[lookup] ||
        prestamosPorCedula[sinGuion] ||
        prestamosPorCedula[lookup.toUpperCase()] ||
        prestamosPorCedula[lookup.toLowerCase()] ||
        []

      if (prestamos.length === 1) {
        const correctId = prestamos[0].id
        if (Number(row.prestamo_id) === correctId) return
        onUpdateCell(row, 'prestamo_id', correctId)
      }
    })
  }, [rows, prestamosPorCedula, onUpdateCell])

  if (!rows || rows.length === 0) {
    return (
      <div className="rounded border border-dashed border-gray-300 p-4 text-gray-500">
        No hay datos para mostrar
      </div>
    )
  }

  const total = rows.length

  const validos = rows.filter(r => !r._hasErrors).length

  const invalidas = total - validos

  return (
    <div className="space-y-4">
      {/* Indicadores: filas cargadas, válidas, inválidas (varían al editar y validar) */}

      <div className="rounded-lg border border-blue-400 bg-blue-50 p-4">
        <h2 className="mb-2 text-lg font-bold text-blue-800">
          Indicadores (se actualizan al editar)
        </h2>

        <div className="flex flex-wrap gap-6 text-sm">
          <span className="font-medium text-gray-700">
            Filas cargadas:{' '}
            <strong className="tabular-nums text-gray-900">{total}</strong>
          </span>

          <span className="font-medium text-green-700">
            Válidas: <strong className="tabular-nums">{validos}</strong>
          </span>

          <span className="font-medium text-red-700">
            Inválidas: <strong className="tabular-nums">{invalidas}</strong>
            <span className="ml-1 text-blue-600">(van a Revisar Pagos)</span>
          </span>
        </div>

        <p className="mt-2 text-xs text-blue-700">
          <strong>Los que no cumplen validadores van a Revisar Pagos.</strong>{' '}
          Puede enviarlos con el botón &quot;Revisar Pagos&quot; por fila o con
          &quot;Revisar Pagos (N)&quot; para enviar todas las inválidas.
        </p>

        <p className="mt-1 text-xs text-blue-700">
          Al guardar una fila (botón Guardar en cada fila), esta desaparece de
          la tabla y el pago se registra aplicando las mismas reglas de negocio:
          aplicación a cuotas (cascada), conciliación y actualización de
          pagos/cuotas.
        </p>

        <p className="mt-1 text-xs text-blue-700">
          <strong>Crédito:</strong> el ID de préstamo debe venir en el archivo (o
          elegir en la lista si hay varios). Un solo crédito activo no rellena
          la celda sola: vacío = error de validación. &quot;Sin crédito&quot;
          cuando el cliente no tiene préstamos activos.
        </p>

        <p className="mt-1 text-xs text-blue-700">
          <strong>Moneda / tasa:</strong> USD por defecto. Bolívares (Bs) solo
          si la cédula está en la lista autorizada. La tasa se toma de la BD por
          fecha de pago; si no existe, ingrese la tasa manual (Bs por 1 USD) en
          la columna correspondiente. Esa tasa no se copia a la tabla de tasas
          diarias (solo queda en el registro del pago); para dejarla en el
          calendario de tasas use Administracion.
        </p>
      </div>

      {/* Tabla */}

      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-100">
            <tr>
              <th className="w-12 border-r p-2 text-center font-semibold">#</th>

              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Banco
              </th>

              <th className="min-w-[140px] border-r p-2 text-left font-semibold">
                Cédula
              </th>

              <th className="min-w-[130px] border-r p-2 text-left font-semibold">
                Fecha pago
              </th>

              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Monto
              </th>

              <th className="min-w-[100px] border-r p-2 text-left font-semibold">
                Moneda
              </th>

              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Tasa (Bs/USD)
              </th>

              <th className="min-w-[160px] border-r p-2 text-left font-semibold">
                Documento
              </th>

              <th className="min-w-[80px] border-r p-2 text-left font-semibold">
                Crédito
              </th>

              <th className="min-w-[100px] p-2 text-center font-semibold">
                Acción
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map(row => (
              <tr
                key={row._rowIndex}
                className={
                  row._hasErrors
                    ? 'border-l-4 border-l-red-400 bg-red-50'
                    : 'bg-white hover:bg-gray-50'
                }
              >
                <td className="border-r p-2 text-center text-gray-500">
                  {row._rowIndex}
                </td>

                {/* Banco (plantilla Excel) */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.institucion_bancaria ?? ''}
                    isValid={row._validation.institucion_bancaria?.isValid}
                    errorMsg={row._validation.institucion_bancaria?.message}
                    placeholder="BINANCE, BNC..."
                    onChange={v => onUpdateCell(row, 'institucion_bancaria', v)}
                  />
                </td>

                {/* Cédula */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.cedula}
                    isValid={row._validation.cedula?.isValid}
                    errorMsg={row._validation.cedula?.message}
                    placeholder="V12345678"
                    onChange={v => onUpdateCell(row, 'cedula', v)}
                  />
                </td>

                {/* Fecha */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.fecha_pago}
                    isValid={row._validation.fecha_pago?.isValid}
                    errorMsg={row._validation.fecha_pago?.message}
                    placeholder="DD/MM/YYYY"
                    onChange={v => onUpdateCell(row, 'fecha_pago', v)}
                  />
                </td>

                {/* Monto */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.monto_pagado || ''}
                    isValid={row._validation.monto_pagado?.isValid}
                    errorMsg={row._validation.monto_pagado?.message}
                    placeholder="0.00"
                    type="number"
                    onChange={v => onUpdateCell(row, 'monto_pagado', v)}
                  />
                </td>

                {/* Moneda */}

                <td className="border-r p-2">
                  {(() => {
                    const lk = cedulaLookupParaFila(
                      row.cedula || '',
                      row.numero_documento || ''
                    )
                      .trim()
                      .replace(/-/g, '')
                      .toUpperCase()
                    const enAuth =
                      lk.length >= 5 ? autorizadoBsPorCedula[lk] : null
                    const puedeBs = enAuth === true
                    const m = normMoneda(row.moneda_registro)
                    return (
                      <Select
                        value={m}
                        onValueChange={v =>
                          onUpdateCell(row, 'moneda_registro', v)
                        }
                        disabled={enAuth === null}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="USD">USD</SelectItem>
                          <SelectItem value="BS" disabled={!puedeBs}>
                            Bs
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    )
                  })()}
                </td>

                {/* Tasa manual si BS y no hay en BD */}

                <td className="border-r p-2">
                  {(() => {
                    const m = normMoneda(row.moneda_registro)
                    if (m !== 'BS') {
                      return <span className="text-xs text-gray-400">-</span>
                    }
                    const tb = tasaBdPorFila[row._rowIndex]
                    if (tb === undefined) {
                      return (
                        <span className="text-xs text-blue-600">
                          <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
                          Tasa...
                        </span>
                      )
                    }
                    if (typeof tb === 'number') {
                      return (
                        <span className="text-xs text-green-800">BD: {tb}</span>
                      )
                    }
                    return (
                      <TasaManualInput row={row} onUpdateCell={onUpdateCell} />
                    )
                  })()}
                </td>

                {/* Documento */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.numero_documento}
                    isValid={row._validation.numero_documento?.isValid}
                    errorMsg={row._validation.numero_documento?.message}
                    placeholder="VE/xxx"
                    onChange={v => onUpdateCell(row, 'numero_documento', v)}
                  />
                </td>

                {/* Crédito: 1 = auto; varios = elegir; 0 = Sin crédito (solo cuando no hay cliente o sin créditos activos) */}

                <td className="border-r p-2">
                  <CreditoCell
                    row={row}
                    prestamosPorCedula={prestamosPorCedula}
                    onUpdateCell={onUpdateCell}
                  />
                </td>

                {/* Acción: Guardar solo si la fila pasa validadores y crédito (1 auto, varios elegido, 0 no guardar) */}

                <td className="p-2">
                  {saveRowIfValid ? (
                    (() => {
                      const lookup = cedulaLookupParaFila(
                        row.cedula || '',
                        row.numero_documento || ''
                      )

                      const sinGuion = lookup.replace(/-/g, '')

                      const prestamos =
                        prestamosPorCedula[lookup] ||
                        prestamosPorCedula[sinGuion] ||
                        prestamosPorCedula[lookup?.toUpperCase()] ||
                        prestamosPorCedula[lookup?.toLowerCase()] ||
                        []

                      const sinCreditoElegido =
                        prestamos.length > 0 &&
                        prestamoIdVacio(row.prestamo_id)

                      const sinCreditosActivos = prestamos.length === 0

                      const lkBs = cedulaLookupParaFila(
                        row.cedula || '',
                        row.numero_documento || ''
                      )
                        .trim()
                        .replace(/-/g, '')
                        .toUpperCase()
                      const enListaBs =
                        lkBs.length >= 5 ? autorizadoBsPorCedula[lkBs] : null
                      const monedaF = normMoneda(row.moneda_registro)
                      const tasaBd = tasaBdPorFila[row._rowIndex]
                      const tasaMan = row.tasa_cambio_manual
                      const bsBloqueado =
                        monedaF === 'BS' &&
                        (enListaBs !== true ||
                          tasaBd === undefined ||
                          (tasaBd === null &&
                            !(typeof tasaMan === 'number' && tasaMan > 0)))

                      const noPuedeGuardar =
                        row._hasErrors ||
                        sinCreditoElegido ||
                        sinCreditosActivos ||
                        bsBloqueado

                      const title = row._hasErrors
                        ? 'Corrija los errores de la fila para poder guardar'
                        : sinCreditosActivos
                          ? 'Sin créditos activos para esta cédula; use Revisar Pagos'
                          : sinCreditoElegido
                            ? 'Indique el ID de préstamo en el archivo (obligatorio)'
                            : 'Guardar esta fila'

                      return (
                        <div className="flex flex-col gap-1">
                          <button
                            type="button"
                            onClick={async () => {
                              if (noPuedeGuardar) return

                              setLocalSaving(s => new Set(s).add(row._rowIndex))

                              try {
                                await saveRowIfValid(row)
                              } finally {
                                setLocalSaving(s => {
                                  const next = new Set(s)

                                  next.delete(row._rowIndex)

                                  return next
                                })
                              }
                            }}
                            disabled={
                              noPuedeGuardar ||
                              isSaving(row._rowIndex) ||
                              serviceStatus === 'offline'
                            }
                            title={title}
                            className={`inline-flex items-center gap-1 rounded px-2 py-1.5 text-xs font-medium transition-colors ${
                              noPuedeGuardar
                                ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                                : 'bg-green-600 text-white hover:bg-green-700 disabled:opacity-70'
                            }`}
                          >
                            {isSaving(row._rowIndex) ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                Guardando...
                              </>
                            ) : (
                              <>
                                <Save className="h-3.5 w-3.5" />
                                Guardar
                              </>
                            )}
                          </button>

                          {noPuedeGuardar && onSendToRevisarPagos && (
                            <button
                              type="button"
                              onClick={() => onSendToRevisarPagos(row)}
                              disabled={
                                isSendingRevisar ||
                                isSaving(row._rowIndex) ||
                                serviceStatus === 'offline'
                              }
                              className="inline-flex items-center gap-1 rounded border border-amber-300 bg-amber-100 px-2 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-200 disabled:opacity-70"
                              title="Enviar esta fila a Revisar Pagos (no cumple validadores)"
                            >
                              {isSendingRevisar || isSaving(row._rowIndex) ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <>
                                  <Search className="h-3.5 w-3.5" />
                                  Revisar Pagos
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      )
                    })()
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Leyenda de errores */}

      {invalidas > 0 && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <strong>⚠ {invalidas} fila(s) con errores detectados.</strong>{' '}
          Corrígelas en la tabla; cuando pasen los validadores el botón Guardar
          se activará. Al guardar, la fila desaparece y el pago se aplica a
          cuotas y reglas de negocio.
          <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-xs text-red-700">
            <li>
              <strong>Cédula</strong>: debe existir en la base de datos de
              clientes (formato V/E/J + dígitos).
            </li>

            <li>
              <strong>Fecha</strong>: formato DD/MM/YYYY y fecha válida.
            </li>

            <li>
              <strong>Monto</strong>: número mayor a 0.
            </li>

            <li>
              <strong>Documento</strong>: no puede duplicarse en este archivo ni
              en la BD.
            </li>
          </ul>
        </div>
      )}
    </div>
  )
}
