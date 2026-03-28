import { useState, useEffect, useMemo } from 'react'

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
  emailConfigService,
  type ClientesRetrasadosResponse,
  type ClienteRetrasadoItem,
  type EstadisticasPorTab,
  type NotificacionPlantilla,
} from '../services/notificacionService'

import { prestamoService } from '../services/prestamoService'

import { toast } from 'sonner'

import { ConfiguracionNotificaciones } from '../components/notificaciones/ConfiguracionNotificaciones'

import {
  NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
  NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
  NOTIFICACIONES_MORA_BROADCAST_CHANNEL,
  invalidateListasNotificacionesMora,
} from '../constants/queryKeys'

import { NOTIFICACIONES_QUERY_KEYS } from '../queries/notificaciones'

type TabId =
  | 'dias_1_atraso'
  | 'dias_5_atraso'
  | 'dias_30_atraso'
  | 'masivos'
  | 'configuracion'

const TABS: { id: TabId; label: string; icon: typeof Clock }[] = [
  {
    id: 'dias_1_atraso',
    label: 'Día después del venc.',
    icon: Clock,
  },

  { id: 'dias_5_atraso', label: '5 días atrasado', icon: Clock },

  { id: 'dias_30_atraso', label: '30 días atrasado', icon: Clock },

  { id: 'masivos', label: 'Masivos', icon: Mail },

  { id: 'configuracion', label: 'Configuración', icon: Settings },
]

/** Clave de GET estadisticas-por-tab / rebotados (coincide con tipo_tab en envíos). */

type EstadisticaTabKey = keyof EstadisticasPorTab

function tipoParaKpiYRebotados(tab: TabId): EstadisticaTabKey | null {
  switch (tab) {
    case 'dias_1_atraso':
      return 'dias_1_retraso'

    case 'dias_5_atraso':
      return 'dias_5_retraso'

    case 'dias_30_atraso':
      return 'prejudicial'

    case 'masivos':
      return 'masivos'

    default:
      return null
  }
}

/** Deep-link a Configuracion: ?tab=configuracion&cfg=... */

type ConfigEnvioSeccionId =
  | 'por-vencer'
  | 'dia-pago'
  | 'retrasada'
  | 'prejudicial'
  | 'comunicaciones'

function cfgSlugParaPestanaListado(tab: TabId): ConfigEnvioSeccionId | null {
  switch (tab) {
    case 'dias_1_atraso':
    case 'dias_5_atraso':
      return 'retrasada'

    case 'dias_30_atraso':
      return 'prejudicial'

    case 'masivos':
      return 'comunicaciones'

    default:
      return null
  }
}

/** Tipo de fila en GET/PUT notificaciones/envios que corresponde a cada pestaña de listado. */

function tipoConfigPlantillaParaPestana(
  tab: TabId
):
  | 'PAGO_1_DIA_ATRASADO'
  | 'PAGO_5_DIAS_ATRASADO'
  | 'PREJUDICIAL'
  | 'MASIVOS'
  | null {
  switch (tab) {
    case 'dias_1_atraso':
      return 'PAGO_1_DIA_ATRASADO'

    case 'dias_5_atraso':
      return 'PAGO_5_DIAS_ATRASADO'

    case 'dias_30_atraso':
      return 'PREJUDICIAL'

    case 'masivos':
      return 'MASIVOS'

    default:
      return null
  }
}

function parsePlantillaIdEnvio(raw: unknown): number | null {
  if (raw == null || typeof raw !== 'object') return null
  const pid = (raw as { plantilla_id?: unknown }).plantilla_id
  if (pid == null || pid === '') return null
  const n = Number(pid)
  return Number.isFinite(n) ? n : null
}

function etiquetaPlantillaParaPestana(
  tab: TabId,
  enviosRaw: Record<string, unknown> | undefined,
  plantillas: NotificacionPlantilla[] | undefined
): { linea: string; cfgHref: string } {
  const slug = cfgSlugParaPestanaListado(tab)
  const tipo = tipoConfigPlantillaParaPestana(tab)
  const baseSearch =
    slug == null
      ? '?tab=configuracion'
      : slug === 'retrasada'
        ? '?tab=configuracion'
        : `?tab=configuracion&cfg=${slug}`

  if (!tipo) {
    return {
      linea: 'Abra Configuracion para revisar envios.',
      cfgHref: baseSearch,
    }
  }

  const pid = parsePlantillaIdEnvio(enviosRaw?.[tipo])
  if (pid == null) {
    return {
      linea: 'Texto por defecto (sin plantilla HTML elegida para este caso).',
      cfgHref: baseSearch,
    }
  }

  const nombre = plantillas?.find(p => p.id === pid)?.nombre?.trim()
  return {
    linea: nombre ? `Plantilla: ${nombre} (#${pid})` : `Plantilla ID ${pid}`,
    cfgHref: baseSearch,
  }
}

