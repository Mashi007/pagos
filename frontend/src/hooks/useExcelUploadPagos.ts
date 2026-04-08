/**





 * Hook para carga masiva de pagos desde Excel.





 * Columnas: cedula, fecha, monto, documento, prestamo, conciliacion





 * Solo Prestamo / Credito / ID (plantilla v3)





 * v3: validacion de columnas y montos





 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { invalidatePagosPrestamosRevisionYCuotas } from '../constants/queryKeys'

import { pagoService } from '../services/pagoService'

import {
  pagoConErrorService,
  type PagoConErrorCreate,
} from '../services/pagoConErrorService'

import { prestamoService } from '../services/prestamoService'

import { useIsMounted } from './useIsMounted'

import {
  type PagoExcelRow,
  OBSERVACIONES_POR_CAMPO,
  OBSERVACION_SIN_CREDITO,
  OBSERVACION_MULTIPLES_CREDITOS,
  convertirFechaExcelPago,
  convertirFechaParaBackendPago,
  validatePagoField,
  claveDocumentoExcelCompuesta,
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
  normalizarNumeroDocumento,
  NUMERO_DOCUMENTO_MAX_LEN,
  cedulaParaLookup,
  cedulaLookupParaFila,
  looksLikeDocumentNotCedula,
  parsePrestamoIdFromNumeroCredito,
  institucionBancariaDesdeExcel,
  buscarEnMapaPrestamos,
  linkComprobanteDesdeCeldaExcel,
} from '../utils/pagoExcelValidation'

import { readExcelToJSON } from '../types/exceljs'

const ESTADOS_PRESTAMO_ACTIVO = ['APROBADO', 'DESEMBOLSADO']

// Layout de columnas (primera fila Excel)

const PRESTAMO_ID_MAX = 2147483647

/**
 * Sufijo admin carga masiva: _ + A|P + 4 digitos (mismo archivo vs otro prestamo en BD).
 */
const SUFIJO_VISTO_ARCHIVO_RE = /_[AP]\d{4}$/i

/** Genera token A#### o P#### unicos dentro de `usados`. */
function allocarTokenSufijoVistoArchivo(
  letter: 'A' | 'P',
  usados: Set<string>
): string {
  for (let t = 0; t < 80; t++) {
    const n = Math.floor(Math.random() * 10000)
    const tok = `${letter}${String(n).padStart(4, '0')}`
    if (!usados.has(tok)) {
      usados.add(tok)
      return tok
    }
  }
  const tok = `${letter}${String(Date.now() % 10000).padStart(4, '0')}`
  usados.add(tok)
  return tok
}

/** Si el monto visible antes de guardar es >= este valor, se avisa verificar USD vs Bs. */
const MONTO_MIN_ADVERTENCIA_MONEDA = 2000

function montoFilaParaAdvertenciaMoneda(row: PagoExcelRow): number {
  const n = Number(row.monto_pagado)
  if (!Number.isFinite(n) || n < 0) return 0
  return n
}

function filaRequiereAdvertenciaMontoAlto(row: PagoExcelRow): boolean {
  return montoFilaParaAdvertenciaMoneda(row) >= MONTO_MIN_ADVERTENCIA_MONEDA
}

function codigoDocumentoOpcionalFila(row: PagoExcelRow): string | null {
  const c = String(row.codigo_documento ?? '').trim()

  return c ? c : null
}

/** Mapas de BD tras validar-filas-batch (también en refs para edición en vivo). */
export type MapsValidacionBatchPagos = {
  cedulasExistentesBD: Set<string>
  documentosDuplicadosBD: Set<string>
  detalleDuplicadosBD: Map<string, string>
  prestamoPorDocDupBD: Map<string, number | null>
  pagoPorDocDupBD: Map<string, number>
}

/**
 * Validación de cédula y documento alineada con el batch (sin API).
 * Duplicado en archivo: misma clave compuesta (comprobante + código opcional); si está en
 * `documentosRepetidosArchivoJustificados`, pasa (un comprobante, varias filas/cuotas).
 */
export function applyRowValidationsSync(
  processed: PagoExcelRow[],
  maps: MapsValidacionBatchPagos,
  documentosRepetidosArchivoJustificados: Set<string>
): PagoExcelRow[] {
  const docFreq = new Map<string, number>()
  processed.forEach(r => {
    const clave = claveDocumentoExcelCompuesta(
      r.numero_documento,
      r.codigo_documento ?? null
    )
    if (clave) docFreq.set(clave, (docFreq.get(clave) || 0) + 1)
  })
  const documentosDuplicadosEnArchivo = new Set(
    Array.from(docFreq.entries())
      .filter(([, count]) => count > 1)
      .map(([doc]) => doc)
  )
  const todasCedulas = [
    ...new Set(
      processed
        .map(r => r.cedula.replace(/-/g, '').toUpperCase())
        .filter(c => /^[VEJZ]\d{6,11}$/i.test(c))
    ),
  ]

  return processed.map(r => {
    const docNorm = normalizarNumeroDocumento(r.numero_documento)
    const claveDoc = claveDocumentoExcelCompuesta(
      r.numero_documento,
      r.codigo_documento ?? null
    )
    const {
      _prestamoIdExistenteDuplicadoBD: _omitDup,
      _pagoIdExistenteDuplicadoBD: _omitPagoDup,
      ...restRow
    } = r

    const vCedula = validatePagoField('cedula', r.cedula, {
      cedulasInvalidas: new Set(
        todasCedulas.filter(c => !maps.cedulasExistentesBD.has(c))
      ),
    })

    const esDuplicadoEnArchivo =
      !!claveDoc && documentosDuplicadosEnArchivo.has(claveDoc)
    const esDuplicadoEnBD =
      !!claveDoc && maps.documentosDuplicadosBD.has(claveDoc)

    let vDoc: { isValid: boolean; message?: string }
    if (esDuplicadoEnArchivo) {
      const justificado =
        !!claveDoc && documentosRepetidosArchivoJustificados.has(claveDoc)
      vDoc = {
        isValid: justificado,
        message: 'Documento repetido en este archivo',
      }
    } else if (esDuplicadoEnBD) {
      vDoc = {
        isValid: false,
        message: `Documento ya existe en la base de datos${maps.detalleDuplicadosBD.get(claveDoc) || maps.detalleDuplicadosBD.get(docNorm) || ''}`,
      }
    } else {
      vDoc = validatePagoField('numero_documento', r.numero_documento, {
        documentosEnArchivo: documentosDuplicadosEnArchivo,

        codigoDocumento: r.codigo_documento ?? null,
      })
    }

    const newValidation: Record<
      string,
      { isValid: boolean; message?: string }
    > = {
      ...r._validation,
      cedula: vCedula,
      numero_documento: vDoc,
    }

    const hasErrors =
      !newValidation['cedula']?.isValid ||
      !newValidation['fecha_pago']?.isValid ||
      !newValidation['monto_pagado']?.isValid ||
      !newValidation['numero_documento']?.isValid

    const prestamoDupBd =
      esDuplicadoEnBD && claveDoc
        ? (maps.prestamoPorDocDupBD.get(claveDoc) ??
          maps.prestamoPorDocDupBD.get(docNorm) ??
          null)
        : undefined

    const pagoDupBd =
      esDuplicadoEnBD && claveDoc
        ? (maps.pagoPorDocDupBD.get(claveDoc) ??
          maps.pagoPorDocDupBD.get(docNorm))
        : undefined

    return {
      ...restRow,
      _validation: newValidation,
      _hasErrors: hasErrors,
      ...(prestamoDupBd !== undefined
        ? { _prestamoIdExistenteDuplicadoBD: prestamoDupBd }
        : {}),
      ...(pagoDupBd !== undefined
        ? { _pagoIdExistenteDuplicadoBD: pagoDupBd }
        : {}),
    }
  })
}

/**
 * Si el monto es alto y la fila sigue en USD, se envía como BS para que el backend
 * convierta con tasa de la fecha (evita dejar montos enormes como dólares por error).
 * Alinear con backend: `PAGOS_BS_MONTO_EXENTO_LISTA_CEDULA` (.env del API).
 * Opcional: `VITE_PAGOS_MONTO_AUTO_BS` en build del frontend.
 */
const _envMontoAutoBs = import.meta.env.VITE_PAGOS_MONTO_AUTO_BS
const MONTO_AUTO_APLICAR_TASA_BS =
  _envMontoAutoBs !== undefined &&
  _envMontoAutoBs !== '' &&
  Number.isFinite(Number(_envMontoAutoBs)) &&
  Number(_envMontoAutoBs) > 0
    ? Math.floor(Number(_envMontoAutoBs))
    : 10000

function registroMonedaEfectivoCargaMasiva(row: PagoExcelRow): {
  moneda_registro: 'USD' | 'BS'
  tasa_cambio_manual?: number
  aplicoAutoBs: boolean
} {
  const m = Number(row.monto_pagado) || 0
  const raw = String(row.moneda_registro || 'USD').toUpperCase()
  const esUsd = raw === 'USD' || raw === 'USDT'
  const tm = row.tasa_cambio_manual
  const tasaOk =
    tm != null && Number.isFinite(Number(tm)) && Number(tm) > 0
      ? Number(tm)
      : undefined

  if (Number.isFinite(m) && m >= MONTO_AUTO_APLICAR_TASA_BS && esUsd) {
    return {
      moneda_registro: 'BS',
      ...(tasaOk != null ? { tasa_cambio_manual: tasaOk } : {}),
      aplicoAutoBs: true,
    }
  }

  return {
    moneda_registro: raw === 'BS' ? 'BS' : 'USD',
    ...(tasaOk != null ? { tasa_cambio_manual: tasaOk } : {}),
    aplicoAutoBs: false,
  }
}

function observacionesDesdeCampos(campos: string[]): string {
  if (campos.length === 0) return 'Revisar'

  return campos.map(c => OBSERVACIONES_POR_CAMPO[c] || c).join(' / ')
}

/** Infiere observaciones desde el mensaje de error del backend (422, 400, etc.) */

function observacionesDesdeError(msg: string): string {
  const m = (msg || '').toLowerCase()

  const partes: string[] = []

  if (/fecha_pago|formato.*yyyy-mm-dd|fecha.*invalida/i.test(msg)) {
    partes.push(OBSERVACIONES_POR_CAMPO.fecha_pago)
  } else if (/fecha|date/.test(m))
    partes.push(OBSERVACIONES_POR_CAMPO.fecha_pago)

  if (
    /cedula|cliente|client|not found|no existe|no encontrad|encontrado/.test(m)
  )
    partes.push(OBSERVACIONES_POR_CAMPO.cedula)

  if (/monto|amount|debe ser|greater|positive/i.test(msg))
    partes.push(OBSERVACIONES_POR_CAMPO.monto_pagado)

  if (/prestamo_id|prestamo.*entre|entre 1 y|id fuera|numero/i.test(msg)) {
    partes.push(OBSERVACIONES_POR_CAMPO.prestamo_id)
  } else if (/prestamo|credito|credito\/id/i.test(m))
    partes.push(OBSERVACIONES_POR_CAMPO.prestamo_id)

  if (/documento|duplicado|already exists|ya existe/.test(m))
    partes.push('Duplicado BD (documento ya existe en base de datos)')

  return partes.length > 0
    ? partes.join(' / ')
    : 'Revisar (error de validacion)'
}

