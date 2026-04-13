import {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
  Fragment,
} from 'react'

import { Link, useSearchParams, useLocation } from 'react-router-dom'

import { motion } from 'framer-motion'

import {
  RefreshCw,
  Settings,
  AlertTriangle,
  Clock,
  Mail,
  Download,
  Bell,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  X,
  Scale,
  LayoutList,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  notificacionService,
  TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL,
  type AplicarAbonosDriveCuotasResponse,
  type ClienteRetrasadoItem,
  type CompararAbonosDriveCuotasResponse,
  type EstadisticasPorTab,
} from '../services/notificacionService'

import { prestamoService } from '../services/prestamoService'

import { revisionManualService } from '../services/revisionManualService'

import { useSimpleAuth } from '../store/simpleAuthStore'

import { toast } from 'sonner'

import { ConfiguracionNotificaciones } from '../components/notificaciones/ConfiguracionNotificaciones'

import {
  NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
  NOTIFICACIONES_D2_ANTES_QUERY_KEY,
  NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
  NOTIFICACIONES_MORA_BROADCAST_CHANNEL,
  NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,
  invalidateListasNotificacionesMora,
  invalidatePagosPrestamosRevisionYCuotas,
} from '../constants/queryKeys'

import { NOTIFICACIONES_QUERY_KEYS } from '../queries/notificaciones'

import { marcarReturnRevisionDesdeNotificaciones } from '../constants/revisionNavigation'

import { isRequestCanceled } from '../utils/requestCanceled'

import { getErrorMessage, isAxiosTimeoutError } from '../types/errors'

/** Máximo de filas (clientes / casos) por página en cada pestaña de listado de notificaciones. */
const NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA = 10

/**
 * GET comparar-abonos por lote: evita disparar cientos de XHR en paralelo (Firefox/Render
 * cancelan o vacían respuestas) y reduce presión en el worker de la hoja.
 */
const COMPARAR_ABONOS_GENERAL_CONCURRENCIA = 8

async function compararAbonosGeneralEnLotes(
  targets: ReadonlyArray<{
    cedula: string
    prestamoId: number
    rowKey: string
  }>,
  chunkSize: number,
  isCanceled: () => boolean
): Promise<Array<readonly [string, CompararAbonosDriveCuotasResponse | null]>> {
  const out: Array<readonly [string, CompararAbonosDriveCuotasResponse | null]> =
    []
  const n = Math.max(1, chunkSize)
  for (let i = 0; i < targets.length; i += n) {
    if (isCanceled()) return out
    const slice = targets.slice(i, i + n)
    const parte = await Promise.all(
      slice.map(async t => {
        try {
          const d = await notificacionService.getCompararAbonosDriveCuotas({
            cedula: t.cedula,
            prestamoId: t.prestamoId,
          })
          return [t.rowKey, d] as const
        } catch {
          return [t.rowKey, null] as const
        }
      })
    )
    out.push(...parte)
  }
  return out
}

/** Etiquetas de origen en el submódulo GENERAL (misma semántica que cada submenú). */
const CASO_NOTIF_GENERAL_D1 = 'Día siguiente al vencimiento'
const CASO_NOTIF_GENERAL_PREJ = 'Atraso 5 cuotas (prejudicial)'
const CASO_NOTIF_GENERAL_D2 = '2 días antes del vencimiento'

/** Botones numéricos mostrados en la barra de paginación (ventana deslizante). */
const NOTIFICACIONES_VENTANA_NUMEROS_PAGINA = 5

/** Fecha calendario actual en America/Caracas como YYYY-MM-DD (para max en input date). */
function fechaHoyCaracasISO(): string {
  return new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/Caracas',
  })
}

/** Interpreta la respuesta del envío manual para que no parezca «no pasó nada» si enviados = 0. */
function toastResultadoEnvioNotificaciones(
  res: {
    mensaje?: string
    enviados?: number
    sin_email?: number
    fallidos?: number
    total_en_lista?: number
    omitidos_config?: number
    omitidos_paquete_incompleto?: number
  },
  filasVisiblesEnTabla: number
) {
  const enviados = Number(res.enviados ?? 0)
  const totalLista =
    res.total_en_lista != null && !Number.isNaN(Number(res.total_en_lista))
      ? Number(res.total_en_lista)
      : filasVisiblesEnTabla
  const sinEmail = Number(res.sin_email ?? 0)
  const fallidos = Number(res.fallidos ?? 0)
  const omitPkg = Number(res.omitidos_paquete_incompleto ?? 0)
  const omitCfg = Number(res.omitidos_config ?? 0)
  const msgBase = (res.mensaje ?? 'Envío finalizado').trim()

  if (enviados === 0 && totalLista > 0) {
    toast.warning(
      `${msgBase} Nadie recibió correo aunque la lista tenía ${totalLista} fila(s). Revise: email del cliente, modo prueba, fila «Envío» en Configuración, plantilla y PDF de cobranza (paquete incompleto). Sin email: ${sinEmail}. Omitidos por config: ${omitCfg}. Paquete incompleto: ${omitPkg}. Fallidos SMTP: ${fallidos}.`,
      { duration: 14000 }
    )
    return
  }

  if (enviados === 0 && totalLista === 0) {
    toast.message(
      'No había destinatarios en la lista para esta fecha y criterio. No se envió ningún correo.',
      { duration: 7000 }
    )
    return
  }

  toast.success(
    `${msgBase} Enviados: ${enviados}. Sin email: ${sinEmail}. Fallidos: ${fallidos}.`,
    { duration: 9000 }
  )
}

function toastErrorTrasEnvioManual(e: unknown, fraseRevisionConfig: string) {
  if (isAxiosTimeoutError(e)) {
    const min = Math.max(
      1,
      Math.round(TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL / 60000)
    )
    toast.warning(
      `El navegador dejó de esperar tras ${min} min (timeout). Con muchas filas y adjuntos el envío puede seguir en el servidor: antes de reintentar, revise «Último envío por lote» o el historial para no duplicar correos. ${fraseRevisionConfig}`,
      { duration: 20000 }
    )
    return
  }

  toast.error(
    `No se pudo completar el envío: ${getErrorMessage(e)}. ${fraseRevisionConfig}`
  )
}

export type NotificacionesModulo = 'a1dia' | 'a3cuotas' | 'd2antes' | 'general'

type TabId =
  | 'dias_1_atraso'
  | 'prejudicial'
  | 'd2antes'
  | 'general_todos'
  | 'configuracion'

