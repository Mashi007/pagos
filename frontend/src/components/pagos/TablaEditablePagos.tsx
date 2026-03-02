/**
 * Tabla Editable Simplificada para Preview de Carga Masiva
 * Versión básica sin complejidades
 */

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

export interface FilaEditableProps {
  rows: PagoExcelRow[]
  prestamosPorCedula?: Record<string, Array<{ id: number; estado: string }>>
  onRowsChange?: (newRows: PagoExcelRow[]) => void
  onUpdateCell: (row: PagoExcelRow, field: string, value: string | number) => void
  saveRowIfValid?: (row: PagoExcelRow) => Promise<boolean>
}

export function TablaEditablePagos({
  rows,
  onUpdateCell,
}: FilaEditableProps) {
  console.log('🟦 TablaEditablePagos recibió rows:', rows?.length || 0, rows)
  
  if (!rows || rows.length === 0) {
    return <div className="text-gray-500 p-4 border border-dashed border-gray-300 rounded">❌ No hay datos para mostrar</div>
  }

  return (
    <div className="space-y-4">
      {/* Encabezado simple */}
      <div className="bg-blue-50 border border-blue-400 rounded p-4">
        <h2 className="text-xl font-bold text-blue-700 mb-3">✅ TABLA EDITABLE - NUEVA INTERFAZ</h2>
        <div className="flex gap-4">
          <span className="text-sm">
            <strong>Total:</strong> {rows.length}
          </span>
          <span className="text-sm">
            <strong>Cargados:</strong> {rows.length}
          </span>
          <span className="text-sm text-green-700">
            <strong>Válidos:</strong> {rows.filter((r) => !r._hasErrors).length}
          </span>
          <span className="text-sm text-red-700">
            <strong>Con Errores:</strong> {rows.filter((r) => r._hasErrors).length}
          </span>
        </div>
      </div>

      {/* Tabla HTML simple */}
      <div className="border rounded overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="p-2 text-left font-medium border-r">Fila</th>
              <th className="p-2 text-left font-medium border-r">Cédula</th>
              <th className="p-2 text-left font-medium border-r">Fecha Pago</th>
              <th className="p-2 text-left font-medium border-r">Monto</th>
              <th className="p-2 text-left font-medium border-r">Documento</th>
              <th className="p-2 text-left font-medium">Crédito</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row._rowIndex}
                className={row._hasErrors ? 'bg-red-50' : 'bg-white hover:bg-gray-50'}
              >
                <td className="p-2 border-r text-center">{row._rowIndex}</td>
                <td className="p-2 border-r">
                  <input
                    type="text"
                    value={row.cedula}
                    onChange={(e) => onUpdateCell(row, 'cedula', e.target.value)}
                    className={`w-full p-1 border rounded ${
                      row._validation.cedula?.isValid === false ? 'border-red-500 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="V12345678"
                  />
                </td>
                <td className="p-2 border-r">
                  <input
                    type="text"
                    value={row.fecha_pago}
                    onChange={(e) => onUpdateCell(row, 'fecha_pago', e.target.value)}
                    className={`w-full p-1 border rounded ${
                      row._validation.fecha_pago?.isValid === false ? 'border-red-500 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="DD/MM/YYYY"
                  />
                </td>
                <td className="p-2 border-r">
                  <input
                    type="number"
                    value={row.monto_pagado || ''}
                    onChange={(e) => onUpdateCell(row, 'monto_pagado', e.target.value)}
                    className={`w-full p-1 border rounded ${
                      row._validation.monto_pagado?.isValid === false ? 'border-red-500 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="0.00"
                  />
                </td>
                <td className="p-2 border-r">
                  <input
                    type="text"
                    value={row.numero_documento}
                    onChange={(e) => onUpdateCell(row, 'numero_documento', e.target.value)}
                    className={`w-full p-1 border rounded ${
                      row._validation.numero_documento?.isValid === false ? 'border-red-500 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="VE/xxx"
                  />
                </td>
                <td className="p-2">
                  <input type="text" value={row.prestamo_id || ''} className="w-full p-1 border border-gray-300 rounded" placeholder="--" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Estado */}
      {rows.filter((r) => r._hasErrors).length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-4 text-sm text-red-800">
          <strong>⚠️ {rows.filter((r) => r._hasErrors).length} fila(s) con errores</strong>
          <p className="mt-2">Corrígelas antes de guardar</p>
        </div>
      )}
    </div>
  )
}
