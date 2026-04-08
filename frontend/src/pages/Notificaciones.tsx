import { useState, useEffect, useMemo, useRef, type ReactNode } from 'react'

import { Link, useSearchParams } from 'react-router-dom'

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
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  notificacionService,
  type ClienteRetrasadoItem,
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
} from '../constants/queryKeys'

import { NOTIFICACIONES_QUERY_KEYS } from '../queries/notificaciones'

import { isRequestCanceled } from '../utils/requestCanceled'

export type NotificacionesModulo = 'a1dia' | 'a3cuotas' | 'd2antes'

type TabId = 'dias_1_atraso' | 'prejudicial' | 'd2antes' | 'configuracion'

function tabsParaModulo(
  modulo: NotificacionesModulo
): { id: TabId; label: string; icon: typeof Clock }[] {
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

function tipoParaKpiYRebotados(tab: TabId): EstadisticaTabKey | null {
  switch (tab) {
    case 'dias_1_atraso':
      return 'dias_1_retraso'

    case 'prejudicial':
      return 'prejudicial'

    case 'd2antes':
      return 'd_2_antes_vencimiento'

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

  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab')

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
      (modulo === 'd2antes' && (t === 'dias_1_atraso' || t === 'prejudicial'))
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
      queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,

      queryFn: () => notificacionService.getClientesRetrasados(),

      // Siempre considerar obsoleto: al volver a la pestaña o tras invalidar por pagos, se refetch al instante.
      staleTime: 0,

      refetchOnWindowFocus: true,

      // Sin placeholderData: con v5, placeholder hace isPending=false y la tabla se ve vacía mientras carga (Render frío).
      /** En Configuración no se listan cuotas: evita GET pesado y errores 500 por carga/BD innecesaria. */

      enabled: modulo === 'a1dia' && activeTab !== 'configuracion',
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
    queryKey: NOTIFICACIONES_D2_ANTES_QUERY_KEY,

    queryFn: () => notificacionService.getCuotasPendiente2DiasAntes(),

    staleTime: 0,

    refetchOnWindowFocus: true,

    enabled: modulo === 'd2antes' && activeTab !== 'configuracion',
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
    queryKey: NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,

    queryFn: () => notificacionService.listarNotificacionesPrejudiciales(),

    staleTime: 0,

    refetchOnWindowFocus: true,

    enabled: modulo === 'a3cuotas' && activeTab !== 'configuracion',
  })

  const { data: estadisticasPorTab } = useQuery({
    queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,

    queryFn: () => notificacionService.getEstadisticasPorTab(),

    staleTime: 0,

    enabled: activeTab !== 'configuracion',

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

  const handleEnviarPrejudicialManual = async () => {
    if (modulo !== 'a3cuotas') return

    const n = dataPrejudicial?.items?.length ?? 0

    const confirmar =
      n === 0
        ? window.confirm(
            'No hay filas en el listado en pantalla. El servidor procesará su lista prejudicial actual (puede estar vacía). ¿Ejecutar envío manual?'
          )
        : window.confirm(
            `Envío manual a clientes del caso PREJUDICIAL (${n} filas visibles; el servidor usa la misma regla de lista). Respeta plantilla, CCO y modo prueba en Configuración. ¿Continuar?`
          )

    if (!confirmar) return

    const ac = beginOperacionListaAbortable()
    setEnviandoPrejudicial(true)

    try {
      const res = await notificacionService.enviarNotificacionesPrejudiciales({
        signal: ac.signal,
      })

      toast.success(
        `${res.mensaje} Enviados: ${res.enviados}. Sin email: ${res.sin_email}. Fallidos: ${res.fallidos}.`
      )

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
      if (isRequestCanceled(e)) {
        toast.info('Envío cancelado en el navegador.')
        return
      }

      toast.error(
        'No se pudo completar el envío. Revise PREJUDICIAL en Configuración, cuentas de correo y modo prueba.'
      )
    } finally {
      if (operacionListaAbortRef.current === ac) {
        operacionListaAbortRef.current = null
      }
      setEnviandoPrejudicial(false)
    }
  }

  const handleEnviarD2AntesManual = async () => {
    if (modulo !== 'd2antes') return

    const n = dataD2Antes?.items?.length ?? 0

    const confirmar =
      n === 0
        ? window.confirm(
            'No hay filas en el listado. El servidor procesará la lista actual del criterio PAGO_2_DIAS_ANTES_PENDIENTE (puede estar vacía). ¿Ejecutar envío manual?'
          )
        : window.confirm(
            `Envío manual para 2 días antes (${n} filas visibles; mismo criterio en servidor). Respeta plantilla, CCO y modo prueba en Configuración. ¿Continuar?`
          )

    if (!confirmar) return

    const ac = beginOperacionListaAbortable()
    setEnviandoD2Antes(true)

    try {
      const res = await notificacionService.enviarCasoManual(
        'PAGO_2_DIAS_ANTES_PENDIENTE',
        { signal: ac.signal }
      )

      toast.success(
        `${res.mensaje} Enviados: ${res.enviados}. Sin email: ${res.sin_email}. Fallidos: ${res.fallidos}.`
      )

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
      if (isRequestCanceled(e)) {
        toast.info('Envío cancelado en el navegador.')
        return
      }

      toast.error(
        'No se pudo completar el envío. Revise PAGO_2_DIAS_ANTES_PENDIENTE en Configuración, cuentas de correo y modo prueba.'
      )
    } finally {
      if (operacionListaAbortRef.current === ac) {
        operacionListaAbortRef.current = null
      }
      setEnviandoD2Antes(false)
    }
  }

  const handleEnviarPago1DiaManual = async () => {
    if (modulo !== 'a1dia') return

    const n = data?.dias_1_atraso?.length ?? 0

    const confirmar =
      n === 0
        ? window.confirm(
            'No hay filas en el listado. El servidor procesará la lista actual del criterio día siguiente al vencimiento (puede estar vacía). ¿Ejecutar envío manual?'
          )
        : window.confirm(
            `Envío manual para día siguiente al vencimiento (${n} filas visibles; mismo criterio en servidor). Respeta plantilla, CCO y modo prueba en Configuración. ¿Continuar?`
          )

    if (!confirmar) return

    const ac = beginOperacionListaAbortable()
    setEnviandoPago1Dia(true)

    try {
      const res = await notificacionService.enviarCasoManual(
        'PAGO_1_DIA_ATRASADO',
        { signal: ac.signal }
      )

      toast.success(
        `${res.mensaje} Enviados: ${res.enviados}. Sin email: ${res.sin_email}. Fallidos: ${res.fallidos}.`
      )

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
      if (isRequestCanceled(e)) {
        toast.info('Envío cancelado en el navegador.')
        return
      }

      toast.error(
        'No se pudo completar el envío. Revise PAGO_1_DIA_ATRASADO en Configuración, cuentas de correo y modo prueba.'
      )
    } finally {
      if (operacionListaAbortRef.current === ac) {
        operacionListaAbortRef.current = null
      }
      setEnviandoPago1Dia(false)
    }
  }

  const getListForTab = (): ClienteRetrasadoItem[] => {
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
  }

  const list = getListForTab()

  const [sortCol, setSortCol] = useState<NotificacionesCuotasSortCol | null>(
    null
  )

  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

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

  const aplicarOrdenAsc = (c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('asc')
  }

  const aplicarOrdenDesc = (c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('desc')
  }

  const isLoadingLista =
    modulo === 'a1dia'
      ? isPending
      : modulo === 'a3cuotas'
        ? isPendingPrej
        : isPendingD2

  /**
   * No deshabilitar «Enviar notificaciones (manual)» durante refetch en segundo plano
   * (staleTime 0 + refocus): solo hasta la primera respuesta de la lista.
   */
  const esperandoPrimeraCargaLista =
    (modulo === 'a1dia' && isPending && !isFetched) ||
    (modulo === 'a3cuotas' && isPendingPrej && !isFetchedPrej) ||
    (modulo === 'd2antes' && isPendingD2 && !isFetchedD2)

  const isErrorLista =
    modulo === 'a1dia'
      ? isError
      : modulo === 'a3cuotas'
        ? isErrorPrej
        : isErrorD2

  const errorLista =
    modulo === 'a1dia' ? error : modulo === 'a3cuotas' ? errorPrej : errorD2

  const refetchLista =
    modulo === 'a1dia'
      ? refetch
      : modulo === 'a3cuotas'
        ? refetchPrej
        : refetchD2

  const isFetchingLista =
    modulo === 'a1dia'
      ? isFetching
      : modulo === 'a3cuotas'
        ? isFetchingPrej
        : isFetchingD2

  const isFetchedLista =
    modulo === 'a1dia'
      ? isFetched
      : modulo === 'a3cuotas'
        ? isFetchedPrej
        : isFetchedD2

  const listaCargadaSinFilas =
    !isErrorLista && !isLoadingLista && isFetchedLista && list.length === 0

  const statTabKey = tipoParaKpiYRebotados(activeTab)

  const hasColumnasCuota = list.some(
    row =>
      row.numero_cuota != null ||
      row.fecha_vencimiento != null ||
      row.dias_atraso != null ||
      row.cuotas_atrasadas != null ||
      row.total_cuotas_atrasadas != null ||
      row.monto != null ||
      row.total_pendiente_pagar != null
  )

  const mostrarTablaCuotas = hasColumnasCuota

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description="Clientes retrasados por fecha de vencimiento y mora"
          actions={
            <div className="flex flex-wrap items-center gap-2">
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
                title="Emergencia: corta la petición en curso (actualizar listas). El servidor puede seguir unos segundos."
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
            modulo === 'a3cuotas'
              ? 'Clientes con al menos cinco cuotas en estado VENCIDO o MORA (morosidad según reglas del sistema en BD). Al regularizar, pueden dejar de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
              : modulo === 'd2antes'
                ? 'Solo cuotas con columna estado PENDIENTE y fecha de vencimiento dentro de 2 días (hoy + 2, zona Caracas). Al pagar o cambiar estado, dejan de listarse. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos.'
                : 'Cuotas pendientes en tiempo real: al registrar pagos que cubren la cuota, el cliente deja de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
          }
          actions={
            <div className="flex flex-wrap items-center gap-2">
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
                title="Emergencia: corta actualización de listas o envío manual en curso. El servidor puede seguir unos segundos."
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>
          }
        />
      </motion.div>

      <div className="border-b border-gray-200">
        <nav className="flex flex-wrap gap-1">
          {TABS.filter(t => t.id !== 'configuracion').map(tab => {
            const count =
              tab.id === 'prejudicial'
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
              {modulo === 'a3cuotas'
                ? 'Cinco o más cuotas VENCIDO o MORA (prejudicial)'
                : modulo === 'd2antes'
                  ? '2 días antes - PENDIENTE, vence en 2 días'
                  : 'Día siguiente al vencimiento (1 día de atraso calendario)'}
            </CardTitle>

            <CardDescription>
              {modulo === 'a3cuotas'
                ? 'Una fila por cliente con al menos cinco cuotas en estado VENCIDO o MORA (columna cuotas.estado). La cuota y fecha mostradas son referencia; «Cuotas atrasadas» es el número de esas cuotas que cumplen el criterio.'
                : modulo === 'd2antes'
                  ? 'Solo filas con cuotas.estado = PENDIENTE y fecha_vencimiento = hoy + 2 (calendario Caracas), sin fecha_pago y con saldo pendiente. «Cuotas atrasadas» sigue la misma regla que el estado de cuenta para el préstamo.'
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
                  size="sm"
                  onClick={() => void handleEnviarPago1DiaManual()}
                  disabled={
                    enviandoPago1Dia ||
                    actualizandoListas ||
                    esperandoPrimeraCargaLista
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
                  size="sm"
                  onClick={() => void handleEnviarPrejudicialManual()}
                  disabled={
                    enviandoPrejudicial ||
                    actualizandoListas ||
                    esperandoPrimeraCargaLista
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
                  size="sm"
                  onClick={() => void handleEnviarD2AntesManual()}
                  disabled={
                    enviandoD2Antes ||
                    actualizandoListas ||
                    esperandoPrimeraCargaLista
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
                title="Emergencia: interrumpe la petición en curso (actualizar listas o envío manual). El servidor puede seguir unos segundos."
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>

            {/* KPIs por pestaña: correos enviados y rebotados */}

            {(activeTab as TabId) !== 'configuracion' && estadisticasPorTab && (
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

            {isLoadingLista && (
              <div className="mb-4 flex items-center gap-2 rounded border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700">
                <RefreshCw
                  className={`h-4 w-4 ${isFetchingLista ? 'animate-spin' : ''}`}
                />

                <span>Cargando datos...</span>
              </div>
            )}

            {mostrarTablaCuotas ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                        #
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                        Nombre
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                        Cédula
                      </th>

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
                        className="w-[4.5rem] min-w-[4.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                        scope="col"
                        title="Revisión manual: triángulo marca visto con nota genérica; visto solo admin puede reabrir."
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
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={9}
                          className="py-8 text-center text-gray-500"
                        >
                          <span className="block font-medium text-gray-600">
                            Ningún registro en este criterio.
                          </span>
                          {listaCargadaSinFilas ? (
                            <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                              {modulo === 'a3cuotas'
                                ? 'Lista ya cargada: se requieren 5+ cuotas en estado VENCIDO o MORA en BD. Si hay mora pero no aparece nadie, sincronice estados de cuotas (auditoría / job) para alinear la columna estado.'
                                : modulo === 'd2antes'
                                  ? 'Lista ya cargada: solo cuotas en estado PENDIENTE con vencimiento exactamente dentro de 2 días (Caracas). Si la columna estado no es PENDIENTE o la fecha no coincide, no aparecerá.'
                                  : 'Lista ya cargada: solo entran cuotas con fecha de vencimiento igual a ayer (Caracas). Si no hay ninguna, la tabla quedará vacía aunque exista mora en otros días.'}
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ) : (
                      sortedList.map((row, idx) => (
                        <tr
                          key={`${row.cliente_id}-${row.prestamo_id ?? 'np'}-${row.numero_cuota ?? 'nc'}`}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="px-3 py-2">{idx + 1}</td>

                          <td className="px-3 py-2 font-medium">
                            {row.nombre}
                          </td>

                          <td className="px-3 py-2">{row.cedula}</td>

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
                            <RevisionManualNotifCell row={row} />
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
                      <th className="px-3 py-2 text-left font-semibold">#</th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Nombre
                      </th>

                      <th className="px-3 py-2 text-left font-semibold">
                        Cédula
                      </th>

                      <th
                        className="w-[4.5rem] min-w-[4.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                        scope="col"
                        title="Revisión manual: triángulo marca visto con nota genérica; visto solo admin puede reabrir."
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
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-8 text-center text-gray-500"
                        >
                          <span className="block font-medium text-gray-600">
                            Ningún cliente en este criterio.
                          </span>
                          {listaCargadaSinFilas ? (
                            <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                              {modulo === 'a3cuotas'
                                ? 'Lista ya cargada: 5+ cuotas VENCIDO o MORA. Sin filas con detalle de cuota: sincronice estados en BD o confirme que algún cliente cumple el umbral.'
                                : modulo === 'd2antes'
                                  ? 'Lista ya cargada: sin cuotas PENDIENTE con vencimiento en 2 días. Revise estados en BD o el calendario de vencimientos.'
                                  : 'Lista ya cargada: sin cuotas con vencimiento ayer. Use Actualizar tras registrar pagos o revise el calendario de vencimientos.'}
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ) : (
                      list.map((row, idx) => (
                        <tr
                          key={`${row.cliente_id}-${row.numero_cuota ?? idx}`}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="px-3 py-2">{idx + 1}</td>

                          <td className="px-3 py-2 font-medium">
                            {row.nombre}
                          </td>

                          <td className="px-3 py-2">{row.cedula}</td>

                          <td className="px-1 py-2 text-center align-middle">
                            <RevisionManualNotifCell row={row} />
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
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

export default Notificaciones
