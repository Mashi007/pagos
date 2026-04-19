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
  Database,
  Calendar,
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
  type AplicarAbonosDriveCuotasResponse,
  type ClienteRetrasadoItem,
  type CompararAbonosDriveCuotasResponse,
  type CompararFechaEntregaQvsAprobacionResponse,
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

import { getErrorMessage } from '../types/errors'

import {
  CASO_NOTIF_GENERAL_D1,
  CASO_NOTIF_GENERAL_D2,
  CASO_NOTIF_GENERAL_PREJ,
  NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA,
  NOTIFICACIONES_VENTANA_NUMEROS_PAGINA,
} from './notificaciones/notificacionesPage.constants'
import {
  cuotasAtrasadasSortValue,
  fechaVencSortValue,
  numericDiferenciaAbonoSort,
  numericTotalPendienteSort,
  textoNumeroCreditoNotif,
  textoTotalPendientePagar,
} from './notificaciones/notificacionesListSort'

import {
  CompararAbonosDriveCuotasCell,
  CompararFechaEntregaQAprobacionCell,
  DiferenciaAbonoGeneralCell,
  DiferenciaFechaGeneralCell,
  RevisionManualNotifCell,
  SortArrowsCuotas,
  filaCoincideFiltroCedulaNotif,
  filaCumpleFiltroDiferenciaAbonoGeneral,
  filaCumpleFiltroDiferenciaFechaGeneral,
  type FiltroDiferenciaAbonoGeneral,
  type FiltroDiferenciaFechaGeneral,
  type NotificacionesCuotasSortCol,
} from './notificaciones/notificacionesPageCells'

import {
  tabListadoDefault,
  tabsParaModulo,
  tipoParaKpiYRebotados,
  type NotificacionesModulo,
  type TabId,
} from './notificaciones/notificacionesPage.tabs'

import {
  tituloEncabezadoNotificaciones,
  tituloDocumentoNotificaciones,
} from './notificaciones/notificacionesPage.header'

import {
  fechaHoyCaracasISO,
  toastErrorTrasEnvioManual,
  toastResultadoEnvioNotificaciones,
} from './notificaciones/notificacionesPage.toasts'

export type { NotificacionesModulo, TabId } from './notificaciones/notificacionesPage.tabs'

type NotificacionesProps = {
  modulo?: NotificacionesModulo
}

