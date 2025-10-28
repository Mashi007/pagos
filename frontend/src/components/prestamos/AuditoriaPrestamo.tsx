import { useAuditoriaPrestamo } from '@/hooks/useAuditoriaPrestamo'
import { formatDate } from '@/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Clock, User, Calendar, Edit } from 'lucide-react'

interface AuditoriaPrestamoProps {
  prestamoId: number
}

const getAccionColor = (accion: string) => {
  const colors = {
    CREAR: 'bg-green-100 text-green-800 border-green-300',
    EDITAR: 'bg-blue-100 text-blue-800 border-blue-300',
    APROBAR: 'bg-green-100 text-green-800 border-green-300',
    RECHAZAR: 'bg-red-100 text-red-800 border-red-300',
    CAMBIO_ESTADO: 'bg-purple-100 text-purple-800 border-purple-300',
    ACTUALIZACION_GENERAL: 'bg-gray-100 text-gray-800 border-gray-300',
  }
  return colors[accion as keyof typeof colors] || 'bg-gray-100 text-gray-800 border-gray-300'
}

export function AuditoriaPrestamo({ prestamoId }: AuditoriaPrestamoProps) {
  const { data: auditoria, isLoading, isError } = useAuditoriaPrestamo(prestamoId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="ml-3 text-gray-600">Cargando historial de auditoría...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-red-600">Error al cargar el historial de auditoría</p>
        </CardContent>
      </Card>
    )
  }

  if (!auditoria || auditoria.length === 0) {
    return (
        <Card>
        <CardContent className="py-8 text-center">
          <Clock className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No hay historial de auditoría para este préstamo</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {auditoria.map((entry) => (
        <Card key={entry.id} className="border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-3">
                <div className={`px-2 py-1 rounded text-xs font-semibold border ${getAccionColor(entry.accion)}`}>
                  {entry.accion}
                </div>
                <span className="text-xs text-gray-500 font-mono">
                  {entry.campo_modificado}
                </span>
              </div>
              <div className="flex items-center text-xs text-gray-500">
                <Calendar className="h-3 w-3 mr-1" />
                {formatDate(new Date(entry.fecha_cambio), 'dd/MM/yyyy HH:mm')}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="flex items-start space-x-2">
                <User className="h-4 w-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="font-medium text-gray-600">Usuario:</span>
                  <p className="text-gray-800">{entry.usuario}</p>
                </div>
              </div>

              {entry.estado_anterior && entry.estado_nuevo && (
              <div className="flex items-start space-x-2">
                <Edit className="h-4 w-4 text-gray-400 mt-0.5" />
                <div>
                    <span className="font-medium text-gray-600">Cambio de estado:</span>
                    <p className="text-gray-800">
                      <span className="line-through text-red-600">{entry.estado_anterior}</span>{' '}
                      → <span className="text-green-600 font-semibold">{entry.estado_nuevo}</span>
                    </p>
                  </div>
                </div>
              )}
            </div>

            {entry.valor_anterior && entry.valor_nuevo && (
              <div className="mt-3 p-3 bg-gray-50 rounded-md text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="font-medium text-gray-600">Valor anterior:</span>
                    <p className="text-gray-700 line-through">{entry.valor_anterior}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Valor nuevo:</span>
                    <p className="text-green-700 font-semibold">{entry.valor_nuevo}</p>
                  </div>
                </div>
              </div>
            )}

            {entry.observaciones && (
              <div className="mt-3 p-3 bg-blue-50 rounded-md border border-blue-200">
                <p className="text-sm text-blue-900">
                  <span className="font-medium">Observaciones:</span> {entry.observaciones}
                </p>
              </div>
            )}

            {!entry.valor_anterior && entry.valor_nuevo && (
              <div className="mt-3">
                <span className="text-sm font-medium text-gray-600">Detalles:</span>
                <p className="text-sm text-gray-700">{entry.valor_nuevo}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

