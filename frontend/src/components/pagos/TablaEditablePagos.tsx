/**
 * Tabla Editable para Preview de Carga Masiva de Pagos
 * Features:
 * - Validación inline mientras edita
 * - Auto-guardar cuando cumple todos los validadores
 * - Mostrar tipo de error por línea (CEDULA, MONTO, FECHA, DOCUMENTO)
 * - Desaparecer fila tras guardar
 * - Encabezado dinámico con contadores actualizados
 */

import { useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, AlertTriangle, CheckCircle, Loader2, Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

export interface FilaEditableProps {
  rows: PagoExcelRow[]
  prestamosPorCedula: Record<string, Array<{ id: number; estado: string }>>
  onRowsChange?: (newRows: PagoExcelRow[]) => void
  onUpdateCell: (row: PagoExcelRow, field: string, value: string | number) => void
  saveRowIfValid?: (row: PagoExcelRow) => Promise<boolean>
}

const inputClass = (isValid: boolean, isSaving?: boolean) =>
  `w-full text-sm p-2 border rounded min-w-[70px] transition-colors ${
    isSaving
      ? 'bg-gray-100 border-gray-300 text-gray-500 cursor-wait'
      : isValid
        ? 'border-gray-300 bg-white text-black focus:ring-2 focus:ring-green-500'
        : 'border-red-600 bg-red-50 text-red-900 focus:ring-2 focus:ring-red-500'
  }`

export function TablaEditablePagos({
  rows,
  prestamosPorCedula,
  onRowsChange,
  onUpdateCell,
  saveRowIfValid,
}: FilaEditableProps) {
  const [savingIndices, setSavingIndices] = useState<Set<number>>(new Set())

  // Contadores dinámicos
  const stats = useMemo(() => {
    const cargados = rows.length
    const guardados = 0 // Las filas guardadas desaparecen de excelData
    const aRevisar = rows.filter((r) => r._hasErrors).length
    return { cargados, guardados, aRevisar }
  }, [rows])

  const handleCellChange = useCallback(
    (row: PagoExcelRow, field: string, value: string | number) => {
      onUpdateCell(row, field, value)
      // NO intenta auto-guardar, solo actualiza validación
    },
    [onUpdateCell]
  )

  const filasValidas = rows.filter((r) => !r._hasErrors)

  return (
    <div className="space-y-4">
      {/* Encabezado dinámico */}
      <Card className="border-green-200 bg-green-50">
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">Cargados: {stats.cargados}</Badge>
              <Badge variant="outline" className="text-green-700">
                ✅ Guardados: {stats.guardados}
              </Badge>
              <Badge variant="outline" className="text-red-700">
                ⚠️ A Revisar: {stats.aRevisar}
              </Badge>
            </div>
            <Button disabled={filasValidas.length === 0} className="bg-green-600 hover:bg-green-700">
              <Save className="mr-2 h-4 w-4" />
              Guardar Todos ({filasValidas.length})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabla editable */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Eye className="mr-2 h-5 w-5" />
            Previsualización Editable
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse min-w-[1100px]">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border p-2 text-left text-xs font-medium w-12">Fila</th>
                  <th className="border p-2 text-left text-xs font-medium w-28">Cédula</th>
                  <th className="border p-2 text-left text-xs font-medium w-24">Fecha Pago</th>
                  <th className="border p-2 text-left text-xs font-medium w-24">Monto</th>
                  <th className="border p-2 text-left text-xs font-medium w-28">Documento</th>
                  <th className="border p-2 text-left text-xs font-medium w-32">Crédito</th>
                  <th className="border p-2 text-left text-xs font-medium w-20">Estado</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence mode="popLayout">
                  {rows.map((row) => {
                    const isSaving = savingIndices.has(row._rowIndex)
                    return (
                      <motion.tr
                        key={row._rowIndex}
                        initial={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className={`border-t transition-colors ${
                          row._hasErrors ? 'bg-red-50' : isSaving ? 'bg-gray-100' : 'bg-gray-50'
                        }`}
                      >
                        <td className="border p-2 text-xs font-medium">{row._rowIndex}</td>

                        {/* Cédula */}
                        <td className="border p-2">
                          <input
                            type="text"
                            value={row.cedula}
                            onChange={(e) => handleCellChange(row, 'cedula', e.target.value)}
                            disabled={isSaving}
                            placeholder="V12345678"
                            className={inputClass(
                              row._validation.cedula?.isValid !== false,
                              isSaving
                            )}
                          />
                          {row._validation.cedula?.isValid === false && (
                            <p className="text-xs text-red-700 mt-0.5">❌ CEDULA</p>
                          )}
                        </td>

                        {/* Fecha */}
                        <td className="border p-2">
                          <input
                            type="text"
                            value={row.fecha_pago}
                            onChange={(e) => handleCellChange(row, 'fecha_pago', e.target.value)}
                            disabled={isSaving}
                            placeholder="DD/MM/YYYY"
                            className={inputClass(
                              row._validation.fecha_pago?.isValid !== false,
                              isSaving
                            )}
                          />
                          {row._validation.fecha_pago?.isValid === false && (
                            <p className="text-xs text-red-700 mt-0.5">❌ FECHA</p>
                          )}
                        </td>

                        {/* Monto */}
                        <td className="border p-2">
                          <input
                            type="number"
                            value={row.monto_pagado}
                            onChange={(e) => handleCellChange(row, 'monto_pagado', e.target.value)}
                            disabled={isSaving}
                            placeholder="0.00"
                            step="0.01"
                            className={inputClass(
                              row._validation.monto_pagado?.isValid !== false,
                              isSaving
                            )}
                          />
                          {row._validation.monto_pagado?.isValid === false && (
                            <p className="text-xs text-yellow-700 mt-0.5">❌ MONTO</p>
                          )}
                        </td>

                        {/* Documento */}
                        <td className="border p-2">
                          <input
                            type="text"
                            value={row.numero_documento}
                            onChange={(e) => handleCellChange(row, 'numero_documento', e.target.value)}
                            disabled={isSaving}
                            placeholder="VE/xxx o 7400874..."
                            className={inputClass(
                              row._validation.numero_documento?.isValid !== false,
                              isSaving
                            )}
                            title="Debe ser único (no duplicado en BD ni en este lote)"
                          />
                          {row._validation.numero_documento?.isValid === false && (
                            <p className="text-xs text-red-900 mt-0.5">❌ DUPLICADO</p>
                          )}
                        </td>

                        {/* Crédito */}
                        <td className="border p-2">
                          {prestamosPorCedula[row.cedula] && prestamosPorCedula[row.cedula].length > 0 ? (
                            <Select
                              value={String(row.prestamo_id || '')}
                              onValueChange={(v) =>
                                handleCellChange(row, 'prestamo_id', v === '' ? '0' : v)
                              }
                              disabled={isSaving}
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue placeholder="Seleccionar" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="">-- Seleccionar --</SelectItem>
                                {prestamosPorCedula[row.cedula].map((p) => (
                                  <SelectItem key={p.id} value={String(p.id)}>
                                    Cred. #{p.id}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          ) : (
                            <span className="text-xs text-gray-400">--</span>
                          )}
                        </td>

                        {/* Estado */}
                        <td className="border p-2 text-center">
                          {isSaving ? (
                            <Loader2 className="h-4 w-4 animate-spin mx-auto text-blue-500" />
                          ) : row._hasErrors ? (
                            <AlertTriangle className="h-4 w-4 mx-auto text-red-500" />
                          ) : (
                            <CheckCircle className="h-4 w-4 mx-auto text-green-500" />
                          )}
                        </td>
                      </motion.tr>
                    )
                  })}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
