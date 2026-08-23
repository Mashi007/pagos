import {
  useState,
  useEffect,
  useMemo,
  useRef,
  Fragment,
} from 'react'

import { useSearchParams } from 'react-router-dom'

import { motion } from 'framer-motion'

import {
  RefreshCw,
  AlertTriangle,
  Mail,
  Download,
  Bell,
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

import {
  EnvioNotificacionesProgressBar,
  LoteContinuarIndicador,
  type EnvioProgressState,
  type LoteContinuarItem,
} from '../components/notificaciones/EnvioNotificacionesProgressBar'

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
  type ClienteRetrasadoItem,
  type EstadisticasPorTab,
} from '../services/notificacionService'

import { prestamoService } from '../services/prestamoService'

import { toast } from 'sonner'

import { ConfiguracionNotificaciones } from '../components/notificaciones/ConfiguracionNotificaciones'

import {
  NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
  NOTIFICACIONES_D2_ANTES_QUERY_KEY,
  NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
  NOTIFICACIONES_MORA_BROADCAST_CHANNEL,
  NOTIFICACIONES_PREJUDICIAL_LISTA_QUERY_KEY,
  NOTIFICACIONES_ESTADO_CUENTA_LISTA_QUERY_KEY,
  NOTIFICACIONES_COBRANZAS_LISTA_QUERY_KEY,
  NOTIFICACIONES_CUOTAS_4_MAS_LISTA_QUERY_KEY,
  invalidateListasNotificacionesMora,
} from '../constants/queryKeys'
import { envioBatchSigueActivoUi } from '../utils/envioBatchActivo'

import { NOTIFICACIONES_QUERY_KEYS } from '../queries/notificaciones'

import { marcarReturnRevisionDesdeNotificaciones } from '../constants/revisionNavigation'

import { isRequestCanceled } from '../utils/requestCanceled'

import { getErrorMessage } from '../types/errors'

import {
  NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA,
  NOTIFICACIONES_VENTANA_NUMEROS_PAGINA,
} from './notificaciones/notificacionesPage.constants'
import {
  cuotasAtrasadasSortValue,
  fechaVencSortValue,
  numericTotalPendienteSort,
  textoNumeroCreditoNotif,
  textoTotalPendientePagar,
} from './notificaciones/notificacionesListSort'

import {
  CompararAbonosDriveCuotasCell,
  RevisionManualNotifCell,
  SortArrowsCuotas,
  filaCoincideFiltroCedulaNotif,
  type NotificacionesCuotasSortCol,
} from './notificaciones/notificacionesPageCells'

import {
  tabListadoDefault,
  tabsParaModulo,
  tipoCasoEnvioParaModulo,
  tipoCasoEnvioParaTab,
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
  omitidosDesdeEnvioRes,
  toastErrorTrasEnvioManual,
  toastResultadoEnvioNotificaciones,
} from './notificaciones/notificacionesPage.toasts'

export type {
  NotificacionesModulo,
  TabId,
} from './notificaciones/notificacionesPage.tabs'

type NotificacionesProps = {
  modulo?: NotificacionesModulo
}

