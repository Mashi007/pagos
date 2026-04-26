/**









 * Listado de pagos reportados (módulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.
 * Cola manual: filas que no cumplen validadores; «Incluir ya exportados» vuelve a mostrar las marcadas en corrección.
 * Por defecto filtra por fecha de creación del reporte (últimos 90 días) para aligerar el barrido en API; «Sin límite de fechas» recupera el historial completo.









 */

import React, {
  useState,
  useEffect,
  useLayoutEffect,
  useRef,
  useCallback,
  useMemo,
} from 'react'
import { createPortal } from 'react-dom'

import { useNavigate } from 'react-router-dom'

import { useQueryClient } from '@tanstack/react-query'

import { invalidateListasNotificacionesMora } from '../constants/queryKeys'

import {
  listPagosReportadosConKpis,
  cambiarEstadoPago,
  eliminarPagoReportado,
  invalidateCobrosListadoKpisCache,
  COBROS_LISTADO_KPIS_CACHE_TTL_MS,
  type PagoReportadoItem,
  type ListPagosReportadosResponse,
  type PagosReportadosKpis,
  type CambiarEstadoPagoResponse,
} from '../services/cobrosService'
import { apiClient } from '../services/api'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import toast from 'react-hot-toast'

import { getErrorMessage } from '../types/errors'

/** Toast según envío real del correo de rechazo (API devuelve mensaje + flags). */
function toastAfterRechazoCobros(data: CambiarEstadoPagoResponse) {
  const msg = data.mensaje ?? 'Estado actualizado a rechazado.'
  if (data.rechazo_correo_enviado === true) {
    toast.success(msg)
  } else if (data.rechazo_correo_enviado === false) {
    const err = data.rechazo_correo_error
    toast.error(
      err ? `${msg} (${err.length > 160 ? `${err.slice(0, 160)}…` : err})` : msg
    )
  } else {
    toast(msg, { duration: 7000 })
  }
}

/** Alineado con filtros `fecha_desde` / `fecha_hasta` del API (fecha local del navegador). */
const COBROS_REPORTADOS_FILTRO_FECHA_DIAS = 90

function cobrosFechaLocalYMD(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function cobrosFechaDesdeHaceNDias(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return cobrosFechaLocalYMD(d)
}

const COMPROBANTE_FLOAT_MIN_W = 260
const COMPROBANTE_FLOAT_MIN_H = 180
const COMPROBANTE_FLOAT_DEFAULT_W = 460
const COMPROBANTE_FLOAT_DEFAULT_H = 560

function clampComprobanteFloat(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n))
}

type ComprobanteResizeCorner = 'nw' | 'ne' | 'sw' | 'se'
type ComprobantePreviewState = {
  open: boolean
  pagoId: number | null
  blobUrl: string | null
  contentType: string | null
  loading: boolean
  rotDeg: number
}

import {
  Loader2,
  FileText,
  Settings,
  Clock,
  Search,
  CheckCircle,
  XCircle,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Edit,
  Mail,
  Eye,
  RotateCcw,
  X,
} from 'lucide-react'

import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

import { cn } from '../utils'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover'

const MENSAJE_RECHAZO_POR_DEFECTO = `Buenas tardes



















La imagen no se aprecia detalles, agradezco enviar una imagen sin recortar a cobranza@rapicreditca.com



















Gracias`

const ESTADO_CONFIG: Record<
  string,
  {
    label: string
    short: string
    variant: 'default' | 'secondary' | 'destructive' | 'outline'
    Icon: typeof Clock
  }
> = {
  pendiente: {
    label: 'Pendiente',
    short: 'Pend.',
    variant: 'secondary',
    Icon: Clock,
  },

  en_revision: {
    label: 'En revisión (manual)',
    short: 'Revisión',
    variant: 'outline',
    Icon: Search,
  },

  aprobado: {
    label: 'Aprobado',
    short: 'Aprobado',
    variant: 'default',
    Icon: CheckCircle,
  },

  importado: {
    label: 'Importado a Pagos',
    short: 'Import.',
    variant: 'default',
    Icon: CheckCircle,
  },

  rechazado: {
    label: 'Rechazado',
    short: 'Rechazado',
    variant: 'destructive',
    Icon: XCircle,
  },
}

const normalizeEstadoValue = (value: string) =>
  String(value ?? '')
    .normalize('NFD')

    .replace(/[\u0300-\u036f]/g, '')

    .trim()

    .replace(/\s+/g, '_')

    .toLowerCase()

const isMercantilBank = (value: string) =>
  String(value ?? '')
    .trim()
    .toLowerCase()
    .includes('mercantil')

/** Filas que pueden aprobarse desde el listado (misma regla que el selector «Aprobar» por fila). */
function puedeAprobarMasivoRow(row: PagoReportadoItem): boolean {
  return row.estado === 'pendiente' || row.estado === 'en_revision'
}

/** Anchos por defecto (px) para la tabla de pagos reportados; el usuario puede redimensionar. */
const COBROS_REPORTADOS_COL_WIDTHS_KEY =
  'rapicredit:cobrosPagosReportados:colWidthsV1'

const COBROS_REPORTADOS_COL_COUNT = 11

const COBROS_REPORTADOS_DEFAULT_COL_WIDTHS: readonly number[] = [
  44, 96, 168, 88, 110, 150, 110, 100, 260, 108, 132,
]

function readCobrosReportadosColWidths(): number[] {
  if (typeof window === 'undefined') {
    return [...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS]
  }
  try {
    const raw = window.localStorage.getItem(COBROS_REPORTADOS_COL_WIDTHS_KEY)
    if (!raw) return [...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS]
    const parsed = JSON.parse(raw) as unknown
    if (
      !Array.isArray(parsed) ||
      parsed.length !== COBROS_REPORTADOS_COL_COUNT
    ) {
      return [...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS]
    }
    const nums = parsed.map(x => Number(x))
    if (!nums.every(n => Number.isFinite(n) && n >= 48 && n <= 640)) {
      return [...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS]
    }
    return nums
  } catch {
    return [...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS]
  }
}

const COBROS_REPORTADOS_TABLE_HEAD: ReadonlyArray<{
  label: string
  align: 'left' | 'right' | 'center'
}> = [
  { label: 'Sel.', align: 'center' },
  { label: 'Cédula', align: 'left' },
  { label: 'Banco', align: 'left' },
  { label: 'Monto', align: 'right' },
  { label: 'Fecha pago', align: 'left' },
  { label: 'Nº operación', align: 'left' },
  { label: 'Fecha reporte', align: 'left' },
  { label: 'Comprobante', align: 'center' },
  { label: 'Observación', align: 'left' },
  { label: 'Estado', align: 'left' },
  { label: 'Acciones', align: 'right' },
]

