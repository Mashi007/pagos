import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SearchableSelect } from '@/components/ui/searchable-select'
import { ConfirmacionDuplicadoModal } from './ConfirmacionDuplicadoModal'
import * as XLSX from 'xlsx'
import { concesionarioService, type Concesionario } from '@/services/concesionarioService'
import { analistaService, type Analista } from '@/services/analistaService'
import { modeloVehiculoService, type ModeloVehiculo } from '@/services/modeloVehiculoService'
import { clienteService } from '@/services/clienteService'
import { useQueryClient } from '@tanstack/react-query'

interface ExcelData {
  cedula: string
  nombres: string  // ✅ CARGA MASIVA: Solo 2 palabras exactamente (nombre + apellido)
  telefono: string
  email: string
  direccion: string
  fecha_nacimiento: string
  ocupacion: string
  modelo_vehiculo: string | null
  concesionario: string | null
  analista: string | null
  total_financiamiento: string
  cuota_inicial: string
  numero_amortizaciones: string
  modalidad_pago: string
  fecha_entrega: string
  estado: string
  activo: string
  notas: string
}

interface ValidationResult {
  isValid: boolean
  message?: string
  normalizedValue?: string
}

interface ExcelRow extends ExcelData {
  _rowIndex: number
  _validation: { [key: string]: ValidationResult }
  _hasErrors: boolean
}

interface ExcelUploaderProps {
  onClose: () => void
  onDataProcessed?: (data: ExcelRow[]) => void
  onSuccess?: () => void
}

