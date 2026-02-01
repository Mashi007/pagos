import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  RefreshCw,
  Settings,
  Calendar,
  AlertTriangle,
  FileText,
  Clock,
  Mail,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { useQuery } from '@tanstack/react-query'
import { notificacionService, type ClientesRetrasadosResponse, type ClienteRetrasadoItem } from '../services/notificacionService'
import { toast } from 'sonner'
import { ConfiguracionNotificaciones } from '../components/notificaciones/ConfiguracionNotificaciones'

type TabId = 'dias_5' | 'dias_3' | 'dias_1' | 'hoy' | 'mora_61' | 'configuracion'

const TABS: { id: TabId; label: string; icon: typeof Calendar }[] = [
  { id: 'dias_5', label: 'Faltan 5 días', icon: Calendar },
  { id: 'dias_3', label: 'Faltan 3 días', icon: Calendar },
  { id: 'dias_1', label: 'Falta 1 día', icon: Clock },
  { id: 'hoy', label: 'Hoy vence', icon: AlertTriangle },
  { id: 'mora_61', label: '61+ días de mora', icon: FileText },
  { id: 'configuracion', label: 'Configuración', icon: Settings },
]

export function Notificaciones() {
  const [activeTab, setActiveTab] = useState<TabId>('dias_5')

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['notificaciones-clientes-retrasados'],
    queryFn: () => notificacionService.getClientesRetrasados(),
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: true,
  })

  const [enviando, setEnviando] = useState(false)

  const handleRefresh = () => {
    refetch()
    toast.success('Datos actualizados. Se recomienda ejecutar actualización a las 2am (cron).')
  }

  const handleEnviarCorreos = async () => {
    setEnviando(true)
    try {
      let res: { mensaje: string; enviados: number; sin_email: number; fallidos: number }
      if (activeTab === 'dias_5' || activeTab === 'dias_3' || activeTab === 'dias_1') {
        res = await notificacionService.enviarNotificacionesPrevias()
      } else if (activeTab === 'hoy') {
        res = await notificacionService.enviarNotificacionesDiaPago()
      } else if (activeTab === 'mora_61') {
        res = await notificacionService.enviarNotificacionesMora61()
      } else {
        setEnviando(false)
        return
      }
      toast.success(`${res.mensaje} Enviados: ${res.enviados}. Sin email: ${res.sin_email}. Fallidos: ${res.fallidos}.`)
      refetch()
    } catch (e) {
      toast.error('Error al enviar correos')
      console.error(e)
    } finally {
      setEnviando(false)
    }
  }

  const getListForTab = (): ClienteRetrasadoItem[] => {
    if (!data) return []
    switch (activeTab) {
      case 'dias_5': return data.dias_5
      case 'dias_3': return data.dias_3
      case 'dias_1': return data.dias_1
      case 'hoy': return data.hoy
      case 'mora_61': return data.mora_61?.cuotas ?? []
      default: return []
    }
  }

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Notificaciones</h1>
            <p className="text-gray-600 mt-1">Clientes retrasados por fecha de vencimiento y mora</p>
          </div>
        </div>
        <div className="border-b border-gray-200">
          <nav className="flex flex-wrap gap-2">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-2 px-3 rounded-t font-medium text-sm ${
                  activeTab === tab.id ? 'bg-white border border-b-0 border-gray-200 text-blue-600' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
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
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notificaciones a clientes retrasados</h1>
          <p className="text-gray-600 mt-1">
            Cuotas no pagadas por días hasta vencimiento y mora 61+. Datos desde BD. Actualización recomendada a las 2am.
          </p>
          {data?.actualizado_en && (
            <p className="text-xs text-gray-500 mt-1">Última consulta: {new Date(data.actualizado_en).toLocaleString('es-ES')}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button
            variant="default"
            onClick={handleEnviarCorreos}
            disabled={enviando || isLoading || getListForTab().length === 0}
          >
            <Mail className={`w-4 h-4 mr-2 ${enviando ? 'animate-pulse' : ''}`} />
            {enviando ? 'Enviando...' : 'Enviar correos'}
          </Button>
        </div>
      </motion.div>

      <div className="border-b border-gray-200">
        <nav className="flex flex-wrap gap-1">
          {TABS.filter((t) => t.id !== 'configuracion').map((tab) => {
            const count =
              tab.id === 'dias_5' ? data?.dias_5?.length ?? 0
              : tab.id === 'dias_3' ? data?.dias_3?.length ?? 0
              : tab.id === 'dias_1' ? data?.dias_1?.length ?? 0
              : tab.id === 'hoy' ? data?.hoy?.length ?? 0
              : tab.id === 'mora_61' ? data?.mora_61?.total_cuotas ?? 0
              : 0
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 font-medium text-sm ${
                  activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {count > 0 && (
                  <span className="bg-gray-200 text-gray-700 text-xs font-semibold px-2 py-0.5 rounded-full">{count}</span>
                )}
              </button>
            )
          })}
          <button
            onClick={() => setActiveTab('configuracion')}
            className="flex items-center gap-2 py-3 px-4 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700"
          >
            <Settings className="w-4 h-4" />
            Configuración
          </button>
        </nav>
      </div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {TABS.find((t) => t.id === activeTab)?.icon && <TABS.find((t) => t.id === activeTab)!.icon className="w-5 h-5" />}
              {activeTab === 'mora_61'
                ? 'Informe: cuotas con 61 o más días de mora (una a una)'
                : `Clientes con cuota no pagada ${activeTab === 'dias_5' ? 'y faltan 5 días' : activeTab === 'dias_3' ? 'y faltan 3 días' : activeTab === 'dias_1' ? 'y falta 1 día' : 'y vence hoy'}`}
            </CardTitle>
            <CardDescription>
              {activeTab === 'mora_61'
                ? 'Listado de cada cuota atrasada 61+ días con nombre, cédula, número de cuota, fecha de vencimiento, días de atraso y monto.'
                : 'Nombre y cédula de clientes a notificar.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin mb-2" />
                <p>Cargando datos...</p>
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-600">
                <AlertTriangle className="w-10 h-10 mx-auto mb-2" />
                <p>Error al cargar. Comprueba que exista la tabla <code className="bg-gray-100 px-1">cuotas</code> y que tenga datos.</p>
                <Button variant="outline" className="mt-4" onClick={() => refetch()}>Reintentar</Button>
              </div>
            ) : activeTab === 'mora_61' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left py-2 px-3 font-semibold">#</th>
                      <th className="text-left py-2 px-3 font-semibold">Nombre</th>
                      <th className="text-left py-2 px-3 font-semibold">Cédula</th>
                      <th className="text-left py-2 px-3 font-semibold">Nº cuota</th>
                      <th className="text-left py-2 px-3 font-semibold">Fecha venc.</th>
                      <th className="text-right py-2 px-3 font-semibold">Días atraso</th>
                      <th className="text-right py-2 px-3 font-semibold">Monto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getListForTab().length === 0 ? (
                      <tr><td colSpan={7} className="py-8 text-center text-gray-500">No hay cuotas con 61+ días de mora.</td></tr>
                    ) : (
                      getListForTab().map((row, idx) => (
                        <tr key={`${row.cliente_id}-${row.numero_cuota ?? idx}`} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-3">{idx + 1}</td>
                          <td className="py-2 px-3 font-medium">{row.nombre}</td>
                          <td className="py-2 px-3">{row.cedula}</td>
                          <td className="py-2 px-3">{row.numero_cuota ?? '-'}</td>
                          <td className="py-2 px-3">{row.fecha_vencimiento ?? '-'}</td>
                          <td className="py-2 px-3 text-right font-medium text-red-600">{row.dias_atraso ?? '-'}</td>
                          <td className="py-2 px-3 text-right">{row.monto != null ? Number(row.monto).toLocaleString('es') : '-'}</td>
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
                      <th className="text-left py-2 px-3 font-semibold">#</th>
                      <th className="text-left py-2 px-3 font-semibold">Nombre</th>
                      <th className="text-left py-2 px-3 font-semibold">Cédula</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getListForTab().length === 0 ? (
                      <tr><td colSpan={3} className="py-8 text-center text-gray-500">Ningún cliente en este criterio.</td></tr>
                    ) : (
                      getListForTab().map((row, idx) => (
                        <tr key={`${row.cliente_id}-${row.numero_cuota ?? idx}`} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-3">{idx + 1}</td>
                          <td className="py-2 px-3 font-medium">{row.nombre}</td>
                          <td className="py-2 px-3">{row.cedula}</td>
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
