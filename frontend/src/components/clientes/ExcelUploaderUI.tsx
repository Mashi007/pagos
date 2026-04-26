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
  Search,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Button } from '../ui/button'

import { Badge } from '../ui/badge'

import {
  useExcelUpload,
  type ExcelUploaderProps,
} from '../../hooks/useExcelUpload'

import {
  CARGA_MASIVA_CLIENTES_DEFAULT_FECHA_NACIMIENTO,
  CLIENTE_EMAIL_MAX_LENGTH,
  cedulaComparableKey,
} from '../../utils/excelValidation'

export function ExcelUploaderUI(props: ExcelUploaderProps) {
  const {
    handleCambiarArchivo,

    isDragging,

    uploadedFile,

    excelData,

    isProcessing,

    showPreview,

    setShowPreview,

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

    removeToast,

    getValidClients,

    getDisplayData,

    getSavedClientsCount,

    getDuplicadoMotivo,

    isClientValid,

    cedulasDuplicadasEnArchivo,

    nombresDuplicadosEnArchivo,

    emailDuplicadosEnArchivo,

    duplicateEmailKeysEnArchivo,

    telefonoDuplicadosEnArchivo,

    emailsExistentesEnBD,

    saveIndividualClient,

    saveAllValidClients,

    confirmSaveOmittingExistingCedulas,

    sendToRevisarClientes,

    sendAllToRevisarClientes,

    getRowsToRevisarClientes,

    enviadosRevisar,

    isSendingAllRevisar,

    batchProgress,

    onClose,

    navigate,
  } = useExcelUpload(props)

  const hasDuplicates =
    cedulasDuplicadasEnArchivo.size > 0 ||
    nombresDuplicadosEnArchivo.size > 0 ||
    emailDuplicadosEnArchivo.size > 0 ||
    telefonoDuplicadosEnArchivo.size > 0 ||
    duplicateEmailKeysEnArchivo.length > 0

  const hayConflictosConBD =
    cedulasExistentesEnBD.length > 0 || emailsExistentesEnBD.length > 0

  /** Regla: observación 100% solo nombre(s) de columna - sin "duplicado" ni texto extra */

  const columnasDuplicadas = (motivos: string[]) =>
    [
      ...new Set(
        motivos.map(m => {
          if (m.includes('cédula')) return 'Cédula'

          if (m.includes('email')) return 'Email'

          if (m.includes('nombres')) return 'Nombres'

          if (m.includes('teléfono')) return 'Teléfono'

          return m
        })
      ),
    ].join(', ')

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
        {/* cabecera fija (fuera del scroll) */}

        <div className="flex-shrink-0 rounded-t-lg bg-gradient-to-r from-green-600 to-green-700 p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />

              <h2 className="text-xl font-bold">CARGA MASIVA DE CLIENTES</h2>

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
                  className={`h-2 w-2 rounded-full ${
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
          getSavedClientsCount() === 0 ? (
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
                    Columnas: Cédula | Nombres | Teléfono | Email (columna D).
                    La cédula y el email se comparan con la tabla{' '}
                    <strong>clientes</strong> al cargar. Si hay duplicado en el
                    archivo o ya registrado en BD, la fila no se puede guardar
                    hasta corregir.
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
            (enviadosRevisar.size > 0 || getSavedClientsCount() > 0) && (
              <Card className="border-green-300 bg-green-50">
                <CardContent className="space-y-4 pb-8 pt-8 text-center">
                  <CheckCircle className="mx-auto h-16 w-16 text-green-500" />

                  <h3 className="text-xl font-bold text-green-800">
                    ¡Procesamiento completado!
                  </h3>

                  <div className="mt-2 flex justify-center gap-6 text-sm">
                    {getSavedClientsCount() > 0 && (
                      <span className="rounded-full bg-green-100 px-4 py-2 font-semibold text-green-800">
                        ✓ {getSavedClientsCount()} guardado(s)
                      </span>
                    )}

                    {enviadosRevisar.size > 0 && (
                      <span className="rounded-full bg-amber-100 px-4 py-2 font-semibold text-amber-800">
                        ⚠ {enviadosRevisar.size} enviado(s) a Revisar clientes
                      </span>
                    )}
                  </div>

                  <div className="flex justify-center gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        navigate('/clientes?revisar=1')
                        onClose()
                      }}
                      className="border-amber-300 bg-amber-50 text-amber-800"
                    >
                      <Search className="mr-2 h-4 w-4" />
                      Ver Revisar clientes
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

          {/* Tabla y estadísticas cuando hay datos */}

          {excelData.length > 0 && (
            <div className="space-y-4">
              {/* Preview table */}

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>

                <CardContent>
                  {(hasDuplicates || hayConflictosConBD) && (
                    <div className="mb-4 space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                      <div className="flex items-center gap-2 font-semibold">
                        <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                        Duplicados en el archivo y coincidencias con{' '}
                        <strong>clientes</strong>
                      </div>

                      <p className="text-amber-900">
                        No se puede guardar filas con cédula o email repetido en
                        el Excel, ni si ya están en la tabla{' '}
                        <strong>clientes</strong>. Revise las filas en rojo o
                        use otro archivo.
                      </p>

                      {cedulasExistentesEnBD.length > 0 && (
                        <div>
                          <p className="font-medium text-amber-950">
                            Cédulas que ya están en <strong>clientes</strong> (
                            {cedulasExistentesEnBD.length})
                          </p>

                          <p className="mt-1 text-xs text-amber-800">
                            Lista desplazable (no se muestra todo en una sola
                            línea).
                          </p>

                          <div className="mt-1 max-h-40 overflow-y-auto break-all rounded border border-amber-200 bg-white/90 p-2 font-mono text-xs">
                            {cedulasExistentesEnBD.join(', ')}
                          </div>
                        </div>
                      )}

                      {emailsExistentesEnBD.length > 0 && (
                        <div>
                          <p className="font-medium text-amber-950">
                            Correos que ya están en <strong>clientes</strong> (
                            {emailsExistentesEnBD.length})
                          </p>

                          <div className="mt-1 max-h-32 overflow-y-auto break-all rounded border border-amber-200 bg-white/90 p-2 font-mono text-xs">
                            {emailsExistentesEnBD.join(', ')}
                          </div>
                        </div>
                      )}

                      {cedulasDuplicadasEnArchivo.size > 0 && (
                        <div>
                          <p className="font-medium text-amber-950">
                            Cédulas repetidas en este Excel (
                            {cedulasDuplicadasEnArchivo.size})
                          </p>

                          <div className="mt-1 max-h-32 overflow-y-auto break-all rounded border border-amber-200 bg-white/90 p-2 font-mono text-xs">
                            {[...cedulasDuplicadasEnArchivo].join(', ')}
                          </div>
                        </div>
                      )}

                      {duplicateEmailKeysEnArchivo.length > 0 && (
                        <div>
                          <p className="font-medium text-amber-950">
                            Correos repetidos en este Excel (
                            {duplicateEmailKeysEnArchivo.length})
                          </p>

                          <div className="mt-1 max-h-32 overflow-y-auto break-all rounded border border-amber-200 bg-white/90 p-2 font-mono text-xs">
                            {duplicateEmailKeysEnArchivo.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div
                    className="relative min-w-full overflow-x-auto"
                    style={{
                      resize: 'both',
                      minWidth: '800px',
                      minHeight: '400px',
                    }}
                  >
                    <table className="w-full min-w-[1400px] border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="w-16 border p-2 text-left text-xs font-medium text-gray-500">
                            Fila
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium text-gray-500">
                            Cédula
                          </th>

                          <th className="w-48 border p-2 text-left text-xs font-medium text-gray-500">
                            Nombres y Apellidos
                          </th>

                          <th className="w-28 border p-2 text-left text-xs font-medium text-gray-500">
                            Teléfono
                          </th>

                          <th className="w-40 border p-2 text-left text-xs font-medium text-gray-500">
                            Email
                          </th>

                          <th className="w-48 border p-2 text-left text-xs font-medium text-gray-500">
                            Dirección
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium text-gray-500">
                            Fecha Nac.
                          </th>

                          <th className="w-32 border p-2 text-left text-xs font-medium text-gray-500">
                            Ocupación
                          </th>

                          <th className="w-48 border p-2 text-left text-xs font-medium text-gray-500">
                            Notas
                          </th>

                          <th className="w-24 border p-2 text-left text-xs font-medium text-gray-500">
                            Verificar
                          </th>

                          <th className="w-28 border p-2 text-left text-xs font-medium text-gray-500">
                            Advertencia
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {getDisplayData().map(row => {
                          const motivosDuplicado = getDuplicadoMotivo(row)

                          const esDuplicado = motivosDuplicado.length > 0

                          const esCedulaNoAcepta =
                            esDuplicado &&
                            motivosDuplicado.some(m => /c[eé]dula/i.test(m))

                          return (
                            <tr
                              key={row._rowIndex}
                              className={
                                esDuplicado
                                  ? 'border-l-4 border-l-red-600 bg-red-200'
                                  : row._hasErrors
                                    ? 'bg-red-50'
                                    : 'bg-green-50'
                              }
                            >
                              <td className="border p-2 text-xs">
                                {row._rowIndex}
                              </td>

                              <td className="border p-2">
                                <div className="space-y-1">
                                  <input
                                    type="text"
                                    value={row.cedula}
                                    onChange={e =>
                                      updateCellValue(
                                        row,
                                        'cedula',
                                        e.target.value
                                      )
                                    }
                                    className={`w-full min-w-[80px] rounded border p-2 text-sm ${
                                      row._validation.cedula?.isValid
                                        ? 'border-gray-300 bg-white text-black'
                                        : 'border-red-800 bg-red-800 text-white'
                                    }`}
                                  />

                                  {(() => {
                                    const ck = cedulaComparableKey(row.cedula)

                                    return ck &&
                                      cedulasDuplicadasEnArchivo.has(ck) ? (
                                      <span className="block rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">
                                        Duplicada en archivo
                                      </span>
                                    ) : null
                                  })()}
                                </div>
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.nombres}
                                  onChange={e =>
                                    updateCellValue(
                                      row,
                                      'nombres',
                                      e.target.value
                                    )
                                  }
                                  className={`w-full min-w-[120px] rounded border p-2 text-sm ${
                                    row._validation.nombres?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <div className="flex items-center">
                                  <span className="rounded-l border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700">
                                    +58
                                  </span>

                                  <input
                                    type="tel"
                                    value={row.telefono.replace('+58', '')}
                                    onChange={e => {
                                      const digits = e.target.value.replace(
                                        /\D/g,
                                        ''
                                      )

                                      const value =
                                        digits.length > 10
                                          ? '9999999999'
                                          : digits.slice(0, 10)

                                      updateCellValue(
                                        row,
                                        'telefono',
                                        '+58' + value
                                      )
                                    }}
                                    placeholder="XXXXXXXXXX"
                                    className={`min-w-[80px] flex-1 rounded-r border border-l-0 p-2 text-sm ${
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
                                  maxLength={CLIENTE_EMAIL_MAX_LENGTH}
                                  onChange={e =>
                                    updateCellValue(
                                      row,
                                      'email',
                                      e.target.value
                                    )
                                  }
                                  className={`w-full min-w-[50ch] rounded border p-2 text-sm ${
                                    row._validation.email?.isValid
                                      ? 'border-gray-300 bg-white text-black'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  readOnly
                                  title="Valor fijo en carga masiva (no se usa la columna del Excel)"
                                  value={row.direccion}
                                  className={`w-full min-w-[80px] cursor-not-allowed rounded border p-2 text-sm ${
                                    row._validation.direccion?.isValid
                                      ? 'border-gray-200 bg-gray-50 text-gray-800'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  readOnly
                                  title="Valor fijo en carga masiva (no se usa la columna del Excel)"
                                  value={row.fecha_nacimiento}
                                  placeholder={
                                    CARGA_MASIVA_CLIENTES_DEFAULT_FECHA_NACIMIENTO
                                  }
                                  maxLength={10}
                                  className={`w-full min-w-[80px] cursor-not-allowed rounded border p-2 text-sm ${
                                    row._validation.fecha_nacimiento?.isValid
                                      ? 'border-gray-200 bg-gray-50 text-gray-800'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  readOnly
                                  title="Valor fijo en carga masiva (no se usa la columna del Excel)"
                                  value={row.ocupacion}
                                  className={`w-full min-w-[80px] cursor-not-allowed rounded border p-2 text-sm ${
                                    row._validation.ocupacion?.isValid
                                      ? 'border-gray-200 bg-gray-50 text-gray-800'
                                      : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </td>

                              <td className="border p-2">
                                <input
                                  type="text"
                                  value={row.notas}
                                  onChange={e =>
                                    updateCellValue(
                                      row,
                                      'notas',
                                      e.target.value
                                    )
                                  }
                                  className="w-full min-w-[80px] rounded border border-gray-300 bg-white p-2 text-sm text-black"
                                />
                              </td>

                              <td className="border p-2">
                                <div className="flex flex-col items-center gap-1">
                                  <div className="flex items-center justify-center space-x-1">
                                    {savedClients.has(row._rowIndex) ? (
                                      <div className="flex items-center text-green-600">
                                        <CheckCircle className="mr-1 h-4 w-4" />

                                        <span className="text-xs">
                                          Guardado
                                        </span>
                                      </div>
                                    ) : esDuplicado ? (
                                      <div className="flex flex-col items-center text-xs text-red-700">
                                        {esCedulaNoAcepta ? (
                                          <span className="font-semibold">
                                            No se acepta
                                          </span>
                                        ) : (
                                          <>
                                            <span>No se puede guardar</span>

                                            <span
                                              className="text-[10px] font-medium"
                                              title={motivosDuplicado.join(
                                                '; '
                                              )}
                                            >
                                              {columnasDuplicadas(
                                                motivosDuplicado
                                              )}
                                            </span>
                                          </>
                                        )}
                                      </div>
                                    ) : isClientValid(row) ? (
                                      <Button
                                        size="sm"
                                        onClick={() =>
                                          saveIndividualClient(row)
                                        }
                                        disabled={
                                          savingProgress[row._rowIndex] ||
                                          serviceStatus === 'offline'
                                        }
                                        className="bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700"
                                      >
                                        {savingProgress[row._rowIndex] ? (
                                          <>
                                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                            Guardando...
                                          </>
                                        ) : (
                                          <>
                                            <Save className="mr-1 h-3 w-3" />
                                            Guardar
                                          </>
                                        )}
                                      </Button>
                                    ) : (
                                      <div className="flex items-center text-gray-400">
                                        <AlertTriangle className="mr-1 h-4 w-4" />

                                        <span className="text-xs">
                                          Incompleto
                                        </span>
                                      </div>
                                    )}

                                    {!savedClients.has(row._rowIndex) && (
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() =>
                                          sendToRevisarClientes(row)
                                        }
                                        disabled={
                                          savingProgress[row._rowIndex] ||
                                          serviceStatus === 'offline'
                                        }
                                        className="border-amber-400 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50"
                                        title="Enviar a Revisar clientes"
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
                                </div>
                              </td>

                              <td
                                className={`border p-2 ${esDuplicado ? 'bg-red-300 font-semibold' : 'bg-gray-50'}`}
                              >
                                {esDuplicado ? (
                                  <div className="flex flex-col items-center justify-center gap-1 text-red-800">
                                    <div className="flex items-center gap-2">
                                      <AlertTriangle className="h-5 w-5 flex-shrink-0" />

                                      <span
                                        className="text-sm font-semibold"
                                        title={motivosDuplicado.join('; ')}
                                      >
                                        {columnasDuplicadas(motivosDuplicado)}
                                      </span>
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-xs text-gray-400">
                                    -
                                  </span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>

                    <div className="absolute bottom-0 right-0 h-4 w-4 cursor-se-resize bg-gray-400 opacity-50 transition-opacity hover:opacity-100">
                      <div className="h-full w-full bg-gradient-to-br from-transparent via-gray-600 to-gray-800" />
                    </div>
                  </div>
                </CardContent>

                {batchProgress && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                    <div className="mb-1 flex items-center justify-between text-sm font-medium text-blue-800">
                      <span>Enviando a Revisar clientes...</span>

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
                        <Badge variant="outline">
                          Total: {totalRows} filas
                        </Badge>

                        <Badge variant="outline" className="text-green-700">
                          Válidos: {getValidClients().length}
                        </Badge>

                        <Badge variant="outline">
                          Guardados: {getSavedClientsCount()}
                        </Badge>

                        {(hasDuplicates || hayConflictosConBD) && (
                          <Badge
                            variant="outline"
                            className="border-red-400 bg-red-100 text-red-800"
                          >
                            Duplicados: revisar archivo o BD
                          </Badge>
                        )}

                        {enviadosRevisar.size > 0 && (
                          <Badge
                            variant="outline"
                            className="border-amber-300 text-amber-700"
                          >
                            {enviadosRevisar.size} a Revisar clientes
                          </Badge>
                        )}

                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id="showOnlyPending"
                            checked={showOnlyPending}
                            onChange={e => setShowOnlyPending(e.target.checked)}
                            className="rounded"
                          />

                          <label
                            htmlFor="showOnlyPending"
                            className="text-sm text-gray-600"
                          >
                            Solo pendientes
                          </label>
                        </div>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleCambiarArchivo}
                          title="Limpiar datos actuales y cargar otro archivo"
                        >
                          <X className="mr-2 h-4 w-4" />
                          Cambiar archivo
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            navigate('/clientes')
                            onClose()
                          }}
                          className="border-green-300 bg-green-50"
                          title="Ir al listado de clientes"
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          Ir a clientes
                        </Button>

                        {getRowsToRevisarClientes().length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => sendAllToRevisarClientes()}
                            disabled={
                              isSendingAllRevisar || serviceStatus === 'offline'
                            }
                            className="border-amber-400 bg-amber-100 text-amber-800 hover:bg-amber-200"
                            title="Enviar todas las filas pendientes a Revisar clientes"
                          >
                            {isSendingAllRevisar ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Enviando...
                              </>
                            ) : (
                              <>
                                <Search className="mr-2 h-4 w-4" />
                                ENVIAR REVISAR CLIENTES (
                                {getRowsToRevisarClientes().length})
                              </>
                            )}
                          </Button>
                        )}
                      </div>

                      <Button
                        onClick={saveAllValidClients}
                        disabled={
                          getValidClients().length === 0 ||
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
                            Guardar Todos ({getValidClients().length})
                          </>
                        )}
                      </Button>
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
                      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                    >
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.9, opacity: 0 }}
                        className="max-h-[80vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white shadow-xl"
                      >
                        <div className="p-6">
                          <div className="mb-4 flex items-center justify-between">
                            <h2 className="flex items-center text-2xl font-bold text-red-600">
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

                          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3">
                            <p className="text-sm text-red-700">
                              <strong>No se puede guardar:</strong> Se
                              encontraron {totalRows - validRows} registros con
                              errores que deben corregirse antes de continuar.
                            </p>

                            <p className="mt-1 text-sm text-red-600">
                              <strong>Errores incluyen:</strong> campos de
                              validación inválidos.
                            </p>
                          </div>

                          <div className="max-h-[50vh] space-y-4 overflow-y-auto">
                            {getDisplayData()
                              .filter(row => row._hasErrors)

                              .map((row, index) => (
                                <div
                                  key={index}
                                  className="rounded-lg border border-red-200 bg-red-50 p-4"
                                >
                                  <div className="mb-3 flex items-center justify-between">
                                    <h3 className="font-semibold text-red-800">
                                      Fila {row._rowIndex}: {row.nombres}
                                    </h3>

                                    <Badge
                                      variant="outline"
                                      className="border-red-300 text-red-600"
                                    >
                                      {
                                        Object.keys(row._validation).filter(
                                          f => !row._validation[f]?.isValid
                                        ).length
                                      }{' '}
                                      errores
                                    </Badge>
                                  </div>

                                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                    {Object.entries(row._validation).map(
                                      ([field, validation]) => {
                                        const v = validation as {
                                          isValid?: boolean
                                          message?: string
                                        }

                                        if (v?.isValid) return null

                                        return (
                                          <div
                                            key={field}
                                            className="flex items-start space-x-2"
                                          >
                                            <div className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-red-500" />

                                            <div className="flex-1">
                                              <span className="text-sm font-medium capitalize text-gray-700">
                                                {field}:
                                              </span>

                                              <div className="mt-1 text-sm text-red-600">
                                                {v?.message}
                                              </div>
                                            </div>
                                          </div>
                                        )
                                      }
                                    )}
                                  </div>
                                </div>
                              ))}
                          </div>

                          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
                            <div className="flex items-start space-x-2">
                              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-600" />

                              <div className="text-sm text-blue-800">
                                <strong>Instrucciones para corregir:</strong>

                                <ul className="ml-4 mt-2 list-disc space-y-1">
                                  <li>
                                    Los campos con fondo rojo en la tabla tienen
                                    errores de validación
                                  </li>

                                  <li>
                                    Haz clic en cualquier campo para editarlo
                                    directamente
                                  </li>

                                  <li>
                                    Los errores se corrigen automáticamente al
                                    escribir valores válidos
                                  </li>

                                  <li>
                                    Una vez corregidos todos los errores, podrás
                                    guardar los datos
                                  </li>
                                </ul>
                              </div>
                            </div>
                          </div>

                          <div className="mt-6 flex justify-end space-x-3">
                            <Button
                              variant="outline"
                              onClick={() => setShowValidationModal(false)}
                            >
                              Cerrar
                            </Button>

                            <Button
                              onClick={() => {
                                setShowValidationModal(false)

                                const tableElement =
                                  document.querySelector('.overflow-x-auto')

                                if (tableElement) {
                                  tableElement.scrollIntoView({
                                    behavior: 'smooth',
                                  })
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
                  {showModalCedulasExistentes &&
                    cedulasExistentesEnBD.length > 0 && (
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
                          className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
                        >
                          <div className="mb-4 flex items-center gap-2">
                            <AlertTriangle className="h-6 w-6 flex-shrink-0 text-amber-600" />

                            <h2 className="text-xl font-bold text-gray-800">
                              Cédulas ya registradas
                            </h2>
                          </div>

                          <p className="mb-3 text-sm text-gray-600">
                            Las siguientes cédulas ya existen en el sistema. Si
                            continúa, esas filas se omitirán y solo se guardarán
                            el resto.
                          </p>

                          <ul className="mb-4 max-h-40 overflow-y-auto rounded border border-gray-200 bg-gray-50 p-2 font-mono text-sm">
                            {cedulasExistentesEnBD.map((ced, idx) => (
                              <li key={idx} className="py-0.5">
                                {ced}
                              </li>
                            ))}
                          </ul>

                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              onClick={cancelCedulasModal}
                            >
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
              </Card>
            </div>
          )}
        </div>
      </motion.div>

      {/* Toasts */}

      <div className="fixed right-4 top-4 z-[60] space-y-2">
        <AnimatePresence>
          {toasts.map(toast => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 300, scale: 0.8 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 300, scale: 0.8 }}
              className={`max-w-sm rounded-lg border-l-4 p-4 shadow-lg ${
                toast.type === 'error'
                  ? 'border-red-500 bg-red-50 text-red-800'
                  : toast.type === 'warning'
                    ? 'border-yellow-500 bg-yellow-50 text-yellow-800'
                    : 'border-green-500 bg-green-50 text-green-800'
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
                    <p className="mt-1 text-xs opacity-80">
                      {toast.suggestion}
                    </p>
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