export interface ExcelUploaderPagosProps {
  onClose: () => void

  onSuccess?: () => void
}

export function useExcelUploadPagos({
  onClose,
  onSuccess,
}: ExcelUploaderPagosProps) {
  const queryClient = useQueryClient()

  const isMounted = useIsMounted()

  const [isDragging, setIsDragging] = useState(false)

  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const [excelData, setExcelData] = useState<PagoExcelRow[]>([])

  const excelDataRef = useRef<PagoExcelRow[]>([])

  useEffect(() => {
    excelDataRef.current = excelData
  }, [excelData])

  useEffect(() => {
    return () => {
      if (debounceRevalidarBatchBdRef.current) {
        clearTimeout(debounceRevalidarBatchBdRef.current)
      }
    }
  }, [])

  const [isProcessing, setIsProcessing] = useState(false)

  const [showPreview, setShowPreview] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  /** Evita doble peticion al subir el mismo archivo */

  const batchRequestedForCedulasRef = useRef<string | null>(null)

  const cedulasExistentesBDRef = useRef<Set<string>>(new Set())

  const documentosDuplicadosBDRef = useRef<Set<string>>(new Set())

  const detalleDuplicadosBDRef = useRef<Map<string, string>>(new Map())

  const prestamoPorDocDupBDRef = useRef<Map<string, number | null>>(new Map())

  const pagoPorDocDupBDRef = useRef<Map<string, number>>(new Map())

  const [
    documentosRepetidosArchivoJustificados,
    setDocumentosRepetidosArchivoJustificados,
  ] = useState<string[]>([])

  const documentosRepetidosArchivoJustificadosRef = useRef<Set<string>>(
    new Set()
  )

  useEffect(() => {
    documentosRepetidosArchivoJustificadosRef.current = new Set(
      documentosRepetidosArchivoJustificados
    )
  }, [documentosRepetidosArchivoJustificados])

  useEffect(() => {
    const filas = excelDataRef.current
    if (!filas.length) return
    const maps: MapsValidacionBatchPagos = {
      cedulasExistentesBD: cedulasExistentesBDRef.current,
      documentosDuplicadosBD: documentosDuplicadosBDRef.current,
      detalleDuplicadosBD: detalleDuplicadosBDRef.current,
      prestamoPorDocDupBD: prestamoPorDocDupBDRef.current,
      pagoPorDocDupBD: pagoPorDocDupBDRef.current,
    }
    setExcelData(
      applyRowValidationsSync(
        filas,
        maps,
        new Set(documentosRepetidosArchivoJustificados)
      )
    )
  }, [documentosRepetidosArchivoJustificados])

  const debounceRevalidarBatchBdRef = useRef<ReturnType<
    typeof setTimeout
  > | null>(null)

  const [savedRows, setSavedRows] = useState<Set<number>>(new Set())

  const [enviadosRevisar, setEnviadosRevisar] = useState<Set<number>>(new Set())

  const [duplicadosPendientesRevisar, setDuplicadosPendientesRevisar] =
    useState<Set<number>>(new Set())

  const [isSavingIndividual, setIsSavingIndividual] = useState(false)

  const [isSendingAllRevisar, setIsSendingAllRevisar] = useState(false)

  const [savingProgress, setSavingProgress] = useState<Record<number, boolean>>(
    {}
  )

  const [batchProgress, setBatchProgress] = useState<{
    sent: number
    total: number
  } | null>(null)

  const [serviceStatus, setServiceStatus] = useState<
    'unknown' | 'online' | 'offline'
  >('unknown')

  const [toasts, setToasts] = useState<
    Array<{
      id: string
      type: 'error' | 'warning' | 'success' | 'info'
      message: string
    }>
  >([])

  const [pagosConErrores, setPagosConErrores] = useState<
    Array<{
      id: number

      fila_origen: number

      cedula: string

      monto: number

      errores: string[]

      accion: string
    }>
  >([])

  const [registrosConError, setRegistrosConError] = useState(0)

  const addToast = useCallback(
    (type: 'error' | 'warning' | 'success' | 'info', message: string) => {
      const id = Date.now().toString() + Math.random().toString(36).slice(2)

      setToasts(prev => [...prev, { id, type, message }])

      const ms = type === 'info' ? 6500 : 3500
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), ms)
    },
    []
  )

  const removeToast = useCallback((toastId: string) => {
    setToasts(prev => prev.filter(t => t.id !== toastId))
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

  // Incluir todas las columnas relevantes del Excel

  const looksLikeCedula = (c: string) => {
    const normalized = (c || '').replace(/-/g, '').trim()
    // Aceptar: V/E/J/Z + dígitos, O solo dígitos (para búsquedas fallback)
    return /^[VEJZ]\d{6,11}$/i.test(normalized) || /^\d{6,11}$/.test(normalized)
  }

  const cedulasUnicas = useMemo(() => {
    const candidates = new Set<string>()

    excelData.forEach(r => {
      const fromCedula = cedulaParaLookup(r.cedula)

      const fromDoc = cedulaParaLookup(r.numero_documento)

      const lookup = cedulaLookupParaFila(
        r.cedula || '',
        r.numero_documento || ''
      )

      ;[fromCedula, fromDoc, lookup].forEach(c => {
        if (c && c.length >= 5 && looksLikeCedula(c)) candidates.add(c)
      })
    })

    // Normalizar (sin guiones ni espacios extra)

    const result = [...candidates]
      .map(c => (c || '').trim().replace(/-/g, ''))
      .filter(c => c.length >= 5 && looksLikeCedula(c))

    // DEBUG: Log cédulas siendo buscadas
    if (result.length > 0 && typeof window !== 'undefined') {
      console.log('[ExcelUpload] Cédulas únicas para búsqueda:', result)
    }

    return result
  }, [excelData])

  const [prestamosPorCedula, setPrestamosPorCedula] = useState<
    Record<string, Array<{ id: number; estado: string }>>
  >({})

  const [cedulasBuscando, setCedulasBuscando] = useState<Set<string>>(new Set())

  const mergePrestamosEnMap = useCallback(
    (cedula: string, prestamos: Array<{ id: number; estado: string }>) => {
      const activos = prestamos.filter(p =>
        ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
      )

      const arr = activos.map(p => ({ id: p.id, estado: p.estado || '' }))

      setPrestamosPorCedula(prev => {
        const next = { ...prev }

        next[cedula] = arr

        const cedulaSinGuion = cedula.replace(/-/g, '')

        if (cedulaSinGuion !== cedula) next[cedulaSinGuion] = arr

        return next
      })
    },

    []
  )

  // Buscar fila de encabezados

  const fetchSingleCedula = useCallback(
    async (cedula: string): Promise<boolean> => {
      const cedulaNorm = cedulaParaLookup(cedula) || (cedula || '').trim()

      if (cedulaNorm.length < 5) return false

      const cedulaSinGuion = cedulaNorm.replace(/-/g, '')

      setCedulasBuscando(prev => new Set([...prev, cedulaNorm]))

      try {
        const prestamos = await prestamoService.getPrestamosByCedula(cedulaNorm)

        mergePrestamosEnMap(
          cedulaNorm,
          (prestamos || []).map((p: any) => ({
            id: p.id,
            estado: p.estado || '',
          }))
        )

        return true
      } catch {
        return false
      } finally {
        setCedulasBuscando(prev => {
          const next = new Set(prev)

          next.delete(cedulaNorm)

          return next
        })
      }
    },

    [mergePrestamosEnMap]
  )

  // Carga inicial: buscar Prestamos

  // Si processExcelFile ya pidio prestamo, no repetir

  useEffect(() => {
    if (!showPreview || cedulasUnicas.length === 0) {
      batchRequestedForCedulasRef.current = null

      setPrestamosPorCedula(prev => (Object.keys(prev).length ? {} : prev))

      return
    }

    const cedulasKey = cedulasUnicas.join(',')

    if (batchRequestedForCedulasRef.current === cedulasKey) return

    batchRequestedForCedulasRef.current = cedulasKey

    setCedulasBuscando(prev => new Set([...prev, ...cedulasUnicas]))

    let cancelled = false

    const timer = setTimeout(() => {
      prestamoService

        .getPrestamosByCedulasBatch(cedulasUnicas)

        .then(batch => {
          const map: Record<string, Array<{ id: number; estado: string }>> = {}

          console.log(
            '[ExcelUpload v2.1] Batch response keys:',
            Object.keys(batch || {}).slice(0, 15),
            'total:',
            Object.keys(batch || {}).length
          )

          cedulasUnicas.forEach(cedula => {
            const raw = batch[cedula] || batch[cedula.replace(/-/g, '')] || []

            const prestamos = raw.filter((p: any) =>
              ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
            )

            const arr = prestamos.map((p: any) => ({
              id: p.id,
              estado: p.estado || '',
            }))

            console.log(
              `[ExcelUpload v2.1] ${cedula}: raw=${raw.length} activos=${arr.length}`,
              arr
                .map(
                  (a: { id: number; estado: string }) => `${a.id}(${a.estado})`
                )
                .join(',')
            )

            map[cedula] = arr

            const cedulaSinGuion = cedula.replace(/-/g, '')

            if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr

            map[cedula.toUpperCase()] = arr

            map[cedula.toLowerCase()] = arr

            // Si la cédula es V+dígitos, también guardar sin V (para búsquedas que vienen sin V)
            if (/^V\d{6,11}$/i.test(cedula)) {
              const sinV = cedula.slice(1)
              map[sinV] = arr
              map[sinV.toUpperCase()] = arr
              map[sinV.toLowerCase()] = arr
            }
          })

          console.log(
            '[ExcelUpload v2.1] Mapa construido, claves:',
            Object.keys(map).length,
            Object.keys(map).slice(0, 15)
          )

          return map
        })

        .then(map => {
          if (!cancelled) {
            setPrestamosPorCedula(prev => {
              const merged = { ...prev, ...map }
              console.log(
                '[ExcelUpload v2.1] prestamosPorCedula actualizado: prev=',
                Object.keys(prev).length,
                'new=',
                Object.keys(map).length,
                'merged=',
                Object.keys(merged).length
              )
              return merged
            })

            setExcelData(prev => prev.map(r => r))
          }
        })

        .catch(err => {
          console.error('[ExcelUpload] Error batch principal:', err)
        })

        .finally(() => {
          if (!cancelled) {
            setCedulasBuscando(prev => {
              const next = new Set(prev)

              cedulasUnicas.forEach(c => next.delete(c))

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

  // Fallback: si tras 1.5s el batch no lleno prestamos para algunas cedulas, buscar en un solo batch (evita N GETs individuales)

  useEffect(() => {
    if (!showPreview || excelData.length === 0) return

    const timer = setTimeout(() => {
      const cedulasFaltantes = cedulasUnicas.filter(cedula => {
        if (cedula.length < 5 || cedulasBuscando.has(cedula)) return false

        const sinGuion = cedula.replace(/-/g, '')
        const alreadyQueried =
          cedula in prestamosPorCedula ||
          sinGuion in prestamosPorCedula ||
          cedula.toUpperCase() in prestamosPorCedula ||
          cedula.toLowerCase() in prestamosPorCedula

        return !alreadyQueried
      })

      if (cedulasFaltantes.length === 0) return

      setCedulasBuscando(prev => new Set([...prev, ...cedulasFaltantes]))

      prestamoService

        .getPrestamosByCedulasBatch(cedulasFaltantes)

        .then(batch => {
          const map: Record<string, Array<{ id: number; estado: string }>> = {}

          cedulasFaltantes.forEach(cedula => {
            const prestamos = (
              batch[cedula] ||
              batch[cedula.replace(/-/g, '')] ||
              []
            ).filter(
              (p: any) =>
                p &&
                ESTADOS_PRESTAMO_ACTIVO.includes((p.estado || '').toUpperCase())
            )

            const arr = prestamos.map((p: any) => ({
              id: p.id,
              estado: p.estado || '',
            }))

            map[cedula] = arr

            const cedulaSinGuion = cedula.replace(/-/g, '')

            if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr

            map[cedula.toUpperCase()] = arr

            map[cedula.toLowerCase()] = arr

            // Si la cédula es V+dígitos, también guardar sin V (para búsquedas que vienen sin V)
            if (/^V\d{6,11}$/i.test(cedula)) {
              const sinV = cedula.slice(1)
              map[sinV] = arr
              map[sinV.toUpperCase()] = arr
              map[sinV.toLowerCase()] = arr
            }
          })

          setPrestamosPorCedula(prev => ({ ...prev, ...map }))
        })

        .finally(() => {
          setCedulasBuscando(prev => {
            const next = new Set(prev)

            cedulasFaltantes.forEach(c => next.delete(c))

            return next
          })
        })
    }, 1500)

    return () => clearTimeout(timer)
  }, [showPreview, excelData.length, cedulasUnicas.join(',')])

  const refreshPagos = useCallback(() => {
    void invalidatePagosPrestamosRevisionYCuotas(queryClient, {
      includeDashboardMenu: true,
    })
  }, [queryClient])

  const getValidRows = useCallback((): PagoExcelRow[] => {
    return excelData.filter(
      r =>
        !r._hasErrors &&
        !savedRows.has(r._rowIndex) &&
        !enviadosRevisar.has(r._rowIndex)
    )
  }, [excelData, savedRows, enviadosRevisar])

  const getRowsToRevisarPagos = useCallback((): PagoExcelRow[] => {
    return excelData.filter(row => {
      if (savedRows.has(row._rowIndex) || enviadosRevisar.has(row._rowIndex))
        return false

      if (duplicadosPendientesRevisar.has(row._rowIndex)) return true

      if (row._hasErrors) return true

      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const prestamosActivos = buscarEnMapaPrestamos(
        cedulaLookup,
        prestamosPorCedula
      )

      return prestamosActivos.length !== 1
    })
  }, [
    excelData,
    savedRows,
    enviadosRevisar,
    duplicadosPendientesRevisar,
    prestamosPorCedula,
  ])

  const saveRowIfValid = useCallback(
    async (row: PagoExcelRow): Promise<boolean> => {
      const currentRow =
        excelData.find(r => r._rowIndex === row._rowIndex) ?? row

      if (currentRow._hasErrors) {
        return false
      }

      try {
        const cedulaLookup = cedulaLookupParaFila(
          row.cedula || '',
          row.numero_documento || ''
        )

        const prestamosActivos = buscarEnMapaPrestamos(
          cedulaLookup,
          prestamosPorCedula
        )

        let prestamoId: number | null = currentRow.prestamo_id

        if (!prestamoId && prestamosActivos.length === 1) {
          prestamoId = prestamosActivos[0].id
        }

        // Solo enviar prestamo_id que exista en la lista de créditos de esta cédula (evita números incorrectos del Excel)

        if (
          prestamoId != null &&
          prestamosActivos.length > 0 &&
          !prestamosActivos.some(p => p.id === prestamoId)
        ) {
          prestamoId =
            prestamosActivos.length === 1 ? prestamosActivos[0].id : null
        }

        if (prestamosActivos.length > 1 && !prestamoId) {
          return false
        }

        const numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

        const fechaFormato =
          convertirFechaParaBackendPago(row.fecha_pago) ||
          new Date().toISOString().split('T')[0]

        const fechaDDMMYYYY = fechaFormato.split('-').reverse().join('-')

        const regMonFila = registroMonedaEfectivoCargaMasiva(currentRow)
        if (regMonFila.aplicoAutoBs) {
          addToast(
            'info',
            `Fila ${row._rowIndex}: monto ≥ ${MONTO_AUTO_APLICAR_TASA_BS.toLocaleString('es-VE')}: se aplicará tasa BCV (bolívares) y se guardará el equivalente en USD.`
          )
        } else if (filaRequiereAdvertenciaMontoAlto(currentRow)) {
          const m = montoFilaParaAdvertenciaMoneda(currentRow)
          const mon = String(currentRow.moneda_registro || 'USD').toUpperCase()
          addToast(
            'warning',
            `Fila ${row._rowIndex}: monto ${m.toLocaleString('es-VE')} (${mon}). Verifique que la moneda sea la correcta (USD o Bs.): si no coincide con el comprobante, el importe quedará mal y puede quedar muy alto.`
          )
        }

        await pagoService.guardarFilaEditable({
          cedula: cedulaLookup,

          prestamo_id: prestamoId,

          monto_pagado: Number(row.monto_pagado) || 0,

          fecha_pago: fechaDDMMYYYY,

          numero_documento: numeroDoc || null,

          codigo_documento: codigoDocumentoOpcionalFila(currentRow),

          moneda_registro: regMonFila.moneda_registro,

          ...(regMonFila.tasa_cambio_manual != null
            ? { tasa_cambio_manual: regMonFila.tasa_cambio_manual }
            : {}),
        })

        setSavedRows(prev => new Set([...prev, row._rowIndex]))

        setExcelData(prev => prev.filter(r => r._rowIndex !== row._rowIndex))

        refreshPagos()

        return true
      } catch (err: any) {
        const detail = err?.response?.data?.detail

        const msg = Array.isArray(detail)
          ? detail.map((d: any) => d.msg || d.message).join(' ')
          : detail || err?.message || 'Error al guardar'

        addToast(
          'error',
          typeof msg === 'string' ? msg : 'Error al guardar la fila'
        )

        return false
      }
    },

    [prestamosPorCedula, refreshPagos, addToast, excelData]
  )

  const saveIndividualPago = useCallback(
    async (
      row: PagoExcelRow,
      opts?: { skipToast?: boolean; skipRefresh?: boolean }
    ): Promise<{ ok: boolean; was409?: boolean }> => {
      const currentRow =
        excelData.find(r => r._rowIndex === row._rowIndex) ?? row

      if (currentRow._hasErrors) {
        addToast('error', 'Hay errores en esta fila.')

        return { ok: false }
      }

      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const prestamosActivos = buscarEnMapaPrestamos(
        cedulaLookup,
        prestamosPorCedula
      )

      if (prestamosActivos.length > 1 && !currentRow.prestamo_id) {
        addToast(
          'error',
          `Fila ${row._rowIndex}: La cédula no tiene préstamo registrado.`
        )

        return { ok: false }
      }

      if (prestamosActivos.length === 0 && !currentRow.prestamo_id) {
        addToast(
          'warning',
          'Fila ' + row._rowIndex + ': No hay credito asignado.'
        )
      }

      setSavingProgress(prev => ({ ...prev, [row._rowIndex]: true }))

      try {
        let prestamoId: number | null = currentRow.prestamo_id

        if (!prestamoId && prestamosActivos.length === 1) {
          prestamoId = prestamosActivos[0].id
        }

        // Solo enviar prestamo_id que exista en la lista de créditos de esta cédula (evita números incorrectos del Excel)

        if (
          prestamoId != null &&
          prestamosActivos.length > 0 &&
          !prestamosActivos.some(p => p.id === prestamoId)
        ) {
          prestamoId =
            prestamosActivos.length === 1 ? prestamosActivos[0].id : null
        }

        let numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

        if (
          prestamoId != null &&
          (prestamoId < 1 || prestamoId > PRESTAMO_ID_MAX)
        ) {
          addToast(
            'error',
            'Fila ' + row._rowIndex + ': El valor del credito no es valido.'
          )

          return { ok: false }
        }

        const regMon = registroMonedaEfectivoCargaMasiva(row)

        const pagoData = {
          cedula_cliente: cedulaLookup,

          prestamo_id: prestamoId,

          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],

          monto_pagado: Number(row.monto_pagado) || 0,

          numero_documento: numeroDoc || '',

          codigo_documento: codigoDocumentoOpcionalFila(row),

          institucion_bancaria: institucionBancariaDesdeExcel(
            row.institucion_bancaria ?? undefined
          ),

          notas: null,

          conciliado: !!row.conciliado,

          moneda_registro: regMon.moneda_registro,

          ...(regMon.tasa_cambio_manual != null
            ? { tasa_cambio_manual: regMon.tasa_cambio_manual }
            : {}),

          ...(() => {
            const lc = linkComprobanteDesdeCeldaExcel(
              String(row.link_comprobante ?? '').trim()
            )
            return lc ? { link_comprobante: lc } : {}
          })(),
        }

        const montoGuardar = Number(row.monto_pagado) || 0
        if (!opts?.skipToast) {
          if (regMon.aplicoAutoBs) {
            addToast(
              'info',
              `Fila ${row._rowIndex}: monto ≥ ${MONTO_AUTO_APLICAR_TASA_BS.toLocaleString('es-VE')}: se aplicará tasa Bs.→USD según la fecha de pago.`
            )
          } else if (montoGuardar >= MONTO_MIN_ADVERTENCIA_MONEDA) {
            const mon = String(row.moneda_registro || 'USD').toUpperCase()
            addToast(
              'warning',
              `Fila ${row._rowIndex}: monto ${montoGuardar.toLocaleString('es-VE')} (${mon}). Verifique que la moneda sea la correcta (USD o Bs.): si no coincide con el comprobante, el importe quedará mal y puede quedar muy alto.`
            )
          }
        }

        await pagoService.createPago(pagoData as any)

        setSavedRows(prev => new Set([...prev, row._rowIndex]))

        setDuplicadosPendientesRevisar(prev => {
          const next = new Set(prev)

          next.delete(row._rowIndex)

          return next
        })

        // REMOVER fila de la tabla editable (ya se guardo)

        setExcelData(prev => prev.filter(r => r._rowIndex !== row._rowIndex))

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

        const msg = Array.isArray(detail)
          ? detail.map((d: any) => d.msg || d.message).join(' ')
          : detail || err?.message || 'Error al guardar'

        const status = err?.response?.status

        const is409 = status === 409

        const is422 = status === 422

        if (is409) {
          setDuplicadosPendientesRevisar(
            prev => new Set([...prev, row._rowIndex])
          )

          const numeroDoc =
            normalizarNumeroDocumento(row.numero_documento) || ''

          const cedulaR = cedulaLookupParaFila(
            row.cedula || '',
            row.numero_documento || ''
          )

          const prestamosR = buscarEnMapaPrestamos(cedulaR, prestamosPorCedula)

          const prestamoIdRevisar =
            row.prestamo_id != null &&
            prestamosR.some(p => p.id === row.prestamo_id)
              ? row.prestamo_id
              : null

          try {
            await pagoConErrorService.create({
              cedula_cliente: cedulaR,

              prestamo_id: prestamoIdRevisar,

              fecha_pago:
                convertirFechaParaBackendPago(row.fecha_pago) ||
                new Date().toISOString().split('T')[0],

              monto_pagado: Number(row.monto_pagado) || 0,

              numero_documento: numeroDoc || null,

              codigo_documento: codigoDocumentoOpcionalFila(row),

              institucion_bancaria: institucionBancariaDesdeExcel(
                row.institucion_bancaria ?? undefined
              ),

              notas: null,

              conciliado: !!row.conciliado,

              observaciones:
                'Duplicado BD (documento ya existe en base de datos)',

              fila_origen: row._rowIndex,
            })

            setEnviadosRevisar(prev => new Set([...prev, row._rowIndex]))

            setDuplicadosPendientesRevisar(prev => {
              const next = new Set(prev)

              next.delete(row._rowIndex)

              return next
            })

            queryClient.invalidateQueries({
              queryKey: ['pagos-con-errores'],
              exact: false,
            })

            if (!opts?.skipToast)
              addToast(
                'success',
                `Fila ${row._rowIndex}: Duplicado enviado a Revisar Pagos.`
              )
          } catch (_) {
            if (!opts?.skipToast) {
              addToast(
                'warning',

                `Documento duplicado. Use "Revisar Pagos" o "Enviar duplicados" para registrarlo en observaciones.`
              )
            }
          }

          return { ok: false, was409: true }
        }

        if (is422) {
          const observaciones = observacionesDesdeError(msg)

          const cedulaR = cedulaLookupParaFila(
            row.cedula || '',
            row.numero_documento || ''
          )

          const prestamosR = buscarEnMapaPrestamos(cedulaR, prestamosPorCedula)

          const prestamoIdRevisar =
            row.prestamo_id != null &&
            prestamosR.some(p => p.id === row.prestamo_id)
              ? row.prestamo_id
              : null

          try {
            await pagoConErrorService.create({
              cedula_cliente: cedulaR,

              prestamo_id: prestamoIdRevisar,

              fecha_pago:
                convertirFechaParaBackendPago(row.fecha_pago) ||
                new Date().toISOString().split('T')[0],

              monto_pagado: Number(row.monto_pagado) || 0,

              numero_documento:
                normalizarNumeroDocumento(row.numero_documento) || null,

              codigo_documento: codigoDocumentoOpcionalFila(row),

              institucion_bancaria: institucionBancariaDesdeExcel(
                row.institucion_bancaria ?? undefined
              ),

              notas: null,

              conciliado: !!row.conciliado,

              observaciones,

              fila_origen: row._rowIndex,
            })

            queryClient.invalidateQueries({
              queryKey: ['pagos-con-errores'],
              exact: false,
            })

            if (!opts?.skipToast)
              addToast(
                'warning',
                `Fila ${row._rowIndex}: Enviado a Revisar Pagos (${observaciones}).`
              )
          } catch {
            if (!opts?.skipToast)
              addToast('error', `Fila ${row._rowIndex}: ${msg}`)
          }

          return { ok: false }
        }

        addToast('error', `Fila ${row._rowIndex}: ${msg}`)

        return { ok: false }
      } finally {
        setSavingProgress(prev => ({ ...prev, [row._rowIndex]: false }))
      }
    },

    [
      excelData,
      prestamosPorCedula,
      addToast,
      refreshPagos,
      onSuccess,
      onClose,
      getValidRows,
      queryClient,
    ]
  )

  const sendToRevisarPagos = useCallback(
    async (
      row: PagoExcelRow,
      onNavigate: () => void,
      skipRefresh = false,
      skipToast = false,
      skipStateUpdate = false
    ): Promise<boolean> => {
      setSavingProgress(prev => ({ ...prev, [row._rowIndex]: true }))

      let numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

      try {
        const cedulaLk = cedulaLookupParaFila(
          row.cedula || '',
          row.numero_documento || ''
        )
        const prestamosRow = buscarEnMapaPrestamos(cedulaLk, prestamosPorCedula)
        const autoPrestamoId =
          row.prestamo_id ||
          (prestamosRow.length === 1 ? prestamosRow[0].id : null)

        if (row._hasErrors) {
          const camposConProblema = Object.entries(row._validation || {})
            .filter(([, v]) => !v.isValid)
            .map(([field]) => field)

          const observaciones = observacionesDesdeCampos(camposConProblema)

          await pagoConErrorService.create({
            cedula_cliente: cedulaLk,

            prestamo_id: autoPrestamoId || null,

            fecha_pago:
              convertirFechaParaBackendPago(row.fecha_pago) ||
              new Date().toISOString().split('T')[0],

            monto_pagado: Number(row.monto_pagado) || 0,

            numero_documento: numeroDoc || null,

            codigo_documento: codigoDocumentoOpcionalFila(row),

            institucion_bancaria: institucionBancariaDesdeExcel(
              row.institucion_bancaria ?? undefined
            ),

            notas: null,

            conciliado: !!row.conciliado,

            observaciones: observaciones || undefined,

            fila_origen: row._rowIndex,
          })
        } else {
          let observaciones: string

          if (duplicadosPendientesRevisar.has(row._rowIndex)) {
            observaciones = OBSERVACIONES_POR_CAMPO.numero_documento
          } else {
            observaciones =
              prestamosRow.length === 0
                ? OBSERVACION_SIN_CREDITO
                : prestamosRow.length > 1
                  ? OBSERVACION_MULTIPLES_CREDITOS
                  : 'Revisar'
          }

          await pagoConErrorService.create({
            cedula_cliente: cedulaLk,

            prestamo_id: autoPrestamoId || null,

            fecha_pago:
              convertirFechaParaBackendPago(row.fecha_pago) ||
              new Date().toISOString().split('T')[0],

            monto_pagado: Number(row.monto_pagado) || 0,

            numero_documento: numeroDoc || null,

            codigo_documento: codigoDocumentoOpcionalFila(row),

            institucion_bancaria: institucionBancariaDesdeExcel(
              row.institucion_bancaria ?? undefined
            ),

            notas: null,

            conciliado: !!row.conciliado,

            observaciones: observaciones || undefined,

            fila_origen: row._rowIndex,
          })
        }

        if (!skipStateUpdate) {
          setEnviadosRevisar(prev => new Set([...prev, row._rowIndex]))

          setDuplicadosPendientesRevisar(prev => {
            const next = new Set(prev)

            next.delete(row._rowIndex)

            return next
          })
        }

        if (!skipRefresh) refreshPagos()

        if (!skipToast)
          addToast(
            row._hasErrors ? 'warning' : 'success',
            row._hasErrors
              ? 'Pago enviado a Revisar Pagos con errores.'
              : 'Pago guardado correctamente.'
          )

        onNavigate()

        return true
      } catch (err: any) {
        const detail = err?.response?.data?.detail

        const msg = Array.isArray(detail)
          ? detail.map((d: any) => d.msg || d.message).join(' ')
          : detail || err?.message || 'Error al guardar'

        const is409 = err?.response?.status === 409

        addToast(
          'error',

          is409
            ? `Fila ${row._rowIndex}: ${msg} Cambie el valor indicado.`
            : `Fila ${row._rowIndex}: ${msg}`
        )

        return false
      } finally {
        setSavingProgress(prev => ({ ...prev, [row._rowIndex]: false }))
      }
    },

    [addToast, refreshPagos, duplicadosPendientesRevisar, prestamosPorCedula]
  )

  const getDuplicadosRows = useCallback((): PagoExcelRow[] => {
    return excelData.filter(row =>
      duplicadosPendientesRevisar.has(row._rowIndex)
    )
  }, [excelData, duplicadosPendientesRevisar])

  const sendDuplicadosToRevisarPagos = useCallback(async () => {
    const rows = getDuplicadosRows()

    if (rows.length === 0) {
      addToast('warning', 'No hay duplicados pendientes')
      return
    }

    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexion')
      return
    }

    setIsSendingAllRevisar(true)

    setBatchProgress({ sent: 0, total: rows.length })

    const pagosPayload: PagoConErrorCreate[] = []

    for (const row of rows) {
      const numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const psDup = buscarEnMapaPrestamos(cedulaLookup, prestamosPorCedula)
      const autoIdDup =
        row.prestamo_id || (psDup.length === 1 ? psDup[0].id : null)

      if (row._hasErrors) {
        const camposConProblema = Object.entries(row._validation || {})
          .filter(([, v]) => !v.isValid)
          .map(([field]) => field)

        pagosPayload.push({
          cedula_cliente: cedulaLookup,
          prestamo_id: autoIdDup || null,
          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],
          monto_pagado: Number(row.monto_pagado) || 0,
          numero_documento: numeroDoc || null,
          codigo_documento: codigoDocumentoOpcionalFila(row),
          institucion_bancaria: institucionBancariaDesdeExcel(
            row.institucion_bancaria ?? undefined
          ),
          notas: null,
          conciliado: !!row.conciliado,
          observaciones:
            observacionesDesdeCampos(camposConProblema) || undefined,
          fila_origen: row._rowIndex,
        })
      } else {
        const obs = duplicadosPendientesRevisar.has(row._rowIndex)
          ? OBSERVACIONES_POR_CAMPO.numero_documento
          : (() => {
              return psDup.length === 0
                ? OBSERVACION_SIN_CREDITO
                : psDup.length > 1
                  ? OBSERVACION_MULTIPLES_CREDITOS
                  : 'Revisar'
            })()

        pagosPayload.push({
          cedula_cliente: cedulaLookup,
          prestamo_id: autoIdDup || null,
          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],
          monto_pagado: Number(row.monto_pagado) || 0,
          numero_documento: numeroDoc || null,
          codigo_documento: codigoDocumentoOpcionalFila(row),
          institucion_bancaria: institucionBancariaDesdeExcel(
            row.institucion_bancaria ?? undefined
          ),
          notas: null,
          conciliado: !!row.conciliado,
          observaciones: obs || undefined,
          fila_origen: row._rowIndex,
        })
      }
    }

    let ok = 0
    let fail = 0

    try {
      const res = await pagoConErrorService.createBatch(pagosPayload)

      ok = res.ok_count ?? res.results.filter(r => r.success).length

      fail = res.fail_count ?? res.results.filter(r => !r.success).length

      res.results.forEach((r, idx) => {
        if (r.success && rows[idx]) {
          setEnviadosRevisar(p => new Set([...p, rows[idx]._rowIndex]))
          setDuplicadosPendientesRevisar(p => {
            const n = new Set(p)
            n.delete(rows[idx]._rowIndex)
            return n
          })
        }
      })
    } catch {
      fail = rows.length
    }

    setBatchProgress({ sent: rows.length, total: rows.length })

    setBatchProgress(null)

    setIsSendingAllRevisar(false)

    if (ok > 0)
      addToast('success', `${ok} duplicado(s) enviado(s) a Revisar Pagos`)

    if (fail > 0) addToast('error', `${fail} fallaron`)

    if (ok > 0) refreshPagos()
  }, [
    getDuplicadosRows,
    serviceStatus,
    sendToRevisarPagos,
    addToast,
    refreshPagos,
  ])

  const sendAllToRevisarPagos = useCallback(async () => {
    const rows = getRowsToRevisarPagos()

    if (rows.length === 0) {
      addToast('warning', 'No hay filas para enviar a Revisar Pagos')
      return
    }

    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexion')
      return
    }

    setIsSendingAllRevisar(true)

    setBatchProgress({ sent: 0, total: rows.length })

    const pagosPayload: PagoConErrorCreate[] = []

    for (const row of rows) {
      const numeroDoc = normalizarNumeroDocumento(row.numero_documento) || ''

      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const psRow = buscarEnMapaPrestamos(cedulaLookup, prestamosPorCedula)
      const autoId =
        row.prestamo_id || (psRow.length === 1 ? psRow[0].id : null)

      if (row._hasErrors) {
        const camposConProblema = Object.entries(row._validation || {})
          .filter(([, v]) => !v.isValid)
          .map(([field]) => field)

        pagosPayload.push({
          cedula_cliente: cedulaLookup,
          prestamo_id: autoId || null,
          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],
          monto_pagado: Number(row.monto_pagado) || 0,
          numero_documento: numeroDoc || null,
          codigo_documento: codigoDocumentoOpcionalFila(row),
          institucion_bancaria: institucionBancariaDesdeExcel(
            row.institucion_bancaria ?? undefined
          ),
          notas: null,
          conciliado: !!row.conciliado,
          observaciones:
            observacionesDesdeCampos(camposConProblema) || undefined,
          fila_origen: row._rowIndex,
        })
      } else {
        const obs = duplicadosPendientesRevisar.has(row._rowIndex)
          ? OBSERVACIONES_POR_CAMPO.numero_documento
          : (() => {
              return psRow.length === 0
                ? OBSERVACION_SIN_CREDITO
                : psRow.length > 1
                  ? OBSERVACION_MULTIPLES_CREDITOS
                  : 'Revisar'
            })()

        pagosPayload.push({
          cedula_cliente: cedulaLookup,
          prestamo_id: autoId || null,
          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],
          monto_pagado: Number(row.monto_pagado) || 0,
          numero_documento: numeroDoc || null,
          codigo_documento: codigoDocumentoOpcionalFila(row),
          institucion_bancaria: institucionBancariaDesdeExcel(
            row.institucion_bancaria ?? undefined
          ),
          notas: null,
          conciliado: !!row.conciliado,
          observaciones: obs || undefined,
          fila_origen: row._rowIndex,
        })
      }
    }

    let ok = 0
    let fail = 0

    try {
      const res = await pagoConErrorService.createBatch(pagosPayload)

      ok = res.ok_count ?? res.results.filter(r => r.success).length

      fail = res.fail_count ?? res.results.filter(r => !r.success).length

      res.results.forEach((r, idx) => {
        if (r.success && rows[idx]) {
          setEnviadosRevisar(p => new Set([...p, rows[idx]._rowIndex]))
          setDuplicadosPendientesRevisar(p => {
            const n = new Set(p)
            n.delete(rows[idx]._rowIndex)
            return n
          })
        }
      })
    } catch {
      fail = rows.length
    }

    setBatchProgress({ sent: rows.length, total: rows.length })

    setBatchProgress(null)

    setIsSendingAllRevisar(false)

    if (ok > 0 && fail === 0)
      addToast('success', `${ok} enviado(s) a Revisar Pagos.`)
    else if (ok > 0 && fail > 0)
      addToast('warning', `${ok} enviado(s), ${fail} con errores.`)
    else if (fail > 0) addToast('error', `Error al enviar.`)

    if (ok > 0) refreshPagos()
  }, [
    getRowsToRevisarPagos,
    sendToRevisarPagos,
    addToast,
    refreshPagos,
    serviceStatus,
  ])

  const saveAllValid = useCallback(async () => {
    const valid = getValidRows()

    if (valid.length === 0) {
      addToast('warning', 'No hay pagos validos')

      return
    }

    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexion')

      return
    }

    const toSave = valid.filter(row => {
      if (duplicadosPendientesRevisar.has(row._rowIndex)) return false

      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const prestamosActivos = buscarEnMapaPrestamos(
        cedulaLookup,
        prestamosPorCedula
      )

      if (prestamosActivos.length > 1 && !row.prestamo_id) return false

      return true
    })

    const omitidos = valid.length - toSave.length

    if (toSave.length === 0) {
      addToast(
        'warning',

        omitidos > 0
          ? ` fila(s) pendientes: guarde uno a uno, corrija o envie a revisar.`
          : 'No hay filas que cumplan criterios para guardar en lote.'
      )

      return
    }

    // En progreso (no usar success: 200 en batch puede traer ok_count=0 por rechazos por fila)

    const filasAutoBs = toSave.filter(
      r => registroMonedaEfectivoCargaMasiva(r).aplicoAutoBs
    )
    if (filasAutoBs.length > 0) {
      addToast(
        'info',
        `${filasAutoBs.length} pago(s) con monto ≥ ${MONTO_AUTO_APLICAR_TASA_BS.toLocaleString('es-VE')}: se interpretarán en bolívares y se convertirán a USD con la tasa de la fecha de cada pago (o tasa manual de la fila).`
      )
    }

    const filasMontoAlto = toSave.filter(
      r =>
        filaRequiereAdvertenciaMontoAlto(r) &&
        !registroMonedaEfectivoCargaMasiva(r).aplicoAutoBs
    )
    if (filasMontoAlto.length > 0) {
      addToast(
        'warning',
        `${filasMontoAlto.length} pago(s) tienen monto ≥ ${MONTO_MIN_ADVERTENCIA_MONEDA.toLocaleString('es-VE')}. Revise que la moneda (USD o Bs.) coincida con cada comprobante: si no, el importe guardado será incorrecto y puede quedar muy alto.`
      )
    }

    addToast('warning', `Guardando ${toSave.length} pago(s)...`)

    setIsSavingIndividual(true)

    let ok = 0

    let fail = 0

    /** Primer mensaje de error del lote (POST /batch devuelve 200 con fallos por fila). */

    let batchFirstError: string | undefined

    const indicesGuardadosEstaRonda = new Set<number>()

    let duplicados = 0

    const buildPagoData = (row: PagoExcelRow) => {
      const cedulaLookup = cedulaLookupParaFila(
        row.cedula || '',
        row.numero_documento || ''
      )

      const prestamosActivos = buscarEnMapaPrestamos(
        cedulaLookup,
        prestamosPorCedula
      )

      let prestamoId: number | null = row.prestamo_id ?? null

      if (!prestamoId && prestamosActivos.length === 1)
        prestamoId = prestamosActivos[0].id

      if (
        prestamoId != null &&
        prestamosActivos.length > 0 &&
        !prestamosActivos.some(p => p.id === prestamoId)
      )
        prestamoId =
          prestamosActivos.length === 1 ? prestamosActivos[0].id : null

      const regMonBatch = registroMonedaEfectivoCargaMasiva(row)

      return {
        cedula_cliente: cedulaLookup,

        prestamo_id: prestamoId,

        fecha_pago:
          convertirFechaParaBackendPago(row.fecha_pago) ||
          new Date().toISOString().split('T')[0],

        monto_pagado: Number(row.monto_pagado) || 0,

        numero_documento: normalizarNumeroDocumento(row.numero_documento) || '',

        codigo_documento: codigoDocumentoOpcionalFila(row),

        institucion_bancaria: institucionBancariaDesdeExcel(
          row.institucion_bancaria ?? undefined
        ),

        notas: null,

        conciliado: !!row.conciliado,

        moneda_registro: regMonBatch.moneda_registro,

        ...(regMonBatch.tasa_cambio_manual != null
          ? { tasa_cambio_manual: regMonBatch.tasa_cambio_manual }
          : {}),

        ...(() => {
          const lc = linkComprobanteDesdeCeldaExcel(
            String(row.link_comprobante ?? '').trim()
          )
          return lc ? { link_comprobante: lc } : {}
        })(),
      }
    }

    if (toSave.length >= 2) {
      try {
        const pagosPayload = toSave.map(buildPagoData)

        const batchRes = await pagoService.createPagosBatch(pagosPayload)

        batchFirstError = batchRes.results?.find(r => !r.success)?.error

        for (const r of batchRes.results) {
          const row = toSave[r.index]

          if (!row) continue

          if (r.success) {
            ok++

            indicesGuardadosEstaRonda.add(row._rowIndex)

            setSavedRows(prev => new Set([...prev, row._rowIndex]))

            setDuplicadosPendientesRevisar(prev => {
              const next = new Set(prev)
              next.delete(row._rowIndex)
              return next
            })
          } else {
            fail++

            if (r.status_code === 409) {
              duplicados++

              setDuplicadosPendientesRevisar(
                prev => new Set([...prev, row._rowIndex])
              )
            }
          }
        }

        if (typeof batchRes.ok_count === 'number') ok = batchRes.ok_count
        if (typeof batchRes.fail_count === 'number') fail = batchRes.fail_count
      } catch {
        for (const row of toSave) {
          const result = await saveIndividualPago(row, {
            skipToast: true,
            skipRefresh: true,
          })

          if (result.ok) {
            ok++
            indicesGuardadosEstaRonda.add(row._rowIndex)
          } else {
            fail++
            if (result.was409) duplicados++
          }
        }
      }
    } else {
      for (const row of toSave) {
        const result = await saveIndividualPago(row, {
          skipToast: true,
          skipRefresh: true,
        })

        if (result.ok) {
          ok++
          indicesGuardadosEstaRonda.add(row._rowIndex)
        } else {
          fail++
          if (result.was409) duplicados++
        }
      }
    }

    // Mostrar RESUMEN FINAL en lugar de notificaciones individuales

    if (ok > 0 && fail === 0) {
      addToast('success', `${ok} pago(s) guardado(s) correctamente.`)
    } else if (ok > 0 && fail > 0) {
      addToast('warning', `${ok} guardado(s), ${fail} con errores.`)

      if (duplicados > 0) {
        addToast(
          'warning',
          `${duplicados} duplicado(s). Use "Enviar duplicados" para registrarlos.`
        )
      }
    } else if (fail > 0) {
      const hint = batchFirstError
        ? batchFirstError.length > 220
          ? `${batchFirstError.slice(0, 217)}...`
          : batchFirstError
        : null

      addToast(
        'error',
        hint
          ? `Ningún pago guardado (${fail} rechazado(s)). ${hint}`
          : `Ningún pago guardado (${fail} rechazado(s)). Revise duplicados, cédula o crédito.`
      )
    }

    if (omitidos > 0) {
      addToast(
        'warning',
        `${omitidos} fila(s) omitidas: revise los criterios de guardado.`
      )
    }

    if (ok > 0 || fail > 0) refreshPagos()

    setIsSavingIndividual(false)

    const quedanConErrores = excelData.some(
      r =>
        r._hasErrors &&
        !indicesGuardadosEstaRonda.has(r._rowIndex) &&
        !savedRows.has(r._rowIndex) &&
        !enviadosRevisar.has(r._rowIndex)
    )

    const quedanSinGuardar = excelData.some(
      r =>
        !indicesGuardadosEstaRonda.has(r._rowIndex) &&
        !savedRows.has(r._rowIndex) &&
        !enviadosRevisar.has(r._rowIndex)
    )

    if (fail === 0 && ok > 0 && !quedanConErrores && !quedanSinGuardar) {
      onSuccess?.()

      onClose()
    } else if (fail === 0 && ok > 0 && (quedanConErrores || quedanSinGuardar)) {
      addToast(
        'warning',
        'Quedan filas pendientes. Use "Revisar Pagos" o envie a revisar.'
      )
    }
  }, [
    getValidRows,
    serviceStatus,
    saveIndividualPago,
    addToast,
    onSuccess,
    onClose,
    prestamosPorCedula,
    excelData,
    savedRows,
    enviadosRevisar,
    duplicadosPendientesRevisar,
  ])

  /**
   * Aplica validacion de cedulas + documentos duplicados en BD (misma logica que al cargar Excel).
   * Actualiza refs cedulasExistentesBDRef / documentosDuplicadosBDRef.
   */
  const applyBatchValidationToRows = useCallback(
    async (processed: PagoExcelRow[]): Promise<PagoExcelRow[]> => {
      const docFreq = new Map<string, number>()

      processed.forEach(r => {
        const clave = claveDocumentoExcelCompuesta(
          r.numero_documento,
          r.codigo_documento ?? null
        )

        if (clave) docFreq.set(clave, (docFreq.get(clave) || 0) + 1)
      })

      const documentosDuplicadosEnArchivo = new Set(
        Array.from(docFreq.entries())
          .filter(([, count]) => count > 1)
          .map(([doc]) => doc)
      )

      const todasCedulas = [
        ...new Set(
          processed
            .map(r => r.cedula.replace(/-/g, '').toUpperCase())
            .filter(c => /^[VEJZ]\d{6,11}$/i.test(c))
        ),
      ]

      const todosDocumentos = [
        ...new Set(
          processed
            .map(r =>
              claveDocumentoExcelCompuesta(
                r.numero_documento,
                r.codigo_documento ?? null
              )
            )
            .filter(d => !!d)
        ),
      ]

      let cedulasExistentesBD = new Set<string>()

      let documentosDuplicadosBD = new Set<string>()

      let detalleDuplicadosBD = new Map<string, string>()

      let prestamoPorDocDupBD = new Map<string, number | null>()

      let pagoPorDocDupBD = new Map<string, number>()

      if (todasCedulas.length > 0 || todosDocumentos.length > 0) {
        try {
          const resultado = await pagoService.validarFilasBatch({
            cedulas: todasCedulas,

            documentos: todosDocumentos,
          })

          if (!isMounted()) return processed

          cedulasExistentesBD = new Set(
            (resultado.cedulas_existentes || []).map((c: string) =>
              c.replace(/-/g, '').toUpperCase()
            )
          )

          documentosDuplicadosBD = new Set(
            (resultado.documentos_duplicados || []).map(
              (d: { numero_documento?: string }) =>
                normalizarNumeroDocumento(d.numero_documento)
            )
          )

          const dupList = resultado.documentos_duplicados || []

          // 1) Siempre tomar pago_id de filas origen "pagos" (no depender del orden mezclado con pagos_con_errores).
          for (const raw of dupList) {
            const d = raw as {
              numero_documento?: string
              origen?: string
              pago_id?: number
            }
            if (d.origen !== 'pagos' || d.pago_id == null) continue
            const key = normalizarNumeroDocumento(d.numero_documento)
            if (!key) continue
            const pid = Number(d.pago_id)
            if (!Number.isFinite(pid) || pid <= 0) continue
            if (!pagoPorDocDupBD.has(key)) pagoPorDocDupBD.set(key, pid)
          }

          for (const raw of dupList) {
            const d = raw as {
              numero_documento?: string
              origen?: string
              pago_id?: number
              pago_con_error_id?: number
              prestamo_id?: number | null
            }

            const key = normalizarNumeroDocumento(d.numero_documento)

            if (!key || detalleDuplicadosBD.has(key)) continue

            let suffix = ''

            if (d.origen === 'pagos' && d.pago_id != null) {
              suffix = ` (pago id ${d.pago_id})`
            } else if (
              d.origen === 'pagos_con_errores' &&
              d.pago_con_error_id != null
            ) {
              suffix = ` (cola errores id ${d.pago_con_error_id})`
            }

            detalleDuplicadosBD.set(key, suffix)

            const pid = d.prestamo_id
            prestamoPorDocDupBD.set(
              key,
              pid != null && Number.isFinite(Number(pid)) ? Number(pid) : null
            )
          }
        } catch {
          // Igual que carga inicial: sin respuesta del API, validar sin listas de BD
          cedulasExistentesBD = new Set()
          documentosDuplicadosBD = new Set()
          detalleDuplicadosBD = new Map()
          prestamoPorDocDupBD = new Map()
          pagoPorDocDupBD = new Map()
          detalleDuplicadosBDRef.current = new Map()
          prestamoPorDocDupBDRef.current = new Map()
          pagoPorDocDupBDRef.current = new Map()
        }
      }

      cedulasExistentesBDRef.current = cedulasExistentesBD

      documentosDuplicadosBDRef.current = documentosDuplicadosBD

      detalleDuplicadosBDRef.current = detalleDuplicadosBD

      prestamoPorDocDupBDRef.current = prestamoPorDocDupBD

      pagoPorDocDupBDRef.current = pagoPorDocDupBD

      const maps: MapsValidacionBatchPagos = {
        cedulasExistentesBD,
        documentosDuplicadosBD,
        detalleDuplicadosBD,
        prestamoPorDocDupBD,
        pagoPorDocDupBD,
      }

      return applyRowValidationsSync(
        processed,
        maps,
        documentosRepetidosArchivoJustificadosRef.current
      )
    },
    [isMounted]
  )

  const scheduleRevalidarBatchBd = useCallback(() => {
    if (debounceRevalidarBatchBdRef.current) {
      clearTimeout(debounceRevalidarBatchBdRef.current)
    }

    debounceRevalidarBatchBdRef.current = setTimeout(async () => {
      debounceRevalidarBatchBdRef.current = null

      const filas = excelDataRef.current

      if (!filas.length) return

      try {
        const validated = await applyBatchValidationToRows(filas)

        if (!isMounted()) return

        setExcelData(validated)
      } catch (e) {
        console.error('revalidar batch BD:', e)
      }
    }, 450)
  }, [applyBatchValidationToRows, isMounted])

  const refrescarValidacionFilasBd = useCallback(async () => {
    const filas = excelDataRef.current

    if (!filas.length) return

    try {
      const validated = await applyBatchValidationToRows(filas)

      if (isMounted()) setExcelData(validated)
    } catch (e) {
      console.error('refrescarValidacionFilasBd:', e)
    }
  }, [applyBatchValidationToRows, isMounted])

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
          alert('Archivo demasiado grande. Maximo permitido excedido.')

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

        const processed: PagoExcelRow[] = []

        const headerRow = (jsonData[0] as unknown[]) ?? ([] as unknown[])

        const cols = (() => {
          const h = (i: number) =>
            String(headerRow[i] ?? '')
              .toLowerCase()
              .trim()

          const match = (i: number, ...keys: string[]) =>
            keys.some(k => h(i).includes(k))

          let cedula = 0,
            fecha = 1,
            monto = 2,
            documento = 3,
            prestamo = 4,
            conciliacion = 5

          let monedaCol = -1

          let tasaCol = -1

          let bancoCol = -1

          let linkCol = -1

          let codigoCol = -1

          let cedulaHeaderMatched = false

          for (let i = 0; i < Math.max(headerRow.length, 10); i++) {
            if (
              !cedulaHeaderMatched &&
              match(
                i,
                'cedula',
                'cédula',
                'cedula dep',
                'cédula dep',
                'dni',
                'identificacion',
                'identificación',
                'rif'
              )
            ) {
              cedula = i
              cedulaHeaderMatched = true
            } else if (!cedulaHeaderMatched && h(i) === 'id') {
              cedula = i
              cedulaHeaderMatched = true
            }

            if (match(i, 'fecha', 'fecha_pago', 'date')) fecha = i

            if (match(i, 'monto', 'monto_pagado', 'amount')) monto = i

            if (
              match(
                i,
                'documento',
                'numero_documento',
                'numero documento',
                'n documento',
                'doc',
                'referencia',
                'numero doc',
                'zelle'
              )
            )
              documento = i

            if (
              match(
                i,
                'prestamo',
                'credito',
                'prestamo_id',
                'credito id',
                'crédito'
              )
            )
              prestamo = i

            if (match(i, 'conciliacion', 'conciliación')) conciliacion = i

            if (match(i, 'moneda', 'currency')) monedaCol = i

            if (match(i, 'tasa', 'tasa_cambio', 'tc', 'bcv')) tasaCol = i

            if (
              match(
                i,
                'banco',
                'institucion',
                'institución',
                'institucion bancaria',
                'institución bancaria',
                'entidad'
              )
            )
              bancoCol = i

            const hi = h(i)
            if (
              hi === 'link' ||
              hi.includes('link comprobante') ||
              hi.includes('url comprobante') ||
              hi === 'ver imagen'
            )
              linkCol = i

            if (
              codigoCol < 0 &&
              (match(
                i,
                'codigo documento',
                'código documento',
                'codigo_doc',
                'cod doc',
                'cod. documento'
              ) ||
                h(i) === 'codigo' ||
                h(i) === 'código')
            ) {
              const hx = h(i)
              if (!hx.includes('postal') && !hx.includes('zip')) codigoCol = i
            }
          }

          return {
            cedula,
            fecha,
            monto,
            documento,
            prestamo,
            conciliacion,
            monedaCol,
            tasaCol,
            bancoCol,
            linkCol,
            codigoCol,
          }
        })()

        for (let i = 1; i < jsonData.length; i++) {
          if (!isMounted()) return

          const row = jsonData[i] as unknown[]

          if (!row || row.every(c => c == null || c === '')) continue

          let cedula =
            (row[cols.cedula] != null
              ? String(row[cols.cedula]).trim()
              : ''
            ).trim() || ''

          const fechaPago = convertirFechaExcelPago(row[cols.fecha])

          const montoRaw = String(row[cols.monto] || 0).replace(',', '.')

          const monto = parseFloat(montoRaw) || 0

          let numeroDoc = normalizarNumeroDocumento(row[cols.documento])

          if (
            looksLikeDocumentNotCedula(cedula) &&
            (!numeroDoc ||
              numeroDoc === 'NaN' ||
              /^[VEJZ]\d{6,11}$/i.test(String(numeroDoc).replace(/-/g, '')))
          ) {
            numeroDoc = normalizarNumeroDocumento(cedula)

            cedula = (
              row[cols.documento] != null
                ? String(row[cols.documento]).trim()
                : ''
            ).trim()

            if (!cedula || looksLikeDocumentNotCedula(cedula)) cedula = ''
          }

          const prestamoIdRaw = row[cols.prestamo]

          const conciliacionRawCol4 = (row[cols.prestamo]?.toString() || '')
            .trim()
            .toUpperCase()

          const conciliacionRawCol5 = (row[cols.conciliacion]?.toString() || '')
            .trim()
            .toUpperCase()

          const isConciliacionCol4 = ['SI', 'S\u00cd', 'NO', '1', '0'].includes(
            conciliacionRawCol4
          )

          // Solo usar columna Crédito/ID Préstamo; NUNCA numero_documento (evita confundir 96179604 con prestamo_id)

          let prestamoId: number | null = null

          if (
            !isConciliacionCol4 &&
            prestamoIdRaw != null &&
            String(prestamoIdRaw).trim() !== ''
          ) {
            const fromCred = parsePrestamoIdFromNumeroCredito(prestamoIdRaw)
            if (fromCred != null) {
              prestamoId = fromCred
            } else {
              const n = parseInt(String(prestamoIdRaw).trim(), 10)
              prestamoId = Number.isNaN(n) ? null : n
            }
          }
          if (
            prestamoId != null &&
            (Number.isNaN(prestamoId) ||
              prestamoId < 1 ||
              prestamoId > PRESTAMO_ID_MAX)
          ) {
            prestamoId = null
          }

          const conciliacionRaw = (
            isConciliacionCol4 ? conciliacionRawCol4 : conciliacionRawCol5
          ).trim()

          const conciliado = conciliacionRaw === 'NO' ? false : true

          let moneda_registro: 'USD' | 'BS' = 'USD'

          if (cols.monedaCol >= 0) {
            const raw = String(row[cols.monedaCol] ?? '')
              .trim()
              .toUpperCase()

            if (raw === 'BS' || raw.includes('BOLIV')) moneda_registro = 'BS'
          }

          let tasa_cambio_manual: number | undefined

          if (cols.tasaCol >= 0) {
            const tr = parseFloat(
              String(row[cols.tasaCol] ?? '').replace(',', '.')
            )

            if (Number.isFinite(tr) && tr > 0) tasa_cambio_manual = tr
          }

          const institucion_bancaria =
            cols.bancoCol >= 0 && row[cols.bancoCol] != null
              ? institucionBancariaDesdeExcel(String(row[cols.bancoCol]))
              : null

          const linkRaw =
            cols.linkCol >= 0 && row[cols.linkCol] != null
              ? String(row[cols.linkCol]).trim()
              : ''

          const link_comprobante = linkComprobanteDesdeCeldaExcel(linkRaw)

          const codigoDocRaw =
            cols.codigoCol >= 0 && row[cols.codigoCol] != null
              ? String(row[cols.codigoCol]).trim()
              : ''

          const codigo_documento = codigoDocRaw ? codigoDocRaw : null

          const numeroDocStr =
            numeroDoc && numeroDoc !== 'NaN'
              ? (
                  normalizarNumeroDocumento(numeroDoc) || String(numeroDoc)
                ).trim()
              : ''

          const rowData: PagoExcelRow = {
            _rowIndex: i + 1,

            _validation: {},

            _hasErrors: false,

            cedula,

            fecha_pago: fechaPago,

            monto_pagado: monto,

            numero_documento: numeroDocStr || (numeroDoc ?? ''),

            codigo_documento,

            prestamo_id: Number.isNaN(prestamoId) ? null : prestamoId,

            conciliado,

            moneda_registro,

            tasa_cambio_manual,

            institucion_bancaria,

            link_comprobante,
          }

          // Validaciones locales inmediatas (fecha, monto; documentos duplicados se validan despues)

          const vCedula = validatePagoField('cedula', rowData.cedula)

          const vFecha = validatePagoField('fecha_pago', rowData.fecha_pago)

          const vMonto = validatePagoField('monto_pagado', rowData.monto_pagado)

          rowData._validation = {
            cedula: vCedula,

            fecha_pago: vFecha,

            monto_pagado: vMonto,

            numero_documento: { isValid: true }, // Se valida despues en el servidor

            prestamo_id: { isValid: true },

            conciliado: { isValid: true },

            institucion_bancaria: { isValid: true },

            link_comprobante: { isValid: true },
          }

          rowData._hasErrors =
            !vCedula.isValid || !vFecha.isValid || !vMonto.isValid

          processed.push(rowData)
        }

        if (!isMounted()) return

        const validatedData = await applyBatchValidationToRows(processed)

        if (!isMounted()) return

        setExcelData(validatedData)

        setShowPreview(true)

        // Asignar credito / prestamo al cliente

        const uniqueCedulasSet = new Set<string>()

        processed.forEach(r => {
          const fromCedula = cedulaParaLookup(r.cedula)

          const fromDoc = cedulaParaLookup(r.numero_documento)

          const lookup = cedulaLookupParaFila(
            r.cedula || '',
            r.numero_documento || ''
          )

          ;[fromCedula, fromDoc, lookup].forEach(c => {
            if (c && c.length >= 5 && looksLikeCedula(c))
              uniqueCedulasSet.add(c)
          })
        })

        // Normalizar igual que el backend (sin guiones ni espacios extra)

        const uniqueCedulas = [...uniqueCedulasSet]
          .map(c => (c || '').trim().replace(/-/g, ''))
          .filter(c => c.length >= 5 && looksLikeCedula(c))

        if (uniqueCedulas.length > 0) {
          batchRequestedForCedulasRef.current = uniqueCedulas.join(',')

          setCedulasBuscando(prev => new Set([...prev, ...uniqueCedulas]))

          const prestamoIdVacio = (v: unknown) =>
            v == null ||
            v === undefined ||
            v === '' ||
            v === 'none' ||
            v === 0 ||
            (typeof v === 'number' && Number.isNaN(v))

          const buildMap = (
            batchOrResults: Record<string, any[]> | any[][]
          ): Record<string, Array<{ id: number; estado: string }>> => {
            const map: Record<
              string,
              Array<{ id: number; estado: string }>
            > = {}

            const isResultsArray =
              Array.isArray(batchOrResults) &&
              batchOrResults.length > 0 &&
              Array.isArray((batchOrResults as any[])[0])

            if (isResultsArray) {
              const results = batchOrResults as any[][]

              uniqueCedulas.forEach((cedula, i) => {
                const prestamos = (results[i] || []).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes(
                    (p.estado || '').toUpperCase()
                  )
                )

                const arr = prestamos.map((p: any) => ({
                  id: p.id,
                  estado: p.estado || '',
                }))

                map[cedula] = arr

                const cedulaSinGuion = cedula.replace(/-/g, '')

                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr

                map[cedula.toUpperCase()] = arr

                map[cedula.toLowerCase()] = arr

                // Si la cédula es V+dígitos, también guardar sin V
                if (/^V\d{6,11}$/i.test(cedula)) {
                  const sinV = cedula.slice(1)
                  map[sinV] = arr
                  map[sinV.toUpperCase()] = arr
                  map[sinV.toLowerCase()] = arr
                }
              })
            } else {
              const batch = batchOrResults as Record<string, any[]>

              uniqueCedulas.forEach(cedula => {
                const prestamos = (
                  batch[cedula] ||
                  batch[cedula.replace(/-/g, '')] ||
                  []
                ).filter((p: any) =>
                  ESTADOS_PRESTAMO_ACTIVO.includes(
                    (p.estado || '').toUpperCase()
                  )
                )

                const arr = prestamos.map((p: any) => ({
                  id: p.id,
                  estado: p.estado || '',
                }))

                map[cedula] = arr

                const cedulaSinGuion = cedula.replace(/-/g, '')

                if (cedulaSinGuion !== cedula) map[cedulaSinGuion] = arr

                map[cedula.toUpperCase()] = arr

                map[cedula.toLowerCase()] = arr

                // Si la cédula es V+dígitos, también guardar sin V
                if (/^V\d{6,11}$/i.test(cedula)) {
                  const sinV = cedula.slice(1)
                  map[sinV] = arr
                  map[sinV.toUpperCase()] = arr
                  map[sinV.toLowerCase()] = arr
                }
              })
            }

            return map
          }

          const fetchPromise = prestamoService

            .getPrestamosByCedulasBatch(uniqueCedulas)

            .then(batch => buildMap(batch || {}))

          fetchPromise

            .then(map => {
              if (!isMounted()) return

              setPrestamosPorCedula(prev => ({ ...prev, ...map }))

              setExcelData(validatedData)
            })

            .catch(err => {
              console.error('[ExcelUpload] Error batch processExcelFile:', err)
              if (isMounted()) setExcelData(validatedData)
            })

            .finally(() => {
              if (isMounted()) {
                setCedulasBuscando(prev => {
                  const next = new Set(prev)

                  uniqueCedulas.forEach(c => next.delete(c))

                  return next
                })
              }
            })
        }
      } catch (err) {
        console.error('Error procesando Excel:', err)

        alert(
          `Error: ${err instanceof Error ? err.message : 'Error desconocido'}`
        )
      } finally {
        setIsProcessing(false)
      }
    },

    [isMounted, applyBatchValidationToRows]
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
        f => f.name.endsWith('.xlsx') || f.name.endsWith('.xls')
      )

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

  const updateCellValue = useCallback(
    (row: PagoExcelRow, field: string, value: string | number) => {
      setExcelData(prev =>
        prev.map(r => {
          if (r._rowIndex !== row._rowIndex) return r

          const updated = { ...r }

          if (field === 'prestamo_id') {
            const parsed =
              value === '' || value === 'none'
                ? null
                : (parsePrestamoIdFromNumeroCredito(value) ??
                  (Number.isNaN(Number(value)) ? null : Number(value)))

            updated.prestamo_id = parsed
          } else if (field === 'conciliado') {
            updated.conciliado =
              value === 'si' || value === 'SI' || String(value) === '1'
          } else if (field === 'moneda_registro') {
            const m = String(value).toUpperCase() === 'BS' ? 'BS' : 'USD'
            ;(updated as any).moneda_registro = m
            if (m === 'USD') {
              delete (updated as any).tasa_cambio_manual
            }
          } else if (field === 'tasa_cambio_manual') {
            if (value === '' || value === null || value === undefined) {
              delete (updated as any).tasa_cambio_manual
            } else {
              const n = parseFloat(String(value).replace(',', '.'))
              ;(updated as any).tasa_cambio_manual =
                Number.isFinite(n) && n > 0 ? n : undefined
            }
          } else if (field === 'codigo_documento') {
            const c = String(value ?? '').trim()
            ;(updated as any).codigo_documento = c ? c : null
          } else {
            ;(updated as any)[field] =
              field === 'monto_pagado' ? Number(value) || 0 : value
          }

          // REGLA ESTRICTA: ningun prestamo_id sin confirmacion de columna

          const afectaClaveDocumento =
            field === 'numero_documento' || field === 'codigo_documento'

          if (afectaClaveDocumento) {
            const documentosEnArchivo = new Set<string>()
            prev.forEach(other => {
              if (other._rowIndex === row._rowIndex) return
              const cl = claveDocumentoExcelCompuesta(
                other.numero_documento,
                other.codigo_documento ?? null
              )
              if (cl) documentosEnArchivo.add(cl)
            })

            const docFreq = new Map<string, number>()
            prev.forEach(o => {
              const rowData = o._rowIndex === row._rowIndex ? updated : o
              const cl = claveDocumentoExcelCompuesta(
                rowData.numero_documento,
                rowData.codigo_documento ?? null
              )
              if (cl) docFreq.set(cl, (docFreq.get(cl) || 0) + 1)
            })
            const documentosDuplicadosEnArchivo = new Set(
              Array.from(docFreq.entries())
                .filter(([, c]) => c > 1)
                .map(([d]) => d)
            )

            const claveCur = claveDocumentoExcelCompuesta(
              updated.numero_documento,
              updated.codigo_documento ?? null
            )
            const docNorm = normalizarNumeroDocumento(updated.numero_documento)

            const dupArchivo =
              !!claveCur && documentosDuplicadosEnArchivo.has(claveCur)
            const dupBD =
              !!claveCur && documentosDuplicadosBDRef.current.has(claveCur)

            let vDoc: { isValid: boolean; message?: string }
            if (
              dupArchivo &&
              claveCur &&
              documentosRepetidosArchivoJustificadosRef.current.has(claveCur)
            ) {
              vDoc = {
                isValid: true,
                message: 'Documento repetido en este archivo',
              }
            } else if (dupArchivo) {
              vDoc = {
                isValid: false,
                message: 'Documento repetido en este archivo',
              }
            } else if (dupBD) {
              vDoc = {
                isValid: false,
                message: `Documento ya existe en la base de datos${detalleDuplicadosBDRef.current.get(claveCur) || detalleDuplicadosBDRef.current.get(docNorm) || ''}`,
              }
            } else {
              vDoc = validatePagoField(
                'numero_documento',
                updated.numero_documento,
                {
                  documentosEnArchivo: documentosDuplicadosEnArchivo,
                  codigoDocumento: updated.codigo_documento ?? null,
                }
              )
            }

            updated._validation = {
              ...r._validation,
              numero_documento: vDoc,
            }

            updated._hasErrors =
              !updated._validation.cedula?.isValid ||
              !updated._validation.fecha_pago?.isValid ||
              !updated._validation.monto_pagado?.isValid ||
              !vDoc.isValid

            if (dupBD && claveCur) {
              const pr =
                prestamoPorDocDupBDRef.current.get(claveCur) ??
                prestamoPorDocDupBDRef.current.get(docNorm)
              const pg =
                pagoPorDocDupBDRef.current.get(claveCur) ??
                pagoPorDocDupBDRef.current.get(docNorm)
              if (pr !== undefined)
                (updated as any)._prestamoIdExistenteDuplicadoBD = pr
              if (pg !== undefined)
                (updated as any)._pagoIdExistenteDuplicadoBD = pg
            } else {
              delete (updated as any)._prestamoIdExistenteDuplicadoBD
              delete (updated as any)._pagoIdExistenteDuplicadoBD
            }
          } else if (field === 'cedula') {
            updated.prestamo_id = null

            const allCedulas = new Set<string>()

            prev.forEach(other => {
              const ced =
                other._rowIndex === row._rowIndex
                  ? String(value ?? '')
                      .trim()
                      .replace(/-/g, '')
                      .toUpperCase()
                  : (other.cedula || '').trim().replace(/-/g, '').toUpperCase()

              if (ced && /^[VEJZ]\d{6,11}$/.test(ced)) allCedulas.add(ced)
            })

            const cedulasInvalidas = new Set(
              [...allCedulas].filter(
                c => !cedulasExistentesBDRef.current.has(c)
              )
            )

            const vCedula = validatePagoField(
              'cedula',
              (updated as any).cedula,
              { cedulasInvalidas }
            )

            updated._validation = { ...r._validation, cedula: vCedula }

            updated._hasErrors =
              !vCedula.isValid ||
              !r._validation.fecha_pago?.isValid ||
              !r._validation.monto_pagado?.isValid ||
              !r._validation.numero_documento?.isValid
          } else if (field === 'fecha_pago') {
            const vFecha = validatePagoField(
              'fecha_pago',
              (updated as any).fecha_pago
            )

            updated._validation = { ...r._validation, fecha_pago: vFecha }

            updated._hasErrors =
              !r._validation.cedula?.isValid ||
              !vFecha.isValid ||
              !r._validation.monto_pagado?.isValid ||
              !r._validation.numero_documento?.isValid
          } else if (field === 'monto_pagado') {
            const vMonto = validatePagoField(
              'monto_pagado',
              (updated as any).monto_pagado
            )

            updated._validation = { ...r._validation, monto_pagado: vMonto }

            updated._hasErrors =
              !r._validation.cedula?.isValid ||
              !r._validation.fecha_pago?.isValid ||
              !vMonto.isValid ||
              !r._validation.numero_documento?.isValid
          } else {
            updated._validation = {
              ...r._validation,
              [field]: { isValid: true },
            }

            updated._hasErrors =
              !updated._validation.cedula?.isValid ||
              !updated._validation.fecha_pago?.isValid ||
              !updated._validation.monto_pagado?.isValid ||
              !updated._validation.numero_documento?.isValid
          }

          return updated
        })
      )

      if (
        field === 'numero_documento' ||
        field === 'codigo_documento' ||
        field === 'cedula'
      ) {
        scheduleRevalidarBatchBd()
      }
    },
    [scheduleRevalidarBatchBd]
  )

  const moveErrorToReviewPagos = useCallback(
    async (id: number) => {
      try {
        await pagoConErrorService.moveToReviewPagos(id)

        setPagosConErrores(prev => prev.filter(p => p.id !== id))

        addToast('success', 'Movido a Revisar Pagos')

        queryClient.invalidateQueries({ queryKey: ['pagosConErrores'] })
      } catch (error) {
        addToast('error', 'Error al mover a revisar pagos')
      }
    },

    [addToast, queryClient]
  )

  const dismissError = useCallback(
    (id: number) => {
      setPagosConErrores(prev => prev.filter(p => p.id !== id))
    },

    []
  )

  const sendAllErrorsToRevisarPagos = useCallback(async () => {
    const erroresRows = excelData.filter(r => r._hasErrors)

    if (erroresRows.length === 0) {
      addToast('warning', 'No hay filas con errores para enviar')
      return
    }

    if (serviceStatus === 'offline') {
      addToast('error', 'Sin conexion')
      return
    }

    setIsSavingIndividual(true)

    setBatchProgress({ sent: 0, total: erroresRows.length })

    let ok = 0
    let fail = 0

    for (let i = 0; i < erroresRows.length; i++) {
      const row = erroresRows[i]

      const success = await sendToRevisarPagos(row, () => {}, true, true, true)

      if (success) {
        ok++

        setEnviadosRevisar(prev => new Set([...prev, row._rowIndex]))

        setDuplicadosPendientesRevisar(prev => {
          const next = new Set(prev)
          next.delete(row._rowIndex)
          return next
        })

        setExcelData(prev => prev.filter(r => r._rowIndex !== row._rowIndex))
      } else fail++

      setBatchProgress({ sent: i + 1, total: erroresRows.length })
    }

    setBatchProgress(null)

    if (ok > 0 && fail === 0)
      addToast('success', `${ok} enviado(s) a Revisar Pagos.`)
    else if (ok > 0 && fail > 0)
      addToast('warning', `${ok} enviado(s), ${fail} con errores.`)
    else if (fail > 0) addToast('error', `Error al enviar.`)

    if (ok > 0) refreshPagos()

    setIsSavingIndividual(false)
  }, [excelData, serviceStatus, sendToRevisarPagos, addToast, refreshPagos])

  /** Borra todo el estado y deja la pantalla lista para cargar otro archivo. */

  const clearAndShowFileSelect = useCallback(() => {
    setExcelData([])

    setSavedRows(new Set())

    setEnviadosRevisar(new Set())

    setDuplicadosPendientesRevisar(new Set())

    setDocumentosRepetidosArchivoJustificados([])

    setUploadedFile(null)

    setShowPreview(false)
  }, [])

  const justificarDocumentoRepetidoEnArchivo = useCallback(
    (claveDocRaw: string) => {
      const claveCompuesta = (claveDocRaw || '').trim()
      if (!claveCompuesta) return

      const maps: MapsValidacionBatchPagos = {
        cedulasExistentesBD: cedulasExistentesBDRef.current,
        documentosDuplicadosBD: documentosDuplicadosBDRef.current,
        detalleDuplicadosBD: detalleDuplicadosBDRef.current,
        prestamoPorDocDupBD: prestamoPorDocDupBDRef.current,
        pagoPorDocDupBD: pagoPorDocDupBDRef.current,
      }

      const dupPrestamoBd =
        prestamoPorDocDupBDRef.current.get(claveCompuesta) ?? null

      setExcelData(prev => {
        const usados = new Set<string>()
        const mapped = prev.map(r => {
          const clave = claveDocumentoExcelCompuesta(
            r.numero_documento,
            r.codigo_documento ?? null
          )
          if (clave !== claveCompuesta) return r

          const raw = String(r.numero_documento ?? '').trim()
          if (SUFIJO_VISTO_ARCHIVO_RE.test(raw)) return r

          const rowPid = r.prestamo_id ?? null
          const letter: 'A' | 'P' =
            dupPrestamoBd != null &&
            rowPid != null &&
            Number(dupPrestamoBd) !== Number(rowPid)
              ? 'P'
              : 'A'

          const token = allocarTokenSufijoVistoArchivo(letter, usados)
          const maxBase = NUMERO_DOCUMENTO_MAX_LEN - 1 - token.length
          let base = raw
          if (base.length > maxBase) {
            base = base.slice(0, Math.max(0, maxBase))
          }

          return { ...r, numero_documento: `${base}_${token}` }
        })

        return applyRowValidationsSync(
          mapped,
          maps,
          new Set(documentosRepetidosArchivoJustificadosRef.current)
        )
      })

      scheduleRevalidarBatchBd()
    },
    [scheduleRevalidarBatchBd]
  )

  /** Admin: permite duplicado en archivo sin tocar el texto del documento (decisión humana distinta a añadir sufijos). */
  const marcarJustificadoDocumentoRepetidoEnArchivo = useCallback(
    (claveDocRaw: string) => {
      const key = (claveDocRaw || '').trim()
      if (!key) return
      setDocumentosRepetidosArchivoJustificados(prev =>
        prev.includes(key) ? prev : [...prev, key]
      )
    },
    []
  )

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

    clearAndShowFileSelect,

    getValidRows,

    saveIndividualPago,

    saveRowIfValid,

    saveAllValid,

    sendToRevisarPagos,

    sendAllToRevisarPagos,

    sendAllErrorsToRevisarPagos,

    sendDuplicadosToRevisarPagos,

    getRowsToRevisarPagos,

    getDuplicadosRows,

    isSendingAllRevisar,

    enviadosRevisar,

    duplicadosPendientesRevisar,

    onClose,

    removeToast,

    addToast,

    pagosConErrores,

    registrosConError,

    moveErrorToReviewPagos,

    dismissError,

    batchProgress,

    refrescarValidacionFilasBd,

    documentosRepetidosArchivoJustificados,

    justificarDocumentoRepetidoEnArchivo,

    marcarJustificadoDocumentoRepetidoEnArchivo,
  }
}
