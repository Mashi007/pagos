import { useState, useEffect } from 'react'

import { useSearchParams } from 'react-router-dom'

import { motion } from 'framer-motion'

import {
  RefreshCw,
  Settings,
  Calendar,
  AlertTriangle,
  FileText,
  Clock,
  Mail,
  Download,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'

import { Button } from '../components/ui/button'

import { useQuery } from '@tanstack/react-query'

import {
  notificacionService,
  type ClientesRetrasadosResponse,
  type ClienteRetrasadoItem,
  type LiquidadoItem,
  type EstadisticasPorTab,
} from '../services/notificacionService'

import { toast } from 'sonner'

import { ConfiguracionNotificaciones } from '../components/notificaciones/ConfiguracionNotificaciones'

type TabId =
  | 'dias_5'
  | 'dias_3'
  | 'dias_1'
  | 'hoy'
  | 'dias_5_atraso'
  | 'dias_30_atraso'
  | 'mora_90'
  | 'liquidados'
  | 'configuracion'

const TABS: { id: TabId; label: string; icon: typeof Calendar }[] = [
  { id: 'dias_5', label: 'Faltan 5', icon: Calendar },

  { id: 'dias_3', label: 'Faltan 3', icon: Calendar },

  { id: 'dias_1', label: 'Falta 1', icon: Clock },

  { id: 'hoy', label: 'Hoy vence', icon: AlertTriangle },

  { id: 'dias_5_atraso', label: '5 días atrasado', icon: Clock },

  { id: 'dias_30_atraso', label: '30 días atrasado', icon: Clock },

  { id: 'mora_90', label: '90+ días de mora (moroso)', icon: FileText },

  { id: 'liquidados', label: 'Crédito pagado', icon: FileText },

  { id: 'configuracion', label: 'Configuración', icon: Settings },
]

const PLACEHOLDER_NOTIFICACIONES: ClientesRetrasadosResponse = {
  actualizado_en: new Date().toISOString(),

  dias_5: [],

  dias_3: [],

  dias_1: [],

  hoy: [],

  dias_5_atraso: [],

  dias_30_atraso: [],

  mora_90: { cuotas: [], total_cuotas: 0 },

  liquidados: [],
}

export function Notificaciones() {
  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab') as TabId | null

  const [activeTab, setActiveTab] = useState<TabId>(() =>
    tabParam && TABS.some(t => t.id === tabParam) ? tabParam : 'dias_5'
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

  const setActiveTabAndUrl = (tab: TabId) => {
    setActiveTab(tab)

    setSearchParams(p => {
      const next = new URLSearchParams(p)

      if (tab === 'dias_5') next.delete('tab')
      else next.set('tab', tab)

      return next
    })
  }

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['notificaciones-clientes-retrasados'],

    queryFn: () => notificacionService.getClientesRetrasados(),

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: true,

    placeholderData: PLACEHOLDER_NOTIFICACIONES,
  })

  const { data: estadisticasPorTab } = useQuery({
    queryKey: ['notificaciones-estadisticas-por-tab'],

    queryFn: () => notificacionService.getEstadisticasPorTab(),

    staleTime: 1 * 60 * 1000,

    placeholderData: {
      dias_5: { enviados: 0, rebotados: 0 },

      dias_3: { enviados: 0, rebotados: 0 },

      dias_1: { enviados: 0, rebotados: 0 },

      hoy: { enviados: 0, rebotados: 0 },

      mora_90: { enviados: 0, rebotados: 0 },
    } as EstadisticasPorTab,
  })

  const [descargandoExcel, setDescargandoExcel] = useState(false)

  const handleRefresh = () => {
    refetch()

    toast.success(
      'Datos actualizados. Se recomienda ejecutar actualización a las 2am (cron).'
    )
  }

  const handleDescargarInformeRebotados = async () => {
    if (
      activeTab === 'configuracion' ||
      activeTab === 'liquidados' ||
      activeTab === 'dias_5_atraso' ||
      activeTab === 'dias_30_atraso'
    )
      return

    setDescargandoExcel(true)

    try {
      const { total } = await notificacionService.getRebotadosPorTab(activeTab)

      if (total === 0) {
        toast.success('Todos los correos fueron enviados.')

        setDescargandoExcel(false)

        return
      }

      const blob = await notificacionService.descargarExcelRebotados(activeTab)

      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = `correos_no_entregados_${activeTab}.xlsx`

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
      case 'dias_5':
        return data.dias_5

      case 'dias_3':
        return data.dias_3

      case 'dias_1':
        return data.dias_1

      case 'hoy':
        return data.hoy

      case 'dias_5_atraso':
        return data.dias_5_atraso ?? []

      case 'dias_30_atraso':
        return data.dias_30_atraso ?? []

      case 'mora_90':
        return data.mora_90?.cuotas ?? []

      case 'liquidados':
        return []

      default:
        return []
    }
  }

  const list = getListForTab()

  const hasColumnasCuota = list.some(
    row =>
      row.numero_cuota != null ||
      row.fecha_vencimiento != null ||
      row.dias_atraso != null ||
      row.monto != null
  )

  const mostrarTablaCuotas = activeTab === 'mora_90' || hasColumnasCuota

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Notificaciones</h1>

            <p className="mt-1 text-gray-600">
              Clientes retrasados por fecha de vencimiento y mora
            </p>
          </div>
        </div>

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
        className="flex flex-wrap items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notificaciones</h1>

          <p className="mt-1 text-gray-600">
            Recordatorios (Faltan 5, 3, 1), vence hoy, atrasos (5 y 30 días),
            mora 90+ y crédito pagado. Datos desde BD. Se recomienda actualizar
            a las 2:00.
          </p>

          {data?.actualizado_en && (
            <p className="mt-1 text-xs text-gray-500">
              Última actualización:{' '}
              {new Date(data.actualizado_en).toLocaleString('es-ES')}
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isFetching}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
            />
            Actualizar
          </Button>
        </div>
      </motion.div>

      <div className="border-b border-gray-200">
        <nav className="flex flex-wrap gap-1">
          {TABS.filter(t => t.id !== 'configuracion').map(tab => {
            const count =
              tab.id === 'dias_5'
                ? (data?.dias_5?.length ?? 0)
                : tab.id === 'dias_3'
                  ? (data?.dias_3?.length ?? 0)
                  : tab.id === 'dias_1'
                    ? (data?.dias_1?.length ?? 0)
                    : tab.id === 'hoy'
                      ? (data?.hoy?.length ?? 0)
                      : tab.id === 'mora_90'
                        ? (data?.mora_90?.total_cuotas ?? 0)
                        : tab.id === 'liquidados'
                          ? (data?.liquidados?.length ?? 0)
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

              {activeTab === 'mora_90'
                ? 'Informe: cuotas con 90 o más días de mora - moroso (una a una)'
                : activeTab === 'liquidados'
                  ? 'Crédito pagado (Total financiamiento = Total abonos)'
                  : activeTab === 'dias_5_atraso'
                    ? 'Cuotas con 5 días de atraso'
                    : activeTab === 'dias_30_atraso'
                      ? 'Cuotas con 30 días de atraso'
                      : `Clientes con cuota no pagada ${activeTab === 'dias_5' ? 'y faltan 5 días' : activeTab === 'dias_3' ? 'y faltan 3 días' : activeTab === 'dias_1' ? 'y falta 1 día' : 'y vence hoy'}`}
            </CardTitle>

            <CardDescription>
              {activeTab === 'mora_90'
                ? 'Listado de cada cuota atrasada 90+ días (moroso) con nombre, cédula, número de cuota, fecha de vencimiento, días de atraso y monto.'
                : activeTab === 'liquidados'
                  ? 'Préstamos donde total financiamiento (tabla préstamo) menos total abonos (tabla cuotas) es cero. Por cédula/cliente.'
                  : activeTab === 'dias_5_atraso' ||
                      activeTab === 'dias_30_atraso'
                    ? 'Cuotas vencidas no pagadas con 5 o 30 días de atraso (nombre, cédula, nº cuota, fecha venc., días atraso, monto).'
                    : 'Nombre y cédula de clientes a notificar.'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            {/* KPIs por pestaña: correos enviados y rebotados */}

            {(activeTab as TabId) !== 'configuracion' &&
              (activeTab as TabId) !== 'liquidados' &&
              estadisticasPorTab && (
                <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-2">
                  <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
                    <Mail className="h-8 w-8 text-green-600" />

                    <div>
                      <p className="text-2xl font-bold text-green-800">
                        {estadisticasPorTab[activeTab]?.enviados ?? 0}
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
                        {estadisticasPorTab[activeTab]?.rebotados ?? 0}
                      </p>

                      <p className="text-xs font-medium text-red-700">
                        Correos rebotados
                      </p>
                    </div>
                  </div>
                </div>
              )}

            {/* Botón descargar informe Excel de no entregados (rebotados) */}

            {(activeTab as TabId) !== 'configuracion' &&
              (activeTab as TabId) !== 'liquidados' &&
              (activeTab as TabId) !== 'dias_5_atraso' &&
              (activeTab as TabId) !== 'dias_30_atraso' && (
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
                    Si todos los correos se enviaron correctamente se mostrará
                    una notificación.
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

            {activeTab === 'liquidados' ? (
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

                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                        Total financiamiento
                      </th>

                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                        Total abonos
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {(data?.liquidados ?? []).length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-8 text-center text-gray-500"
                        >
                          No hay préstamos con crédito pagado (Total
                          financiamiento = Total abonos).
                        </td>
                      </tr>
                    ) : (
                      (data?.liquidados ?? []).map(
                        (row: LiquidadoItem, idx: number) => (
                          <tr
                            key={`liquidado-${row.prestamo_id}-${idx}`}
                            className="border-b hover:bg-gray-50"
                          >
                            <td className="px-3 py-2">{idx + 1}</td>

                            <td className="px-3 py-2 font-medium">
                              {row.nombre}
                            </td>

                            <td className="px-3 py-2">{row.cedula}</td>

                            <td className="px-3 py-2 text-right">
                              {Number(row.total_financiamiento).toLocaleString(
                                'es'
                              )}
                            </td>

                            <td className="px-3 py-2 text-right">
                              {Number(row.total_abonos).toLocaleString('es')}
                            </td>
                          </tr>
                        )
                      )
                    )}
                  </tbody>
                </table>
              </div>
            ) : mostrarTablaCuotas ? (
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
                    </tr>
                  </thead>

                  <tbody>
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={7}
                          className="py-8 text-center text-gray-500"
                        >
                          {activeTab === 'mora_90'
                            ? 'No hay cuotas con 90+ días de mora (moroso).'
                            : 'Ningún registro en este criterio.'}
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
                    </tr>
                  </thead>

                  <tbody>
                    {list.length === 0 ? (
                      <tr>
                        <td
                          colSpan={3}
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
