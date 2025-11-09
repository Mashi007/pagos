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
// xlsx se importa dinámicamente para reducir el bundle inicial
import { clienteService } from '@/services/clienteService'
import { useQueryClient } from '@tanstack/react-query'

interface ExcelData {
  cedula: string
  nombres: string  // ✅ CARGA MASIVA: Entre 2-4 palabras
  telefono: string
  email: string
  direccion: string
  fecha_nacimiento: string
  ocupacion: string
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


  // Normalizador: si el valor es 'nn' (cualquier caso/espacios), convertir a vacío
  const blankIfNN = (value: string | null | undefined): string => {
    if (value == null) return ''
    const trimmed = value.toString().trim()
    return trimmed.toLowerCase() === 'nn' ? '' : trimmed
  }

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
      ocupacion: rowData.ocupacion
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
    // Verificar cada 2 minutos (optimizado de 30s para reducir requests)
    const interval = setInterval(checkServiceStatus, 2 * 60 * 1000)
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
    // Invalidar cache de clientes para refrescar Dashboard y formularios de préstamos
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-list'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
    // ✅ Invalidar también búsquedas de clientes (usadas en formularios de préstamos)
    queryClient.invalidateQueries({ 
      queryKey: ['clientes', 'search'],
      exact: false  // Invalida todas las búsquedas: ['clientes', 'search', ...]
    })
    
