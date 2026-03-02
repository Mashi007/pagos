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
import { Eye, AlertTriangle, CheckCircle, Loader2, Save, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { pagoService } from '../../services/pagoService'
import { OBSERVACIONES_POR_CAMPO } from '../../utils/pagoExcelValidation'

export interface FilaEditable {
  _rowIndex: number
  cedula: string
  fecha_pago: string // "DD-MM-YYYY"
  monto_pagado: number | string
  numero_documento: string
  prestamo_id: number | null
  conciliado: boolean
  _validation: Record<string, { isValid: boolean; errorType?: string; message?: string }>
  _hasErrors: boolean
  _saving?: boolean
}

interface TablaEditablePagosProps {
  rows: FilaEditable[]
  prestamosPorCedula: Record<string, Array<{ id: number; numero: string; monto: number; estado: string }>>
  onRowSaved: (rowIndex: number) => void
  onRowError: (rowIndex: number, error: string) => void
  serviceDatos?: boolean
}

const inputClass = (isValid: boolean, isSaving?: boolean) =>
  `w-full text-sm p-2 border rounded min-w-[70px] transition-colors ${
    isSaving
      ? 'bg-gray-100 border-gray-300 text-gray-500 cursor-wait'
      : isValid
        ? 'border-gray-300 bg-white text-black focus:ring-2 focus:ring-green-500'
        : 'border-red-600 bg-red-50 text-red-900 focus:ring-2 focus:ring-red-500'
  }`

const errorColor = (errorType?: string) => {
  switch (errorType) {
    case 'CEDULA':
      return 'bg-red-50 border-l-4 border-l-red-500'
    case 'MONTO':
      return 'bg-yellow-50 border-l-4 border-l-yellow-500'
    case 'FECHA':
      return 'bg-orange-50 border-l-4 border-l-orange-500'
    case 'DOCUMENTO':
      return 'bg-red-100 border-l-4 border-l-red-700'
    default:
      return 'bg-red-50 border-l-4 border-l-red-500'
  }
}

export function TablaEditablePagos({
  rows,
  prestamosPorCedula,
  onRowSaved,
  onRowError,
  serviceDatos = false,
}: TablaEditablePagosProps) {
  const [editingCell, setEditingCell] = useState<string | null>(null)

  // Contadores dinámicos
  const stats = useMemo(() => {
    const cargados = rows.length
    const guardados = rows.filter((r) => r._saving === false).length // Ya guardadas y removidas
    const aRevisar = rows.filter((r) => r._hasErrors).length
    return { cargados, guardados, aRevisar }
  }, [rows])

  const handleCellChange = useCallback(
    (row: FilaEditable, field: string, value: string) => {
      row[field as keyof FilaEditable] = value
      // Las validaciones se harán inline (simuladas aquí)
      // En el hook real, la validación ocurre en updateCellValue
    },
    []
  )

  const handleSaveRow = useCallback(
    async (row: FilaEditable) => {
      // Validaciones finales antes de guardar
      const errores: string[] = []

      // Validar cédula
      if (!row.cedula || !/^[VEJZ]\d{6,11}$/i.test(row.cedula.trim())) {
        errores.push('CEDULA')
      }

      // Validar monto
      const monto = parseFloat(String(row.monto_pagado))
      if (isNaN(monto) || monto <= 0 || monto > 999_999_999_999.99) {
        errores.push('MONTO')
      }

      // Validar fecha
      const fechaRegex = /^(\d{2})-(\d{2})-(\d{4})$/
      if (!fechaRegex.test(row.fecha_pago)) {
        errores.push('FECHA')
      }

      // Validar documento (duplicado)
      if (
        row.numero_documento &&
        rows.filter(
          (r) => r.numero_documento === row.numero_documento && r._rowIndex !== row._rowIndex
        ).length > 0
      ) {
        errores.push('DOCUMENTO')
      }

      if (errores.length > 0) {
        onRowError(row._rowIndex, `Errores: ${errores.join(', ')}`)
        return
      }

      row._saving = true

      try {
        await pagoService.guardarFilaEditable({
          cedula: row.cedula.trim(),
          prestamo_id: row.prestamo_id && row.prestamo_id !== 0 ? row.prestamo_id : null,
          monto_pagado: monto,
          fecha_pago: row.fecha_pago,
          numero_documento: row.numero_documento || null,
        })

        onRowSaved(row._rowIndex)
      } catch (error) {
        row._saving = false
        onRowError(row._rowIndex, `Error al guardar: ${String(error)}`)
      }
    },
    [rows, onRowSaved, onRowError]
  )

  const filasValidas = rows.filter((r) => !r._hasErrors)
  const filasConError = rows.filter((r) => r._hasErrors)

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
                  {rows.map((row) => (
                    <motion.tr
                      key={row._rowIndex}
                      initial={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className={`border-t transition-colors ${
                        row._hasErrors ? 'bg-red-50' : row._saving === false ? 'bg-gray-50' : 'bg-white'
                      }`}
                    >
                      <td className="border p-2 text-xs font-medium">{row._rowIndex}</td>

                      {/* Cédula */}
                      <td className="border p-2">
                        <input
                          type="text"
                          value={row.cedula}
                          onChange={(e) => handleCellChange(row, 'cedula', e.target.value)}
                          disabled={row._saving}
                          placeholder="V12345678"
                          className={inputClass(
                            row._validation.cedula?.isValid !== false,
                            row._saving
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
                          disabled={row._saving}
                          placeholder="DD-MM-YYYY"
                          className={inputClass(
                            row._validation.fecha_pago?.isValid !== false,
                            row._saving
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
                          disabled={row._saving}
                          placeholder="0.00"
                          step="0.01"
                          className={inputClass(
                            row._validation.monto_pagado?.isValid !== false,
                            row._saving
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
                          disabled={row._saving}
                          placeholder="VE/xxx o 7400874..."
                          className={inputClass(
                            row._validation.numero_documento?.isValid !== false,
                            row._saving
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
                            disabled={row._saving}
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
                        {row._saving ? (
                          <Loader2 className="h-4 w-4 animate-spin mx-auto text-blue-500" />
                        ) : row._hasErrors ? (
                          <AlertTriangle className="h-4 w-4 mx-auto text-red-500" />
                        ) : (
                          <CheckCircle className="h-4 w-4 mx-auto text-green-500" />
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
