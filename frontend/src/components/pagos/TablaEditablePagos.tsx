/**
 * Tabla editable para preview de carga masiva de pagos.
 * Muestra errores de validación por celda (cédula, fecha, monto, documento).
 */

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

export interface FilaEditableProps {
  rows: PagoExcelRow[]
  prestamosPorCedula?: Record<string, Array<{ id: number; estado: string }>>
  onRowsChange?: (newRows: PagoExcelRow[]) => void
  onUpdateCell: (row: PagoExcelRow, field: string, value: string | number) => void
  saveRowIfValid?: (row: PagoExcelRow) => Promise<boolean>
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

export function TablaEditablePagos({
  rows,
  onUpdateCell,
}: FilaEditableProps) {
  if (!rows || rows.length === 0) {
    return (
      <div className="text-gray-500 p-4 border border-dashed border-gray-300 rounded">
        No hay datos para mostrar
      </div>
    )
  }

  const total = rows.length
  const validos = rows.filter((r) => !r._hasErrors).length
  const conError = total - validos

  return (
    <div className="space-y-4">
      {/* Encabezado con resumen */}
      <div className="bg-blue-50 border border-blue-400 rounded p-4">
        <h2 className="text-lg font-bold text-blue-800 mb-2">Vista previa — Pagos cargados</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <span className="font-medium text-gray-700">Total: <strong>{total}</strong></span>
          <span className="font-medium text-green-700">
            ✓ Válidos: <strong>{validos}</strong>
          </span>
          {conError > 0 && (
            <span className="font-medium text-red-700">
              ✗ Con errores: <strong>{conError}</strong>
            </span>
          )}
        </div>
      </div>

      {/* Tabla */}
      <div className="border rounded overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="p-2 text-center font-semibold border-r w-12">#</th>
              <th className="p-2 text-left font-semibold border-r min-w-[140px]">Cédula</th>
              <th className="p-2 text-left font-semibold border-r min-w-[130px]">Fecha pago</th>
              <th className="p-2 text-left font-semibold border-r min-w-[120px]">Monto</th>
              <th className="p-2 text-left font-semibold border-r min-w-[160px]">Documento</th>
              <th className="p-2 text-left font-semibold min-w-[80px]">Crédito</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row._rowIndex}
                className={row._hasErrors ? 'bg-red-50 border-l-4 border-l-red-400' : 'bg-white hover:bg-gray-50'}
              >
                <td className="p-2 border-r text-center text-gray-500">{row._rowIndex}</td>

                {/* Cédula */}
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

                {/* Crédito (solo lectura por ahora) */}
                <td className="p-2">
                  <input
                    type="text"
                    value={row.prestamo_id ?? ''}
                    readOnly
                    className="w-full p-1 border border-gray-200 rounded bg-gray-50 text-gray-600 text-sm"
                    placeholder="--"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Leyenda de errores */}
      {conError > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
          <strong>⚠ {conError} fila(s) con errores detectados.</strong>
          {' '}Corrígelas directamente en la tabla antes de guardar.
          <ul className="mt-1.5 list-disc list-inside space-y-0.5 text-xs text-red-700">
            <li><strong>Cédula</strong>: debe existir en la base de datos de clientes (formato V/E/J + dígitos).</li>
            <li><strong>Fecha</strong>: formato DD/MM/YYYY y fecha válida.</li>
            <li><strong>Monto</strong>: número mayor a 0.</li>
            <li><strong>Documento</strong>: no puede duplicarse en este archivo ni en la BD.</li>
          </ul>
        </div>
      )}
    </div>
  )
}
