/**
 * UI para carga masiva de pagos desde Excel.
 * Columnas: Cédula, Fecha de pago, Monto, Documento, ID Préstamo (opcional).
 * Solo créditos activos (APROBADO, DESEMBOLSADO) en el selector.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileSpreadsheet, X, CheckCircle, Save, Loader2, Eye, AlertTriangle, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { useExcelUploadPagos, type ExcelUploaderPagosProps } from '../../hooks/useExcelUploadPagos'
import { useNavigate } from 'react-router-dom'

const inputClass = (isValid: boolean) =>
  `w-full text-sm p-2 border rounded min-w-[70px] ${
    isValid ? 'border-gray-300 bg-white text-black' : 'border-red-600 bg-red-50 text-red-900'
  }`

export function ExcelUploaderPagosUI(props: ExcelUploaderPagosProps) {
  const navigate = useNavigate()
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
    prestamosPorCedula,
    cedulasBuscando,
    fetchSingleCedula,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileSelect,
    updateCellValue,
    setShowPreview,
    getValidRows,
    saveIndividualPago,
    saveAllValid,
    sendToRevisarPagos,
    enviadosRevisar,
    duplicadosPendientesRevisar,
    onClose,
    removeToast,
  } = useExcelUploadPagos(props)

  const validCount = getValidRows().length

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl max-w-[95vw] w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="bg-gradient-to-r from-green-600 to-green-700 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />
              <h2 className="text-xl font-bold">CARGA MASIVA DE PAGOS</h2>
              <div
                className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 ${
                  serviceStatus === 'online' ? 'bg-green-100 text-green-800' : serviceStatus === 'offline' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${serviceStatus === 'online' ? 'bg-green-500' : serviceStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                {serviceStatus === 'online' ? 'Online' : serviceStatus === 'offline' ? 'Offline' : 'Verificando...'}
              </div>
            </div>
            <Button onClick={onClose} variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2">
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {!showPreview ? (
            <Card>
              <CardContent className="pt-6">
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragging ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-lg font-semibold mb-2">{isDragging ? 'Suelta el archivo aquí' : 'Sube tu archivo Excel'}</h3>
                  <p className="text-gray-600 mb-4 text-sm">
                    Columnas: Cédula | Fecha de pago | Monto | Documento | ID Préstamo (opcional) | Conciliación (Sí/No)
                  </p>
                  <Button onClick={() => fileInputRef.current?.click()} disabled={isProcessing} className="mb-4">
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    Seleccionar archivo
                  </Button>
                  <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleFileSelect} className="hidden" />
                  {isProcessing && (
                    <div className="mt-4">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto text-green-600" />
                      <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                    </div>
                  )}
                  {uploadedFile && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <FileSpreadsheet className="h-5 w-5 text-green-600 inline mr-2" />
                      <span className="text-sm font-medium text-green-800">{uploadedFile.name}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <Card className="border-green-200 bg-green-50">
                <CardContent className="pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline">Total: {excelData.length}</Badge>
                      <Badge variant="outline" className="text-green-700">Válidos: {validCount}</Badge>
                      <Badge variant="outline">Guardados: {savedRows.size}</Badge>
                      {duplicadosPendientesRevisar.size > 0 && (
                        <Badge variant="outline" className="text-amber-700 border-amber-300">
                          Duplicados: {duplicadosPendientesRevisar.size}
                        </Badge>
                      )}
                      <Button variant="outline" size="sm" onClick={() => setShowPreview(false)}>
                        <X className="mr-2 h-4 w-4" />
                        Cambiar archivo
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => navigate('/pagos')} className="bg-green-50 border-green-300">
                        <Eye className="mr-2 h-4 w-4" />
                        Ir a Pagos
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          onClose()
                          navigate('/pagos?revisar=1')
                        }}
                        className="bg-amber-50 border-amber-300"
                        title="Ver pagos sin crédito asignado"
                      >
                        <Search className="mr-2 h-4 w-4" />
                        Revisar Pagos
                      </Button>
                    </div>
                    <Button
                      onClick={saveAllValid}
                      disabled={validCount === 0 || isSavingIndividual || serviceStatus === 'offline'}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {isSavingIndividual ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
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

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse min-w-[980px]">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border p-2 text-left text-xs font-medium w-12">Fila</th>
                          <th className="border p-2 text-left text-xs font-medium w-24">Cédula</th>
                          <th className="border p-2 text-left text-xs font-medium w-24">Fecha pago</th>
                          <th className="border p-2 text-left text-xs font-medium w-24">Monto</th>
                          <th className="border p-2 text-left text-xs font-medium w-28">Documento</th>
                          <th className="border p-2 text-left text-xs font-medium w-32">Crédito</th>
                          <th className="border p-2 text-left text-xs font-medium w-24">Conciliación</th>
                          <th className="border p-2 text-left text-xs font-medium w-20">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelData
                          .filter((row) => !enviadosRevisar.has(row._rowIndex) && !savedRows.has(row._rowIndex))
                          .map((row) => {
                          const cedulaNorm = (row.cedula || '').trim()
                          const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
                          const prestamosActivos =
                            prestamosPorCedula[cedulaNorm] ||
                            prestamosPorCedula[cedulaSinGuion] ||
                            []
                          const tieneCreditos = prestamosActivos.length >= 1
                          const valorCredito =
                            row.prestamo_id != null
                              ? String(row.prestamo_id)
                              : prestamosActivos.length === 1
                                ? String(prestamosActivos[0].id)
                                : 'none'
                          return (
                            <tr key={row._rowIndex} className={row._hasErrors ? 'bg-red-50' : 'bg-green-50'}>
                              <td className="border p-2 text-xs">{row._rowIndex}</td>
                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.cedula}
                                  onChange={(e) => updateCellValue(row, 'cedula', e.target.value)}
                                  onBlur={() => {
                                    const c = (row.cedula || '').trim()
                                    if (c.length >= 5) fetchSingleCedula(c)
                                  }}
                                  placeholder="Ej: V22546175"
                                  className={inputClass(row._validation.cedula?.isValid ?? true)}
                                />
                              </td>
                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.fecha_pago}
                                  onChange={(e) => updateCellValue(row, 'fecha_pago', e.target.value)}
                                  placeholder="DD/MM/YYYY"
                                  className={inputClass(row._validation.fecha_pago?.isValid ?? true)}
                                />
                              </td>
                              <td className="border p-2">
                                <input
                                  type="number"
                                  value={row.monto_pagado || ''}
                                  onChange={(e) => updateCellValue(row, 'monto_pagado', e.target.value)}
                                  className={inputClass(row._validation.monto_pagado?.isValid ?? true)}
                                />
                              </td>
                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.numero_documento}
                                  onChange={(e) => updateCellValue(row, 'numero_documento', e.target.value)}
                                  className={inputClass(row._validation.numero_documento?.isValid ?? true)}
                                  placeholder="Nº documento"
                                />
                              </td>
                              <td className="border p-2">
                                {tieneCreditos ? (
                                  <Select
                                    value={valorCredito}
                                    onValueChange={(v) => updateCellValue(row, 'prestamo_id', v)}
                                  >
                                    <SelectTrigger className="h-8 text-xs">
                                      <SelectValue placeholder="Seleccionar crédito" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="none">— Seleccionar —</SelectItem>
                                      {prestamosActivos.map((p) => (
                                        <SelectItem key={p.id} value={String(p.id)}>
                                          Crédito #{p.id}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                ) : (
                                  <div className="flex items-center gap-1">
                                    {cedulaNorm && cedulasBuscando.has(cedulaNorm) ? (
                                      <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                                    ) : cedulaNorm && cedulaNorm.length >= 5 ? (
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs px-2"
                                        onClick={() => fetchSingleCedula(cedulaNorm)}
                                        disabled={serviceStatus === 'offline'}
                                      >
                                        <Search className="h-3 w-3 mr-1" />
                                        Buscar
                                      </Button>
                                    ) : null}
                                    {(!cedulaNorm || cedulaNorm.length < 5) && (
                                      <span className="text-xs text-gray-400">—</span>
                                    )}
                                  </div>
                                )}
                              </td>
                              <td className="border p-2">
                                <Select
                                  value={row.conciliado ? 'si' : 'no'}
                                  onValueChange={(v) => updateCellValue(row, 'conciliado', v)}
                                >
                                  <SelectTrigger className="h-8 text-xs">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="no">No</SelectItem>
                                    <SelectItem value="si">Sí</SelectItem>
                                  </SelectContent>
                                </Select>
                              </td>
                              <td className="border p-2">
                                {savedRows.has(row._rowIndex) ? (
                                  <div className="flex items-center text-green-600 text-sm">
                                    <CheckCircle className="h-4 w-4 mr-1" />
                                    Guardado
                                  </div>
                                ) : duplicadosPendientesRevisar.has(row._rowIndex) ? (
                                  <div className="flex flex-col gap-1">
                                    <span className="text-xs text-amber-700 flex items-center">
                                      <AlertTriangle className="h-4 w-4 mr-1" />
                                      Documento duplicado
                                    </span>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        sendToRevisarPagos(row, () => navigate('/pagos?revisar=1'))
                                      }
                                      disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
                                      className="text-amber-700 border-amber-300 hover:bg-amber-50 text-xs"
                                      title="Enviar a Revisar Pagos para confirmar uno a uno"
                                    >
                                      {savingProgress[row._rowIndex] ? (
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                      ) : (
                                        <>
                                          <Search className="h-3 w-3 mr-1" />
                                          Revisar Pagos
                                        </>
                                      )}
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => saveIndividualPago(row)}
                                      disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
                                      className="text-gray-600 text-xs"
                                      title="Cambie el documento o intente guardar de nuevo"
                                    >
                                      <Save className="h-3 w-3 mr-1" />
                                      Guardar de nuevo
                                    </Button>
                                  </div>
                                ) : !row._hasErrors ? (
                                  <div className="flex flex-col gap-1">
                                    <Button
                                      size="sm"
                                      onClick={() => saveIndividualPago(row)}
                                      disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
                                      className="bg-green-600 hover:bg-green-700 text-white text-xs"
                                    >
                                      {savingProgress[row._rowIndex] ? (
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                      ) : (
                                        <>
                                          <Save className="h-3 w-3 mr-1" />
                                          Guardar
                                        </>
                                      )}
                                    </Button>
                                    {(!tieneCreditos || prestamosActivos.length > 1) && (
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() =>
                                          sendToRevisarPagos(row, () => navigate('/pagos?revisar=1'))
                                        }
                                        disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
                                        className="text-amber-700 border-amber-300 hover:bg-amber-50 text-xs"
                                        title={
                                          prestamosActivos.length > 1
                                            ? 'Enviar a Revisar Pagos para asignar el crédito correcto'
                                            : 'Enviar a Revisar Pagos'
                                        }
                                      >
                                        {savingProgress[row._rowIndex] ? (
                                          <Loader2 className="h-3 w-3 animate-spin" />
                                        ) : (
                                          <>
                                            <Search className="h-3 w-3 mr-1" />
                                            Revisar Pagos
                                          </>
                                        )}
                                      </Button>
                                    )}
                                  </div>
                                ) : (
                                  <div className="flex flex-col gap-1">
                                    <span className="text-xs text-red-600 flex items-center">
                                      <AlertTriangle className="h-4 w-4 mr-1" />
                                      Corregir
                                    </span>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        sendToRevisarPagos(row, () => navigate('/pagos?revisar=1'))
                                      }
                                      disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
                                      className="text-amber-700 border-amber-300 hover:bg-amber-50 text-xs"
                                    >
                                      {savingProgress[row._rowIndex] ? (
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                      ) : (
                                        <>
                                          <Search className="h-3 w-3 mr-1" />
                                          Revisar Pagos
                                        </>
                                      )}
                                    </Button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </motion.div>

      <div className="fixed top-4 right-4 z-[60] space-y-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              className={`max-w-sm p-4 rounded-lg shadow-lg border-l-4 flex items-center justify-between gap-2 ${
                t.type === 'error' ? 'bg-red-50 border-red-500 text-red-800' : t.type === 'warning' ? 'bg-yellow-50 border-yellow-500 text-yellow-800' : 'bg-green-50 border-green-500 text-green-800'
              }`}
            >
              <span className="flex-1">{t.message}</span>
              <button
                type="button"
                onClick={() => removeToast(t.id)}
                className="flex-shrink-0 p-1 rounded hover:bg-black/10 opacity-70 hover:opacity-100"
                aria-label="Cerrar"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