export function ExcelUploader({ onClose, onDataProcessed, onSuccess }: ExcelUploaderProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Estados para listas desplegables
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [analistas, setAnalistas] = useState<Analista[]>([])
  const [modelosVehiculos, setModelosVehiculos] = useState<ModeloVehiculo[]>([])

  // Estado para tracking de errores en dropdowns
  const [dropdownErrors, setDropdownErrors] = useState<{[key: string]: boolean}>({})

  // Estado para notificaciones toast con tracking de violaciones
  const [toasts, setToasts] = useState<Array<{
    id: string
    type: 'error' | 'warning' | 'success'
    message: string
    suggestion?: string
    field: string
    rowIndex: number
  }>>([])

  // Estado para tracking de violaciones por fila completa
  const [violationTracker, setViolationTracker] = useState<{[key: string]: {
    violationCount: number
    lastRowData: string
  }}>({})

  // Estado para sistema de guardado híbrido
  const [savedClients, setSavedClients] = useState<Set<number>>(new Set())
  const [isSavingIndividual, setIsSavingIndividual] = useState(false)
  const [savingProgress, setSavingProgress] = useState<{[key: number]: boolean}>({})
  const [serviceStatus, setServiceStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [showOnlyPending, setShowOnlyPending] = useState(false)

  // Estado para modal de confirmación de duplicados
  const [showConfirmacionModal, setShowConfirmacionModal] = useState(false)
  const [clienteDuplicado, setClienteDuplicado] = useState<{
    existente: any
    nuevo: any
    rowIndex: number
  } | null>(null)

  // Función para manejar notificaciones de validación por fila completa
  const handleRowValidationNotification = (rowIndex: number, rowData: ExcelRow) => {
    const trackerKey = `row-${rowIndex}`
    const currentTracker = violationTracker[trackerKey] || {
      violationCount: 0,
      lastRowData: ''
    }

    // Crear hash de los datos de la fila para detectar cambios
    const rowDataHash = JSON.stringify({
      cedula: rowData.cedula,
      nombres: rowData.nombres,  // ✅ nombres unificados
      telefono: rowData.telefono,
      email: rowData.email,
      direccion: rowData.direccion,
      fecha_nacimiento: rowData.fecha_nacimiento,
      ocupacion: rowData.ocupacion,
      modelo_vehiculo: rowData.modelo_vehiculo,
      concesionario: rowData.concesionario,
      analista: rowData.analista
    })

    // Si los datos de la fila cambiaron, resetear el contador
    if (currentTracker.lastRowData !== rowDataHash) {
      setViolationTracker(prev => ({
        ...prev,
        [trackerKey]: {
          violationCount: 0,
          lastRowData: rowDataHash
        }
      }))
      return
    }

    // Verificar si la fila tiene errores
    const hasErrors = rowData._hasErrors
    const errorFields = Object.entries(rowData._validation)
      .filter(([_, validation]) => !validation.isValid)
      .map(([field, _]) => field)

    if (!hasErrors) {
      // Fila válida - mostrar notificación de éxito
      const successToast = {
        id: `success-row-${rowIndex}-${Date.now()}`,
        type: 'success' as const,
        message: `Fila ${rowIndex + 1} es válida`,
        field: 'fila_completa',
        rowIndex
      }
      
      setToasts(prev => [...prev, successToast])
      
      // Limpiar tracker
      setViolationTracker(prev => ({
        ...prev,
        [trackerKey]: {
          violationCount: 0,
          lastRowData: rowDataHash
        }
      }))
      
      // Auto-remover notificación después de 3 segundos
      setTimeout(() => {
        setToasts(prev => prev.filter(toast => toast.id !== successToast.id))
      }, 3000)
      
    } else {
      // Fila con errores - incrementar contador
      const newViolationCount = currentTracker.violationCount + 1
      
      // Mostrar notificación solo en violaciones específicas: 1ra, 3ra, 6ta, 9na, 12va...
      const shouldShowNotification = newViolationCount === 1 || 
                                   newViolationCount === 3 || 
                                   newViolationCount === 6 || 
                                   newViolationCount === 9 || 
                                   newViolationCount === 12 ||
                                   (newViolationCount > 12 && newViolationCount % 3 === 0)
      
      if (shouldShowNotification) {
        const errorToast = {
          id: `error-row-${rowIndex}-${Date.now()}`,
          type: 'error' as const,
          message: `Fila ${rowIndex + 1}: Campos con errores: ${errorFields.join(', ')}`,
          suggestion: `Corrija los campos marcados en rojo para continuar`,
          field: 'fila_completa',
          rowIndex
        }
        
        setToasts(prev => [...prev, errorToast])
        
        // Auto-remover notificación después de 3 segundos
        setTimeout(() => {
          setToasts(prev => prev.filter(toast => toast.id !== errorToast.id))
        }, 3000)
      }
      
      // Actualizar contador de violaciones
      setViolationTracker(prev => ({
        ...prev,
        [trackerKey]: {
          violationCount: newViolationCount,
          lastRowData: rowDataHash
        }
      }))
    }
  }

  // Función para remover notificación manualmente
  const removeToast = (toastId: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== toastId))
  }

  // Cargar datos de configuración
  useEffect(() => {
    const cargarDatosConfiguracion = async () => {
      try {
        console.log('🔄 Cargando datos de configuración para ExcelUploader...')
        
        const [concesionariosData, analistasData, modelosData] = await Promise.all([
          concesionarioService.getConcesionarios(),
          analistaService.getAnalistas(),
          modeloVehiculoService.getModelosVehiculos()
        ])
        
        console.log('📊 Datos cargados para ExcelUploader:')
        console.log('  - Concesionarios:', concesionariosData.length)
        console.log('  - Analistas:', analistasData.length)
        console.log('  - Modelos:', modelosData.length)
        
        setConcesionarios(concesionariosData)
        setAnalistas(analistasData)
        setModelosVehiculos(modelosData)
        
        console.log('✅ Estados actualizados correctamente en ExcelUploader')
      } catch (error) {
        console.error('❌ Error cargando datos de configuración en ExcelUploader:', error)
      }
    }

    cargarDatosConfiguracion()
  }, [])

  // Validar dropdowns cuando cambien los datos de Excel
  useEffect(() => {
    if (excelData.length > 0) {
      console.log('🔄 Validando dropdowns al cambiar datos de Excel...')
      updateDropdownErrors(excelData)
    }
  }, [excelData])

  // Efecto para verificar estado del servicio al cargar
  useEffect(() => {
    checkServiceStatus()
    // Verificar cada 30 segundos
    const interval = setInterval(checkServiceStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  // 🔔 FUNCIONES PARA NOTIFICACIONES TOAST
  const addToast = (type: 'error' | 'warning' | 'success', message: string, suggestion?: string, field: string = 'general', rowIndex: number = -1) => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, type, message, suggestion, field, rowIndex }])
    
    // Auto-remover después de 3 segundos
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id))
    }, 3000)
  }

  // Limpiar notificaciones contradictorias
  const clearContradictoryToasts = () => {
    setToasts(prev => prev.filter(toast => 
      !toast.message.includes('guardado exitosamente') && 
      !toast.message.includes('agregado al Dashboard') &&
      !toast.message.includes('Redirigiendo')
    ))
  }

  // Manejar confirmación de cliente duplicado
  const handleConfirmarDuplicado = async (comentarios: string) => {
    if (!clienteDuplicado) return

    // ✅ CORRECCIÓN DEFINITIVA: Guardar rowIndex antes de limpiar clienteDuplicado
    const currentRowIndex = clienteDuplicado.rowIndex

    try {
      const row = excelData[currentRowIndex]
      const clienteData = {
        cedula: row.cedula,
        nombres: row.nombres,  // ✅ Ya unificados (nombres + apellidos)
        telefono: row.telefono,
        email: row.email,
        direccion: row.direccion,
        fecha_nacimiento: row.fecha_nacimiento,
        ocupacion: row.ocupacion,
        modelo_vehiculo: row.modelo_vehiculo || undefined,
        concesionario: row.concesionario || undefined,
        analista: row.analista || undefined,
        total_financiamiento: parseFloat(row.total_financiamiento) || 0,
        cuota_inicial: parseFloat(row.cuota_inicial) || 0,
        numero_amortizaciones: parseInt(row.numero_amortizaciones) || 0,
        modalidad_pago: row.modalidad_pago,
        fecha_entrega: row.fecha_entrega,
        estado: row.estado,
        activo: row.activo === 'TRUE',
        notas: row.notas
      }

      await clienteService.createClienteWithConfirmation(clienteData, comentarios)
      
      // Marcar como guardado
      setSavedClients(prev => new Set([...prev, currentRowIndex]))
      
      // Refrescar Dashboard de Clientes
      refreshDashboardClients()
      
      addToast('success', `Cliente ${row.nombres} creado con confirmación exitosamente`)
      
      // Eliminar la fila de la lista después de guardar exitosamente
      setExcelData(prev => prev.filter(r => r._rowIndex !== currentRowIndex))
      
      // Verificar si quedan filas pendientes
      const remainingRows = excelData.filter(r => r._rowIndex !== currentRowIndex)
      if (remainingRows.length === 0) {
        addToast('success', '🎉 ¡Todos los clientes han sido guardados exitosamente!')
        notifyDashboardUpdate(getSavedClientsCount())
        
        // Mostrar mensaje informativo sobre navegación automática
        addToast('success', '🔄 Redirigiendo al Dashboard de Clientes en 2 segundos...')
        
        // Navegar automáticamente al Dashboard de Clientes después de 2 segundos
        setTimeout(() => {
          // Cerrar el modal de Carga Masiva
          onClose()
          // Navegar directamente al Dashboard de Clientes
          navigate('/clientes')
        }, 2000)
      }
      
      // Limpiar estado del modal
      setClienteDuplicado(null)
      setShowConfirmacionModal(false)
      
    } catch (error: any) {
      console.error('Error confirmando cliente duplicado:', error)
      
      // Limpiar notificaciones anteriores para evitar contradicciones
      clearContradictoryToasts()
      
      // Manejar diferentes tipos de errores
      if (error.response?.status === 503) {
        addToast('error', '🚨 SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
      } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        addToast('error', '🚨 ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
      } else if (error.response?.status === 400) {
        addToast('error', `Error de validación: ${error.response?.data?.detail || error.message}`)
      } else if (error.response?.status >= 500) {
        addToast('error', 'Error del servidor. Contacta al administrador.')
      } else {
        addToast('error', `Error confirmando cliente: ${error.response?.data?.detail || error.message}`)
      }
    } finally {
      // ✅ CORRECCIÓN DEFINITIVA: Usar currentRowIndex en lugar de clienteDuplicado?.rowIndex
      setSavingProgress(prev => ({ ...prev, [currentRowIndex]: false }))
    }
  }

  // Verificar estado del servicio
  const checkServiceStatus = async () => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      
      // Usar endpoint raíz que sabemos que funciona
      const response = await fetch('/', { 
        method: 'HEAD',
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      setServiceStatus(response.ok ? 'online' : 'offline')
    } catch (error) {
      setServiceStatus('offline')
    }
  }

  // 🔄 FUNCIONES PARA SISTEMA DE GUARDADO HÍBRIDO
  const isClientValid = (row: ExcelRow): boolean => {
    // Usar el mismo sistema de validación que los campos visuales
    return !row._hasErrors
  }

  const getValidClients = (): ExcelRow[] => {
    return excelData.filter(row => isClientValid(row) && !savedClients.has(row._rowIndex))
  }

  // 📊 FUNCIONES PARA FILTRAR DATOS MOSTRADOS
  const getDisplayData = (): ExcelRow[] => {
    if (showOnlyPending) {
      return excelData.filter(row => !savedClients.has(row._rowIndex))
    }
    return excelData
  }

  const getPendingClients = (): ExcelRow[] => {
    return excelData.filter(row => !savedClients.has(row._rowIndex))
  }

  const getSavedClientsCount = (): number => {
    return savedClients.size
  }

  // 🔄 FUNCIONES PARA CONEXIÓN CON DASHBOARD
  const refreshDashboardClients = () => {
    // Invalidar cache de clientes para refrescar Dashboard
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-list'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
    
    console.log('🔄 Cache de Dashboard de Clientes invalidado')
  }

  const notifyDashboardUpdate = (clientCount: number) => {
    addToast('success', 
      `${clientCount} cliente${clientCount > 1 ? 's' : ''} agregado${clientCount > 1 ? 's' : ''} al Dashboard de Clientes`,
      'Los clientes ya están disponibles en la lista principal'
    )
  }

  const saveIndividualClient = async (row: ExcelRow): Promise<boolean> => {
    try {
      setSavingProgress(prev => ({ ...prev, [row._rowIndex]: true }))
      
      const clienteData = {
        cedula: row.cedula,
        nombres: row.nombres,  // ✅ Ya unificados (nombres + apellidos)
        telefono: row.telefono,
        email: row.email,
        direccion: row.direccion,
        fecha_nacimiento: row.fecha_nacimiento,
        ocupacion: row.ocupacion,
        modelo_vehiculo: row.modelo_vehiculo || undefined,
        concesionario: row.concesionario || undefined,
        analista: row.analista || undefined,
        total_financiamiento: parseFloat(row.total_financiamiento) || 0,
        cuota_inicial: parseFloat(row.cuota_inicial) || 0,
        numero_amortizaciones: parseInt(row.numero_amortizaciones) || 0,
        modalidad_pago: row.modalidad_pago,
        fecha_entrega: row.fecha_entrega,
        estado: row.estado,
        activo: row.activo === 'TRUE',
        notas: row.notas
      }

      try {
        await clienteService.createCliente(clienteData)
      } catch (error: any) {
        console.error('Error guardando cliente individual:', error)
        
        // Manejar error de cliente duplicado (CORREGIDO: usar la nueva estructura)
        if (error.response?.status === 409 && 
            error.response?.data?.detail?.error === 'CLIENTE_DUPLICADO') {
          const clienteExistente = error.response?.data?.detail?.cliente_existente
          
          // ✅ CORRECCIÓN CRÍTICA: Validar que clienteExistente existe antes del spread
          if (!clienteExistente) {
            console.error('❌ ERROR: clienteExistente es undefined en respuesta 409')
            console.error('❌ Respuesta completa:', error.response?.data)
            return false
          }
          
          setClienteDuplicado({
            existente: {
              ...clienteExistente,
              cedula: error.response?.data?.detail?.cedula || row.cedula
            },
            nuevo: {
              nombres: row.nombres,  // ✅ nombres unificados
              cedula: row.cedula,
              telefono: row.telefono,
              email: row.email
            },
            rowIndex: row._rowIndex
          })
          
          // ✅ LOGS ADICIONALES: Verificar estructura de datos antes de mostrar modal
          console.log('🔍 DEBUG - clienteExistente del backend:', clienteExistente)
          console.log('🔍 DEBUG - cedula del backend:', error.response?.data?.detail?.cedula)
          console.log('🔍 DEBUG - cedula de la fila:', row.cedula)
          console.log('🔍 DEBUG - clienteDuplicado establecido:', {
            existente: {
              ...clienteExistente,
              cedula: error.response?.data?.detail?.cedula || row.cedula
            },
            nuevo: {
              nombres: row.nombres,  // ✅ nombres unificados
              cedula: row.cedula,
              telefono: row.telefono,
              email: row.email
            },
            rowIndex: row._rowIndex
          })
          
          setShowConfirmacionModal(true)
          return false
        }
        
        // Manejar error 503 - Servicio no disponible
        if (error.response?.status === 503) {
          addToast('error', '🚨 SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
          return false
        }
        
        // Manejar otros errores de red
        if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
          addToast('error', '🚨 ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
          return false
        }
        
        // Manejar errores de validación
        if (error.response?.status === 400) {
          addToast('error', `Error de validación: ${error.response?.data?.detail || error.message}`)
          return false
        }
        
        // Manejar otros errores del servidor
        if (error.response?.status >= 500) {
          addToast('error', 'Error del servidor. Contacta al administrador.')
          return false
        }
        
        // Error genérico
        addToast('error', `Error guardando cliente: ${error.response?.data?.detail || error.message}`)
        return false
      }
      
      // Marcar como guardado
      setSavedClients(prev => new Set([...prev, row._rowIndex]))
      
      // Refrescar Dashboard de Clientes
      refreshDashboardClients()
      
      addToast('success', `Cliente ${row.nombres} guardado exitosamente`)
      
      // Eliminar la fila de la lista después de guardar exitosamente
      setExcelData(prev => prev.filter(r => r._rowIndex !== row._rowIndex))
      
      // Verificar si quedan filas pendientes
      const remainingRows = excelData.filter(r => r._rowIndex !== row._rowIndex)
      if (remainingRows.length === 0) {
        addToast('success', '🎉 ¡Todos los clientes han sido guardados exitosamente!')
        notifyDashboardUpdate(getSavedClientsCount())
        
        // Mostrar mensaje informativo sobre navegación automática
        addToast('success', '🔄 Redirigiendo al Dashboard de Clientes en 2 segundos...')
        
        // Navegar automáticamente al Dashboard de Clientes después de 2 segundos
        setTimeout(() => {
          // Cerrar el modal de Carga Masiva
          onClose()
          // Navegar directamente al Dashboard de Clientes
          navigate('/clientes')
        }, 2000)
      }
      
      return true
      
    } catch (error: any) {
      console.error('Error guardando cliente individual:', error)
      
      // Limpiar notificaciones anteriores para evitar contradicciones
      clearContradictoryToasts()
      
      // Manejar diferentes tipos de errores
      if (error.response?.status === 503) {
        addToast('error', '🚨 SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
      } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        addToast('error', '🚨 ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
      } else if (error.response?.status === 400) {
        addToast('error', `Error de validación: ${error.response?.data?.detail || error.message}`)
      } else if (error.response?.status >= 500) {
        addToast('error', 'Error del servidor. Contacta al administrador.')
      } else {
        addToast('error', `Error guardando cliente: ${error.response?.data?.detail || error.message}`)
      }
      
      return false
    } finally {
      setSavingProgress(prev => ({ ...prev, [row._rowIndex]: false }))
    }
  }

  const saveAllValidClients = async (): Promise<void> => {
    const validClients = getValidClients()
    
    if (validClients.length === 0) {
      addToast('warning', 'No hay clientes válidos para guardar')
      return
    }

    setIsSavingIndividual(true)
    
    try {
      // Guardar todos los clientes válidos uno por uno
      let successful = 0
      let failed = 0
      const successfulRowIndexes: number[] = []
      
      for (const client of validClients) {
        try {
          const result = await saveIndividualClient(client)
          if (result === true) {
            successful++
            successfulRowIndexes.push(client._rowIndex)
          } else {
            failed++
          }
        } catch (error) {
          failed++
          console.error('Error guardando cliente:', error)
        }
      }
      
      if (successful > 0) {
        // Solo mostrar notificación de éxito si realmente se guardaron
        addToast('success', `${successful} clientes guardados exitosamente`)
        
        // Refrescar Dashboard de Clientes
        refreshDashboardClients()
        notifyDashboardUpdate(successful)
        
        // Eliminar las filas guardadas de la lista
        setExcelData(prev => prev.filter(r => !successfulRowIndexes.includes(r._rowIndex)))
        
        // Solo navegar si realmente se guardaron clientes
        if (successful > 0) {
          // Mostrar mensaje informativo sobre navegación automática
          addToast('success', '🔄 Redirigiendo al Dashboard de Clientes en 2 segundos...')
          
          // Navegar automáticamente al Dashboard de Clientes después de 2 segundos
          setTimeout(() => {
            // Cerrar el modal de Carga Masiva
            onClose()
            // Navegar directamente al Dashboard de Clientes
            navigate('/clientes')
          }, 2000)
        }
      }
      
      if (failed > 0) {
        addToast('error', `${failed} clientes fallaron al guardar`)
      }
      
    } catch (error: any) {
      console.error('Error en guardado masivo:', error)
      
      // Limpiar notificaciones anteriores para evitar contradicciones
      clearContradictoryToasts()
      
      // Manejar diferentes tipos de errores
      if (error.response?.status === 503) {
        addToast('error', '🚨 SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
      } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        addToast('error', '🚨 ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
      } else if (error.response?.status === 400) {
        addToast('error', `Error de validación: ${error.response?.data?.detail || error.message}`)
      } else if (error.response?.status >= 500) {
        addToast('error', 'Error del servidor. Contacta al administrador.')
      } else {
        addToast('error', 'Error en el guardado masivo')
      }
      
      // NO navegar si hay errores
      console.log('No se navegará al Dashboard debido a errores en el guardado')
    } finally {
      setIsSavingIndividual(false)
    }
  }

  // 💡 FUNCIÓN PARA OBTENER SUGERENCIAS ESPECÍFICAS
  const getSuggestion = (field: string, value: string): string => {
    switch (field) {
      case 'nombres':
        if (value.trim().split(/\s+/).length < 2) {
          return `Ejemplo: "Juan Carlos" en lugar de "${value}"`
        }
        break
      // case 'apellidos' eliminado - nombres ahora unifica ambos
      case 'cedula':
        return `Ejemplo: "V12345678" o "E87654321"`
      case 'telefono':
        return `Ejemplo: "8741236589" (10 dígitos sin 0 inicial)`
      case 'email':
        return `Ejemplo: "usuario@dominio.com"`
      case 'concesionario':
        return `Selecciona un concesionario de la lista`
      case 'analista':
        return `Selecciona un analista de la lista`
      case 'modelo_vehiculo':
        return `Selecciona un modelo de vehículo de la lista`
      case 'estado':
        return `Ejemplo: "ACTIVO", "INACTIVO" o "FINALIZADO"`
      case 'activo':
        return `Ejemplo: "true" o "false"`
      default:
        return `Revisa el formato del campo`
    }
    return ''
  }

  // 🔍 VALIDAR CAMPO INDIVIDUAL
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    switch (field) {
      case 'cedula':
        if (!value.trim()) return { isValid: false, message: 'Cédula requerida' }
        const cedulaPattern = /^[VEJ]\d{7,10}$/
        if (!cedulaPattern.test(value.toUpperCase())) {
          return { isValid: false, message: 'Formato: V/E/J + 7-10 dígitos' }
        }
        return { isValid: true }

      case 'nombres':
        if (!value.trim()) return { isValid: false, message: 'Nombres requeridos' }
        const nombresWords = value.trim().split(/\s+/).filter(word => word.length > 0)
        // ✅ CARGA MASIVA: SOLO 2 PALABRAS EXACTAMENTE
        if (nombresWords.length !== 2) {
          return { isValid: false, message: 'DEBE tener exactamente 2 palabras (nombre + apellido)' }
        }
        return { isValid: true }

      case 'telefono':
        if (!value || !value.trim()) return { isValid: false, message: 'Teléfono requerido' }
        
        // El valor ya viene con +58, solo validar los 10 dígitos
        if (!value.startsWith('+58')) {
          return { isValid: false, message: 'Formato: +58 + 10 dígitos' }
        }
        
        const phoneDigits = value.replace('+58', '')
        
        // Validar que sean exactamente 10 dígitos y no empiece por 0
        const phonePattern = /^[1-9]\d{9}$/
        if (!phonePattern.test(phoneDigits)) {
          return { 
            isValid: false, 
            message: 'Formato: 10 dígitos (sin 0 inicial)' 
          }
        }
        
        return { isValid: true }

      case 'email':
        if (!value.trim()) return { isValid: false, message: 'Email requerido' }
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
        if (!emailPattern.test(value.toLowerCase())) {
          return { isValid: false, message: 'Formato de email inválido' }
        }
        return { isValid: true }

      case 'total_financiamiento':
        if (!value.trim()) return { isValid: false, message: 'Total requerido' }
        const total = parseFloat(value.replace(/[^\d.-]/g, ''))
        if (isNaN(total) || total <= 0) return { isValid: false, message: 'Debe ser un número positivo' }
        if (total < 1 || total > 50000000) return { isValid: false, message: 'Entre $1 y $50,000,000' }
        return { isValid: true }

      case 'numero_amortizaciones':
        if (!value.trim()) return { isValid: false, message: 'Número requerido' }
        const amortizaciones = parseInt(value)
        if (isNaN(amortizaciones) || amortizaciones < 1 || amortizaciones > 60) {
          return { isValid: false, message: 'Entre 1 y 60 cuotas' }
        }
        return { isValid: true }

      case 'modalidad_pago':
        if (!value.trim()) return { isValid: false, message: 'Modalidad requerida' }
        const modalidades = ['SEMANAL', 'QUINCENAL', 'MENSUAL']
        if (!modalidades.includes(value.toUpperCase())) {
          return { isValid: false, message: 'Debe ser SEMANAL, QUINCENAL o MENSUAL' }
        }
        return { isValid: true }

      case 'fecha_entrega':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        
        // ✅ NUEVO: Detectar números de serie de Excel
        if (/^\d{4,}$/.test(value.trim())) {
          try {
            const numeroSerie = parseInt(value.trim())
            // Excel cuenta desde 1900-01-01, pero tiene un bug del año bisiesto
            // Fórmula: fecha = new Date(1900, 0, 1) + (numeroSerie - 2) días
            const fechaExcel = new Date(1900, 0, 1)
            fechaExcel.setDate(fechaExcel.getDate() + numeroSerie - 2)
            
            const hoyEntrega = new Date()
            hoyEntrega.setHours(0, 0, 0, 0)
            
            // Calcular límites: 2 años atrás y 4 años adelante
            const fechaLimiteAtras = new Date(hoyEntrega)
            fechaLimiteAtras.setFullYear(hoyEntrega.getFullYear() - 2)
            
            const fechaLimiteAdelante = new Date(hoyEntrega)
            fechaLimiteAdelante.setFullYear(hoyEntrega.getFullYear() + 4)
            
            if (fechaExcel < fechaLimiteAtras) {
              return { isValid: false, message: 'La fecha no puede ser anterior a hace 2 años' }
            }
            
            if (fechaExcel > fechaLimiteAdelante) {
              return { isValid: false, message: 'La fecha no puede ser posterior a 4 años en el futuro' }
            }
            
            return { isValid: true }
          } catch (error) {
            return { isValid: false, message: 'Número de serie de Excel inválido' }
          }
        }
        
        // Validación normal para fechas en formato string
        const fechaEntrega = new Date(value)
        const hoyEntrega = new Date()
        hoyEntrega.setHours(0, 0, 0, 0)
        
        // Calcular límites: 2 años atrás y 4 años adelante
        const fechaLimiteAtras = new Date(hoyEntrega)
        fechaLimiteAtras.setFullYear(hoyEntrega.getFullYear() - 2)
        
        const fechaLimiteAdelante = new Date(hoyEntrega)
        fechaLimiteAdelante.setFullYear(hoyEntrega.getFullYear() + 4)
        
        if (isNaN(fechaEntrega.getTime())) {
          return { isValid: false, message: 'Formato de fecha inválido' }
        }
        
        if (fechaEntrega < fechaLimiteAtras) {
          return { isValid: false, message: 'La fecha no puede ser anterior a hace 2 años' }
        }
        
        if (fechaEntrega > fechaLimiteAdelante) {
          return { isValid: false, message: 'La fecha no puede ser posterior a 4 años en el futuro' }
        }
        
        return { isValid: true }

      case 'estado':
        if (!value.trim()) return { isValid: false, message: 'Estado requerido' }
        const estados = ['ACTIVO', 'INACTIVO', 'FINALIZADO']
        const estadoNormalizado = value.toUpperCase().trim()
        if (!estados.includes(estadoNormalizado)) {
          return { isValid: false, message: 'Debe ser ACTIVO, INACTIVO o FINALIZADO' }
        }
        return { isValid: true }

      case 'activo':
        if (!value.trim()) return { isValid: false, message: 'Valor requerido' }
        const activos = ['true', 'false']
        if (!activos.includes(value.toLowerCase())) {
          return { isValid: false, message: 'Debe ser true o false' }
        }
        return { isValid: true }

      case 'direccion':
        if (!value.trim()) return { isValid: false, message: 'Dirección requerida' }
        if (value.trim().length < 5) return { isValid: false, message: 'Mínimo 5 caracteres' }
        return { isValid: true }

      case 'fecha_nacimiento':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        const fechaNac = new Date(value)
        const hoyNac = new Date()
        if (isNaN(fechaNac.getTime())) {
          return { isValid: false, message: 'Formato de fecha inválido' }
        }
        if (fechaNac >= hoyNac) {
          return { isValid: false, message: 'Debe ser una fecha pasada' }
        }
        return { isValid: true }

      case 'ocupacion':
        if (!value.trim()) return { isValid: false, message: 'Ocupación requerida' }
        if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
        return { isValid: true }

      case 'modelo_vehiculo':
        if (!value || value === null || !value.trim()) return { isValid: false, message: 'Modelo requerido' }
        // Verificar si el valor existe en la lista de modelos disponibles
        const modeloExists = modelosVehiculos.some(modelo => modelo.modelo === value.trim())
        if (!modeloExists) return { isValid: false, message: 'Modelo no válido' }
        return { isValid: true }

      case 'concesionario':
        if (!value || value === null || !value.trim()) return { isValid: false, message: 'Concesionario requerido' }
        // Verificar si el valor existe en la lista de concesionarios disponibles
        const concesionarioExists = concesionarios.some(concesionario => concesionario.nombre === value.trim())
        if (!concesionarioExists) return { isValid: false, message: 'Concesionario no válido' }
        return { isValid: true }

      case 'analista':
        if (!value || value === null || !value.trim()) return { isValid: false, message: 'Analista requerido' }
        // Verificar si el valor existe en la lista de analistas disponibles
        const analistaExists = analistas.some(analista => analista.nombre === value.trim())
        if (!analistaExists) return { isValid: false, message: 'Analista no válido' }
        return { isValid: true }

      case 'notas':
        // Notas es opcional, siempre válido
        return { isValid: true }

      default:
        return { isValid: true }
    }
  }

  // 📊 PROCESAR ARCHIVO EXCEL
  const processExcelFile = async (file: File) => {
    setIsProcessing(true)
    try {
      console.log('📊 Procesando archivo Excel:', file.name)
      
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      const sheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[sheetName]
      
      // Convertir a JSON
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })
      
      if (jsonData.length < 2) {
        throw new Error('El archivo debe tener al menos una fila de datos')
      }
      
      // Obtener encabezados (primera fila)
      const headers = jsonData[0] as string[]
      console.log('📋 Encabezados encontrados:', headers)
      
      // Procesar filas de datos
      const processedData: ExcelRow[] = []
      
      for (let i = 1; i < jsonData.length; i++) {
        const row = jsonData[i] as any[]
        if (!row || row.every(cell => !cell)) continue // Saltar filas vacías
        
        const rowData: ExcelRow = {
          _rowIndex: i + 1,
          _validation: {},
          _hasErrors: false,
          cedula: row[0]?.toString() || '',
          nombres: `${row[1]?.toString() || ''} ${row[2]?.toString() || ''}`.trim(),  // ✅ Unificar nombres + apellidos
          telefono: row[3]?.toString() || '',
          email: row[4]?.toString() || '',
          direccion: row[5]?.toString() || '',
          fecha_nacimiento: row[6]?.toString() || '',
          ocupacion: row[7]?.toString() || '',
          modelo_vehiculo: row[8]?.toString() || null,
          concesionario: row[9]?.toString() || null,
          analista: row[10]?.toString() || null,
          total_financiamiento: row[11]?.toString() || '',
          cuota_inicial: row[12]?.toString() || '',
          numero_amortizaciones: row[13]?.toString() || '',
          modalidad_pago: row[14]?.toString() || '',
          fecha_entrega: row[15]?.toString() || '',
          estado: row[16]?.toString() || 'ACTIVO', // ✅ Por defecto siempre ACTIVO
          activo: row[17]?.toString() || 'TRUE', // ✅ Por defecto siempre TRUE
          notas: row[18]?.toString() || ''
        }
        
        // Validar campos requeridos
        const requiredFields = ['cedula', 'nombres', 'telefono', 'email', 
                              'direccion', 'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 
                              'concesionario', 'analista', 'estado', 'activo']
        
        let hasErrors = false
        for (const field of requiredFields) {
          const validation = await validateField(field, rowData[field as keyof ExcelData] || '')
          rowData._validation[field] = validation
          if (!validation.isValid) hasErrors = true
        }
        
        // Validar notas por separado (siempre válido)
        rowData._validation.notas = { isValid: true }
        
        rowData._hasErrors = hasErrors
        processedData.push(rowData)
      }
      
      console.log('✅ Datos procesados:', processedData.length, 'filas')
      setExcelData(processedData)
      setShowPreview(true)
      
      // Validar dropdowns después de procesar
      updateDropdownErrors(processedData)
      
    } catch (error) {
      console.error('❌ Error procesando Excel:', error)
      alert(`Error procesando el archivo: ${error instanceof Error ? error.message : 'Error desconocido'}`)
    } finally {
      setIsProcessing(false)
    }
  }

  // 🎯 MANEJAR DRAG & DROP
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    const excelFile = files.find(file => 
      file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    )
    
    if (excelFile) {
      setUploadedFile(excelFile)
      processExcelFile(excelFile)
    } else {
      alert('Por favor selecciona un archivo Excel (.xlsx o .xls)')
    }
  }

  // 📁 MANEJAR SELECCIÓN DE ARCHIVO
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      processExcelFile(file)
    }
  }

  // 🔄 ACTUALIZAR VALOR EN PREVISUALIZACIÓN
  const updateCellValue = async (rowIndex: number, field: string, value: string | null) => {
    const newData = [...excelData]
    const row = newData[rowIndex]
    
    if (row) {
      row[field as keyof ExcelData] = value || ''
      
      // Para el campo notas, no hacer validación ni notificaciones
      if (field === 'notas') {
        // Solo actualizar el valor sin validación ni notificaciones
        row._validation[field] = { isValid: true }
        setExcelData(newData)
        return
      }
      
      // Re-validar el campo (solo para campos que no son notas)
      const validation = await validateField(field, value || '')
      row._validation[field] = validation
      
      // Recalcular si tiene errores (excluyendo notas que es opcional)
      const fieldsToCheck = Object.keys(row._validation).filter(field => field !== 'notas')
      const hasErrors = fieldsToCheck.some(field => !row._validation[field]?.isValid)
      row._hasErrors = hasErrors
      
      setExcelData(newData)
      
      // Manejar notificaciones por fila completa según el comportamiento requerido
      handleRowValidationNotification(rowIndex, row)
      
      // Actualizar estado de errores en dropdowns (ya no necesario - usando validación unificada)
      // updateDropdownErrors(newData)
      
      // Sistema de notificaciones anterior (comentado para usar el nuevo)
      // if (!validation.isValid) {
      //   addToast('error', `Campo "${field}": ${validation.message}`, getSuggestion(field, value))
      // } else {
      //   addToast('success', `Campo "${field}" es válido`)
      // }
    }
  }

  // 🎯 VALIDAR DROPDOWNS Y ACTUALIZAR ESTADO DE ERRORES
  const updateDropdownErrors = (data: ExcelRow[]) => {
    const errors: {[key: string]: boolean} = {}
    
    data.forEach((row, index) => {
      // Validar dropdowns específicos - SIEMPRE mostrar error si está vacío
      if (!row.concesionario || row.concesionario.trim() === '') {
        errors[`concesionario_${index}`] = true
      }
      if (!row.analista || row.analista.trim() === '') {
        errors[`analista_${index}`] = true
      }
      if (!row.modelo_vehiculo || row.modelo_vehiculo.trim() === '') {
        errors[`modelo_${index}`] = true
      }
    })
    
    console.log('🔍 Actualizando errores de dropdowns:', errors)
    setDropdownErrors(errors)
  }

  // 💾 GUARDAR DATOS VALIDADOS
  const handleSaveData = async () => {
    // Filtrar solo registros completamente válidos
    const validData = excelData.filter(row => {
      const hasNoErrors = !row._hasErrors
      const hasConcesionario = row.concesionario && row.concesionario.trim() !== ''
      const hasAnalista = row.analista && row.analista.trim() !== ''
      const hasModelo = row.modelo_vehiculo && row.modelo_vehiculo.trim() !== ''
      
      return hasNoErrors && hasConcesionario && hasAnalista && hasModelo
    })
    
    if (validData.length === 0) {
      setShowValidationModal(true) // Abre modal de advertencias
      return
    }
    
    setIsSaving(true)
    
    try {
      console.log('💾 Guardando datos:', validData.length, 'clientes')
      console.log('📋 Datos a guardar:', validData.map(row => ({
        fila: row._rowIndex,
        cedula: row.cedula,
        nombres: row.nombres,
        estado: row.estado,
        activo: row.activo,
        errores: row._hasErrors
      })))
      
      // Guardar cada cliente individualmente
      const resultados: Array<{
        success: boolean;
        cliente?: any;
        fila: number;
        error?: string;
        cedula?: string;
      }> = []
      for (const row of validData) {
        try {
          const clienteData = {
            cedula: row.cedula,
            nombres: row.nombres,  // ✅ nombres unificados
            telefono: row.telefono,
            email: row.email,
            direccion: row.direccion,
            fecha_nacimiento: row.fecha_nacimiento,
            ocupacion: row.ocupacion,
            modelo_vehiculo: row.modelo_vehiculo || undefined,
            concesionario: row.concesionario || undefined,
            analista: row.analista || undefined,
            estado: row.estado.toUpperCase().trim(), // ✅ Normalizar estado
            activo: row.activo === 'true' || row.activo === 'TRUE' || row.activo === '1',
            notas: row.notas || 'NA'
          }
          
          console.log(`🔄 Procesando fila ${row._rowIndex}:`, clienteData)
          
          const clienteCreado = await clienteService.createCliente(clienteData)
          resultados.push({ success: true, cliente: clienteCreado, fila: row._rowIndex })
          console.log(`✅ Cliente creado exitosamente: ${clienteData.nombres}`)
          
        } catch (error: any) {
          console.error(`❌ Error creando cliente en fila ${row._rowIndex}:`, error)
          
          // Manejar error de cliente duplicado (CORREGIDO: usar la nueva estructura)
          if (error.response?.status === 409 && 
              error.response?.data?.detail?.error === 'CLIENTE_DUPLICADO') {
            console.log(`⚠️ Cliente duplicado detectado en fila ${row._rowIndex}: ${row.cedula}`)
            resultados.push({ 
              success: false, 
              error: `Cliente duplicado: ${error.response?.data?.detail?.message || 'Cédula ya existe'}`, 
              fila: row._rowIndex,
              cedula: row.cedula
            })
          } else {
            resultados.push({ 
              success: false, 
              error: error instanceof Error ? error.message : 'Error desconocido', 
              fila: row._rowIndex,
              cedula: row.cedula
            })
          }
        }
      }
      
      // Mostrar resumen de resultados
      const exitosos = resultados.filter(r => r.success).length
      const fallidos = resultados.filter(r => !r.success).length
      
      console.log(`📊 Resumen: ${exitosos} exitosos, ${fallidos} fallidos`)
      
      if (exitosos > 0) {
        // Notificar éxito y cerrar
        onDataProcessed?.(validData)
        onSuccess?.()
        // ✅ Cerrar automáticamente al guardar exitosamente
        onClose()
      } else {
        alert('No se pudo guardar ningún cliente. Revisa los errores.')
      }
      
    } catch (error) {
      console.error('❌ Error en proceso de guardado:', error)
      alert('Error al guardar los datos. Intenta nuevamente.')
    } finally {
      setIsSaving(false)
    }
  }

  // 🎯 CONTAR REGISTROS VÁLIDOS (sin errores + dropdowns seleccionados)
  const validRows = excelData.filter(row => {
    const hasNoErrors = !row._hasErrors
    const hasConcesionario = row.concesionario && row.concesionario.trim() !== ''
    const hasAnalista = row.analista && row.analista.trim() !== ''
    const hasModelo = row.modelo_vehiculo && row.modelo_vehiculo.trim() !== ''
    
    return hasNoErrors && hasConcesionario && hasAnalista && hasModelo
  }).length
  
  const totalRows = excelData.length

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
              <div className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 ${
                serviceStatus === 'online' ? 'bg-green-100 text-green-800' :
                serviceStatus === 'offline' ? 'bg-red-100 text-red-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  serviceStatus === 'online' ? 'bg-green-500' :
                  serviceStatus === 'offline' ? 'bg-red-500' :
                  'bg-yellow-500'
                }`}></div>
                {serviceStatus === 'online' ? 'Online' :
                 serviceStatus === 'offline' ? 'Offline' :
                 'Verificando...'}
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
            /* ZONA DE SUBIDA */
            <Card>
              <CardContent className="pt-6">
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragging 
                      ? 'border-green-500 bg-green-50' 
                      : 'border-gray-300 hover:border-gray-400'
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
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
                      <p className="text-sm text-gray-600 mt-2">Procesando archivo...</p>
                    </div>
                  )}
                  
                  {uploadedFile && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <FileSpreadsheet className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-800">
                          {uploadedFile.name}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            /* PREVISUALIZACIÓN */
            <div className="space-y-4">
              {/* Estadísticas */}
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
                        Con errores: {totalRows - getValidClients().length - getSavedClientsCount()}
                      </Badge>
                      {getSavedClientsCount() > 0 && (
                        <Badge variant="outline" className="text-green-700 bg-green-50">
                          ✅ {getSavedClientsCount()} en Dashboard
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
                      <Button
                        onClick={() => setShowPreview(false)}
                        variant="outline"
                        size="sm"
                      >
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
                          📊 Ir al Dashboard de Clientes
                        </Button>
                      )}
                      <Button
                        onClick={saveAllValidClients}
                        disabled={getValidClients().length === 0 || isSavingIndividual || serviceStatus === 'offline'}
                        className="bg-green-600 hover:bg-green-700 disabled:opacity-50"
                      >
                        {isSavingIndividual ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
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

              {/* Modal de Advertencias de Validación */}
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
                          <Button variant="ghost" size="sm" onClick={() => setShowValidationModal(false)}>
                            <X className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-700">
                            <strong>No se puede guardar:</strong> Se encontraron {totalRows - validRows} registros con errores que deben corregirse antes de continuar.
                          </p>
                          <p className="text-sm text-red-600 mt-1">
                            <strong>Errores incluyen:</strong> Campos de validación inválidos y/o dropdowns sin seleccionar (Concesionario, Analista, Modelo Vehículo).
                          </p>
                        </div>

                        <div className="space-y-4 max-h-[50vh] overflow-y-auto">
                          {excelData.filter(row => {
                            // Incluir filas con errores de validación O con dropdowns sin seleccionar
                            const hasValidationErrors = row._hasErrors
                            const hasDropdownErrors = !row.concesionario || !row.analista || !row.modelo_vehiculo ||
                              row.concesionario.trim() === '' || row.analista.trim() === '' || row.modelo_vehiculo.trim() === ''
                            
                            return hasValidationErrors || hasDropdownErrors
                          }).map((row, index) => (
                            <div key={index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                              <div className="flex items-center justify-between mb-3">
                                <h3 className="font-semibold text-red-800">
                                  Fila {row._rowIndex}: {row.nombres}
                                </h3>
                                <Badge variant="outline" className="text-red-600 border-red-300">
                                  {Object.keys(row._validation).filter(field => !row._validation[field]?.isValid).length + 
                                   (dropdownErrors[`concesionario_${index}`] ? 1 : 0) +
                                   (dropdownErrors[`analista_${index}`] ? 1 : 0) +
                                   (dropdownErrors[`modelo_${index}`] ? 1 : 0)} errores
                                </Badge>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {Object.entries(row._validation).map(([field, validation]) => {
                                  if (validation?.isValid) return null;
                                  return (
                                    <div key={field} className="flex items-start space-x-2">
                                      <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                      <div className="flex-1">
                                        <span className="text-sm font-medium text-gray-700 capitalize">{field}:</span>
                                        <div className="text-sm text-red-600 mt-1">{validation?.message}</div>
                                      </div>
                                    </div>
                                  );
                                })}
                                
                                {/* Mostrar errores de dropdowns */}
                                {dropdownErrors[`concesionario_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Concesionario:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un concesionario</div>
                                    </div>
                                  </div>
                                )}
                                
                                {dropdownErrors[`analista_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Analista:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un analista</div>
                                    </div>
                                  </div>
                                )}
                                
                                {dropdownErrors[`modelo_${index}`] && (
                                  <div className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <div className="flex-1">
                                      <span className="text-sm font-medium text-gray-700">Modelo Vehículo:</span>
                                      <div className="text-sm text-red-600 mt-1">Debe seleccionar un modelo de vehículo</div>
                                    </div>
                                  </div>
                                )}
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
                                <li>Los campos con fondo rojo en la tabla tienen errores de validación</li>
                                <li>Haz clic en cualquier campo para editarlo directamente</li>
                                <li>Los errores se corrigen automáticamente al escribir valores válidos</li>
                                <li>Una vez corregidos todos los errores, podrás guardar los datos</li>
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
                              setShowValidationModal(false);
                              // Scroll a la tabla para que el usuario corrija
                              const tableElement = document.querySelector('.overflow-x-auto');
                              if (tableElement) {
                                tableElement.scrollIntoView({ behavior: 'smooth' });
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

              {/* Tabla de previsualización */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Eye className="mr-2 h-5 w-5" />
                    Previsualización de Datos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto min-w-full relative" style={{ resize: 'both', minWidth: '800px', minHeight: '400px' }}>
                    <table className="w-full border-collapse min-w-[1400px]">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-16">Fila</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Cédula</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">Nombres y Apellidos</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-28">Teléfono</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Email</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">Dirección</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Fecha Nac.</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Ocupación</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Modelo Veh.</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-40">Concesionario</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-32">Analista</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Estado</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-20">Activo</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-48">Notas</th>
                          <th className="border p-2 text-left text-xs font-medium text-gray-500 w-24">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {getDisplayData().map((row, index) => (
                          <tr key={index} className={row._hasErrors ? 'bg-red-50' : 'bg-green-50'}>
                            <td className="border p-2 text-xs">{row._rowIndex}</td>
                            
                            {/* Cédula */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.cedula}
                                onChange={(e) => updateCellValue(index, 'cedula', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.cedula?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Nombres y Apellidos (unificados) */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.nombres}
                                onChange={(e) => updateCellValue(index, 'nombres', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[120px] ${
                                  row._validation.nombres?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Teléfono */}
                            <td className="border p-2">
                              <div className="flex items-center">
                                <span className="bg-gray-100 border border-gray-300 rounded-l px-3 py-2 text-sm font-medium text-gray-700">
                                  +58
                                </span>
                                <input
                                  type="tel"
                                  value={row.telefono.replace('+58', '')}
                                  onChange={(e) => {
                                    const value = e.target.value
                                    // Solo permitir números y máximo 10 dígitos
                                    const cleanValue = value.replace(/\D/g, '').slice(0, 10)
                                    updateCellValue(index, 'telefono', '+58' + cleanValue)
                                  }}
                                  placeholder="XXXXXXXXXX"
                                  className={`flex-1 text-sm p-2 border border-l-0 rounded-r min-w-[80px] ${
                                    row._validation.telefono?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                  }`}
                                />
                              </div>
                            </td>
                            
                            {/* Email */}
                            <td className="border p-2">
                              <input
                                type="email"
                                value={row.email}
                                onChange={(e) => updateCellValue(index, 'email', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.email?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Dirección */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.direccion}
                                onChange={(e) => updateCellValue(index, 'direccion', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.direccion?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Fecha Nacimiento */}
                            <td className="border p-2">
                              <input
                                type="date"
                                value={row.fecha_nacimiento}
                                onChange={(e) => updateCellValue(index, 'fecha_nacimiento', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.fecha_nacimiento?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Ocupación */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.ocupacion}
                                onChange={(e) => updateCellValue(index, 'ocupacion', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.ocupacion?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Modelo Vehículo */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={modelosVehiculos.map(modelo => ({
                                  value: modelo.modelo,
                                  label: modelo.modelo
                                }))}
                                value={row.modelo_vehiculo || ''}
                                onChange={(value) => updateCellValue(index, 'modelo_vehiculo', value)}
                                placeholder="Seleccionar modelo..."
                                className={`w-full text-sm min-w-[120px] ${
                                  row._validation.modelo_vehiculo?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Concesionario */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={concesionarios.map(concesionario => ({
                                  value: concesionario.nombre,
                                  label: concesionario.nombre
                                }))}
                                value={row.concesionario || ''}
                                onChange={(value) => updateCellValue(index, 'concesionario', value)}
                                placeholder="Seleccionar concesionario..."
                                className={`w-full text-sm min-w-[120px] ${
                                  row._validation.concesionario?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Analista */}
                            <td className="border p-2">
                              <SearchableSelect
                                options={analistas.map(analista => ({
                                  value: analista.nombre,
                                  label: analista.nombre
                                }))}
                                value={row.analista || ''}
                                onChange={(value) => updateCellValue(index, 'analista', value)}
                                placeholder="Seleccionar analista..."
                                className={`w-full text-sm min-w-[120px] ${
                                  row._validation.analista?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Estado */}
                            <td className="border p-2">
                              <select
                                value={row.estado || 'ACTIVO'}
                                onChange={(e) => updateCellValue(index, 'estado', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.estado?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              >
                                <option value="ACTIVO">ACTIVO</option>
                                <option value="INACTIVO">INACTIVO</option>
                                <option value="FINALIZADO">FINALIZADO</option>
                              </select>
                            </td>
                            
                            {/* Activo */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.activo}
                                onChange={(e) => updateCellValue(index, 'activo', e.target.value)}
                                className={`w-full text-sm p-2 border rounded min-w-[80px] ${
                                  row._validation.activo?.isValid ? 'border-gray-300 bg-white text-black' : 'border-red-800 bg-red-800 text-white'
                                }`}
                              />
                            </td>
                            
                            {/* Notas */}
                            <td className="border p-2">
                              <input
                                type="text"
                                value={row.notas}
                                onChange={(e) => updateCellValue(index, 'notas', e.target.value)}
                                className="w-full text-sm p-2 border border-gray-300 bg-white text-black rounded min-w-[80px]"
                              />
                            </td>
                            
                            {/* Acciones */}
                            <td className="border p-2">
                              <div className="flex items-center justify-center space-x-1">
                                {savedClients.has(row._rowIndex) ? (
                                  <div className="flex items-center text-green-600">
                                    <CheckCircle className="h-4 w-4 mr-1" />
                                    <span className="text-xs">Guardado</span>
                                  </div>
                                ) : isClientValid(row) ? (
                                  <Button
                                    size="sm"
                                    onClick={() => saveIndividualClient(row)}
                                    disabled={savingProgress[row._rowIndex] || serviceStatus === 'offline'}
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
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {/* Handle de redimensionamiento */}
                    <div className="absolute bottom-0 right-0 w-4 h-4 bg-gray-400 cursor-se-resize opacity-50 hover:opacity-100 transition-opacity">
                      <div className="w-full h-full bg-gradient-to-br from-transparent via-gray-600 to-gray-800"></div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </motion.div>

      {/* 🔔 NOTIFICACIONES TOAST */}
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
                  {toast.type === 'error' && <AlertTriangle className="h-5 w-5 text-red-500" />}
                  {toast.type === 'warning' && <Info className="h-5 w-5 text-yellow-500" />}
                  {toast.type === 'success' && <CheckCircle2 className="h-5 w-5 text-green-500" />}
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

      {/* Modal de confirmación de duplicados */}
      {showConfirmacionModal && clienteDuplicado && clienteDuplicado.existente && clienteDuplicado.existente.cedula && (
        <ConfirmacionDuplicadoModal
          isOpen={showConfirmacionModal}
          onClose={() => {
            setShowConfirmacionModal(false)
            setClienteDuplicado(null)
          }}
          onConfirm={handleConfirmarDuplicado}
          clienteExistente={clienteDuplicado.existente}
          clienteNuevo={clienteDuplicado.nuevo}
        />
      )}
    </motion.div>
  )
}
