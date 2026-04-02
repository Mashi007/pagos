/**







 * UI para carga masiva de préstamos desde Excel.







 * Columnas: Cédula, Total financiamiento, Modalidad pago, Fecha requerimiento, Producto,







 * Concesionario, Analista, Modelo vehículo, Número cuotas, Cuota período, Tasa interés, Observaciones, Fecha aprobación / desembolso (columna M).







 */

import { motion, AnimatePresence } from 'framer-motion'

import {
  Upload,
  FileSpreadsheet,
  X,
  CheckCircle,
  Save,
  Loader2,
  Eye,
  AlertTriangle,
  Search,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Button } from '../ui/button'

import { Badge } from '../ui/badge'

import {
  useExcelUploadPrestamos,
  type ExcelUploaderPrestamosProps,
} from '../../hooks/useExcelUploadPrestamos'

const inputClass = (isValid: boolean) =>
  `w-full text-sm p-2 border rounded min-w-[70px] ${
    isValid
      ? 'border-gray-300 bg-white text-black'
      : 'border-red-600 bg-red-50 text-red-900'
  }`

export function ExcelUploaderPrestamosUI(props: ExcelUploaderPrestamosProps) {
  const {
    isDragging,

    uploadedFile,

    excelData,

    isProcessing,

    showPreview,

    toasts,

    savedRows,

    isSavingIndividual,

    savingProgress,

    serviceStatus,

    fileInputRef,

    handleDragOver,

    handleDragLeave,

    handleDrop,

    handleFileSelect,

    updateCellValue,

    setShowPreview,

    getValidRows,

    getRowsToRevisarPrestamos,

    getDisplayData,

    saveIndividualPrestamo,

    saveAllValid,

    sendToRevisarPrestamos,

    sendAllToRevisarPrestamos,

    enviadosRevisar,

    isSendingAllRevisar,

    batchProgress,

    onClose,

    navigate,
  } = useExcelUploadPrestamos(props)

  const validCount = getValidRows().length

  const errorCount = excelData.filter(r => r._hasErrors).length

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="flex max-h-[90vh] w-full max-w-[95vw] flex-col rounded-lg bg-white shadow-xl"
      >
        {/* Cabecera fija (fuera del scroll) */}

        <div className="flex-shrink-0 rounded-t-lg bg-gradient-to-r from-green-600 to-green-700 p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />

              <h2 className="text-xl font-bold">CARGA MASIVA DE PRÉSTAMOS</h2>

              <div
                className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs ${
                  serviceStatus === 'online'
                    ? 'bg-green-100 text-green-800'
                    : serviceStatus === 'offline'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                <div
                  className={`h-2 w-2 rounded-full ${serviceStatus === 'online' ? 'bg-green-500' : serviceStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'}`}
                />

                {serviceStatus === 'online'
                  ? 'Online'
                  : serviceStatus === 'offline'
                    ? 'Offline'
                    : 'Verificando...'}
              </div>
            </div>

            <Button
              onClick={onClose}
              variant="ghost"
              size="sm"
              className="p-2 text-white hover:bg-white/20"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Contenido con scroll */}

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-6">
          {excelData.length === 0 &&
          enviadosRevisar.size === 0 &&
          savedRows.size === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <div
                  className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                    isDragging
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload className="mx-auto mb-4 h-12 w-12 text-gray-400" />

                  <h3 className="mb-2 text-lg font-semibold">
                    {isDragging
                      ? 'Suelta el archivo aquí'
                      : 'Sube tu archivo Excel'}
                  </h3>

                  <p className="mb-4 text-sm text-gray-600">
                    Columnas: Cédula | Total financiamiento | Modalidad pago |
                    Fecha requerimiento | Producto | Concesionario | Analista |
                    Modelo | Nº cuotas | Cuota período | Tasa interés |
                    Observaciones
                  </p>

                  <p className="mb-4 text-sm text-amber-900">
                    La cédula de cada fila debe existir como cliente con la
                    misma cédula en ficha: el préstamo se guarda con la cédula
                    del cliente. Filas sin cédula en cliente serán rechazadas.
                  </p>

                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isProcessing}
                    className="mb-4"
                  >
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    Seleccionar archivo
                  </Button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileSelect}
                    className="hidden"
                  />

                  {isProcessing && (
                    <div className="mt-4">
                      <Loader2 className="mx-auto h-8 w-8 animate-spin text-green-600" />

                      <p className="mt-2 text-sm text-gray-600">
                        Procesando archivo...
                      </p>
                    </div>
                  )}

                  {uploadedFile && (
                    <div className="mt-4 rounded-lg bg-green-50 p-3">
                      <FileSpreadsheet className="mr-2 inline h-5 w-5 text-green-600" />

                      <span className="text-sm font-medium text-green-800">
                        {uploadedFile.name}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : null}

          {/* RESUMEN FINAL: excelData vacío pero filas ya procesadas */}

          {excelData.length === 0 &&
            (enviadosRevisar.size > 0 || savedRows.size > 0) && (
              <Card className="border-green-300 bg-green-50">
                <CardContent className="space-y-4 pb-8 pt-8 text-center">
                  <CheckCircle className="mx-auto h-16 w-16 text-green-500" />

                  <h3 className="text-xl font-bold text-green-800">
                    ¡Procesamiento completado!
                  </h3>

                  <div className="mt-2 flex justify-center gap-6 text-sm">
                    {savedRows.size > 0 && (
                      <span className="rounded-full bg-green-100 px-4 py-2 font-semibold text-green-800">
                        ✓ {savedRows.size} guardado(s)
                      </span>
                    )}

                    {enviadosRevisar.size > 0 && (
                      <span className="rounded-full bg-amber-100 px-4 py-2 font-semibold text-amber-800">
                        ⚠ {enviadosRevisar.size} enviado(s) a Revisar Préstamos
                      </span>
                    )}
                  </div>

                  <div className="flex justify-center gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        navigate('/prestamos?revisar=1')
                        onClose()
                      }}
                      className="border-amber-300 bg-amber-50 text-amber-800"
                    >
                      <Search className="mr-2 h-4 w-4" />
                      Ver Revisar Préstamos
                    </Button>

                    <Button
                      variant="outline"
                      onClick={onClose}
                      className="border-gray-300"
                    >
                      <X className="mr-2 h-4 w-4" />
                      Cerrar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

          {/* Tabla, progreso y estadísticas cuando hay datos (mismo orden que Pagos) */}

          {excelData.length > 0 && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>

                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[1200px] border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="w-12 border p-2 text-left text-xs font-medium">
                            Fila
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Cédula
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Total $
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Modalidad
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Fecha req.
                          </th>

                          <th className="w-28 border p-2 text-left text-xs font-medium">
                            Fecha aprob.
                          </th>

                          <th className="w-28 border p-2 text-left text-xs font-medium">
                            Producto
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Concesionario
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium">
                            Analista
                          </th>

                          <th className="w-28 border p-2 text-left text-xs font-medium">
                            Modelo vehículo
                          </th>

                          <th className="w-16 border p-2 text-left text-xs font-medium">
                            Cuotas
                          </th>

                          <th className="w-20 border p-2 text-left text-xs font-medium">
                            Acción
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {getDisplayData().map(row => (
                          <tr
                            key={row._rowIndex}
                            className={
                              row._hasErrors ? 'bg-red-50' : 'bg-green-50'
                            }
                          >
                            <td className="border p-2 text-xs">
                              {row._rowIndex}
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.cedula}
                                onChange={e =>
                                  updateCellValue(row, 'cedula', e.target.value)
                                }
                                className={inputClass(
                                  row._validation.cedula?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="number"
                                value={row.total_financiamiento || ''}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'total_financiamiento',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.total_financiamiento
                                    ?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <select
                                value={row.modalidad_pago}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'modalidad_pago',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.modalidad_pago?.isValid ??
                                    true
                                )}
                              >
                                <option value="MENSUAL">MENSUAL</option>

                                <option value="QUINCENAL">QUINCENAL</option>

                                <option value="SEMANAL">SEMANAL</option>
                              </select>
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.fecha_requerimiento}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'fecha_requerimiento',
                                    e.target.value
                                  )
                                }
                                placeholder="DD/MM/YYYY"
                                className={inputClass(
                                  row._validation.fecha_requerimiento
                                    ?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.fecha_aprobacion}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'fecha_aprobacion',
                                    e.target.value
                                  )
                                }
                                placeholder="DD/MM/YYYY"
                                className={inputClass(
                                  row._validation.fecha_aprobacion?.isValid ??
                                    true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.producto}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'producto',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.producto?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.concesionario}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'concesionario',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.concesionario?.isValid ?? true
                                )}
                                placeholder="Concesionario"
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.analista}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'analista',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.analista?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.modelo_vehiculo}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'modelo_vehiculo',
                                    e.target.value
                                  )
                                }
                                className={inputClass(
                                  row._validation.modelo_vehiculo?.isValid ??
                                    true
                                )}
                                placeholder="Modelo vehículo"
                              />
                            </td>

                            <td className="border p-2">
                              <input
                                type="number"
                                value={row.numero_cuotas || ''}
                                onChange={e =>
                                  updateCellValue(
                                    row,
                                    'numero_cuotas',
                                    e.target.value
                                  )
                                }
                                min={1}
                                max={12}
                                className={inputClass(
                                  row._validation.numero_cuotas?.isValid ?? true
                                )}
                              />
                            </td>

                            <td className="border p-2">
                              <div className="flex flex-wrap items-center gap-1">
                                {savedRows.has(row._rowIndex) ? (
                                  <div className="flex items-center text-sm text-green-600">
                                    <CheckCircle className="mr-1 h-4 w-4" />
                                    Guardado
                                  </div>
                                ) : !row._hasErrors ? (
                                  <Button
                                    size="sm"
                                    onClick={() => saveIndividualPrestamo(row)}
                                    disabled={
                                      savingProgress[row._rowIndex] ||
                                      serviceStatus === 'offline'
                                    }
                                    className="bg-green-600 text-xs text-white hover:bg-green-700"
                                  >
                                    {savingProgress[row._rowIndex] ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      <>
                                        <Save className="mr-1 h-3 w-3" />
                                        Guardar
                                      </>
                                    )}
                                  </Button>
                                ) : (
                                  <span className="flex items-center text-xs text-red-600">
                                    <AlertTriangle className="mr-1 h-4 w-4" />
                                    Corregir
                                  </span>
                                )}

                                {!savedRows.has(row._rowIndex) && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => sendToRevisarPrestamos(row)}
                                    disabled={
                                      savingProgress[row._rowIndex] ||
                                      serviceStatus === 'offline'
                                    }
                                    className="border-amber-400 text-xs text-amber-700 hover:bg-amber-50"
                                    title="Enviar a Revisar Préstamos"
                                  >
                                    {savingProgress[row._rowIndex] ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      <>
                                        <Search className="mr-1 h-3 w-3" />
                                        Revisar
                                      </>
                                    )}
                                  </Button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {batchProgress && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                  <div className="mb-1 flex items-center justify-between text-sm font-medium text-blue-800">
                    <span>Enviando a Revisar Préstamos...</span>

                    <span>
                      {batchProgress.sent} / {batchProgress.total}
                    </span>
                  </div>

                  <div className="h-2 w-full rounded-full bg-blue-200">
                    <div
                      className="h-2 rounded-full bg-blue-600 transition-all duration-200"
                      style={{
                        width: `${Math.round((batchProgress.sent / batchProgress.total) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              )}

              <Card className="border-green-200 bg-green-50">
                <CardContent className="pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">Total: {excelData.length}</Badge>

                      <Badge variant="outline" className="text-green-700">
                        Válidos: {validCount}
                      </Badge>

                      <Badge variant="outline">
                        Guardados: {savedRows.size}
                      </Badge>

                      {enviadosRevisar.size > 0 && (
                        <Badge
                          variant="outline"
                          className="border-amber-300 text-amber-700"
                        >
                          {enviadosRevisar.size} a Revisar Préstamos
                        </Badge>
                      )}

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowPreview(false)}
                      >
                        <X className="mr-2 h-4 w-4" />
                        Cambiar archivo
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigate('/prestamos')
                          onClose()
                        }}
                        className="border-green-300 bg-green-50"
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ir a Préstamos
                      </Button>

                      {getRowsToRevisarPrestamos().length > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => sendAllToRevisarPrestamos()}
                          disabled={
                            isSendingAllRevisar || serviceStatus === 'offline'
                          }
                          className="border-amber-400 bg-amber-100 text-amber-800 hover:bg-amber-200"
                          title="Enviar todas las filas pendientes a Revisar Préstamos"
                        >
                          {isSendingAllRevisar ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Enviando...
                            </>
                          ) : (
                            <>
                              <Search className="mr-2 h-4 w-4" />
                              ENVIAR REVISAR PRÉSTAMOS (
                              {getRowsToRevisarPrestamos().length})
                            </>
                          )}
                        </Button>
                      )}
                    </div>

                    <Button
                      onClick={saveAllValid}
                      disabled={
                        validCount === 0 ||
                        isSavingIndividual ||
                        serviceStatus === 'offline'
                      }
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {isSavingIndividual ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2 h-4 w-4" />
                          Guardar Todos ({validCount})
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </motion.div>

      <div className="fixed right-4 top-4 z-[60] space-y-2">
        <AnimatePresence>
          {toasts.map(t => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              className={`max-w-sm rounded-lg border-l-4 p-4 shadow-lg ${
                t.type === 'error'
                  ? 'border-red-500 bg-red-50 text-red-800'
                  : t.type === 'warning'
                    ? 'border-yellow-500 bg-yellow-50 text-yellow-800'
                    : 'border-green-500 bg-green-50 text-green-800'
              }`}
            >
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
