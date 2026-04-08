/**





 * Tabla editable para preview de carga masiva de pagos.





 * Muestra errores de validación por celda (cédula, fecha, monto, documento).





 * La columna Crédito se rellena automáticamente cuando la cédula tiene un solo préstamo activo.





 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { Save, Loader2, Search, Check } from 'lucide-react'

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

import {
  cedulaLookupParaFila,
  claveDocumentoExcelCompuesta,
  convertirFechaParaBackendPago,
  buscarEnMapaPrestamos,
  normalizarNumeroDocumento,
} from '../../utils/pagoExcelValidation'

import { pagoService } from '../../services/pagoService'

import { auditoriaService } from '../../services/auditoriaService'

import { usePermissions } from '../../hooks/usePermissions'

import { toast } from 'sonner'

import { getErrorMessage } from '../../types/errors'

import { getTasaPorFecha } from '../../services/tasaCambioService'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

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

  /** Tras aplicar Visto (control 5) al pago que bloqueaba por documento duplicado, revalidar contra BD. */

  onRefrescarValidacionDocumentosBd?: () => Promise<void>

  /** Claves compuestas (comprobante + código opc.) marcadas por admin: duplicado en archivo permitido. */

  documentosRepetidosArchivoJustificados?: string[]

  /** Añade sufijos _A#### / _P#### al comprobante en cada fila con la misma clave compuesta. */

  onJustificarDocumentoRepetidoArchivo?: (
    claveDocumentoCompuesta: string
  ) => void

  /** Marca la clave compuesta duplicada como revisada sin modificar el texto del comprobante. */

  onMarcarDocumentoRepetidoArchivoJustificado?: (
    claveDocumentoCompuesta: string
  ) => void
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

      {!hasError && errorMsg && (
        <p className="mt-0.5 text-xs leading-tight text-amber-800">
          {errorMsg}
        </p>
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

/** Segunda línea en columna Crédito: préstamo del pago ya existente en BD (mismo documento). */

export function PrestamoDuplicadoEnBdBloque({ row }: { row: PagoExcelRow }) {
  if (row._prestamoIdExistenteDuplicadoBD === undefined) return null

  const pid = row._prestamoIdExistenteDuplicadoBD

  return (
    <div className="mt-1.5 border-t border-red-200 pt-1.5">
      <p className="text-[10px] font-medium text-red-600/90">
        Ya registrado (mismo documento)
      </p>

      <p
        className="text-sm font-semibold tabular-nums text-red-700"
        title="prestamo_id del pago que ya existe en la base de datos con este documento"
      >
        {typeof pid === 'number' && pid > 0 ? pid : '-'}
      </p>
    </div>
  )
}

function CreditoDestinoEnvoltorio({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <p className="text-[10px] font-medium leading-tight text-gray-600">
        Préstamo destino (esta fila)
      </p>

      {children}
    </div>
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

  const prestamos = buscarEnMapaPrestamos(lookup, prestamosPorCedula)

  if (prestamos.length === 0) {
    const mapKeys = Object.keys(prestamosPorCedula).length
    return (
      <div className="flex flex-col gap-0.5">
        <CreditoDestinoEnvoltorio>
          <div>
            <span
              className="rounded bg-red-50 px-1.5 py-0.5 text-xs font-medium text-red-700"
              title={`lookup=${lookup} mapKeys=${mapKeys}`}
            >
              Sin credito
            </span>

            <p className="mt-0.5 text-[10px] leading-tight text-red-500">
              No hay prestamos activos (APROBADO) para esta cedula
            </p>
          </div>
        </CreditoDestinoEnvoltorio>

        <PrestamoDuplicadoEnBdBloque row={row} />
      </div>
    )
  }

  // 1 crédito: si está vacío, mostrar el ID automáticamente (ya debería estar en el estado del padre gracias al useEffect).

  if (prestamos.length === 1) {
    const correctId = prestamos[0].id
    const vacio = prestamoIdVacio(row.prestamo_id)
    const ok = Number(row.prestamo_id) === correctId

    if (vacio) {
      return (
        <div className="flex flex-col gap-0.5">
          <CreditoDestinoEnvoltorio>
            <input
              type="text"
              value={String(correctId)}
              readOnly
              className="w-full rounded border border-green-200 bg-green-50 p-1 text-sm font-medium text-green-800"
              title="ID de préstamo auto-llenado (único crédito activo)"
            />
          </CreditoDestinoEnvoltorio>

          <PrestamoDuplicadoEnBdBloque row={row} />
        </div>
      )
    }

    if (ok) {
      return (
        <div className="flex flex-col gap-0.5">
          <CreditoDestinoEnvoltorio>
            <input
              type="text"
              value={String(correctId)}
              readOnly
              className="w-full rounded border border-gray-200 bg-green-50 p-1 text-sm font-medium text-green-800"
              title="ID de préstamo coincide con el único crédito activo"
            />
          </CreditoDestinoEnvoltorio>

          <PrestamoDuplicadoEnBdBloque row={row} />
        </div>
      )
    }

    return (
      <div className="flex flex-col gap-0.5">
        <CreditoDestinoEnvoltorio>
          <input
            type="text"
            value={String(row.prestamo_id ?? '')}
            readOnly
            className="w-full rounded border border-amber-300 bg-amber-50 p-1 text-sm text-amber-900"
            title="ID no coincide con el crédito; se ajustará al guardar si corresponde"
          />
        </CreditoDestinoEnvoltorio>

        <PrestamoDuplicadoEnBdBloque row={row} />
      </div>
    )
  }

  // 2+ créditos: el usuario debe elegir

  const valorActual = !prestamoIdVacio(row.prestamo_id)
    ? String(row.prestamo_id)
    : 'none'

  const esValido = prestamos.some(p => p.id === row.prestamo_id)

  return (
    <div className="flex flex-col gap-0.5">
      <CreditoDestinoEnvoltorio>
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
      </CreditoDestinoEnvoltorio>

      <PrestamoDuplicadoEnBdBloque row={row} />
    </div>
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

  onRefrescarValidacionDocumentosBd,

  documentosRepetidosArchivoJustificados = [],

  onJustificarDocumentoRepetidoArchivo,

  onMarcarDocumentoRepetidoArchivoJustificado,
}: FilaEditableProps) {
  const { isAdmin } = usePermissions()

  const [vistoPagoIdCargando, setVistoPagoIdCargando] = useState<number | null>(
    null
  )

  const [vistoArchivoDialogOpen, setVistoArchivoDialogOpen] = useState(false)

  const [vistoArchivoDocNorm, setVistoArchivoDocNorm] = useState<string | null>(
    null
  )

  const [vistoBdDialogOpen, setVistoBdDialogOpen] = useState(false)

  const [vistoBdPagoId, setVistoBdPagoId] = useState<number | null>(null)

  const [vistoBdDocNorm, setVistoBdDocNorm] = useState<string | null>(null)

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

  // Auto-llenar prestamo_id cuando hay un único crédito válido (aunque esté vacío);
  // También corregir cuando hay valor incorrecto (p. ej. nº de documento en columna crédito).

  useEffect(() => {
    if (!rows?.length || Object.keys(prestamosPorCedula).length === 0) return

    rows.forEach(row => {
      const lookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const prestamos = buscarEnMapaPrestamos(lookup, prestamosPorCedula)

      if (prestamos.length === 1) {
        const correctId = prestamos[0].id
        const esVacio = prestamoIdVacio(row.prestamo_id)
        const esIncorrecto = Number(row.prestamo_id) !== correctId && !esVacio

        // Auto-llenar si está vacío, o corregir si es incorrecto
        if (esVacio || esIncorrecto) {
          onUpdateCell(row, 'prestamo_id', correctId)
        }
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

  const docFreqEnArchivo = useMemo(() => {
    const m = new Map<string, number>()
    for (const r of rows) {
      const d = claveDocumentoExcelCompuesta(
        r.numero_documento,
        r.codigo_documento ?? null
      )
      if (d) m.set(d, (m.get(d) || 0) + 1)
    }
    return m
  }, [rows])

  const justificadosArchivoSet = useMemo(
    () => new Set(documentosRepetidosArchivoJustificados),
    [documentosRepetidosArchivoJustificados]
  )

  return (
    <div className="space-y-4">
      {/* Indicadores: filas cargadas, válidas, inválidas (varían al editar y validar) */}

      <div className="rounded-lg border border-blue-400 bg-blue-50 p-4">
        <h2 className="mb-2 text-lg font-bold text-blue-800">
          Indicadores (se actualizan al editar)
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            v2.1
          </span>
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
          </span>
        </div>
      </div>

      {/* Tabla */}

      <div className="overflow-x-auto rounded border">
        <table className="w-full border-collapse text-sm">
          <thead className="border-b-2 border-gray-300 bg-gray-100">
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

              <th className="min-w-[100px] border-r p-2 text-left font-semibold">
                Código
              </th>

              <th className="min-w-[200px] border-r p-2 text-left font-semibold">
                Link comprobante
              </th>

              <th className="min-w-[140px] border-r p-2 text-left font-semibold">
                Crédito
              </th>

              <th className="min-w-[4.5rem] p-2 text-center font-semibold">
                Acción
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-300">
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

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.codigo_documento ?? ''}
                    isValid={row._validation.numero_documento?.isValid}
                    errorMsg={undefined}
                    placeholder="Opcional"
                    onChange={v => onUpdateCell(row, 'codigo_documento', v)}
                  />
                </td>

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.link_comprobante ?? ''}
                    isValid={row._validation.link_comprobante?.isValid}
                    errorMsg={row._validation.link_comprobante?.message}
                    placeholder="https:// o ID Drive"
                    onChange={v => onUpdateCell(row, 'link_comprobante', v)}
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

                      const prestamos = buscarEnMapaPrestamos(
                        lookup,
                        prestamosPorCedula
                      )

                      const sinCreditoElegido =
                        prestamos.length > 1 && prestamoIdVacio(row.prestamo_id)

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

                      const motivoBloqueo = row._hasErrors
                        ? Object.entries(row._validation || {})
                            .filter(([, v]) => !v.isValid && v.message)
                            .map(([, v]) => v.message)
                            .join('; ') || 'Corrija los errores'
                        : sinCreditosActivos
                          ? 'Sin creditos activos para esta cedula'
                          : sinCreditoElegido
                            ? 'Elija un credito de los disponibles'
                            : bsBloqueado
                              ? 'Bs requiere tasa de cambio'
                              : ''

                      const pagoIdCampo = row._pagoIdExistenteDuplicadoBD

                      const msgDoc =
                        row._validation?.numero_documento?.message ?? ''

                      const matchPagoId = msgDoc.match(/\(pago id (\d+)\)/i)

                      const pagoIdDesdeMensaje = matchPagoId
                        ? Number(matchPagoId[1])
                        : NaN

                      const pagoIdParaVisto =
                        typeof pagoIdCampo === 'number' &&
                        pagoIdCampo > 0 &&
                        Number.isFinite(pagoIdCampo)
                          ? pagoIdCampo
                          : Number.isFinite(pagoIdDesdeMensaje) &&
                              pagoIdDesdeMensaje > 0
                            ? pagoIdDesdeMensaje
                            : null

                      const claveDocAccion = claveDocumentoExcelCompuesta(
                        row.numero_documento,
                        row.codigo_documento ?? null
                      )
                      const esDupArchivoFila =
                        !!claveDocAccion &&
                        (docFreqEnArchivo.get(claveDocAccion) || 0) > 1
                      const archivoDupJustificado =
                        !!claveDocAccion &&
                        justificadosArchivoSet.has(claveDocAccion)

                      const puedeVistoControl5Bd = pagoIdParaVisto != null

                      const puedeVistoJustificarArchivo =
                        esDupArchivoFila &&
                        !archivoDupJustificado &&
                        !!onJustificarDocumentoRepetidoArchivo

                      /** Duplicado en BD (pagos o cola errores): aunque no haya pago_id para control 5, debe poder añadirse sufijo. */
                      const mensajeIndicaDupDocumentoBd =
                        /ya existe en la base de datos/i.test(msgDoc)

                      const puedeVistoSufijoPorDupBd =
                        !!claveDocAccion &&
                        !!onJustificarDocumentoRepetidoArchivo &&
                        !row._validation?.numero_documento?.isValid &&
                        mensajeIndicaDupDocumentoBd

                      const mostrarBotonVisto =
                        puedeVistoJustificarArchivo ||
                        puedeVistoControl5Bd ||
                        puedeVistoSufijoPorDupBd

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
                            title={motivoBloqueo || 'Guardar esta fila'}
                            className={`inline-flex items-center justify-center rounded p-1.5 transition-colors ${
                              noPuedeGuardar
                                ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                                : 'bg-green-600 text-white hover:bg-green-700 disabled:opacity-70'
                            }`}
                          >
                            {isSaving(row._rowIndex) ? (
                              <>
                                <Loader2
                                  className="h-3.5 w-3.5 animate-spin"
                                  aria-hidden
                                />
                                <span className="sr-only">Guardando</span>
                              </>
                            ) : (
                              <>
                                <Save className="h-3.5 w-3.5" aria-hidden />
                                <span className="sr-only">Guardar</span>
                              </>
                            )}
                          </button>

                          {mostrarBotonVisto && (
                            <button
                              type="button"
                              onClick={async () => {
                                if (!isAdmin) {
                                  toast.error(
                                    'Solo un usuario administrador puede aplicar Visto.'
                                  )
                                  return
                                }
                                // Duplicado en Excel: la decisión (sufijos o solo autorizar) es humana → diálogo.
                                if (
                                  puedeVistoJustificarArchivo &&
                                  claveDocAccion
                                ) {
                                  setVistoArchivoDocNorm(claveDocAccion)
                                  setVistoArchivoDialogOpen(true)
                                  return
                                }
                                // Duplicado en BD: siempre ofrecer sufijo; control 5 solo si hay pago_id operativo.
                                if (
                                  claveDocAccion &&
                                  onJustificarDocumentoRepetidoArchivo &&
                                  puedeVistoSufijoPorDupBd
                                ) {
                                  setVistoBdPagoId(
                                    puedeVistoControl5Bd &&
                                      pagoIdParaVisto != null
                                      ? pagoIdParaVisto
                                      : null
                                  )
                                  setVistoBdDocNorm(claveDocAccion)
                                  setVistoBdDialogOpen(true)
                                }
                              }}
                              disabled={
                                !isAdmin ||
                                vistoPagoIdCargando != null ||
                                isSaving(row._rowIndex) ||
                                serviceStatus === 'offline'
                              }
                              title={
                                isAdmin
                                  ? puedeVistoJustificarArchivo
                                    ? 'Visto: elige si añadir sufijos o autorizar sin cambiar el documento.'
                                    : puedeVistoSufijoPorDupBd
                                      ? 'Visto: documento ya en BD - añadir código (sufijo) o, si aplica, control 5.'
                                      : 'Visto: solo administradores.'
                                  : 'Visto: solo administradores.'
                              }
                              className={`inline-flex items-center justify-center gap-0.5 rounded border p-1.5 text-[10px] font-semibold disabled:opacity-60 ${
                                isAdmin
                                  ? 'border-violet-400 bg-violet-100 text-violet-950 hover:bg-violet-200'
                                  : 'cursor-not-allowed border-gray-300 bg-gray-100 text-gray-500'
                              }`}
                            >
                              {puedeVistoControl5Bd &&
                              vistoPagoIdCargando === pagoIdParaVisto ? (
                                <Loader2
                                  className="h-3.5 w-3.5 animate-spin"
                                  aria-hidden
                                />
                              ) : (
                                <Check className="h-3.5 w-3.5" aria-hidden />
                              )}
                              Visto
                            </button>
                          )}

                          {noPuedeGuardar && onSendToRevisarPagos && (
                            <button
                              type="button"
                              onClick={() => onSendToRevisarPagos(row)}
                              disabled={
                                isSendingRevisar ||
                                isSaving(row._rowIndex) ||
                                serviceStatus === 'offline'
                              }
                              className="inline-flex items-center justify-center rounded border border-amber-300 bg-amber-100 p-1.5 text-amber-800 hover:bg-amber-200 disabled:opacity-70"
                              title={
                                motivoBloqueo
                                  ? `Enviar a Revisar Pagos - ${motivoBloqueo}`
                                  : 'Enviar esta fila a Revisar Pagos (no cumple validadores)'
                              }
                            >
                              {isSendingRevisar || isSaving(row._rowIndex) ? (
                                <>
                                  <Loader2
                                    className="h-3.5 w-3.5 animate-spin"
                                    aria-hidden
                                  />
                                  <span className="sr-only">
                                    Enviando a Revisar Pagos
                                  </span>
                                </>
                              ) : (
                                <>
                                  <Search className="h-3.5 w-3.5" aria-hidden />
                                  <span className="sr-only">Revisar Pagos</span>
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
              <strong>Documento</strong>: la clave comprobante + código (columna
              Código opcional) no puede repetirse en este archivo ni en la BD.
            </li>
          </ul>
        </div>
      )}

      <Dialog
        open={vistoArchivoDialogOpen}
        onOpenChange={open => {
          setVistoArchivoDialogOpen(open)
          if (!open) setVistoArchivoDocNorm(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Documento repetido en este archivo</DialogTitle>
            <div className="space-y-2 text-sm text-gray-600">
              <p>
                Usted decide si se modifica el número de documento o solo se
                marca como revisado.
              </p>
              <ul className="list-inside list-disc space-y-1 text-xs">
                <li>
                  <strong>Añadir sufijos</strong>: agrega{' '}
                  <code className="rounded bg-gray-100 px-1">_A####</code> o{' '}
                  <code className="rounded bg-gray-100 px-1">_P####</code> en
                  cada fila afectada (únicos para la base de datos).
                </li>
                <li>
                  <strong>Sin cambiar el texto</strong>: el documento queda
                  igual; la fila pasa validación local, pero al guardar puede
                  fallar si la regla de unicidad en BD no lo permite.
                </li>
              </ul>
            </div>
          </DialogHeader>
          <DialogFooter className="flex flex-col gap-2 sm:flex-col sm:justify-stretch">
            <button
              type="button"
              className="w-full rounded-md bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"
              onClick={() => {
                const d = vistoArchivoDocNorm
                if (d && onJustificarDocumentoRepetidoArchivo) {
                  onJustificarDocumentoRepetidoArchivo(d)
                  toast.success(
                    'Se añadió _A#### o _P#### a cada fila con este documento. Puede guardar cada fila.'
                  )
                }
                setVistoArchivoDialogOpen(false)
                setVistoArchivoDocNorm(null)
              }}
            >
              Añadir sufijos al documento
            </button>
            {onMarcarDocumentoRepetidoArchivoJustificado ? (
              <button
                type="button"
                className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
                onClick={() => {
                  const d = vistoArchivoDocNorm
                  if (d) {
                    onMarcarDocumentoRepetidoArchivoJustificado(d)
                    toast.success(
                      'Autorizado sin modificar el documento (revisión humana).'
                    )
                  }
                  setVistoArchivoDialogOpen(false)
                  setVistoArchivoDocNorm(null)
                }}
              >
                Autorizar sin cambiar el documento
              </button>
            ) : null}
            <button
              type="button"
              className="w-full rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
              onClick={() => {
                setVistoArchivoDialogOpen(false)
                setVistoArchivoDocNorm(null)
              }}
            >
              Cancelar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={vistoBdDialogOpen}
        onOpenChange={open => {
          setVistoBdDialogOpen(open)
          if (!open) {
            setVistoBdPagoId(null)
            setVistoBdDocNorm(null)
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              Documento ya existente en la base de datos
            </DialogTitle>
            <div className="space-y-2 text-sm text-gray-600">
              <p>
                Lo habitual con el mismo comprobante en otra cuota es{' '}
                <strong>añadir el código</strong> (
                <code className="rounded bg-gray-100 px-1">_A####</code> /{' '}
                <code className="rounded bg-gray-100 px-1">_P####</code>) al
                documento en esta carga. El control 5 solo aplica en casos
                concretos de auditoría (misma fecha y monto entre pagos en BD).
              </p>
              <ul className="list-inside list-disc space-y-1 text-xs">
                <li>
                  <strong>Añadir código</strong>: nuevo Nº documento único en
                  las filas de este archivo con el mismo valor.
                </li>
                <li>
                  <strong>Control 5</strong>: solo si el pago en BD cumple
                  duplicado fecha+monto; si el servidor rechaza, use sufijo.
                </li>
              </ul>
            </div>
          </DialogHeader>
          <DialogFooter className="flex flex-col gap-2 sm:flex-col sm:justify-stretch">
            <button
              type="button"
              className="w-full rounded-md bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={
                !vistoBdDocNorm ||
                !onJustificarDocumentoRepetidoArchivo ||
                serviceStatus === 'offline'
              }
              title={
                !onJustificarDocumentoRepetidoArchivo
                  ? 'No disponible en este contexto'
                  : undefined
              }
              onClick={() => {
                const d = vistoBdDocNorm
                if (d && onJustificarDocumentoRepetidoArchivo) {
                  onJustificarDocumentoRepetidoArchivo(d)
                  toast.success(
                    'Se añadió _A#### o _P#### a cada fila con este documento en la carga.'
                  )
                }
                setVistoBdDialogOpen(false)
                setVistoBdPagoId(null)
                setVistoBdDocNorm(null)
              }}
            >
              Añadir código (sufijo) en esta carga
            </button>
            {vistoBdPagoId != null ? (
              <button
                type="button"
                className="w-full rounded-md border border-violet-500 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-950 hover:bg-violet-100 disabled:opacity-50"
                disabled={
                  vistoPagoIdCargando != null || serviceStatus === 'offline'
                }
                onClick={async () => {
                  const pid = vistoBdPagoId
                  if (pid == null) return
                  setVistoPagoIdCargando(pid)
                  try {
                    await auditoriaService.aplicarControl5VistoPago(pid)
                    toast.success(
                      'Visto control 5 aplicado al pago en BD. Revalidando filas…'
                    )
                    await onRefrescarValidacionDocumentosBd?.()
                    setVistoBdDialogOpen(false)
                    setVistoBdPagoId(null)
                    setVistoBdDocNorm(null)
                  } catch (e) {
                    toast.error(
                      `${getErrorMessage(e)} Si no aplica control 5, use «Añadir código (sufijo)».`
                    )
                  } finally {
                    setVistoPagoIdCargando(null)
                  }
                }}
              >
                {vistoPagoIdCargando != null &&
                vistoBdPagoId === vistoPagoIdCargando
                  ? 'Aplicando…'
                  : 'Visto control 5 (pago en BD)'}
              </button>
            ) : null}
            <button
              type="button"
              className="w-full rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
              onClick={() => {
                setVistoBdDialogOpen(false)
                setVistoBdPagoId(null)
                setVistoBdDocNorm(null)
              }}
            >
              Cancelar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
