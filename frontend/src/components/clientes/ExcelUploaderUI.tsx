/**
 * Pure UI for Excel client bulk upload.
 * Uses useExcelUpload hook for all logic.
 */

import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  FileSpreadsheet,
  X,
  CheckCircle,
  AlertTriangle,
  Eye,
  Save,
  Info,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { useExcelUpload, type ExcelUploaderProps } from '../../hooks/useExcelUpload'

export function ExcelUploaderUI(props: ExcelUploaderProps) {
  const {
    isDragging,
    uploadedFile,
    isProcessing,
    showPreview,
    showValidationModal,
    setShowValidationModal,
    toasts,
    savedClients,
    isSavingIndividual,
    savingProgress,
    serviceStatus,
    showOnlyPending,
    setShowOnlyPending,
    showModalCedulasExistentes,
    cedulasExistentesEnBD,
    cancelCedulasModal,
    opcionesEstado,
    validRows,
    totalRows,
    fileInputRef,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileSelect,
    updateCellValue,
    setShowPreview,
    removeToast,
    getValidClients,
    getDisplayData,
    getSavedClientsCount,
    getDuplicadoMotivo,
    isClientValid,
    cedulasDuplicadasEnArchivo,
    nombresDuplicadosEnArchivo,
    emailDuplicadosEnArchivo,
    telefonoDuplicadosEnArchivo,
    saveIndividualClient,
    saveAllValidClients,
    confirmSaveOmittingExistingCedulas,
    onClose,
    navigate,
  } = useExcelUpload(props)

  const hasDuplicates =
    cedulasDuplicadasEnArchivo.size > 0 ||
    nombresDuplicadosEnArchivo.size > 0 ||
    emailDuplicadosEnArchivo.size > 0 ||
    telefonoDuplicadosEnArchivo.size > 0

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
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />
              <h2 className="text-xl font-bold">CARGA MASIVA DE CLIENTES</h2>
              <div
                className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 ${
                  serviceStatus === 'online'
                    ? 'bg-green-100 text-green-800'
                    : serviceStatus === 'offline'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    serviceStatus === 'online'
                      ? 'bg-green-500'
                      : serviceStatus === 'offline'
                        ? 'bg-red-500'
                        : 'bg-yellow-500'
                  }`}
                />
                {serviceStatus === 'online'
                  ? 'Online'
                  : serviceStatus === 'offline'
                    ? 'Offline'
                    : 'Verificando...'}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                onClick={onClose}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white/20 p-2"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
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
                  <h3 className="text-lg font-semibold mb-2">
                    {isDragging ? 'Suelta el archivo aquí' : 'Sube tu archivo Excel'}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Arrastra y suelta tu archivo Excel o haz clic para seleccionar
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
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto" />
                      <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                    </div>
                  )}

                  {uploadedFile && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <FileSpreadsheet className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-800">{uploadedFile.name}</span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Stats */}
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <Badge variant="outline" className="text-blue-700">
                        Total: {totalRows} filas
                      </Badge>
                      <Badge variant="outline" className="text-green-700">
                        Válidos: {getValidClients().length}
                      </Badge>
                      <Badge variant="outline" className="text-blue-700">
                        Guardados: {getSavedClientsCount()}
                      </Badge>
                      <Badge variant="outline" className="text-red-700">
                        Con errores:{' '}
                        {totalRows - getValidClients().length - getSavedClientsCount()}
                      </Badge>
                      {hasDuplicates && (
                        <Badge
                          variant="outline"
                          className="text-red-800 bg-red-100 border-red-400"
                        >
                          Regla estricta: NO DUPLICADOS (cédula, nombres, email, tel). Corrija las
                          filas marcadas para poder guardarlas.
                        </Badge>
                      )}
                      {getSavedClientsCount() > 0 && (
                        <Badge variant="outline" className="text-green-700 bg-green-50">
                          {getSavedClientsCount()} en Dashboard
                        </Badge>
                      )}
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="showOnlyPending"
                          checked={showOnlyPending}
                          onChange={(e) => setShowOnlyPending(e.target.checked)}
                          className="rounded"
                        />
                        <label htmlFor="showOnlyPending" className="text-sm text-gray-600">
                          Solo pendientes
                        </label>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button onClick={() => setShowPreview(false)} variant="outline" size="sm">
                        <X className="mr-2 h-4 w-4" />
                        Cambiar archivo
                      </Button>
                      {getSavedClientsCount() > 0 && (
                        <Button
                          onClick={() => navigate('/clientes')}
                          variant="outline"
                          size="sm"
                          className="bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100 font-semibold"
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          Ir al Dashboard de Clientes
                        </Button>
                      )}
                      <Button
                        onClick={saveAllValidClients}
                        disabled={
                          getValidClients().length === 0 ||
                          isSavingIndividual ||
                          serviceStatus === 'offline'
                        }
                        className="bg-green-600 hover:bg-green-700 disabled:opacity-50"
                      >
                        {isSavingIndividual ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                            Guardando...
                          </>
                        ) : (
                          <>
                            <Save className="mr-2 h-4 w-4" />
                            Guardar Todos ({getValidClients().length})
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Validation modal */}
              <AnimatePresence>
                {showValidationModal && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                  >
                    <motion.div
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.9, opacity: 0 }}
                      className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-y-auto"
                    >
                      <div className="p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h2 className="text-2xl font-bold text-red-600 flex items-center">
                            <AlertTriangle className="mr-2 h-6 w-6" />
                            Errores de Validación Encontrados
                          </h2>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowValidationModal(false)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-700">
                            <strong>No se puede guardar:</strong> Se encontraron{' '}
                            {totalRows - validRows} registros con errores que deben corregirse antes
                            de continuar.
                          </p>
                          <p className="text-sm text-red-600 mt-1">
                            <strong>Errores incluyen:</strong> Campos de validación inválidos.
                          </p>
                        </div>

                        <div className="space-y-4 max-h-[50vh] overflow-y-auto">
                          {getDisplayData()
                            .filter((row) => row._hasErrors)
                            .map((row, index) => (
                              <div
                                key={index}
                                className="border border-red-200 rounded-lg p-4 bg-red-50"
                              >
                                <div className="flex items-center justify-between mb-3">
                                  <h3 className="font-semibold text-red-800">
                                    Fila {row._rowIndex}: {row.nombres}
                                  </h3>
                                  <Badge
                                    variant="outline"
                                    className="text-red-600 border-red-300"
                                  >
                                    {Object.keys(row._validation).filter(
                                      (f) => !row._validation[f]?.isValid
                                    ).length}{' '}
                                    errores
                                  </Badge>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                  {Object.entries(row._validation).map(([field, validation]) => {
                                    const v = validation as { isValid?: boolean; message?: string }
                                    if (v?.isValid) return null
                                    return (
                                      <div key={field} className="flex items-start space-x-2">
                                        <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0" />
                                        <div className="flex-1">
                                          <span className="text-sm font-medium text-gray-700 capitalize">
                                            {field}:
                                          </span>
                                          <div className="text-sm text-red-600 mt-1">
                                            {v?.message}
                                          </div>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            ))}
                        </div>

                        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-start space-x-2">
                            <AlertTriangle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div className="text-sm text-blue-800">
                              <strong>Instrucciones para corregir:</strong>
                              <ul className="mt-2 ml-4 list-disc space-y-1">
                                <li>
                                  Los campos con fondo rojo en la tabla tienen errores de validación
                                </li>
                                <li>Haz clic en cualquier campo para editarlo directamente</li>
                                <li>
                                  Los errores se corrigen automáticamente al escribir valores
                                  válidos
                                </li>
                                <li>
                                  Una vez corregidos todos los errores, podrás guardar los datos
                                </li>
                              </ul>
                            </div>
                          </div>
                        </div>

                        <div className="mt-6 flex justify-end space-x-3">
                          <Button variant="outline" onClick={() => setShowValidationModal(false)}>
                            Cerrar
                          </Button>
                          <Button
                            onClick={() => {
                              setShowValidationModal(false)
                              const tableElement = document.querySelector('.overflow-x-auto')
                              if (tableElement) {
                                tableElement.scrollIntoView({ behavior: 'smooth' })
                              }
                            }}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            Ir a Corregir Errores
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Cedulas existentes modal */}
              <AnimatePresence>
                {showModalCedulasExistentes && cedulasExistentesEnBD.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                  >
                    <motion.div
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.9, opacity: 0 }}
                      className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6"
                    >
                      <div className="flex items-center gap-2 mb-4">
                        <AlertTriangle className="h-6 w-6 text-amber-600 flex-shrink-0" />
                        <h2 className="text-xl font-bold text-gray-800">
                          Cédulas ya registradas
                        </h2>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">
                        Las siguientes cédulas ya existen en el sistema. Si continúa, esas filas se
                        omitirán y solo se guardarán el resto.
                      </p>
                      <ul className="mb-4 max-h-40 overflow-y-auto rounded border border-gray-200 bg-gray-50 p-2 text-sm font-mono">
                        {cedulasExistentesEnBD.map((ced, idx) => (
                          <li key={idx} className="py-0.5">
                            {ced}
                          </li>
                        ))}
                      </ul>
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={cancelCedulasModal}>
                          Cancelar
                        </Button>
                        <Button
                          className="bg-green-600 hover:bg-green-700"
                          onClick={confirmSaveOmittingExistingCedulas}
                        >
                          Sí, guardar el resto
                        </Button>
                      </div>
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Preview table */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div
                    className="overflow-x-auto min-w-full relative"
                    style={{ resize: 'both', minWidth: '800px', minHeight: '400px' }}
                  >
                    <table className="w-full border-collapse min-w-[1400px]">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-16">
                            Fila
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">
                            Cédula
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">
                            Nombres y Apellidos
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-28">
                            Teléfono
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">
                            Email
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">
                            Dirección
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">
                            Fecha Nac.
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">
                            Ocupación
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">
                            Estado
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-20">
                            Activo
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">
                            Notas
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">
                            Acciones
                          </th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-28">
                            Advertencia
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {getDisplayData().map((row) => {
                          const motivosDuplicado = getDuplicadoMotivo(row)
                          const esDuplicado = motivosDuplicado.length > 0
                          return (
                            <tr
                              key={row._rowIndex}
                              className={
                                esDuplicado
                                  ? 'bg-red-200 border-l-4 border-l-red-600'
                                  : row._hasErrors
                                    ? 'bg-red-50'
                                    : 'bg-green-50'
                              }
                            >
                              <td className="border p-2 text-xs">{row._rowIndex}</td>

                              <td className="border p-2">
                                <div className="space-y-1">
                                  <input
                                    type="text"
                                    value={row.cedula}
                                    onChange={(e) =>
                                      updateCellValue(row, 'cedula', e.target.value)
                                    }
                                    className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                      row._validation.cedula?.isValid
                                        ? 'border-gray-300 bg-white text-black'
                                        : 'border-red-800 bg-red-800 text-white'
                                    }`}
                                  />
                                  {row.cedula &&
                                    cedulasDuplicadasEnArchivo.has((row.cedula || '').trim()) && (
                                      <span className="text-xs text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded block">
                                        Duplicada en archivo
                                      </span>
                                    )}
                                </div>
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.nombres}
                                  onChange={(e) =>
                                    updateCellValue(row, 'nombres', e.target.value)
                                  }
                                  className={`w-full text-sm p-2 border rounded min-w-[120px] ${
                                    row._validation.nombres?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <div className="flex items-center">
                                  <span className="bg-gray-100 border border-gray-300 rounded-l px-3 py-2 text-sm font-medium text-gray-700">
                                    +58
                                  </span>
                                  <input
                                    type="tel"
                                    value={row.telefono.replace('+58', '')}
                                    onChange={(e) => {
                                      const digits = e.target.value.replace(/\D/g, '')
                                      const value =
                                        digits.length > 10 ? '9999999999' : digits.slice(0, 10)
                                      updateCellValue(row, 'telefono', '+58' + value)
                                    }}
                                    placeholder="XXXXXXXXXX"
                                    className={`flex-1 text-sm p-2 border border-l-0 rounded-r min-w-[80px] ${
                                      row._validation.telefono?.isValid
                                        ? 'border-gray-300 bg-white text-black'
                                        : 'border-red-800 bg-red-800 text-white'
                                    }`}
                                  />
                                </div>
                              </td>

                              <td className="border p-2">
                                <input
                                  type="email"
                                  value={row.email}
                                  onChange={(e) => updateCellValue(row, 'email', e.target.value)}
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.email?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.direccion}
                                  onChange={(e) =>
                                    updateCellValue(row, 'direccion', e.target.value)
                                  }
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.direccion?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.fecha_nacimiento}
                                  onChange={(e) => {
                                    const value = e.target.value
                                    const onlyDigits = value.replace(/\D/g, '')
                                    if (onlyDigits.length === 0) {
                                      updateCellValue(row, 'fecha_nacimiento', '')
                                      return
                                    }
                                    let formatted = ''
                                    const digits = onlyDigits.substring(0, 8)
                                    if (digits.length === 1) formatted = digits
                                    else if (digits.length === 2)
                                      formatted = digits.substring(0, 2)
                                    else if (digits.length === 3)
                                      formatted =
                                        digits.substring(0, 2) + '/' + digits.substring(2, 3)
                                    else if (digits.length === 4)
                                      formatted =
                                        digits.substring(0, 2) + '/' + digits.substring(2, 4)
                                    else if (digits.length >= 5) {
                                      const dia = digits.substring(0, 2)
                                      const mes = digits.substring(2, 4)
                                      const ano = digits.substring(4, 8)
                                      formatted = dia + '/' + mes + '/' + ano
                                    }
                                    updateCellValue(row, 'fecha_nacimiento', formatted)
                                  }}
                                  onBlur={(e) => {
                                    const value = e.target.value
                                    if (!value || !value.includes('/')) return
                                    const parts = value.split('/')
                                    if (parts.length === 3) {
                                      if (parts[0].length === 1 && parseInt(parts[0]) <= 3) {
                                        parts[0] = '0' + parts[0]
                                      }
                                      if (parts[1].length === 1) {
                                        parts[1] = '0' + parts[1]
                                      }
                                      if (parts[2].length < 4) {
                                        parts[2] = parts[2].padStart(4, '0')
                                      }
                                      updateCellValue(row, 'fecha_nacimiento', parts.join('/'))
                                    }
                                  }}
                                  placeholder="DD/MM/YYYY"
                                  maxLength={10}
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.fecha_nacimiento?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.ocupacion}
                                  onChange={(e) =>
                                    updateCellValue(row, 'ocupacion', e.target.value)
                                  }
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.ocupacion?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <select
                                  value={row.estado || 'ACTIVO'}
                                  onChange={(e) =>
                                    updateCellValue(row, 'estado', e.target.value)
                                  }
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.estado?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                >
                                  {(opcionesEstado.length > 0
                                    ? opcionesEstado
                                    : [
                                        { valor: 'ACTIVO', etiqueta: 'Activo' },
                                        { valor: 'INACTIVO', etiqueta: 'Inactivo' },
                                        { valor: 'FINALIZADO', etiqueta: 'Finalizado' },
                                        { valor: 'LEGACY', etiqueta: 'Legacy' },
                                      ]
                                  ).map((opt) => (
                                    <option key={opt.valor} value={opt.valor}>
                                      {opt.etiqueta}
                                    </option>
                                  ))}
                                </select>
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.activo}
                                  onChange={(e) =>
                                    updateCellValue(row, 'activo', e.target.value)
                                  }
                                  className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                    row._validation.activo?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.notas}
                                  onChange={(e) => updateCellValue(row, 'notas', e.target.value)}
                                  className="w-full text-sm p-2 border border-gray-300 bg-white text-black rounded min-w-[80px]"
                                />
                              </td>

                              <td className="border p-2">
                                <div className="flex items-center justify-center space-x-1">
                                  {savedClients.has(row._rowIndex) ? (
                                    <div className="flex items-center text-green-600">
                                      <CheckCircle className="h-4 w-4 mr-1" />
                                      <span className="text-xs">Guardado</span>
                                    </div>
                                  ) : esDuplicado ? (
                                    <div className="flex flex-col items-center text-red-700 text-xs">
                                      <span>No se puede guardar</span>
                                      <span className="text-[10px]">(duplicado en archivo)</span>
                                    </div>
                                  ) : isClientValid(row) ? (
                                    <Button
                                      size="sm"
                                      onClick={() => saveIndividualClient(row)}
                                      disabled={
                                        savingProgress[row._rowIndex] ||
                                        serviceStatus === 'offline'
                                      }
                                      className="bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-1"
                                    >
                                      {savingProgress[row._rowIndex] ? (
                                        <>
                                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                          Guardando...
                                        </>
                                      ) : (
                                        <>
                                          <Save className="h-3 w-3 mr-1" />
                                          Guardar
                                        </>
                                      )}
                                    </Button>
                                  ) : (
                                    <div className="flex items-center text-gray-400">
                                      <AlertTriangle className="h-4 w-4 mr-1" />
                                      <span className="text-xs">Incompleto</span>
                                    </div>
                                  )}
                                </div>
                              </td>

                              <td
                                className={`border p-2 ${esDuplicado ? 'bg-red-300 font-semibold' : 'bg-gray-50'}`}
                              >
                                {esDuplicado ? (
                                  <div className="flex flex-col items-center justify-center gap-1 text-red-800">
                                    <div className="flex items-center gap-2">
                                      <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                                      <span className="text-sm uppercase tracking-wide">
                                        Duplicado
                                      </span>
                                    </div>
                                    <span className="text-xs">({motivosDuplicado.join(', ')})</span>
                                  </div>
                                ) : (
                                  <span className="text-gray-400 text-xs">—</span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>

                    <div className="absolute bottom-0 right-0 w-4 h-4 bg-gray-400 cursor-se-resize opacity-50 hover:opacity-100 transition-opacity">
                      <div className="w-full h-full bg-gradient-to-br from-transparent via-gray-600 to-gray-800" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </motion.div>

      {/* Toasts */}
      <div className="fixed top-4 right-4 z-[60] space-y-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 300, scale: 0.8 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 300, scale: 0.8 }}
              className={`max-w-sm p-4 rounded-lg shadow-lg border-l-4 ${
                toast.type === 'error'
                  ? 'bg-red-50 border-red-500 text-red-800'
                  : toast.type === 'warning'
                    ? 'bg-yellow-50 border-yellow-500 text-yellow-800'
                    : 'bg-green-50 border-green-500 text-green-800'
              }`}
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  {toast.type === 'error' && (
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                  )}
                  {toast.type === 'warning' && (
                    <Info className="h-5 w-5 text-yellow-500" />
                  )}
                  {toast.type === 'success' && (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{toast.message}</p>
                  {toast.suggestion && (
                    <p className="text-xs mt-1 opacity-80">{toast.suggestion}</p>
                  )}
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="flex-shrink-0 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