export default function CobrosPagosReportadosPage() {
  const navigate = useNavigate()
  const diagnosticoNoEmail = useMemo(() => {
    if (typeof window === 'undefined') return false
    const q = new URLSearchParams(window.location.search)
    return q.get('diag') === '1' || q.get('no_email') === '1'
  }, [])

  const queryClient = useQueryClient()

  const [data, setData] = useState<ListPagosReportadosResponse | null>(null)

  const [loading, setLoading] = useState(true)

  /** Recarga con datos previos en pantalla (evita pantalla en blanco "Cargando..." durante listado-y-kpis lento). */
  const [refreshing, setRefreshing] = useState(false)

  const [page, setPage] = useState(1)

  const [estado, setEstado] = useState<string>('')

  const [fechaDesde, setFechaDesde] = useState(() =>
    cobrosFechaDesdeHaceNDias(COBROS_REPORTADOS_FILTRO_FECHA_DIAS)
  )

  const [fechaHasta, setFechaHasta] = useState(() =>
    cobrosFechaLocalYMD(new Date())
  )

  const [cedula, setCedula] = useState('')

  const [institucion, setInstitucion] = useState('')

  const [incluirExportados, setIncluirExportados] = useState(false)
  const [soloCedulasDuplicadas, setSoloCedulasDuplicadas] = useState(false)
  /** Cliente: filas cuya observación incluye falla de lista autorizada para pagos en Bs. */
  const [soloFallaListaBs, setSoloFallaListaBs] = useState(false)
  /** Cliente: filas marcadas DUPLICADO (misma regla que el listado / validadores). */
  const [soloDuplicadoDocumento, setSoloDuplicadoDocumento] = useState(false)

  const [changingEstadoId, setChangingEstadoId] = useState<number | null>(null)

  /** IDs seleccionados en la página actual para aprobación masiva (solo pendiente / en revisión). */
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const [bulkApproving, setBulkApproving] = useState(false)

  const headerCheckboxRef = useRef<HTMLInputElement>(null)

  const [viewingComprobanteId, setViewingComprobanteId] = useState<
    number | null
  >(null)
  const [previewComprobante, setPreviewComprobante] =
    useState<ComprobantePreviewState>({
      open: false,
      pagoId: null,
      blobUrl: null,
      contentType: null,
      loading: false,
      rotDeg: 0,
    })
  const [previewFloatLeft, setPreviewFloatLeft] = useState(0)
  const [previewFloatTop, setPreviewFloatTop] = useState(0)
  const [previewFloatW, setPreviewFloatW] = useState(
    COMPROBANTE_FLOAT_DEFAULT_W
  )
  const [previewFloatH, setPreviewFloatH] = useState(
    COMPROBANTE_FLOAT_DEFAULT_H
  )
  const previewFloatInitRef = useRef(false)
  const previewFloatLRef = useRef(0)
  const previewFloatTRef = useRef(0)
  const previewFloatWRef = useRef(COMPROBANTE_FLOAT_DEFAULT_W)
  const previewFloatHRef = useRef(COMPROBANTE_FLOAT_DEFAULT_H)
  const previewInteractRef = useRef<
    | {
        kind: 'drag'
        pointerId: number
        startX: number
        startY: number
        originL: number
        originT: number
      }
    | {
        kind: 'resize'
        pointerId: number
        corner: ComprobanteResizeCorner
        startX: number
        startY: number
        originL: number
        originT: number
        originW: number
        originH: number
      }
    | null
  >(null)

  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [rechazarModal, setRechazarModal] = useState<{
    open: boolean
    row: PagoReportadoItem | null
  }>({ open: false, row: null })

  const [motivoRechazo, setMotivoRechazo] = useState('')

  const [kpis, setKpis] = useState<PagosReportadosKpis | null>(null)

  const [ultimaCargaMs, setUltimaCargaMs] = useState<number | null>(null)

  const [searchNonce, setSearchNonce] = useState(0)
  const loadSeqRef = useRef(0)
  const postMutationSyncTimerRef = useRef<number | null>(null)
  const dataRef = useRef<ListPagosReportadosResponse | null>(null)
  dataRef.current = data

  const [colWidths, setColWidths] = useState<number[]>(
    readCobrosReportadosColWidths
  )

  /** En ≥1024px el comprobante se acopla a la izquierda y el listado a la derecha (sin ventana flotante). */
  const [lgViewport, setLgViewport] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(min-width: 1024px)')
    const apply = () => setLgViewport(mq.matches)
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  const dockComprobante = previewComprobante.open && lgViewport

  useEffect(() => {
    try {
      window.localStorage.setItem(
        COBROS_REPORTADOS_COL_WIDTHS_KEY,
        JSON.stringify(colWidths)
      )
    } catch {
      /* ignore quota / private mode */
    }
  }, [colWidths])

  const handleColResizeStart = useCallback(
    (colIndex: number, e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const startX = e.clientX
      const startW = colWidths[colIndex] ?? 96
      const onMove = (ev: MouseEvent) => {
        const next = Math.max(
          48,
          Math.min(640, Math.round(startW + (ev.clientX - startX)))
        )
        setColWidths(prev => {
          if (prev[colIndex] === next) return prev
          const copy = [...prev]
          copy[colIndex] = next
          return copy
        })
      }
      const onUp = () => {
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
      }
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },
    [colWidths]
  )

  const resetColWidths = useCallback(() => {
    try {
      window.localStorage.removeItem(COBROS_REPORTADOS_COL_WIDTHS_KEY)
    } catch {
      /* ignore */
    }
    setColWidths([...COBROS_REPORTADOS_DEFAULT_COL_WIDTHS])
  }, [])

  const fetchListado = useCallback(
    async (opts?: {
      bypassCache?: boolean
      silent?: boolean
      page?: number
    }) => {
      const startedAt = performance.now()
      const requestSeq = ++loadSeqRef.current
      const initialLoad = dataRef.current === null
      const silent = Boolean(opts?.silent) && dataRef.current !== null
      const pageToFetch = opts?.page != null ? opts.page : page
      setLoading(initialLoad)
      // Sin overlay "Actualizando listado…" en refrescos silenciosos (p. ej. tras aprobar o intervalo automático).
      setRefreshing(!initialLoad && !silent)

      try {
        const filterParams = {
          fecha_desde: fechaDesde || undefined,

          fecha_hasta: fechaHasta || undefined,

          cedula: cedula.trim() || undefined,

          institucion: institucion.trim() || undefined,
        }

        const res = await listPagosReportadosConKpis(
          {
            page: pageToFetch,

            per_page: 20,

            estado: estado || undefined,

            incluir_exportados: incluirExportados,

            ...filterParams,
          },
          { bypassCache: opts?.bypassCache }
        )
        if (requestSeq !== loadSeqRef.current) return

        setData(res)

        setKpis(res.kpis)
        setUltimaCargaMs(Math.round(performance.now() - startedAt))
      } catch (e: any) {
        toast.error(e?.message || 'Error al cargar.')
      } finally {
        if (requestSeq === loadSeqRef.current) {
          setLoading(false)
          setRefreshing(false)
        }
      }
    },
    [
      page,
      estado,
      fechaDesde,
      fechaHasta,
      cedula,
      institucion,
      incluirExportados,
    ]
  )

  useEffect(() => {
    void fetchListado()
  }, [fetchListado, searchNonce])

  useEffect(() => {
    setSelectedIds([])
  }, [
    page,
    estado,
    fechaDesde,
    fechaHasta,
    cedula,
    institucion,
    incluirExportados,
    soloCedulasDuplicadas,
    soloFallaListaBs,
    soloDuplicadoDocumento,
  ])

  useEffect(() => {
    const tick = () => {
      if (
        typeof document !== 'undefined' &&
        document.visibilityState !== 'visible'
      ) {
        return
      }
      void fetchListado({ bypassCache: true, silent: true })
    }
    const id = window.setInterval(tick, COBROS_LISTADO_KPIS_CACHE_TTL_MS)
    return () => window.clearInterval(id)
  }, [fetchListado])

  useLayoutEffect(() => {
    previewFloatLRef.current = previewFloatLeft
    previewFloatTRef.current = previewFloatTop
    previewFloatWRef.current = previewFloatW
    previewFloatHRef.current = previewFloatH
  }, [previewFloatLeft, previewFloatTop, previewFloatW, previewFloatH])

  useEffect(() => {
    if (!previewComprobante.open) {
      previewFloatInitRef.current = false
      return
    }
    if (lgViewport) {
      previewFloatInitRef.current = false
      return
    }
    if (previewFloatInitRef.current) return
    const vw = window.innerWidth
    const vh = window.innerHeight
    const w = clampComprobanteFloat(
      COMPROBANTE_FLOAT_DEFAULT_W,
      COMPROBANTE_FLOAT_MIN_W,
      vw - 20
    )
    const h = clampComprobanteFloat(
      COMPROBANTE_FLOAT_DEFAULT_H,
      COMPROBANTE_FLOAT_MIN_H,
      vh - 24
    )
    setPreviewFloatW(w)
    setPreviewFloatH(h)
    setPreviewFloatLeft(clampComprobanteFloat(vw - w - 12, 8, vw - w - 8))
    setPreviewFloatTop(clampComprobanteFloat((vh - h) / 2, 8, vh - h - 8))
    previewFloatInitRef.current = true
  }, [previewComprobante.open, lgViewport])

  useEffect(() => {
    return () => {
      if (previewComprobante.blobUrl)
        URL.revokeObjectURL(previewComprobante.blobUrl)
    }
  }, [previewComprobante.blobUrl])

  const closeComprobantePreview = useCallback(() => {
    setPreviewComprobante(prev => {
      if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
      return {
        open: false,
        pagoId: null,
        blobUrl: null,
        contentType: null,
        loading: false,
        rotDeg: 0,
      }
    })
    previewInteractRef.current = null
  }, [])

  const attachPreviewPointerListeners = useCallback(() => {
    const onMove = (e: PointerEvent) => {
      const s = previewInteractRef.current
      if (!s || e.pointerId !== s.pointerId) return
      const dx = e.clientX - s.startX
      const dy = e.clientY - s.startY
      const vw = window.innerWidth
      const vh = window.innerHeight
      if (s.kind === 'drag') {
        const w = previewFloatWRef.current
        const h = previewFloatHRef.current
        setPreviewFloatLeft(
          clampComprobanteFloat(s.originL + dx, 8 - w + 64, vw - 64)
        )
        setPreviewFloatTop(clampComprobanteFloat(s.originT + dy, 8, vh - h - 8))
        return
      }
      const right = s.originL + s.originW
      const bottom = s.originT + s.originH
      if (s.corner === 'se') {
        setPreviewFloatW(
          clampComprobanteFloat(
            s.originW + dx,
            COMPROBANTE_FLOAT_MIN_W,
            vw - s.originL - 8
          )
        )
        setPreviewFloatH(
          clampComprobanteFloat(
            s.originH + dy,
            COMPROBANTE_FLOAT_MIN_H,
            vh - s.originT - 8
          )
        )
      } else if (s.corner === 'ne') {
        const nextW = clampComprobanteFloat(
          s.originW + dx,
          COMPROBANTE_FLOAT_MIN_W,
          vw - s.originL - 8
        )
        const nextTop = clampComprobanteFloat(
          s.originT + dy,
          8,
          bottom - COMPROBANTE_FLOAT_MIN_H
        )
        setPreviewFloatW(nextW)
        setPreviewFloatTop(nextTop)
        setPreviewFloatH(bottom - nextTop)
      } else if (s.corner === 'sw') {
        const nextLeft = clampComprobanteFloat(
          s.originL + dx,
          8,
          right - COMPROBANTE_FLOAT_MIN_W
        )
        setPreviewFloatLeft(nextLeft)
        setPreviewFloatW(right - nextLeft)
        setPreviewFloatH(
          clampComprobanteFloat(
            s.originH + dy,
            COMPROBANTE_FLOAT_MIN_H,
            vh - s.originT - 8
          )
        )
      } else {
        const nextLeft = clampComprobanteFloat(
          s.originL + dx,
          8,
          right - COMPROBANTE_FLOAT_MIN_W
        )
        const nextTop = clampComprobanteFloat(
          s.originT + dy,
          8,
          bottom - COMPROBANTE_FLOAT_MIN_H
        )
        setPreviewFloatLeft(nextLeft)
        setPreviewFloatTop(nextTop)
        setPreviewFloatW(right - nextLeft)
        setPreviewFloatH(bottom - nextTop)
      }
    }
    const onUp = (e: PointerEvent) => {
      const s = previewInteractRef.current
      if (!s || e.pointerId !== s.pointerId) return
      previewInteractRef.current = null
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
  }, [])

  const beginPreviewDrag = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return
      e.preventDefault()
      previewInteractRef.current = {
        kind: 'drag',
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originL: previewFloatLRef.current,
        originT: previewFloatTRef.current,
      }
      attachPreviewPointerListeners()
    },
    [attachPreviewPointerListeners]
  )

  const beginPreviewResize = useCallback(
    (corner: ComprobanteResizeCorner) => (e: React.PointerEvent) => {
      if (e.button !== 0) return
      e.preventDefault()
      previewInteractRef.current = {
        kind: 'resize',
        pointerId: e.pointerId,
        corner,
        startX: e.clientX,
        startY: e.clientY,
        originL: previewFloatLRef.current,
        originT: previewFloatTRef.current,
        originW: previewFloatWRef.current,
        originH: previewFloatHRef.current,
      }
      attachPreviewPointerListeners()
    },
    [attachPreviewPointerListeners]
  )

  const handleKpiClick = (estadoKey: string) => {
    setEstado(estadoKey)
    setPage(1)
  }

  const schedulePostMutationSync = useCallback(() => {
    if (postMutationSyncTimerRef.current != null) {
      window.clearTimeout(postMutationSyncTimerRef.current)
    }
    postMutationSyncTimerRef.current = window.setTimeout(() => {
      postMutationSyncTimerRef.current = null
      if (
        typeof document !== 'undefined' &&
        document.visibilityState !== 'visible'
      ) {
        return
      }
      void fetchListado({ silent: true })
    }, 1800)
  }, [fetchListado])

  const handleCambiarEstado = async (
    id: number,
    nuevoEstado: string,
    motivo?: string
  ) => {
    if (diagnosticoNoEmail && nuevoEstado === 'rechazado') {
      toast.error(
        'Modo diagnóstico activo: rechazo bloqueado para evitar envío de correo.'
      )
      return
    }
    setChangingEstadoId(id)

    try {
      const estadoAnteriorEnLista =
        data?.items.find(r => r.id === id)?.estado ?? ''
      const resp = await cambiarEstadoPago(id, nuevoEstado, motivo)

      if (nuevoEstado === 'rechazado') {
        toastAfterRechazoCobros(resp)
      } else {
        toast.success(resp.mensaje || 'Estado actualizado.')
      }

      // Al aprobar: el backend crea el pago en pagos, lo concilia y aplica a cuotas en cascada.
      // Invalidar queries para que prestamos, cuotas y notificaciones de mora se actualicen.
      if (nuevoEstado === 'aprobado') {
        queryClient.invalidateQueries({ queryKey: ['pagos'] })
        queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'] })
        queryClient.invalidateQueries({ queryKey: ['prestamos'] })
        void invalidateListasNotificacionesMora(queryClient)
      }

      // Quitar la fila al instante si ya no pertenece al filtro actual.
      // Vista por defecto ("") muestra solo por gestionar: pendiente/en_revision.
      const quedaEnVistaActual =
        estado === ''
          ? nuevoEstado === 'pendiente' || nuevoEstado === 'en_revision'
          : nuevoEstado === estado

      if (!quedaEnVistaActual) {
        setData(prev => {
          if (!prev) return prev

          return {
            ...prev,
            items: prev.items.filter(r => r.id !== id),
            total: Math.max(0, prev.total - 1),
          }
        })
      }
      setKpis(prev => {
        if (!prev) return prev
        const from = String(
          estadoAnteriorEnLista || ''
        ).trim() as keyof PagosReportadosKpis
        const to = String(nuevoEstado || '').trim() as keyof PagosReportadosKpis
        const next: PagosReportadosKpis = { ...prev }
        if (from in next && typeof next[from] === 'number') {
          ;(next[from] as number) = Math.max(0, Number(next[from]) - 1)
        }
        if (to in next && typeof next[to] === 'number') {
          ;(next[to] as number) = Number(next[to]) + 1
        }
        return next
      })
      schedulePostMutationSync()

      if (nuevoEstado === 'rechazado') {
        setRechazarModal({ open: false, row: null })

        setMotivoRechazo('')
      }
    } catch (e: any) {
      const detail =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        e?.message ||
        'Error al actualizar.'
      toast.error(detail)
    } finally {
      setChangingEstadoId(null)
    }
  }

  const handleAbrirModalRechazo = (row: PagoReportadoItem) => {
    setMotivoRechazo(MENSAJE_RECHAZO_POR_DEFECTO)

    const rowToOpen = { ...row }

    setTimeout(() => setRechazarModal({ open: true, row: rowToOpen }), 0)
  }

  const handleConfirmarRechazo = () => {
    if (!rechazarModal.row || !motivoRechazo.trim()) {
      toast.error('El motivo de rechazo es obligatorio.')

      return
    }

    handleCambiarEstado(rechazarModal.row.id, 'rechazado', motivoRechazo.trim())
  }

  const handleEliminar = async (id: number, ref: string) => {
    const refLabel = (ref || '').trim() || '#' + String(id)
    if (
      !window.confirm(
        'Eliminar el pago reportado ' +
          refLabel +
          '? Esta acción no se puede deshacer.'
      )
    )
      return

    setDeletingId(id)

    try {
      const res = await eliminarPagoReportado(id)
      if (res && res.ok === false) {
        toast.error(res.mensaje || 'No se pudo eliminar.')
        return
      }
      // Quitar la fila al instante aunque el refresh posterior falle (p. ej. 502 temporal).
      setData(prev => {
        if (!prev) return prev
        const nextItems = prev.items.filter(r => r.id !== id)
        if (nextItems.length === prev.items.length) return prev
        return {
          ...prev,
          items: nextItems,
          total: Math.max(0, prev.total - 1),
        }
      })
      setSelectedIds(prev => prev.filter(x => x !== id))
      setKpis(prev => {
        if (!prev) return prev
        const anterior =
          (data?.items ?? []).find(r => r.id === id)?.estado ?? ''
        const from = String(anterior || '').trim() as keyof PagosReportadosKpis
        const next: PagosReportadosKpis = {
          ...prev,
          total: Math.max(0, Number(prev.total || 0) - 1),
        }
        if (from in next && typeof next[from] === 'number') {
          ;(next[from] as number) = Math.max(0, Number(next[from]) - 1)
        }
        return next
      })
      toast.success(res?.mensaje || 'Pago reportado eliminado.')
      schedulePostMutationSync()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(
        typeof detail === 'string'
          ? detail
          : getErrorMessage(e) || 'Error al eliminar.'
      )
    } finally {
      setDeletingId(null)
    }
  }

  const handleVerComprobante = async (id: number) => {
    setViewingComprobanteId(id)
    setPreviewComprobante(prev => {
      if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
      return {
        open: true,
        pagoId: id,
        blobUrl: null,
        contentType: null,
        loading: true,
        rotDeg: 0,
      }
    })

    try {
      const path = `/api/v1/cobros/pagos-reportados/${id}/comprobante`
      const data = await apiClient.getBlob(path)
      const blobUrl = URL.createObjectURL(data)
      setPreviewComprobante({
        open: true,
        pagoId: id,
        blobUrl,
        contentType: data.type || null,
        loading: false,
        rotDeg: 0,
      })
    } catch (e: any) {
      toast.error(e?.message || 'No se pudo abrir el comprobante.')
      setPreviewComprobante(prev => ({ ...prev, loading: false, open: false }))
    } finally {
      setViewingComprobanteId(null)
    }
  }

  const itemsTabla = React.useMemo(() => {
    const base = [...(data?.items ?? [])]
    if (!base.length) return base

    const normalizarCedula = (value: string) =>
      String(value ?? '')
        .replace(/[^0-9A-Za-z]/g, '')
        .toUpperCase()
        .trim()

    const frecuencia = new Map<string, number>()
    base.forEach(row => {
      const key = normalizarCedula(row.cedula_display)
      if (!key) return
      frecuencia.set(key, (frecuencia.get(key) ?? 0) + 1)
    })

    let filtrados = soloCedulasDuplicadas
      ? base.filter(row => {
          const key = normalizarCedula(row.cedula_display)
          return !!key && (frecuencia.get(key) ?? 0) > 1
        })
      : base

    if (soloFallaListaBs) {
      filtrados = filtrados.filter(row =>
        /No pag Bs\.?/i.test(String(row.observacion ?? ''))
      )
    }
    if (soloDuplicadoDocumento) {
      filtrados = filtrados.filter(row =>
        /DUPLICADO/i.test(String(row.observacion ?? ''))
      )
    }

    // Cola operativa: primero la entrada más vieja.
    filtrados.sort((a, b) => {
      const ta = Number(new Date(a.fecha_reporte).getTime())
      const tb = Number(new Date(b.fecha_reporte).getTime())
      if (ta !== tb) return ta - tb

      const aa = normalizarCedula(a.cedula_display)
      const bb = normalizarCedula(b.cedula_display)
      const cmp = aa.localeCompare(bb, 'es', {
        numeric: true,
        sensitivity: 'base',
      })
      if (cmp !== 0) return cmp

      return Number(a.id) - Number(b.id)
    })

    return filtrados
  }, [
    data?.items,
    soloCedulasDuplicadas,
    soloFallaListaBs,
    soloDuplicadoDocumento,
  ])

  const seleccionablesEnPagina = useMemo(
    () => itemsTabla.filter(puedeAprobarMasivoRow).map(r => r.id),
    [itemsTabla]
  )

  const allSeleccionadosEnPagina = useMemo(
    () =>
      seleccionablesEnPagina.length > 0 &&
      seleccionablesEnPagina.every(id => selectedIds.includes(id)),
    [seleccionablesEnPagina, selectedIds]
  )

  useEffect(() => {
    const el = headerCheckboxRef.current
    if (!el) return
    const algunos =
      seleccionablesEnPagina.some(id => selectedIds.includes(id)) &&
      !allSeleccionadosEnPagina
    el.indeterminate = algunos
  }, [seleccionablesEnPagina, selectedIds, allSeleccionadosEnPagina])

  const toggleSeleccionarTodosPagina = useCallback(() => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      const todosMarcados =
        seleccionablesEnPagina.length > 0 &&
        seleccionablesEnPagina.every(id => next.has(id))
      if (todosMarcados) {
        seleccionablesEnPagina.forEach(id => next.delete(id))
      } else {
        seleccionablesEnPagina.forEach(id => next.add(id))
      }
      return Array.from(next)
    })
  }, [seleccionablesEnPagina])

  const toggleRowSelected = useCallback((id: number, checked: boolean) => {
    setSelectedIds(prev => {
      if (checked) return prev.includes(id) ? prev : [...prev, id]
      return prev.filter(x => x !== id)
    })
  }, [])

  const handleAprobarMasivo = async () => {
    const ids = [...selectedIds]
    if (!ids.length) return
    if (
      !window.confirm(
        '¿Aprobar ' +
          String(ids.length) +
          ' pago(s) reportado(s) seleccionado(s)? Se creará el pago en cartera y se aplicará a cuotas por cada uno. ' +
          'Los que fallen (duplicado, sin tasa Bs., etc.) se mostrarán en un resumen.'
      )
    ) {
      return
    }
    setBulkApproving(true)
    let ok = 0
    let fail = 0
    let primerError = ''
    const okIds: number[] = []
    for (const id of ids) {
      try {
        const data = await cambiarEstadoPago(id, 'aprobado')
        ok += 1
        okIds.push(id)
        if (data?.mensaje) {
          /* un toast por fila sería ruidoso; solo contar */
        }
      } catch (e: unknown) {
        fail += 1
        if (!primerError) {
          const d = (e as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail
          primerError =
            typeof d === 'string'
              ? d
              : (e as Error)?.message || 'Error desconocido'
        }
      }
    }
    if (ok > 0) {
      queryClient.invalidateQueries({ queryKey: ['pagos'] })
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos'] })
      void invalidateListasNotificacionesMora(queryClient)
      if (estado !== 'aprobado') {
        const quit = new Set(okIds)
        setData(prev => {
          if (!prev) return prev
          return {
            ...prev,
            items: prev.items.filter(r => !quit.has(r.id)),
            total: Math.max(0, prev.total - okIds.length),
          }
        })
      }
      invalidateCobrosListadoKpisCache()
      void fetchListado({ bypassCache: true, silent: true })
    }
    setSelectedIds([])
    setBulkApproving(false)
    if (fail === 0 && ok > 0) {
      toast.success('Aprobación masiva: ' + String(ok) + ' correcto(s).')
    } else if (ok > 0 && fail > 0) {
      toast(
        'Aprobados: ' +
          String(ok) +
          '. Fallidos: ' +
          String(fail) +
          '.' +
          (primerError ? ' Ejemplo: ' + primerError.slice(0, 200) : ''),
        { duration: 9000 }
      )
    } else if (fail > 0) {
      toast.error(
        'Ninguna aprobación masiva exitosa (' +
          String(fail) +
          ' error(es)). ' +
          (primerError ? primerError.slice(0, 220) : '')
      )
    }
  }

  return (
    <div
      className={cn(
        !dockComprobante && 'space-y-6 p-6',
        dockComprobante &&
          '-mx-4 flex w-[calc(100%+2rem)] max-w-none flex-col gap-0 border-y border-slate-200/70 bg-white p-0 lg:grid lg:h-[calc(100dvh-7.5rem)] lg:max-h-[calc(100dvh-7.5rem)] lg:grid-cols-2 lg:items-stretch lg:divide-x lg:divide-slate-200/70 lg:overflow-hidden'
      )}
    >
      {dockComprobante ? (
        <aside className="flex min-h-[min(36vh,320px)] min-w-0 flex-col bg-slate-100 lg:h-full lg:max-h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-y-contain">
          <div className="flex shrink-0 items-center gap-2 border-b border-slate-200/80 bg-slate-50/95 px-3 py-2">
            <span className="min-w-0 flex-1 truncate text-xs font-semibold text-slate-800">
              Comprobante #{previewComprobante.pagoId ?? ''}
            </span>
            {previewComprobante.contentType?.startsWith('image/') && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 shrink-0 p-0"
                  title="Rotar 90° a la izquierda"
                  aria-label="Rotar 90 grados a la izquierda"
                  onClick={() =>
                    setPreviewComprobante(prev => ({
                      ...prev,
                      rotDeg: (prev.rotDeg - 90 + 360) % 360,
                    }))
                  }
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 shrink-0 p-0"
                  title="Rotar 90° a la derecha"
                  aria-label="Rotar 90 grados a la derecha"
                  onClick={() =>
                    setPreviewComprobante(prev => ({
                      ...prev,
                      rotDeg: (prev.rotDeg + 90) % 360,
                    }))
                  }
                >
                  <span className="inline-flex" aria-hidden>
                    <RotateCcw className="h-4 w-4 scale-x-[-1]" />
                  </span>
                </Button>
              </>
            )}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 w-7 shrink-0 p-0"
              title="Cerrar comprobante"
              onClick={closeComprobantePreview}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden p-2 lg:pl-0 lg:pr-2">
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
              {previewComprobante.loading ? (
                <Loader2 className="h-10 w-10 animate-spin text-slate-500" />
              ) : previewComprobante.blobUrl &&
                previewComprobante.contentType?.startsWith('image/') ? (
                <div
                  className="inline-flex max-h-full max-w-full origin-center transition-transform duration-200"
                  style={{
                    transform: `rotate(${previewComprobante.rotDeg}deg)`,
                  }}
                >
                  <img
                    src={previewComprobante.blobUrl}
                    alt="Comprobante"
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              ) : previewComprobante.blobUrl ? (
                <iframe
                  title={`Comprobante ${previewComprobante.pagoId ?? ''}`}
                  src={previewComprobante.blobUrl}
                  className="h-[min(36vh,320px)] min-h-[200px] w-full flex-1 border-0 lg:h-full lg:min-h-[min(50vh,520px)]"
                />
              ) : (
                <div className="px-3 text-sm text-muted-foreground">
                  No se pudo cargar el comprobante.
                </div>
              )}
            </div>
          </div>
        </aside>
      ) : null}

      <div
        className={cn(
          dockComprobante &&
            'min-h-0 min-w-0 space-y-6 overflow-y-auto overscroll-y-contain px-3 py-4 sm:px-4 lg:py-4 lg:pl-5 lg:pr-0',
          !dockComprobante && 'contents'
        )}
      >
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold">Pagos Reportados</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              {ultimaCargaMs != null
                ? `Última carga del listado: ${ultimaCargaMs} ms`
                : 'Preparando diagnóstico de carga...'}
            </p>
            {diagnosticoNoEmail ? (
              <p className="mt-1 text-xs font-medium text-amber-700">
                Modo diagnóstico activo: no se permite rechazar desde esta
                pantalla para evitar correos.
              </p>
            ) : null}
          </div>

          <a
            href={
              (typeof window !== 'undefined' ? window.location.origin : '') +
              (import.meta.env.BASE_URL || '/').replace(/\/$/, '') +
              '/' +
              PUBLIC_REPORTE_PAGO_PATH
            }
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 text-sm text-blue-600 hover:underline"
          >
            Link al formulario público
          </a>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filtros</CardTitle>
          </CardHeader>

          <CardContent className="flex flex-wrap gap-4">
            <div className="flex min-w-[min(100%,280px)] flex-col gap-1">
              <select
                className="rounded-md border px-3 py-2"
                value={estado}
                onChange={e => setEstado(e.target.value)}
                aria-label="Filtrar por estado del reporte"
              >
                <option value="">
                  Por gestionar (excluye aprobados, importados y rechazados)
                </option>

                <option value="pendiente">Pendiente</option>

                <option value="en_revision">En revisión</option>

                <option value="aprobado">Aprobado</option>

                <option value="rechazado">Rechazado</option>

                <option value="importado">Importado a Pagos</option>
              </select>

              <p className="text-xs text-muted-foreground">
                <strong>No cumplen validadores:</strong> misma regla que la
                carga masiva. Por defecto no se listan aprobados, importados ni
                rechazados, ni filas ya marcadas como exportadas a corrección;
                use &quot;Incluir ya exportados&quot; para volver a ver esas
                últimas. Los rechazados solo con filtro o tarjeta.
              </p>
            </div>

            <div className="flex min-w-[min(100%,320px)] flex-col gap-1">
              <div className="flex flex-wrap items-end gap-2">
                <Input
                  type="date"
                  aria-label="Fecha desde (creación del reporte)"
                  value={fechaDesde}
                  onChange={e => setFechaDesde(e.target.value)}
                  className="w-40"
                />

                <Input
                  type="date"
                  aria-label="Fecha hasta (creación del reporte)"
                  value={fechaHasta}
                  onChange={e => setFechaHasta(e.target.value)}
                  className="w-40"
                />

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => {
                    setFechaDesde(
                      cobrosFechaDesdeHaceNDias(
                        COBROS_REPORTADOS_FILTRO_FECHA_DIAS
                      )
                    )
                    setFechaHasta(cobrosFechaLocalYMD(new Date()))
                    setPage(1)
                  }}
                >
                  Últimos {COBROS_REPORTADOS_FILTRO_FECHA_DIAS} días
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="shrink-0"
                  onClick={() => {
                    setFechaDesde('')
                    setFechaHasta('')
                    setPage(1)
                  }}
                >
                  Sin límite de fechas
                </Button>
              </div>

              <p className="text-xs text-muted-foreground">
                Por defecto se filtra por{' '}
                <strong>fecha de creación del reporte</strong> (mismo criterio
                que el API). Acota el volumen que revisa el servidor sin cambiar
                validadores ni la cola manual. Use «Sin límite de fechas» solo
                cuando necesite todo el historial.
              </p>
            </div>

            <Input
              placeholder="Cédula"
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              className="w-40"
            />

            <Input
              placeholder="Institución"
              value={institucion}
              onChange={e => setInstitucion(e.target.value)}
              className="w-48"
            />

            <label
              htmlFor="cobros-incluir-exportados"
              className="flex max-w-xs cursor-pointer items-start gap-2 text-xs text-muted-foreground"
            >
              <input
                id="cobros-incluir-exportados"
                type="checkbox"
                className="mt-0.5 shrink-0 rounded border-input"
                checked={incluirExportados}
                onChange={e => {
                  setIncluirExportados(e.target.checked)
                  setPage(1)
                }}
              />
              <span>
                Incluir filas ya marcadas como exportadas a corrección (ocultas
                en la vista normal hasta activar esta opción).
              </span>
            </label>

            <label
              htmlFor="cobros-solo-cedulas-duplicadas"
              className="flex max-w-xs cursor-pointer items-start gap-2 text-xs text-muted-foreground"
            >
              <input
                id="cobros-solo-cedulas-duplicadas"
                type="checkbox"
                className="mt-0.5 shrink-0 rounded border-input"
                checked={soloCedulasDuplicadas}
                onChange={e => setSoloCedulasDuplicadas(e.target.checked)}
              />
              <span>Mostrar solo cédulas duplicadas en esta página.</span>
            </label>

            <label
              htmlFor="cobros-solo-falla-lista-bs"
              className="flex max-w-xs cursor-pointer items-start gap-2 text-xs text-muted-foreground"
            >
              <input
                id="cobros-solo-falla-lista-bs"
                type="checkbox"
                className="mt-0.5 shrink-0 rounded border-input"
                checked={soloFallaListaBs}
                onChange={e => setSoloFallaListaBs(e.target.checked)}
              />
              <span>
                Solo filas con falla de lista para pago en Bs. (texto «No pag
                Bs.» en observación; moneda Bs. y cédula no autorizada).
              </span>
            </label>

            <label
              htmlFor="cobros-solo-duplicado-documento"
              className="flex max-w-xs cursor-pointer items-start gap-2 text-xs text-muted-foreground"
            >
              <input
                id="cobros-solo-duplicado-documento"
                type="checkbox"
                className="mt-0.5 shrink-0 rounded border-input"
                checked={soloDuplicadoDocumento}
                onChange={e => setSoloDuplicadoDocumento(e.target.checked)}
              />
              <span>
                Solo filas con DUPLICADO en observación (documento ya en cartera
                o repetido entre reportados en la página).
              </span>
            </label>

            <Button
              onClick={() => {
                setPage(1)
                invalidateCobrosListadoKpisCache()
                setSearchNonce(prev => prev + 1)
              }}
            >
              Buscar
            </Button>
          </CardContent>
        </Card>

        {kpis != null && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleKpiClick('')}
              title="Cola de análisis manual: pendiente, en revisión y aprobados que aún no cumplen validadores (Gemini/reglas). Si Gemini es correcto y no hay observación, no entra en cola."
              className={
                'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
                (estado === ''
                  ? 'border-primary bg-primary/10 font-semibold'
                  : 'border-muted hover:bg-muted/50')
              }
            >
              <span className="block text-xs uppercase tracking-wide text-muted-foreground">
                Por gestionar
              </span>

              <span className="text-2xl font-bold">
                {kpis.pendiente + kpis.en_revision + kpis.aprobado}
              </span>
            </button>

            {(
              ['pendiente', 'en_revision', 'aprobado', 'rechazado'] as const
            ).map(key => {
              const cfg = ESTADO_CONFIG[key]

              const Icon = cfg.Icon

              const selected = estado === key

              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleKpiClick(key)}
                  className={
                    'flex min-w-28 flex-col gap-0.5 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
                    (selected
                      ? 'border-primary bg-primary/10 font-semibold'
                      : 'border-muted hover:bg-muted/50')
                  }
                >
                  <span className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />

                    {cfg.label}
                  </span>

                  <span className="text-2xl font-bold">{kpis[key]}</span>
                </button>
              )
            })}
          </div>
        )}

        <Card>
          <CardContent className="pt-6">
            {loading && data === null ? (
              <div
                className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground"
                role="status"
                aria-live="polite"
              >
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
                <p className="text-base font-medium text-foreground">
                  Consultando cola de reportes…
                </p>
                <p className="max-w-md text-center text-sm">
                  Si la cartera es grande, el servidor puede tardar hasta un
                  minuto en el primer análisis; las siguientes búsquedas suelen
                  ir más rápido.
                </p>
              </div>
            ) : !itemsTabla.length ? (
              <p className="text-gray-500">No hay registros.</p>
            ) : (
              <>
                <div className="mb-2 flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-xs text-muted-foreground">
                    Arrastre el borde derecho del encabezado de cada columna
                    para ajustar el ancho. Se guarda en este navegador.
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 shrink-0 self-start text-xs sm:self-auto"
                    onClick={resetColWidths}
                  >
                    Restaurar anchos
                  </Button>
                </div>
                {(selectedIds.length > 0 || bulkApproving) && (
                  <div className="mb-2 flex flex-wrap items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50/90 px-3 py-2 text-sm text-emerald-950 dark:bg-emerald-950/30 dark:text-emerald-50">
                    <span className="font-medium">
                      {bulkApproving
                        ? 'Aprobando…'
                        : String(selectedIds.length) + ' seleccionado(s)'}
                    </span>
                    <Button
                      type="button"
                      size="sm"
                      className="h-8 bg-emerald-600 text-white hover:bg-emerald-700"
                      disabled={bulkApproving || selectedIds.length === 0}
                      onClick={() => void handleAprobarMasivo()}
                    >
                      {bulkApproving ? (
                        <>
                          <Loader2 className="mr-1.5 inline h-3.5 w-3.5 animate-spin" />
                          Procesando
                        </>
                      ) : (
                        'Aprobar seleccionados'
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8"
                      disabled={bulkApproving}
                      onClick={() => setSelectedIds([])}
                    >
                      Quitar selección
                    </Button>
                  </div>
                )}
                <div className="relative w-full min-w-0 max-w-full overflow-x-auto rounded-lg border">
                  {refreshing ? (
                    <div
                      className="absolute inset-0 z-10 flex items-start justify-center bg-background/70 pt-10 backdrop-blur-[1px]"
                      role="status"
                      aria-live="polite"
                    >
                      <span className="flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm shadow-sm">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Actualizando listado…
                      </span>
                    </div>
                  ) : null}
                  <table className="w-max min-w-full table-fixed border-collapse text-sm">
                    <colgroup>
                      {colWidths.map((w, i) => (
                        <col key={`col-${i}`} style={{ width: w }} />
                      ))}
                    </colgroup>

                    <thead>
                      <tr className="border-b bg-muted/50">
                        {COBROS_REPORTADOS_TABLE_HEAD.map((h, i) => (
                          <th
                            key={h.label}
                            className={cn(
                              'relative whitespace-nowrap py-2 pl-2 pr-3 text-xs font-semibold sm:text-sm',
                              i < COBROS_REPORTADOS_TABLE_HEAD.length - 1 &&
                                'border-r border-border/60',
                              h.align === 'left' && 'text-left',
                              h.align === 'right' && 'text-right',
                              h.align === 'center' && 'text-center'
                            )}
                            style={{
                              width: colWidths[i],
                              minWidth: colWidths[i],
                            }}
                          >
                            <span
                              className={cn(
                                'block min-w-0 overflow-hidden text-ellipsis pr-2',
                                h.align === 'right' && 'pr-3',
                                h.align === 'center' && 'px-1'
                              )}
                            >
                              {h.label === 'Sel.' ? (
                                <span className="flex justify-center py-0.5">
                                  <input
                                    ref={headerCheckboxRef}
                                    type="checkbox"
                                    className="h-4 w-4 cursor-pointer accent-primary"
                                    checked={allSeleccionadosEnPagina}
                                    onChange={toggleSeleccionarTodosPagina}
                                    disabled={
                                      bulkApproving ||
                                      seleccionablesEnPagina.length === 0
                                    }
                                    aria-label="Seleccionar en esta página pendientes y en revisión"
                                    title="Solo pendiente o en revisión en esta página"
                                  />
                                </span>
                              ) : (
                                h.label
                              )}
                            </span>
                            <button
                              type="button"
                              className="absolute right-0 top-0 z-20 h-full w-2 cursor-col-resize touch-none border-0 bg-transparent p-0 hover:bg-primary/15 active:bg-primary/25"
                              aria-label={`Redimensionar columna ${h.label}`}
                              title="Arrastrar para cambiar ancho"
                              onMouseDown={e => handleColResizeStart(i, e)}
                            />
                          </th>
                        ))}
                      </tr>
                    </thead>

                    <tbody>
                      {itemsTabla.map((row: PagoReportadoItem) => (
                        <tr
                          key={row.id}
                          className="border-b transition-colors hover:bg-muted/20"
                        >
                          <td className="px-1 py-2 text-center align-middle">
                            {puedeAprobarMasivoRow(row) ? (
                              <input
                                type="checkbox"
                                className="h-4 w-4 cursor-pointer accent-primary"
                                checked={selectedIds.includes(row.id)}
                                onChange={e =>
                                  toggleRowSelected(row.id, e.target.checked)
                                }
                                disabled={
                                  bulkApproving || changingEstadoId === row.id
                                }
                                aria-label={
                                  'Seleccionar reporte ' +
                                  String(row.referencia_interna || row.id)
                                }
                              />
                            ) : (
                              <span
                                className="text-muted-foreground"
                                title="Solo se puede marcar pendiente o en revisión"
                              >
                                -
                              </span>
                            )}
                          </td>
                          <td
                            className={
                              'whitespace-nowrap px-2 py-2 align-middle text-xs sm:text-sm ' +
                              ((row.observacion || '').trim().length > 0
                                ? 'bg-destructive/10 font-medium text-destructive'
                                : '')
                            }
                            title={
                              (row.observacion || '').trim().length > 0
                                ? 'Observación: ' + (row.observacion || '')
                                : undefined
                            }
                          >
                            {(row.observacion || '').trim().length > 0 && (
                              <AlertCircle
                                className="mr-1 inline-block h-4 w-4 align-middle"
                                aria-hidden
                              />
                            )}

                            <span className="block truncate">
                              {row.cedula_display}
                            </span>
                          </td>

                          <td className="min-w-0 px-2 py-2 align-middle">
                            {(() => {
                              const hasDuplicado = /DUPLICADO/i.test(
                                row.observacion || ''
                              )
                              const showMercantilExceptionTag =
                                hasDuplicado &&
                                isMercantilBank(row.institucion_financiera)
                              return (
                                <>
                                  <span
                                    className="block truncate text-xs sm:text-sm"
                                    title={row.institucion_financiera}
                                  >
                                    {row.institucion_financiera}
                                  </span>
                                  {showMercantilExceptionTag ? (
                                    <span
                                      className="mt-1 inline-flex rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700"
                                      title="Duplicado por número de operación en Mercantil: excepción activa (revisión manual)."
                                    >
                                      Excepción Mercantil
                                    </span>
                                  ) : null}
                                </>
                              )
                            })()}
                          </td>

                          <td className="whitespace-nowrap px-2 py-2 text-right align-middle text-xs sm:text-sm">
                            <span>
                              {row.monto} {row.moneda}
                            </span>
                            {row.moneda === 'BS' &&
                              row.equivalente_usd != null && (
                                <span
                                  className="mt-0.5 block text-xs text-emerald-700"
                                  title={
                                    row.tasa_cambio_bs_usd != null
                                      ? `Tasa: ${row.tasa_cambio_bs_usd.toLocaleString('es-VE')} Bs/USD`
                                      : 'Equivalente en USD'
                                  }
                                >
                                  {'≈ '}
                                  {row.equivalente_usd.toLocaleString('es-VE', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })}{' '}
                                  USD
                                </span>
                              )}
                            {row.moneda === 'BS' &&
                              row.equivalente_usd == null && (
                                <span
                                  className="mt-0.5 block text-xs text-amber-600"
                                  title="No hay tasa registrada para esta fecha. Registre la tasa en Pagos antes de aprobar."
                                >
                                  Sin tasa
                                </span>
                              )}
                          </td>

                          <td className="whitespace-nowrap px-2 py-2 align-middle text-xs sm:text-sm">
                            <span className="block truncate">
                              {row.fecha_pago}
                            </span>
                          </td>

                          <td
                            className={
                              'min-w-0 px-2 py-2 align-middle ' +
                              (/DUPLICADO/i.test(row.observacion || '')
                                ? 'bg-destructive/10 font-medium text-destructive'
                                : '')
                            }
                            title={
                              /DUPLICADO/i.test(row.observacion || '')
                                ? 'DUPLICADO: el número de operación / documento coincide con otro registro en pagos o con otro reporte en esta página.'
                                : row.numero_operacion
                            }
                          >
                            <span className="block truncate font-mono text-[11px] sm:text-xs">
                              {row.numero_operacion}
                            </span>
                          </td>

                          <td className="whitespace-nowrap px-2 py-2 align-middle text-xs sm:text-sm">
                            <span className="block truncate">
                              {new Date(row.fecha_reporte).toLocaleDateString()}
                            </span>
                          </td>

                          <td className="px-2 py-2 align-middle">
                            {row.tiene_comprobante ? (
                              <button
                                type="button"
                                onClick={() => handleVerComprobante(row.id)}
                                disabled={viewingComprobanteId === row.id}
                                className="mx-auto inline-flex min-w-0 max-w-full items-center justify-center gap-1 rounded-md border border-border bg-muted/30 px-2 py-1 text-[11px] font-medium text-foreground shadow-none transition-colors hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-ring/40 disabled:opacity-60"
                                title="Abrir imagen o PDF del comprobante"
                              >
                                {viewingComprobanteId === row.id ? (
                                  <Loader2
                                    className="h-3.5 w-3.5 shrink-0 animate-spin"
                                    aria-hidden
                                  />
                                ) : (
                                  <Eye
                                    className="h-3.5 w-3.5 shrink-0 opacity-80"
                                    aria-hidden
                                  />
                                )}
                                <span className="truncate underline decoration-muted-foreground/40 underline-offset-2">
                                  Ver
                                </span>
                              </button>
                            ) : (
                              <div
                                className="mx-auto flex max-w-[5.5rem] items-center justify-center rounded-md border border-dashed border-muted-foreground/30 bg-muted/15 px-1.5 py-1 text-center"
                                title="Sin archivo adjunto en este reporte"
                              >
                                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                                  Sin archivo
                                </span>
                              </div>
                            )}
                          </td>

                          <td
                            className={
                              'min-w-0 px-2 py-2 align-middle ' +
                              ((row.observacion || '').trim().length > 0
                                ? 'bg-destructive/10'
                                : '')
                            }
                            title={
                              /NO CLIENTES/i.test(row.observacion || '')
                                ? 'NO CLIENTES: la cédula del reporte (' +
                                  row.cedula_display +
                                  ') no figura en la tabla clientes. Se compara normalizada (sin guión, sin ceros a la izquierda). Verifique en Préstamos > Clientes o registre al cliente.'
                                : /DUPLICADO/i.test(row.observacion || '')
                                  ? 'DUPLICADO: ya existe en la tabla pagos (documento/referencia normalizado) o hay otro reporte con el mismo número en esta página. No se debe aprobar dos veces el mismo comprobante.'
                                  : /No pag Bs|solo Bs|Bolívares/i.test(
                                        row.observacion || ''
                                      )
                                    ? 'No pag Bs.: la cédula no está en la lista autorizada para bolívares (cedulas_reportar_bs). Use USD o agregue la cédula en Configuración > Pagos.'
                                    : (row.observacion ?? '')
                            }
                          >
                            {row.observacion ? (
                              <div
                                className={
                                  'text-xs ' +
                                  ((row.observacion || '').trim().length > 0
                                    ? 'font-medium text-destructive'
                                    : 'text-muted-foreground')
                                }
                              >
                                {(row.observacion || '')
                                  .split('/')
                                  .map(part => part.trim())
                                  .filter(Boolean)
                                  .map((part, idx) => (
                                    <span
                                      key={`${row.id}-obs-${idx}`}
                                      className="block leading-5"
                                    >
                                      {part}
                                    </span>
                                  ))}
                              </div>
                            ) : (
                              '-'
                            )}
                          </td>

                          <td className="whitespace-nowrap px-2 py-2 align-middle">
                            {(() => {
                              const cfg = ESTADO_CONFIG[row.estado] ?? {
                                label: row.estado,
                                short: row.estado,
                                variant: 'outline' as const,
                                Icon: Clock,
                              }

                              const Icon = cfg.Icon

                              return (
                                <Badge
                                  variant={cfg.variant}
                                  className="inline-flex max-w-full items-center gap-0.5 px-1.5 py-0.5 text-[11px] font-normal leading-tight"
                                  title={cfg.label}
                                >
                                  <Icon
                                    className="h-3 w-3 shrink-0"
                                    aria-hidden
                                  />

                                  <span className="truncate">{cfg.short}</span>
                                </Badge>
                              )
                            })()}
                          </td>

                          <td className="px-2 py-2 align-middle">
                            <div className="grid grid-cols-2 justify-items-center gap-1">
                              {/* Estado envío recibo: X = no enviado, visto = entregado, triángulo = en revisión */}

                              <span
                                className="flex h-7 w-7 shrink-0 items-center justify-center text-muted-foreground"
                                title={
                                  row.estado === 'aprobado'
                                    ? row.tiene_recibo_pdf &&
                                      row.correo_enviado_a
                                      ? 'Recibo enviado por correo'
                                      : 'No se envió recibo por correo'
                                    : 'En revisión'
                                }
                              >
                                {row.estado === 'aprobado' ? (
                                  row.tiene_recibo_pdf &&
                                  row.correo_enviado_a ? (
                                    <CheckCircle
                                      className="h-3.5 w-3.5 text-green-600"
                                      aria-hidden
                                    />
                                  ) : (
                                    <XCircle
                                      className="h-3.5 w-3.5 text-muted-foreground"
                                      aria-hidden
                                    />
                                  )
                                ) : (
                                  <AlertTriangle
                                    className="h-3.5 w-3.5 text-blue-600"
                                    aria-hidden
                                  />
                                )}
                              </span>

                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 shrink-0"
                                title="Ver detalle"
                                onClick={() =>
                                  navigate(
                                    '/cobros/pagos-reportados/' + String(row.id)
                                  )
                                }
                              >
                                <FileText className="h-3.5 w-3.5" />
                              </Button>

                              {(row.estado === 'pendiente' ||
                                row.estado === 'en_revision' ||
                                row.estado === 'rechazado') && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7 shrink-0"
                                  title="Editar (monto, referencia, cédula, etc.)"
                                  onClick={() =>
                                    navigate(
                                      '/cobros/pagos-reportados/' +
                                        String(row.id) +
                                        '/editar'
                                    )
                                  }
                                >
                                  <Edit className="h-3.5 w-3.5" />
                                </Button>
                              )}

                              <div className="relative inline-block h-7 w-7 shrink-0 overflow-hidden rounded-md">
                                <select
                                  className="absolute inset-0 box-border h-full max-h-full w-full min-w-0 max-w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
                                  value=""
                                  title="Estado"
                                  aria-label="Cambiar estado del reporte"
                                  onChange={e => {
                                    const v = e.target.value

                                    e.target.value = ''

                                    if (!v) return

                                    if (v === 'rechazado') {
                                      handleAbrirModalRechazo(row)

                                      return
                                    }

                                    handleCambiarEstado(row.id, v)
                                  }}
                                  disabled={changingEstadoId === row.id}
                                >
                                  <option value="">Seleccionar estado</option>

                                  <option value="en_revision">
                                    En revisión
                                  </option>

                                  <option value="aprobado">Aprobar</option>

                                  {!diagnosticoNoEmail ? (
                                    <option value="rechazado">Rechazar</option>
                                  ) : null}
                                </select>

                                <span
                                  className="pointer-events-none flex h-7 w-7 items-center justify-center rounded-md border border-input bg-background"
                                  title="Estado"
                                >
                                  {changingEstadoId === row.id ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <Settings className="h-3.5 w-3.5" />
                                  )}
                                </span>
                              </div>

                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="relative z-10 h-7 w-7 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                                title="Eliminar"
                                onClick={() =>
                                  handleEliminar(row.id, row.referencia_interna)
                                }
                                disabled={deletingId === row.id}
                              >
                                {deletingId === row.id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Trash2 className="h-3.5 w-3.5" />
                                )}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {data && data.total > data.per_page && (
              <div className="mt-4 flex justify-between">
                <p className="text-sm text-gray-600">Total: {data.total}</p>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                  >
                    Anterior
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page * data.per_page >= data.total}
                    onClick={() => setPage(p => p + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {previewComprobante.open &&
          !lgViewport &&
          typeof document !== 'undefined' &&
          createPortal(
            <div
              className="fixed inset-0 z-[240] bg-black/20"
              onClick={closeComprobantePreview}
              role="presentation"
            >
              <div
                className="fixed z-[241] flex select-none flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl ring-1 ring-black/10"
                style={{
                  left: previewFloatLeft,
                  top: previewFloatTop,
                  width: previewFloatW,
                  height: previewFloatH,
                }}
                onClick={e => e.stopPropagation()}
                role="dialog"
                aria-label="Visor temporal de comprobante"
              >
                <div
                  className="flex shrink-0 cursor-grab items-center gap-2 border-b border-slate-100 bg-slate-50/95 px-2 py-2 active:cursor-grabbing"
                  onPointerDown={beginPreviewDrag}
                >
                  <span
                    className="flex shrink-0 flex-col justify-center gap-0.5 py-0.5"
                    aria-hidden
                  >
                    <span className="h-0.5 w-4 rounded-full bg-slate-500" />
                    <span className="h-0.5 w-4 rounded-full bg-slate-500" />
                    <span className="h-0.5 w-4 rounded-full bg-slate-500" />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-700">
                    Comprobante #{previewComprobante.pagoId ?? ''}
                  </span>
                  {previewComprobante.contentType?.startsWith('image/') && (
                    <>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        title="Rotar 90° a la izquierda"
                        aria-label="Rotar 90 grados a la izquierda"
                        onClick={() =>
                          setPreviewComprobante(prev => ({
                            ...prev,
                            rotDeg: (prev.rotDeg - 90 + 360) % 360,
                          }))
                        }
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        title="Rotar 90° a la derecha"
                        aria-label="Rotar 90 grados a la derecha"
                        onClick={() =>
                          setPreviewComprobante(prev => ({
                            ...prev,
                            rotDeg: (prev.rotDeg + 90) % 360,
                          }))
                        }
                      >
                        <span className="inline-flex" aria-hidden>
                          <RotateCcw className="h-4 w-4 scale-x-[-1]" />
                        </span>
                      </Button>
                    </>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    title="Cerrar visor"
                    onClick={closeComprobantePreview}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="relative min-h-0 flex-1 overflow-hidden p-1">
                  <div className="flex h-full min-h-0 w-full items-center justify-center overflow-auto rounded-md bg-slate-50">
                    {previewComprobante.loading ? (
                      <Loader2 className="h-10 w-10 animate-spin text-slate-500" />
                    ) : previewComprobante.blobUrl &&
                      previewComprobante.contentType?.startsWith('image/') ? (
                      <div
                        className="inline-flex max-h-full max-w-full origin-center transition-transform duration-200"
                        style={{
                          transform: `rotate(${previewComprobante.rotDeg}deg)`,
                        }}
                      >
                        <img
                          src={previewComprobante.blobUrl}
                          alt="Comprobante"
                          className="max-h-full max-w-full object-contain"
                        />
                      </div>
                    ) : previewComprobante.blobUrl ? (
                      <iframe
                        title={`Comprobante ${previewComprobante.pagoId ?? ''}`}
                        src={previewComprobante.blobUrl}
                        className="h-full min-h-0 w-full border-0"
                      />
                    ) : (
                      <div className="px-3 text-sm text-muted-foreground">
                        No se pudo cargar el comprobante.
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    aria-label="Redimensionar esquina superior izquierda"
                    className="absolute left-0 top-8 z-30 h-5 w-5 cursor-nwse-resize bg-transparent p-0"
                    onPointerDown={beginPreviewResize('nw')}
                  />
                  <button
                    type="button"
                    aria-label="Redimensionar esquina superior derecha"
                    className="absolute right-0 top-8 z-30 h-5 w-5 cursor-nesw-resize bg-transparent p-0"
                    onPointerDown={beginPreviewResize('ne')}
                  />
                  <button
                    type="button"
                    aria-label="Redimensionar esquina inferior izquierda"
                    className="absolute bottom-0 left-0 z-30 h-5 w-5 cursor-nesw-resize bg-transparent p-0"
                    onPointerDown={beginPreviewResize('sw')}
                  />
                  <button
                    type="button"
                    aria-label="Redimensionar esquina inferior derecha"
                    className="absolute bottom-0 right-0 z-30 h-5 w-5 cursor-nwse-resize bg-transparent p-0"
                    onPointerDown={beginPreviewResize('se')}
                  />
                </div>
              </div>
            </div>,
            document.body
          )}

        {/* Modal: interfaz rápida para escribir mensaje de rechazo y enviar correo al cliente */}

        <Dialog
          open={rechazarModal.open}
          onOpenChange={open => {
            if (!open) {
              setRechazarModal({ open: false, row: null })

              setMotivoRechazo('')
            }
          }}
        >
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <XCircle className="h-5 w-5" /> Rechazar pago reportado
              </DialogTitle>

              <DialogDescription>
                {rechazarModal.row && (
                  <>
                    Referencia:{' '}
                    <strong>
                      {rechazarModal.row.referencia_interna?.startsWith('#')
                        ? rechazarModal.row.referencia_interna
                        : '#' + String(rechazarModal.row.referencia_interna)}
                    </strong>
                    {rechazarModal.row.correo_enviado_a && (
                      <span className="mt-1 block">
                        Se enviará un correo automáticamente a{' '}
                        <strong>{rechazarModal.row.correo_enviado_a}</strong>{' '}
                        desde <strong>notificaciones@rapicreditca.com</strong>{' '}
                        con el mensaje y el comprobante adjunto.
                      </span>
                    )}
                  </>
                )}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-2">
              <label className="block text-sm font-medium">
                Mensaje para el cliente (obligatorio)
              </label>

              <textarea
                className="min-h-[100px] w-full resize-y rounded-md border px-3 py-2 text-sm"
                placeholder="Indique el motivo del rechazo. Este texto se enviará por correo al cliente."
                value={motivoRechazo}
                onChange={e => setMotivoRechazo(e.target.value)}
                autoFocus
              />
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setRechazarModal({ open: false, row: null })

                  setMotivoRechazo('')
                }}
              >
                Cancelar
              </Button>

              <Button
                variant="destructive"
                onClick={handleConfirmarRechazo}
                disabled={
                  diagnosticoNoEmail ||
                  !motivoRechazo.trim() ||
                  changingEstadoId === rechazarModal.row?.id
                }
              >
                {changingEstadoId === rechazarModal.row?.id ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="mr-2 h-4 w-4" />
                )}
                {diagnosticoNoEmail
                  ? 'Bloqueado en diagnóstico (sin correo)'
                  : 'Rechazar y enviar correo'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}
