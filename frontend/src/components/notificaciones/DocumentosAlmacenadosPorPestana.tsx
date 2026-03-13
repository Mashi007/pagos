import { useState, useEffect } from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { Loader2, Trash2, FileText } from 'lucide-react'

export const TIPOS_CASO_DOCS: { value: string; label: string }[] = [
  { value: 'dias_5', label: 'Faltan 5' },
  { value: 'dias_3', label: 'Faltan 3' },
  { value: 'dias_1', label: 'Falta 1' },
  { value: 'hoy', label: 'Hoy vence' },
  { value: 'dias_1_retraso', label: '1 día retraso' },
  { value: 'dias_3_retraso', label: '3 días retraso' },
  { value: 'dias_5_retraso', label: '5 días retraso' },
  { value: 'prejudicial', label: 'Prejudicial' },
  { value: 'mora_90', label: '90+ mora' },
]

type AdjuntoItem = { id: string; nombre_archivo: string; ruta: string }

interface DocumentosAlmacenadosPorPestanaProps {
  /** Si true, muestra botón eliminar en cada documento. Por defecto true. */
  permitirEliminar?: boolean
  /** Título de la sección. Por defecto "Documentos almacenados por pestaña". */
  titulo?: string
  /** Clase CSS adicional para el contenedor. */
  className?: string
}

export function DocumentosAlmacenadosPorPestana({
  permitirEliminar = true,
  titulo = 'Documentos almacenados por pestaña',
  className = '',
}: DocumentosAlmacenadosPorPestanaProps) {
  const [porCaso, setPorCaso] = useState<Record<string, AdjuntoItem[]>>({})
  const [loading, setLoading] = useState(true)
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const cargar = () => {
    setLoading(true)
    notificacionService
      .getAdjuntosFijosCobranza()
      .then((data) => setPorCaso(data || {}))
      .catch(() => toast.error('Error al cargar documentos anexos.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    cargar()
  }, [])

  const handleEliminar = async (id: string) => {
    setEliminandoId(id)
    try {
      await notificacionService.deleteAdjuntoFijoCobranza(id)
      toast.success('Documento eliminado.')
      cargar()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
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

  const tieneAlguno = TIPOS_CASO_DOCS.some((t) => (porCaso[t.value]?.length ?? 0) > 0)

  return (
    <Card className={className}>
      <CardContent className="pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-1">{titulo}</h4>
        <p className="text-xs text-muted-foreground mb-3">
          Cada documento se adjunta solo a la notificación de la pestaña indicada (ej. los de «1 día retraso» van con ese tipo de aviso).
        </p>
        <div className="space-y-3">
          {TIPOS_CASO_DOCS.map(({ value, label }) => {
            const items = porCaso[value] || []
            if (items.length === 0) return null
            return (
              <div key={value} className="rounded-md border bg-gray-50/50 p-3">
                <span className="text-sm font-medium text-gray-600" title={`Se envían con la notificación: ${label}`}>
                  {label}
                </span>
                <ul className="mt-2 space-y-1">
                  {items.map((doc) => (
                    <li key={doc.id} className="flex items-center justify-between gap-2 text-sm">
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
            )
          })}
          {!tieneAlguno && (
            <p className="text-sm text-gray-500">Aún no hay documentos. Sube un PDF en la pestaña «Documentos PDF anexos» y elige la pestaña.</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
