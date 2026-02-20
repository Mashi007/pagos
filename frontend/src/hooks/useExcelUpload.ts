/**
 * Hook for Excel client bulk upload.
 * Extracted from ExcelUploader component.
 */

import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { clienteService } from '../services/clienteService'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { useIsMounted } from './useIsMounted'
import { useEstadosCliente } from './useEstadosCliente'
import {
  type ExcelRow,
  blankIfNN,
  formatNombres,
  convertirFechaExcel,
  convertirFechaParaBackend,
  validateField,
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
} from '../utils/excelValidation'

export interface ExcelUploaderProps {
  onClose: () => void
  onDataProcessed?: (data: ExcelRow[]) => void
  onSuccess?: () => void
}

export interface ToastItem {
  id: string
  type: 'error' | 'warning' | 'success'
  message: string
  suggestion?: string
  field: string
  rowIndex: number
}

export function useExcelUpload({ onClose, onDataProcessed, onSuccess }: ExcelUploaderProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const isMounted = useIsMounted()
  const { user } = useSimpleAuth()
  const { opciones: opcionesEstado } = useEstadosCliente()
  const usuarioRegistro = user?.email ?? 'carga-masiva'

  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [violationTracker, setViolationTracker] = useState<
    Record<
      string,
      {
        violationCount: number
        lastRowData: string
      }
    >
  >({})

  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [savedClients, setSavedClients] = useState<Set<number>>(new Set())
  const [isSavingIndividual, setIsSavingIndividual] = useState(false)
  const [savingProgress, setSavingProgress] = useState<Record<number, boolean>>({})
  const [serviceStatus, setServiceStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [showOnlyPending, setShowOnlyPending] = useState(false)
  const [showModalCedulasExistentes, setShowModalCedulasExistentes] = useState(false)
  const [cedulasExistentesEnBD, setCedulasExistentesEnBD] = useState<string[]>([])
  const [pendingSaveFilteredByCedulas, setPendingSaveFilteredByCedulas] = useState<ExcelRow[] | null>(null)

  const estadoOpciones = useMemo(
    () => (opcionesEstado.length > 0 ? opcionesEstado.map((o) => o.valor) : []),
    [opcionesEstado]
  )

  const validateFieldWithOptions = useCallback(
    (field: string, value: string) =>
      validateField(field, value, { estadoOpciones }),
    [estadoOpciones]
  )

  // Service status check
  const checkServiceStatus = useCallback(async () => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      const response = await fetch('/', { method: 'HEAD', signal: controller.signal })
      clearTimeout(timeoutId)
      setServiceStatus(response.ok ? 'online' : 'offline')
    } catch {
      setServiceStatus('offline')
    }
  }, [])

  useEffect(() => {
    checkServiceStatus()
    const interval = setInterval(checkServiceStatus, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [checkServiceStatus])

  // Toast helpers
  const addToast = useCallback(
    (
      type: 'error' | 'warning' | 'success',
      message: string,
      suggestion?: string,
      field = 'general',
      rowIndex = -1
    ) => {
      const id = Date.now().toString()
      setToasts((prev) => [...prev, { id, type, message, suggestion, field, rowIndex }])
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, 3000)
    },
    []
  )

  const removeToast = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
  }, [])

  const clearContradictoryToasts = useCallback(() => {
    setToasts((prev) =>
      prev.filter(
        (t) =>
          !t.message.includes('guardado exitosamente') &&
          !t.message.includes('agregado al Dashboard') &&
          !t.message.includes('Redirigiendo')
      )
    )
  }, [])

  // Duplicate detection
  const cedulasDuplicadasEnArchivo = useMemo(() => {
    const counts: Record<string, number> = {}
    excelData.forEach((row) => {
      const c = (row.cedula || '').trim() || 'Z999999999'
      if (c !== 'Z999999999') counts[c] = (counts[c] || 0) + 1
    })
    return new Set(Object.keys(counts).filter((ced) => (counts[ced] || 0) > 1))
  }, [excelData])

  const nombresDuplicadosEnArchivo = useMemo(() => {
    const counts: Record<string, number> = {}
    excelData.forEach((row) => {
      const n = (row.nombres || '').trim()
      if (n) counts[n] = (counts[n] || 0) + 1
    })
    return new Set(Object.keys(counts).filter((n) => (counts[n] || 0) > 1))
  }, [excelData])

  const emailDuplicadosEnArchivo = useMemo(() => {
    const counts: Record<string, number> = {}
    excelData.forEach((row) => {
      const e = (row.email || '').trim().toLowerCase()
      if (e) counts[e] = (counts[e] || 0) + 1
    })
    return new Set(Object.keys(counts).filter((em) => (counts[em] || 0) > 1))
  }, [excelData])

  const telefonoDuplicadosEnArchivo = useMemo(() => {
    const counts: Record<string, number> = {}
    const digits = (s: string) => (s || '').replace(/\D/g, '')
    excelData.forEach((row) => {
      let t = digits(row.telefono || '')
      if (t.startsWith('58') && t.length > 10) t = t.slice(2)
      if (t.length > 10) t = '9999999999'
      if (t.length >= 10) counts[t] = (counts[t] || 0) + 1
    })
    return new Set(Object.keys(counts).filter((t) => (counts[t] || 0) > 1))
  }, [excelData])

  const isClientValid = useCallback(
    (row: ExcelRow): boolean => {
      if (row._hasErrors) return false
      const ced = (row.cedula || '').trim() || 'Z999999999'
      if (ced !== 'Z999999999' && cedulasDuplicadasEnArchivo.has(ced)) return false
      const nom = (row.nombres || '').trim()
      if (nom && nombresDuplicadosEnArchivo.has(nom)) return false
      const em = (row.email || '').trim().toLowerCase()
      if (em && emailDuplicadosEnArchivo.has(em)) return false
      let telDig = (row.telefono || '').replace(/\D/g, '')
      if (telDig.startsWith('58') && telDig.length > 10) telDig = telDig.slice(2)
      if (telDig.length > 10) telDig = '9999999999'
      if (telDig.length >= 10 && telefonoDuplicadosEnArchivo.has(telDig)) return false
      return true
    },
    [
      cedulasDuplicadasEnArchivo,
      nombresDuplicadosEnArchivo,
      emailDuplicadosEnArchivo,
      telefonoDuplicadosEnArchivo,
    ]
  )

  const getDuplicadoMotivo = useCallback(
    (row: ExcelRow): string[] => {
      const motivos: string[] = []
      const ced = (row.cedula || '').trim() || 'Z999999999'
      if (ced !== 'Z999999999' && cedulasDuplicadasEnArchivo.has(ced)) motivos.push('cédula')
      if ((row.nombres || '').trim() && nombresDuplicadosEnArchivo.has((row.nombres || '').trim()))
        motivos.push('nombres')
      if (
        (row.email || '').trim() &&
        emailDuplicadosEnArchivo.has((row.email || '').trim().toLowerCase())
      )
        motivos.push('email')
      let telDig = (row.telefono || '').replace(/\D/g, '')
      if (telDig.startsWith('58') && telDig.length > 10) telDig = telDig.slice(2)
      if (telDig.length > 10) telDig = '9999999999'
      if (telDig.length >= 10 && telefonoDuplicadosEnArchivo.has(telDig)) motivos.push('teléfono')
      return motivos
    },
    [
      cedulasDuplicadasEnArchivo,
      nombresDuplicadosEnArchivo,
      emailDuplicadosEnArchivo,
      telefonoDuplicadosEnArchivo,
    ]
  )

  const getValidClients = useCallback((): ExcelRow[] => {
    return excelData.filter((row) => isClientValid(row) && !savedClients.has(row._rowIndex))
  }, [excelData, isClientValid, savedClients])

  const getDisplayData = useCallback((): ExcelRow[] => {
    if (showOnlyPending) {
      return excelData.filter((row) => !savedClients.has(row._rowIndex))
    }
    return excelData
  }, [excelData, showOnlyPending, savedClients])

  const getSavedClientsCount = useCallback(() => savedClients.size, [savedClients])

  const refreshDashboardClients = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-list'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
    queryClient.invalidateQueries({ queryKey: ['clientes', 'search'], exact: false })
  }, [queryClient])

  const notifyDashboardUpdate = useCallback(
    (clientCount: number) => {
      addToast(
        'success',
        `${clientCount} cliente${clientCount > 1 ? 's' : ''} agregado${clientCount > 1 ? 's' : ''} al Dashboard de Clientes`,
        'Los clientes ya están disponibles en la lista principal'
      )
    },
    [addToast]
  )

  const handleRowValidationNotification = useCallback(
    (rowIndex: number, row: ExcelRow) => {
      const trackerKey = `row-${rowIndex}`
      const currentTracker = violationTracker[trackerKey] || {
        violationCount: 0,
        lastRowData: '',
      }
      const rowDataHash = JSON.stringify({
        cedula: row.cedula,
        nombres: row.nombres,
        telefono: row.telefono,
        email: row.email,
        direccion: row.direccion,
        fecha_nacimiento: row.fecha_nacimiento,
        ocupacion: row.ocupacion,
      })
      if (currentTracker.lastRowData !== rowDataHash) {
        setViolationTracker((prev) => ({
          ...prev,
          [trackerKey]: { violationCount: 0, lastRowData: rowDataHash },
        }))
        return
      }
      const hasErrors = row._hasErrors
      const errorFields = Object.entries(row._validation)
        .filter(([, v]) => !v.isValid)
        .map(([f]) => f)

      if (!hasErrors) {
        const successToast: ToastItem = {
          id: `success-row-${rowIndex}-${Date.now()}`,
          type: 'success',
          message: `Fila ${rowIndex + 1} es válida`,
          field: 'fila_completa',
          rowIndex,
        }
        setToasts((prev) => [...prev, successToast])
        setViolationTracker((prev) => ({
          ...prev,
          [trackerKey]: { violationCount: 0, lastRowData: rowDataHash },
        }))
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== successToast.id))
        }, 3000)
      } else {
        const newViolationCount = currentTracker.violationCount + 1
        const shouldShow =
          newViolationCount === 1 ||
          newViolationCount === 3 ||
          newViolationCount === 6 ||
          newViolationCount === 9 ||
          newViolationCount === 12 ||
          (newViolationCount > 12 && newViolationCount % 3 === 0)
        if (shouldShow) {
          const errorToast: ToastItem = {
            id: `error-row-${rowIndex}-${Date.now()}`,
            type: 'error',
            message: `Fila ${rowIndex + 1}: Campos con errores: ${errorFields.join(', ')}`,
            suggestion: 'Corrija los campos marcados en rojo para continuar',
            field: 'fila_completa',
            rowIndex,
          }
          setToasts((prev) => [...prev, errorToast])
          setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== errorToast.id))
          }, 3000)
        }
        setViolationTracker((prev) => ({
          ...prev,
          [trackerKey]: { violationCount: newViolationCount, lastRowData: rowDataHash },
        }))
      }
    },
    [violationTracker]
  )

  const saveIndividualClient = useCallback(
    async (row: ExcelRow): Promise<boolean> => {
      try {
        if (row._hasErrors) {
          alert(
            '⚠️ NO SE PUEDE GUARDAR: Hay campos vacíos o con errores en esta fila.\n\nPor favor, complete todos los campos obligatorios en la tabla antes de guardar.'
          )
          return false
        }
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
        const rawTel = blankIfNN(row.telefono)
        const digits = rawTel.replace(/\D/g, '')
        const tel10 = digits.length > 10 ? '9999999999' : digits.slice(0, 10)
        const telefonoNormalizado = '+58' + (tel10 || rawTel)
        const clienteData = {
          cedula: blankIfNN(row.cedula) || 'Z999999999',
          nombres: formatNombres(blankIfNN(row.nombres)),
          telefono: telefonoNormalizado,
          email: blankIfNN(row.email).toLowerCase(),
          direccion: blankIfNN(row.direccion),
          fecha_nacimiento: convertirFechaParaBackend(blankIfNN(row.fecha_nacimiento)),
          ocupacion: blankIfNN(row.ocupacion),
          estado: blankIfNN(row.estado).toUpperCase(),
          activo: row.activo === 'true' || row.activo === 'TRUE' || row.activo === '1',
          notas: blankIfNN(row.notas) || 'NA',
          usuario_registro: usuarioRegistro,
        }
        try {
          await clienteService.createCliente(clienteData)
        } catch (error: unknown) {
          const err = error as { response?: { status?: number; data?: { detail?: string; message?: string } }; code?: string; message?: string }
          if (err.response?.status === 400 || err.response?.status === 409) {
            const msg =
              err.response?.data?.detail ||
              err.response?.data?.message ||
              'No se puede crear un cliente: ya existe uno con la misma cédula, nombre, email o teléfono.'
            addToast('error', `Error en fila ${row._rowIndex}: ${msg}`)
          } else if (err.response?.status === 503) {
            addToast('error', '⚠️ SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
          } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
            addToast('error', '⚠️ ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
          } else if (err.response && err.response.status && err.response.status >= 500) {
            addToast('error', 'Error del servidor. Contacta al administrador.')
          } else {
            const msg =
              err.response?.data?.detail ||
              err.response?.data?.message ||
              err.message ||
              'Error desconocido'
            addToast('error', `Error guardando cliente en fila ${row._rowIndex}: ${msg}`)
          }
          setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
          return false
        }
        setSavedClients((prev) => new Set([...prev, row._rowIndex]))
        refreshDashboardClients()
        addToast('success', `Cliente ${row.nombres} guardado exitosamente`)
        setExcelData((prev) => {
          const remaining = prev.filter((r) => r._rowIndex !== row._rowIndex)
          if (remaining.length === 0) {
            addToast('success', '¡Todos los clientes han sido guardados exitosamente!')
            notifyDashboardUpdate(getSavedClientsCount())
            addToast('success', 'Redirigiendo al Dashboard de Clientes en 2 segundos...')
            setTimeout(() => {
              onClose()
              navigate('/clientes')
            }, 2000)
          } else {
            addToast('warning', `${remaining.length} clientes pendientes`)
          }
          return remaining
        })
        return true
      } catch (error: unknown) {
        const err = error as { response?: { status?: number; data?: { detail?: string } }; code?: string; message?: string }
        clearContradictoryToasts()
        if (err.response?.status === 503) {
          addToast('error', '⚠️ SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
        } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
          addToast('error', '⚠️ ERROR DE RED: No se puede conectar al servidor. Verifica tu conexión.')
        } else if (err.response?.status === 400) {
          addToast('error', `Error de validación: ${err.response?.data?.detail || err.message}`)
        } else if (err.response && err.response.status && err.response.status >= 500) {
          addToast('error', 'Error del servidor. Contacta al administrador.')
        } else {
          addToast('error', `Error guardando cliente: ${err.response?.data?.detail || err.message}`)
        }
        return false
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [
      usuarioRegistro,
      addToast,
      refreshDashboardClients,
      notifyDashboardUpdate,
      getSavedClientsCount,
      onClose,
      navigate,
      clearContradictoryToasts,
    ]
  )

  const doSaveClientesList = useCallback(
    async (clientsToSave: ExcelRow[]) => {
      let failed = 0
      const successfulRowIndexes: number[] = []
      for (const client of clientsToSave) {
        try {
          const result = await saveIndividualClient(client)
          if (result) {
            successfulRowIndexes.push(client._rowIndex)
          } else {
            failed++
          }
        } catch (error: unknown) {
          failed++
          const err = error as { response?: { status?: number }; message?: string }
          if (err.response?.status === 409) {
            addToast('warning', `Cliente ${client.cedula} (${client.nombres}) duplicado - se omitió`)
          } else {
            addToast('error', `Error guardando ${client.cedula}: ${err.message || 'Error desconocido'}`)
          }
        }
      }
      const successful = successfulRowIndexes.length
      if (successful > 0) {
        addToast('success', `${successful} clientes guardados exitosamente`)
        refreshDashboardClients()
        notifyDashboardUpdate(successful)
        setExcelData((prev) => {
          const remaining = prev.filter((r) => !successfulRowIndexes.includes(r._rowIndex))
          if (remaining.length === 0) {
            addToast('success', '¡Todos los clientes guardados! Cerrando en 2 segundos...')
            setTimeout(() => {
              onClose()
              navigate('/clientes')
            }, 2000)
          } else {
            addToast('warning', `Quedan ${remaining.length} clientes por verificar`)
          }
          return remaining
        })
      }
      if (failed > 0) addToast('error', `${failed} clientes fallaron al guardar`)
    },
    [
      saveIndividualClient,
      addToast,
      refreshDashboardClients,
      notifyDashboardUpdate,
      onClose,
      navigate,
    ]
  )

  const saveAllValidClients = useCallback(async () => {
    const validClients = getValidClients()
    if (validClients.length === 0) {
      addToast('warning', 'No hay clientes válidos para guardar')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexión. No se puede comprobar cédulas ni guardar.')
      return
    }
    setIsSavingIndividual(true)
    try {
      const cedulasToCheck = validClients
        .map((c) => blankIfNN(c.cedula) || 'Z999999999')
        .filter(Boolean)
      const { existing_cedulas } = await clienteService.checkCedulas(cedulasToCheck)
      if (existing_cedulas.length > 0) {
        setCedulasExistentesEnBD(existing_cedulas)
        setPendingSaveFilteredByCedulas(
          validClients.filter(
            (c) => !existing_cedulas.includes(blankIfNN(c.cedula) || 'Z999999999')
          )
        )
        setShowModalCedulasExistentes(true)
        setIsSavingIndividual(false)
        return
      }
      await doSaveClientesList(validClients)
    } catch (error: unknown) {
      const err = error as { response?: { status?: number }; code?: string; message?: string }
      clearContradictoryToasts()
      if (err.response?.status === 503) {
        addToast('error', 'SERVICIO NO DISPONIBLE: El backend está caído. Contacta al administrador.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        addToast('error', 'ERROR DE RED: No se puede conectar al servidor.')
      } else if (err.response && err.response.status && err.response.status >= 500) {
        addToast('error', 'Error del servidor. Contacta al administrador.')
      } else {
        addToast('error', 'Error al comprobar cédulas o guardar.')
      }
    } finally {
      setIsSavingIndividual(false)
    }
  }, [
    getValidClients,
    serviceStatus,
    addToast,
    doSaveClientesList,
    clearContradictoryToasts,
  ])

  const confirmSaveOmittingExistingCedulas = useCallback(async () => {
    if (!pendingSaveFilteredByCedulas) return
    setShowModalCedulasExistentes(false)
    setCedulasExistentesEnBD([])
    const toSave = pendingSaveFilteredByCedulas
    setPendingSaveFilteredByCedulas(null)
    setIsSavingIndividual(true)
    try {
      await doSaveClientesList(toSave)
    } finally {
      setIsSavingIndividual(false)
    }
  }, [pendingSaveFilteredByCedulas, doSaveClientesList])

  const processExcelFile = useCallback(
    async (file: File) => {
      if (!isMounted()) return
      setIsProcessing(true)
      try {
        const fileValidation = validateExcelFile(file)
        if (!fileValidation.isValid) {
          alert(`Error de validación: ${fileValidation.error}`)
          if (isMounted()) setIsProcessing(false)
          return
        }
        if (fileValidation.warnings?.length) {
          console.warn('Advertencias de validación:', fileValidation.warnings)
        }
        sanitizeFileName(file.name)

        const data = await file.arrayBuffer()
        if (!isMounted()) return
        if (data.byteLength > 10 * 1024 * 1024) {
          alert('El archivo es demasiado grande. Tamaño máximo: 10 MB')
          if (isMounted()) setIsProcessing(false)
          return
        }

        const { readExcelToJSON } = await import('../types/exceljs')
        const jsonData = await readExcelToJSON(data)
        if (!isMounted()) return

        const dataValidation = validateExcelData(jsonData)
        if (!dataValidation.isValid) {
          alert(`Error en datos del archivo: ${dataValidation.error}`)
          if (isMounted()) setIsProcessing(false)
          return
        }

        if (jsonData.length < 2) {
          throw new Error('El archivo debe tener al menos una fila de datos')
        }

        const processedData: ExcelRow[] = []
        const requiredFields = [
          'cedula',
          'nombres',
          'telefono',
          'email',
          'direccion',
          'fecha_nacimiento',
          'ocupacion',
          'estado',
          'activo',
        ]

        for (let i = 1; i < jsonData.length; i++) {
          if (!isMounted()) return
          const row = jsonData[i] as unknown[]
          if (!row || row.every((cell) => !cell)) continue

          const rowData: ExcelRow = {
            _rowIndex: i + 1,
            _validation: {},
            _hasErrors: false,
            cedula: (row[0]?.toString() || '').trim() || 'Z999999999',
            nombres: row[1]?.toString() || '',
            telefono: row[2]?.toString() || '',
            email: row[3]?.toString() || '',
            direccion: row[4]?.toString() || '',
            fecha_nacimiento: convertirFechaExcel(row[5]),
            ocupacion: row[6]?.toString() || '',
            estado: row[7]?.toString() || 'ACTIVO',
            activo: row[8]?.toString() || 'TRUE',
            notas: row[9]?.toString() || '',
          }

          let hasErrors = false
          for (const field of requiredFields) {
            if (!isMounted()) return
            const validation = validateFieldWithOptions(
              field,
              rowData[field as keyof typeof rowData] || ''
            )
            rowData._validation[field] = validation
            if (!validation.isValid) hasErrors = true
          }
          rowData._validation.notas = { isValid: true }
          rowData._hasErrors = hasErrors
          processedData.push(rowData)
        }

        if (!isMounted()) return
        setExcelData(processedData)
        setShowPreview(true)
      } catch (err) {
        console.error('Error procesando Excel:', err)
        alert(
          `Error procesando el archivo: ${err instanceof Error ? err.message : 'Error desconocido'}`
        )
      } finally {
        if (isMounted()) setIsProcessing(false)
      }
    },
    [isMounted, validateFieldWithOptions]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const files = Array.from(e.dataTransfer.files)
      const excelFile = files.find(
        (f) => f.name.endsWith('.xlsx') || f.name.endsWith('.xls')
      )
      if (excelFile) {
        setUploadedFile(excelFile)
        processExcelFile(excelFile)
      } else {
        alert('Por favor selecciona un archivo Excel (.xlsx o .xls)')
      }
    },
    [processExcelFile]
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        setUploadedFile(file)
        processExcelFile(file)
      }
    },
    [processExcelFile]
  )

  const updateCellValue = useCallback(
    async (rowIndex: number, field: string, value: string | null) => {
      const newData = [...excelData]
      const row = newData[rowIndex]
      if (!row) return

      let formattedValue = value || ''
      if (field === 'cedula' && !formattedValue.trim()) {
        formattedValue = 'Z999999999'
      }
      row[field as keyof typeof row] = formattedValue

      if (field === 'notas') {
        row._validation[field] = { isValid: true }
        setExcelData(newData)
        return
      }

      const validation = validateFieldWithOptions(field, formattedValue)
      row._validation[field] = validation
      const fieldsToCheck = Object.keys(row._validation).filter((f) => f !== 'notas')
      row._hasErrors = fieldsToCheck.some((f) => !row._validation[f]?.isValid)
      setExcelData(newData)
      handleRowValidationNotification(rowIndex, row)
    },
    [excelData, validateFieldWithOptions, handleRowValidationNotification]
  )

  const validRows = excelData.filter((r) => !r._hasErrors).length
  const totalRows = excelData.length

  return {
    // State
    isDragging,
    uploadedFile,
    excelData,
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
    pendingSaveFilteredByCedulas,
    setShowModalCedulasExistentes,
    setCedulasExistentesEnBD,
    setPendingSaveFilteredByCedulas,
    opcionesEstado,
    validRows,
    totalRows,
    // Refs
    fileInputRef,
    // Handlers
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
  }
}
