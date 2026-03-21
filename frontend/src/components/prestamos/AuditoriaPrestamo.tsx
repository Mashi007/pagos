import { useAuditoriaPrestamo } from '../../hooks/useAuditoriaPrestamo'

import { formatDate } from '../../utils'

import { Card, CardContent } from '../../components/ui/card'

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

  return (
    colors[accion as keyof typeof colors] ||
    'bg-gray-100 text-gray-800 border-gray-300'
  )
}

export function AuditoriaPrestamo({ prestamoId }: AuditoriaPrestamoProps) {
  const {
    data: auditoria,
    isLoading,
    isError,
  } = useAuditoriaPrestamo(prestamoId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>

        <p className="ml-3 text-gray-600">Cargando historial de auditoría...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-red-600">
            Error al cargar el historial de auditoría
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!auditoria || auditoria.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Clock className="mx-auto mb-4 h-12 w-12 text-gray-400" />

          <p className="text-gray-600">
            No hay historial de auditoría para este préstamo
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {auditoria.map(entry => (
        <Card key={entry.id} className="border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <div className="mb-3 flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div
                  className={`rounded border px-2 py-1 text-xs font-semibold ${getAccionColor(entry.accion)}`}
                >
                  {entry.accion}
                </div>

                <span className="font-mono text-xs text-gray-500">
                  {entry.campo_modificado}
                </span>
              </div>

              <div className="flex items-center text-xs text-gray-500">
                <Calendar className="mr-1 h-3 w-3" />

                {formatDate(new Date(entry.fecha_cambio), 'dd/MM/yyyy HH:mm')}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
              <div className="flex items-start space-x-2">
                <User className="mt-0.5 h-4 w-4 text-gray-400" />

                <div>
                  <span className="font-medium text-gray-600">Usuario:</span>

                  <p className="text-gray-800">{entry.usuario}</p>
                </div>
              </div>

              {entry.estado_anterior && entry.estado_nuevo && (
                <div className="mb-2 flex items-start space-x-2">
                  <Edit className="mt-0.5 h-4 w-4 text-blue-500" />

                  <div className="flex-1">
                    <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                      Cambio de estado
                    </span>

                    <div className="mt-1 flex items-center space-x-3">
                      <span className="rounded-md border border-red-200 bg-red-50 px-3 py-1 font-medium text-red-700">
                        {entry.estado_anterior}
                      </span>

                      <span className="text-gray-400">â†'</span>

                      <span className="rounded-md border border-green-200 bg-green-50 px-3 py-1 font-medium text-green-700">
                        {entry.estado_nuevo}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {entry.valor_anterior && entry.valor_nuevo && (
              <div className="mt-3 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Detalles del cambio
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                    <div className="mb-1 text-xs font-semibold text-red-600">
                      VALOR ANTERIOR
                    </div>

                    <div className="break-words text-sm text-red-700">
                      {entry.valor_anterior}
                    </div>
                  </div>

                  <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                    <div className="mb-1 text-xs font-semibold text-green-600">
                      VALOR NUEVO
                    </div>

                    <div className="break-words text-sm text-green-700">
                      {entry.valor_nuevo}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {entry.observaciones && (
              <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3">
                <p className="text-sm text-blue-900">
                  <span className="font-medium">Observaciones:</span>{' '}
                  {entry.observaciones}
                </p>
              </div>
            )}

            {!entry.valor_anterior && entry.valor_nuevo && (
              <div className="mt-3">
                <span className="text-sm font-medium text-gray-600">
                  Detalles:
                </span>

                <p className="text-sm text-gray-700">{entry.valor_nuevo}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
