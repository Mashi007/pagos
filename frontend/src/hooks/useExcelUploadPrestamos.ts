/**
 * Hook para carga masiva de préstamos desde Excel.
 * Si el cliente no existe, lo crea primero con datos placeholder.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { clienteService } from '../services/clienteService'
import { prestamoService } from '../services/prestamoService'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { useIsMounted } from './useIsMounted'
import {
  type PrestamoExcelRow,
  convertirFechaExcelPrestamo,
  convertirFechaParaBackendPrestamo,
  validatePrestamoField,
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
} from '../utils/prestamoExcelValidation'

export interface ExcelUploaderPrestamosProps {
  onClose: () => void
  onSuccess?: () => void
}

export function useExcelUploadPrestamos({ onClose, onSuccess }: ExcelUploaderPrestamosProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const isMounted = useIsMounted()
  const { user } = useSimpleAuth()
  const usuarioRegistro = user?.email ?? 'carga-masiva'

  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelData, setExcelData] = useState<PrestamoExcelRow[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [savedRows, setSavedRows] = useState<Set<number>>(new Set())
  const [isSavingIndividual, setIsSavingIndividual] = useState(false)
  const [savingProgress, setSavingProgress] = useState<Record<number, boolean>>({})
  const [serviceStatus, setServiceStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'error' | 'warning' | 'success'; message: string }>>([])

  const addToast = useCallback((type: 'error' | 'warning' | 'success', message: string) => {
    const id = Date.now().toString()
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
  }, [])

  const checkServiceStatus = useCallback(async () => {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      await fetch('/', { method: 'HEAD', signal: controller.signal })
      clearTimeout(timeoutId)
      setServiceStatus('online')
    } catch {
      setServiceStatus('offline')
    }
  }, [])

  useEffect(() => {
    checkServiceStatus()
    const interval = setInterval(checkServiceStatus, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [checkServiceStatus])

  const refreshPrestamos = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['prestamos'] })
    queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
    queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
  }, [queryClient])

  const getValidRows = useCallback((): PrestamoExcelRow[] => {
    return excelData.filter((r) => !r._hasErrors && !savedRows.has(r._rowIndex))
  }, [excelData, savedRows])

  const saveIndividualPrestamo = useCallback(
    async (row: PrestamoExcelRow): Promise<boolean> => {
      if (row._hasErrors) {
        addToast('error', 'Hay errores en esta fila. Corrígelos antes de guardar.')
        return false
      }
      setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
      try {
        const cedulaNorm = (row.cedula || '').trim() || 'Z999999999'
        let cliente = await clienteService.getClienteByCedula(cedulaNorm)

        if (!cliente) {
          const clienteData = {
            cedula: cedulaNorm,
            nombres: 'Revisar - Carga masiva',
            telefono: '+589999999999',
            email: 'revisar@email.com',
            direccion: 'Revisar',
            fecha_nacimiento: '1990-01-01',
            ocupacion: 'Revisar',
            estado: 'ACTIVO',
            activo: true,
            notas: 'Cliente creado por carga masiva de préstamos',
            usuario_registro: usuarioRegistro,
          }
          cliente = await clienteService.createCliente(clienteData)
        }

        const total = Number(row.total_financiamiento) || 0
        const numCuotas = Math.min(12, Math.max(1, Math.round(Number(row.numero_cuotas) || 12)))
        const cuotaPeriodo = row.cuota_periodo != null && Number(row.cuota_periodo) > 0
          ? Number(row.cuota_periodo)
          : total / numCuotas

        const prestamoData = {
          cliente_id: cliente.id,
          total_financiamiento: total,
          modalidad_pago: (row.modalidad_pago || 'MENSUAL').toUpperCase() as 'MENSUAL' | 'QUINCENAL' | 'SEMANAL',
          fecha_requerimiento: convertirFechaParaBackendPrestamo(row.fecha_requerimiento) || new Date().toISOString().split('T')[0],
          producto: (row.producto || '').trim() || 'Financiamiento',
          concesionario: (row.concesionario || '').trim() || undefined,
          analista: (row.analista || '').trim() || '',
          modelo_vehiculo: (row.modelo_vehiculo || '').trim() || undefined,
          numero_cuotas: numCuotas,
          cuota_periodo: cuotaPeriodo,
          tasa_interes: row.tasa_interes != null ? Number(row.tasa_interes) : 0,
          observaciones: (row.observaciones || '').trim() || undefined,
          estado: 'DRAFT',
        }

        await prestamoService.createPrestamo(prestamoData as any)
        setSavedRows((prev) => new Set([...prev, row._rowIndex]))
        refreshPrestamos()
        addToast('success', `Préstamo ${row.cedula} guardado`)
        return true
      } catch (err: any) {
        const msg = err?.response?.data?.detail || err?.message || 'Error al guardar'
        addToast('error', `Fila ${row._rowIndex}: ${msg}`)
        return false
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [usuarioRegistro, addToast, refreshPrestamos, onSuccess, onClose, navigate]
  )

  const saveAllValid = useCallback(async () => {
    const valid = getValidRows()
    if (valid.length === 0) {
      addToast('warning', 'No hay préstamos válidos para guardar')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexión')
      return
    }
    setIsSavingIndividual(true)
    let ok = 0
    let fail = 0
    for (const row of valid) {
      const result = await saveIndividualPrestamo(row)
      if (result) ok++
      else fail++
    }
    if (ok > 0) addToast('success', `${ok} préstamos guardados`)
    if (fail > 0) addToast('error', `${fail} fallaron`)
    setIsSavingIndividual(false)
  }, [getValidRows, serviceStatus, saveIndividualPrestamo, addToast])

  const processExcelFile = useCallback(
    async (file: File) => {
      if (!isMounted()) return
      setIsProcessing(true)
      try {
        const fileValidation = validateExcelFile(file)
        if (!fileValidation.isValid) {
          alert(`Error: ${fileValidation.error}`)
          return
        }
        sanitizeFileName(file.name)
        const data = await file.arrayBuffer()
        if (!isMounted()) return
        if (data.byteLength > 10 * 1024 * 1024) {
          alert('Archivo demasiado grande. Máximo 10 MB')
          return
        }
        const { readExcelToJSON } = await import('../types/exceljs')
        const jsonData = await readExcelToJSON(data)
        if (!isMounted()) return
        const dataValidation = validateExcelData(jsonData)
        if (!dataValidation.isValid) {
          alert(`Error en datos: ${dataValidation.error}`)
          return
        }
        if (jsonData.length < 2) {
          alert('El archivo debe tener al menos una fila de datos')
          return
        }

        const requiredFields = ['cedula', 'total_financiamiento', 'modalidad_pago', 'fecha_requerimiento', 'producto', 'analista', 'numero_cuotas']
        const processed: PrestamoExcelRow[] = []

        for (let i = 1; i < jsonData.length; i++) {
          if (!isMounted()) return
          const row = jsonData[i] as unknown[]
          if (!row || row.every((c) => c == null || c === '')) continue

          const rowData: PrestamoExcelRow = {
            _rowIndex: i + 1,
            _validation: {},
            _hasErrors: false,
            cedula: (row[0]?.toString() || '').trim() || 'Z999999999',
            total_financiamiento: parseFloat(String(row[1] || 0)) || 0,
            modalidad_pago: (row[2]?.toString() || 'MENSUAL').trim().toUpperCase(),
            fecha_requerimiento: convertirFechaExcelPrestamo(row[3]),
            producto: (row[4]?.toString() || '').trim(),
            concesionario: (row[5]?.toString() || '').trim(),
            analista: (row[6]?.toString() || '').trim(),
            modelo_vehiculo: (row[7]?.toString() || '').trim(),
            numero_cuotas: Math.round(parseFloat(String(row[8] || 12)) || 12),
            cuota_periodo: parseFloat(String(row[9] || 0)) || 0,
            tasa_interes: parseFloat(String(row[10] || 0)) || 0,
            observaciones: (row[11]?.toString() || '').trim(),
          }

          let hasErrors = false
          for (const field of requiredFields) {
            const val = rowData[field as keyof PrestamoExcelRow]
            const validation = validatePrestamoField(field, val as string | number)
            rowData._validation[field] = validation
            if (!validation.isValid) hasErrors = true
          }
          rowData._validation.concesionario = { isValid: true }
          rowData._validation.modelo_vehiculo = { isValid: true }
          rowData._validation.cuota_periodo = validatePrestamoField('cuota_periodo', rowData.cuota_periodo)
          rowData._validation.tasa_interes = validatePrestamoField('tasa_interes', rowData.tasa_interes)
          rowData._validation.observaciones = { isValid: true }
          if (!rowData._validation.cuota_periodo.isValid) hasErrors = true
          if (!rowData._validation.tasa_interes.isValid) hasErrors = true
          rowData._hasErrors = hasErrors
          processed.push(rowData)
        }

        if (!isMounted()) return
        setExcelData(processed)
        setShowPreview(true)
      } catch (err) {
        console.error('Error procesando Excel:', err)
        alert(`Error: ${err instanceof Error ? err.message : 'Error desconocido'}`)
      } finally {
        setIsProcessing(false)
      }
    },
    [isMounted]
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
      const excelFile = files.find((f) => f.name.endsWith('.xlsx') || f.name.endsWith('.xls'))
      if (excelFile) {
        setUploadedFile(excelFile)
        processExcelFile(excelFile)
      } else {
        alert('Selecciona un archivo Excel (.xlsx o .xls)')
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

  const updateCellValue = useCallback((row: PrestamoExcelRow, field: string, value: string | number) => {
    setExcelData((prev) =>
      prev.map((r) => {
        if (r._rowIndex !== row._rowIndex) return r
        const updated = { ...r, [field]: value }
        const validation = validatePrestamoField(field, value)
        updated._validation = { ...r._validation, [field]: validation }
        const required = ['cedula', 'total_financiamiento', 'modalidad_pago', 'fecha_requerimiento', 'producto', 'analista', 'numero_cuotas']
        updated._hasErrors = required.some((f) => !updated._validation[f]?.isValid)
        return updated
      })
    )
  }, [])

  return {
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
    saveIndividualPrestamo,
    saveAllValid,
    onClose,
    navigate,
  }
}