export function Notificaciones({ modulo = 'a1dia' }: NotificacionesProps) {
  const TABS = tabsParaModulo(modulo)

  const esListaCombinadaMoras = modulo === 'general' || modulo === 'fecha'

  const listadoDefault = tabListadoDefault(modulo)

  const pageTitle = useMemo(
    () => tituloEncabezadoNotificaciones(modulo),
    [modulo]
  )

  const descripcionModulo = useMemo(() => {
    if (modulo === 'fecha') {
      return 'Solo consulta: mismas listas combinadas que General (día siguiente, prejudicial 5+ cuotas, 2 días antes). La columna «Diferencia fecha» compara la columna Q de la hoja CONCILIACIÓN (entrega) con fecha_aprobacion del préstamo en BD; caché en servidor (cada domingo 04:00 Caracas o Recalcular; luego Actualización manual). Sin envío de correos desde esta pantalla.'
    }
    if (modulo === 'general') {
      return 'Solo consulta: listas unificadas (día siguiente al vencimiento, prejudicial 5+ cuotas, 2 días antes) con columna de caso. La columna «Diferencia abono» usa caché en BD (cada domingo 02:00 Caracas o botón Recalcular; tras el job, use Actualización manual). Sin envío de correos ni ajustes de comunicación desde esta pantalla.'
    }
    if (modulo === 'a3cuotas') {
      return 'Clientes con al menos cinco cuotas en estado VENCIDO o MORA (morosidad según reglas del sistema en BD). Al regularizar, pueden dejar de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
    }
    if (modulo === 'd2antes') {
      return 'Solo cuotas con columna estado PENDIENTE y fecha de vencimiento dentro de 2 días (hoy + 2, zona Caracas). Al pagar o cambiar estado, dejan de listarse. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos.'
    }
    if (modulo === 'a10dias') {
      return 'Solo cuotas pendientes cuya fecha de vencimiento está exactamente a 10 días calendario en el pasado respecto de la fecha de referencia (America/Caracas), con saldo pendiente, y el préstamo con exactamente entre 2 y 3 cuotas en mora (inclusive). Con 1 cuota o con 4 o más no aplica este listado. No mezcla otros días de mora.'
    }
    return 'Cuotas pendientes en tiempo real: al registrar pagos que cubren la cuota, el cliente deja de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos.'
  }, [modulo])

  useEffect(() => {
    const prev = document.title
    document.title = tituloDocumentoNotificaciones(modulo)
    return () => {
      document.title = prev
    }
  }, [modulo])

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
      t === 'dias_10_atraso' ||
      (modulo === 'a3cuotas' && t === 'dias_1_atraso') ||
      (modulo === 'a3cuotas' && t === 'd2antes') ||
      (modulo === 'a1dia' && t === 'prejudicial') ||
      (modulo === 'a1dia' && t === 'd2antes') ||
      (modulo === 'a10dias' &&
        (t === 'dias_1_atraso' || t === 'prejudicial' || t === 'd2antes')) ||
      (modulo === 'd2antes' && (t === 'dias_1_atraso' || t === 'prejudicial')) ||
      (esListaCombinadaMoras &&
        t !== 'general_todos' &&
        Boolean(t)) ||
      (esListaCombinadaMoras && t === 'configuracion')
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
  }, [searchParams, setSearchParams, modulo, esListaCombinadaMoras])

  useEffect(() => {
    if (!esListaCombinadaMoras) return
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
  }, [modulo, activeTab, setSearchParams, esListaCombinadaMoras])

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
        (modulo === 'a1dia' || modulo === 'a10dias' || esListaCombinadaMoras) &&
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
      (modulo === 'd2antes' || esListaCombinadaMoras) &&
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
      (modulo === 'a3cuotas' || esListaCombinadaMoras) &&
      activeTab !== 'configuracion',
  })

  const { data: estadisticasPorTab } = useQuery({
    queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,

    queryFn: () => notificacionService.getEstadisticasPorTab(),

    staleTime: 0,

    enabled: activeTab !== 'configuracion' && !esListaCombinadaMoras,

    placeholderData: {
      dias_5: { enviados: 0, rebotados: 0 },

      dias_3: { enviados: 0, rebotados: 0 },

      dias_1: { enviados: 0, rebotados: 0 },

      hoy: { enviados: 0, rebotados: 0 },

      dias_1_retraso: { enviados: 0, rebotados: 0 },

      dias_10_retraso: { enviados: 0, rebotados: 0 },

      prejudicial: { enviados: 0, rebotados: 0 },

      masivos: { enviados: 0, rebotados: 0 },

      liquidados: { enviados: 0, rebotados: 0 },

      d_2_antes_vencimiento: { enviados: 0, rebotados: 0 },

      recibos: { enviados: 0, rebotados: 0 },
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

  const [programandoRefreshAbonosDrive, setProgramandoRefreshAbonosDrive] =
    useState(false)

  const [programandoRefreshFechaQ, setProgramandoRefreshFechaQ] =
    useState(false)

  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)

  const [enviandoPrejudicial, setEnviandoPrejudicial] = useState(false)

  const [enviandoD2Antes, setEnviandoD2Antes] = useState(false)

  const [enviandoPago1Dia, setEnviandoPago1Dia] = useState(false)

  const [enviandoPago10Dias, setEnviandoPago10Dias] = useState(false)

  /** Confirmación en pantalla (sustituye window.confirm: más clara y fiable en Firefox). */
  const [confirmEnvio, setConfirmEnvio] = useState<null | {
    kind: 'prejudicial' | 'd2antes' | 'pago1dia' | 'pago10dias'
    n: number
  }>(null)

  /** Obligatorio si la lista visible tiene 0 filas y aun así se quiere disparar el POST al servidor. */
  const [ackEnvioConListaVacia, setAckEnvioConListaVacia] = useState(false)

  useEffect(() => {
    if (confirmEnvio == null) return
    setAckEnvioConListaVacia(false)
  }, [confirmEnvio])

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
    setEnviandoPago10Dias(false)
    toast.warning(
      'Cancelación: se cortó la petición en el navegador. El servidor puede seguir unos segundos.'
    )
  }

  const hayOperacionListaEnCurso =
    actualizandoListas ||
    enviandoPrejudicial ||
    enviandoD2Antes ||
    enviandoPago1Dia ||
    enviandoPago10Dias

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

  const handleRefreshAbonosDriveCache = async () => {
    setProgramandoRefreshAbonosDrive(true)
    try {
      const res = await notificacionService.refreshAbonosDriveCache()
      toast.success(
        res.mensaje ??
          'Recálculo de «Diferencia abono» programado en el servidor. En unos minutos use Actualización manual o recargue.'
      )
    } catch (e) {
      console.error(e)
      toast.error(
        getErrorMessage(e) ||
          'No se pudo programar el recálculo de «Diferencia abono».'
      )
    } finally {
      setProgramandoRefreshAbonosDrive(false)
    }
  }

  const handleRefreshFechaEntregaQCache = async () => {
    setProgramandoRefreshFechaQ(true)
    try {
      const res = await notificacionService.refreshFechaEntregaQCache()
      toast.success(
        res.mensaje ??
          'Recálculo de «Fecha Q vs aprobación» programado en el servidor. En unos minutos use Actualización manual o recargue.'
      )
    } catch (e) {
      console.error(e)
      toast.error(
        getErrorMessage(e) ||
          'No se pudo programar el recálculo de «Fecha Q vs aprobación».'
      )
    } finally {
      setProgramandoRefreshFechaQ(false)
    }
  }

  const ejecutarEnvioManualTrasConfirmar = async (p: {
    kind: 'prejudicial' | 'd2antes' | 'pago1dia' | 'pago10dias'
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

    if (kind === 'pago10dias') {
      const ac = beginOperacionListaAbortable()
      setEnviandoPago10Dias(true)
      const loadingId = toast.loading(
        'Enviando correos… con muchas filas puede tardar más de 10 minutos. No cierre esta pestaña.'
      )

      try {
        const res = await notificacionService.enviarCasoManual(
          'PAGO_10_DIAS_ATRASADO',
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
          'Revise PAGO_10_DIAS_ATRASADO en Configuración y el correo del servidor.'
        )
      } finally {
        if (operacionListaAbortRef.current === ac) {
          operacionListaAbortRef.current = null
        }
        setEnviandoPago10Dias(false)
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

  const solicitarConfirmacionEnvioPago10Dias = () => {
    if (modulo !== 'a10dias') return
    const n = data?.dias_10_atraso?.length ?? 0
    setConfirmEnvio({ kind: 'pago10dias', n })
  }

  const confirmarEnvioManualYEnviar = () => {
    const p = confirmEnvio
    if (!p) return
    setConfirmEnvio(null)
    void ejecutarEnvioManualTrasConfirmar(p)
  }

  const list = useMemo((): ClienteRetrasadoItem[] => {
    if (esListaCombinadaMoras && activeTab === 'general_todos') {
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

    if (modulo === 'a10dias') {
      if (activeTab !== 'atraso10dias') return []
      return data?.dias_10_atraso ?? []
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
    data?.dias_10_atraso,
    dataPrejudicial?.items,
    dataD2Antes?.items,
    esListaCombinadaMoras,
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

  const [filtroDiferenciaFechaGeneral, setFiltroDiferenciaFechaGeneral] =
    useState<FiltroDiferenciaFechaGeneral>('todas')

  useEffect(() => {
    setFiltroCedula('')
  }, [activeTab, modulo, fechaCaracasApi])

  useEffect(() => {
    setFiltroDiferenciaAbonoGeneral('todas')
  }, [activeTab, modulo, fechaCaracasApi, filtroCedula])

  useEffect(() => {
    setFiltroDiferenciaFechaGeneral('todas')
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

        case 'diferencia_abono': {
          const va = numericDiferenciaAbonoSort(a)
          const vb = numericDiferenciaAbonoSort(b)
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

  /** Siempre partir de `sortedList`: con `sortCol` null es idéntico a `list`; en tabla compacta permite ordenar por diferencia abono. */
  const listaBasePaginacion = sortedList

  const listaTrasFiltroCedula = useMemo(() => {
    const q = filtroCedula.trim()
    if (!q) return listaBasePaginacion
    return listaBasePaginacion.filter(row =>
      filaCoincideFiltroCedulaNotif(row, q)
    )
  }, [listaBasePaginacion, filtroCedula])

  const listaFiltradaCedula = useMemo(() => {
    let base = listaTrasFiltroCedula
    if (modulo === 'general' && filtroDiferenciaAbonoGeneral !== 'todas') {
      base = base.filter(row => {
        const ced = String(row.cedula ?? '').trim()
        const pid = row.prestamo_id
        if (!ced || pid == null) return false
        const d = row.comparar_abonos_drive_cuotas
        if (!d) return false
        return filaCumpleFiltroDiferenciaAbonoGeneral(
          filtroDiferenciaAbonoGeneral,
          d
        )
      })
    }
    if (modulo === 'fecha' && filtroDiferenciaFechaGeneral !== 'todas') {
      base = base.filter(row => {
        const ced = String(row.cedula ?? '').trim()
        const pid = row.prestamo_id
        if (!ced || pid == null) return false
        const d = row.comparar_fecha_entrega_q_aprobacion
        if (!d) return false
        return filaCumpleFiltroDiferenciaFechaGeneral(
          filtroDiferenciaFechaGeneral,
          d
        )
      })
    }
    return base
  }, [
    listaTrasFiltroCedula,
    modulo,
    filtroDiferenciaAbonoGeneral,
    filtroDiferenciaFechaGeneral,
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
    esListaCombinadaMoras
      ? isPending || isPendingPrej || isPendingD2
      : modulo === 'a1dia' || modulo === 'a10dias'
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
    (esListaCombinadaMoras &&
      ((isPending && !isFetched && !isError) ||
        (isPendingPrej && !isFetchedPrej && !isErrorPrej) ||
        (isPendingD2 && !isFetchedD2 && !isErrorD2))) ||
    ((modulo === 'a1dia' || modulo === 'a10dias') &&
      isPending &&
      !isFetched &&
      !isError) ||
    (modulo === 'a3cuotas' &&
      isPendingPrej &&
      !isFetchedPrej &&
      !isErrorPrej) ||
    (modulo === 'd2antes' && isPendingD2 && !isFetchedD2 && !isErrorD2)

  const isErrorLista =
    esListaCombinadaMoras
      ? isError && isErrorPrej && isErrorD2
      : modulo === 'a1dia' || modulo === 'a10dias'
        ? isError
        : modulo === 'a3cuotas'
          ? isErrorPrej
          : isErrorD2

  const errorLista =
    esListaCombinadaMoras
      ? error ?? errorPrej ?? errorD2
      : modulo === 'a1dia' || modulo === 'a10dias'
        ? error
        : modulo === 'a3cuotas'
          ? errorPrej
          : errorD2

  const refetchLista =
    esListaCombinadaMoras
      ? () => {
          void Promise.all([refetch(), refetchPrej(), refetchD2()])
        }
      : modulo === 'a1dia' || modulo === 'a10dias'
        ? refetch
        : modulo === 'a3cuotas'
          ? refetchPrej
          : refetchD2

  const isFetchingLista =
    esListaCombinadaMoras
      ? isFetching || isFetchingPrej || isFetchingD2
      : modulo === 'a1dia' || modulo === 'a10dias'
        ? isFetching
        : modulo === 'a3cuotas'
          ? isFetchingPrej
          : isFetchingD2

  const isFetchedLista =
    esListaCombinadaMoras
      ? (isFetched || isError) &&
        (isFetchedPrej || isErrorPrej) &&
        (isFetchedD2 || isErrorD2)
      : modulo === 'a1dia' || modulo === 'a10dias'
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
            modulo === 'general' || modulo === 'fecha'
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

  if (activeTab === 'configuracion' && !esListaCombinadaMoras) {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title={pageTitle}
          description={descripcionModulo}
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
                Actualización manual
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
          <nav
            role="tablist"
            aria-label="Secciones: listado y configuración"
            className="flex flex-wrap gap-2"
          >
            {TABS.map(tab => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                id={`notif-cfg-tab-${tab.id}`}
                aria-selected={activeTab === tab.id}
                aria-controls={
                  tab.id === 'configuracion'
                    ? 'notif-cfg-panel-config'
                    : 'notif-cfg-panel-listado'
                }
                tabIndex={0}
                onClick={() => setActiveTabAndUrl(tab.id)}
                className={`flex items-center gap-2 rounded-t px-3 py-2 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border border-b-0 border-gray-200 bg-white text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="h-4 w-4" aria-hidden />

                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Cada submenú: una fila de envíos / adjuntos por tipo en BD. */}
        <div
          role="tabpanel"
          id={
            activeTab === 'configuracion'
              ? 'notif-cfg-panel-config'
              : 'notif-cfg-panel-listado'
          }
          aria-labelledby={`notif-cfg-tab-${activeTab}`}
        >
          <ConfiguracionNotificaciones
          alcance={
            modulo === 'a1dia'
              ? 'solo_pago_1_dia'
              : modulo === 'd2antes'
                ? 'solo_pago_2_dias_antes_pendiente'
                : modulo === 'a10dias'
                  ? 'solo_pago_10_dias_atrasado'
                  : 'solo_prejudicial'
          }
        />
        </div>
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
          title={pageTitle}
          description={descripcionModulo}
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
                Actualización manual
              </Button>

              {modulo === 'general' ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleRefreshAbonosDriveCache()}
                  disabled={
                    programandoRefreshAbonosDrive || actualizandoListas
                  }
                  title="Misma lógica que el job cada domingo 02:00 (America/Caracas): persiste comparación ABONOS (hoja) vs cuotas para préstamos activos. Corre en segundo plano; luego use Actualización manual."
                >
                  <Database
                    className={`mr-2 h-4 w-4 ${
                      programandoRefreshAbonosDrive ? 'animate-pulse' : ''
                    }`}
                  />
                  Recalcular Diferencia abono
                </Button>
              ) : null}

              {modulo === 'fecha' ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleRefreshFechaEntregaQCache()}
                  disabled={programandoRefreshFechaQ || actualizandoListas}
                  title="Misma lógica que el job cada domingo 04:00 (America/Caracas): columna Q vs fecha_aprobacion. Segundo plano; luego use Actualización manual."
                >
                  <Calendar
                    className={`mr-2 h-4 w-4 ${
                      programandoRefreshFechaQ ? 'animate-pulse' : ''
                    }`}
                  />
                  Recalcular Diferencia fecha
                </Button>
              ) : null}

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

      {!esListaCombinadaMoras ? (
        <div className="border-b border-gray-200">
          <nav
            role="tablist"
            aria-label="Vistas del submódulo de notificaciones"
            className="flex flex-wrap gap-1"
          >
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
                      : tab.id === 'atraso10dias'
                        ? (data?.dias_10_atraso?.length ?? 0)
                        : (data?.dias_1_atraso?.length ?? 0)

              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`notif-tab-${tab.id}`}
                  aria-selected={activeTab === tab.id}
                  aria-controls="notif-panel-principal"
                  tabIndex={0}
                  onClick={() => setActiveTabAndUrl(tab.id)}
                  className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <tab.icon className="h-4 w-4" aria-hidden />

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
              type="button"
              role="tab"
              id="notif-tab-configuracion"
              aria-selected={activeTab === 'configuracion'}
              aria-controls="notif-panel-principal"
              tabIndex={0}
              onClick={() => setActiveTabAndUrl('configuracion')}
              className="flex items-center gap-2 border-b-2 border-transparent px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              <Settings className="h-4 w-4" aria-hidden />
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

      <div
        role={esListaCombinadaMoras ? 'region' : 'tabpanel'}
        id="notif-panel-principal"
        aria-label={
          esListaCombinadaMoras ? 'Listados de mora combinados' : undefined
        }
        aria-labelledby={
          esListaCombinadaMoras ? undefined : `notif-tab-${activeTab}`
        }
      >
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
              {modulo === 'fecha'
                ? 'Fecha - mismos casos de mora (listas combinadas)'
                : modulo === 'general'
                  ? 'General'
                  : modulo === 'a3cuotas'
                    ? 'Cinco o más cuotas VENCIDO o MORA (prejudicial)'
                    : modulo === 'd2antes'
                      ? '2 días antes - PENDIENTE, vence en 2 días'
                      : modulo === 'a10dias'
                        ? '10 días de atraso (calendario desde vencimiento)'
                        : 'Día siguiente al vencimiento (1 día de atraso calendario)'}
            </CardTitle>

            <CardDescription>
              {fechaCaracasApi ? (
                <span className="mb-2 block font-medium text-amber-800">
                  Referencia de listado y envío: {fechaCaracasApi}{' '}
                  (America/Caracas). Use «Hoy» arriba para volver al día actual.
                </span>
              ) : null}
              {modulo === 'fecha'
                ? 'Se concatenan las mismas filas que en General. «Diferencia fecha» = días (columna Q de la hoja CONCILIACIÓN, posición Excel dentro del rango configurado, p. ej. A:S − fecha_aprobacion del préstamo en BD). Caché domingo 04:00 Caracas o Recalcular arriba.'
                : modulo === 'general'
                  ? 'Se concatenan las mismas filas que en los submenús «Día siguiente al vencimiento», «Prejudicial (5+ cuotas)» y «2 días antes». El listado por «10 días de atraso» (calendario) es otro submenú y no entra aquí. La columna «Caso» indica el criterio. Un mismo cliente puede aparecer más de una vez si cumple varios criterios. «Diferencia abono» lee caché en BD (02:00 Caracas o Recalcular arriba; también se actualiza al aplicar ABONOS desde la balanza).'
                  : modulo === 'a3cuotas'
                    ? 'Una fila por cliente con al menos cinco cuotas en estado VENCIDO o MORA (columna cuotas.estado). La cuota y fecha mostradas son referencia; «Cuotas atrasadas» es el número de esas cuotas que cumplen el criterio.'
                    : modulo === 'd2antes'
                      ? 'Solo filas con cuotas.estado = PENDIENTE y fecha_vencimiento = hoy + 2 (calendario Caracas), sin fecha_pago y con saldo pendiente. Se omiten préstamos con «Cuotas atrasadas» = 0 (al corriente en mora). «Cuotas atrasadas» sigue la misma regla que el estado de cuenta para el préstamo.'
                      : modulo === 'a10dias'
                        ? 'Una fila por cuota pendiente con fecha_vencimiento = fecha de referencia − 10 días (calendario), sin fecha_pago y con saldo pendiente; préstamo no liquidado ni desistimiento. Solo si el préstamo tiene entre 2 y 3 cuotas en mora (misma regla que la columna Cuotas atrasadas); con 1 o con 4 o más no entra. No incluye cuotas con otro número de días de atraso respecto de esa fecha.'
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
                  enviandoPago1Dia ||
                  enviandoPago10Dias
                }
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualización manual
              </Button>

              {modulo === 'general' ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleRefreshAbonosDriveCache()}
                  disabled={
                    programandoRefreshAbonosDrive ||
                    actualizandoListas ||
                    enviandoPrejudicial ||
                    enviandoD2Antes ||
                    enviandoPago1Dia ||
                    enviandoPago10Dias
                  }
                  title="Job en servidor (segundo plano), igual que 02:00 Caracas. Luego pulse Actualización manual."
                >
                  <Database
                    className={`mr-2 h-4 w-4 ${
                      programandoRefreshAbonosDrive ? 'animate-pulse' : ''
                    }`}
                  />
                  Recalcular Diferencia abono
                </Button>
              ) : null}

              {modulo === 'fecha' ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleRefreshFechaEntregaQCache()}
                  disabled={
                    programandoRefreshFechaQ ||
                    actualizandoListas ||
                    enviandoPrejudicial ||
                    enviandoD2Antes ||
                    enviandoPago1Dia ||
                    enviandoPago10Dias
                  }
                  title="Job en servidor (segundo plano), igual que domingo 04:00 Caracas. Luego pulse Actualización manual."
                >
                  <Calendar
                    className={`mr-2 h-4 w-4 ${
                      programandoRefreshFechaQ ? 'animate-pulse' : ''
                    }`}
                  />
                  Recalcular Diferencia fecha
                </Button>
              ) : null}

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

              {modulo === 'a10dias' && (
                <Button
                  type="button"
                  size="sm"
                  onClick={solicitarConfirmacionEnvioPago10Dias}
                  disabled={enviandoPago10Dias || esperandoPrimeraCargaLista}
                  title={
                    esperandoPrimeraCargaLista
                      ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                      : undefined
                  }
                  className="bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Mail
                    className={`mr-2 h-4 w-4 ${enviandoPago10Dias ? 'animate-pulse' : ''}`}
                  />
                  {enviandoPago10Dias
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
                    title="Cero = coincide con tolerancia del modal. Mayor a cero = diferencia (hoja − cuotas) estrictamente mayor que la tolerancia (mismo umbral que «Sí» en el modal). Menor a cero = diferencia menor que −tolerancia. El listado usa caché en BD: si el modal en vivo no coincide, resincronice o recalcule."
                  >
                    <option value="todas">Todas</option>
                    <option value="cero">Cero (sin diferencia; tolerancia como en el modal)</option>
                    <option value="drive_mayor">
                      Mayor a cero (diferencia &gt; tolerancia; Drive por encima del total en cuotas)
                    </option>
                    <option value="drive_menor">
                      Menor a cero (Drive &lt; sistema; más pagado en cuotas que en la hoja)
                    </option>
                  </select>
                </div>
              ) : null}
              {modulo === 'fecha' ? (
                <div className="flex min-w-[14rem] max-w-md flex-col gap-1">
                  <label
                    htmlFor="filtro-dif-fecha-general"
                    className="text-xs font-medium text-gray-600"
                  >
                    Diferencia fecha (Q − aprobación)
                  </label>
                  <select
                    id="filtro-dif-fecha-general"
                    className="h-9 rounded-md border border-input bg-white px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                    value={filtroDiferenciaFechaGeneral}
                    onChange={e =>
                      setFiltroDiferenciaFechaGeneral(
                        e.target.value as FiltroDiferenciaFechaGeneral
                      )
                    }
                    disabled={isLoadingLista}
                    title="Igual a 0 = misma fecha calendario (Q y aprobación; tolerancia como en el modal). Mayor que cero = Q estrictamente posterior (indicador Sí). Menor que cero = Q anterior a la aprobación (días negativos)."
                  >
                    <option value="todas">Todas</option>
                    <option value="cero">
                      Igual a 0 (misma fecha calendario; tolerancia como en el modal)
                    </option>
                    <option value="mayor_cero">
                      Mayor que cero (Q posterior a la fecha de aprobación; indicador Sí)
                    </option>
                    <option value="menor_cero">
                      Menor que cero (Q anterior a la fecha de aprobación; días negativos)
                    </option>
                  </select>
                </div>
              ) : null}
              {filtroCedula.trim() &&
              list.length > 0 &&
              !(
                modulo === 'general' &&
                filtroDiferenciaAbonoGeneral !== 'todas'
              ) &&
              !(
                modulo === 'fecha' &&
                filtroDiferenciaFechaGeneral !== 'todas'
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
                  filas (tras filtro de diferencia de abono)
                </p>
              ) : null}
              {!filtroCedula.trim() &&
              modulo === 'fecha' &&
              filtroDiferenciaFechaGeneral !== 'todas' &&
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
                  filas (tras filtro de diferencia de fecha)
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
              {filtroCedula.trim() &&
              modulo === 'fecha' &&
              filtroDiferenciaFechaGeneral !== 'todas' &&
              list.length > 0 ? (
                <p className="text-xs text-muted-foreground sm:ml-auto">
                  Tras cédula y diferencia de fecha:{' '}
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
              !esListaCombinadaMoras &&
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

            {esListaCombinadaMoras &&
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

                        {!esListaCombinadaMoras ? (
                          <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                            Nombre
                          </th>
                        ) : null}

                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          Cédula
                        </th>

                        {esListaCombinadaMoras ? (
                          <th className="min-w-[10rem] whitespace-normal px-3 py-2 text-left text-xs font-semibold leading-tight">
                            Caso
                          </th>
                        ) : null}

                        {modulo === 'general' ? (
                          <th className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight">
                            <div className="inline-flex w-full items-center justify-end gap-1">
                              <span
                                title="Valor del listado desde caché en BD: domingo 02:00 Caracas o Recalcular; también al aplicar ABONOS desde la balanza."
                              >
                                Diferencia Abono
                              </span>

                              <SortArrowsCuotas
                                column="diferencia_abono"
                                labelAsc="Orden ascendente: diferencia abono (hoja − cuotas)"
                                labelDesc="Orden descendente: diferencia abono (hoja − cuotas)"
                                sortCol={sortCol}
                                sortDir={sortDir}
                                onAsc={aplicarOrdenAsc}
                                onDesc={aplicarOrdenDesc}
                              />
                            </div>
                          </th>
                        ) : null}

                        {modulo === 'fecha' ? (
                          <th
                            className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight"
                            title="Días = fecha columna Q (hoja) − fecha_aprobacion (BD). Caché cada domingo 04:00 Caracas o Recalcular."
                          >
                            Diferencia fecha (días)
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
                          title={
                            modulo === 'fecha'
                              ? 'Revisión manual (triángulo) y comparar columna Q (hoja) vs fecha de aprobación en BD (icono calendario).'
                              : 'Revisión manual (triángulo) y comparar ABONOS hoja vs total pagado en cuotas (icono azul).'
                          }
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
                            colSpan={esListaCombinadaMoras ? 10 : 9}
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
                                    : modulo === 'fecha' &&
                                        filtroDiferenciaFechaGeneral !== 'todas' &&
                                        listaTrasFiltroCedula.length > 0
                                      ? 'Ninguna fila cumple el filtro de diferencia de fecha.'
                                      : 'Ningún registro en este criterio.'}
                            </span>
                            {listaCargadaSinFilas ? (
                              <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                                {modulo === 'general' || modulo === 'fecha'
                                  ? 'Listas ya cargadas: no hay filas en ninguno de los tres criterios (día siguiente, prejudicial, 2 días antes) para la fecha de referencia.'
                                  : modulo === 'a3cuotas'
                                    ? 'Lista ya cargada: se requieren 5+ cuotas en estado VENCIDO o MORA en BD. Si hay mora pero no aparece nadie, sincronice estados de cuotas (auditoría / job) para alinear la columna estado.'
                                    : modulo === 'd2antes'
                                      ? 'Lista ya cargada: solo cuotas en estado PENDIENTE con vencimiento exactamente dentro de 2 días (Caracas). Si la columna estado no es PENDIENTE o la fecha no coincide, no aparecerá.'
                                      : modulo === 'a10dias'
                                        ? 'Lista ya cargada: vencimiento = referencia − 10 días (Caracas), saldo pendiente y entre 2 y 3 cuotas en mora en el préstamo. Con 1 o con 4+ cuotas atrasadas, o si la fecha no coincide, no aparecerá.'
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
                                Elija «Todas» u otro criterio. «Cero» usa la misma
                                coincidencia por tolerancia que el modal; «Mayor a
                                cero» = diferencia (hoja − cuotas) mayor que la
                                tolerancia; «Menor a cero» = diferencia menor que
                                −tolerancia (más pagado en cuotas que en la hoja).
                                El listado refleja caché: si difiere del modal, actualice
                                datos o espere el recálculo programado.
                              </span>
                            ) : modulo === 'fecha' &&
                              filtroDiferenciaFechaGeneral !== 'todas' &&
                              listaTrasFiltroCedula.length > 0 ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Elija «Todas» u otro criterio. «Igual a 0» = misma fecha
                                (calendario; tolerancia como en el modal); «Mayor que
                                cero» = columna Q posterior a la aprobación (indicador
                                Sí); «Menor que cero» = Q anterior (días negativos).
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

                            {!esListaCombinadaMoras ? (
                              <td className="px-3 py-2 font-medium">
                                {row.nombre}
                              </td>
                            ) : null}

                            <td className="px-3 py-2">{row.cedula}</td>

                            {esListaCombinadaMoras ? (
                              <td className="max-w-[14rem] px-3 py-2 text-xs leading-snug text-slate-800">
                                {row.notificacion_caso ?? '-'}
                              </td>
                            ) : null}

                            {modulo === 'general' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                <DiferenciaAbonoGeneralCell
                                  row={row}
                                  data={
                                    row.comparar_abonos_drive_cuotas ?? undefined
                                  }
                                  isLoading={false}
                                  isError={false}
                                />
                              </td>
                            ) : null}

                            {modulo === 'fecha' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                <DiferenciaFechaGeneralCell
                                  row={row}
                                  data={
                                    row.comparar_fecha_entrega_q_aprobacion ??
                                    undefined
                                  }
                                  isLoading={false}
                                  isError={false}
                                />
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
                                {modulo === 'fecha' ? (
                                  <CompararFechaEntregaQAprobacionCell row={row} />
                                ) : (
                                  <CompararAbonosDriveCuotasCell row={row} />
                                )}
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

                        {!esListaCombinadaMoras ? (
                          <th className="px-3 py-2 text-left font-semibold">
                            Nombre
                          </th>
                        ) : null}

                        <th className="px-3 py-2 text-left font-semibold">
                          Cédula
                        </th>

                        {esListaCombinadaMoras ? (
                          <th className="min-w-[10rem] px-3 py-2 text-left text-xs font-semibold leading-tight">
                            Caso
                          </th>
                        ) : null}

                        {modulo === 'general' ? (
                          <th className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight">
                            <div className="inline-flex w-full items-center justify-end gap-1">
                              <span
                                title="Valor del listado desde caché en BD: domingo 02:00 Caracas o Recalcular; también al aplicar ABONOS desde la balanza."
                              >
                                Diferencia Abono
                              </span>

                              <SortArrowsCuotas
                                column="diferencia_abono"
                                labelAsc="Orden ascendente: diferencia abono (hoja − cuotas)"
                                labelDesc="Orden descendente: diferencia abono (hoja − cuotas)"
                                sortCol={sortCol}
                                sortDir={sortDir}
                                onAsc={aplicarOrdenAsc}
                                onDesc={aplicarOrdenDesc}
                              />
                            </div>
                          </th>
                        ) : null}

                        {modulo === 'fecha' ? (
                          <th
                            className="whitespace-nowrap px-3 py-2 text-right text-xs font-semibold leading-tight"
                            title="Días = fecha columna Q (hoja) − fecha_aprobacion (BD). Caché cada domingo 04:00 Caracas o Recalcular."
                          >
                            Diferencia fecha (días)
                          </th>
                        ) : null}

                        <th
                          className="min-w-[5.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                          scope="col"
                          title={
                            modulo === 'fecha'
                              ? 'Revisión manual (triángulo) y comparar columna Q (hoja) vs fecha de aprobación en BD (icono calendario).'
                              : 'Revisión manual (triángulo) y comparar ABONOS hoja vs total pagado en cuotas (icono azul).'
                          }
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
                            colSpan={esListaCombinadaMoras ? 6 : 5}
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
                                    : modulo === 'fecha' &&
                                        filtroDiferenciaFechaGeneral !== 'todas' &&
                                        listaTrasFiltroCedula.length > 0
                                      ? 'Ninguna fila cumple el filtro de diferencia de fecha.'
                                      : 'Ningún cliente en este criterio.'}
                            </span>
                            {listaCargadaSinFilas ? (
                              <span className="mx-auto mt-2 block max-w-lg text-xs text-gray-500">
                                {modulo === 'general' || modulo === 'fecha'
                                  ? 'Listas ya cargadas: ningún criterio devolvió filas sin detalle de cuota para la fecha de referencia.'
                                  : modulo === 'a3cuotas'
                                    ? 'Lista ya cargada: 5+ cuotas VENCIDO o MORA. Sin filas con detalle de cuota: sincronice estados en BD o confirme que algún cliente cumple el umbral.'
                                    : modulo === 'd2antes'
                                      ? 'Lista ya cargada: sin cuotas PENDIENTE con vencimiento en 2 días. Revise estados en BD o el calendario de vencimientos.'
                                      : modulo === 'a10dias'
                                        ? 'Lista ya cargada: sin cuotas en −10 días con saldo pendiente y entre 2 y 3 cuotas en mora, o todos los casos tienen 1 o 4+ cuotas atrasadas (no aplican aquí).'
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
                                Elija «Todas» u otro criterio. «Cero» coincide con la
                                tolerancia del modal; «Mayor a cero» = diferencia
                                mayor que tolerancia; «Menor a cero» = diferencia menor
                                que −tolerancia. Caché en listado vs comparación en vivo
                                en el modal pueden discrepar hasta resincronizar.
                              </span>
                            ) : modulo === 'fecha' &&
                              filtroDiferenciaFechaGeneral !== 'todas' &&
                              listaTrasFiltroCedula.length > 0 ? (
                              <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                Elija «Todas» u otro criterio. «Igual a 0» = misma fecha
                                (tolerancia como en el modal); «Mayor que cero» = Q
                                posterior (indicador Sí); «Menor que cero» = Q anterior
                                (días negativos).
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

                            {!esListaCombinadaMoras ? (
                              <td className="px-3 py-2 font-medium">
                                {row.nombre}
                              </td>
                            ) : null}

                            <td className="px-3 py-2">{row.cedula}</td>

                            {esListaCombinadaMoras ? (
                              <td className="max-w-[14rem] px-3 py-2 text-xs leading-snug text-slate-800">
                                {row.notificacion_caso ?? '-'}
                              </td>
                            ) : null}

                            {modulo === 'general' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                <DiferenciaAbonoGeneralCell
                                  row={row}
                                  data={
                                    row.comparar_abonos_drive_cuotas ?? undefined
                                  }
                                  isLoading={false}
                                  isError={false}
                                />
                              </td>
                            ) : null}

                            {modulo === 'fecha' ? (
                              <td className="px-3 py-2 text-right align-middle">
                                <DiferenciaFechaGeneralCell
                                  row={row}
                                  data={
                                    row.comparar_fecha_entrega_q_aprobacion ??
                                    undefined
                                  }
                                  isLoading={false}
                                  isError={false}
                                />
                              </td>
                            ) : null}

                            <td className="px-1 py-2 text-center align-middle">
                              <div className="flex flex-wrap items-center justify-center gap-1">
                                <RevisionManualNotifCell row={row} />
                                {modulo === 'fecha' ? (
                                  <CompararFechaEntregaQAprobacionCell row={row} />
                                ) : (
                                  <CompararAbonosDriveCuotasCell row={row} />
                                )}
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
      </div>

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

              {confirmEnvio?.kind === 'pago10dias' ? (
                <p>
                  {confirmEnvio.n === 0
                    ? 'No hay casos en la lista cargada. El servidor procesará PAGO_10_DIAS_ATRASADO (puede estar vacía).'
                    : `Envío para 10 días de atraso (${confirmEnvio.n} casos en la lista completa; mismo criterio en servidor, no solo la página actual). Respeta plantilla, CCO y modo prueba en Configuración.`}
                </p>
              ) : null}

              {confirmEnvio != null && confirmEnvio.n === 0 ? (
                <label className="flex cursor-pointer items-start gap-2 rounded-md border border-amber-200 bg-amber-50/90 p-3 text-gray-800">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 shrink-0 rounded border-gray-300 accent-blue-600"
                    checked={ackEnvioConListaVacia}
                    onChange={e =>
                      setAckEnvioConListaVacia(e.target.checked)
                    }
                  />
                  <span>
                    Confirmo enviar igualmente: la lista en pantalla tiene 0
                    filas y entiendo que el servidor recalcula el criterio (el
                    envío puede quedar vacío).
                  </span>
                </label>
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
              disabled={
                confirmEnvio != null &&
                confirmEnvio.n === 0 &&
                !ackEnvioConListaVacia
              }
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
