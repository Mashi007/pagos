import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import {
  Loader2,
  Edit,
  Check,
  X,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { toast } from 'sonner'
import { revisionManualService } from '../services/revisionManualService'

interface PrestamoRevision {
  prestamo_id: number
  cliente_id: number
  cedula: string
  nombres: string
  total_prestamo: number
  total_abonos: number
  saldo: number
  cuotas_vencidas: number
  cuotas_morosas: number
  estado_revision: string
  fecha_revision: string | null
}

interface ResumenRevision {
  total_prestamos: number
  prestamos_revisados: number
  prestamos_pendientes: number
  porcentaje_completado: number
  prestamos: PrestamoRevision[]
}

export function RevisionManual() {
  const [filtro, setFiltro] = useState<'todos' | 'pendientes' | 'revisados' | 'revisando'>('todos')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['revision-manual-prestamos', filtro],
    queryFn: () => revisionManualService.getPreslamosRevision(filtro),
    staleTime: 60 * 1000,
  })

  const handleConfirmarSi = async (prestamoId: number, nombres: string) => {
    const confirmar = window.confirm(
      `⚠️ CONFIRMAR REVISIÓN - ${nombres}\n\n` +
      '✓ Se marcarán TODOS los datos como correctos:\n' +
      '  - Datos del cliente\n' +
      '  - Datos del préstamo\n' +
      '  - Cuotas y pagos\n\n' +
      '✓ El préstamo desaparecerá de esta lista\n' +
      '✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO\n\n' +
      '¿Confirmas que todo está correcto?'
    )
    if (!confirmar) {
      toast.info('ℹ️ Confirmación cancelada')
      return
    }

    try {
      const res = await revisionManualService.confirmarPrestamoRevisado(prestamoId)
      toast.success(`✅ ${res.mensaje}`)
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error al confirmar'
      toast.error(`❌ ${errorMsg}`)
      console.error('Error confirmando:', err)
    }
  }

  const handleEditarNo = (prestamoId: number) => {
    // Confirmar antes de abrir editor
    const confirmar = window.confirm(
      '⚠️ INICIAR EDICIÓN\n\n' +
      'Al presionar "No", accederás a la interfaz de edición donde podrás:\n' +
      '✓ Editar datos del cliente\n' +
      '✓ Editar datos del préstamo\n' +
      '✓ Editar cuotas y pagos\n\n' +
      '✓ Puedes guardar cambios parciales (Guardar Parciales)\n' +
      '✓ O finalizar la revisión (Guardar y Cerrar)\n\n' +
      '¿Deseas continuar?'
    )
    if (!confirmar) {
      toast.info('ℹ️ Edición cancelada')
      return
    }

    // Inicia revisión (cambia estado a 'revisando')
    revisionManualService.iniciarRevision(prestamoId).then(() => {
      toast.info('ℹ️ Edición iniciada. Abriendo editor...')
      // Navega a página de edición
      navigate(`/pagos/revision-manual/editar/${prestamoId}`)
    }).catch((err: any) => {
      const errorMsg = err?.response?.data?.detail || 'Error al iniciar revisión'
      toast.error(`❌ ${errorMsg}`)
      console.error('Error iniciando revisión:', err)
    })
  }

  const datosVisibles = data?.prestamos.filter((p) => {
    if (filtro === 'pendientes') return p.estado_revision === 'pendiente'
    if (filtro === 'revisados') return p.estado_revision === 'revisado'
    if (filtro === 'revisando') return p.estado_revision === 'revisando'
    return true
  }) || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-4 sm:p-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-gray-900">Revisión Manual de Préstamos</h1>
          <p className="text-sm text-gray-600">
            Verifica y confirma los detalles de cada préstamo post-migración
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            refetch()
            toast.info('Actualizando...')
          }}
          disabled={isLoading}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </div>

      {/* Barra de Progreso */}
      {data && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Progreso de Revisión</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">
                  {data.prestamos_revisados} de {data.total_prestamos} préstamos revisados
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Faltan: {data.prestamos_pendientes} préstamos por revisar
                </p>
              </div>
              <div className="text-3xl font-bold text-blue-600">{data.porcentaje_completado}%</div>
            </div>
            {/* Barra gráfica */}
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${data.porcentaje_completado}%` }}
                transition={{ duration: 0.5 }}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        <Button
          variant={filtro === 'todos' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFiltro('todos')}
        >
          Todos
        </Button>
        <Button
          variant={filtro === 'pendientes' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFiltro('pendientes')}
        >
          Pendientes ({data?.prestamos_pendientes || 0})
        </Button>
        <Button
          variant={filtro === 'revisando' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFiltro('revisando')}
        >
          🔄 Revisando
        </Button>
        <Button
          variant={filtro === 'revisados' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFiltro('revisados')}
        >
          ✓ Revisados ({data?.prestamos_revisados || 0})
        </Button>
      </div>

      {/* Tabla de Préstamos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Lista de Préstamos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="text-center py-8 text-red-600">
              <p>Error al cargar préstamos</p>
            </div>
          ) : datosVisibles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No hay préstamos para mostrar</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold">Nombre</th>
                    <th className="px-4 py-2 text-left font-semibold">Cédula</th>
                    <th className="px-4 py-2 text-right font-semibold">Total Préstamo</th>
                    <th className="px-4 py-2 text-right font-semibold">Total Abonos</th>
                    <th className="px-4 py-2 text-right font-semibold">Saldo</th>
                    <th className="px-4 py-2 text-center font-semibold">Vencidas</th>
                    <th className="px-4 py-2 text-center font-semibold">Morosas</th>
                    <th className="px-4 py-2 text-center font-semibold">Estado</th>
                    <th className="px-4 py-2 text-center font-semibold">Decisión</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {datosVisibles.map((prestamo) => (
                    <motion.tr
                      key={prestamo.prestamo_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="hover:bg-gray-50 transition"
                    >
                      <td className="px-4 py-3 font-medium">{prestamo.nombres}</td>
                      <td className="px-4 py-3 text-gray-600">{prestamo.cedula}</td>
                      <td className="px-4 py-3 text-right font-semibold">
                        ${prestamo.total_prestamo.toLocaleString('es-ES', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-right text-green-600 font-semibold">
                        ${prestamo.total_abonos.toLocaleString('es-ES', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-orange-600">
                        ${prestamo.saldo.toLocaleString('es-ES', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${prestamo.cuotas_vencidas > 0 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100'}`}>
                          {prestamo.cuotas_vencidas}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${prestamo.cuotas_morosas > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>
                          {prestamo.cuotas_morosas}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {prestamo.estado_revision === 'revisado' && (
                          <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">✓ Revisado</span>
                        )}
                        {prestamo.estado_revision === 'revisando' && (
                          <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-800">🔄 Revisando</span>
                        )}
                        {prestamo.estado_revision === 'pendiente' && (
                          <span className="px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">Pendiente</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {prestamo.estado_revision === 'pendiente' && (
                          <div className="flex gap-2 justify-center">
                            <Button
                              size="sm"
                              className="bg-green-600 hover:bg-green-700 text-white text-xs h-8 px-2"
                              onClick={() => handleConfirmarSi(prestamo.prestamo_id, prestamo.nombres)}
                            >
                              ✓ Sí
                            </Button>
                            <Button
                              size="sm"
                              className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-2"
                              onClick={() => handleEditarNo(prestamo.prestamo_id)}
                            >
                              ✎ No
                            </Button>
                          </div>
                        )}
                        {prestamo.estado_revision === 'revisando' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-blue-600 text-xs h-8"
                            onClick={() => navigate(`/pagos/revision-manual/editar/${prestamo.prestamo_id}`)}
                          >
                            <Edit className="h-3 w-3 mr-1" />
                            Continuar
                          </Button>
                        )}
                        {prestamo.estado_revision === 'revisado' && (
                          <span className="text-xs text-gray-500">Finalizado</span>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default RevisionManual
