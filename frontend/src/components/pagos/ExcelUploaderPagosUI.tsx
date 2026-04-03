/**









 * UI para carga masiva de pagos desde Excel (previsualizar y editar).









 * Formatos (fila 1 = encabezados): opcional columna Banco / institución; D) Cédula | Monto | Fecha | Documento;









 * A) Documento | Cédula | Fecha | Monto; B) Fecha | Cédula | Monto | Documento;









 * C) Cédula | ID Préstamo | Fecha | Monto | Documento.









 * Solo créditos activos (APROBADO) en el selector.









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
  Search,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Button } from '../ui/button'

import { Badge } from '../ui/badge'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import {
  useExcelUploadPagos,
  type ExcelUploaderPagosProps,
} from '../../hooks/useExcelUploadPagos'

import { useMemo } from 'react'

import { PagosConErroresSection } from './PagosConErroresSection'

import {
  TablaEditablePagos,
  PrestamoDuplicadoEnBdBloque,
} from './TablaEditablePagos'

import {
  cedulaLookupParaFila,
  cedulaParaLookup,
  OBSERVACIONES_POR_CAMPO,
  parsePrestamoIdFromNumeroCredito,
} from '../../utils/pagoExcelValidation'

import { useNavigate } from 'react-router-dom'

const inputClass = (isValid: boolean) =>
  `w-full text-sm p-2 border rounded min-w-[70px] ${
    isValid
      ? 'border-gray-300 bg-white text-black'
      : 'border-red-600 bg-red-50 text-red-900'
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

    setExcelData,

    clearAndShowFileSelect,

    getValidRows,

    saveIndividualPago,

    saveRowIfValid,

    saveAllValid,

    sendToRevisarPagos,

    sendAllToRevisarPagos,

    sendDuplicadosToRevisarPagos,

    getRowsToRevisarPagos,

    getDuplicadosRows,

    isSendingAllRevisar,

    enviadosRevisar,

    duplicadosPendientesRevisar,

    onClose,

    removeToast,

    addToast,

    batchProgress,
  } = useExcelUploadPagos(props)

  const totalCargadas = excelData.length

  const validCount = getValidRows().length

  const invalidCount = excelData.filter(r => r._hasErrors).length

  const tablaRowsVisibles = useMemo(
    () =>
      excelData.filter(
        r => !savedRows.has(r._rowIndex) && !enviadosRevisar.has(r._rowIndex)
      ),
    [excelData, savedRows, enviadosRevisar]
  )

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
        {/* Cabecera fija (fuera del scroll, evita efecto scroll-linked en Firefox) */}

        <div className="flex-shrink-0 rounded-t-lg bg-gradient-to-r from-green-600 to-green-700 p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileSpreadsheet className="h-6 w-6" />

              <div>
                <h2 className="text-xl font-bold">CARGA MASIVA DE PAGOS</h2>

                <p className="mt-0.5 text-xs text-green-100">
                  Recomendado: Cédula | Fecha | Monto | Documento. Máx. 10 MB.
                  Hasta 2.500 filas recomendado; máx. 10.000.
                </p>
              </div>

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

          {/* Indicadores: filas cargadas, válidas, inválidas (varían al editar y validar) */}

          <div className="mt-4 flex flex-wrap items-center gap-4 rounded-lg bg-white/15 px-4 py-2 text-sm">
            <span className="font-medium text-green-100">Indicadores:</span>

            <span className="flex items-center gap-1.5">
              <span className="text-green-100">Filas cargadas:</span>

              <strong className="tabular-nums text-white">
                {totalCargadas}
              </strong>
            </span>

            <span className="flex items-center gap-1.5">
              <span className="text-green-100">Válidas:</span>

              <strong className="tabular-nums text-white">{validCount}</strong>
            </span>

            <span className="flex items-center gap-1.5">
              <span className="text-green-100">Inválidas:</span>

              <strong className="tabular-nums text-white">
                {invalidCount}
              </strong>

              <span className="text-xs text-green-200">
                (van a Revisar Pagos)
              </span>
            </span>

            {savedRows.size > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="text-green-100">Guardadas:</span>

                <strong className="tabular-nums text-white">
                  {savedRows.size}
                </strong>
              </span>
            )}

            {enviadosRevisar.size > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="text-green-100">En Revisar Pagos:</span>

                <strong className="tabular-nums text-white">
                  {enviadosRevisar.size}
                </strong>
              </span>
            )}
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
                    Columnas: Cédula | Fecha de pago | Monto | Documento | ID
                    Préstamo (opcional) | Conciliación (Sí/No) | Moneda (USD/BS)
                    | Tasa (opcional, Bs/USD si no hay tasa en BD). Documentos
                    numéricos largos se normalizan automáticamente.
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

                  <div className="mt-2 flex flex-wrap justify-center gap-4 text-sm text-gray-700">
                    <span className="rounded-full border border-gray-200 bg-white/80 px-4 py-2">
                      Filas cargadas:{' '}
                      <strong>{savedRows.size + enviadosRevisar.size}</strong>
                    </span>

                    <span className="rounded-full bg-green-100 px-4 py-2 font-semibold text-green-800">
                      ✓ Guardadas: {savedRows.size}
                    </span>

                    <span className="rounded-full bg-amber-100 px-4 py-2 font-semibold text-amber-800">
                      ⚠ En Revisar Pagos: {enviadosRevisar.size}
                    </span>
                  </div>

                  <div className="flex justify-center gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        navigate('/pagos?revisar=1')
                        onClose()
                      }}
                      className="border-amber-300 bg-amber-50 text-amber-800"
                    >
                      <Search className="mr-2 h-4 w-4" />
                      Ver Revisar Pagos
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

          {/* TABLA EDITABLE: solo filas pendientes (guardadas/enviadas a revisar se ocultan en cuanto se guardan) */}

          {excelData.length > 0 && (
            <div className="space-y-4">
              <TablaEditablePagos
                rows={tablaRowsVisibles}
                prestamosPorCedula={prestamosPorCedula}
                onUpdateCell={updateCellValue}
                saveRowIfValid={saveRowIfValid}
                savingProgress={savingProgress}
                serviceStatus={serviceStatus}
                onSendToRevisarPagos={
                  sendToRevisarPagos
                    ? row =>
                        sendToRevisarPagos(row, () =>
                          navigate('/pagos?revisar=1')
                        )
                    : undefined
                }
                isSendingRevisar={isSendingAllRevisar}
              />
              {batchProgress && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                  <div className="mb-1 flex items-center justify-between text-sm font-medium text-blue-800">
                    <span>Enviando a Revisar Pagos...</span>

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
                      <Badge variant="outline" className="font-medium">
                        Filas cargadas: {totalCargadas}
                      </Badge>

                      <Badge
                        variant="outline"
                        className="border-green-400 text-green-700"
                      >
                        Válidas: {validCount}
                      </Badge>

                      <Badge
                        variant="outline"
                        className={
                          invalidCount > 0 ? 'border-red-400 text-red-700' : ''
                        }
                      >
                        Inválidas: {invalidCount}
                      </Badge>

                      <Badge variant="outline">
                        Guardadas: {savedRows.size}
                      </Badge>

                      {duplicadosPendientesRevisar.size > 0 && (
                        <Badge
                          variant="outline"
                          className="border-amber-300 text-amber-700"
                        >
                          Duplicados: {duplicadosPendientesRevisar.size}
                        </Badge>
                      )}

                      {duplicadosPendientesRevisar.size > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => sendDuplicadosToRevisarPagos()}
                          disabled={
                            isSendingAllRevisar || serviceStatus === 'offline'
                          }
                          className="border-amber-400 bg-amber-100 text-amber-800 hover:bg-amber-200"
                          title="Enviar solo duplicados a Revisar Pagos (observaciones)"
                        >
                          {isSendingAllRevisar ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Enviando...
                            </>
                          ) : (
                            <>
                              <Search className="mr-2 h-4 w-4" />
                              ENVIAR DUPLICADOS (
                              {duplicadosPendientesRevisar.size})
                            </>
                          )}
                        </Button>
                      )}

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          addToast(
                            'warning',
                            'Se borrará todo y se cargará otro archivo.'
                          )

                          clearAndShowFileSelect()
                        }}
                      >
                        <X className="mr-2 h-4 w-4" />
                        Cambiar archivo
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigate('/pagos')
                          onClose()
                        }}
                        className="border-green-300 bg-green-50"
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ir a Pagos
                      </Button>

                      {getRowsToRevisarPagos().length > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => sendAllToRevisarPagos()}
                          disabled={
                            isSendingAllRevisar || serviceStatus === 'offline'
                          }
                          className="border-amber-400 bg-amber-100 text-amber-800 hover:bg-amber-200"
                          title="Enviar TODAS las pendientes a Revisar Pagos: inválidas + duplicados + sin crédito / varios créditos sin elegir"
                        >
                          {isSendingAllRevisar ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Enviando...
                            </>
                          ) : (
                            <>
                              <Search className="mr-2 h-4 w-4" />
                              Enviar todas → Revisar Pagos (
                              {getRowsToRevisarPagos().length})
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
              {/* ANTERIOR - TABLA HTML REMOVIDA */}
              {false && (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <Eye className="mr-2 h-5 w-5" />
                        Previsualización
                      </CardTitle>
                    </CardHeader>

                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[980px] border-collapse">
                          <thead>
                            <tr className="border-b-2 border-gray-300 bg-gray-50">
                              <th className="w-12 border p-2 text-left text-xs font-medium">
                                Fila
                              </th>

                              <th className="w-24 border p-2 text-left text-xs font-medium">
                                Cédula
                              </th>

                              <th className="w-24 border p-2 text-left text-xs font-medium">
                                Fecha pago
                              </th>

                              <th className="w-24 border p-2 text-left text-xs font-medium">
                                Monto
                              </th>

                              <th className="w-28 border p-2 text-left text-xs font-medium">
                                Documento
                              </th>

                              <th className="min-w-[140px] border p-2 text-left text-xs font-medium">
                                Crédito
                              </th>

                              <th className="w-24 border p-2 text-left text-xs font-medium">
                                Conciliación
                              </th>

                              <th className="w-14 border p-2 text-center text-xs font-medium">
                                Acción
                              </th>
                            </tr>
                          </thead>

                          <tbody>
                            {excelData

                              .filter(
                                row =>
                                  !enviadosRevisar.has(row._rowIndex) &&
                                  !savedRows.has(row._rowIndex)
                              )

                              .map(row => {
                                const cedulaLookup = cedulaLookupParaFila(
                                  row.cedula || '',
                                  row.numero_documento || ''
                                )

                                const cedulaColNorm =
                                  cedulaParaLookup(row.cedula) ||
                                  (row.cedula || '').trim().replace(/-/g, '')

                                const cedulaSinGuion = cedulaLookup.replace(
                                  /-/g,
                                  ''
                                )

                                let prestamosActivos =
                                  prestamosPorCedula[cedulaLookup] ||
                                  prestamosPorCedula[cedulaSinGuion] ||
                                  prestamosPorCedula[
                                    cedulaLookup.toUpperCase()
                                  ] ||
                                  prestamosPorCedula[
                                    cedulaLookup.toLowerCase()
                                  ] ||
                                  []

                                if (
                                  prestamosActivos.length === 0 &&
                                  cedulaColNorm
                                )
                                  prestamosActivos =
                                    prestamosPorCedula[cedulaColNorm] ||
                                    prestamosPorCedula[
                                      cedulaColNorm.toUpperCase()
                                    ] ||
                                    prestamosPorCedula[
                                      cedulaColNorm.toLowerCase()
                                    ] ||
                                    []

                                if (prestamosActivos.length === 0) {
                                  const keysMap =
                                    Object.keys(prestamosPorCedula)

                                  if (keysMap.length === 1)
                                    prestamosActivos =
                                      prestamosPorCedula[keysMap[0]] || []
                                }

                                const tieneCreditos =
                                  prestamosActivos.length >= 1

                                // Normalizar prestamo_id: acepta numérico o formato VE-96179604, VE/96179604, etc.

                                const rawId = row.prestamo_id

                                const idNormalizado =
                                  rawId != null &&
                                  rawId !== 0 &&
                                  String(rawId) !== 'none'
                                    ? typeof rawId === 'number'
                                      ? rawId
                                      : parsePrestamoIdFromNumeroCredito(rawId)
                                    : null

                                const prestamoIdElegido =
                                  idNormalizado != null
                                    ? String(idNormalizado)
                                    : null

                                const esValidoEnLista =
                                  prestamoIdElegido != null &&
                                  prestamosActivos.some(
                                    p => p.id === idNormalizado
                                  )

                                const valorCredito = esValidoEnLista
                                  ? prestamoIdElegido
                                  : prestamosActivos.length === 1
                                    ? String(prestamosActivos[0].id)
                                    : 'none'

                                return (
                                  <tr
                                    key={row._rowIndex}
                                    className={
                                      row._hasErrors
                                        ? 'border-b border-gray-300 bg-red-50'
                                        : 'border-b border-gray-300 bg-green-50'
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
                                          updateCellValue(
                                            row,
                                            'cedula',
                                            e.target.value
                                          )
                                        }
                                        onBlur={() => {
                                          const c =
                                            cedulaLookupParaFila(
                                              row.cedula || '',
                                              row.numero_documento || ''
                                            ) || (row.cedula || '').trim()

                                          if (c.length >= 5)
                                            fetchSingleCedula(c)
                                        }}
                                        placeholder="Ej: V22546175"
                                        className={inputClass(
                                          row._validation.cedula?.isValid ??
                                            true
                                        )}
                                      />

                                      {row._validation.cedula?.isValid ===
                                        false && (
                                        <p className="mt-0.5 text-xs text-amber-700">
                                          {OBSERVACIONES_POR_CAMPO.cedula ??
                                            'No cliente'}
                                        </p>
                                      )}
                                    </td>

                                    <td className="border p-2">
                                      <input
                                        type="text"
                                        value={row.fecha_pago}
                                        onChange={e =>
                                          updateCellValue(
                                            row,
                                            'fecha_pago',
                                            e.target.value
                                          )
                                        }
                                        onBlur={() => {
                                          const c =
                                            cedulaLookupParaFila(
                                              row.cedula || '',
                                              row.numero_documento || ''
                                            ) || (row.cedula || '').trim()

                                          if (c.length >= 5)
                                            fetchSingleCedula(c)
                                        }}
                                        placeholder="DD/MM/YYYY"
                                        className={inputClass(
                                          row._validation.fecha_pago?.isValid ??
                                            true
                                        )}
                                      />

                                      {row._validation.fecha_pago?.isValid ===
                                        false && (
                                        <p className="mt-0.5 text-xs text-amber-700">
                                          {OBSERVACIONES_POR_CAMPO.fecha_pago ??
                                            'No Fecha'}
                                        </p>
                                      )}
                                    </td>

                                    <td className="border p-2">
                                      <input
                                        type="number"
                                        value={row.monto_pagado || ''}
                                        onChange={e =>
                                          updateCellValue(
                                            row,
                                            'monto_pagado',
                                            e.target.value
                                          )
                                        }
                                        className={inputClass(
                                          row._validation.monto_pagado
                                            ?.isValid ?? true
                                        )}
                                      />

                                      {row._validation.monto_pagado?.isValid ===
                                        false && (
                                        <p className="mt-0.5 text-xs text-amber-700">
                                          {OBSERVACIONES_POR_CAMPO.monto_pagado ??
                                            'Monto inválido'}
                                        </p>
                                      )}
                                    </td>

                                    <td className="border p-2">
                                      <input
                                        type="text"
                                        value={row.numero_documento}
                                        onChange={e =>
                                          updateCellValue(
                                            row,
                                            'numero_documento',
                                            e.target.value
                                          )
                                        }
                                        className={inputClass(
                                          row._validation.numero_documento
                                            ?.isValid !== false
                                        )}
                                        placeholder="Cualquier formato (ej. 740087…, BS./REF, con € $)"
                                        title="Cualquier formato aceptado. Solo no duplicados."
                                      />

                                      {row._validation.numero_documento
                                        ?.isValid === false && (
                                        <p className="mt-0.5 text-xs text-amber-700">
                                          {OBSERVACIONES_POR_CAMPO.numero_documento ??
                                            'Duplicado Excel'}
                                        </p>
                                      )}
                                    </td>

                                    <td className="border p-2">
                                      <div className="flex flex-col gap-1.5">
                                        <div className="min-w-0">
                                          <p className="mb-0.5 text-[10px] font-medium leading-tight text-gray-600">
                                            Préstamo destino (esta fila)
                                          </p>

                                          {tieneCreditos ? (
                                            <>
                                              <Select
                                                key={`credito-${row._rowIndex}-${prestamosActivos.length}-${row.prestamo_id ?? 'n'}`}
                                                value={valorCredito}
                                                onValueChange={v =>
                                                  updateCellValue(
                                                    row,
                                                    'prestamo_id',
                                                    v
                                                  )
                                                }
                                              >
                                                <SelectTrigger className="h-8 text-xs">
                                                  <SelectValue placeholder="Seleccionar crédito" />
                                                </SelectTrigger>

                                                <SelectContent>
                                                  <SelectItem value="none">
                                                    - Seleccionar -
                                                  </SelectItem>

                                                  {prestamosActivos.map(p => (
                                                    <SelectItem
                                                      key={p.id}
                                                      value={String(p.id)}
                                                    >
                                                      Crédito #{p.id}
                                                    </SelectItem>
                                                  ))}
                                                </SelectContent>
                                              </Select>

                                              {prestamosActivos.length > 1 &&
                                                valorCredito === 'none' && (
                                                  <p className="mt-0.5 text-xs text-amber-700">
                                                    {OBSERVACIONES_POR_CAMPO.prestamo_id ??
                                                      'Crédito inválido'}
                                                  </p>
                                                )}
                                            </>
                                          ) : (
                                            <div className="flex flex-col gap-0.5">
                                              <div className="flex items-center gap-1">
                                                {cedulaLookup &&
                                                cedulasBuscando.has(
                                                  cedulaLookup
                                                ) ? (
                                                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                                                ) : cedulaLookup &&
                                                  cedulaLookup.length >= 5 ? (
                                                  <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="h-7 px-2 text-xs"
                                                    onClick={() =>
                                                      fetchSingleCedula(
                                                        cedulaLookup
                                                      )
                                                    }
                                                    disabled={
                                                      serviceStatus ===
                                                      'offline'
                                                    }
                                                  >
                                                    <Search className="mr-1 h-3 w-3" />
                                                    Buscar
                                                  </Button>
                                                ) : null}

                                                {(!cedulaLookup ||
                                                  cedulaLookup.length < 5) && (
                                                  <span className="text-xs text-gray-400">
                                                    -
                                                  </span>
                                                )}
                                              </div>

                                              {cedulaLookup &&
                                                cedulaLookup.length >= 5 &&
                                                !tieneCreditos && (
                                                  <p className="mt-0.5 text-xs text-amber-700">
                                                    {OBSERVACIONES_POR_CAMPO.prestamo_id ??
                                                      'Crédito inválido'}
                                                  </p>
                                                )}
                                            </div>
                                          )}
                                        </div>

                                        <PrestamoDuplicadoEnBdBloque
                                          row={row}
                                        />
                                      </div>
                                    </td>

                                    <td className="border p-2">
                                      <Select
                                        value={row.conciliado ? 'si' : 'no'}
                                        onValueChange={v =>
                                          updateCellValue(row, 'conciliado', v)
                                        }
                                      >
                                        <SelectTrigger className="h-8 text-xs">
                                          <SelectValue />
                                        </SelectTrigger>

                                        <SelectContent>
                                          <SelectItem value="no">No</SelectItem>

                                          <SelectItem value="si">Sí</SelectItem>
                                        </SelectContent>
                                      </Select>

                                      {row._validation.conciliado?.isValid ===
                                        false && (
                                        <p className="mt-0.5 text-xs text-amber-700">
                                          {OBSERVACIONES_POR_CAMPO.conciliado ??
                                            'Conciliación inválida'}
                                        </p>
                                      )}
                                    </td>

                                    <td className="border p-2">
                                      {savedRows.has(row._rowIndex) ? (
                                        <div className="flex items-center text-sm text-green-600">
                                          <CheckCircle className="mr-1 h-4 w-4" />
                                          Guardado
                                        </div>
                                      ) : duplicadosPendientesRevisar.has(
                                          row._rowIndex
                                        ) ? (
                                        <div className="flex flex-col gap-1">
                                          <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() =>
                                              sendToRevisarPagos(row, () =>
                                                navigate('/pagos?revisar=1')
                                              )
                                            }
                                            disabled={
                                              savingProgress[row._rowIndex] ||
                                              serviceStatus === 'offline'
                                            }
                                            className="h-8 w-8 shrink-0 border-amber-300 p-0 text-amber-700 hover:bg-amber-50"
                                            title={
                                              row._validation.numero_documento
                                                ?.message ||
                                              'Documento duplicado - enviar a Revisar Pagos para confirmar uno a uno'
                                            }
                                          >
                                            {savingProgress[row._rowIndex] ? (
                                              <>
                                                <Loader2
                                                  className="h-3.5 w-3.5 animate-spin"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Enviando
                                                </span>
                                              </>
                                            ) : (
                                              <>
                                                <Search
                                                  className="h-3.5 w-3.5"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Revisar Pagos
                                                </span>
                                              </>
                                            )}
                                          </Button>

                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() =>
                                              saveIndividualPago(row)
                                            }
                                            disabled={
                                              savingProgress[row._rowIndex] ||
                                              serviceStatus === 'offline'
                                            }
                                            className="h-8 w-8 shrink-0 p-0 text-gray-600"
                                            title="Cambie el documento o intente guardar de nuevo"
                                          >
                                            <Save
                                              className="h-3.5 w-3.5"
                                              aria-hidden
                                            />
                                            <span className="sr-only">
                                              Guardar de nuevo
                                            </span>
                                          </Button>
                                        </div>
                                      ) : !row._hasErrors ? (
                                        <div className="flex flex-col gap-1">
                                          <Button
                                            size="sm"
                                            onClick={() =>
                                              saveIndividualPago(row)
                                            }
                                            disabled={
                                              savingProgress[row._rowIndex] ||
                                              serviceStatus === 'offline'
                                            }
                                            className="h-8 w-8 shrink-0 bg-green-600 p-0 text-white hover:bg-green-700"
                                            title="Guardar esta fila"
                                          >
                                            {savingProgress[row._rowIndex] ? (
                                              <>
                                                <Loader2
                                                  className="h-3.5 w-3.5 animate-spin"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Guardando
                                                </span>
                                              </>
                                            ) : (
                                              <>
                                                <Save
                                                  className="h-3.5 w-3.5"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Guardar
                                                </span>
                                              </>
                                            )}
                                          </Button>

                                          {(!tieneCreditos ||
                                            prestamosActivos.length > 1) && (
                                            <Button
                                              size="sm"
                                              variant="outline"
                                              onClick={() =>
                                                sendToRevisarPagos(row, () =>
                                                  navigate('/pagos?revisar=1')
                                                )
                                              }
                                              disabled={
                                                savingProgress[row._rowIndex] ||
                                                serviceStatus === 'offline'
                                              }
                                              className="h-8 w-8 shrink-0 border-amber-300 p-0 text-amber-700 hover:bg-amber-50"
                                              title={
                                                prestamosActivos.length > 1
                                                  ? 'Enviar a Revisar Pagos para asignar el crédito correcto'
                                                  : 'Enviar a Revisar Pagos'
                                              }
                                            >
                                              {savingProgress[row._rowIndex] ? (
                                                <>
                                                  <Loader2
                                                    className="h-3.5 w-3.5 animate-spin"
                                                    aria-hidden
                                                  />
                                                  <span className="sr-only">
                                                    Enviando
                                                  </span>
                                                </>
                                              ) : (
                                                <>
                                                  <Search
                                                    className="h-3.5 w-3.5"
                                                    aria-hidden
                                                  />
                                                  <span className="sr-only">
                                                    Revisar Pagos
                                                  </span>
                                                </>
                                              )}
                                            </Button>
                                          )}
                                        </div>
                                      ) : (
                                        <div className="flex flex-col gap-1">
                                          <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() =>
                                              sendToRevisarPagos(row, () =>
                                                navigate('/pagos?revisar=1')
                                              )
                                            }
                                            disabled={
                                              savingProgress[row._rowIndex] ||
                                              serviceStatus === 'offline'
                                            }
                                            className="h-8 w-8 shrink-0 border-amber-300 p-0 text-amber-700 hover:bg-amber-50"
                                            title={
                                              row._validation.numero_documento
                                                ?.message ||
                                              'Enviar a Revisar Pagos'
                                            }
                                          >
                                            {savingProgress[row._rowIndex] ? (
                                              <>
                                                <Loader2
                                                  className="h-3.5 w-3.5 animate-spin"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Enviando
                                                </span>
                                              </>
                                            ) : (
                                              <>
                                                <Search
                                                  className="h-3.5 w-3.5"
                                                  aria-hidden
                                                />
                                                <span className="sr-only">
                                                  Revisar Pagos
                                                </span>
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
                </>
              )}{' '}
              {/* Fin comentario tabla antigua */}
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
              className={`flex max-w-sm items-center justify-between gap-2 rounded-lg border-l-4 p-4 shadow-lg ${
                t.type === 'error'
                  ? 'border-red-500 bg-red-50 text-red-800'
                  : t.type === 'warning'
                    ? 'border-yellow-500 bg-yellow-50 text-yellow-800'
                    : t.type === 'info'
                      ? 'border-sky-500 bg-sky-50 text-sky-900'
                      : 'border-green-500 bg-green-50 text-green-800'
              }`}
            >
              <span className="flex-1">{t.message}</span>

              <button
                type="button"
                onClick={() => removeToast(t.id)}
                className="flex-shrink-0 rounded p-1 opacity-70 hover:bg-black/10 hover:opacity-100"
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