function tabsParaModulo(
  modulo: NotificacionesModulo
): { id: TabId; label: string; icon: typeof Clock }[] {
  if (modulo === 'general') {
    return [{ id: 'general_todos', label: 'General', icon: LayoutList }]
  }
  if (modulo === 'a3cuotas') {
    return [
      { id: 'prejudicial', label: 'Atraso 5 cuotas', icon: Clock },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'd2antes') {
    return [
      { id: 'd2antes', label: '2 días antes', icon: Clock },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  return [
    {
      id: 'dias_1_atraso',
      label: 'Día siguiente al vencimiento',
      icon: Clock,
    },
    { id: 'configuracion', label: 'Configuración', icon: Settings },
  ]
}

function tabListadoDefault(modulo: NotificacionesModulo): TabId {
  if (modulo === 'general') return 'general_todos'
  if (modulo === 'a3cuotas') return 'prejudicial'
  if (modulo === 'd2antes') return 'd2antes'
  return 'dias_1_atraso'
}

/** Clave de GET estadisticas-por-tab / rebotados (coincide con tipo_tab en envíos). */

type EstadisticaTabKey = keyof EstadisticasPorTab

function textoTotalPendientePagar(row: ClienteRetrasadoItem): string {
  const v =
    row.total_pendiente_pagar != null
      ? Number(row.total_pendiente_pagar)
      : row.monto != null
        ? Number(row.monto)
        : null
  return v != null && Number.isFinite(v) ? v.toLocaleString('es') : '-'
}

/** Mismo id de préstamo que usa estado de cuenta / revisión (BD). */
function textoNumeroCreditoNotif(row: ClienteRetrasadoItem): string {
  const pid = row.prestamo_id
  if (pid == null) return '—'
  const n = Number(pid)
  return Number.isFinite(n) ? String(n) : '—'
}

/** Valor numérico para ordenar (misma prioridad que el texto mostrado). */
function numericTotalPendienteSort(row: ClienteRetrasadoItem): number | null {
  if (row.total_pendiente_pagar != null) {
    const n = Number(row.total_pendiente_pagar)
    return Number.isFinite(n) ? n : null
  }
  if (row.monto != null) {
    const n = Number(row.monto)
    return Number.isFinite(n) ? n : null
  }
  return null
}

/** Timestamp para ordenar fechas de vencimiento; vacío al final en orden ascendente. */
function fechaVencSortValue(s: string | undefined): number {
  if (s == null || String(s).trim() === '') return Number.POSITIVE_INFINITY
  const t = Date.parse(s)
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t
}

function cuotasAtrasadasSortValue(row: ClienteRetrasadoItem): number {
  const n = row.cuotas_atrasadas ?? row.total_cuotas_atrasadas
  if (n == null || Number.isNaN(Number(n))) return Number.POSITIVE_INFINITY
  return Number(n)
}

type NotificacionesCuotasSortCol =
  | 'numero_cuota'
  | 'fecha_vencimiento'
  | 'cuotas_atrasadas'
  | 'total_pendiente'

function SortArrowsCuotas({
  column,
  labelAsc,
  labelDesc,
  sortCol,
  sortDir,
  onAsc,
  onDesc,
}: {
  column: NotificacionesCuotasSortCol
  labelAsc: string
  labelDesc: string
  sortCol: NotificacionesCuotasSortCol | null
  sortDir: 'asc' | 'desc'
  onAsc: (c: NotificacionesCuotasSortCol) => void
  onDesc: (c: NotificacionesCuotasSortCol) => void
}) {
  const upActive = sortCol === column && sortDir === 'asc'
  const downActive = sortCol === column && sortDir === 'desc'
  const baseBtn =
    'rounded p-0.5 text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500'
  return (
    <span
      className="inline-flex shrink-0 flex-col gap-0 leading-none"
      role="group"
    >
      <button
        type="button"
        className={`${baseBtn} ${upActive ? 'text-blue-600' : ''}`}
        aria-label={labelAsc}
        onClick={() => onAsc(column)}
      >
        <ChevronUp className="h-3.5 w-3.5" strokeWidth={2.5} />
      </button>
      <button
        type="button"
        className={`${baseBtn} ${downActive ? 'text-blue-600' : ''}`}
        aria-label={labelDesc}
        onClick={() => onDesc(column)}
      >
        <ChevronDown className="h-3.5 w-3.5" strokeWidth={2.5} />
      </button>
    </span>
  )
}

/** Texto fijo de probación / cierre rápido desde la tabla de notificaciones. */
const TEXTO_NOTA_REVISION_DESDE_NOTIF = 'Revisión en módulo de notificación'

function detalleErrorRevisionNotif(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail
  return typeof d === 'string'
    ? d
    : (e as Error)?.message || 'Error desconocido'
}

function soloDigitosCedulaNotif(s: string): string {
  return String(s ?? '').replace(/\D/g, '')
}

/** Coincidencia por subcadena: prioriza comparación solo dígitos (V-123 / 123). */
function filaCoincideFiltroCedulaNotif(
  row: ClienteRetrasadoItem,
  filtro: string
): boolean {
  const t = filtro.trim()
  if (!t) return true
  const qDigits = soloDigitosCedulaNotif(t)
  const ced = String(row.cedula ?? '')
  if (qDigits.length > 0) {
    return soloDigitosCedulaNotif(ced).includes(qDigits)
  }
  return ced.toLowerCase().includes(t.toLowerCase())
}

/** Filtro de columna «Diferencia Abono» (General): misma semántica que el modal ABONOS vs cuotas. */
type FiltroDiferenciaAbonoGeneral = 'todas' | 'cero' | 'drive_mayor'

function filaCumpleFiltroDiferenciaAbonoGeneral(
  filtro: FiltroDiferenciaAbonoGeneral,
  cmp: CompararAbonosDriveCuotasResponse
): boolean {
  if (filtro === 'todas') return true
  const puede =
    cmp.puede_aplicar === true ||
    (typeof cmp.indicador === 'string' && cmp.indicador.toLowerCase() === 'si')
  if (filtro === 'drive_mayor') return puede
  if (filtro === 'cero') return cmp.coincide_aproximado === true
  return true
}

function fmtDiferenciaAbonoCelda(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Number(n).toLocaleString('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function DiferenciaAbonoGeneralCell({
  row,
  data,
  isLoading,
  isError,
}: {
  row: ClienteRetrasadoItem
  data?: CompararAbonosDriveCuotasResponse
  isLoading: boolean
  isError: boolean
}) {
  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  if (pid == null || !ced) {
    return (
      <span className="text-xs text-muted-foreground" title="Sin cédula o préstamo">
        —
      </span>
    )
  }
  if (isLoading) {
    return <span className="text-xs text-muted-foreground">…</span>
  }
  if (isError || !data) {
    return (
      <span
        className="text-xs text-amber-800"
        title="No se pudo obtener la comparación ABONOS vs cuotas"
      >
        —
      </span>
    )
  }
  return (
    <span
      className={`tabular-nums text-sm font-medium ${
        data.coincide_aproximado ? 'text-green-700' : 'text-amber-800'
      }`}
      title="Diferencia (hoja Drive − total pagado en cuotas), misma regla que el icono de balanza."
    >
      {fmtDiferenciaAbonoCelda(data.diferencia)}
    </span>
  )
}

/**
 * Triángulo: un clic marca revisado (visto) y deja constancia en notas del cliente; si no hay
 * permiso para notas, en observaciones de la revisión. Visto: solo admin puede reabrir a revisando.
 */
function RevisionManualNotifCell({ row }: { row: ClienteRetrasadoItem }) {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const pid = row.prestamo_id
  const rev = (row.revision_manual_estado || 'pendiente').toLowerCase().trim()
  const esVisto = rev === 'revisado'
  const [busy, setBusy] = useState(false)

  if (pid == null) return null

  const lineaAuditoria = () => {
    const ts = new Date().toLocaleString('es-VE', {
      timeZone: 'America/Caracas',
    })
    return `${ts} - ${TEXTO_NOTA_REVISION_DESDE_NOTIF}`
  }

  const invalidarListas = async () => {
    await invalidateListasNotificacionesMora(queryClient, {
      skipCrossTabBroadcast: true,
    })
    await queryClient.invalidateQueries({
      queryKey: ['revision-manual-prestamos'],
    })
  }

  const marcarVisto = async () => {
    setBusy(true)
    try {
      const detalle =
        await revisionManualService.getDetallePrestamoRevision(pid)
      const estadoSrv = (
        detalle?.revision?.estado_revision || 'pendiente'
      ).toLowerCase()

      if (estadoSrv === 'revisado') {
        await invalidarListas()
        toast.message('Ya constaba como revisado.')
        return
      }

      const clienteId = detalle?.cliente?.cliente_id as number | undefined
      if (!clienteId) {
        toast.error('No se pudo obtener el cliente del préstamo.')
        return
      }

      const notasPrev = String(detalle?.cliente?.notas || '').trim()
      const linea = lineaAuditoria()
      const notasNuevas = notasPrev ? `${notasPrev}\n${linea}` : linea

      let notasClienteOk = false
      try {
        await revisionManualService.editarCliente(
          clienteId,
          { notas: notasNuevas },
          { prestamoId: pid }
        )
        notasClienteOk = true
      } catch (e) {
        const msg = detalleErrorRevisionNotif(e)
        toast.message(
          `Notas del cliente no actualizadas (${msg}). Se deja constancia en la revisión.`
        )
      }

      await revisionManualService.cambiarEstadoRevision(pid, {
        nuevo_estado: 'revisado',
        ...(notasClienteOk ? {} : { observaciones: linea }),
      })

      await invalidarListas()
      toast.success('Marcado como visto (revisión en módulo de notificación).')
    } catch (e) {
      toast.error(detalleErrorRevisionNotif(e))
    } finally {
      setBusy(false)
    }
  }

  const quitarVisto = async () => {
    if (!esAdmin) {
      toast.error(
        'Solo un administrador puede quitar el visto. Use Revisión manual en el menú.'
      )
      return
    }
    setBusy(true)
    try {
      await revisionManualService.cambiarEstadoRevision(pid, {
        nuevo_estado: 'revisando',
      })
      await invalidarListas()
      toast.success('Revisión reabierta (estado revisando).')
    } catch (e) {
      toast.error(detalleErrorRevisionNotif(e))
    } finally {
      setBusy(false)
    }
  }

  const btnBase =
    'inline-flex h-9 w-9 items-center justify-center rounded-md border border-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50'

  if (!esVisto) {
    return (
      <button
        type="button"
        role="switch"
        aria-checked={false}
        disabled={busy}
        title="Marcar visto: revisión cerrada y nota genérica en datos del cliente (o en observaciones si no hay permiso)"
        aria-label="Marcar como revisado desde notificaciones con nota genérica"
        onClick={() => {
          if (busy) return
          void marcarVisto()
        }}
        className={`${btnBase} bg-amber-50 text-amber-600 hover:bg-amber-100`}
      >
        <AlertTriangle className="h-4 w-4" aria-hidden />
      </button>
    )
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked
      disabled={busy}
      title={
        esAdmin
          ? 'Visto: clic para reabrir revisión (solo admin)'
          : 'Visto: solo un administrador puede reabrir'
      }
      aria-label="Revisión cerrada. Clic para reabrir si es administrador"
      onClick={() => {
        if (busy) return
        void quitarVisto()
      }}
      className={`${btnBase} bg-emerald-50 text-green-600 hover:bg-emerald-100`}
    >
      <CheckCircle2 className="h-4 w-4" aria-hidden />
    </button>
  )
}

function umbralConfirmaAbonosUsd(
  data: CompararAbonosDriveCuotasResponse | null
): number {
  const u = data?.umbral_doble_confirmacion_abonos_usd
  return u != null && Number.isFinite(Number(u)) ? Number(u) : 5000
}

function abonosSuperanUmbralConfirmo(
  data: CompararAbonosDriveCuotasResponse | null,
  abonos: number | null | undefined
): boolean {
  if (abonos == null || Number.isNaN(Number(abonos))) return false
  return Number(abonos) > umbralConfirmaAbonosUsd(data)
}

/**
 * Icono junto a revisión manual: compara ABONOS (hoja CONCILIACIÓN en BD) vs suma total_pagado en cuotas del préstamo.
 * El borrado de pagos y la cascada solo ocurren si el usuario pulsa explícitamente «Sí» y confirma (no al abrir el diálogo).
 */
function CompararAbonosDriveCuotasCell({ row }: { row: ClienteRetrasadoItem }) {
  const queryClient = useQueryClient()
  const location = useLocation()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  const [open, setOpen] = useState(false)
  const [paso, setPaso] = useState<'resumen' | 'confirmar'>('resumen')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [data, setData] = useState<CompararAbonosDriveCuotasResponse | null>(null)
  const [confirmacionMontosAltos, setConfirmacionMontosAltos] = useState('')

  /** Cierra el modal sin cambiar de ruta (mismo submenú de notificaciones). */
  const onDialogAbonosOpenChange = useCallback((v: boolean) => {
    setOpen(v)
    if (!v) {
      setPaso('resumen')
      setData(null)
      setConfirmacionMontosAltos('')
    }
  }, [])

  if (pid == null || !ced) return null

  const loteResuelto =
    !data?.requiere_seleccion_lote ||
    Boolean((data?.lote_aplicado ?? '').toString().trim())

  const puedeOperar =
    loteResuelto &&
    (data?.puede_aplicar === true ||
      (typeof data?.indicador === 'string' && data.indicador.toLowerCase() === 'si'))

  const abrir = async (loteExplicito?: string | null) => {
    setOpen(true)
    setPaso('resumen')
    setConfirmacionMontosAltos('')
    setLoading(true)
    setData(null)
    try {
      const loteQ = (loteExplicito ?? '').trim()
      const res = await notificacionService.getCompararAbonosDriveCuotas({
        cedula: ced,
        prestamoId: pid,
        ...(loteQ ? { lote: loteQ } : {}),
      })
      setData(res)
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo comparar ABONOS vs cuotas.')
      onDialogAbonosOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  const aplicar = async () => {
    setApplying(true)
    try {
      const loteAplicar = (data?.lote_aplicado ?? '').toString().trim() || undefined
      const needConf =
        data != null && abonosSuperanUmbralConfirmo(data, data.abonos_drive)
      const res: AplicarAbonosDriveCuotasResponse =
        await notificacionService.postAplicarAbonosDriveACuotas({
          cedula: ced,
          prestamoId: pid,
          ...(loteAplicar ? { lote: loteAplicar } : {}),
          ...(needConf
            ? { confirmacionMontosAltos: confirmacionMontosAltos.trim() }
            : {}),
        })
      toast.success(
        `Aplicado: pago #${res.pago_id}. Pagos eliminados: ${res.pagos_eliminados}. Cuotas completadas: ${res.cuotas_completadas}.`
      )
      onDialogAbonosOpenChange(false)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
        skipNotificacionesMora: true,
        includeDashboardMenu: true,
      })
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo aplicar ABONOS a cuotas.')
    } finally {
      setApplying(false)
    }
  }

  const fmt = (n: number | null | undefined) =>
    n == null || Number.isNaN(Number(n))
      ? '—'
      : Number(n).toLocaleString('es-VE', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })

  const btnBase =
    'inline-flex h-9 w-9 items-center justify-center rounded-md border border-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50'

  const pillBase =
    'inline-flex min-w-[2.25rem] items-center justify-center rounded-md border px-2 py-1 text-xs font-semibold'

  const needConfirmaMontosAltos =
    data != null && abonosSuperanUmbralConfirmo(data, data.abonos_drive)

  return (
    <>
      <button
        type="button"
        className={`${btnBase} bg-sky-50 text-sky-700 hover:bg-sky-100`}
        title="Comparar ABONOS (Drive / hoja CONCILIACIÓN) con total pagado en cuotas (BD)"
        aria-label="Comparar ABONOS de la hoja con total pagado en cuotas"
        onClick={() => {
          void abrir()
        }}
      >
        <Scale className="h-4 w-4" aria-hidden />
      </button>

      <Dialog open={open} onOpenChange={onDialogAbonosOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {paso === 'confirmar'
                ? 'Confirmar aplicación desde la hoja'
                : 'ABONOS (hoja) vs cuotas pagadas'}
            </DialogTitle>
          </DialogHeader>

          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : paso === 'confirmar' && data ? (
            <div className="space-y-3 text-sm">
              <p className="text-amber-900">
                Se eliminarán todos los pagos del préstamo #{data.prestamo_id} y se registrará un
                único pago por{' '}
                <span className="font-semibold tabular-nums">{fmt(data.abonos_drive)}</span>{' '}
                (ABONOS hoja), aplicado en cascada a las cuotas. Esta acción no se deshace desde
                aquí.
              </p>
              <div className="rounded-md border border-slate-200 bg-muted/30 p-3 text-xs text-foreground">
                <p className="mb-1 font-semibold text-slate-800">Verifique antes de aplicar</p>
                <ul className="list-none space-y-1 tabular-nums">
                  <li>
                    Cédula: <span className="font-medium">{data.cedula}</span>
                  </li>
                  <li>
                    Préstamo: <span className="font-medium">#{data.prestamo_id}</span>
                  </li>
                  <li>
                    Lote (hoja):{' '}
                    <span className="font-mono font-medium">
                      {(data.lote_aplicado ?? '').toString().trim() || '—'}
                    </span>
                  </li>
                  <li>
                    Monto ABONOS (hoja):{' '}
                    <span className="font-semibold">{fmt(data.abonos_drive)}</span>
                  </li>
                </ul>
              </div>
              {needConfirmaMontosAltos ? (
                <div className="space-y-2 rounded-md border border-amber-300 bg-amber-50/90 p-3 text-xs text-amber-950">
                  <p className="font-medium">
                    Monto elevado (&gt; {umbralConfirmaAbonosUsd(data).toLocaleString('es-VE')} USD).
                    Escriba <span className="font-mono">CONFIRMO</span> para continuar.
                  </p>
                  <Input
                    id="confirma-abonos-montos-altos"
                    autoComplete="off"
                    placeholder="CONFIRMO"
                    value={confirmacionMontosAltos}
                    onChange={e => setConfirmacionMontosAltos(e.target.value)}
                    className="bg-white font-mono text-sm"
                    aria-label="Confirmación por monto elevado: escriba CONFIRMO"
                  />
                </div>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Solo continúe si revisó cédula, hoja y montos. Requiere administrador.
              </p>
            </div>
          ) : data ? (
            <div className="space-y-3 text-sm">
              <p className="text-muted-foreground">
                Cédula <span className="font-medium text-foreground">{data.cedula}</span>
                {' · '}
                Préstamo <span className="font-medium text-foreground">#{data.prestamo_id}</span>
              </p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <Link
                  to={`/revision-manual/editar/${pid}`}
                  state={{
                    returnTo: `${location.pathname}${location.search || ''}`,
                  }}
                  className="font-medium text-blue-600 hover:underline"
                >
                  Abrir en revisión manual
                </Link>
                <span className="text-muted-foreground">
                  (edición del préstamo y cuotas en otra pantalla)
                </span>
              </div>

              {data.hoja_sync_antigua ? (
                <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                  La hoja supera las 48 h desde la última sincronización (aprox.{' '}
                  {data.hoja_sync_antigua_horas != null
                    ? `${data.hoja_sync_antigua_horas} h`
                    : '—'}
                  ). Resincronice CONCILIACIÓN si necesita ABONOS al día.
                </p>
              ) : null}

              {data.prestamo_huella ? (
                <div className="rounded-md border bg-slate-50 p-3 text-xs text-slate-900">
                  <p className="mb-1 font-semibold text-slate-800">
                    Huella del préstamo en BD (alinear con fila de la hoja)
                  </p>
                  <ul className="list-none space-y-0.5 tabular-nums">
                    <li>
                      Total financiamiento:{' '}
                      {fmt(data.prestamo_huella.total_financiamiento)}
                    </li>
                    <li>N.º cuotas: {data.prestamo_huella.numero_cuotas}</li>
                    <li>Modalidad: {data.prestamo_huella.modalidad_pago || '—'}</li>
                  </ul>
                </div>
              ) : null}

              {!puedeOperar ? (
                <p className="rounded-md border border-slate-200 bg-muted/40 p-2 text-xs text-slate-800">
                  <span className="font-medium">Regla: </span>
                  solo se puede aplicar desde aquí si ABONOS en la hoja es{' '}
                  <strong>mayor</strong> que la suma de los pagos reflejados en cuotas del préstamo
                  (total pagado en cuotas), más una tolerancia de ±{data.tolerancia}. Si ABONOS es
                  igual o menor (p. ej. cero o ya cubierto en BD), el flujo queda en «No»: aquí no se
                  reordenan pagos ni se corrigen diferencias pequeñas; use revisión manual o la
                  conciliación habitual.
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground text-xs">Indicador:</span>
                <button
                  type="button"
                  disabled={!puedeOperar || !esAdmin || applying}
                  title={
                    !esAdmin
                      ? 'Solo administradores pueden operar.'
                      : data?.requiere_seleccion_lote && !loteResuelto
                        ? 'Elija primero el lote de la hoja que corresponde a este préstamo.'
                        : puedeOperar
                          ? 'Pulsar Sí para continuar al paso de confirmación (no aplica nada todavía).'
                          : 'ABONOS no supera el total en cuotas: no hay operación.'
                  }
                  onClick={() => {
                    if (!puedeOperar || !esAdmin || applying) return
                    setPaso('confirmar')
                  }}
                  className={`${pillBase} ${
                    puedeOperar
                      ? 'border-green-600 bg-green-50 text-green-800 hover:bg-green-100 disabled:opacity-50'
                      : 'cursor-not-allowed border-muted bg-muted/40 text-muted-foreground'
                  }`}
                  aria-label={
                    puedeOperar
                      ? 'Sí: ABONOS mayor que total en cuotas; pulse para confirmar operación'
                      : 'Sí: no aplica'
                  }
                >
                  Sí
                </button>
                <button
                  type="button"
                  className={`${pillBase} ${
                    !puedeOperar
                      ? 'border-slate-600 bg-slate-100 text-slate-800 hover:bg-slate-200/80'
                      : 'border-muted bg-muted/30 text-muted-foreground hover:bg-muted/50'
                  }`}
                  title="Cierra el cuadro sin aplicar nada; permanece en esta misma pantalla de notificaciones."
                  aria-label="No: cerrar el cuadro sin cambiar de submenú"
                  onClick={() => onDialogAbonosOpenChange(false)}
                >
                  No
                </button>
              </div>

              {data.requiere_seleccion_lote &&
              data.opciones_lote &&
              data.opciones_lote.length > 0 ? (
                <div className="rounded-md border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-950">
                  <p className="mb-2 font-medium">
                    Hay varios lotes en la hoja para esta cédula. Elija el que corresponde a este
                    préstamo (solo se usará el abono de esa fila; no se mezclan otros créditos).
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {data.opciones_lote.map(op => (
                      <Button
                        key={op.lote}
                        type="button"
                        size="sm"
                        variant="outline"
                        className="border-amber-300 bg-white text-amber-950 hover:bg-amber-100"
                        disabled={loading}
                        onClick={() => {
                          void abrir(op.lote)
                        }}
                      >
                        Lote {op.lote} — {fmt(op.abonos)}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {data.lote_aplicado && loteResuelto ? (
                <p className="rounded-md border border-sky-200 bg-sky-50/90 p-2 text-xs text-sky-950">
                  <span className="font-semibold">Resumen: </span>
                  Lote <span className="font-mono">{data.lote_aplicado}</span>
                  {' · '}
                  ABONOS hoja{' '}
                  <span className="font-medium tabular-nums">{fmt(data.abonos_drive)}</span>
                  {' · '}
                  Préstamo #{data.prestamo_id}
                </p>
              ) : data.lote_aplicado ? (
                <p className="text-xs text-muted-foreground">
                  Lote usado para esta comparación:{' '}
                  <span className="font-mono font-medium text-foreground">{data.lote_aplicado}</span>
                </p>
              ) : null}

              <dl className="grid grid-cols-1 gap-2 rounded-md border bg-muted/30 p-3">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">ABONOS (hoja Drive)</dt>
                  <dd className="font-medium tabular-nums">{fmt(data.abonos_drive)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Total pagado (cuotas)</dt>
                  <dd className="font-medium tabular-nums">
                    {fmt(data.total_pagado_cuotas)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Diferencia (hoja − cuotas)</dt>
                  <dd
                    className={`font-semibold tabular-nums ${
                      data.coincide_aproximado ? 'text-green-700' : 'text-amber-800'
                    }`}
                  >
                    {fmt(data.diferencia)}
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-muted-foreground">
                Filas de la hoja que corresponden a este préstamo:{' '}
                <span className="font-medium text-foreground">
                  {data.filas_hoja_coincidentes}
                </span>
                {data.filas_misma_cedula_hoja != null ? (
                  <>
                    {' '}
                    · Filas con la misma cédula en la hoja (todas):{' '}
                    <span className="font-medium text-foreground">
                      {data.filas_misma_cedula_hoja}
                    </span>
                  </>
                ) : null}
                {data.hoja_synced_at ? (
                  <>
                    {' '}
                    · Última sync hoja:{' '}
                    <span className="font-medium text-foreground">
                      {new Date(data.hoja_synced_at).toLocaleString('es-VE', {
                        timeZone: 'America/Caracas',
                      })}
                    </span>
                  </>
                ) : null}
              </p>
              {data.columna_cedula_detectada ||
              data.columna_abonos_detectada ||
              data.columna_lote_detectada ? (
                <p className="text-xs text-muted-foreground">
                  Columnas detectadas:{' '}
                  <span className="font-mono text-foreground">
                    {data.columna_cedula_detectada ?? '—'}
                  </span>
                  {' · '}
                  <span className="font-mono text-foreground">
                    {data.columna_abonos_detectada ?? '—'}
                  </span>
                  {data.columna_lote_detectada ? (
                    <>
                      {' · '}
                      <span className="font-mono text-foreground">
                        {data.columna_lote_detectada}
                      </span>
                    </>
                  ) : null}
                </p>
              ) : null}
              {data.advertencias?.length ? (
                <ul className="list-disc space-y-1 pl-4 text-xs text-amber-900">
                  {data.advertencias.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              ) : null}
              {data.coincide_aproximado ? (
                <p className="text-xs font-medium text-green-700">
                  Coinciden (tolerancia ±{data.tolerancia}).
                </p>
              ) : data.diferencia != null ? (
                <p className="text-xs text-amber-900">
                  Hay diferencia mayor a la tolerancia (±{data.tolerancia}). Revise sync de la
                  hoja o pagos aplicados a cuotas.
                </p>
              ) : null}
              {!esAdmin && puedeOperar ? (
                <p className="text-xs text-muted-foreground">
                  El indicador «Sí» requiere administrador para operar.
                </p>
              ) : null}
            </div>
          ) : null}

          <DialogFooter className="gap-2 sm:gap-0">
            {paso === 'confirmar' ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  disabled={applying}
                  onClick={() => {
                    setConfirmacionMontosAltos('')
                    setPaso('resumen')
                  }}
                >
                  Volver
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  disabled={
                    applying ||
                    !esAdmin ||
                    (needConfirmaMontosAltos &&
                      confirmacionMontosAltos.trim().toUpperCase() !== 'CONFIRMO')
                  }
                  onClick={() => {
                    void aplicar()
                  }}
                >
                  {applying ? 'Aplicando…' : 'Confirmar y aplicar'}
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => onDialogAbonosOpenChange(false)}
              >
                Cerrar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function tipoParaKpiYRebotados(tab: TabId): EstadisticaTabKey | null {
  switch (tab) {
    case 'dias_1_atraso':
      return 'dias_1_retraso'

    case 'prejudicial':
      return 'prejudicial'

    case 'd2antes':
      return 'd_2_antes_vencimiento'

    case 'general_todos':
      return null

    default:
      return null
  }
}

type NotificacionesProps = {
  modulo?: NotificacionesModulo
}

export function Notificaciones({ modulo = 'a1dia' }: NotificacionesProps) {
  const TABS = tabsParaModulo(modulo)

  const listadoDefault = tabListadoDefault(modulo)

  useEffect(() => {
    marcarReturnRevisionDesdeNotificaciones()
  }, [])

  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab')

  const fcParam = searchParams.get('fc')

  const [fechaReferenciaCaracas, setFechaReferenciaCaracas] = useState(() => {
    const raw = fcParam?.trim()
    return raw && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : ''
  })

  useEffect(() => {
    const raw = searchParams.get('fc')?.trim()
    if (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      setFechaReferenciaCaracas(prev => (prev === raw ? prev : raw))
    } else if (!raw) {
      setFechaReferenciaCaracas(prev => (prev === '' ? prev : ''))
    }
  }, [searchParams])

  const setFechaCaracasYUrl = (valor: string) => {
    const v = valor.trim()
    setFechaReferenciaCaracas(v)
    setSearchParams(
      p => {
        const next = new URLSearchParams(p)
        if (!v) next.delete('fc')
        else next.set('fc', v)
        return next
      },
      { replace: true }
    )
  }

  const fechaCaracasApi =
    fechaReferenciaCaracas && fechaReferenciaCaracas.trim()
      ? fechaReferenciaCaracas.trim()
      : undefined

  const [activeTab, setActiveTab] = useState<TabId>(() =>
    tabParam && TABS.some(t => t.id === tabParam)
      ? (tabParam as TabId)
      : listadoDefault
  )

  useEffect(() => {
    if (
      tabParam &&
      TABS.some(t => t.id === tabParam) &&
      activeTab !== tabParam
    ) {
      setActiveTab(tabParam as TabId)
    }
  }, [tabParam, activeTab, TABS])

  useEffect(() => {
    const t = searchParams.get('tab')
    if (
      t === 'liquidados' ||
      t === 'masivos' ||
      t === 'dias_5_atraso' ||
      t === 'dias_30_atraso' ||
      (modulo === 'a3cuotas' && t === 'dias_1_atraso') ||
      (modulo === 'a3cuotas' && t === 'd2antes') ||
      (modulo === 'a1dia' && t === 'prejudicial') ||
      (modulo === 'a1dia' && t === 'd2antes') ||
      (modulo === 'd2antes' && (t === 'dias_1_atraso' || t === 'prejudicial')) ||
      (modulo === 'general' &&
        t !== 'general_todos' &&
        Boolean(t)) ||
      (modulo === 'general' && t === 'configuracion')
    ) {
      setSearchParams(
        p => {
          const next = new URLSearchParams(p)

          next.delete('tab')

          return next
        },
        { replace: true }
      )
    }
  }, [searchParams, setSearchParams, modulo])

  useEffect(() => {
    if (modulo !== 'general') return
    if (activeTab === 'configuracion') {
      setActiveTab('general_todos')
      setSearchParams(
        p => {
          const next = new URLSearchParams(p)
          next.delete('tab')
          next.delete('cfg')
          return next
        },
        { replace: true }
      )
    }
  }, [modulo, activeTab, setSearchParams])

  const setActiveTabAndUrl = (tab: TabId) => {
    setActiveTab(tab)

    setSearchParams(p => {
      const next = new URLSearchParams(p)

      if (tab === listadoDefault) next.delete('tab')
      else next.set('tab', tab)

      if (tab !== 'configuracion') next.delete('cfg')

      return next
    })
  }

  const { data, isPending, isFetched, isError, error, refetch, isFetching } =
    useQuery({
      queryKey: [
        ...NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
        fechaCaracasApi ?? null,
      ],

      queryFn: () => notificacionService.getClientesRetrasados(fechaCaracasApi),

      // Siempre considerar obsoleto: al volver a la pestaña o tras invalidar por pagos, se refetch al instante.
      staleTime: 0,

      refetchOnWindowFocus: true,

      // Sin placeholderData: con v5, placeholder hace isPending=false y la tabla se ve vacía mientras carga (Render frío).
      /** En Configuración no se listan cuotas: evita GET pesado y errores 500 por carga/BD innecesaria. */

      enabled:
        (modulo === 'a1dia' || modulo === 'general') &&
        activeTab !== 'configuracion',
    })

  const {
    data: dataD2Antes,
    isPending: isPendingD2,
    isFetched: isFetchedD2,
    isError: isErrorD2,
    error: errorD2,
    refetch: refetchD2,
    isFetching: isFetchingD2,
  } = useQuery({
    queryKey: [...NOTIFICACIONES_D2_ANTES_QUERY_KEY, fechaCaracasApi ?? null],

    queryFn: () =>
      notificacionService.getCuotasPendiente2DiasAntes(fechaCaracasApi),

    // El criterio d2antes (vencimiento exactamente hoy+2) cambia muy poco intradía;
    // 30 s de gracia evitan GETs en cada foco de ventana sin sacrificar frescura operativa.
    staleTime: 30_000,

    refetchOnWindowFocus: true,

    enabled:
      (modulo === 'd2antes' || modulo === 'general') &&
      activeTab !== 'configuracion',
  })

  const {
    data: dataPrejudicial,
    isPending: isPendingPrej,
    isFetched: isFetchedPrej,
    isError: isErrorPrej,
    error: errorPrej,
    refetch: refetchPrej,
    isFetching: isFetchingPrej,
  } = useQuery({
    queryKey: [
      ...NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,
      fechaCaracasApi ?? null,
    ],

    queryFn: () =>
      notificacionService.listarNotificacionesPrejudiciales(
        undefined,
        fechaCaracasApi
      ),

    staleTime: 0,

    refetchOnWindowFocus: true,

    enabled:
      (modulo === 'a3cuotas' || modulo === 'general') &&
      activeTab !== 'configuracion',
  })

  const { data: estadisticasPorTab } = useQuery({
    queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,

    queryFn: () => notificacionService.getEstadisticasPorTab(),

    staleTime: 0,

    enabled: activeTab !== 'configuracion' && modulo !== 'general',

    placeholderData: {
      dias_5: { enviados: 0, rebotados: 0 },

      dias_3: { enviados: 0, rebotados: 0 },

      dias_1: { enviados: 0, rebotados: 0 },

      hoy: { enviados: 0, rebotados: 0 },

      dias_1_retraso: { enviados: 0, rebotados: 0 },

      dias_3_retraso: { enviados: 0, rebotados: 0 },

      dias_5_retraso: { enviados: 0, rebotados: 0 },

      dias_30_retraso: { enviados: 0, rebotados: 0 },

      prejudicial: { enviados: 0, rebotados: 0 },

      masivos: { enviados: 0, rebotados: 0 },

      liquidados: { enviados: 0, rebotados: 0 },

      d_2_antes_vencimiento: { enviados: 0, rebotados: 0 },
    } as EstadisticasPorTab,
  })

  const queryClient = useQueryClient()

  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return undefined
    let ch: BroadcastChannel
    try {
      ch = new BroadcastChannel(NOTIFICACIONES_MORA_BROADCAST_CHANNEL)
    } catch {
      return undefined
    }
    ch.onmessage = (ev: MessageEvent<{ type?: string }>) => {
      if (ev?.data?.type !== 'invalidate') return
      void invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
    }
    return () => {
      ch.onmessage = null
      ch.close()
    }
  }, [queryClient])

  const [actualizandoListas, setActualizandoListas] = useState(false)

  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)

  const [enviandoPrejudicial, setEnviandoPrejudicial] = useState(false)

  const [enviandoD2Antes, setEnviandoD2Antes] = useState(false)

  const [enviandoPago1Dia, setEnviandoPago1Dia] = useState(false)

  /** Confirmación en pantalla (sustituye window.confirm: más clara y fiable en Firefox). */
  const [confirmEnvio, setConfirmEnvio] = useState<null | {
    kind: 'prejudicial' | 'd2antes' | 'pago1dia'
    n: number
  }>(null)

  const operacionListaAbortRef = useRef<AbortController | null>(null)

  const beginOperacionListaAbortable = () => {
    operacionListaAbortRef.current?.abort()
    const c = new AbortController()
    operacionListaAbortRef.current = c
    return c
  }

  const cancelarOperacionListaEmergencia = () => {
    operacionListaAbortRef.current?.abort()
    operacionListaAbortRef.current = null
    setActualizandoListas(false)
    setEnviandoPrejudicial(false)
    setEnviandoD2Antes(false)
    setEnviandoPago1Dia(false)
    toast.warning(
      'Cancelación: se cortó la petición en el navegador. El servidor puede seguir unos segundos.'
    )
  }

  const hayOperacionListaEnCurso =
    actualizandoListas ||
    enviandoPrejudicial ||
    enviandoD2Antes ||
    enviandoPago1Dia

  const handleDescargarEstadoCuentaPdf = async (prestamoId: number) => {
    setDescargandoEstadoCuentaId(prestamoId)

    try {
      await prestamoService.descargarEstadoCuentaPDF(prestamoId)

      toast.success('Estado de cuenta PDF descargado exitosamente')
    } catch (e) {
      console.error(e)

      toast.error('Error al exportar estado de cuenta PDF')
    } finally {
      setDescargandoEstadoCuentaId(null)
    }
  }

  const estadoCuentaPdfCell = (prestamoId: number | undefined) => {
    if (prestamoId == null) {
      return (
        <span className="text-xs text-gray-400" title="Sin id de préstamo">
          -
        </span>
      )
    }

    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-9 w-9 shrink-0 text-blue-600 hover:bg-blue-50 hover:text-blue-800"
        disabled={descargandoEstadoCuentaId === prestamoId}
        onClick={() => handleDescargarEstadoCuentaPdf(prestamoId)}
        title="Exportar estado de cuenta en PDF (mismo que en tabla de amortización)"
        aria-label="Exportar estado de cuenta en PDF"
      >
        <Download
          className={`h-4 w-4 ${
            descargandoEstadoCuentaId === prestamoId ? 'animate-pulse' : ''
          }`}
          aria-hidden
        />
      </Button>
    )
  }

  const handleRefresh = async () => {
    const ac = beginOperacionListaAbortable()
    setActualizandoListas(true)
    try {
      await notificacionService.actualizarNotificaciones({
        signal: ac.signal,
      })
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })
      await Promise.all([
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_D2_ANTES_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
        }),
      ])
      setCompararAbonoGeneralTick(t => t + 1)
      toast.success(
        'Listas y KPI actualizados. El envio de correos y campanas sigue siendo manual desde esta pantalla o configuracion.'
      )
    } catch (e) {
      console.error(e)
      if (isRequestCanceled(e)) {
        toast.info('Actualización cancelada.')
        return
      }
      toast.error(
        'No se pudo recalcular la mora en el servidor. Puede reintentar o revisar conexion y permisos.'
      )
    } finally {
      if (operacionListaAbortRef.current === ac) {
        operacionListaAbortRef.current = null
      }
      setActualizandoListas(false)
    }
  }

  const ejecutarEnvioManualTrasConfirmar = async (p: {
    kind: 'prejudicial' | 'd2antes' | 'pago1dia'
    n: number
  }) => {
    const { kind, n } = p

    if (kind === 'prejudicial') {
      const ac = beginOperacionListaAbortable()
      setEnviandoPrejudicial(true)
      const loadingId = toast.loading(
        'Enviando correos… con muchas filas puede tardar más de 10 minutos. No cierre esta pestaña.'
      )

      try {
        const res = await notificacionService.enviarNotificacionesPrejudiciales(
          {
            signal: ac.signal,
            fechaCaracas: fechaCaracasApi,
          }
        )

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)

        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
        })

        await invalidateListasNotificacionesMora(queryClient, {
          skipCrossTabBroadcast: true,
        })

        await queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
        })
      } catch (e) {
        console.error(e)
        toast.dismiss(loadingId)
        if (isRequestCanceled(e)) {
          toast.info('Envío cancelado en el navegador.')
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise PREJUDICIAL en Configuración y el correo del servidor.'
        )
      } finally {
        if (operacionListaAbortRef.current === ac) {
          operacionListaAbortRef.current = null
        }
        setEnviandoPrejudicial(false)
      }
      return
    }

    if (kind === 'd2antes') {
      const ac = beginOperacionListaAbortable()
      setEnviandoD2Antes(true)
      const loadingId = toast.loading(
        'Enviando correos… con muchas filas puede tardar más de 10 minutos. No cierre esta pestaña.'
      )

      try {
        const res = await notificacionService.enviarCasoManual(
          'PAGO_2_DIAS_ANTES_PENDIENTE',
          { signal: ac.signal, fechaCaracas: fechaCaracasApi }
        )

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)

        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
        })

        await invalidateListasNotificacionesMora(queryClient, {
          skipCrossTabBroadcast: true,
        })

        await queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
        })
      } catch (e) {
        console.error(e)
        toast.dismiss(loadingId)
        if (isRequestCanceled(e)) {
          toast.info('Envío cancelado en el navegador.')
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise PAGO_2_DIAS_ANTES_PENDIENTE en Configuración.'
        )
      } finally {
        if (operacionListaAbortRef.current === ac) {
          operacionListaAbortRef.current = null
        }
        setEnviandoD2Antes(false)
      }
      return
    }

    const ac = beginOperacionListaAbortable()
    setEnviandoPago1Dia(true)
    const loadingId = toast.loading(
      'Enviando correos… con muchas filas puede tardar más de 10 minutos. No cierre esta pestaña.'
    )

    try {
      const res = await notificacionService.enviarCasoManual(
        'PAGO_1_DIA_ATRASADO',
        { signal: ac.signal, fechaCaracas: fechaCaracasApi }
      )

      toast.dismiss(loadingId)
      toastResultadoEnvioNotificaciones(res, n)

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })

      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })

      await queryClient.refetchQueries({
        queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
      })
    } catch (e) {
      console.error(e)
      toast.dismiss(loadingId)
      if (isRequestCanceled(e)) {
        toast.info('Envío cancelado en el navegador.')
        return
      }

      toastErrorTrasEnvioManual(
        e,
        'Revise PAGO_1_DIA_ATRASADO en Configuración y el correo del servidor.'
      )
    } finally {
      if (operacionListaAbortRef.current === ac) {
        operacionListaAbortRef.current = null
      }
      setEnviandoPago1Dia(false)
    }
  }

  const solicitarConfirmacionEnvioPrejudicial = () => {
    if (modulo !== 'a3cuotas') return
    const n = dataPrejudicial?.items?.length ?? 0
    setConfirmEnvio({ kind: 'prejudicial', n })
  }

  const solicitarConfirmacionEnvioD2Antes = () => {
    if (modulo !== 'd2antes') return
    const n = dataD2Antes?.items?.length ?? 0
    setConfirmEnvio({ kind: 'd2antes', n })
  }

  const solicitarConfirmacionEnvioPago1Dia = () => {
    if (modulo !== 'a1dia') return
    const n = data?.dias_1_atraso?.length ?? 0
    setConfirmEnvio({ kind: 'pago1dia', n })
  }

  const confirmarEnvioManualYEnviar = () => {
    const p = confirmEnvio
    if (!p) return
    setConfirmEnvio(null)
    void ejecutarEnvioManualTrasConfirmar(p)
  }

  const list = useMemo((): ClienteRetrasadoItem[] => {
    if (modulo === 'general' && activeTab === 'general_todos') {
      const a = (data?.dias_1_atraso ?? []).map(r => ({
        ...r,
        notificacion_caso: CASO_NOTIF_GENERAL_D1,
      }))
      const b = (dataPrejudicial?.items ?? []).map(r => ({
        ...r,
        notificacion_caso: CASO_NOTIF_GENERAL_PREJ,
      }))
      const c = (dataD2Antes?.items ?? []).map(r => ({
        ...r,
        notificacion_caso: CASO_NOTIF_GENERAL_D2,
      }))
      return [...a, ...b, ...c]
    }

    if (modulo === 'a3cuotas') {
      if (activeTab !== 'prejudicial') return []
      return dataPrejudicial?.items ?? []
    }

    if (modulo === 'd2antes') {
      if (activeTab !== 'd2antes') return []
      return dataD2Antes?.items ?? []
    }

    if (!data) return []

    switch (activeTab) {
      case 'dias_1_atraso':
        return data.dias_1_atraso ?? []

      default:
        return []
    }
  }, [
    modulo,
    activeTab,
    data,
    data?.dias_1_atraso,
    dataPrejudicial?.items,
    dataD2Antes?.items,
  ])

  const [sortCol, setSortCol] = useState<NotificacionesCuotasSortCol | null>(
    null
  )

  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const [paginaPorTab, setPaginaPorTab] = useState<
    Partial<Record<TabId, number>>
  >({})

  const [filtroCedula, setFiltroCedula] = useState('')

  const [filtroDiferenciaAbonoGeneral, setFiltroDiferenciaAbonoGeneral] =
    useState<FiltroDiferenciaAbonoGeneral>('todas')

  useEffect(() => {
    setFiltroCedula('')
  }, [activeTab, modulo, fechaCaracasApi])

  useEffect(() => {
    setFiltroDiferenciaAbonoGeneral('todas')
  }, [activeTab, modulo, fechaCaracasApi, filtroCedula])

  useEffect(() => {
    setSortCol(null)

    setSortDir('asc')
  }, [activeTab, modulo])

  const sortedList = useMemo(() => {
    if (!sortCol || list.length === 0) return list

    const cmp = (a: ClienteRetrasadoItem, b: ClienteRetrasadoItem): number => {
      switch (sortCol) {
        case 'numero_cuota': {
          const na = a.numero_cuota
          const nb = b.numero_cuota
          const va =
            na == null || Number.isNaN(Number(na))
              ? Number.POSITIVE_INFINITY
              : Number(na)
          const vb =
            nb == null || Number.isNaN(Number(nb))
              ? Number.POSITIVE_INFINITY
              : Number(nb)
          return va - vb
        }

        case 'fecha_vencimiento':
          return (
            fechaVencSortValue(a.fecha_vencimiento) -
            fechaVencSortValue(b.fecha_vencimiento)
          )

        case 'cuotas_atrasadas':
          return cuotasAtrasadasSortValue(a) - cuotasAtrasadasSortValue(b)

        case 'total_pendiente': {
          const va = numericTotalPendienteSort(a)
          const vb = numericTotalPendienteSort(b)
          const na = va == null ? Number.POSITIVE_INFINITY : va
          const nb = vb == null ? Number.POSITIVE_INFINITY : vb
          return na - nb
        }

        default:
          return 0
      }
    }

    const out = [...list]

    out.sort((a, b) => {
      const p = sortDir === 'asc' ? cmp(a, b) : -cmp(a, b)

      if (p !== 0) return p

      return String(a.cliente_id).localeCompare(String(b.cliente_id))
    })

    return out
  }, [list, sortCol, sortDir])

  const mostrarTablaCuotas = list.some(
    row =>
      row.numero_cuota != null ||
      row.fecha_vencimiento != null ||
      row.dias_atraso != null ||
      row.cuotas_atrasadas != null ||
      row.total_cuotas_atrasadas != null ||
      row.monto != null ||
      row.total_pendiente_pagar != null
  )

  const listaBasePaginacion = mostrarTablaCuotas ? sortedList : list

  const listaTrasFiltroCedula = useMemo(() => {
    const q = filtroCedula.trim()
    if (!q) return listaBasePaginacion
    return listaBasePaginacion.filter(row =>
      filaCoincideFiltroCedulaNotif(row, q)
    )
  }, [listaBasePaginacion, filtroCedula])

  const generalCompararTargets = useMemo(() => {
    if (modulo !== 'general' || activeTab !== 'general_todos') return []
    const seen = new Set<string>()
    const out: Array<{
      cedula: string
      prestamoId: number
      rowKey: string
    }> = []
    for (const row of listaTrasFiltroCedula) {
      const ced = String(row.cedula ?? '').trim()
      const pid = row.prestamo_id
      if (!ced || pid == null) continue
      const k = `${ced}|${pid}`
      if (seen.has(k)) continue
      seen.add(k)
      out.push({ cedula: ced, prestamoId: pid, rowKey: k })
    }
    return out
  }, [modulo, activeTab, listaTrasFiltroCedula])

  const generalCompararTargetsKey = useMemo(
    () => [...generalCompararTargets.map(t => t.rowKey)].sort().join('\n'),
    [generalCompararTargets]
  )

  const generalCompararRowKeySet = useMemo(
    () => new Set(generalCompararTargets.map(t => t.rowKey)),
    [generalCompararTargets]
  )

  const [compararAbonoGeneralMap, setCompararAbonoGeneralMap] = useState<
    Map<string, CompararAbonosDriveCuotasResponse>
  >(() => new Map())

  const [compararAbonoGeneralCargando, setCompararAbonoGeneralCargando] =
    useState(false)

  const [compararAbonoGeneralTick, setCompararAbonoGeneralTick] = useState(0)

  useEffect(() => {
    if (modulo !== 'general' || activeTab !== 'general_todos') {
      setCompararAbonoGeneralMap(new Map())
      setCompararAbonoGeneralCargando(false)
      return undefined
    }
    const targetsSnapshot = generalCompararTargets
    if (targetsSnapshot.length === 0) {
      setCompararAbonoGeneralMap(new Map())
      setCompararAbonoGeneralCargando(false)
      return undefined
    }
    let cancelado = false
    setCompararAbonoGeneralCargando(true)
    void (async () => {
      try {
        const entradas = await compararAbonosGeneralEnLotes(
          targetsSnapshot,
          COMPARAR_ABONOS_GENERAL_CONCURRENCIA,
          () => cancelado
        )
        if (cancelado) return
        const m = new Map<string, CompararAbonosDriveCuotasResponse>()
        for (const [k, v] of entradas) {
          if (v) m.set(k, v)
        }
        setCompararAbonoGeneralMap(m)
      } finally {
        if (!cancelado) setCompararAbonoGeneralCargando(false)
      }
    })()
    return () => {
      cancelado = true
    }
  }, [modulo, activeTab, generalCompararTargetsKey, compararAbonoGeneralTick])

  const filtrosAbonoGeneralPendientes =
    modulo === 'general' &&
    filtroDiferenciaAbonoGeneral !== 'todas' &&
    compararAbonoGeneralCargando

  const listaFiltradaCedula = useMemo(() => {
    if (modulo !== 'general' || filtroDiferenciaAbonoGeneral === 'todas') {
      return listaTrasFiltroCedula
    }
    if (filtrosAbonoGeneralPendientes) {
      return listaTrasFiltroCedula
    }
    return listaTrasFiltroCedula.filter(row => {
      const ced = String(row.cedula ?? '').trim()
      const pid = row.prestamo_id
      if (!ced || pid == null) return false
      const d = compararAbonoGeneralMap.get(`${ced}|${pid}`)
      if (!d) return false
      return filaCumpleFiltroDiferenciaAbonoGeneral(
        filtroDiferenciaAbonoGeneral,
        d
      )
    })
  }, [
    listaTrasFiltroCedula,
    modulo,
    filtroDiferenciaAbonoGeneral,
    filtrosAbonoGeneralPendientes,
    compararAbonoGeneralMap,
  ])

  const totalFilasListado = listaFiltradaCedula.length

  const totalPaginasListado = Math.max(
    1,
    Math.ceil(totalFilasListado / NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA)
  )

  useEffect(() => {
    setPaginaPorTab({})
  }, [fechaCaracasApi, modulo])

  useEffect(() => {
    setPaginaPorTab(prev => {
      const raw = prev[activeTab] ?? 1
      const clamped = Math.min(Math.max(1, raw), totalPaginasListado)
      if (clamped === raw) return prev
      return { ...prev, [activeTab]: clamped }
    })
  }, [activeTab, totalPaginasListado])

  const paginaListaActual = Math.min(
    paginaPorTab[activeTab] ?? 1,
    totalPaginasListado
  )

  const indiceInicioPagina =
    (paginaListaActual - 1) * NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA

  const filasPagina = useMemo(() => {
    return listaFiltradaCedula.slice(
      indiceInicioPagina,
      indiceInicioPagina + NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA
    )
  }, [listaFiltradaCedula, indiceInicioPagina])

  const irPaginaLista = (p: number) => {
    const next = Math.min(Math.max(1, p), totalPaginasListado)
    setPaginaPorTab(prev => ({ ...prev, [activeTab]: next }))
  }

  const numerosPaginaVisibles = useMemo(() => {
    const total = totalPaginasListado
    const current = paginaListaActual
    const max = NOTIFICACIONES_VENTANA_NUMEROS_PAGINA
    if (total <= max) {
      return Array.from({ length: total }, (_, i) => i + 1)
    }
    const half = Math.floor(max / 2)
    const start = Math.max(1, Math.min(current - half, total - max + 1))
    return Array.from({ length: max }, (_, i) => start + i)
  }, [totalPaginasListado, paginaListaActual])

  const aplicarOrdenAsc = (c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('asc')
  }

  const aplicarOrdenDesc = (c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('desc')
  }

  const isLoadingLista =
    modulo === 'general'
      ? isPending || isPendingPrej || isPendingD2
      : modulo === 'a1dia'
        ? isPending
        : modulo === 'a3cuotas'
          ? isPendingPrej
          : isPendingD2

  /**
   * No deshabilitar «Enviar notificaciones (manual)» durante refetch en segundo plano
   * (staleTime 0 + refocus): solo hasta la primera respuesta de la lista.
   * Si el GET de la lista falló (isError), no bloquear envío: el servidor puede armar la lista al enviar.
   */
  const esperandoPrimeraCargaLista =
    (modulo === 'general' &&
      ((isPending && !isFetched && !isError) ||
        (isPendingPrej && !isFetchedPrej && !isErrorPrej) ||
        (isPendingD2 && !isFetchedD2 && !isErrorD2))) ||
    (modulo === 'a1dia' && isPending && !isFetched && !isError) ||
    (modulo === 'a3cuotas' &&
      isPendingPrej &&
      !isFetchedPrej &&
      !isErrorPrej) ||
    (modulo === 'd2antes' && isPendingD2 && !isFetchedD2 && !isErrorD2)

  const isErrorLista =
    modulo === 'general'
      ? isError && isErrorPrej && isErrorD2
      : modulo === 'a1dia'
        ? isError
        : modulo === 'a3cuotas'
          ? isErrorPrej
          : isErrorD2

  const errorLista =
    modulo === 'general'
      ? error ?? errorPrej ?? errorD2
      : modulo === 'a1dia'
        ? error
        : modulo === 'a3cuotas'
          ? errorPrej
          : errorD2

  const refetchLista =
    modulo === 'general'
      ? () => {
          void Promise.all([refetch(), refetchPrej(), refetchD2()])
        }
      : modulo === 'a1dia'
        ? refetch
        : modulo === 'a3cuotas'
          ? refetchPrej
          : refetchD2

  const isFetchingLista =
    modulo === 'general'
      ? isFetching || isFetchingPrej || isFetchingD2
      : modulo === 'a1dia'
        ? isFetching
        : modulo === 'a3cuotas'
          ? isFetchingPrej
          : isFetchingD2

  const isFetchedLista =
    modulo === 'general'
      ? (isFetched || isError) &&
        (isFetchedPrej || isErrorPrej) &&
        (isFetchedD2 || isErrorD2)
      : modulo === 'a1dia'
        ? isFetched
        : modulo === 'a3cuotas'
          ? isFetchedPrej
          : isFetchedD2

  const listaCargadaSinFilas =
    !isErrorLista && !isLoadingLista && isFetchedLista && list.length === 0

  const statTabKey = tipoParaKpiYRebotados(activeTab)

  const controlFechaReferenciaCaracas = (
    <div className="flex max-w-full flex-col gap-1 rounded-md border border-gray-200 bg-gray-50/90 px-2 py-1.5 sm:flex-row sm:items-center sm:gap-2">
      <label
        htmlFor="fc-notificaciones-caracas"
        className="whitespace-nowrap text-xs font-medium text-gray-600"
      >
        Fecha referencia (Caracas)
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          id="fc-notificaciones-caracas"
          type="date"
          max={fechaHoyCaracasISO()}
          value={fechaReferenciaCaracas}
          onChange={e => setFechaCaracasYUrl(e.target.value)}
          className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 shadow-sm"
          title={
            modulo === 'general'
              ? 'Listados como si fuera este día en America/Caracas. Vacío = hoy.'
              : 'Listados y envíos manuales como si fuera este día en America/Caracas (p. ej. si no envió a tiempo). Vacío = hoy.'
          }
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8"
          onClick={() => setFechaCaracasYUrl('')}
        >
          Hoy
        </Button>
      </div>
    </div>
  )

  if (activeTab === 'configuracion' && modulo !== 'general') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description="Clientes retrasados por fecha de vencimiento y mora"
          actions={
            <div className="flex flex-wrap items-center gap-2">
              {controlFechaReferenciaCaracas}

              <Button
                variant="outline"
                onClick={() => void handleRefresh()}
                disabled={actualizandoListas}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-red-400 text-red-800 hover:bg-red-50"
                disabled={!hayOperacionListaEnCurso}
                onClick={cancelarOperacionListaEmergencia}
                title="Emergencia: corta actualización de listas en curso. No confundir con confirmar envío de correos (eso es en la pestaña de listado)."
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>
          }
        />

        <div className="border-b border-gray-200">
          <nav className="flex flex-wrap gap-2">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTabAndUrl(tab.id)}
                className={`flex items-center gap-2 rounded-t px-3 py-2 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border border-b-0 border-gray-200 bg-white text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="h-4 w-4" />

                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Cada submenú: una fila de envíos / adjuntos por tipo en BD. */}
        <ConfiguracionNotificaciones
          alcance={
            modulo === 'a1dia'
              ? 'solo_pago_1_dia'
              : modulo === 'd2antes'
                ? 'solo_pago_2_dias_antes_pendiente'
                : 'solo_prejudicial'
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description={
            modulo === 'general'
              ? 'Solo consulta: listas unificadas (día siguiente al vencimiento, atraso 5 cuotas, 2 días antes) con columna de caso. Sin envío de correos ni ajustes de comunicación desde esta pantalla.'
              : modulo === 'a3cuotas'
                ? 'Clientes con al menos cinco cuotas en estado VENCIDO o MORA (morosidad según reglas del sistema en BD). Al regularizar, pueden dejar de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
                : modulo === 'd2antes'
                  ? 'Solo cuotas con columna estado PENDIENTE y fecha de vencimiento dentro de 2 días (hoy + 2, zona Caracas). Al pagar o cambiar estado, dejan de listarse. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos.'
                  : 'Cuotas pendientes en tiempo real: al registrar pagos que cubren la cuota, el cliente deja de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
          }
          actions={
            <div className="flex flex-wrap items-center gap-2">
              {controlFechaReferenciaCaracas}

              <Button
                variant="outline"
                onClick={() => void handleRefresh()}
                disabled={actualizandoListas}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-red-400 text-red-800 hover:bg-red-50"
                disabled={!hayOperacionListaEnCurso}
                onClick={cancelarOperacionListaEmergencia}
                title="Emergencia: corta petición en curso. No es la confirmación de envío: en el modal use «Enviar correos» o «No enviar»."
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>
          }
        />
      </motion.div>

      {modulo !== 'general' ? (
        <div className="border-b border-gray-200">
          <nav className="flex flex-wrap gap-1">
            {TABS.filter(t => t.id !== 'configuracion').map(tab => {
              const count =
                tab.id === 'general_todos'
                  ? (data?.dias_1_atraso?.length ?? 0) +
                    (dataPrejudicial?.items?.length ?? 0) +
                    (dataD2Antes?.items?.length ?? 0)
                  : tab.id === 'prejudicial'
                    ? (dataPrejudicial?.items?.length ?? 0)
                    : tab.id === 'd2antes'
                      ? (dataD2Antes?.items?.length ?? 0)
                      : (data?.dias_1_atraso?.length ?? 0)

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTabAndUrl(tab.id)}
                  className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <tab.icon className="h-4 w-4" />

                  {tab.label}

                  {count > 0 && (
                    <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700">
                      {count}
                    </span>
                  )}
                </button>
              )
            })}

            <button
              onClick={() => setActiveTabAndUrl('configuracion')}
              className="flex items-center gap-2 border-b-2 border-transparent px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              <Settings className="h-4 w-4" />
              Configuración
            </button>
          </nav>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Total de filas en las tres listas:{' '}
          <span className="font-semibold tabular-nums text-foreground">
            {(data?.dias_1_atraso?.length ?? 0) +
              (dataPrejudicial?.items?.length ?? 0) +
              (dataD2Antes?.items?.length ?? 0)}
          </span>
        </p>
      )}

      <motion.div
        key={activeTab}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {(() => {
                const TabIcon = TABS.find(t => t.id === activeTab)?.icon

                return TabIcon ? <TabIcon className="h-5 w-5" /> : null
              })()}
              {modulo === 'general'
                ? 'General — todos los casos de mora (listas combinadas)'
                : modulo === 'a3cuotas'
                  ? 'Cinco o más cuotas VENCIDO o MORA (prejudicial)'
                  : modulo === 'd2antes'
                    ? '2 días antes - PENDIENTE, vence en 2 días'
                    : 'Día siguiente al vencimiento (1 día de atraso calendario)'}
            </CardTitle>

            <CardDescription>
              {fechaCaracasApi ? (
                <span className="mb-2 block font-medium text-amber-800">
                  Referencia de listado y envío: {fechaCaracasApi}{' '}
                  (America/Caracas). Use «Hoy» arriba para volver al día actual.
                </span>
              ) : null}
              {modulo === 'general'
                ? 'Se concatenan las mismas filas que en los submenús «Día siguiente al vencimiento», «Atraso 5 cuotas» y «2 días antes». La columna «Caso» indica el criterio. Un mismo cliente puede aparecer más de una vez si cumple varios criterios.'
                : modulo === 'a3cuotas'
                  ? 'Una fila por cliente con al menos cinco cuotas en estado VENCIDO o MORA (columna cuotas.estado). La cuota y fecha mostradas son referencia; «Cuotas atrasadas» es el número de esas cuotas que cumplen el criterio.'
                  : modulo === 'd2antes'
                    ? 'Solo filas con cuotas.estado = PENDIENTE y fecha_vencimiento = hoy + 2 (calendario Caracas), sin fecha_pago y con saldo pendiente. Se omiten préstamos con «Cuotas atrasadas» = 0 (al corriente en mora). «Cuotas atrasadas» sigue la misma regla que el estado de cuenta para el préstamo.'
                    : 'Cuotas cuya fecha de vencimiento fue ayer (hoy es el primer día después del vencimiento). La columna Cuotas atrasadas cuenta las cuotas en mora del préstamo con la misma regla que el estado de cuenta (Vencido, Mora, etc.).'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={
                  actualizandoListas ||
                  enviandoPrejudicial ||
                  enviandoD2Antes ||
                  enviandoPago1Dia
                }
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>

              {modulo === 'a1dia' && (
                <Button
                  type="button"
                  size="sm"
                  onClick={solicitarConfirmacionEnvioPago1Dia}
                  disabled={enviandoPago1Dia || esperandoPrimeraCargaLista}
                  title={
                    esperandoPrimeraCargaLista
                      ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                      : undefined
                  }
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Mail
                    className={`mr-2 h-4 w-4 ${enviandoPago1Dia ? 'animate-pulse' : ''}`}
                  />
                  {enviandoPago1Dia
                    ? 'Enviando...'
                    : 'Enviar notificaciones (manual)'}
                </Button>
              )}

              {modulo === 'a3cuotas' && (
                <Button
                  type="button"
                  size="sm"
                  onClick={solicitarConfirmacionEnvioPrejudicial}
                  disabled={enviandoPrejudicial || esperandoPrimeraCargaLista}
                  title={
                    esperandoPrimeraCargaLista
                      ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                      : undefined
                  }
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Mail
                    className={`mr-2 h-4 w-4 ${enviandoPrejudicial ? 'animate-pulse' : ''}`}
                  />
                  {enviandoPrejudicial
                    ? 'Enviando...'
                    : 'Enviar notificaciones (manual)'}
                </Button>
              )}

              {modulo === 'd2antes' && (
                <Button
                  type="button"
                  size="sm"
                  onClick={solicitarConfirmacionEnvioD2Antes}
                  disabled={enviandoD2Antes || esperandoPrimeraCargaLista}
                  title={
                    esperandoPrimeraCargaLista
                      ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                      : undefined
                  }
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Mail
                    className={`mr-2 h-4 w-4 ${enviandoD2Antes ? 'animate-pulse' : ''}`}
                  />
                  {enviandoD2Antes
                    ? 'Enviando...'
                    : 'Enviar notificaciones (manual)'}
                </Button>
              )}

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-red-400 text-red-800 hover:bg-red-50"
                disabled={!hayOperacionListaEnCurso}
                onClick={cancelarOperacionListaEmergencia}
                title="Emergencia: corta actualización o envío ya en curso. No sustituye al modal de confirmación: use «Enviar correos» en la ventana que se abre al pulsar enviar."
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>

            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="flex min-w-[12rem] max-w-md flex-1 flex-col gap-1">
                <label
                  htmlFor="filtro-cedula-notificaciones"
                  className="text-xs font-medium text-gray-600"
                >
                  Filtrar por cédula
                </label>
                <Input
                  id="filtro-cedula-notificaciones"
                  type="search"
                  placeholder="Contiene (ej. 17579297 o V-17579297)"
                  value={filtroCedula}
                  onChange={e => setFiltroCedula(e.target.value)}
                  autoComplete="off"
                  className="h-9 max-w-md bg-white"
                  disabled={isLoadingLista}
                />
              </div>
              {filtroCedula.trim() ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-9 shrink-0"
                  onClick={() => setFiltroCedula('')}
                >
                  Limpiar filtro
                </Button>
              ) : null}
              {modulo === 'general' ? (
                <div className="flex min-w-[14rem] max-w-md flex-col gap-1">
                  <label
                    htmlFor="filtro-dif-abono-general"
                    className="text-xs font-medium text-gray-600"
                  >
                    Diferencia Abono (hoja − cuotas)
                  </label>
                  <select
                    id="filtro-dif-abono-general"
                    className="h-9 rounded-md border border-input bg-white px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                    value={filtroDiferenciaAbonoGeneral}
                    onChange={e =>
                      setFiltroDiferenciaAbonoGeneral(
                        e.target.value as FiltroDiferenciaAbonoGeneral
                      )
                    }
                    disabled={isLoadingLista}
                    title="Misma regla que el modal de la balanza: «0» = coincide con tolerancia; «Drive &gt; sistema» = solo ahí se permite aplicar desde el modal."
                  >
                    <option value="todas">Todas</option>
                    <option value="cero">
                      0 — sin diferencia (tolerancia, como en el modal)
                    </option>
                    <option value="drive_mayor">
                      Drive &gt; sistema (indicador Sí; solo ahí se permite aplicar)
                    </option>
                  </select>
                </div>
              ) : null}
              {filtroCedula.trim() &&
              list.length > 0 &&
              !(
                modulo === 'general' &&
                filtroDiferenciaAbonoGeneral !== 'todas'
              ) ? (
                <p className="text-xs text-muted-foreground sm:ml-auto">
                  Mostrando{' '}
                  <span className="font-semibold tabular-nums text-foreground">
                    {listaFiltradaCedula.length}
                  </span>{' '}
                  de <span className="tabular-nums">{list.length}</span> filas
                </p>
              ) : null}
              {!filtroCedula.trim() &&
              modulo === 'general' &&
              filtroDiferenciaAbonoGeneral !== 'todas' &&
              list.length > 0 ? (
                <p className="text-xs text-muted-foreground sm:ml-auto">
                  Mostrando{' '}
                  <span className="font-semibold tabular-nums text-foreground">
                    {listaFiltradaCedula.length}
                  </span>{' '}
                  de{' '}
                  <span className="tabular-nums">
                    {listaTrasFiltroCedula.length}
                  </span>{' '}
                  filas (tras filtro de diferencia)
                </p>
              ) : null}
              {filtroCedula.trim() &&
              modulo === 'general' &&
              filtroDiferenciaAbonoGeneral !== 'todas' &&
              list.length > 0 ? (
                <p className="text-xs text-muted-foreground sm:ml-auto">
                  Tras cédula y diferencia:{' '}
                  <span className="font-semibold tabular-nums text-foreground">
                    {listaFiltradaCedula.length}
                  </span>{' '}
                  de{' '}
                  <span className="tabular-nums">
                    {listaTrasFiltroCedula.length}
                  </span>
                </p>
              ) : null}
            </div>

            {/* KPIs por pestaña: correos enviados y rebotados */}

            {(activeTab as TabId) !== 'configuracion' &&
              modulo !== 'general' &&
              estadisticasPorTab && (
              <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-2">
                <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
                  <Mail className="h-8 w-8 text-green-600" />

                  <div>
                    <p className="text-2xl font-bold text-green-800">
                      {statTabKey
                        ? (estadisticasPorTab[statTabKey]?.enviados ?? 0)
                        : 0}
                    </p>

                    <p className="text-xs font-medium text-green-700">
                      Correos enviados
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                  <AlertTriangle className="h-8 w-8 text-red-600" />

                  <div>
                    <p className="text-2xl font-bold text-red-800">
                      {statTabKey
                        ? (estadisticasPorTab[statTabKey]?.rebotados ?? 0)
                        : 0}
                    </p>

                    <p className="text-xs font-medium text-red-700">
                      Correos rebotados
                    </p>
                  </div>
                </div>
              </div>
            )}

            {isErrorLista && (
              <div className="mb-4 flex items-center justify-between gap-2 rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
                <span>
                  Error al cargar.
                  {errorLista?.message
                    ? ` ${String(errorLista.message)}`
                    : ''}{' '}
                  Comprueba que exista la tabla{' '}
                  <code className="bg-gray-100 px-1">cuotas</code>.
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchLista()}
                >
                  Reintentar
                </Button>
              </div>
            )}

            {modulo === 'general' &&
            !isErrorLista &&
            (isError || isErrorPrej || isErrorD2) ? (
              <div className="mb-4 rounded border border-amber-200 bg-amber-50/90 px-3 py-2 text-xs text-amber-950">
                Parte de las listas no respondió (día siguiente, prejudicial o 2
                días antes). Se muestran las que sí cargaron; use Reintentar o
                Actualización manual.
              </div>
            ) : null}

            {isLoadingLista && (
              <div className="mb-4 flex items-center gap-2 rounded border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700">
                <RefreshCw
                  className={`h-4 w-4 ${isFetchingLista ? 'animate-spin' : ''}`}
                />

                <span>Cargando datos...</span>
              </div>
            )}

            <Fragment>
              {mostrarTablaCuotas ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th
                          className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold leading-tight"
                          title="Identificador del préstamo (crédito) en el sistema"
                        >
                          Número de
                          <br />
                          crédito
                        </th>

                        {modulo !== 'general' ? (
                          <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                            Nombre
                          </th>
                        ) : null}

                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          Cédula
                        </th>

                        {modulo === 'general' ? (
                          <th className="min-w-[10rem] whitespace-normal px-3 py-2 text-left text-xs font-semibold leading-tight">
                            Caso
                          </th>
                        ) : null}

                        {modulo === 'general' ? (
                          <th className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight">
                            Diferencia Abono
                          </th>
                        ) : null}

                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Nº cuota</span>

                            <SortArrowsCuotas
                              column="numero_cuota"
                              labelAsc="Orden ascendente: Nº cuota"
                              labelDesc="Orden descendente: Nº cuota"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>

                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Fecha venc.</span>

                            <SortArrowsCuotas
                              column="fecha_vencimiento"
                              labelAsc="Orden ascendente: fecha de vencimiento"
                              labelDesc="Orden descendente: fecha de vencimiento"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>

                        <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                          <div className="inline-flex w-full items-center justify-end gap-1">
                            <span>Cuotas atrasadas</span>

                            <SortArrowsCuotas
                              column="cuotas_atrasadas"
                              labelAsc="Orden ascendente: cuotas atrasadas"
                              labelDesc="Orden descendente: cuotas atrasadas"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>

                        <th className="max-w-[12rem] whitespace-normal px-3 py-2 text-right font-semibold leading-tight">
                          <div className="inline-flex items-start justify-end gap-1">
                            <span>
                              TOTAL PENDIENTE
                              <br />A PAGAR
                            </span>

                            <SortArrowsCuotas
                              column="total_pendiente"
                              labelAsc="Orden ascendente: total pendiente"
                              labelDesc="Orden descendente: total pendiente"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>

                        <th
                          className="min-w-[5.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                          scope="col"
                          title="Revisión manual (triángulo) y comparar ABONOS hoja vs total pagado en cuotas (icono azul)."
                        >
                          Revisión
                          <br />
                          manual
                        </th>

                        <th className="w-14 whitespace-nowrap px-2 py-2 text-center font-semibold">
                          <span title="Descargar PDF de estado de cuenta">
                            Estado de cuenta
                          </span>
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {listaFiltradaCedula.length === 0 ? (
                        <tr>
                          <td
                            colSpan={modulo === 'general' ? 10 : 9}
                            className="py-8 text-center text-gray-500"
                          >
                            <span className="block font-medium text-gray-600">
                              {listaCargadaSinFilas
                                ? 'Ningún registro en este criterio.'
                                : filtroCedula.trim()
                                  ? 'Ninguna fila coincide con la cédula indicada.'
                                  : modulo === 'general' &&
                                      filtroDiferenciaAbonoGeneral !== 'todas' &&
                                      listaTrasFiltroCedula.length > 0
                                    ? 'Ninguna fila cumple el filtro de diferencia de abono.'
                                    : 'Ningún registro en este criterio.'}
                            </span>
                            {listaCargadaSinFilas ? (
                              <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                                {modulo === 'general'
                                  ? 'Listas ya cargadas: no hay filas en ninguno de los tres criterios (día siguiente, prejudicial, 2 días antes) para la fecha de referencia.'
                                  : modulo === 'a3cuotas'
                                    ? 'Lista ya cargada: se requieren 5+ cuotas en estado VENCIDO o MORA en BD. Si hay mora pero no aparece nadie, sincronice estados de cuotas (auditoría / job) para alinear la columna estado.'
                                    : modulo === 'd2antes'
                                      ? 'Lista ya cargada: solo cuotas en estado PENDIENTE con vencimiento exactamente dentro de 2 días (Caracas). Si la columna estado no es PENDIENTE o la fecha no coincide, no aparecerá.'
                                      : 'Lista ya cargada: solo entran cuotas con fecha de vencimiento igual a ayer (Caracas). Si no hay ninguna, la tabla quedará vacía aunque exista mora en otros días.'}
                              </span>
                            ) : filtroCedula.trim() ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Ajuste el texto del filtro o use «Limpiar filtro». La
                                búsqueda ignora puntos y guiones y compara por
                                subcadena de dígitos.
                              </span>
                            ) : modulo === 'general' &&
                              filtroDiferenciaAbonoGeneral !== 'todas' &&
                              listaTrasFiltroCedula.length > 0 ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Elija «Todas» o otro criterio. «0» usa la misma
                                coincidencia por tolerancia que el modal; «Drive
                                &gt; sistema» solo filas con indicador Sí (ABONOS
                                hoja mayor que total en cuotas).
                              </span>
                            ) : null}
                          </td>
                        </tr>
                      ) : (
                        filasPagina.map((row, idx) => (
                          <tr
                            key={`${row.notificacion_caso ?? 'sin-caso'}-${row.cliente_id}-${row.prestamo_id ?? 'np'}-${row.numero_cuota ?? 'nc'}-${indiceInicioPagina + idx}`}
                            className="border-b hover:bg-gray-50"
                          >
                            <td className="px-3 py-2 font-medium tabular-nums">
                              {textoNumeroCreditoNotif(row)}
                            </td>

                            {modulo !== 'general' ? (
                              <td className="px-3 py-2 font-medium">
                                {row.nombre}
                              </td>
                            ) : null}

                            <td className="px-3 py-2">{row.cedula}</td>

                            {modulo === 'general' ? (
                              <td className="max-w-[14rem] px-3 py-2 text-xs leading-snug text-slate-800">
                                {row.notificacion_caso ?? '—'}
                              </td>
                            ) : null}

                            {modulo === 'general' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                {(() => {
                                  const cedR = String(row.cedula ?? '').trim()
                                  const pidR = row.prestamo_id
                                  const rk =
                                    cedR && pidR != null
                                      ? `${cedR}|${pidR}`
                                      : ''
                                  return (
                                    <DiferenciaAbonoGeneralCell
                                      row={row}
                                      data={
                                        rk
                                          ? compararAbonoGeneralMap.get(rk)
                                          : undefined
                                      }
                                      isLoading={Boolean(
                                        rk &&
                                          compararAbonoGeneralCargando &&
                                          generalCompararRowKeySet.has(rk)
                                      )}
                                      isError={Boolean(
                                        rk &&
                                          generalCompararRowKeySet.has(rk) &&
                                          !compararAbonoGeneralCargando &&
                                          !compararAbonoGeneralMap.has(rk)
                                      )}
                                    />
                                  )
                                })()}
                              </td>
                            ) : null}

                            <td className="px-3 py-2">
                              {row.numero_cuota ?? '-'}
                            </td>

                            <td className="px-3 py-2">
                              {row.fecha_vencimiento ?? '-'}
                            </td>

                            <td className="px-3 py-2 text-right font-medium text-red-600">
                              {row.cuotas_atrasadas ??
                                row.total_cuotas_atrasadas ??
                                '-'}
                            </td>

                            <td className="px-3 py-2 text-right">
                              {textoTotalPendientePagar(row)}
                            </td>

                            <td className="px-1 py-2 text-center align-middle">
                              <div className="flex flex-wrap items-center justify-center gap-1">
                                <RevisionManualNotifCell row={row} />
                                <CompararAbonosDriveCuotasCell row={row} />
                              </div>
                            </td>

                            <td className="px-2 py-2 text-center align-middle">
                              {estadoCuentaPdfCell(row.prestamo_id)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th
                          className="px-3 py-2 text-left text-xs font-semibold leading-tight"
                          title="Identificador del préstamo (crédito) en el sistema"
                        >
                          Número de
                          <br />
                          crédito
                        </th>

                        {modulo !== 'general' ? (
                          <th className="px-3 py-2 text-left font-semibold">
                            Nombre
                          </th>
                        ) : null}

                        <th className="px-3 py-2 text-left font-semibold">
                          Cédula
                        </th>

                        {modulo === 'general' ? (
                          <th className="min-w-[10rem] px-3 py-2 text-left text-xs font-semibold leading-tight">
                            Caso
                          </th>
                        ) : null}

                        {modulo === 'general' ? (
                          <th className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight">
                            Diferencia Abono
                          </th>
                        ) : null}

                        <th
                          className="min-w-[5.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                          scope="col"
                          title="Revisión manual (triángulo) y comparar ABONOS hoja vs total pagado en cuotas (icono azul)."
                        >
                          Revisión
                          <br />
                          manual
                        </th>

                        <th className="w-14 px-2 py-2 text-center font-semibold">
                          <span title="Descargar PDF de estado de cuenta">
                            Estado de cuenta
                          </span>
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {listaFiltradaCedula.length === 0 ? (
                        <tr>
                          <td
                            colSpan={modulo === 'general' ? 6 : 5}
                            className="py-8 text-center text-gray-500"
                          >
                            <span className="block font-medium text-gray-600">
                              {listaCargadaSinFilas
                                ? 'Ningún cliente en este criterio.'
                                : filtroCedula.trim()
                                  ? 'Ninguna fila coincide con la cédula indicada.'
                                  : modulo === 'general' &&
                                      filtroDiferenciaAbonoGeneral !== 'todas' &&
                                      listaTrasFiltroCedula.length > 0
                                    ? 'Ninguna fila cumple el filtro de diferencia de abono.'
                                    : 'Ningún cliente en este criterio.'}
                            </span>
                            {listaCargadaSinFilas ? (
                              <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                                {modulo === 'general'
                                  ? 'Listas ya cargadas: ningún criterio devolvió filas sin detalle de cuota para la fecha de referencia.'
                                  : modulo === 'a3cuotas'
                                    ? 'Lista ya cargada: 5+ cuotas VENCIDO o MORA. Sin filas con detalle de cuota: sincronice estados en BD o confirme que algún cliente cumple el umbral.'
                                    : modulo === 'd2antes'
                                      ? 'Lista ya cargada: sin cuotas PENDIENTE con vencimiento en 2 días. Revise estados en BD o el calendario de vencimientos.'
                                      : 'Lista ya cargada: sin cuotas con vencimiento ayer. Use Actualizar tras registrar pagos o revise el calendario de vencimientos.'}
                              </span>
                            ) : filtroCedula.trim() ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Ajuste el texto del filtro o use «Limpiar filtro». La
                                búsqueda ignora puntos y guiones y compara por
                                subcadena de dígitos.
                              </span>
                            ) : modulo === 'general' &&
                              filtroDiferenciaAbonoGeneral !== 'todas' &&
                              listaTrasFiltroCedula.length > 0 ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Elija «Todas» u otro criterio. «0» coincide con la
                                tolerancia del modal; «Drive &gt; sistema» solo
                                filas con indicador Sí.
                              </span>
                            ) : null}
                          </td>
                        </tr>
                      ) : (
                        filasPagina.map((row, idx) => (
                          <tr
                            key={`${row.notificacion_caso ?? 'sin-caso'}-${row.cliente_id}-${row.numero_cuota ?? idx}`}
                            className="border-b hover:bg-gray-50"
                          >
                            <td className="px-3 py-2 font-medium tabular-nums">
                              {textoNumeroCreditoNotif(row)}
                            </td>

                            {modulo !== 'general' ? (
                              <td className="px-3 py-2 font-medium">
                                {row.nombre}
                              </td>
                            ) : null}

                            <td className="px-3 py-2">{row.cedula}</td>

                            {modulo === 'general' ? (
                              <td className="max-w-[14rem] px-3 py-2 text-xs leading-snug text-slate-800">
                                {row.notificacion_caso ?? '—'}
                              </td>
                            ) : null}

                            {modulo === 'general' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                {(() => {
                                  const cedR = String(row.cedula ?? '').trim()
                                  const pidR = row.prestamo_id
                                  const rk =
                                    cedR && pidR != null
                                      ? `${cedR}|${pidR}`
                                      : ''
                                  return (
                                    <DiferenciaAbonoGeneralCell
                                      row={row}
                                      data={
                                        rk
                                          ? compararAbonoGeneralMap.get(rk)
                                          : undefined
                                      }
                                      isLoading={Boolean(
                                        rk &&
                                          compararAbonoGeneralCargando &&
                                          generalCompararRowKeySet.has(rk)
                                      )}
                                      isError={Boolean(
                                        rk &&
                                          generalCompararRowKeySet.has(rk) &&
                                          !compararAbonoGeneralCargando &&
                                          !compararAbonoGeneralMap.has(rk)
                                      )}
                                    />
                                  )
                                })()}
                              </td>
                            ) : null}

                            <td className="px-1 py-2 text-center align-middle">
                              <div className="flex flex-wrap items-center justify-center gap-1">
                                <RevisionManualNotifCell row={row} />
                                <CompararAbonosDriveCuotasCell row={row} />
                              </div>
                            </td>

                            <td className="px-2 py-2 text-center align-middle">
                              {estadoCuentaPdfCell(row.prestamo_id)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {totalFilasListado > 0 ? (
                <div className="mt-4 border-t border-gray-100 pt-4">
                  <nav
                    className="flex flex-col items-center gap-3"
                    aria-label="Paginación del listado"
                  >
                    <div className="flex flex-wrap items-center justify-center gap-1.5 sm:gap-2">
                      <button
                        type="button"
                        disabled={paginaListaActual <= 1}
                        onClick={() => irPaginaLista(paginaListaActual - 1)}
                        aria-label="Página anterior"
                        className="inline-flex h-9 items-center justify-center rounded-md border border-gray-200 bg-white px-3 text-sm font-medium text-gray-900 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-40"
                      >
                        <span aria-hidden className="mr-1.5 text-gray-600">
                          &larr;
                        </span>
                        Anterior
                      </button>

                      {numerosPaginaVisibles.map(n => {
                        const activa = n === paginaListaActual
                        return (
                          <button
                            key={n}
                            type="button"
                            onClick={() => irPaginaLista(n)}
                            aria-label={`Ir a página ${n}`}
                            aria-current={activa ? 'page' : undefined}
                            className={
                              activa
                                ? 'inline-flex h-9 min-w-[2.25rem] items-center justify-center rounded-md border border-blue-600 bg-blue-600 px-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1'
                                : 'inline-flex h-9 min-w-[2.25rem] items-center justify-center rounded-md border border-gray-200 bg-white px-3 text-sm font-medium text-gray-900 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1'
                            }
                          >
                            {n}
                          </button>
                        )
                      })}

                      <button
                        type="button"
                        disabled={paginaListaActual >= totalPaginasListado}
                        onClick={() => irPaginaLista(paginaListaActual + 1)}
                        aria-label="Página siguiente"
                        className="inline-flex h-9 items-center justify-center rounded-md border border-gray-200 bg-white px-3 text-sm font-medium text-gray-900 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-40"
                      >
                        Siguiente
                        <span aria-hidden className="ml-1.5 text-gray-600">
                          &rarr;
                        </span>
                      </button>
                    </div>

                    <p className="text-center text-xs text-gray-500 sm:text-sm">
                      Página {paginaListaActual} de {totalPaginasListado}
                    </p>

                    <p className="text-center text-[11px] leading-snug text-gray-400 sm:text-xs">
                      Casos {indiceInicioPagina + 1}-
                      {indiceInicioPagina + filasPagina.length} de{' '}
                      {totalFilasListado} (
                      {NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA} por página; cada
                      pestaña guarda su página)
                    </p>
                  </nav>
                </div>
              ) : null}
            </Fragment>
          </CardContent>
        </Card>
      </motion.div>

      <Dialog
        open={confirmEnvio != null}
        onOpenChange={open => {
          if (!open) setConfirmEnvio(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar envío de correos</DialogTitle>

            <div className="space-y-3 text-sm text-gray-600">
              {confirmEnvio?.kind === 'prejudicial' ? (
                <p>
                  {confirmEnvio.n === 0
                    ? 'No hay casos en la lista cargada. El servidor procesará la lista prejudicial actual (puede estar vacía).'
                    : `Envío al caso PREJUDICIAL (${confirmEnvio.n} casos en la lista completa; el servidor usa la misma regla, no solo la página actual). Respeta plantilla, CCO y modo prueba en Configuración.`}
                </p>
              ) : null}

              {confirmEnvio?.kind === 'd2antes' ? (
                <p>
                  {confirmEnvio.n === 0
                    ? 'No hay casos en la lista cargada. El servidor procesará PAGO_2_DIAS_ANTES_PENDIENTE (puede estar vacía).'
                    : `Envío para 2 días antes (${confirmEnvio.n} casos en la lista completa; mismo criterio en servidor, no solo la página actual). Respeta plantilla, CCO y modo prueba en Configuración.`}
                </p>
              ) : null}

              {confirmEnvio?.kind === 'pago1dia' ? (
                <p>
                  {confirmEnvio.n === 0
                    ? 'No hay casos en la lista cargada. El servidor procesará el criterio «día siguiente al vencimiento» (puede estar vacía).'
                    : `Envío para día siguiente al vencimiento (${confirmEnvio.n} casos en la lista completa; mismo criterio en servidor, no solo la página actual). Respeta plantilla, CCO y modo prueba en Configuración.`}
                </p>
              ) : null}

              <p className="font-medium text-gray-900">
                Pulse «Enviar correos» para llamar al servidor (aparecerá la
                petición POST en la red). «No enviar» cierra sin enviar.
              </p>
            </div>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmEnvio(null)}
            >
              No enviar
            </Button>

            <Button
              type="button"
              className="bg-blue-600 text-white hover:bg-blue-700"
              onClick={confirmarEnvioManualYEnviar}
            >
              Enviar correos
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Notificaciones
