/**
 * Tabla editable para preview de carga masiva de pagos.
 * Muestra errores de validaciÃ³n por celda (cÃ©dula, fecha, monto, documento).
 * La columna CrÃ©dito se rellena automÃ¡ticamente cuando la cÃ©dula tiene un solo prÃ©stamo activo.
 */

import { useEffect, useRef, useState } from 'react'
import { Save, Loader2, Search } from 'lucide-react'
import type { PagoExcelRow } from '../../utils/pagoExcelValidation'
import { cedulaLookupParaFila } from '../../utils/pagoExcelValidation'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'

export interface FilaEditableProps {
  rows: PagoExcelRow[]
  prestamosPorCedula?: Record<string, Array<{ id: number; estado: string }>>
  onRowsChange?: (newRows: PagoExcelRow[]) => void
  onUpdateCell: (row: PagoExcelRow, field: string, value: string | number) => void
  saveRowIfValid?: (row: PagoExcelRow) => Promise<boolean>
  /** Si se pasa, el botÃ³n Guardar muestra estado de carga y se deshabilita mientras guarda. */
  savingProgress?: Record<number, boolean>
  serviceStatus?: 'online' | 'offline' | 'checking' | 'unknown'
  /** EnvÃ­a esta fila a Revisar Pagos (para filas que no cumplen validadores). */
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
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full p-1 border rounded text-sm ${
          hasError
            ? 'border-red-500 bg-red-50 text-red-900 focus:ring-red-300'
            : 'border-gray-300 focus:border-blue-400'
        } focus:outline-none focus:ring-1`}
      />
      {hasError && errorMsg && (
        <p className="text-xs text-red-600 mt-0.5 leading-tight">{errorMsg}</p>
      )}
    </div>
  )
}

function prestamoIdVacio(v: unknown): boolean {
  return v == null || v === undefined || v === '' || v === 'none' || v === 0 || (typeof v === 'number' && Number.isNaN(v))
}

/**
 * CrÃ©dito: si hay 1 prÃ©stamo activo por cÃ©dula se carga automÃ¡ticamente;
 * si hay mÃ¡s de uno el usuario debe elegir en el selector;
 * si no hay (0) se muestra "Sin crÃ©dito" (solo aplica cuando el cliente estÃ¡ registrado pero sin crÃ©ditos activos; si no hay cliente, la cÃ©dula ya marca error).
 */
function CreditoCell({
  row,
  prestamosPorCedula,
  onUpdateCell,
}: {
  row: PagoExcelRow
  prestamosPorCedula: Record<string, Array<{ id: number; estado: string }>>
  onUpdateCell: (row: PagoExcelRow, field: string, value: string | number) => void
}) {
  const lookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
  const sinGuion = lookup.replace(/-/g, '')
  const prestamos =
    prestamosPorCedula[lookup] ||
    prestamosPorCedula[sinGuion] ||
    prestamosPorCedula[lookup?.toUpperCase()] ||
    prestamosPorCedula[lookup?.toLowerCase()] ||
    []

  // 0 crÃ©ditos: cliente puede no existir (cedula invÃ¡lida) o existir sin crÃ©ditos activos
  if (prestamos.length === 0) {
    return (
      <span className="text-xs text-gray-500 italic">Sin crÃ©dito</span>
    )
  }

  // 1 crÃ©dito: se carga automÃ¡ticamente (ya asignado por useEffect), solo mostrar
  if (prestamos.length === 1) {
    const displayId = !prestamoIdVacio(row.prestamo_id) ? row.prestamo_id : prestamos[0].id
    return (
      <input
        type="text"
        value={displayId ? ''}
        readOnly
        className="w-full p-1 border border-gray-200 rounded bg-green-50 text-green-800 text-sm font-medium"
        placeholder="â"
        title="Cargado automÃ¡ticamente (un solo crÃ©dito por cÃ©dula)"
      />
    )
  }

  // 2+ crÃ©ditos: el usuario debe elegir
  const valorActual = !prestamoIdVacio(row.prestamo_id) ? String(row.prestamo_id) : 'none'
  const esValido = prestamos.some((p) => p.id === row.prestamo_id)
  return (
    <Select
      value={valorActual}
      onValueChange={(v) => onUpdateCell(row, 'prestamo_id', v === 'none' ? 0 : Number(v))}
    >
      <SelectTrigger
        className={`h-8 text-xs w-full ${!esValido && valorActual === 'none' ? 'border-amber-500 bg-amber-50' : ''}`}
      >
        <SelectValue placeholder="Elegir crÃ©dito" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="none">â Elegir crÃ©dito â</SelectItem>
        {prestamos.map((p) => (
          <SelectItem key={p.id} value={String(p.id)}>
            CrÃ©dito #{p.id}
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
  const autoFilledRef = useRef<Set<number>>(new Set())
  const [localSaving, setLocalSaving] = useState<Set<number>>(new Set())
  const isSaving = (rowIndex: number) => savingProgress[rowIndex] ? localSaving.has(rowIndex)

  // Auto-rellenar prestamo_id cuando la cÃ©dula tiene exactamente un prÃ©stamo (persiste en estado del padre)
  useEffect(() => {
    if (!rows?.length || Object.keys(prestamosPorCedula).length === 0) return
    rows.forEach((row) => {
      if (autoFilledRef.current.has(row._rowIndex)) return
      if (!prestamoIdVacio(row.prestamo_id)) return
      const lookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
      const sinGuion = lookup.replace(/-/g, '')
      const prestamos =
        prestamosPorCedula[lookup] ||
        prestamosPorCedula[sinGuion] ||
        prestamosPorCedula[lookup.toUpperCase()] ||
        prestamosPorCedula[lookup.toLowerCase()] ||
        []
      if (prestamos.length === 1) {
        autoFilledRef.current.add(row._rowIndex)
        onUpdateCell(row, 'prestamo_id', prestamos[0].id)
      }
    })
  }, [rows, prestamosPorCedula, onUpdateCell])

  if (!rows || rows.length === 0) {
    return (
      <div className="text-gray-500 p-4 border border-dashed border-gray-300 rounded">
        No hay datos para mostrar
      </div>
    )
  }

  const total = rows.length
  const validos = rows.filter((r) => !r._hasErrors).length
  const invalidas = total - validos

  return (
    <div className="space-y-4">
      {/* Indicadores: filas cargadas, vÃ¡lidas, invÃ¡lidas (varÃ­an al editar y validar) */}
      <div className="bg-blue-50 border border-blue-400 rounded-lg p-4">
        <h2 className="text-lg font-bold text-blue-800 mb-2">Indicadores (se actualizan al editar)</h2>
        <div className="flex flex-wrap gap-6 text-sm">
          <span className="font-medium text-gray-700">
            Filas cargadas: <strong className="text-gray-900 tabular-nums">{total}</strong>
          </span>
          <span className="font-medium text-green-700">
            VÃ¡lidas: <strong className="tabular-nums">{validos}</strong>
          </span>
          <span className="font-medium text-red-700">
            InvÃ¡lidas: <strong className="tabular-nums">{invalidas}</strong>
            <span className="text-blue-600 ml-1">(van a Revisar Pagos)</span>
          </span>
        </div>
        <p className="text-xs text-blue-700 mt-2">
          <strong>Los que no cumplen validadores van a Revisar Pagos.</strong> Puede enviarlos con el botÃ³n &quot;Revisar Pagos&quot; por fila o con &quot;Revisar Pagos (N)&quot; para enviar todas las invÃ¡lidas.
        </p>
        <p className="text-xs text-blue-700 mt-1">
          Al guardar una fila (botÃ³n Guardar en cada fila), esta desaparece de la tabla y el pago se registra aplicando las mismas reglas de negocio: aplicaciÃ³n a cuotas (FIFO), conciliaciÃ³n y actualizaciÃ³n de pagos/cuotas.
        </p>
        <p className="text-xs text-blue-700 mt-1">
          <strong>CrÃ©dito:</strong> si hay un solo crÃ©dito activo por cÃ©dula se carga automÃ¡ticamente; si hay varios debe elegir en la lista. &quot;Sin crÃ©dito&quot; aplica cuando el cliente estÃ¡ registrado pero no tiene crÃ©ditos activos (si no hay cliente, la cÃ©dula marca error).
        </p>
      </div>

      {/* Tabla */}
      <div className="border rounded overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="p-2 text-center font-semibold border-r w-12">#</th>
              <th className="p-2 text-left font-semibold border-r min-w-[140px]">CÃ©dula</th>
              <th className="p-2 text-left font-semibold border-r min-w-[130px]">Fecha pago</th>
              <th className="p-2 text-left font-semibold border-r min-w-[120px]">Monto</th>
              <th className="p-2 text-left font-semibold border-r min-w-[160px]">Documento</th>
              <th className="p-2 text-left font-semibold border-r min-w-[80px]">CrÃ©dito</th>
              <th className="p-2 text-center font-semibold min-w-[100px]">AcciÃ³n</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row._rowIndex}
                className={row._hasErrors ? 'bg-red-50 border-l-4 border-l-red-400' : 'bg-white hover:bg-gray-50'}
              >
                <td className="p-2 border-r text-center text-gray-500">{row._rowIndex}</td>

                {/* CÃ©dula */}
                <td className="p-2 border-r">
                  <CeldaEditable
                    value={row.cedula}
                    isValid={row._validation.cedula?.isValid}
                    errorMsg={row._validation.cedula?.message}
                    placeholder="V12345678"
                    onChange={(v) => onUpdateCell(row, 'cedula', v)}
                  />
                </td>

                {/* Fecha */}
                <td className="p-2 border-r">
                  <CeldaEditable
                    value={row.fecha_pago}
                    isValid={row._validation.fecha_pago?.isValid}
                    errorMsg={row._validation.fecha_pago?.message}
                    placeholder="DD/MM/YYYY"
                    onChange={(v) => onUpdateCell(row, 'fecha_pago', v)}
                  />
                </td>

                {/* Monto */}
                <td className="p-2 border-r">
                  <CeldaEditable
                    value={row.monto_pagado || ''}
                    isValid={row._validation.monto_pagado?.isValid}
                    errorMsg={row._validation.monto_pagado?.message}
                    placeholder="0.00"
                    type="number"
                    onChange={(v) => onUpdateCell(row, 'monto_pagado', v)}
                  />
                </td>

                {/* Documento */}
                <td className="p-2 border-r">
                  <CeldaEditable
                    value={row.numero_documento}
                    isValid={row._validation.numero_documento?.isValid}
                    errorMsg={row._validation.numero_documento?.message}
                    placeholder="VE/xxx"
                    onChange={(v) => onUpdateCell(row, 'numero_documento', v)}
                  />
                </td>

                {/* CrÃ©dito: 1 = auto; varios = elegir; 0 = Sin crÃ©dito (solo cuando no hay cliente o sin crÃ©ditos activos) */}
                <td className="p-2 border-r">
                  <CreditoCell
                    row={row}
                    prestamosPorCedula={prestamosPorCedula}
                    onUpdateCell={onUpdateCell}
                  />
                </td>

                {/* AcciÃ³n: Guardar solo si la fila pasa validadores y crÃ©dito (1 auto, varios elegido, 0 no guardar) */}
                <td className="p-2">
                  {saveRowIfValid ? (() => {
                    const lookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
                    const sinGuion = lookup.replace(/-/g, '')
                    const prestamos =
                      prestamosPorCedula[lookup] ||
                      prestamosPorCedula[sinGuion] ||
                      prestamosPorCedula[lookup?.toUpperCase()] ||
                      prestamosPorCedula[lookup?.toLowerCase()] ||
                      []
                    const sinCreditoElegido = prestamos.length > 1 && prestamoIdVacio(row.prestamo_id)
                    const sinCreditosActivos = prestamos.length === 0
                    const noPuedeGuardar = row._hasErrors || sinCreditoElegido || sinCreditosActivos
                    const title = row._hasErrors
                      ? 'Corrija los errores de la fila para poder guardar'
                      : sinCreditosActivos
                        ? 'Sin crÃ©ditos activos para esta cÃ©dula; use Revisar Pagos'
                        : sinCreditoElegido
                          ? 'Elija un crÃ©dito en la lista (varios por cÃ©dula)'
                          : 'Guardar esta fila'
                    return (
                    <div className="flex flex-col gap-1">
                      <button
                        type="button"
                        onClick={async () => {
                          if (noPuedeGuardar) return
                          setLocalSaving((s) => new Set(s).add(row._rowIndex))
                          try {
                            await saveRowIfValid(row)
                          } finally {
                            setLocalSaving((s) => {
                              const next = new Set(s)
                              next.delete(row._rowIndex)
                              return next
                            })
                          }
                        }}
                        disabled={noPuedeGuardar || isSaving(row._rowIndex) || serviceStatus === 'offline'}
                        title={title}
                        className={`inline-flex items-center gap-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                          noPuedeGuardar
                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
                          disabled={isSendingRevisar || isSaving(row._rowIndex) || serviceStatus === 'offline'}
                          className="inline-flex items-center gap-1 px-2 py-1.5 rounded text-xs font-medium bg-amber-100 text-amber-800 border border-amber-300 hover:bg-amber-200 disabled:opacity-70"
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
                  })() : (
                    <span className="text-gray-400 text-xs">â</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Leyenda de errores */}
      {invalidas > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
          <strong>â  {invalidas} fila(s) con errores detectados.</strong>
          {' '}CorrÃ­gelas en la tabla; cuando pasen los validadores el botÃ³n Guardar se activarÃ¡. Al guardar, la fila desaparece y el pago se aplica a cuotas y reglas de negocio.
          <ul className="mt-1.5 list-disc list-inside space-y-0.5 text-xs text-red-700">
            <li><strong>CÃ©dula</strong>: debe existir en la base de datos de clientes (formato V/E/J + dÃ­gitos).</li>
            <li><strong>Fecha</strong>: formato DD/MM/YYYY y fecha vÃ¡lida.</li>
            <li><strong>Monto</strong>: nÃºmero mayor a 0.</li>
            <li><strong>Documento</strong>: no puede duplicarse en este archivo ni en la BD.</li>
          </ul>
        </div>
      )}
    </div>
  )
}