export function Notificaciones({ modulo = 'a1dia' }: NotificacionesProps) {
  const TABS = tabsParaModulo(modulo)

  const listadoDefault = tabListadoDefault(modulo)

  const pageTitle = useMemo(
    () => tituloEncabezadoNotificaciones(modulo),
    [modulo]
  )

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

  const [rebotadosDesde, setRebotadosDesde] = useState('')
  const [rebotadosHasta, setRebotadosHasta] = useState('')
  const [descargandoAuditoriaCorreos, setDescargandoAuditoriaCorreos] =
    useState(false)

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
      (modulo === 'a2cuotas' && t === 'dias_1_atraso') ||
      (modulo === 'a2cuotas' && t === 'd2antes') ||
      (modulo === 'a2cuotas' && t === 'cobranzas') ||
      (modulo === 'a2cuotas' && t === 'cuotas_4_mas') ||
      (modulo === 'estadoCuenta' && t !== 'estado_cuenta' && t !== 'configuracion') ||
      (modulo === 'cobranzas' &&
        (t === 'dias_1_atraso' ||
          t === 'prejudicial' ||
          t === 'd2antes' ||
          t === 'cuotas_4_mas')) ||
      (modulo === 'a4cuotas' &&
        (t === 'dias_1_atraso' ||
          t === 'prejudicial' ||
          t === 'd2antes' ||
          t === 'cobranzas')) ||
      (modulo === 'a1dia' && t === 'prejudicial') ||
      (modulo === 'a1dia' && t === 'cobranzas') ||
      (modulo === 'a1dia' && t === 'cuotas_4_mas') ||
      (modulo === 'a1dia' && t === 'd2antes') ||
      (modulo === 'a10dias' &&
        (t === 'dias_1_atraso' ||
          t === 'prejudicial' ||
          t === 'cobranzas' ||
          t === 'cuotas_4_mas' ||
          t === 'd2antes')) ||
      (modulo === 'd2antes' &&
        (t === 'dias_1_atraso' ||
          t === 'prejudicial' ||
          t === 'cobranzas' ||
          t === 'cuotas_4_mas'))
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
  const [pausarAutoRefetchNotificaciones, setPausarAutoRefetchNotificaciones] =
    useState(false)

  const { data, isPending, isFetched, isError, error, refetch, isFetching } =
    useQuery({
      queryKey: [
        ...NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
        fechaCaracasApi ?? null,
      ],

      queryFn: () => notificacionService.getClientesRetrasados(fechaCaracasApi),

      // Listas mora: deben reflejar pagos recién registrados (otra pestaña / revisión).
      staleTime: 0,
      refetchOnWindowFocus: true,
      refetchInterval: activeTab !== 'configuracion' ? 30_000 : false,

      // Sin placeholderData: con v5, placeholder hace isPending=false y la tabla se ve vacía mientras carga (Render frío).
      /** En Configuración no se listan cuotas: evita GET pesado y errores 500 por carga/BD innecesaria. */

      enabled:
        (modulo === 'a1dia' || modulo === 'a10dias') &&
        activeTab !== 'configuracion' &&
        !pausarAutoRefetchNotificaciones,
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

    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchInterval: activeTab !== 'configuracion' ? 30_000 : false,

    enabled:
      modulo === 'd2antes' &&
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,
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
    refetchInterval: activeTab !== 'configuracion' ? 30_000 : false,

    enabled:
      modulo === 'a2cuotas' &&
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,
  })

  const {
    data: dataEstadoCuenta,
    isPending: isPendingEstadoCuenta,
    isFetched: isFetchedEstadoCuenta,
    isError: isErrorEstadoCuenta,
    error: errorEstadoCuenta,
    refetch: refetchEstadoCuenta,
    isFetching: isFetchingEstadoCuenta,
  } = useQuery({
    queryKey: [
      ...NOTIFICACIONES_ESTADO_CUENTA_LISTA_QUERY_KEY,
      fechaCaracasApi ?? null,
    ],

    queryFn: () =>
      notificacionService.listarNotificacionesEstadoCuenta(
        undefined,
        fechaCaracasApi
      ),

    staleTime: 20_000,

    refetchOnWindowFocus: false,

    enabled:
      modulo === 'estadoCuenta' &&
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,
  })

  const {
    data: dataCobranzas,
    isPending: isPendingCobex,
    isFetched: isFetchedCobex,
    isError: isErrorCobex,
    error: errorCobex,
    refetch: refetchCobex,
    isFetching: isFetchingCobex,
  } = useQuery({
    queryKey: [
      ...NOTIFICACIONES_COBRANZAS_LISTA_QUERY_KEY,
      fechaCaracasApi ?? null,
    ],

    queryFn: () =>
      notificacionService.listarNotificacionesCobranzas(
        undefined,
        fechaCaracasApi
      ),

    staleTime: 20_000,

    refetchOnWindowFocus: false,

    enabled:
      modulo === 'cobranzas' &&
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,
  })

  const {
    data: dataCuotas4Mas,
    isPending: isPendingC4,
    isFetched: isFetchedC4,
    isError: isErrorC4,
    error: errorC4,
    refetch: refetchC4,
    isFetching: isFetchingC4,
  } = useQuery({
    queryKey: [
      ...NOTIFICACIONES_CUOTAS_4_MAS_LISTA_QUERY_KEY,
      fechaCaracasApi ?? null,
    ],

    queryFn: () =>
      notificacionService.listarNotificacionesCuotas4Mas(
        undefined,
        fechaCaracasApi
      ),

    staleTime: 20_000,

    refetchOnWindowFocus: false,

    enabled:
      modulo === 'a4cuotas' &&
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,
  })

  const { data: estadisticasPorTab } = useQuery({
    queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,

    queryFn: () => notificacionService.getEstadisticasPorTab(),

    staleTime: 0,

    enabled:
      activeTab !== 'configuracion' &&
      !pausarAutoRefetchNotificaciones,

    placeholderData: {
      dias_5: { enviados: 0, rebotados: 0 },

      dias_3: { enviados: 0, rebotados: 0 },

      dias_1: { enviados: 0, rebotados: 0 },

      hoy: { enviados: 0, rebotados: 0 },

      dias_1_retraso: { enviados: 0, rebotados: 0 },

      dias_10_retraso: { enviados: 0, rebotados: 0 },

      prejudicial: { enviados: 0, rebotados: 0 },

      cobranzas: { enviados: 0, rebotados: 0 },

      cuotas_4_mas: { enviados: 0, rebotados: 0 },

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

  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)

  const [enviandoPrejudicial, setEnviandoPrejudicial] = useState(false)

  const [enviandoEstadoCuenta, setEnviandoEstadoCuenta] = useState(false)

  const [enviandoCobranzas, setEnviandoCobranzas] = useState(false)
  const [enviandoCuotas4Mas, setEnviandoCuotas4Mas] = useState(false)

  const [enviandoD2Antes, setEnviandoD2Antes] = useState(false)

  const [enviandoPago1Dia, setEnviandoPago1Dia] = useState(false)

  const [enviandoPago10Dias, setEnviandoPago10Dias] = useState(false)

  /** Avance del envío en curso (sondeo heartbeat del servidor). */
  const [envioProgress, setEnvioProgress] = useState<EnvioProgressState | null>(
    null
  )
  /** Cola de reanudacion (dia siguiente): desde / hasta. */
  const [lotesContinuar, setLotesContinuar] = useState<LoteContinuarItem[]>([])
  const envioDesdeRef = useRef(0)

  /** Cola continuar desde API (no depender solo del efecto de reenganche). */
  const { data: ultimoBatchParaContinuar } = useQuery({
    queryKey: [...NOTIFICACIONES_QUERY_KEYS.envioBatchUltimo, 'vista', modulo],
    queryFn: () => notificacionService.obtenerUltimoEnvioBatch(),
    staleTime: 15 * 1000,
    refetchInterval: query => {
      const u = query.state.data?.ultimo as
        | Record<string, unknown>
        | null
        | undefined
      if (!u) return 60_000
      const est = String(u.estado || '')
        .trim()
        .toLowerCase()
      // Solo sondeo frecuente mientras hay lote activo de ESTE modulo.
      if (est === 'en_proceso') {
        const det =
          typeof u.detalles === 'object' && u.detalles !== null
            ? (u.detalles as Record<string, unknown>)
            : null
        const tipoUlt = String(u.tipo_caso || det?.tipo_caso || '').trim()
        const tipoMod = tipoCasoEnvioParaModulo(modulo)
        if (!tipoMod || !tipoUlt || tipoUlt === tipoMod) return 5000
      }
      return 60_000
    },
    refetchOnWindowFocus: true,
  })

  /** Solo el lote de ESTE submodulo (2 cuotas != dia siguiente, etc.). */
  const tipoCasoVista = useMemo(() => {
    // Preferir modulo (a-2-cuotas => PREJUDICIAL) para no perder el indicador
    // si activeTab no mapea (p. ej. configuracion).
    return (
      tipoCasoEnvioParaModulo(modulo) || tipoCasoEnvioParaTab(activeTab, modulo)
    )
  }, [activeTab, modulo])
  const lotesContinuarVista = useMemo(() => {
    const desdeQuery = Array.isArray(ultimoBatchParaContinuar?.lotes_continuar)
      ? (ultimoBatchParaContinuar!.lotes_continuar as LoteContinuarItem[])
      : null
    const raw =
      desdeQuery && desdeQuery.length > 0 ? desdeQuery : lotesContinuar
    if (!tipoCasoVista) return []
    return raw.filter(L => String(L.tipo_caso || '').trim() === tipoCasoVista)
  }, [lotesContinuar, tipoCasoVista, ultimoBatchParaContinuar])
  const enviandoEsteModulo =
    (modulo === 'a2cuotas' && enviandoPrejudicial) ||
    (modulo === 'estadoCuenta' && enviandoEstadoCuenta) ||
    (modulo === 'cobranzas' && enviandoCobranzas) ||
    (modulo === 'a4cuotas' && enviandoCuotas4Mas) ||
    (modulo === 'd2antes' && enviandoD2Antes) ||
    (modulo === 'a1dia' && enviandoPago1Dia) ||
    (modulo === 'a10dias' && enviandoPago10Dias)
  const envioProgressVista = useMemo(() => {
    if (!envioProgress) return null
    // Mientras este modulo envia, siempre mostrar la barra.
    if (enviandoEsteModulo) return envioProgress
    const tc = String(envioProgress.tipo_caso || '').trim()
    if (tipoCasoVista && tc && tc !== tipoCasoVista) return null
    if (tipoCasoVista && tc === tipoCasoVista) return envioProgress
    if (tipoCasoVista && !tc) return envioProgress
    return null
  }, [envioProgress, tipoCasoVista, enviandoEsteModulo])

  useEffect(() => {
    const lc = ultimoBatchParaContinuar?.lotes_continuar
    if (Array.isArray(lc)) {
      setLotesContinuar(lc as LoteContinuarItem[])
    }
  }, [ultimoBatchParaContinuar])

  /** Confirmación en pantalla (sustituye window.confirm: más clara y fiable en Firefox). */
  const [confirmEnvio, setConfirmEnvio] = useState<null | {
    kind:
      | 'prejudicial'
      | 'estadoCuenta'
      | 'cobranzas'
      | 'a4cuotas'
      | 'd2antes'
      | 'pago1dia'
      | 'pago10dias'
    n: number
  }>(null)

  /** Obligatorio si la lista visible tiene 0 filas y aun así se quiere disparar el POST al servidor. */
  const [ackEnvioConListaVacia, setAckEnvioConListaVacia] = useState(false)

  useEffect(() => {
    if (confirmEnvio == null) return
    setAckEnvioConListaVacia(false)
  }, [confirmEnvio])

  /** Abort solo para actualizar listas (no debe cortar el sondeo de envío). */
  const operacionListaAbortRef = useRef<AbortController | null>(null)
  /** Abort solo del seguimiento UI del envío; el lote en servidor sigue. */
  const envioSeguimientoAbortRef = useRef<AbortController | null>(null)
  const envioSeguimientoTokenRef = useRef<string | null>(null)

  const beginOperacionListaAbortable = () => {
    operacionListaAbortRef.current?.abort()
    const c = new AbortController()
    operacionListaAbortRef.current = c
    return c
  }

  const beginEnvioSeguimientoAbortable = () => {
    envioSeguimientoAbortRef.current?.abort()
    const c = new AbortController()
    envioSeguimientoAbortRef.current = c
    return c
  }

  const applyEnvioProgress = (
    p: EnvioProgressState,
    opts?: { fijarDesde?: number; nuevoInicio?: boolean }
  ) => {
    const hasta = p.hasta && p.hasta > 0 ? p.hasta : p.total
    let desde = p.desde
    if (opts?.fijarDesde != null && Number.isFinite(opts.fijarDesde)) {
      envioDesdeRef.current = Math.max(0, opts.fijarDesde)
      desde = envioDesdeRef.current
    } else if (opts?.nuevoInicio) {
      envioDesdeRef.current = Math.max(0, p.procesados)
      desde = envioDesdeRef.current
    } else if (desde == null) {
      desde = envioDesdeRef.current
    } else {
      envioDesdeRef.current = Math.max(0, desde)
    }
    setEnvioProgress(prev => ({
      ...prev,
      ...p,
      desde,
      hasta,
      tipo_caso: p.tipo_caso || prev?.tipo_caso || tipoCasoVista || undefined,
    }))
  }

  const cancelarOperacionListaEmergencia = () => {
    operacionListaAbortRef.current?.abort()
    operacionListaAbortRef.current = null
    envioSeguimientoAbortRef.current?.abort()
    envioSeguimientoAbortRef.current = null
    setActualizandoListas(false)
    setEnviandoPrejudicial(false)
    setEnviandoEstadoCuenta(false)
    setEnviandoCobranzas(false)
    setEnviandoCuotas4Mas(false)
    setEnviandoD2Antes(false)
    setEnviandoPago1Dia(false)
    setEnviandoPago10Dias(false)
    envioDesdeRef.current = 0
    setEnvioProgress(null)
    toast.dismiss()
    void (async () => {
      try {
        const r = await notificacionService.cancelarEnvioBatch()
        toast.success(
          r.mensaje ||
            'Envío cancelado en el servidor. Ya no quedará en limbo; puede continuar el pendiente luego.'
        )
      } catch (e) {
        toast.warning(
          'Se detuvo el seguimiento en pantalla. Si el lote seguía en el servidor, reintente Cancelar.'
        )
        console.error(e)
      }
    })()
  }

  const hayOperacionListaEnCurso =
    actualizandoListas ||
    enviandoPrejudicial ||
    enviandoEstadoCuenta ||
    enviandoCobranzas ||
    enviandoCuotas4Mas ||
    enviandoD2Antes ||
    enviandoPago1Dia ||
    enviandoPago10Dias

  // Si hay un lote en curso en el servidor, reanudar barra de progreso al entrar.
  useEffect(() => {
    let cancelled = false
    const ac = beginEnvioSeguimientoAbortable()
    const poll = async () => {
      try {
        const { ultimo, lotes_continuar } =
          await notificacionService.obtenerUltimoEnvioBatch({
            signal: ac.signal,
          })
        if (Array.isArray(lotes_continuar)) {
          setLotesContinuar(lotes_continuar as LoteContinuarItem[])
        }
        if (cancelled || !ultimo) return
        const estado = String(ultimo.estado || '')
          .trim()
          .toLowerCase()
        const det =
          typeof ultimo.detalles === 'object' && ultimo.detalles !== null
            ? (ultimo.detalles as Record<string, unknown>)
            : null
        const estadoBatch = String(ultimo.estado || '')
          .trim()
          .toLowerCase()
        const detPausa =
          typeof ultimo.detalles === 'object' && ultimo.detalles !== null
            ? (ultimo.detalles as Record<string, unknown>)
            : null
        const pausadoGmail =
          estadoBatch === 'pausado_limite_gmail' ||
          Boolean(detPausa && detPausa.pausado_limite_gmail)
        const canceladoBatch =
          estadoBatch === 'cancelado_usuario' ||
          Boolean(detPausa && detPausa.cancelado_usuario)
        const enProceso = envioBatchSigueActivoUi(ultimo)
        if (canceladoBatch && !enProceso) return
        if (!enProceso && !pausadoGmail) return
        {
          const tipoUlt = String(
            ultimo.tipo_caso || (detPausa && detPausa.tipo_caso) || ''
          ).trim()
          const tipoMod = tipoCasoEnvioParaModulo(modulo)
          if (tipoMod && tipoUlt && tipoUlt !== tipoMod) {
            // Lote de otro submodulo (ej. PREJUDICIAL vs dia siguiente): no reenganchar UI.
            return
          }
        }
        if (pausadoGmail && !enProceso) {
          const totalN = Number(
            ultimo.total_en_lista ?? (detPausa && detPausa.total_en_lista) ?? 0
          )
          const procesadosN = Number(
            (detPausa && detPausa.procesados) ?? ultimo.enviados ?? 0
          )
          applyEnvioProgress(
            {
              procesados: Number.isFinite(procesadosN) ? procesadosN : 0,
              total: Number.isFinite(totalN) ? totalN : 0,
              enviados: Number(ultimo.enviados ?? 0),
              fallidos: Number(ultimo.fallidos ?? 0),
              sin_email: Number(ultimo.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
              tipo_caso: String(ultimo.tipo_caso || ''),
            },
            { nuevoInicio: true }
          )
          toast.info(
            'Hay un lote pausado por cupo diario Gmail; se reanuda al día siguiente. La barra queda visible sin sondeos frecuentes.'
          )
          return
        }
        const tipo = String(
          ultimo.tipo_caso || (det && det.tipo_caso) || ''
        ).trim()
        if (tipo === 'PREJUDICIAL') setEnviandoPrejudicial(true)
        if (tipo === 'ESTADO_CUENTA') setEnviandoEstadoCuenta(true)
        else if (tipo === 'COBRANZAS_EXCEL') setEnviandoCobranzas(true)
        else if (tipo === 'CUOTAS_4_MAS') setEnviandoCuotas4Mas(true)
        else if (tipo === 'PAGO_2_DIAS_ANTES_PENDIENTE')
          setEnviandoD2Antes(true)
        else if (tipo === 'PAGO_1_DIA_ATRASADO') setEnviandoPago1Dia(true)
        else if (tipo === 'PAGO_10_DIAS_ATRASADO') setEnviandoPago10Dias(true)
        const token = String((det && det.token_seguimiento) || '').trim()
        envioSeguimientoTokenRef.current = token || null
        const totalN = Number(
          ultimo.total_en_lista ?? (det && det.total_en_lista) ?? 0
        )
        const procesadosN = Number(
          (det && det.procesados) ?? ultimo.enviados ?? 0
        )
        {
          const tipoKey = String(
            ultimo.tipo_caso || (det && det.tipo_caso) || ''
          ).trim()
          const L = (
            Array.isArray(lotes_continuar) ? lotes_continuar : []
          ).find(
            x =>
              String((x as { tipo_caso?: unknown }).tipo_caso || '') === tipoKey
          ) as { procesados?: unknown } | undefined
          const desdeCola = Number(L?.procesados ?? 0)
          applyEnvioProgress(
            {
              procesados: Number.isFinite(procesadosN) ? procesadosN : 0,
              total: Number.isFinite(totalN) ? totalN : 0,
              enviados: Number(ultimo.enviados ?? 0),
              fallidos: Number(ultimo.fallidos ?? 0),
              sin_email: Number(ultimo.sin_email ?? 0),
              tipo_caso: tipoKey,
            },
            {
              fijarDesde:
                Number.isFinite(desdeCola) && desdeCola > 0 ? desdeCola : 0,
            }
          )
        }
        toast.info(
          'Hay un envío en curso en el servidor; se reanudó el seguimiento en pantalla.'
        )
        const deadline = Date.now() + 3_600_000
        while (!cancelled && Date.now() < deadline) {
          await new Promise<void>(r => window.setTimeout(r, 3000))
          if (cancelled || ac.signal.aborted) break
          const { ultimo: u2 } =
            await notificacionService.obtenerUltimoEnvioBatch({
              signal: ac.signal,
            })
          if (!u2) continue
          const det2 =
            typeof u2.detalles === 'object' && u2.detalles !== null
              ? (u2.detalles as Record<string, unknown>)
              : null
          const token2 = String((det2 && det2.token_seguimiento) || '').trim()
          if (token && token2 && token2 !== token) break
          const est2 = String(u2.estado || '')
            .trim()
            .toLowerCase()
          const sigue = envioBatchSigueActivoUi(u2)
          const total2 = Number(
            u2.total_en_lista ?? (det2 && det2.total_en_lista) ?? 0
          )
          const proc2 = Number((det2 && det2.procesados) ?? u2.enviados ?? 0)
          applyEnvioProgress({
            procesados: Number.isFinite(proc2) ? proc2 : 0,
            total: Number.isFinite(total2) ? total2 : 0,
            enviados: Number(u2.enviados ?? 0),
            fallidos: Number(u2.fallidos ?? 0),
            sin_email: Number(u2.sin_email ?? 0),
          })
          if (!sigue) {
            const estFin = String(u2.estado || '')
              .trim()
              .toLowerCase()
            const pausadoFin =
              estFin === 'pausado_limite_gmail' ||
              Boolean(det2 && det2.pausado_limite_gmail)
            if (pausadoFin) {
              applyEnvioProgress(
                {
                  procesados: Number.isFinite(proc2) ? proc2 : 0,
                  total: Number.isFinite(total2) ? total2 : 0,
                  enviados: Number(u2.enviados ?? 0),
                  fallidos: Number(u2.fallidos ?? 0),
                  sin_email: Number(u2.sin_email ?? 0),
                  estado: 'pausado_limite_gmail',
                },
                { nuevoInicio: true }
              )
              toast.warning(
                `Lote pausado por cupo Gmail: ${Number(u2.enviados ?? 0)} enviados. Reanuda mañana.`
              )
            } else {
              toast.success(
                `Envío en servidor finalizado: ${Number(u2.enviados ?? 0)} enviados.`
              )
              setEnvioProgress(null)
            }
            await queryClient.invalidateQueries({
              queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
            })
            break
          }
        }
      } catch (e) {
        if (!isRequestCanceled(e)) {
          console.error(e)
        }
      } finally {
        if (!cancelled && envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
          setEnviandoPrejudicial(false)
          setEnviandoEstadoCuenta(false)
          setEnviandoCobranzas(false)
          setEnviandoCuotas4Mas(false)
          setEnviandoD2Antes(false)
          setEnviandoPago1Dia(false)
          setEnviandoPago10Dias(false)
          setEnvioProgress(prev =>
            prev && prev.estado === 'pausado_limite_gmail' ? prev : null
          )
        }
      }
    }
    void poll()
    return () => {
      cancelled = true
      if (envioSeguimientoAbortRef.current === ac) {
        ac.abort()
        envioSeguimientoAbortRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const pausado = hayOperacionListaEnCurso
    if (pausarAutoRefetchNotificaciones !== pausado) {
      setPausarAutoRefetchNotificaciones(pausado)
    }
  }, [hayOperacionListaEnCurso, pausarAutoRefetchNotificaciones])

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
        queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_COBRANZAS_LISTA_QUERY_KEY,
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

  const ejecutarEnvioManualTrasConfirmar = async (p: {
    kind:
      | 'prejudicial'
      | 'estadoCuenta'
      | 'cobranzas'
      | 'a4cuotas'
      | 'd2antes'
      | 'pago1dia'
      | 'pago10dias'
    n: number
  }) => {
    const { kind, n } = p

    if (kind === 'prejudicial') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoPrejudicial(true)
      const loadingId = toast.loading(
        'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
      )

      try {
        {
          const L =
            lotesContinuarVista.find(
              x => String(x.tipo_caso || '') === 'PREJUDICIAL'
            ) ||
            lotesContinuar.find(
              x => String(x.tipo_caso || '') === 'PREJUDICIAL'
            )
          const desdeCola = Number(L?.procesados ?? 0)
          applyEnvioProgress(
            {
              procesados: Number.isFinite(desdeCola) ? desdeCola : 0,
              total: n,
              enviados: 0,
              fallidos: 0,
              sin_email: 0,
              tipo_caso: 'PREJUDICIAL',
            },
            {
              fijarDesde:
                Number.isFinite(desdeCola) && desdeCola > 0 ? desdeCola : 0,
            }
          )
        }
        const res = await notificacionService.enviarCasoManual('PREJUDICIAL', {
          signal: ac.signal,
          fechaCaracas: fechaCaracasApi,
          onProgress: p => applyEnvioProgress(p),
        })

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        if (res.pausado_limite_gmail) {
          applyEnvioProgress(
            {
              procesados: Number(res.procesados ?? res.enviados ?? 0),
              total: Number(res.total_en_lista ?? n),
              enviados: Number(res.enviados ?? 0),
              fallidos: Number(res.fallidos ?? 0),
              sin_email: Number(res.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
              tipo_caso: 'PREJUDICIAL',
            },
            { nuevoInicio: true }
          )
        }

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
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise PREJUDICIAL en Configuración y el correo del servidor.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoPrejudicial(false)
        setEnvioProgress(prev =>
          prev && prev.estado === 'pausado_limite_gmail' ? prev : null
        )
      }
      return
    }

    if (kind === 'estadoCuenta') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoEstadoCuenta(true)
      const loadingId = toast.loading(
        'Enviando Estado de cuenta (máx. 600/día)… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote del día.'
      )

      try {
        {
          const L =
            lotesContinuarVista.find(
              x => String(x.tipo_caso || '') === 'ESTADO_CUENTA'
            ) ||
            lotesContinuar.find(
              x => String(x.tipo_caso || '') === 'ESTADO_CUENTA'
            )
          const desdeCola = Number(L?.procesados ?? 0)
          const hastaLista = Math.max(
            n,
            Number(L?.total_en_lista ?? 0) || 0
          )
          applyEnvioProgress(
            {
              procesados: Number.isFinite(desdeCola) ? desdeCola : 0,
              total: hastaLista > 0 ? hastaLista : n,
              enviados: 0,
              fallidos: 0,
              sin_email: 0,
              tipo_caso: 'ESTADO_CUENTA',
              cupo_diario: 600,
              estado: 'en_proceso',
            },
            {
              fijarDesde:
                Number.isFinite(desdeCola) && desdeCola > 0 ? desdeCola : 0,
            }
          )
        }
        const res = await notificacionService.enviarCasoManual('ESTADO_CUENTA', {
          signal: ac.signal,
          fechaCaracas: fechaCaracasApi,
          onProgress: p =>
            applyEnvioProgress({
              ...p,
              tipo_caso: 'ESTADO_CUENTA',
              cupo_diario: p.cupo_diario ?? 600,
            }),
        })

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        if (res.pausado_limite_gmail) {
          applyEnvioProgress(
            {
              procesados: Number(res.procesados ?? res.enviados ?? 0),
              total: Number(
                res.total_en_lista ?? res.total_universo ?? n
              ),
              enviados: Number(res.enviados ?? 0),
              fallidos: Number(res.fallidos ?? 0),
              sin_email: Number(res.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
              tipo_caso: 'ESTADO_CUENTA',
              cupo_diario: Number(res.cupo_diario ?? 600),
              enviados_hoy: Number(res.enviados_hoy ?? 0),
            },
            { nuevoInicio: true }
          )
        }

        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
        })

        await invalidateListasNotificacionesMora(queryClient, {
          skipCrossTabBroadcast: true,
        })

        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_ESTADO_CUENTA_LISTA_QUERY_KEY,
        })
      } catch (e) {
        console.error(e)
        toast.dismiss(loadingId)
        if (isRequestCanceled(e)) {
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise ESTADO_CUENTA en Configuración y la cuenta tucuenta@.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoEstadoCuenta(false)
        setEnvioProgress(prev =>
          prev && prev.estado === 'pausado_limite_gmail' ? prev : null
        )
      }
      return
    }

    if (kind === 'cobranzas') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoCobranzas(true)
      const loadingId = toast.loading(
        'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
      )

      try {
        setEnvioProgress({
          procesados: 0,
          total: n,
          enviados: 0,
          fallidos: 0,
          sin_email: 0,
          tipo_caso: 'COBRANZAS_EXCEL',
        })
        const res = await notificacionService.enviarCasoManual(
          'COBRANZAS_EXCEL',
          {
            signal: ac.signal,
            fechaCaracas: fechaCaracasApi,
            onProgress: p => applyEnvioProgress(p),
          }
        )

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        if (res.pausado_limite_gmail) {
          applyEnvioProgress(
            {
              procesados: Number(res.procesados ?? res.enviados ?? 0),
              total: Number(res.total_en_lista ?? n),
              enviados: Number(res.enviados ?? 0),
              fallidos: Number(res.fallidos ?? 0),
              sin_email: Number(res.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
            },
            { nuevoInicio: true }
          )
        }

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
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise COBRANZAS_EXCEL en Configuración y el correo del servidor.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoCobranzas(false)
        setEnvioProgress(prev =>
          prev && prev.estado === 'pausado_limite_gmail' ? prev : null
        )
      }
      return
    }

    if (kind === 'a4cuotas') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoCuotas4Mas(true)
      const loadingId = toast.loading(
        'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
      )

      try {
        setEnvioProgress({
          procesados: 0,
          total: n,
          enviados: 0,
          fallidos: 0,
          sin_email: 0,
          tipo_caso: 'CUOTAS_4_MAS',
        })
        const res = await notificacionService.enviarCasoManual('CUOTAS_4_MAS', {
          signal: ac.signal,
          fechaCaracas: fechaCaracasApi,
          onProgress: p => applyEnvioProgress(p),
        })

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        if (res.pausado_limite_gmail) {
          applyEnvioProgress(
            {
              procesados: Number(res.procesados ?? res.enviados ?? 0),
              total: Number(res.total_en_lista ?? n),
              enviados: Number(res.enviados ?? 0),
              fallidos: Number(res.fallidos ?? 0),
              sin_email: Number(res.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
            },
            { nuevoInicio: true }
          )
        }

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
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise CUOTAS_4_MAS en Configuración y el correo del servidor.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoCuotas4Mas(false)
        setEnvioProgress(prev =>
          prev && prev.estado === 'pausado_limite_gmail' ? prev : null
        )
      }
      return
    }

    if (kind === 'd2antes') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoD2Antes(true)
      const loadingId = toast.loading(
        'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
      )

      try {
        {
          const L =
            lotesContinuarVista.find(
              x =>
                String(x.tipo_caso || '') === 'PAGO_2_DIAS_ANTES_PENDIENTE'
            ) ||
            lotesContinuar.find(
              x =>
                String(x.tipo_caso || '') === 'PAGO_2_DIAS_ANTES_PENDIENTE'
            )
          const desdeCola = Number(L?.procesados ?? 0)
          applyEnvioProgress(
            {
              procesados: Number.isFinite(desdeCola) ? desdeCola : 0,
              total: n,
              enviados: 0,
              fallidos: 0,
              sin_email: 0,
              omitidos: 0,
              estado: 'enviando',
              tipo_caso: 'PAGO_2_DIAS_ANTES_PENDIENTE',
            },
            {
              fijarDesde:
                Number.isFinite(desdeCola) && desdeCola > 0 ? desdeCola : 0,
            }
          )
        }
        const res = await notificacionService.enviarCasoManual(
          'PAGO_2_DIAS_ANTES_PENDIENTE',
          {
            signal: ac.signal,
            fechaCaracas: fechaCaracasApi,
            onProgress: p => applyEnvioProgress(p),
          }
        )

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        applyEnvioProgress(
          {
            procesados: Number(res.procesados ?? res.enviados ?? 0),
            total: Number(res.total_en_lista ?? n),
            enviados: Number(res.enviados ?? 0),
            fallidos: Number(res.fallidos ?? 0),
            sin_email: Number(res.sin_email ?? 0),
            omitidos: omitidosDesdeEnvioRes(res),
            estado: res.pausado_limite_gmail
              ? 'pausado_limite_gmail'
              : res.cancelado_usuario
                ? 'cancelado_usuario'
                : 'finalizado',
            tipo_caso: 'PAGO_2_DIAS_ANTES_PENDIENTE',
          },
          res.pausado_limite_gmail || res.cancelado_usuario
            ? { nuevoInicio: true }
            : undefined
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
        toast.dismiss(loadingId)
        if (isRequestCanceled(e)) {
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise PAGO_2_DIAS_ANTES_PENDIENTE en Configuración.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoD2Antes(false)
        setEnvioProgress(prev =>
          prev &&
          (prev.estado === 'pausado_limite_gmail' ||
            prev.estado === 'finalizado' ||
            prev.estado === 'cancelado_usuario')
            ? prev
            : null
        )
      }
      return
    }

    if (kind === 'pago10dias') {
      const ac = beginEnvioSeguimientoAbortable()
      setEnviandoPago10Dias(true)
      const loadingId = toast.loading(
        'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
      )

      try {
        setEnvioProgress({
          procesados: 0,
          total: n,
          enviados: 0,
          fallidos: 0,
          sin_email: 0,
          tipo_caso: 'PAGO_10_DIAS_ATRASADO',
        })
        const res = await notificacionService.enviarCasoManual(
          'PAGO_10_DIAS_ATRASADO',
          {
            signal: ac.signal,
            fechaCaracas: fechaCaracasApi,
            onProgress: p => applyEnvioProgress(p),
          }
        )

        toast.dismiss(loadingId)
        toastResultadoEnvioNotificaciones(res, n)
        if (res.pausado_limite_gmail) {
          applyEnvioProgress(
            {
              procesados: Number(res.procesados ?? res.enviados ?? 0),
              total: Number(res.total_en_lista ?? n),
              enviados: Number(res.enviados ?? 0),
              fallidos: Number(res.fallidos ?? 0),
              sin_email: Number(res.sin_email ?? 0),
              estado: 'pausado_limite_gmail',
            },
            { nuevoInicio: true }
          )
        }

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
          toast.info(
            'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
          )
          return
        }

        toastErrorTrasEnvioManual(
          e,
          'Revise PAGO_10_DIAS_ATRASADO en Configuración y el correo del servidor.'
        )
      } finally {
        if (envioSeguimientoAbortRef.current === ac) {
          envioSeguimientoAbortRef.current = null
        }
        setEnviandoPago10Dias(false)
        setEnvioProgress(prev =>
          prev && prev.estado === 'pausado_limite_gmail' ? prev : null
        )
      }
      return
    }

    const ac = beginEnvioSeguimientoAbortable()
    setEnviandoPago1Dia(true)
    const loadingId = toast.loading(
      'Enviando correos en el servidor… puede tardar varios minutos. Puede cerrar o cambiar de menú: el envío sigue hasta completar el lote.'
    )

    try {
      {
        const L =
          lotesContinuarVista.find(
            x => String(x.tipo_caso || '') === 'PAGO_1_DIA_ATRASADO'
          ) ||
          lotesContinuar.find(
            x => String(x.tipo_caso || '') === 'PAGO_1_DIA_ATRASADO'
          )
        const desdeCola = Number(L?.procesados ?? 0)
        applyEnvioProgress(
          {
            procesados: Number.isFinite(desdeCola) ? desdeCola : 0,
            total: n,
            enviados: 0,
            fallidos: 0,
            sin_email: 0,
            omitidos: 0,
            estado: 'enviando',
            tipo_caso: 'PAGO_1_DIA_ATRASADO',
          },
          {
            fijarDesde:
              Number.isFinite(desdeCola) && desdeCola > 0 ? desdeCola : 0,
          }
        )
      }
      const res = await notificacionService.enviarCasoManual(
        'PAGO_1_DIA_ATRASADO',
        {
          signal: ac.signal,
          fechaCaracas: fechaCaracasApi,
          onProgress: p => applyEnvioProgress(p),
        }
      )

      toast.dismiss(loadingId)
      toastResultadoEnvioNotificaciones(res, n)
      applyEnvioProgress(
        {
          procesados: Number(res.procesados ?? res.enviados ?? 0),
          total: Number(res.total_en_lista ?? n),
          enviados: Number(res.enviados ?? 0),
          fallidos: Number(res.fallidos ?? 0),
          sin_email: Number(res.sin_email ?? 0),
          omitidos: omitidosDesdeEnvioRes(res),
          estado: res.pausado_limite_gmail
            ? 'pausado_limite_gmail'
            : res.cancelado_usuario
              ? 'cancelado_usuario'
              : 'finalizado',
          tipo_caso: 'PAGO_1_DIA_ATRASADO',
        },
        res.pausado_limite_gmail || res.cancelado_usuario
          ? { nuevoInicio: true }
          : undefined
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
      toast.dismiss(loadingId)
      if (isRequestCanceled(e)) {
        toast.info(
          'Seguimiento detenido en pantalla. El servidor sigue enviando hasta terminar el lote.'
        )
        return
      }

      toastErrorTrasEnvioManual(
        e,
        'Revise PAGO_1_DIA_ATRASADO en Configuración y el correo del servidor.'
      )
    } finally {
      if (envioSeguimientoAbortRef.current === ac) {
        envioSeguimientoAbortRef.current = null
      }
      setEnviandoPago1Dia(false)
      setEnvioProgress(prev =>
        prev &&
        (prev.estado === 'pausado_limite_gmail' ||
          prev.estado === 'finalizado' ||
          prev.estado === 'cancelado_usuario')
          ? prev
          : null
      )
    }
  }

  const solicitarConfirmacionEnvioPrejudicial = () => {
    if (modulo !== 'a2cuotas') return
    const n = dataPrejudicial?.items?.length ?? 0
    setConfirmEnvio({ kind: 'prejudicial', n })
  }

  const solicitarConfirmacionEnvioEstadoCuenta = () => {
    if (modulo !== 'estadoCuenta') return
    const n = dataEstadoCuenta?.items?.length ?? 0
    setConfirmEnvio({ kind: 'estadoCuenta', n })
  }

  const solicitarConfirmacionEnvioCobranzas = () => {
    if (modulo !== 'cobranzas') return
    const n = dataCobranzas?.items?.length ?? 0
    setConfirmEnvio({ kind: 'cobranzas', n })
  }

  const solicitarConfirmacionEnvioCuotas4Mas = () => {
    if (modulo !== 'a4cuotas') return
    const n = dataCuotas4Mas?.items?.length ?? 0
    setConfirmEnvio({ kind: 'a4cuotas', n })
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
    if (modulo === 'a2cuotas') {
      if (activeTab !== 'prejudicial') return []
      return dataPrejudicial?.items ?? []
    }

    if (modulo === 'estadoCuenta') {
      if (activeTab !== 'estado_cuenta') return []
      return dataEstadoCuenta?.items ?? []
    }

    if (modulo === 'cobranzas') {
      if (activeTab !== 'cobranzas') return []
      return dataCobranzas?.items ?? []
    }

    if (modulo === 'a4cuotas') {
      if (activeTab !== 'cuotas_4_mas') return []
      return dataCuotas4Mas?.items ?? []
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
    dataEstadoCuenta?.items,
    dataCobranzas?.items,
    dataCuotas4Mas?.items,
    dataD2Antes?.items,
  ])

  const destinosD2 = useMemo(() => {
    if (modulo !== 'd2antes') return null
    const titulares = new Set<string>()
    for (const r of list) {
      const k = String(r.cedula || r.cliente_id || '').trim()
      if (k) titulares.add(k)
    }
    return { filas: list.length, titulares: titulares.size }
  }, [modulo, list])

  /** Cupo diario ESTADO_CUENTA (tope 600 Caracas): cuántos salen si se pulsa Enviar hoy. */
  const cupoEstadoCuenta = useMemo(() => {
    if (modulo !== 'estadoCuenta') return null
    const total = Number(
      dataEstadoCuenta?.total ?? dataEstadoCuenta?.items?.length ?? 0
    )
    const maxDiarios = Number(
      dataEstadoCuenta?.max_diarios ??
        dataEstadoCuenta?.cursor?.max_diarios ??
        600
    )
    const enviadosHoy = Number(
      dataEstadoCuenta?.enviados_hoy ??
        dataEstadoCuenta?.cursor?.enviados_hoy ??
        0
    )
    const cupoRestante = Number(
      dataEstadoCuenta?.cupo_restante ??
        dataEstadoCuenta?.cursor?.cupo_restante ??
        Math.max(0, maxDiarios - (Number.isFinite(enviadosHoy) ? enviadosHoy : 0))
    )
    const previstosRaw = dataEstadoCuenta?.envios_hoy_previstos
    const hoyPrevistos =
      previstosRaw != null && Number.isFinite(Number(previstosRaw))
        ? Math.max(0, Number(previstosRaw))
        : Math.min(
            Number.isFinite(cupoRestante) ? cupoRestante : 0,
            Number.isFinite(total) ? total : 0
          )
    return {
      total: Number.isFinite(total) ? total : 0,
      maxDiarios: Number.isFinite(maxDiarios) && maxDiarios > 0 ? maxDiarios : 600,
      enviadosHoy: Number.isFinite(enviadosHoy) ? Math.max(0, enviadosHoy) : 0,
      cupoRestante: Number.isFinite(cupoRestante)
        ? Math.max(0, cupoRestante)
        : 0,
      hoyPrevistos: Number.isFinite(hoyPrevistos) ? Math.max(0, hoyPrevistos) : 0,
    }
  }, [modulo, dataEstadoCuenta])

  const destinosA1 = useMemo(() => {
    if (modulo !== 'a1dia') return null
    const titulares = new Set<string>()
    for (const r of list) {
      const k = String(r.cedula || r.cliente_id || '').trim()
      if (k) titulares.add(k)
    }
    return { filas: list.length, titulares: titulares.size }
  }, [modulo, list])

  const [sortCol, setSortCol] = useState<NotificacionesCuotasSortCol | null>(
    null
  )

  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const [paginaPorTab, setPaginaPorTab] = useState<
    Partial<Record<TabId, number>>
  >({})

  const [filtroCedula, setFiltroCedula] = useState('')

  useEffect(() => {
    setFiltroCedula('')
  }, [activeTab, modulo, fechaCaracasApi])

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

  /** Siempre partir de `sortedList`: con `sortCol` null es idéntico a `list`; en tabla compacta permite ordenar por diferencia abono. */
  const listaBasePaginacion = sortedList

  const listaTrasFiltroCedula = useMemo(() => {
    const q = filtroCedula.trim()
    if (!q) return listaBasePaginacion
    return listaBasePaginacion.filter(row =>
      filaCoincideFiltroCedulaNotif(row, q)
    )
  }, [listaBasePaginacion, filtroCedula])

  const listaFiltradaCedula = listaTrasFiltroCedula

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
    modulo === 'a1dia' || modulo === 'a10dias'
      ? isPending
      : modulo === 'a2cuotas'
        ? isPendingPrej
        : modulo === 'estadoCuenta'
          ? isPendingEstadoCuenta
          : modulo === 'cobranzas'
            ? isPendingCobex
            : modulo === 'a4cuotas'
              ? isPendingC4
              : isPendingD2

  /**
   * No deshabilitar «Enviar notificaciones (manual)» durante refetch en segundo plano
   * (staleTime 0 + refocus + intervalo 30s): solo hasta la primera respuesta de la lista.
   * Si el GET de la lista falló (isError), no bloquear envío: el servidor puede armar la lista al enviar.
   */
  const esperandoPrimeraCargaLista =
    ((modulo === 'a1dia' || modulo === 'a10dias') &&
      isPending &&
      !isFetched &&
      !isError) ||
    (modulo === 'a2cuotas' &&
      isPendingPrej &&
      !isFetchedPrej &&
      !isErrorPrej) ||
    (modulo === 'estadoCuenta' &&
      isPendingEstadoCuenta &&
      !isFetchedEstadoCuenta &&
      !isErrorEstadoCuenta) ||
    (modulo === 'cobranzas' &&
      isPendingCobex &&
      !isFetchedCobex &&
      !isErrorCobex) ||
    (modulo === 'a4cuotas' && isPendingC4 && !isFetchedC4 && !isErrorC4) ||
    (modulo === 'd2antes' && isPendingD2 && !isFetchedD2 && !isErrorD2)

  const isErrorLista =
    modulo === 'a1dia' || modulo === 'a10dias'
      ? isError
      : modulo === 'a2cuotas'
        ? isErrorPrej
        : modulo === 'estadoCuenta'
          ? isErrorEstadoCuenta
          : modulo === 'cobranzas'
            ? isErrorCobex
            : modulo === 'a4cuotas'
              ? isErrorC4
              : isErrorD2

  const errorLista =
    modulo === 'a1dia' || modulo === 'a10dias'
      ? error
      : modulo === 'a2cuotas'
        ? errorPrej
        : modulo === 'estadoCuenta'
          ? errorEstadoCuenta
          : modulo === 'cobranzas'
            ? errorCobex
            : modulo === 'a4cuotas'
              ? errorC4
              : errorD2

  const refetchLista =
    modulo === 'a1dia' || modulo === 'a10dias'
      ? refetch
      : modulo === 'a2cuotas'
        ? refetchPrej
        : modulo === 'estadoCuenta'
          ? refetchEstadoCuenta
          : modulo === 'cobranzas'
            ? refetchCobex
            : modulo === 'a4cuotas'
              ? refetchC4
              : refetchD2

  const isFetchingLista =
    modulo === 'a1dia' || modulo === 'a10dias'
      ? isFetching
      : modulo === 'a2cuotas'
        ? isFetchingPrej
        : modulo === 'estadoCuenta'
          ? isFetchingEstadoCuenta
          : modulo === 'cobranzas'
            ? isFetchingCobex
            : modulo === 'a4cuotas'
              ? isFetchingC4
              : isFetchingD2

  const isFetchedLista =
    modulo === 'a1dia' || modulo === 'a10dias'
      ? isFetched
      : modulo === 'a2cuotas'
        ? isFetchedPrej
        : modulo === 'cobranzas'
          ? isFetchedCobex
          : modulo === 'a4cuotas'
            ? isFetchedC4
            : isFetchedD2

  const listaCargadaSinFilas =
    !isErrorLista && !isLoadingLista && isFetchedLista && list.length === 0

  const statTabKey = tipoParaKpiYRebotados(activeTab)

  const controlFechaReferenciaCaracas = (
    <div className="flex max-w-full flex-col gap-1 rounded-md border border-gray-200 bg-gray-50/90 px-2 py-1.5 sm:flex-row sm:items-center sm:gap-2">
      <label
        htmlFor="fc-notificaciones-caracas"
        className="text-xs font-medium text-gray-600 sm:whitespace-nowrap"
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
          title="Fecha de referencia (America/Caracas)"
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

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title={pageTitle}
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
                disabled={!hayOperacionListaEnCurso && !envioProgressVista}
                onClick={cancelarOperacionListaEmergencia}
                title="Cancelar"
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>
          }
        />

        {envioProgressVista ? (
          <div className="w-full max-w-2xl">
            <EnvioNotificacionesProgressBar progress={envioProgressVista} />
          </div>
        ) : null}

        {lotesContinuarVista.length > 0 ? (
          <div className="w-full">
            <LoteContinuarIndicador lotes={lotesContinuarVista} />
          </div>
        ) : null}

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
                    : modulo === 'cobranzas'
                      ? 'solo_cobranzas'
                      : modulo === 'a4cuotas'
                        ? 'solo_cuotas_4_mas'
                        : modulo === 'estadoCuenta'
                          ? 'solo_estado_cuenta'
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
                disabled={!hayOperacionListaEnCurso && !envioProgress}
                onClick={cancelarOperacionListaEmergencia}
                title="Cancelar"
              >
                <X className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </div>
          }
        />
      </motion.div>

      <div className="border-b border-gray-200">
        <nav
          role="tablist"
          aria-label="Vistas del submódulo de notificaciones"
          className="flex flex-wrap gap-1"
        >
            {TABS.map(tab => {
              const count =
                tab.id === 'configuracion'
                  ? 0
                  : tab.id === 'prejudicial'
                    ? (dataPrejudicial?.items?.length ?? 0)
                    : tab.id === 'estado_cuenta'
                      ? (dataEstadoCuenta?.items?.length ?? 0)
                      : tab.id === 'cobranzas'
                        ? (dataCobranzas?.items?.length ?? 0)
                        : tab.id === 'cuotas_4_mas'
                          ? (dataCuotas4Mas?.items?.length ?? 0)
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
        </nav>
      </div>

      <div
        role="tabpanel"
        id="notif-panel-principal"
        aria-labelledby={`notif-tab-${activeTab}`}
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
                {modulo === 'a2cuotas'
                  ? '2 cuotas o mas'
                  : modulo === 'estadoCuenta'
                    ? 'Estado de cuenta'
                    : modulo === 'cobranzas'
                    ? 'Cobranzas'
                    : modulo === 'a4cuotas'
                      ? '4 cuotas y más'
                      : modulo === 'd2antes'
                        ? '3 días antes'
                        : modulo === 'a10dias'
                          ? '1 Cuota'
                          : 'Día siguiente al vencimiento'}
              </CardTitle>

              {fechaCaracasApi ? (
                <CardDescription>
                  <span className="font-medium text-amber-800">
                    Referencia: {fechaCaracasApi} (America/Caracas)
                  </span>
                </CardDescription>
              ) : null}
              {modulo === 'estadoCuenta' && cupoEstadoCuenta ? (
                <CardDescription className="mt-2 space-y-1">
                  <span className="block font-semibold text-slate-900">
                    Hoy enviará {cupoEstadoCuenta.hoyPrevistos}
                    <span className="font-normal text-slate-600">
                      {' '}
                      · lista {cupoEstadoCuenta.total} · enviados hoy{' '}
                      {cupoEstadoCuenta.enviadosHoy}/
                      {cupoEstadoCuenta.maxDiarios} · cupo restante{' '}
                      {cupoEstadoCuenta.cupoRestante}
                    </span>
                  </span>
                  <span className="block text-slate-600">
                    Plantilla:{' '}
                    <span className="font-medium text-slate-900">
                      {dataEstadoCuenta?.plantilla?.nombre ||
                        'Estado de cuenta'}
                    </span>
                    {dataEstadoCuenta?.plantilla?.id
                      ? ` (#${dataEstadoCuenta.plantilla.id})`
                      : ''}
                    {' · '}
                    PDF estado de cuenta:{' '}
                    <span className="font-medium text-emerald-800">
                      adjunto al enviar
                    </span>
                  </span>
                </CardDescription>
              ) : null}
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
                    enviandoEstadoCuenta ||
                    enviandoCobranzas ||
                    enviandoCuotas4Mas ||
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


                {modulo === 'a1dia' && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={solicitarConfirmacionEnvioPago1Dia}
                    disabled={enviandoPago1Dia || esperandoPrimeraCargaLista}
                    title={
                      esperandoPrimeraCargaLista
                        ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                        : destinosA1
                          ? `${destinosA1.filas} fila(s) de día siguiente. El lote también envía 2 Cuotas / 1 Cuota / 3 días antes a esos titulares si califican.`
                          : undefined
                    }
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Mail
                      className={`mr-2 h-4 w-4 ${enviandoPago1Dia ? 'animate-pulse' : ''}`}
                    />
                    {enviandoPago1Dia
                      ? 'Enviando...'
                      : destinosA1 && destinosA1.filas > 0
                        ? `Enviar día siguiente (${destinosA1.filas})`
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

                {modulo === 'a2cuotas' && (
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

                {modulo === 'estadoCuenta' && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={solicitarConfirmacionEnvioEstadoCuenta}
                    disabled={
                      enviandoEstadoCuenta || esperandoPrimeraCargaLista
                    }
                    title={
                      esperandoPrimeraCargaLista
                        ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                        : cupoEstadoCuenta
                          ? `Hoy: ${cupoEstadoCuenta.hoyPrevistos} (lista ${cupoEstadoCuenta.total}; cupo ${cupoEstadoCuenta.cupoRestante}/${cupoEstadoCuenta.maxDiarios}).`
                          : 'Máximo 600 correos por día (America/Caracas); continúa mañana desde el cursor.'
                    }
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Mail
                      className={`mr-2 h-4 w-4 ${enviandoEstadoCuenta ? 'animate-pulse' : ''}`}
                    />
                    {enviandoEstadoCuenta
                      ? 'Enviando...'
                      : cupoEstadoCuenta
                        ? `Enviar hoy: ${cupoEstadoCuenta.hoyPrevistos} (cupo ${cupoEstadoCuenta.cupoRestante}/${cupoEstadoCuenta.maxDiarios})`
                        : 'Enviar Estado de cuenta (máx. 600/día)'}
                  </Button>
                )}

                {modulo === 'cobranzas' && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={solicitarConfirmacionEnvioCobranzas}
                    disabled={enviandoCobranzas || esperandoPrimeraCargaLista}
                    title={
                      esperandoPrimeraCargaLista
                        ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                        : undefined
                    }
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Mail
                      className={`mr-2 h-4 w-4 ${enviandoCobranzas ? 'animate-pulse' : ''}`}
                    />
                    {enviandoCobranzas
                      ? 'Enviando…'
                      : 'Enviar notificaciones Cobranzas'}
                  </Button>
                )}

                {modulo === 'a4cuotas' && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={solicitarConfirmacionEnvioCuotas4Mas}
                    disabled={enviandoCuotas4Mas || esperandoPrimeraCargaLista}
                    title={
                      esperandoPrimeraCargaLista
                        ? 'Espere a que termine de cargar la lista (o revise si hay error arriba).'
                        : undefined
                    }
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Mail
                      className={`mr-2 h-4 w-4 ${enviandoCuotas4Mas ? 'animate-pulse' : ''}`}
                    />
                    {enviandoCuotas4Mas
                      ? 'Enviando…'
                      : 'Enviar notificaciones 4 cuotas y más'}
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
                        : destinosD2
                          ? `${destinosD2.filas} correo(s): 1 por fila/préstamo. Quien ya recibió hoy se omite; nadie elegible queda fuera.`
                          : undefined
                    }
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    <Mail
                      className={`mr-2 h-4 w-4 ${enviandoD2Antes ? 'animate-pulse' : ''}`}
                    />
                    {enviandoD2Antes
                      ? 'Enviando...'
                      : destinosD2 && destinosD2.filas > 0
                        ? `Enviar ${destinosD2.filas} correo${destinosD2.filas === 1 ? '' : 's'} (3 días antes)`
                        : 'Enviar notificaciones (manual)'}
                  </Button>
                )}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="border-red-400 text-red-800 hover:bg-red-50"
                  disabled={!hayOperacionListaEnCurso && !envioProgressVista}
                  onClick={cancelarOperacionListaEmergencia}
                  title="Cancelar"
                >
                  <X className="mr-2 h-4 w-4" />
                  Cancelar
                </Button>
              </div>

              {modulo === 'a1dia' && destinosA1 && !envioProgressVista ? (
                <p className="mb-3 text-xs text-gray-600">
                  <strong className="tabular-nums">{destinosA1.filas}</strong>{' '}
                  fila{destinosA1.filas === 1 ? '' : 's'} de día siguiente
                  {destinosA1.titulares !== destinosA1.filas
                    ? ` · ${destinosA1.titulares} titulares`
                    : ''}
                  {' '}
                  (1 correo por préstamo). El lote también envía 2 Cuotas, 1
                  Cuota y 3 días antes a esos mismos titulares si califican; el
                  total de correos puede ser mayor. Corre en segundo plano hasta
                  terminar.
                </p>
              ) : null}

              {modulo === 'd2antes' && destinosD2 && !envioProgressVista ? (
                <p className="mb-3 text-xs text-gray-600">
                  <strong className="tabular-nums">{destinosD2.filas}</strong>{' '}
                  correo{destinosD2.filas === 1 ? '' : 's'} a enviar
                  {destinosD2.titulares !== destinosD2.filas
                    ? ` · ${destinosD2.titulares} titulares (1 correo por préstamo)`
                    : ' (1 correo por fila / préstamo)'}
                  . El lote recorre toda la lista; ya enviados hoy se omiten, no
                  se excluye a nadie elegible.
                </p>
              ) : null}

              {envioProgressVista ? (
                <div className="mb-4 w-full max-w-2xl">
                  <EnvioNotificacionesProgressBar
                    progress={envioProgressVista}
                  />
                  {lotesContinuarVista[0]?.fecha_negocio_inicio ? (
                    <p className="mt-1 text-[11px] text-sky-900/90">
                      Omite OK ya enviados desde{' '}
                      <strong>
                        {String(lotesContinuarVista[0].fecha_negocio_inicio)}
                      </strong>{' '}
                      (inicio de campana). Punto guardado:{' '}
                      <strong>
                        {Number(lotesContinuarVista[0].procesados ?? 0)}
                      </strong>
                      /
                      <strong>
                        {Number(lotesContinuarVista[0].total_en_lista ?? 0)}
                      </strong>
                      .
                    </p>
                  ) : null}
                </div>
              ) : null}

              {lotesContinuarVista.length > 0 ? (
                <div className="mb-4 w-full">
                  <LoteContinuarIndicador lotes={lotesContinuarVista} />
                </div>
              ) : null}

              {pausarAutoRefetchNotificaciones ? (
                <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Refresco automático pausado por operación en curso. Se reanuda
                  al finalizar.
                </div>
              ) : null}

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
                {filtroCedula.trim() && list.length > 0 ? (
                  <p className="text-xs text-muted-foreground sm:ml-auto">
                    Mostrando{' '}
                    <span className="font-semibold tabular-nums text-foreground">
                      {listaFiltradaCedula.length}
                    </span>{' '}
                    de <span className="tabular-nums">{list.length}</span> filas
                  </p>
                ) : null}
              </div>

              {/* KPIs por pestaña: correos enviados y rebotados */}

              {(activeTab as TabId) !== 'configuracion' &&
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

                    <div className="flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="h-8 w-8 shrink-0 text-red-600" />

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

                      {statTabKey ? (
                        <div className="flex flex-wrap items-end gap-2">
                          <div className="flex flex-col gap-0.5">
                            <label
                              htmlFor="rebotados-desde"
                              className="text-[11px] font-medium text-red-800"
                            >
                              Desde
                            </label>
                            <input
                              id="rebotados-desde"
                              type="date"
                              value={rebotadosDesde}
                              onChange={e => setRebotadosDesde(e.target.value)}
                              className="rounded border border-red-300 bg-white px-2 py-1 text-sm text-gray-900"
                            />
                          </div>
                          <div className="flex flex-col gap-0.5">
                            <label
                              htmlFor="rebotados-hasta"
                              className="text-[11px] font-medium text-red-800"
                            >
                              Hasta
                            </label>
                            <input
                              id="rebotados-hasta"
                              type="date"
                              value={rebotadosHasta}
                              onChange={e => setRebotadosHasta(e.target.value)}
                              className="rounded border border-red-300 bg-white px-2 py-1 text-sm text-gray-900"
                            />
                          </div>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="gap-1.5 border-red-300 bg-white text-red-800 hover:bg-red-100"
                            disabled={descargandoAuditoriaCorreos}
                            title="Sin fechas = todos los rebotados del KPI. Con desde/hasta = solo ese rango."
                            onClick={() => {
                              if (!statTabKey) return
                              const tieneDesde = Boolean(rebotadosDesde)
                              const tieneHasta = Boolean(rebotadosHasta)
                              if (tieneDesde !== tieneHasta) {
                                toast.error(
                                  'Indique ambas fechas o déjelas vacías para exportar todos (KPI).'
                                )
                                return
                              }
                              if (
                                tieneDesde &&
                                tieneHasta &&
                                rebotadosDesde > rebotadosHasta
                              ) {
                                toast.error(
                                  'La fecha desde no puede ser posterior a hasta.'
                                )
                                return
                              }
                              setDescargandoAuditoriaCorreos(true)
                              void notificacionService
                                .descargarAuditoriaCorreosRebotadosExcel({
                                  tipo: String(statTabKey),
                                  ...(tieneDesde && tieneHasta
                                    ? {
                                        fechaDesde: rebotadosDesde,
                                        fechaHasta: rebotadosHasta,
                                      }
                                    : {}),
                                })
                                .then(() => {
                                  toast.success(
                                    tieneDesde
                                      ? 'Auditoria de correos descargada (rango de fechas).'
                                      : 'Auditoria de correos descargada (todos, como el KPI).'
                                  )
                                })
                                .catch((err: unknown) => {
                                  toast.error(
                                    getErrorMessage(err) ||
                                      'No se pudo descargar el Excel.'
                                  )
                                })
                                .finally(() => {
                                  setDescargandoAuditoriaCorreos(false)
                                })
                            }}
                          >
                            {descargandoAuditoriaCorreos ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <Download className="h-4 w-4" />
                            )}
                            Auditoria de correos
                          </Button>
                        </div>
                      ) : null}
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
                              colSpan={9}
                              className="py-8 text-center text-gray-500"
                            >
                              <span className="block font-medium text-gray-600">
                                {listaCargadaSinFilas
                                  ? 'Ningún registro en este criterio.'
                                  : filtroCedula.trim()
                                    ? 'Ninguna fila coincide con la cédula indicada.'
                                    : 'Ningún registro en este criterio.'}
                              </span>
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

                          <th className="px-3 py-2 text-left font-semibold">
                            Nombre
                          </th>

                          <th className="px-3 py-2 text-left font-semibold">
                            Cédula
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
                              colSpan={5}
                              className="py-8 text-center text-gray-500"
                            >
                              <span className="block font-medium text-gray-600">
                                {listaCargadaSinFilas
                                  ? 'Ningún cliente en este criterio.'
                                  : filtroCedula.trim()
                                    ? 'Ninguna fila coincide con la cédula indicada.'
                                    : 'Ningún cliente en este criterio.'}
                              </span>
                              {filtroCedula.trim() && !listaCargadaSinFilas ? (
                                <span className="mx-auto mt-2 block max-w-md text-xs text-gray-500">
                                  Ajuste el filtro o use «Limpiar filtro».
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

                              <td className="px-3 py-2 font-medium">
                                {row.nombre}
                              </td>

                              <td className="px-3 py-2">{row.cedula}</td>




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
                        {NOTIFICACIONES_MAX_CLIENTES_POR_PAGINA} por página;
                        cada pestaña guarda su página)
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
              <p>
                {confirmEnvio == null
                  ? null
                  : confirmEnvio.kind === 'estadoCuenta' && cupoEstadoCuenta
                    ? cupoEstadoCuenta.hoyPrevistos === 0
                      ? cupoEstadoCuenta.cupoRestante <= 0
                        ? `Cupo del día agotado (${cupoEstadoCuenta.enviadosHoy}/${cupoEstadoCuenta.maxDiarios}). Lista: ${cupoEstadoCuenta.total}.`
                        : `Hoy enviará 0. Lista: ${cupoEstadoCuenta.total}.`
                      : `¿Enviar hoy ${cupoEstadoCuenta.hoyPrevistos} de ${cupoEstadoCuenta.total} (cupo ${cupoEstadoCuenta.cupoRestante}/${cupoEstadoCuenta.maxDiarios})?`
                    : confirmEnvio.n === 0
                      ? 'Lista vacía (0 filas).'
                      : `¿Enviar ${confirmEnvio.n} notificación${confirmEnvio.n === 1 ? '' : 'es'}?`}
              </p>

              {confirmEnvio != null &&
              ((confirmEnvio.kind === 'estadoCuenta' &&
                cupoEstadoCuenta &&
                cupoEstadoCuenta.hoyPrevistos === 0) ||
                (confirmEnvio.kind !== 'estadoCuenta' &&
                  confirmEnvio.n === 0)) ? (
                <label className="flex cursor-pointer items-start gap-2 rounded-md border border-amber-200 bg-amber-50/90 p-3 text-gray-800">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 shrink-0 rounded border-gray-300 accent-blue-600"
                    checked={ackEnvioConListaVacia}
                    onChange={e => setAckEnvioConListaVacia(e.target.checked)}
                  />
                  <span>
                    {confirmEnvio.kind === 'estadoCuenta'
                      ? 'Confirmo disparar el envío aunque hoy sean 0.'
                      : 'Confirmo enviar con lista vacía (0 filas).'}
                  </span>
                </label>
              ) : null}
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
                ((confirmEnvio.kind === 'estadoCuenta' &&
                  cupoEstadoCuenta != null &&
                  cupoEstadoCuenta.hoyPrevistos === 0 &&
                  !ackEnvioConListaVacia) ||
                  (confirmEnvio.kind !== 'estadoCuenta' &&
                    confirmEnvio.n === 0 &&
                    !ackEnvioConListaVacia))
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
