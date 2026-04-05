import { useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { Card, CardContent } from '../ui/card'

import { Button } from '../ui/button'

import { notificacionService } from '../../services/notificacionService'

import { toast } from 'sonner'

import { Loader2, Trash2, FileText } from 'lucide-react'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

import { listarCasosConAdjuntosGuardados } from '../../constants/adjuntosFijosCasoTab'

/** @deprecated Usar TIPOS_CASO_ADJUNTO_SUBIDA desde constants/adjuntosFijosCasoTab */
export { TIPOS_CASO_ADJUNTO_SUBIDA as TIPOS_CASO_DOCS } from '../../constants/adjuntosFijosCasoTab'

type AdjuntoItem = { id: string; nombre_archivo: string; ruta: string }

interface DocumentosAlmacenadosPorPestanaProps {
  /** Si true, muestra botón eliminar en cada documento. Por defecto true. */

  permitirEliminar?: boolean

  /** Título de la sección. Por defecto "Documentos almacenados por caso". */

  titulo?: string

  /** Clase CSS adicional para el contenedor. */

  className?: string

  /** Si true, al mostrarse la pestaña se vuelve a cargar la lista. */

  tabActivo?: boolean
}

export function DocumentosAlmacenadosPorPestana({
  permitirEliminar = true,

  titulo = 'Documentos almacenados por caso',

  className = '',

  tabActivo = true,
}: DocumentosAlmacenadosPorPestanaProps) {
  const queryClient = useQueryClient()

  const { data: porCaso = {}, isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,

    queryFn: () => notificacionService.getAdjuntosFijosCobranza(),

    staleTime: 1 * 60 * 1000,
  })

  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const handleEliminar = async (id: string) => {
    setEliminandoId(id)

    try {
      await notificacionService.deleteAdjuntoFijoCobranza(id)

      toast.success('Documento eliminado.')

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail

      toast.error(msg || 'Error al eliminar.')
    } finally {
      setEliminandoId(null)
    }
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </CardContent>
      </Card>
    )
  }

  const casosConDocs = listarCasosConAdjuntosGuardados(porCaso)

  const tieneAlguno = casosConDocs.length > 0

  return (
    <Card className={className}>
      <CardContent className="pt-4">
        <h4 className="mb-1 text-sm font-medium text-gray-700">{titulo}</h4>

        <p className="mb-3 text-xs text-muted-foreground">
          Cada documento se adjunta solo al caso de envío indicado (pestaña /
          criterio de notificación).
        </p>

        <div className="space-y-3">
          {casosConDocs.map(({ value, label, items }) => (
            <div key={value} className="rounded-md border bg-gray-50/50 p-3">
              <span
                className="text-sm font-medium text-gray-600"
                title={'Se envían con la notificación: ' + label}
              >
                {label}
              </span>

              <ul className="mt-2 space-y-1">
                {items.map(doc => (
                    <li
                      key={doc.id}
                      className="flex items-center justify-between gap-2 text-sm"
                    >
                      <span className="flex items-center gap-2 truncate">
                        <FileText className="h-4 w-4 shrink-0 text-gray-500" />

                        {doc.nombre_archivo}
                      </span>

                      {permitirEliminar && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEliminar(doc.id)}
                          disabled={eliminandoId === doc.id}
                          aria-label={'Eliminar ' + doc.nombre_archivo}
                        >
                          {eliminandoId === doc.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-red-600" />
                          )}
                        </Button>
                      )}
                    </li>
                ))}
              </ul>
            </div>
          ))}

          {!tieneAlguno && (
            <p className="text-sm text-gray-500">
              No hay documentos vinculados a casos. Sube un PDF en «Documentos
              PDF anexos», elige el caso de envío y pulsa Subir; se guardarán y
              aparecerán aquí.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
