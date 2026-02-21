/**
 * Hook para carga masiva de pagos desde Excel.
 * Columnas: Cédula, Fecha de pago, Monto, Documento, ID Préstamo (opcional).
 * Solo préstamos activos (APROBADO, DESEMBOLSADO) en el selector.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'
import { prestamoService } from '../services/prestamoService'
import { useIsMounted } from './useIsMounted'
import {
  type PagoExcelRow,
  convertirFechaExcelPago,
  convertirFechaParaBackendPago,
  validatePagoField,
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
} from '../utils/pagoExcelValidation'

const ESTADOS_PRESTAMO_ACTIVO = ['APROBADO', 'DESEMBOLSADO']

export interface ExcelUploaderPagosProps {
  onClose: () => void
  onSuccess?: () => void
}

export function useExcelUploadPagos({ onClose, onSuccess }: ExcelUploaderPagosProps) {
  const queryClient = useQueryClient()
  const isMounted = useIsMounted()

  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelData, setExcelData] = useState<PagoExcelRow[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [savedRows, setSavedRows] = useState<Set<number>>(new Set())
  const [enviadosRevisar, setEnviadosRevisar] = useState<Set<number>>(new Set())
  const [duplicadosPendientesRevisar, setDuplicadosPendientesRevisar] = useState<Set<number>>(new Set())
  const [isSavingIndividual, setIsSavingIndividual] = useState(false)
  const [isSendingAllRevisar, setIsSendingAllRevisar] = useState(false)
  const [savingProgress, setSavingProgress] = useState<Record<number, boolean>>({})
  const [serviceStatus, setServiceStatus] = useState<'unknown' | 'online' | 'offline'>('unknown')
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'error' | 'warning' | 'success'; message: string }>>([])

  const addToast = useCallback((type: 'error' | 'warning' | 'success', message: string) => {
    const id = Date.now().toString() + Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500)
  }, [])

  const removeToast = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
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

  const cedulasUnicas = useMemo(
    () => [...new Set(excelData.map((r) => (r.cedula || '').trim()).filter((c) => c.length >= 5))],
    [excelData]
  )

  const [prestamosPorCedula, setPrestamosPorCedula] = useState<Record<string, Array<{ id: number; estado: string }>>>({})
  const [cedulasBuscando, setCedulasBuscando] = useState<Set<string>>(new Set())

  const mergePrestamosEnMap = useCallback(
    (cedula: string, prestamos: Array<{ id: number; estado: string }>) => {
      const activos = prestamos.filter((p) => ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase()))
      const arr = activos.map((p) => ({ id: p.id, estado: p.estado || '' }))
      setPrestamosPorCedula((prev) => {
        const next = { ...prev }
        next[cedula] = arr
        const cedulaSinGuion = cedula.replace(/-/g, '')
        if (cedulaSinGuion !== cedula) next[cedulaSinGuion] = arr
        return next
      })
    },
    []
  )

  // Búsqueda por cédula individual (al hacer clic en Buscar o al salir del campo)
  const fetchSingleCedula = useCallback(
    async (cedula: string): Promise<boolean> => {
      const cedulaNorm = (cedula || '').trim()
      if (cedulaNorm.length < 5) return false
      const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
      setCedulasBuscando((prev) => new Set([...prev, cedulaNorm]))
      try {
        const prestamos = await prestamoService.getPrestamosByCedula(cedulaNorm)
        mergePrestamosEnMap(cedulaNorm, (prestamos || []).map((p: any) => ({ id: p.id, estado: p.estado || '' })))
        return true
      } catch {
        return false
      } finally {
        setCedulasBuscando((prev) => {
          const next = new Set(prev)
          next.delete(cedulaNorm)
          return next
        })
      }
    },
    [mergePrestamosEnMap]
  )

  // Carga inicial: usa batch (1 petición) si hay 3+ cédulas para evitar timeouts en servidores lentos
  const BATCH_THRESHOLD = 3
  useEffect(() => {
    if (!showPreview || cedulasUnicas.length === 0) {
      setPrestamosPorCedula((prev) => (Object.keys(prev).length ? {} : prev))
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      setCedulasBuscando((prev) => new Set([...prev, ...cedulasUnicas]))
      const fetchPromise =
        cedulasUnicas.length > BATCH_THRESHOLD
          ? prestamoService.getPrestamosByCedulasBatch(cedulasUnicas).then((batch) => {
              const map: Record<string, Array<{ id: number; estado: string }>> = {}
              cedulasUnicas.forEach((cedula) => {
                const prestamos = (batch[cedula] || batch[cedula.replace(/-/g, '')] || []).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
                )
                const arr = prestamos.map((p: any) => ({ id: p.id, estado: p.estado || '' }))
                map[cedula] = arr
                const cedulaSinGuion = cedula.replace(/-/g, '')
                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr
              })
              return map
            })
          : Promise.all(cedulasUnicas.map((c) => prestamoService.getPrestamosByCedula(c))).then((results) => {
              const map: Record<string, Array<{ id: number; estado: string }>> = {}
              cedulasUnicas.forEach((cedula, i) => {
                const prestamos = (results[i] || []).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
                )
                const arr = prestamos.map((p: any) => ({ id: p.id, estado: p.estado || '' }))
                map[cedula] = arr
                const cedulaSinGuion = cedula.replace(/-/g, '')
                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr
              })
              return map
            })

      fetchPromise
        .then((map) => {
          if (!cancelled) setPrestamosPorCedula(map)
        })
        .catch(() => {
          if (!cancelled) setPrestamosPorCedula({})
        })
        .finally(() => {
          if (!cancelled) {
            setCedulasBuscando((prev) => {
              const next = new Set(prev)
              cedulasUnicas.forEach((c) => next.delete(c))
              return next
            })
          }
        })
    }, 350)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [showPreview, cedulasUnicas.join(',')])

  // Auto-asignar prestamo_id cuando la cédula tiene exactamente 1 crédito activo
  useEffect(() => {
    if (!showPreview || Object.keys(prestamosPorCedula).length === 0) return
    setExcelData((prev) => {
      let changed = false
      const next = prev.map((r) => {
        const cedulaNorm = (r.cedula || '').trim()
        const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
        const prestamos =
          prestamosPorCedula[cedulaNorm] || prestamosPorCedula[cedulaSinGuion] || []
        if (prestamos.length === 1 && (r.prestamo_id == null || r.prestamo_id === undefined)) {
          changed = true
          return { ...r, prestamo_id: prestamos[0].id }
        }
        return r
      })
      return changed ? next : prev
    })
  }, [showPreview, prestamosPorCedula])

  const refreshPagos = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['pagos-ultimos'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['pagos-por-cedula'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['kpis'], exact: false })
    queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false })
  }, [queryClient])

  const getValidRows = useCallback((): PagoExcelRow[] => {
    return excelData.filter((r) => !r._hasErrors && !savedRows.has(r._rowIndex) && !enviadosRevisar.has(r._rowIndex))
  }, [excelData, savedRows, enviadosRevisar])

  const getRowsToRevisarPagos = useCallback((): PagoExcelRow[] => {
    return excelData.filter((row) => {
      if (savedRows.has(row._rowIndex) || enviadosRevisar.has(row._rowIndex)) return false
      if (duplicadosPendientesRevisar.has(row._rowIndex)) return true
      if (row._hasErrors) return true
      const cedulaNorm = (row.cedula || '').trim()
      const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaNorm] || prestamosPorCedula[cedulaSinGuion] || []
      return prestamosActivos.length !== 1
    })
  }, [excelData, savedRows, enviadosRevisar, duplicadosPendientesRevisar, prestamosPorCedula])

  const saveIndividualPago = useCallback(
    async (row: PagoExcelRow, opts?: { skipToast?: boolean; skipRefresh?: boolean }): Promise<{ ok: boolean; was409?: boolean }> => {
      if (row._hasErrors) {
        addToast('error', 'Hay errores en esta fila. Corrígelos antes de guardar.')
        return { ok: false }
      }
      const cedulaNorm = (row.cedula || '').trim()
      const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaNorm] || prestamosPorCedula[cedulaSinGuion] || []
      if (prestamosActivos.length > 1 && !row.prestamo_id) {
        addToast('error', `Fila ${row._rowIndex}: La cédula ${cedulaNorm} tiene ${prestamosActivos.length} créditos activos. Seleccione uno.`)
        return { ok: false }
      }
      if (prestamosActivos.length === 0 && !row.prestamo_id) {
        addToast('warning', `Fila ${row._rowIndex}: No hay créditos activos para ${cedulaNorm}. Se guardará sin préstamo asociado.`)
      }

      setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
      try {
        let prestamoId: number | null = row.prestamo_id
        if (!prestamoId && prestamosActivos.length === 1) {
          prestamoId = prestamosActivos[0].id
        }

        let numeroDoc = (row.numero_documento || '').trim()
        if (numeroDoc === 'NaN' || numeroDoc === 'nan') numeroDoc = ''
        if (numeroDoc && /[eE]/.test(numeroDoc)) {
          try {
            numeroDoc = Math.floor(parseFloat(numeroDoc)).toString()
          } catch {
            /* keep as is */
          }
        }

        const pagoData = {
          cedula_cliente: cedulaNorm,
          prestamo_id: prestamoId,
          fecha_pago: convertirFechaParaBackendPago(row.fecha_pago) || new Date().toISOString().split('T')[0],
          monto_pagado: Number(row.monto_pagado) || 0,
          numero_documento: numeroDoc || '',
          institucion_bancaria: null,
          notas: null,
          conciliado: row.conciliado ?? false,
        }

        await pagoService.createPago(pagoData as any)
        setSavedRows((prev) => new Set([...prev, row._rowIndex]))
        setDuplicadosPendientesRevisar((prev) => {
          const next = new Set(prev)
          next.delete(row._rowIndex)
          return next
        })
        if (!opts?.skipRefresh) refreshPagos()
        if (!opts?.skipToast) addToast('success', `Pago ${row.cedula} guardado`)
        const valid = getValidRows()
        if (valid.length === 1 && valid[0]._rowIndex === row._rowIndex) {
          onSuccess?.()
          onClose()
        }
        return { ok: true }
      } catch (err: any) {
        const detail = err?.response?.data?.detail
        const msg =
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg || d.message).join(' ')
            : detail || err?.message || 'Error al guardar'
        const is409 = err?.response?.status === 409
        if (is409) {
          setDuplicadosPendientesRevisar((prev) => new Set([...prev, row._rowIndex]))
          addToast(
            'warning',
            `Fila ${row._rowIndex}: Documento duplicado. Use "Revisar Pagos" para confirmar uno a uno.`
          )
          return { ok: false, was409: true }
        } else {
          addToast('error', `Fila ${row._rowIndex}: ${msg}`)
          return { ok: false }
        }
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [prestamosPorCedula, addToast, refreshPagos, onSuccess, onClose, getValidRows]
  )

  const sendToRevisarPagos = useCallback(
    async (row: PagoExcelRow, onNavigate: () => void): Promise<boolean> => {
      setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
      const buildPagoData = (numeroDoc: string) => ({
        cedula_cliente: (row.cedula || '').trim(),
        prestamo_id: null,
        fecha_pago: convertirFechaParaBackendPago(row.fecha_pago) || new Date().toISOString().split('T')[0],
        monto_pagado: Number(row.monto_pagado) || 0,
        numero_documento: numeroDoc || '',
        institucion_bancaria: null,
        notas: null,
        conciliado: row.conciliado ?? false,
      })
      let numeroDoc = (row.numero_documento || '').trim()
      if (numeroDoc === 'NaN' || numeroDoc === 'nan') numeroDoc = ''
      if (numeroDoc && /[eE]/.test(numeroDoc)) {
        try {
          numeroDoc = Math.floor(parseFloat(numeroDoc)).toString()
        } catch {
          /* keep as is */
        }
      }
      try {
        let pagoData = buildPagoData(numeroDoc)
        let usadoRetry409 = false
        let succeeded = false
        let lastErr: any = null
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            await pagoService.createPago(pagoData as any)
            succeeded = true
            if (attempt > 0) usadoRetry409 = true
            break
          } catch (err409: any) {
            lastErr = err409
            if (err409?.response?.status === 409 && numeroDoc) {
              const unique = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
              const docSuffix = `-REV${row._rowIndex}-${unique}`
              pagoData = buildPagoData(numeroDoc + docSuffix)
            } else {
              throw err409
            }
          }
        }
        if (!succeeded) throw lastErr
        setEnviadosRevisar((prev) => new Set([...prev, row._rowIndex]))
        setDuplicadosPendientesRevisar((prev) => {
          const next = new Set(prev)
          next.delete(row._rowIndex)
          return next
        })
        refreshPagos()
        if (usadoRetry409) {
          addToast('warning', 'Documento duplicado. Se envió con sufijo único para corregir en Revisar Pagos.')
        } else if (row._hasErrors) {
          addToast('warning', 'Pago enviado a Revisar Pagos con errores. Corrígelo allí.')
        } else {
          addToast('success', `Pago enviado a Revisar Pagos`)
        }
        return true
      } catch (err: any) {
        const detail = err?.response?.data?.detail
        const msg =
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg || d.message).join(' ')
            : detail || err?.message || 'Error al guardar'
        const is409 = err?.response?.status === 409
        addToast(
          'error',
          is409
            ? `Fila ${row._rowIndex}: ${msg} Cambie el Nº documento o verifique si ya se guardó.`
            : `Fila ${row._rowIndex}: ${msg}`
        )
        return false
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [addToast, refreshPagos]
  )

  const sendAllToRevisarPagos = useCallback(async () => {
    const rows = getRowsToRevisarPagos()
    if (rows.length === 0) {
      addToast('warning', 'No hay filas para enviar a Revisar Pagos')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexión')
      return
    }
    setIsSendingAllRevisar(true)
    let ok = 0
    let fail = 0
    for (const row of rows) {
      const result = await sendToRevisarPagos(row, () => {})
      if (result) ok++
      else fail++
    }
    setIsSendingAllRevisar(false)
    if (ok > 0) addToast('success', `${ok} enviado(s) a Revisar Pagos`)
    if (fail > 0) addToast('error', `${fail} fallaron`)
    if (ok > 0) refreshPagos()
  }, [getRowsToRevisarPagos, sendToRevisarPagos, addToast, refreshPagos, serviceStatus])

  const saveAllValid = useCallback(async () => {
    const valid = getValidRows()
    if (valid.length === 0) {
      addToast('warning', 'No hay pagos válidos para guardar')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexión')
      return
    }
    const toSave = valid.filter((row) => {
      if (duplicadosPendientesRevisar.has(row._rowIndex)) return false
      const cedulaNorm = (row.cedula || '').trim()
      const cedulaSinGuion = cedulaNorm.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaNorm] || prestamosPorCedula[cedulaSinGuion] || []
      if (prestamosActivos.length > 1 && !row.prestamo_id) return false
      return true
    })
    const omitidos = valid.length - toSave.length
    if (toSave.length === 0) {
      addToast(
        'warning',
        omitidos > 0
          ? `${omitidos} fila(s) pendientes: guarde uno a uno, corrija o envíe a Revisar Pagos.`
          : 'No hay filas que cumplan criterios para guardar en lote.'
      )
      return
    }
    setIsSavingIndividual(true)
    let ok = 0
    let fail = 0
    const indicesGuardadosEstaRonda = new Set<number>()
    let duplicados = 0
    for (const row of toSave) {
      const result = await saveIndividualPago(row, { skipToast: true, skipRefresh: true })
      if (result.ok) {
        ok++
        indicesGuardadosEstaRonda.add(row._rowIndex)
      } else {
        fail++
        if (result.was409) duplicados++
      }
    }
    if (ok > 0) addToast('success', `${ok} pago(s) guardado(s)`)
    if (fail > 0) {
      addToast('error', `${fail} fallaron`)
      if (duplicados > 0) {
        addToast('warning', `${duplicados} con documento duplicado. Use "Revisar Pagos" en cada fila para confirmar.`)
      }
    }
    if (omitidos > 0) {
      addToast('warning', `${omitidos} fila(s) omitidas: guarde uno a uno, corrija o envíe a Revisar Pagos.`)
    }
    if (ok > 0 || fail > 0) refreshPagos()
    setIsSavingIndividual(false)
    const quedanConErrores = excelData.some(
      (r) =>
        r._hasErrors &&
        !indicesGuardadosEstaRonda.has(r._rowIndex) &&
        !savedRows.has(r._rowIndex) &&
        !enviadosRevisar.has(r._rowIndex)
    )
    const quedanSinGuardar = excelData.some(
      (r) =>
        !indicesGuardadosEstaRonda.has(r._rowIndex) &&
        !savedRows.has(r._rowIndex) &&
        !enviadosRevisar.has(r._rowIndex)
    )
    if (fail === 0 && ok > 0 && !quedanConErrores && !quedanSinGuardar) {
      onSuccess?.()
      onClose()
    } else if (fail === 0 && ok > 0 && (quedanConErrores || quedanSinGuardar)) {
      addToast('warning', 'Quedan filas pendientes. Use "Revisar Pagos" en cada una o corríjalas.')
    }
  }, [getValidRows, serviceStatus, saveIndividualPago, addToast, onSuccess, onClose, prestamosPorCedula, excelData, savedRows, enviadosRevisar, duplicadosPendientesRevisar])

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

        const requiredFields = ['cedula', 'fecha_pago', 'monto_pagado', 'numero_documento']
        const processed: PagoExcelRow[] = []
        const documentosEnArchivo = new Set<string>()

        for (let i = 1; i < jsonData.length; i++) {
          if (!isMounted()) return
          const row = jsonData[i] as unknown[]
          if (!row || row.every((c) => c == null || c === '')) continue

          const cedula = (row[0]?.toString() || '').trim() || ''
          const fechaPago = convertirFechaExcelPago(row[1])
          const montoRaw = String(row[2] || 0).replace(',', '.')
          const monto = parseFloat(montoRaw) || 0
          let numeroDoc = (row[3]?.toString() || '').trim() || ''
          if (numeroDoc === 'NaN' || numeroDoc === 'nan' || numeroDoc === 'undefined') numeroDoc = ''
          const prestamoIdRaw = row[4]
          const conciliacionRawCol4 = (row[4]?.toString() || '').trim().toUpperCase()
          const conciliacionRawCol5 = (row[5]?.toString() || '').trim().toUpperCase()
          const isConciliacionCol4 = ['SI', 'SÍ', 'NO', '1', '0'].includes(conciliacionRawCol4)
          const prestamoId =
            !isConciliacionCol4 && prestamoIdRaw != null && String(prestamoIdRaw).trim() !== ''
              ? parseInt(String(prestamoIdRaw).trim(), 10)
              : null
          const conciliacionRaw = (isConciliacionCol4 ? conciliacionRawCol4 : conciliacionRawCol5).trim()
          // Por defecto: Conciliación = Sí. Solo No si explícitamente "NO" (evitar que 0/celda vacía = No).
          const conciliado = conciliacionRaw === 'NO' ? false : true

          const rowData: PagoExcelRow = {
            _rowIndex: i + 1,
            _validation: {},
            _hasErrors: false,
            cedula,
            fecha_pago: fechaPago,
            monto_pagado: monto,
            numero_documento: numeroDoc,
            prestamo_id: Number.isNaN(prestamoId) ? null : prestamoId,
            conciliado,
          }

          let hasErrors = false
          for (const field of requiredFields) {
            const val = rowData[field as keyof PagoExcelRow]
            const validation = validatePagoField(field, val as string | number, {
              documentosEnArchivo: documentosEnArchivo,
            })
            rowData._validation[field] = validation
            if (!validation.isValid) hasErrors = true
          }
          rowData._validation.prestamo_id = { isValid: true }
          if (numeroDoc && numeroDoc !== 'NaN') documentosEnArchivo.add(numeroDoc)
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

  const updateCellValue = useCallback((row: PagoExcelRow, field: string, value: string | number) => {
    setExcelData((prev) =>
      prev.map((r) => {
        if (r._rowIndex !== row._rowIndex) return r
        const updated = { ...r }
        if (field === 'prestamo_id') {
          updated.prestamo_id = value === '' || value === 'none' ? null : (Number(value) || null)
        } else if (field === 'conciliado') {
          updated.conciliado = value === 'si' || value === 'SI' || String(value) === '1'
        } else {
          ;(updated as any)[field] = field === 'monto_pagado' ? (Number(value) || 0) : value
        }
        const documentosEnArchivo = new Set<string>()
        prev.forEach((other) => {
          if (other._rowIndex !== row._rowIndex && (other.numero_documento || '').trim())
            documentosEnArchivo.add((other.numero_documento || '').trim())
        })
        const validation = validatePagoField(field, (updated as any)[field], {
          documentosEnArchivo: field === 'numero_documento' ? documentosEnArchivo : undefined,
        })
        updated._validation = { ...r._validation, [field]: validation }
        const required = ['cedula', 'fecha_pago', 'monto_pagado', 'numero_documento']
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
    getValidRows,
    saveIndividualPago,
    saveAllValid,
    sendToRevisarPagos,
    sendAllToRevisarPagos,
    getRowsToRevisarPagos,
    isSendingAllRevisar,
    enviadosRevisar,
    duplicadosPendientesRevisar,
    onClose,
    removeToast,
  }
}