const PLACEHOLDER_NOTIFICACIONES: ClientesRetrasadosResponse = {
  actualizado_en: new Date().toISOString(),

  dias_5: [],

  dias_3: [],

  dias_1: [],

  hoy: [],

  dias_1_atraso: [],

  dias_5_atraso: [],

  dias_30_atraso: [],

  liquidados: [],
}

export function Notificaciones() {
  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab') as TabId | null

  const [activeTab, setActiveTab] = useState<TabId>(() =>
    tabParam && TABS.some(t => t.id === tabParam) ? tabParam : 'dias_1_atraso'
  )

  useEffect(() => {
    if (
      tabParam &&
      TABS.some(t => t.id === tabParam) &&
      activeTab !== tabParam
    ) {
      setActiveTab(tabParam)
    }
  }, [tabParam])

  useEffect(() => {
    if (searchParams.get('tab') === 'liquidados') {
      setSearchParams(
        p => {
          const next = new URLSearchParams(p)

          next.delete('tab')

          return next
        },
        { replace: true }
      )
    }
  }, [searchParams, setSearchParams])

  const setActiveTabAndUrl = (tab: TabId) => {
    setActiveTab(tab)

    setSearchParams(p => {
      const next = new URLSearchParams(p)

      if (tab === 'dias_1_atraso') next.delete('tab')
      else next.set('tab', tab)

      if (tab !== 'configuracion') next.delete('cfg')

      return next
    })
  }

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,

    queryFn: () => notificacionService.getClientesRetrasados(),

    // Siempre considerar obsoleto: al volver a la pestaña o tras invalidar por pagos, se refetch al instante.
    staleTime: 0,

    refetchOnWindowFocus: true,

    placeholderData: PLACEHOLDER_NOTIFICACIONES,

    /** En Configuración no se listan cuotas: evita GET pesado y errores 500 por carga/BD innecesaria. */

    enabled: activeTab !== 'configuracion' && activeTab !== 'masivos',
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

      prejudicial: { enviados: 0, rebotados: 0 },

      masivos: { enviados: 0, rebotados: 0 },

      liquidados: { enviados: 0, rebotados: 0 },
    } as EstadisticasPorTab,
  })

  const { data: masivosData } = useQuery({
    queryKey: ['notificaciones-masivos-lista'],

    queryFn: () => notificacionService.listarNotificacionesMasivos(),

    staleTime: 0,

    enabled: activeTab === 'masivos',

    placeholderData: { items: [], total: 0 },
  })

  const listadoPideResumenEnvios =
    activeTab !== 'configuracion' &&
    tipoConfigPlantillaParaPestana(activeTab) != null

  const { data: enviosResumenRaw } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.envios,

    queryFn: () =>
      emailConfigService.obtenerConfiguracionEnvios() as Promise<
        Record<string, unknown>
      >,

    staleTime: 60 * 1000,

    enabled: listadoPideResumenEnvios,
  })

  const { data: plantillasCatalogo } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,

    queryFn: () => notificacionService.listarPlantillas(undefined, false),

    staleTime: 60 * 1000,

    enabled: listadoPideResumenEnvios,

    placeholderData: [] as NotificacionPlantilla[],
  })

  const resumenPlantillaPestana = useMemo(
    () =>
      etiquetaPlantillaParaPestana(
        activeTab,
        enviosResumenRaw as Record<string, unknown> | undefined,
        plantillasCatalogo
      ),
    [activeTab, enviosResumenRaw, plantillasCatalogo]
  )

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

  const [descargandoExcel, setDescargandoExcel] = useState(false)

  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)

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
        variant="link"
        size="sm"
        className="inline-flex h-auto items-center gap-1 p-0 text-blue-600"
        disabled={descargandoEstadoCuentaId === prestamoId}
        onClick={() => handleDescargarEstadoCuentaPdf(prestamoId)}
        title="Mismo PDF que en tabla de amortización (Exportar PDF)"
      >
        <Download
          className={`h-4 w-4 shrink-0 ${
            descargandoEstadoCuentaId === prestamoId ? 'animate-pulse' : ''
          }`}
        />
        Exportar PDF
      </Button>
    )
  }

  const handleRefresh = async () => {
    setActualizandoListas(true)
    try {
      await notificacionService.actualizarNotificaciones()
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
      await queryClient.invalidateQueries({
        queryKey: ['notificaciones-masivos-lista'],
      })
      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })
      await Promise.all([
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: ['notificaciones-masivos-lista'],
        }),
      ])
      toast.success(
        'Listas y KPI actualizados manualmente. El servidor tambien ejecuta un job a las 00:50 (America/Caracas).'
      )
    } catch (e) {
      console.error(e)
      toast.error(
        'No se pudo recalcular la mora en el servidor. Puede reintentar o revisar conexion y permisos.'
      )
    } finally {
      setActualizandoListas(false)
    }
  }

  const handleDescargarInformeRebotados = async () => {
    const tipoApi = tipoParaKpiYRebotados(activeTab)

    if (!tipoApi) return

    setDescargandoExcel(true)

    try {
      const { total } = await notificacionService.getRebotadosPorTab(tipoApi)

      if (total === 0) {
        toast.success('Todos los correos fueron enviados.')

        setDescargandoExcel(false)

        return
      }

      const blob = await notificacionService.descargarExcelRebotados(tipoApi)

      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = `correos_no_entregados_${tipoApi}.xlsx`

      document.body.appendChild(a)

      a.click()

      window.URL.revokeObjectURL(url)

      a.remove()

      toast.success('Informe descargado.')
    } catch (e) {
      console.error(e)

      toast.error('Error al descargar el informe.')
    } finally {
      setDescargandoExcel(false)
    }
  }

  const getListForTab = (): ClienteRetrasadoItem[] => {
    if (!data) return []

    switch (activeTab) {
      case 'dias_1_atraso':
        return data.dias_1_atraso ?? []

      case 'dias_5_atraso':
        return data.dias_5_atraso ?? []

      case 'dias_30_atraso':
        return data.dias_30_atraso ?? []

      case 'masivos':
        return masivosData?.items ?? []

      default:
        return []
    }
  }

  const list = getListForTab()

  const statTabKey = tipoParaKpiYRebotados(activeTab)

  const hasColumnasCuota = list.some(
    row =>
      row.numero_cuota != null ||
      row.fecha_vencimiento != null ||
      row.dias_atraso != null ||
      row.monto != null
  )

  const mostrarTablaCuotas = hasColumnasCuota

  const esTabMasivos = activeTab === 'masivos'

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description="Clientes retrasados por fecha de vencimiento y mora"
          actions={
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

        <ConfiguracionNotificaciones />
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
          description="Cuotas pendientes en tiempo real: al registrar pagos que cubren la cuota, el cliente deja de aparecer. Use Actualizar o vuelva a entrar; también se refresca al guardar pagos en el módulo Pagos."
          actions={
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
          }
        />
      </motion.div>

      <div className="border-b border-gray-200">
        <nav className="flex flex-wrap gap-1">
          {TABS.filter(t => t.id !== 'configuracion').map(tab => {
            const count =
              tab.id === 'dias_1_atraso'
                ? (data?.dias_1_atraso?.length ?? 0)
                : tab.id === 'dias_5_atraso'
                  ? (data?.dias_5_atraso?.length ?? 0)
                  : tab.id === 'dias_30_atraso'
                    ? (data?.dias_30_atraso?.length ?? 0)
                    : 0

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
        {listadoPideResumenEnvios && (
          <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <span className="font-medium text-slate-800">Esta pestaña: </span>
            <span>{resumenPlantillaPestana.linea}</span>
            <Link
              to={resumenPlantillaPestana.cfgHref}
              className="ml-2 inline-flex items-center text-blue-600 underline-offset-2 hover:underline"
            >
              Ir a configuración del caso
            </Link>
            <span className="mt-1 block text-xs text-slate-500">
              Cada pestaña usa solo su fila en el servidor; aquí solo se muestra
              un resumen. Los cambios requieren Guardar en Configuración.
            </span>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {(() => {
                const TabIcon = TABS.find(t => t.id === activeTab)?.icon

                return TabIcon ? <TabIcon className="h-5 w-5" /> : null
              })()}

              {activeTab === 'dias_1_atraso'
                ? 'Día siguiente al vencimiento (1 día de atraso calendario)'
                : activeTab === 'dias_5_atraso'
                  ? 'Cuotas con 5 días de atraso'
                  : activeTab === 'dias_30_atraso'
                    ? 'Cuotas con 30 días de atraso'
                    : ''}
            </CardTitle>

            <CardDescription>
              {activeTab === 'dias_1_atraso'
                ? 'Cuotas cuya fecha de vencimiento fue ayer (hoy es el primer día después del vencimiento). Ej.: vence 22 → entra el 23. Columna Estado de cuenta: mismo PDF que en amortización del préstamo.'
                : activeTab === 'dias_5_atraso' ||
                    activeTab === 'dias_30_atraso'
                  ? 'Cuotas vencidas no pagadas con 5 o 30 días de atraso. Columna Estado de cuenta: mismo PDF que en amortización del préstamo.'
                  : 'Nombre y cédula de clientes a notificar.'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={actualizandoListas}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>
              <p className="max-w-xl text-xs text-gray-600">
                Vuelve a pedir al servidor las listas de mora, los KPI y masivos
                (POST{' '}
                <code className="rounded bg-white px-1">
                  /notificaciones/actualizar
                </code>{' '}
                y refetch de datos).
              </p>
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

            {activeTab === 'dias_30_atraso' && (
              <p className="mb-4 text-xs text-gray-500">
                Los KPI y el informe Excel corresponden al envio prejudicial
                (tipo_tab{' '}
                <code className="rounded bg-gray-100 px-1">prejudicial</code> en
                la base de datos).
              </p>
            )}

            {esTabMasivos && (
              <p className="mb-4 text-xs text-gray-500">
                Comunicaciones masivas generales: no dependen de cuotas ni de
                préstamos. Se envían a clientes con correo registrado, usando la
                configuración del caso
                <code className="mx-1 rounded bg-gray-100 px-1">MASIVOS</code>.
              </p>
            )}

            {/* Botón descargar informe Excel de no entregados (rebotados) */}

            {statTabKey != null && (
              <div className="mb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDescargarInformeRebotados}
                  disabled={descargandoExcel}
                >
                  <Download
                    className={`mr-2 h-4 w-4 ${descargandoExcel ? 'animate-pulse' : ''}`}
                  />

                  {descargandoExcel
                    ? 'Preparando...'
                    : 'Descargar informe de correos no entregados (Excel)'}
                </Button>

                <p className="mt-1 text-xs text-gray-500">
                  Si todos los correos se enviaron correctamente se mostrará una
                  notificación.
                </p>
              </div>
            )}

            {isError && (
              <div className="mb-4 flex items-center justify-between gap-2 rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
                <span>
                  Error al cargar.
                  {error?.message ? ` ${String(error.message)}` : ''} Comprueba
                  que exista la tabla{' '}
                  <code className="bg-gray-100 px-1">cuotas</code>.
                </span>

                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  Reintentar
                </Button>
              </div>
            )}

            {isLoading && (
              <div className="mb-4 flex items-center gap-2 rounded border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700">
                <RefreshCw className="h-4 w-4 animate-spin" />

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
                        Nº cuota
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                        Fecha venc.
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                        Días atraso
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                        Monto
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                        Estado de cuenta
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={8}
                          className="py-8 text-center text-gray-500"
                        >
                          Ningún registro en este criterio.
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

                          <td className="px-3 py-2">
                            {row.numero_cuota ?? '-'}
                          </td>

                          <td className="px-3 py-2">
                            {row.fecha_vencimiento ?? '-'}
                          </td>

                          <td className="px-3 py-2 text-right font-medium text-red-600">
                            {row.dias_atraso ?? '-'}
                          </td>

                          <td className="px-3 py-2 text-right">
                            {row.monto != null
                              ? Number(row.monto).toLocaleString('es')
                              : '-'}
                          </td>

                          {esTabMasivos ? (
                            <>
                              <td className="px-3 py-2">{row.correo || '-'}</td>

                              <td className="px-3 py-2">
                                {row.telefono || '-'}
                              </td>
                            </>
                          ) : (
                            <td className="px-3 py-2">
                              {estadoCuentaPdfCell(row.prestamo_id)}
                            </td>
                          )}
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

                      {esTabMasivos ? (
                        <>
                          <th className="px-3 py-2 text-left font-semibold">
                            Correo
                          </th>

                          <th className="px-3 py-2 text-left font-semibold">
                            Teléfono
                          </th>
                        </>
                      ) : (
                        <th className="px-3 py-2 text-left font-semibold">
                          Estado de cuenta
                        </th>
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={esTabMasivos ? 5 : 4}
                          className="py-8 text-center text-gray-500"
                        >
                          Ningún cliente en este criterio.
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

                          {esTabMasivos ? (
                            <>
                              <td className="px-3 py-2">{row.correo || '-'}</td>

                              <td className="px-3 py-2">
                                {row.telefono || '-'}
                              </td>
                            </>
                          ) : (
                            <td className="px-3 py-2">
                              {estadoCuentaPdfCell(row.prestamo_id)}
                            </td>
                          )}
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
