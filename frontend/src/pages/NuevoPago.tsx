import React, { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CreditCard,
  Upload,
  FileSpreadsheet,
  Download,
  X,
  Save,
  AlertCircle,
  CheckCircle,
  Calendar,
  DollarSign,
  FileText,
  User,
  Building2,
  RefreshCw,
  Eye,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { AlertWithIcon } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { pagoService, type PagoCreate } from '@/services/pagoService'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import * as XLSX from 'xlsx'

interface ExcelRow {
  cedula_cliente: string
  fecha_pago: string
  monto_pagado: string
  numero_documento: string
  notas?: string
  [key: string]: any // Agregar index signature
}

interface ValidatedRow extends ExcelRow {
  isValid: boolean
  errors: { [key: string]: string }
  originalIndex: number
}

export function NuevoPago() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [modo, setModo] = useState<'formulario' | 'excel'>('formulario')
  const [isSaving, setIsSaving] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingProgress, setProcessingProgress] = useState(0)
  
  // Estados para formulario
  const [formData, setFormData] = useState<PagoCreate>({
    cedula_cliente: '',
    fecha_pago: new Date().toISOString().split('T')[0],
    monto_pagado: 0,
    numero_documento: '',
    notas: ''
  })
  const [formErrors, setFormErrors] = useState<{ [key: string]: string }>({})
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  
  // Estados para Excel
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [validatedData, setValidatedData] = useState<ValidatedRow[]>([])
  const [validationSummary, setValidationSummary] = useState({ total: 0, valid: 0, errors: 0 })

  // ============================================
  // HANDLERS FORMULARIO
  // ============================================

  const handleFormChange = (field: keyof PagoCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Limpiar error del campo
    if (formErrors[field]) {
      setFormErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const validateForm = async (): Promise<boolean> => {
    const errors: { [key: string]: string } = {}

    // Validar cédula
    if (!formData.cedula_cliente.trim()) {
      errors.cedula_cliente = 'Cédula es requerida'
    } else {
      try {
        const validation = await pagoService.validarCedula(formData.cedula_cliente)
        if (!validation.valido) {
          errors.cedula_cliente = validation.mensaje || 'Cédula inválida'
        }
      } catch (error) {
        errors.cedula_cliente = 'Error validando cédula'
      }
    }

    // Validar fecha
    if (!formData.fecha_pago) {
      errors.fecha_pago = 'Fecha es requerida'
    } else {
      try {
        const validation = await pagoService.validarFecha(formData.fecha_pago)
        if (!validation.valido) {
          errors.fecha_pago = validation.mensaje || 'Fecha inválida'
        }
      } catch (error) {
        errors.fecha_pago = 'Error validando fecha'
      }
    }

    // Validar monto
    if (!formData.monto_pagado || formData.monto_pagado <= 0) {
      errors.monto_pagado = 'Monto debe ser mayor a 0'
    } else {
      try {
        const validation = await pagoService.validarMonto(formData.monto_pagado)
        if (!validation.valido) {
          errors.monto_pagado = validation.mensaje || 'Monto inválido'
        }
      } catch (error) {
        errors.monto_pagado = 'Error validando monto'
      }
    }

    // Validar número de documento
    if (!formData.numero_documento.trim()) {
      errors.numero_documento = 'Número de documento es requerido'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSaveForm = async () => {
    const isValid = await validateForm()
    if (!isValid) return

    setIsSaving(true)
    try {
      await pagoService.crearPago(formData)
      toast.success('✅ Pago creado exitosamente')
      queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
      navigate('/pagos')
    } catch (error) {
      toast.error('❌ Error al crear el pago')
      console.error('Error creando pago:', error)
    } finally {
      setIsSaving(false)
    }
  }

  // ============================================
  // HANDLERS EXCEL
  // ============================================

  const handleDownloadTemplate = async () => {
    try {
      await pagoService.descargarTemplateConciliacion()
      toast.success('✅ Template descargado exitosamente')
    } catch (error) {
      toast.error('❌ Error al descargar el template')
    }
  }

  const validateField = async (fieldName: string, value: any): Promise<string | null> => {
    if (value === undefined || value === null || value === '') {
      const requiredFields = ['cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento']
      if (requiredFields.includes(fieldName)) {
        return 'Campo requerido'
      }
      return null
    }

    const stringValue = String(value).trim()

    switch (fieldName) {
      case 'cedula_cliente':
        if (!stringValue) return 'Cédula requerida'
        try {
          const validation = await pagoService.validarCedula(stringValue)
          if (!validation.valido) return validation.mensaje || 'Cédula inválida'
        } catch (error) {
          return 'Error validando cédula'
        }
        break
      case 'fecha_pago':
        if (!stringValue) return 'Fecha requerida'
        try {
          const validation = await pagoService.validarFecha(stringValue)
          if (!validation.valido) return validation.mensaje || 'Fecha inválida'
        } catch (error) {
          return 'Error validando fecha'
        }
        break
      case 'monto_pagado':
        if (!stringValue) return 'Monto requerido'
        const amount = parseFloat(stringValue)
        if (isNaN(amount) || amount <= 0) return 'Monto inválido'
        try {
          const validation = await pagoService.validarMonto(amount)
          if (!validation.valido) return validation.mensaje || 'Monto inválido'
        } catch (error) {
          return 'Error validando monto'
        }
        break
      case 'numero_documento':
        if (!stringValue) return 'Número de documento requerido'
        break
    }
    return null
  }

  const processExcelFile = async (file: File) => {
    setIsProcessing(true)
    setProcessingProgress(0)
    setUploadedFile(file)
    setExcelData([])
    setValidatedData([])
    setValidationSummary({ total: 0, valid: 0, errors: 0 })

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const data = e.target?.result
        const workbook = XLSX.read(data, { type: 'binary' })
        const sheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[sheetName]
        const json: ExcelRow[] = XLSX.utils.sheet_to_json(worksheet)

        setExcelData(json)
        setProcessingProgress(50)

        // Validar cada fila
        const validatedRows: ValidatedRow[] = []
        let validCount = 0
        let errorCount = 0

        for (let i = 0; i < json.length; i++) {
          const row = json[i]
          const errors: { [key: string]: string } = {}
          let rowIsValid = true

          for (const key in row) {
            const error = await validateField(key, row[key])
            if (error) {
              errors[key] = error
              rowIsValid = false
            }
          }
          validatedRows.push({ ...row, isValid: rowIsValid, errors: errors, originalIndex: i })
          if (rowIsValid) {
            validCount++
          } else {
            errorCount++
          }
          setProcessingProgress(50 + Math.floor((i / json.length) * 50))
        }

        setValidatedData(validatedRows)
        setValidationSummary({ total: json.length, valid: validCount, errors: errorCount })
        toast.success(`📊 ${json.length} registros procesados. ${validCount} válidos, ${errorCount} con errores.`)

      } catch (error) {
        console.error('❌ Error procesando archivo Excel:', error)
        toast.error('Error al procesar el archivo Excel. Asegúrate de usar el formato correcto.')
      } finally {
        setIsProcessing(false)
        setProcessingProgress(0)
      }
    }
    reader.readAsBinaryString(file)
  }

  const handleFileInputChange = (event: any) => {
    const file = event.target.files?.[0]
    if (file) {
      processExcelFile(file)
    }
  }

  const handleCellChange = async (index: number, field: keyof ExcelRow, value: any) => {
    const updatedValidatedData = [...validatedData]
    const rowToUpdate = updatedValidatedData[index]
    
    rowToUpdate[field] = value
    
    const error = await validateField(field as string, value)
    if (error) {
      rowToUpdate.errors[field as string] = error
    } else {
      delete rowToUpdate.errors[field as string]
    }

    rowToUpdate.isValid = Object.keys(rowToUpdate.errors).length === 0

    setValidatedData(updatedValidatedData)

    const newValidCount = updatedValidatedData.filter(row => row.isValid).length
    const newErrorCount = updatedValidatedData.length - newValidCount
    setValidationSummary({ total: updatedValidatedData.length, valid: newValidCount, errors: newErrorCount })
  }

  const handleSaveAllValid = async () => {
    setIsSaving(true)
    const validClients = validatedData.filter(row => row.isValid)
    let successCount = 0
    let errorCount = 0

    for (const clientData of validClients) {
      try {
        const pagoFormatted: PagoCreate = {
          cedula_cliente: clientData.cedula_cliente,
          fecha_pago: clientData.fecha_pago,
          monto_pagado: parseFloat(clientData.monto_pagado),
          numero_documento: clientData.numero_documento,
          notas: clientData.notas || undefined
        }
        await pagoService.crearPago(pagoFormatted)
        successCount++
      } catch (error) {
        console.error('Error guardando pago desde Excel:', clientData.cedula_cliente, error)
        errorCount++
      }
    }

    setIsSaving(false)
    if (successCount > 0) {
      toast.success(`✅ ${successCount} pagos guardados exitosamente.`)
      queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
      queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
      navigate('/pagos')
    }
    if (errorCount > 0) {
      toast.error(`❌ ${errorCount} pagos no pudieron ser guardados. Revisa los logs.`)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <CreditCard className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Nuevo Pago</h1>
            <p className="text-gray-600">Crear nuevo pago o carga masiva</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => navigate('/pagos')}
            variant="outline"
            size="sm"
          >
            <X className="h-4 w-4 mr-2" />
            Cancelar
          </Button>
        </div>
      </div>

      {/* Selector de Modo */}
      <Card>
        <CardHeader>
          <CardTitle>Seleccionar Modo de Entrada</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button
              variant={modo === 'formulario' ? 'default' : 'outline'}
              onClick={() => setModo('formulario')}
              className="h-20 flex flex-col items-center justify-center space-y-2"
            >
              <FileText className="h-6 w-6" />
              <span>Formulario Web</span>
              <span className="text-xs text-gray-500">Un pago a la vez</span>
            </Button>
            <Button
              variant={modo === 'excel' ? 'default' : 'outline'}
              onClick={() => setModo('excel')}
              className="h-20 flex flex-col items-center justify-center space-y-2"
            >
              <FileSpreadsheet className="h-6 w-6" />
              <span>Carga Masiva Excel</span>
              <span className="text-xs text-gray-500">Múltiples pagos</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Formulario Web */}
      <AnimatePresence>
        {modo === 'formulario' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <FileText className="h-5 w-5" />
                  <span>Formulario de Pago</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Cédula del Cliente *</label>
                    <Input
                      placeholder="V12345678"
                      value={formData.cedula_cliente}
                      onChange={(e) => handleFormChange('cedula_cliente', e.target.value)}
                      className={formErrors.cedula_cliente ? 'border-red-500' : ''}
                    />
                    {formErrors.cedula_cliente && (
                      <p className="text-sm text-red-600 mt-1">{formErrors.cedula_cliente}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Fecha de Pago *</label>
                    <Input
                      type="date"
                      value={formData.fecha_pago}
                      onChange={(e) => handleFormChange('fecha_pago', e.target.value)}
                      className={formErrors.fecha_pago ? 'border-red-500' : ''}
                    />
                    {formErrors.fecha_pago && (
                      <p className="text-sm text-red-600 mt-1">{formErrors.fecha_pago}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Monto Pagado *</label>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={formData.monto_pagado || ''}
                      onChange={(e) => handleFormChange('monto_pagado', parseFloat(e.target.value) || 0)}
                      className={formErrors.monto_pagado ? 'border-red-500' : ''}
                    />
                    {formErrors.monto_pagado && (
                      <p className="text-sm text-red-600 mt-1">{formErrors.monto_pagado}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Número de Documento *</label>
                    <Input
                      placeholder="DOC001234"
                      value={formData.numero_documento}
                      onChange={(e) => handleFormChange('numero_documento', e.target.value)}
                      className={formErrors.numero_documento ? 'border-red-500' : ''}
                    />
                    {formErrors.numero_documento && (
                      <p className="text-sm text-red-600 mt-1">{formErrors.numero_documento}</p>
                    )}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Notas</label>
                  <textarea
                    className="w-full p-3 border border-gray-300 rounded-md resize-none"
                    rows={3}
                    placeholder="Observaciones adicionales..."
                    value={formData.notas || ''}
                    onChange={(e) => handleFormChange('notas', e.target.value)}
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <Button
                    onClick={handleSaveForm}
                    disabled={isSaving}
                    className="min-w-[120px]"
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Guardar Pago
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Carga Masiva Excel */}
      <AnimatePresence>
        {modo === 'excel' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <FileSpreadsheet className="h-5 w-5" />
                    <span>Carga Masiva Excel</span>
                  </div>
                  <Button
                    onClick={handleDownloadTemplate}
                    variant="outline"
                    size="sm"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Template
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!uploadedFile ? (
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                    <Upload className="h-16 w-16 mx-auto text-gray-400 mb-4" />
                    <p className="text-lg text-gray-700 mb-2">Arrastra tu archivo Excel aquí</p>
                    <p className="text-sm text-gray-500 mb-4">o haz clic para seleccionar</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileInputChange}
                      className="hidden"
                    />
                    <Button onClick={() => fileInputRef.current?.click()} disabled={isProcessing}>
                      Seleccionar Archivo
                    </Button>
                    {isProcessing && (
                      <Progress value={processingProgress} className="w-full mt-4" />
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      <Card className="text-center">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Total Registros</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{validationSummary.total}</div>
                        </CardContent>
                      </Card>
                      <Card className="text-center border-green-400 bg-green-50">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium text-green-700">Válidos</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold text-green-800">{validationSummary.valid}</div>
                        </CardContent>
                      </Card>
                      <Card className="text-center border-red-400 bg-red-50">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium text-red-700">Con Errores</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold text-red-800">{validationSummary.errors}</div>
                        </CardContent>
                      </Card>
                    </div>

                    {validationSummary.errors > 0 && (
                      <AlertWithIcon
                        variant="destructive"
                        title="Errores de Validación"
                        description={`Se encontraron ${validationSummary.errors} registros con errores. Por favor, corrígelos en la tabla de abajo.`}
                      />
                    )}

                    {/* Tabla de Previsualización y Edición */}
                    <div className="overflow-x-auto max-h-96 border rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fila</th>
                            {Object.keys(validatedData[0] || {}).filter(key => !['isValid', 'errors', 'originalIndex'].includes(key)).map(key => (
                              <th key={key} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {key.replace(/_/g, ' ')}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {validatedData.map((row, rowIndex) => (
                            <tr key={rowIndex} className={row.isValid ? 'hover:bg-green-50' : 'bg-red-50 hover:bg-red-100'}>
                              <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                                {row.originalIndex + 2}
                              </td>
                              {Object.keys(row).filter(key => !['isValid', 'errors', 'originalIndex'].includes(key)).map(key => (
                                <td key={key} className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                  <input
                                    type="text"
                                    value={String(row[key as keyof ExcelRow] || '')}
                                    onChange={(e) => handleCellChange(rowIndex, key as keyof ExcelRow, e.target.value)}
                                    className={`w-full p-1 border rounded-md text-sm ${row.errors[key] ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'}`}
                                  />
                                  {row.errors[key] && (
                                    <p className="text-xs text-red-600 mt-1">ERROR: {row.errors[key]}</p>
                                  )}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <Button
                      onClick={handleSaveAllValid}
                      disabled={validationSummary.errors > 0 || isSaving || validationSummary.total === 0}
                      className="w-full"
                    >
                      {isSaving ? 'Guardando...' : 'Guardar Pagos Válidos'}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
