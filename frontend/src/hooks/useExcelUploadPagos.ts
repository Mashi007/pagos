/**
 * Hook para carga masiva de pagos desde Excel.
 * Columnas: C?dula, Fecha de pago, Monto, Documento, ID Pr?stamo (opcional).
 * Solo pr?stamos activos (APROBADO, DESEMBOLSADO) en el selector.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'
import { pagoConErrorService } from '../services/pagoConErrorService'
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
  normalizarNumeroDocumento,
  cedulaParaLookup,
  cedulaLookupParaFila,
} from '../utils/pagoExcelValidation'
import { readExcelToJSON } from '../types/exceljs'

const ESTADOS_PRESTAMO_ACTIVO = ['APROBADO', 'DESEMBOLSADO']
// Límite de INTEGER en BD; si el valor parece número de documento (ej. 740087408451411), el backend devuelve 422
const PRESTAMO_ID_MAX = 2147483647

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

  // Incluir todas las cédulas válidas (V/E/J/Z + 6-11 dígitos) que aparezcan en columna Cédula O en columna Documento
  const looksLikeCedula = (c: string) => /^[VEJZ]\d{6,11}$/i.test((c || '').replace(/-/g, '').trim())
  const cedulasUnicas = useMemo(() => {
    const candidates = new Set<string>()
    excelData.forEach((r) => {
      const fromCedula = cedulaParaLookup(r.cedula)
      const fromDoc = cedulaParaLookup(r.numero_documento)
      const lookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
      ;[fromCedula, fromDoc, lookup].forEach((c) => {
        if (c && c.length >= 5 && looksLikeCedula(c)) candidates.add(c)
      })
    })
    // Normalizar (sin guión) para que coincidan con las claves que devuelve el backend
    return [...candidates].map((c) => (c || '').trim().replace(/-/g, '')).filter((c) => c.length >= 5 && looksLikeCedula(c))
  }, [excelData])

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

  // B?squeda por c?dula individual (al hacer clic en Buscar o al salir del campo)
  const fetchSingleCedula = useCallback(
    async (cedula: string): Promise<boolean> => {
      const cedulaNorm = cedulaParaLookup(cedula) || (cedula || '').trim()
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

  // Carga inicial: buscar préstamos por cédulas únicas (batch) y auto-asignar Crédito cuando hay 1 activo.
  useEffect(() => {
    if (!showPreview || cedulasUnicas.length === 0) {
      setPrestamosPorCedula((prev) => (Object.keys(prev).length ? {} : prev))
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      setCedulasBuscando((prev) => new Set([...prev, ...cedulasUnicas]))
      prestamoService
        .getPrestamosByCedulasBatch(cedulasUnicas)
        .then((batch) => {
          const map: Record<string, Array<{ id: number; estado: string }>> = {}
          cedulasUnicas.forEach((cedula) => {
            const prestamos = (batch[cedula] || batch[cedula.replace(/-/g, '')] || []).filter((p: any) =>
              ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
            )
            const arr = prestamos.map((p: any) => ({ id: p.id, estado: p.estado || '' }))
            map[cedula] = arr
            const cedulaSinGuion = cedula.replace(/-/g, '')
            if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr
            map[cedula.toUpperCase()] = arr
            map[cedula.toLowerCase()] = arr
          })
          return map
        })
        .then((map) => {
          if (!cancelled) {
            setPrestamosPorCedula(map)
            const prestamoIdVacio = (v: unknown) =>
              v == null || v === undefined || v === '' || v === 'none' || v === 0 || (typeof v === 'number' && Number.isNaN(v))
            const keysMap = Object.keys(map)
            const fallbackKey = keysMap.length === 1 ? keysMap[0] : null
            setExcelData((prev) =>
              prev.map((r) => {
                const cedulaLookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
                const cedulaColNorm = cedulaParaLookup(r.cedula) || (r.cedula || '').trim().replace(/-/g, '')
                const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
                let prestamos =
                  map[cedulaLookup] || map[cedulaSinGuion] || map[cedulaLookup.toUpperCase()] || map[cedulaLookup.toLowerCase()] || []
                if (prestamos.length === 0 && cedulaColNorm)
                  prestamos = map[cedulaColNorm] || map[cedulaColNorm.toUpperCase()] || map[cedulaColNorm.toLowerCase()] || []
                if (prestamos.length === 0 && fallbackKey) prestamos = map[fallbackKey] || []
                if (prestamos.length === 1 && prestamoIdVacio(r.prestamo_id)) return { ...r, prestamo_id: prestamos[0].id }
                return r
              })
            )
          }
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
    }, 0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [showPreview, cedulasUnicas.join(',')])

  // Auto-asignar prestamo_id solo cuando la cédula tiene exactamente 1 crédito activo; con 2 o más, asignación manual
  const prestamoIdVacio = (v: unknown) =>
    v == null || v === undefined || v === '' || v === 'none' || v === 0 || (typeof v === 'number' && Number.isNaN(v))

  useEffect(() => {
    if (!showPreview || Object.keys(prestamosPorCedula).length === 0) return
    const keysMap = Object.keys(prestamosPorCedula)
    const fallbackKey = keysMap.length === 1 ? keysMap[0] : null
    setExcelData((prev) => {
      let changed = false
      const next = prev.map((r) => {
        const cedulaLookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
        const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
        let prestamos =
          prestamosPorCedula[cedulaLookup] || prestamosPorCedula[cedulaSinGuion] || prestamosPorCedula[cedulaLookup.toUpperCase()] || prestamosPorCedula[cedulaLookup.toLowerCase()] || []
        if (prestamos.length === 0 && fallbackKey) prestamos = prestamosPorCedula[fallbackKey] || []
        if (prestamos.length === 1 && prestamoIdVacio(r.prestamo_id)) {
          changed = true
          return { ...r, prestamo_id: prestamos[0].id }
        }
        return r
      })
      return changed ? next : prev
    })
  }, [showPreview, prestamosPorCedula, excelData.length])

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
      const cedulaLookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
      const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaLookup] || prestamosPorCedula[cedulaSinGuion] || prestamosPorCedula[cedulaLookup.toUpperCase()] || prestamosPorCedula[cedulaLookup.toLowerCase()] || []
      return prestamosActivos.length !== 1
    })
  }, [excelData, savedRows, enviadosRevisar, duplicadosPendientesRevisar, prestamosPorCedula])

  const saveIndividualPago = useCallback(
    async (row: PagoExcelRow, opts?: { skipToast?: boolean; skipRefresh?: boolean }): Promise<{ ok: boolean; was409?: boolean }> => {
      if (row._hasErrors) {
        addToast('error', 'Hay errores en esta fila. Corr?gelos antes de guardar.')
        return { ok: false }
      }
      const cedulaLookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
      const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaLookup] || prestamosPorCedula[cedulaSinGuion] || prestamosPorCedula[cedulaLookup.toUpperCase()] || prestamosPorCedula[cedulaLookup.toLowerCase()] || []
      if (prestamosActivos.length > 1 && !row.prestamo_id) {
        addToast('error', `Fila ${row._rowIndex}: La c?dula ${cedulaLookup} tiene ${prestamosActivos.length} cr?ditos activos. Seleccione uno.`)
        return { ok: false }
      }
      if (prestamosActivos.length === 0 && !row.prestamo_id) {
        addToast('warning', `Fila ${row._rowIndex}: No hay cr?ditos activos para ${cedulaLookup}. Se guardar? sin pr?stamo asociado.`)
      }

      setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
      try {
        let prestamoId: number | null = row.prestamo_id
        if (!prestamoId && prestamosActivos.length === 1) {
          prestamoId = prestamosActivos[0].id
        }

        let numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

        if (prestamoId != null && (prestamoId < 1 || prestamoId > PRESTAMO_ID_MAX)) {
          addToast(
            'error',
            `Fila ${row._rowIndex}: El valor del crédito no es válido (parece un número de documento). Elija un crédito de la lista.`
          )
          return { ok: false }
        }

        const pagoData = {
          cedula_cliente: cedulaLookup,
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
        const status = err?.response?.status
        const is409 = status === 409
        const is422 = status === 422
        if (is409) {
          setDuplicadosPendientesRevisar((prev) => new Set([...prev, row._rowIndex]))
          addToast(
            'warning',
            `Documento duplicado. Use "Revisar Pagos" para registrarlo en observaciones.`
          )
          return { ok: false, was409: true }
        }
        if (is422 && (typeof msg === 'string' && msg.includes('prestamo_id'))) {
          addToast(
            'error',
            `Fila ${row._rowIndex}: Crédito inválido. Elija un crédito de la lista (no use el número de documento).`
          )
          return { ok: false }
        }
        addToast('error', `Fila ${row._rowIndex}: ${msg}`)
        return { ok: false }
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [prestamosPorCedula, addToast, refreshPagos, onSuccess, onClose, getValidRows]
  )

  const sendToRevisarPagos = useCallback(
    async (row: PagoExcelRow, onNavigate: () => void): Promise<boolean> => {
      setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: true }))
      let numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''
      try {
        if (row._hasErrors) {
          const camposConProblema = Object.entries(row._validation || {}).filter(([, v]) => !v.isValid).map(([field]) => field)
          const observaciones = camposConProblema.join(',')
          await pagoConErrorService.create({
            cedula_cliente: cedulaLookupParaFila(row.cedula || '', row.numero_documento || ''),
            prestamo_id: null,
            fecha_pago: convertirFechaParaBackendPago(row.fecha_pago) || new Date().toISOString().split('T')[0],
            monto_pagado: Number(row.monto_pagado) || 0,
            numero_documento: numeroDoc || null,
            institucion_bancaria: null,
            notas: null,
            conciliado: row.conciliado ?? false,
            observaciones: observaciones || undefined,
            fila_origen: row._rowIndex,
          })
        } else {
          let observaciones: string
          if (duplicadosPendientesRevisar.has(row._rowIndex)) {
            observaciones = 'duplicado'
          } else {
            const cedulaLookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
            const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
            const prestamos = prestamosPorCedula[cedulaLookup] || prestamosPorCedula[cedulaSinGuion] || prestamosPorCedula[cedulaLookup.toUpperCase()] || prestamosPorCedula[cedulaLookup.toLowerCase()] || []
            observaciones = prestamos.length === 0 ? 'sin_prestamo' : prestamos.length > 1 ? 'multiples_prestamos' : 'revisar'
          }
          await pagoConErrorService.create({
            cedula_cliente: cedulaLookupParaFila(row.cedula || '', row.numero_documento || ''),
            prestamo_id: null,
            fecha_pago: convertirFechaParaBackendPago(row.fecha_pago) || new Date().toISOString().split('T')[0],
            monto_pagado: Number(row.monto_pagado) || 0,
            numero_documento: numeroDoc || null,
            institucion_bancaria: null,
            notas: null,
            conciliado: row.conciliado ?? false,
            observaciones: observaciones || undefined,
            fila_origen: row._rowIndex,
          })
        }
        setEnviadosRevisar((prev) => new Set([...prev, row._rowIndex]))
        setDuplicadosPendientesRevisar((prev) => {
          const next = new Set(prev)
          next.delete(row._rowIndex)
          return next
        })
        refreshPagos()
        addToast(row._hasErrors ? 'warning' : 'success', row._hasErrors ? 'Pago enviado a Revisar Pagos con errores. Corr?gelo all?.' : 'Pago enviado a Revisar Pagos')
        onNavigate()
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
            ? `Fila ${row._rowIndex}: ${msg} Cambie el N? documento o verifique si ya se guard?.`
            : `Fila ${row._rowIndex}: ${msg}`
        )
        return false
      } finally {
        setSavingProgress((prev) => ({ ...prev, [row._rowIndex]: false }))
      }
    },
    [addToast, refreshPagos, duplicadosPendientesRevisar, prestamosPorCedula]
  )

  const getDuplicadosRows = useCallback((): PagoExcelRow[] => {
    return excelData.filter((row) => duplicadosPendientesRevisar.has(row._rowIndex))
  }, [excelData, duplicadosPendientesRevisar])

  const sendDuplicadosToRevisarPagos = useCallback(async () => {
    const rows = getDuplicadosRows()
    if (rows.length === 0) {
      addToast('warning', 'No hay duplicados pendientes')
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
    if (ok > 0) addToast('success', "${ok} duplicado(s) enviado(s) a Revisar Pagos")
    if (fail > 0) addToast('error', "${fail} fallaron")
    if (ok > 0) refreshPagos()
  }, [getDuplicadosRows, serviceStatus, sendToRevisarPagos, addToast, refreshPagos])

  const sendAllToRevisarPagos = useCallback(async () => {
    const rows = getRowsToRevisarPagos()
    if (rows.length === 0) {
      addToast('warning', 'No hay filas para enviar a Revisar Pagos')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexi?n')
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
      addToast('warning', 'No hay pagos v?lidos para guardar')
      return
    }
    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexi?n')
      return
    }
    const toSave = valid.filter((row) => {
      if (duplicadosPendientesRevisar.has(row._rowIndex)) return false
      const cedulaLookup = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
      const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
      const prestamosActivos =
        prestamosPorCedula[cedulaLookup] || prestamosPorCedula[cedulaSinGuion] || prestamosPorCedula[cedulaLookup.toUpperCase()] || prestamosPorCedula[cedulaLookup.toLowerCase()] || []
      if (prestamosActivos.length > 1 && !row.prestamo_id) return false
      return true
    })
    const omitidos = valid.length - toSave.length
    if (toSave.length === 0) {
      addToast(
        'warning',
        omitidos > 0
          ? `${omitidos} fila(s) pendientes: guarde uno a uno, corrija o env?e a Revisar Pagos.`
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
        addToast('warning', `${duplicados} duplicado(s). Use "Enviar duplicados" para registrarlos en observaciones.`)
      }
    }
    if (omitidos > 0) {
      addToast('warning', `${omitidos} fila(s) omitidas: guarde uno a uno, corrija o env?e a Revisar Pagos.`)
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
      addToast('warning', 'Quedan filas pendientes. Use "Revisar Pagos" en cada una o corr?jalas.')
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
          alert('Archivo demasiado grande. M?ximo 10 MB')
          return
        }
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
        const headerRow = (jsonData[0] as unknown[]) ?? []
        const cols = (() => {
          const h = (i: number) => String(headerRow[i] ?? '').toLowerCase().trim()
          const match = (i: number, ...keys: string[]) => keys.some(k => h(i).includes(k))
          let cedula = 0, fecha = 1, monto = 2, documento = 3, prestamo = 4, conciliacion = 5
          for (let i = 0; i < Math.max(headerRow.length, 6); i++) {
            if (match(i, 'cedula', 'cÃ©dula')) cedula = i
            if (match(i, 'fecha', 'fecha_pago', 'date')) fecha = i
            if (match(i, 'monto', 'monto_pagado', 'amount')) monto = i
            if (match(i, 'documento', 'numero_documento', 'nÂº documento', 'n documento', 'doc', 'referencia')) documento = i
            if (match(i, 'prÃ©stamo', 'prestamo', 'credito', 'crÃ©dito')) prestamo = i
            if (match(i, 'conciliacion', 'conciliaciÃ³n')) conciliacion = i
          }
          return { cedula, fecha, monto, documento, prestamo, conciliacion }
        })()

        for (let i = 1; i < jsonData.length; i++) {
          if (!isMounted()) return
          const row = jsonData[i] as unknown[]
          if (!row || row.every((c) => c == null || c === '')) continue

          const cedula = (row[cols.cedula] != null ? String(row[cols.cedula]).trim() : '').trim() || ''
          const fechaPago = convertirFechaExcelPago(row[cols.fecha])
          const montoRaw = String(row[cols.monto] || 0).replace(',', '.')
          const monto = parseFloat(montoRaw) || 0
          const numeroDoc = normalizarNumeroDocumento(row[cols.documento])
          const prestamoIdRaw = row[cols.prestamo]
          const conciliacionRawCol4 = (row[cols.prestamo]?.toString() || '').trim().toUpperCase()
          const conciliacionRawCol5 = (row[cols.conciliacion]?.toString() || '').trim().toUpperCase()
          const isConciliacionCol4 = ['SI', 'S?', 'NO', '1', '0'].includes(conciliacionRawCol4)
          const prestamoId =
            !isConciliacionCol4 && prestamoIdRaw != null && String(prestamoIdRaw).trim() !== ''
              ? parseInt(String(prestamoIdRaw).trim(), 10)
              : null
          const conciliacionRaw = (isConciliacionCol4 ? conciliacionRawCol4 : conciliacionRawCol5).trim()
          // Por defecto: Conciliaci?n = S?. Solo No si expl?citamente "NO" (evitar que 0/celda vac?a = No).
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

        // Asignar Crédito en cuanto lleguen los préstamos (misma lógica que el efecto)
        const uniqueCedulasSet = new Set<string>()
        processed.forEach((r) => {
          const fromCedula = cedulaParaLookup(r.cedula)
          const fromDoc = cedulaParaLookup(r.numero_documento)
          const lookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
          ;[fromCedula, fromDoc, lookup].forEach((c) => {
            if (c && c.length >= 5 && looksLikeCedula(c)) uniqueCedulasSet.add(c)
          })
        })
        // Normalizar igual que el backend (sin guión) para que las claves del map coincidan con la respuesta
        const uniqueCedulas = [...uniqueCedulasSet].map((c) => (c || '').trim().replace(/-/g, '')).filter((c) => c.length >= 5 && looksLikeCedula(c))
        if (uniqueCedulas.length > 0) {
          setCedulasBuscando((prev) => new Set([...prev, ...uniqueCedulas]))
          const prestamoIdVacio = (v: unknown) =>
            v == null || v === undefined || v === '' || v === 'none' || v === 0 || (typeof v === 'number' && Number.isNaN(v))
          const buildMap = (
            batchOrResults: Record<string, any[]> | any[][]
          ): Record<string, Array<{ id: number; estado: string }>> => {
            const map: Record<string, Array<{ id: number; estado: string }>> = {}
            const isResultsArray = Array.isArray(batchOrResults) && batchOrResults.length > 0 && Array.isArray((batchOrResults as any[])[0])
            if (isResultsArray) {
              const results = batchOrResults as any[][]
              uniqueCedulas.forEach((cedula, i) => {
                const prestamos = (results[i] || []).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
                )
                const arr = prestamos.map((p: any) => ({ id: p.id, estado: p.estado || '' }))
                map[cedula] = arr
                const cedulaSinGuion = cedula.replace(/-/g, '')
                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr
                map[cedula.toUpperCase()] = arr
                map[cedula.toLowerCase()] = arr
              })
            } else {
              const batch = batchOrResults as Record<string, any[]>
              uniqueCedulas.forEach((cedula) => {
                const prestamos = (batch[cedula] || batch[cedula.replace(/-/g, '')] || []).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
                )
                const arr = prestamos.map((p: any) => ({ id: p.id, estado: p.estado || '' }))
                map[cedula] = arr
                const cedulaSinGuion = cedula.replace(/-/g, '')
                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr
                map[cedula.toUpperCase()] = arr
                map[cedula.toLowerCase()] = arr
              })
            }
            return map
          }
          const fetchPromise = prestamoService
            .getPrestamosByCedulasBatch(uniqueCedulas)
            .then((batch) => buildMap(batch || {}))
          fetchPromise
            .then((map) => {
              if (!isMounted()) return
              setPrestamosPorCedula(map)
              const keysMap = Object.keys(map)
              const fallbackKey = keysMap.length === 1 ? keysMap[0] : null
              // Usar siempre el array local "processed" para evitar race: prev puede estar vacío o desactualizado
              const updated = processed.map((r) => {
                const cedulaLookup = cedulaLookupParaFila(r.cedula || '', r.numero_documento || '')
                const cedulaColNorm = cedulaParaLookup(r.cedula) || (r.cedula || '').trim().replace(/-/g, '')
                const cedulaSinGuion = cedulaLookup.replace(/-/g, '')
                let prestamos =
                  map[cedulaLookup] || map[cedulaSinGuion] || map[cedulaLookup.toUpperCase()] || map[cedulaLookup.toLowerCase()] || []
                if (prestamos.length === 0 && cedulaColNorm)
                  prestamos = map[cedulaColNorm] || map[cedulaColNorm.toUpperCase()] || map[cedulaColNorm.toLowerCase()] || []
                if (prestamos.length === 0 && fallbackKey) prestamos = map[fallbackKey] || []
                if (prestamos.length === 1 && prestamoIdVacio(r.prestamo_id)) return { ...r, prestamo_id: prestamos[0].id }
                return r
              })
              setExcelData(updated)
            })
            .catch(() => {
              if (isMounted()) setPrestamosPorCedula({})
            })
            .finally(() => {
              if (isMounted()) {
                setCedulasBuscando((prev) => {
                  const next = new Set(prev)
                  uniqueCedulas.forEach((c) => next.delete(c))
                  return next
                })
              }
            })
        }
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
    sendDuplicadosToRevisarPagos,
    getRowsToRevisarPagos,
    getDuplicadosRows,
    isSendingAllRevisar,
    enviadosRevisar,
    duplicadosPendientesRevisar,
    onClose,
    removeToast,
  }
}