    console.log('🔄 Cache de Dashboard de Clientes y búsquedas invalidado')
  }

  const notifyDashboardUpdate = (clientCount: number) => {
    addToast('success', 
      `${clientCount} cliente${clientCount > 1 ? 's' : ''} agregado${clientCount > 1 ? 's' : ''} al Dashboard de Clientes`,
      'Los clientes ya están disponibles en la lista principal'
    )
  }


  const saveIndividualClient = async (row: ExcelRow): Promise<boolean> => {
    
    try {
      // ✅ VALIDACIÓN PREVIA: Verificar que NO hay errores antes de intentar guardar
      if (row._hasErrors) {
        alert('⚠️ NO SE PUEDE GUARDAR: Hay campos vacíos o con errores en esta fila.\n\nPor favor, complete todos los campos obligatorios en la tabla antes de guardar.')
        return false
      }
      
      setSavingProgress(prev => ({ ...prev, [row._rowIndex]: true }))
      
      const clienteData = {
        cedula: blankIfNN(row.cedula),
        nombres: formatNombres(blankIfNN(row.nombres)),  // ✅ Aplicar formato Title Case y ya unificados (nombres + apellidos)
        telefono: blankIfNN(row.telefono),
        email: blankIfNN(row.email).toLowerCase(),
        direccion: blankIfNN(row.direccion),
        fecha_nacimiento: convertirFechaParaBackend(blankIfNN(row.fecha_nacimiento)),  // ✅ Convertir DD/MM/YYYY a YYYY-MM-DD
        ocupacion: blankIfNN(row.ocupacion),
        estado: blankIfNN(row.estado).toUpperCase(), // ✅ Normalizar estado
        activo: row.activo === 'true' || row.activo === 'TRUE' || row.activo === '1',
        notas: blankIfNN(row.notas) || 'NA'
      }

      try {
        await clienteService.createCliente(clienteData)
      } catch (error: any) {
        console.error('Error guardando cliente individual:', error)
        
        // Manejar diferentes tipos de errores
        if (error.response?.status === 400 || error.response?.status === 409) {
          // Error de cliente duplicado (misma cédula y mismo nombre)
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'No se puede crear un cliente con la misma cédula y el mismo nombre.'
          addToast('error', `Error en fila ${row._rowIndex}: ${errorMessage}`)
        } else if (error.response?.status === 503) {
          addToast('error', '🚨 SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
        } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
          addToast('error', '🚨 ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
        } else if (error.response?.status >= 500) {
          addToast('error', 'Error del servidor. Contacta al administrador.')
        } else {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Error desconocido'
          addToast('error', `Error guardando cliente en fila ${row._rowIndex}: ${errorMessage}`)
        }
        
        // Limpiar progreso
        setSavingProgress(prev => ({ ...prev, [row._rowIndex]: false }))
        return false
      }
      
      // Marcar como guardado
      setSavedClients(prev => new Set([...prev, row._rowIndex]))
      
      // Refrescar Dashboard de Clientes
      refreshDashboardClients()
      
      addToast('success', `Cliente ${row.nombres} guardado exitosamente`)
      
      // Eliminar la fila de la lista después de guardar exitosamente
      setExcelData(prev => {
        const remaining = prev.filter(r => r._rowIndex !== row._rowIndex)
        
        // ✅ Solo cerrar automáticamente si YA NO HAY filas pendientes
        if (remaining.length === 0) {
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
        } else {
          // ✅ HAY clientes pendientes, mostrar información
          addToast('warning', `${remaining.length} clientes pendientes`)
        }
        
        return remaining
      })
      
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
      // Limpiar progreso
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
      
      console.log(`🔄 Iniciando guardado masivo de ${validClients.length} clientes válidos`)
      
      for (let i = 0; i < validClients.length; i++) {
        const client = validClients[i]
        console.log(`📋 Procesando cliente ${i + 1}/${validClients.length}: ${client.cedula} - ${client.nombres}`)
        
        try {
          // ✅ await esperará automáticamente si hay un duplicado y el usuario debe confirmar
          const result = await saveIndividualClient(client)
          
          if (result === true) {
            successful++
            successfulRowIndexes.push(client._rowIndex)
            console.log(`✅ Cliente ${i + 1}/${validClients.length} guardado exitosamente: ${client.cedula}`)
          } else {
            failed++
            console.log(`⚠️ Cliente ${i + 1}/${validClients.length} no se guardó (result: ${result}): ${client.cedula}`)
          }
        } catch (error: any) {
          failed++
          console.error(`❌ Error guardando cliente ${i + 1}/${validClients.length} (${client.cedula}):`, error)
          // Mostrar error específico al usuario
          if (error.response?.status === 409) {
            addToast('warning', `Cliente ${client.cedula} (${client.nombres}) duplicado - se canceló`)
          } else {
            addToast('error', `Error guardando ${client.cedula}: ${error.message || 'Error desconocido'}`)
          }
        }
        
        console.log(`📊 Progreso: ${successful} exitosos, ${failed} fallidos, ${validClients.length - (i + 1)} pendientes`)
      }
      
      console.log(`✅ Guardado masivo completado: ${successful} exitosos, ${failed} fallidos`)
      
      if (successful > 0) {
        // Solo mostrar notificación de éxito si realmente se guardaron
        addToast('success', `${successful} clientes guardados exitosamente`)
        
        // Refrescar Dashboard de Clientes
        refreshDashboardClients()
        notifyDashboardUpdate(successful)
        
        // Eliminar las filas guardadas de la lista
        setExcelData(prev => {
          const remaining = prev.filter(r => !successfulRowIndexes.includes(r._rowIndex))
          
          // ✅ Solo cerrar automáticamente si YA NO HAY filas pendientes
          if (remaining.length === 0) {
            // Mostrar mensaje informativo sobre navegación automática
            addToast('success', '🎉 ¡Todos los clientes guardados! Cerrando en 2 segundos...')
            
            // Navegar automáticamente al Dashboard de Clientes después de 2 segundos
            setTimeout(() => {
              // Cerrar el modal de Carga Masiva
              onClose()
              // Navegar directamente al Dashboard de Clientes
              navigate('/clientes')
            }, 2000)
          } else {
            // ✅ HAY clientes pendientes, mostrar advertencia
            addToast('warning', `⚠️ Quedan ${remaining.length} clientes por verificar`)
          }
          
          return remaining
        })
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
      case 'estado':
        return `Ejemplo: "ACTIVO", "INACTIVO" o "FINALIZADO"`
      case 'activo':
        return `Ejemplo: "true" o "false"`
      default:
        return `Revisa el formato del campo`
    }
    return ''
  }

  // 🎨 FUNCIÓN PARA FORMATO DE NOMBRES (Primera letra mayúscula)
  const formatNombres = (nombres: string): string => {
    if (!nombres || !nombres.trim()) return nombres
    
    return nombres
      .split(/\s+/)  // Separar por espacios
      .filter(word => word.length > 0)  // Filtrar palabras vacías
      .map(word => {
        // Capitalizar primera letra, resto minúsculas
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
      })
      .join(' ')  // Unir con espacios
  }

  // 📅 FUNCIÓN PARA CONVERTIR FECHA DE EXCEL A DD/MM/YYYY
  const convertirFechaExcel = (value: any): string => {
    if (!value) return ''
    
    const strValue = value.toString().trim()
    
    // Si es un número serial de Excel (ej: 45940, 45941)
    if (/^\d{4,}$/.test(strValue)) {
      try {
        const numeroSerie = parseInt(strValue, 10)
        // Excel cuenta desde 1900-01-01, pero tiene un bug del año bisiesto
        // Fórmula: fecha = new Date(1900, 0, 1) + (numeroSerie - 2) días
        const fechaBase = new Date(1900, 0, 1)
        fechaBase.setDate(fechaBase.getDate() + numeroSerie - 2)
        
        // Convertir a DD/MM/YYYY
        const dia = String(fechaBase.getDate()).padStart(2, '0')
        const mes = String(fechaBase.getMonth() + 1).padStart(2, '0')
        const ano = String(fechaBase.getFullYear())
        
        return `${dia}/${mes}/${ano}`
      } catch (error) {
        console.warn('Error convirtiendo fecha Excel:', strValue, error)
        return strValue
      }
    }
    
    // Si ya está en formato DD/MM/YYYY, devolverlo tal cual
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(strValue)) {
      return strValue
    }
    
    // Si está en formato ISO (YYYY-MM-DD), convertir
    if (/^\d{4}-\d{2}-\d{2}$/.test(strValue)) {
      const [ano, mes, dia] = strValue.split('-')
      return `${dia}/${mes}/${ano}`
    }
    
    // Formato desconocido, devolver tal cual (se validará después)
    return strValue
  }

  // 🔄 FUNCIÓN PARA CONVERTIR DD/MM/YYYY A YYYY-MM-DD (formato que espera el backend)
  const convertirFechaParaBackend = (fechaDDMMYYYY: string): string => {
    if (!fechaDDMMYYYY || !fechaDDMMYYYY.trim()) return ''
    
    const fechaRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/
    const match = fechaDDMMYYYY.trim().match(fechaRegex)
    
    if (!match) {
      console.warn('Formato de fecha inválido para convertir:', fechaDDMMYYYY)
      return fechaDDMMYYYY // Devolver tal cual si no es válido
    }
    
    const [, dia, mes, ano] = match
    return `${ano}-${mes}-${dia}`
  }

  // 🔍 VALIDAR CAMPO INDIVIDUAL
  const validateField = async (field: string, value: string): Promise<ValidationResult> => {
    // Regla NN: aceptar 'nn' como válido en cualquier campo
    if (typeof value === 'string' && value.trim().toLowerCase() === 'nn') {
      return { isValid: true, message: 'Valor omitido por NN' }
    }
    switch (field) {
      case 'cedula':
        if (!value.trim()) return { isValid: false, message: 'Cédula requerida' }
        // Limpiar caracteres no permitidos (como : al final)
        const cedulaLimpia = value.trim().replace(/:$/, '').replace(/:/g, '')
        const cedulaPattern = /^[VEJZ]\d{7,10}$/
        if (!cedulaPattern.test(cedulaLimpia.toUpperCase())) {
          return { isValid: false, message: 'Formato: V/E/J/Z + 7-10 dígitos (sin :)' }
        }
        return { isValid: true }

      case 'nombres':
        if (!value.trim()) return { isValid: false, message: 'Nombres requeridos' }
        const nombresWords = value.trim().split(/\s+/).filter(word => word.length > 0)
        // ✅ CARGA MASIVA: ENTRE 2 Y 7 PALABRAS
        if (nombresWords.length < 2 || nombresWords.length > 7) {
          return { isValid: false, message: 'DEBE tener entre 2 y 7 palabras' }
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
        const emailTrimmed = value.trim()
        
        // Validar que no tenga espacios intermedios
        if (emailTrimmed.includes(' ')) {
          return { isValid: false, message: 'El email no puede contener espacios' }
        }
        
        // Validar que no tenga comas
        if (emailTrimmed.includes(',')) {
          return { isValid: false, message: 'El email no puede contener comas' }
        }
        
        // Validar que tenga arroba
        if (!emailTrimmed.includes('@')) {
          return { isValid: false, message: 'El email debe contener un @' }
        }
        
        // Validar que tenga extensión válida (.com, .edu, .gob, etc.)
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
        if (!emailPattern.test(emailTrimmed.toLowerCase())) {
          return { isValid: false, message: 'El email debe tener una extensión válida (.com, .edu, .gob, etc.)' }
        }
        
        return { isValid: true }

      case 'direccion':
        if (!value.trim()) return { isValid: false, message: 'Dirección requerida' }
        if (value.trim().length < 5) return { isValid: false, message: 'Mínimo 5 caracteres' }
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

      case 'fecha_nacimiento':
        if (!value.trim()) return { isValid: false, message: 'Fecha requerida' }
        
        // Validar formato DD/MM/YYYY
        const fechaFormatRegex = /^(\d{2})\/(\d{2})\/(\d{4})$/
        if (!fechaFormatRegex.test(value.trim())) {
          return { isValid: false, message: 'Formato: DD/MM/YYYY (ej: 01/01/2025)' }
        }
        
        // Extraer día, mes y año
        const [, dia, mes, ano] = value.trim().match(fechaFormatRegex)!
        const diaNum = parseInt(dia, 10)
        const mesNum = parseInt(mes, 10)
        const anoNum = parseInt(ano, 10)
        
        // Validar rangos
        if (diaNum < 1 || diaNum > 31) {
          return { isValid: false, message: 'Día inválido (1-31)' }
        }
        if (mesNum < 1 || mesNum > 12) {
          return { isValid: false, message: 'Mes inválido (1-12)' }
        }
        if (anoNum < 1900 || anoNum > 2100) {
          return { isValid: false, message: 'Año inválido (1900-2100)' }
        }
        
        // Validar que la fecha sea válida (ej: no 31/02/2025)
        const fechaNac = new Date(anoNum, mesNum - 1, diaNum)
        if (fechaNac.getDate() !== diaNum || fechaNac.getMonth() !== mesNum - 1 || fechaNac.getFullYear() !== anoNum) {
          return { isValid: false, message: 'Fecha inválida (ej: 31/02 no existe)' }
        }
        
        // ✅ Validar que la fecha sea pasada (no futura)
        const hoyNac = new Date()
        hoyNac.setHours(0, 0, 0, 0)
        
        if (fechaNac >= hoyNac) {
          return { isValid: false, message: 'La fecha de nacimiento no puede ser futura o de hoy' }
        }
        
        // ✅ Validar que tenga al menos 18 años exactos
        const edad = hoyNac.getFullYear() - anoNum
        const fecha18 = new Date(anoNum + 18, mesNum - 1, diaNum)
        
        if (fecha18 > hoyNac) {
          return { isValid: false, message: 'Debe tener al menos 18 años cumplidos' }
        }
        
        return { isValid: true }

      case 'ocupacion':
        if (!value.trim()) return { isValid: false, message: 'Ocupación requerida' }
        if (value.trim().length < 2) return { isValid: false, message: 'Mínimo 2 caracteres' }
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
      
      // ✅ VALIDACIÓN DE SEGURIDAD: Validar archivo antes de procesar
      const { validateExcelFile, validateWorkbookStructure, validateExcelData, sanitizeFileName } = await import('@/utils/excelValidation')
      
      const fileValidation = validateExcelFile(file)
      if (!fileValidation.isValid) {
        alert(`Error de validación: ${fileValidation.error}`)
        setIsProcessing(false)
        return
      }
      
      if (fileValidation.warnings && fileValidation.warnings.length > 0) {
        console.warn('Advertencias de validación:', fileValidation.warnings)
      }
      
      // Sanitizar nombre del archivo
      const sanitizedFileName = sanitizeFileName(file.name)
      if (sanitizedFileName !== file.name) {
        console.warn('Nombre de archivo sanitizado:', sanitizedFileName)
      }
      
      // ✅ Importar xlsx dinámicamente para reducir bundle inicial
      const XLSXModule = await import('xlsx')
      // xlsx puede exportarse como default o como named export
      const XLSX = (XLSXModule.default || XLSXModule) as typeof import('xlsx')
      
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      
      // ✅ VALIDACIÓN DE SEGURIDAD: Validar estructura del workbook
      const structureValidation = validateWorkbookStructure(workbook)
      if (!structureValidation.isValid) {
        alert(`Error en estructura del archivo: ${structureValidation.error}`)
        setIsProcessing(false)
        return
      }
      
      const sheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[sheetName]
      
      // Convertir a JSON
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })
      
      // ✅ VALIDACIÓN DE SEGURIDAD: Validar datos extraídos
      const dataValidation = validateExcelData(jsonData)
      if (!dataValidation.isValid) {
        alert(`Error en datos del archivo: ${dataValidation.error}`)
        setIsProcessing(false)
        return
      }
      
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
          cedula: row[0]?.toString() || '',                    // Columna A
          nombres: row[1]?.toString() || '',                  // Columna B (nombres completos en un solo campo)
          telefono: row[2]?.toString() || '',                 // Columna C
          email: row[3]?.toString() || '',                    // Columna D
          direccion: row[4]?.toString() || '',                // Columna E
          fecha_nacimiento: convertirFechaExcel(row[5]),       // Columna F - ✅ Convertir de Excel a DD/MM/YYYY
          ocupacion: row[6]?.toString() || '',                // Columna G
          estado: row[7]?.toString() || 'ACTIVO',            // Columna H - Por defecto siempre ACTIVO
          activo: row[8]?.toString() || 'TRUE',              // Columna I - Por defecto siempre TRUE
          notas: row[9]?.toString() || ''                    // Columna J
        }
        
        // Validar campos requeridos
        const requiredFields = ['cedula', 'nombres', 'telefono', 'email', 
                              'direccion', 'fecha_nacimiento', 'ocupacion', 'estado', 'activo']
        
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
      // 🎨 NO APLICAR FORMATO MIENTRAS ESCRIBE (permitir espacios libres)
      // El formato se aplicará al guardar
      const formattedValue = value || ''
      
      row[field as keyof ExcelData] = formattedValue
      
      // Para el campo notas, no hacer validación ni notificaciones
      if (field === 'notas') {
        // Solo actualizar el valor sin validación ni notificaciones
        row._validation[field] = { isValid: true }
        setExcelData(newData)
        return
      }
      
      // Re-validar el campo (solo para campos que no son notas)
      const validation = await validateField(field, formattedValue)
      row._validation[field] = validation
      
      // Recalcular si tiene errores (excluyendo notas que es opcional)
      const fieldsToCheck = Object.keys(row._validation).filter(field => field !== 'notas')
      const hasValidationErrors = fieldsToCheck.some(field => !row._validation[field]?.isValid)
      
      // ✅ Validar dropdowns explícitamente
      const hasDropdownErrors = false
      
      row._hasErrors = hasValidationErrors || hasDropdownErrors
      
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
      // Campos eliminados: modelo_vehiculo, concesionario, analista
    })
    
    console.log('🔍 Actualizando errores de dropdowns:', errors)
    setDropdownErrors(errors)
  }

  // 💾 GUARDAR DATOS VALIDADOS
  const handleSaveData = async () => {
    // Filtrar solo registros completamente válidos
    const validData = excelData.filter(row => {
      const hasNoErrors = !row._hasErrors
      
      return hasNoErrors
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
            cedula: blankIfNN(row.cedula),
            nombres: formatNombres(blankIfNN(row.nombres)),  // ✅ Aplicar formato Title Case al guardar
            telefono: blankIfNN(row.telefono),
            email: blankIfNN(row.email).toLowerCase(),
            direccion: blankIfNN(row.direccion),
            fecha_nacimiento: convertirFechaParaBackend(blankIfNN(row.fecha_nacimiento)),  // ✅ Convertir DD/MM/YYYY a YYYY-MM-DD
            ocupacion: blankIfNN(row.ocupacion),
            estado: blankIfNN(row.estado).toUpperCase(), // ✅ Normalizar estado
            activo: row.activo === 'true' || row.activo === 'TRUE' || row.activo === '1',
            notas: blankIfNN(row.notas) || 'NA'
          }
          
          console.log(`🔄 Procesando fila ${row._rowIndex}:`, clienteData)
          
          const clienteCreado = await clienteService.createCliente(clienteData)
          resultados.push({ success: true, cliente: clienteCreado, fila: row._rowIndex })
          console.log(`✅ Cliente creado exitosamente: ${clienteData.nombres}`)
          
        } catch (error: any) {
          console.error(`❌ Error creando cliente en fila ${row._rowIndex}:`, error)
          
          // Manejar error de cliente duplicado (misma cédula y mismo nombre)
          let errorMessage = error instanceof Error ? error.message : 'Error desconocido'
          
          if (error.response?.status === 400 || error.response?.status === 409) {
            errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Cliente duplicado: Ya existe un cliente con la misma cédula y el mismo nombre'
          }
          
          resultados.push({ 
            success: false, 
            error: errorMessage,
            fila: row._rowIndex,
            cedula: row.cedula
          })
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
    
    return hasNoErrors
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
                            <strong>Errores incluyen:</strong> Campos de validación inválidos.
                          </p>
                        </div>

                        <div className="space-y-4 max-h-[50vh] overflow-y-auto">
                          {excelData.filter(row => {
                            // Incluir filas con errores de validación
                            const hasValidationErrors = row._hasErrors
                            
                            return hasValidationErrors
                          }).map((row, index) => (
                            <div key={index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                              <div className="flex items-center justify-between mb-3">
                                <h3 className="font-semibold text-red-800">
                                  Fila {row._rowIndex}: {row.nombres}
                                </h3>
                                <Badge variant="outline" className="text-red-600 border-red-300">
                                  {Object.keys(row._validation).filter(field => !row._validation[field]?.isValid).length} errores
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
                                }                                )}
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
                                type="text"
                                value={row.fecha_nacimiento}
                                onChange={(e) => {
                                  let value = e.target.value
                                  // Limpiar todos los caracteres no numéricos y barras
                                  const onlyDigits = value.replace(/\D/g, '')
                                  
                                  // Solo procesar si hay dígitos
                                  if (onlyDigits.length === 0) {
                                    updateCellValue(index, 'fecha_nacimiento', '')
                                    return
                                  }
                                  
                                  // Auto-formatear a DD/MM/YYYY
                                  let formatted = ''
                                  const digits = onlyDigits.substring(0, 8) // Limitar a 8 dígitos
                                  
                                  if (digits.length === 1) {
                                    // Solo un dígito: no formatear aún
                                    formatted = digits
                                  } else if (digits.length === 2) {
                                    // Dos dígitos: DD
                                    formatted = digits.substring(0, 2)
                                  } else if (digits.length === 3) {
                                    // Tres dígitos: DD/M
                                    formatted = digits.substring(0, 2) + '/' + digits.substring(2, 3)
                                  } else if (digits.length === 4) {
                                    // Cuatro dígitos: DD/MM
                                    formatted = digits.substring(0, 2) + '/' + digits.substring(2, 4)
                                  } else if (digits.length >= 5) {
                                    // Cinco o más dígitos: DD/MM/YYYY
                                    const dia = digits.substring(0, 2)
                                    const mes = digits.substring(2, 4)
                                    const ano = digits.substring(4, 8)
                                    formatted = dia + '/' + mes + '/' + ano
                                  }
                                  
                                  updateCellValue(index, 'fecha_nacimiento', formatted)
                                }}
                                onBlur={(e) => {
                                  // Al perder el foco, auto-completar con 0 si falta
                                  let value = e.target.value
                                  if (!value) return
                                  
                                  // Si no tiene barras, no formatear
                                  if (!value.includes('/')) {
                                    return
                                  }
                                  
                                  const parts = value.split('/')
                                  if (parts.length === 3) {
                                    // Auto-completar día con 0 si solo tiene un dígito
                                    if (parts[0].length === 1 && parseInt(parts[0]) <= 3) {
                                      parts[0] = '0' + parts[0]
                                    }
                                    // Auto-completar mes con 0 si solo tiene un dígito
                                    if (parts[1].length === 1) {
                                      parts[1] = '0' + parts[1]
                                    }
                                    // Auto-completar año con 0 si es necesario
                                    if (parts[2].length < 4) {
                                      parts[2] = parts[2].padStart(4, '0')
                                    }
                                    const autoFormatted = parts.join('/')
                                    updateCellValue(index, 'fecha_nacimiento', autoFormatted)
                                  }
                                }}
                                placeholder="DD/MM/YYYY"
                                maxLength={10}
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

    </motion.div>
  )
}
