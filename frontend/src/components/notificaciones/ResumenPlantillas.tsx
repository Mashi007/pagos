import { useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { notificacionService, NotificacionPlantilla } from '../../services/notificacionService'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Badge } from '../../components/ui/badge'
import { Edit2, Trash2, FileText, Calendar, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'

interface ResumenPlantillasProps {
  onEditarPlantilla?: (plantilla: NotificacionPlantilla) => void
  onCambiarPestaÃÂ±a?: (pestaÃÂ±a: string) => void
  activeTab?: string
}

// Mapeo de tipos a categorÃÂ­as y casos
const mapeoTipos = {
  'PAGO_5_DIAS_ANTES': { categoria: 'NotificaciÃÂ³n Previa', caso: '5 dÃÂ­as antes' },
  'PAGO_3_DIAS_ANTES': { categoria: 'NotificaciÃÂ³n Previa', caso: '3 dÃÂ­as antes' },
  'PAGO_1_DIA_ANTES': { categoria: 'NotificaciÃÂ³n Previa', caso: '1 dÃÂ­a antes' },
  'PAGO_DIA_0': { categoria: 'DÃÂ­a de Pago', caso: 'DÃÂ­a de pago' },
  'PAGO_1_DIA_ATRASADO': { categoria: 'NotificaciÃÂ³n Retrasada', caso: '1 dÃÂ­a de retraso' },
  'PAGO_3_DIAS_ATRASADO': { categoria: 'NotificaciÃÂ³n Retrasada', caso: '3 dÃÂ­as de retraso' },
  'PAGO_5_DIAS_ATRASADO': { categoria: 'NotificaciÃÂ³n Retrasada', caso: '5 dÃÂ­as de retraso' },
  'PREJUDICIAL': { categoria: 'Prejudicial', caso: 'Prejudicial' },
}

const categoriasOrden = [
  { key: 'NotificaciÃÂ³n Previa', color: 'blue', icon: 'ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ¦' },
  { key: 'DÃÂ­a de Pago', color: 'green', icon: 'ÃÂ°ÃÂ¸Ã¢ÂÂÃÂ°' },
  { key: 'NotificaciÃÂ³n Retrasada', color: 'orange', icon: 'ÃÂ¢ÃÂ¡ ÃÂ¯ÃÂ¸ÃÂ' },
  { key: 'Prejudicial', color: 'red', icon: 'ÃÂ°ÃÂ¸ÃÂ¡ÃÂ¨' },
]

export function ResumenPlantillas({ onEditarPlantilla, onCambiarPestaÃÂ±a, activeTab }: ResumenPlantillasProps) {
  const queryClient = useQueryClient()
  const { data: plantillas = [], isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,
    queryFn: () => notificacionService.listarPlantillas(undefined, false),
    staleTime: 1 * 60 * 1000,
    placeholderData: [] as NotificacionPlantilla[],
  })

  // Organizar plantillas por categorÃÂ­a
  const plantillasPorCategoria = useMemo(() => {
    const organizadas: Record<string, NotificacionPlantilla[]> = {}

    plantillas.forEach(plantilla => {
      const mapeo = mapeoTipos[plantilla.tipo as keyof typeof mapeoTipos]
      if (mapeo) {
        const categoria = mapeo.categoria
        if (!organizadas[categoria]) {
          organizadas[categoria] = []
        }
        organizadas[categoria].push(plantilla)
      }
    })

    // Ordenar plantillas dentro de cada categorÃÂ­a por caso
    Object.keys(organizadas).forEach(categoria => {
      organizadas[categoria].sort((a, b) => {
        const casoA = mapeoTipos[a.tipo as keyof typeof mapeoTipos]?.caso || ''
        const casoB = mapeoTipos[b.tipo as keyof typeof mapeoTipos]?.caso || ''
        return casoA.localeCompare(casoB)
      })
    })

    return organizadas
  }, [plantillas])

  const formatearFecha = (fecha: string | null | undefined) => {
    if (!fecha) return '-'
    try {
      const date = new Date(fecha)
      return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return fecha
    }
  }

  const handleEditar = (plantilla: NotificacionPlantilla) => {
    if (onEditarPlantilla) {
      onEditarPlantilla(plantilla)
    }
    if (onCambiarPestaÃÂ±a) {
      onCambiarPestaÃÂ±a('plantillas')
    }
  }

  const handleEliminar = async (plantilla: NotificacionPlantilla) => {
    if (!window.confirm(`ÃÂ¿EstÃÂ¡ seguro de eliminar la plantilla "${plantilla.nombre}"?`)) {
      return
    }

    try {
      await notificacionService.eliminarPlantilla(plantilla.id)
      toast.success('Plantilla eliminada exitosamente')
      await queryClient.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas })
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al eliminar plantilla')
    }
  }

  const obtenerColorCategoria = (categoria: string) => {
    const cat = categoriasOrden.find(c => c.key === categoria)
    return cat?.color || 'gray'
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Resumen de Plantillas por Caso
          </CardTitle>
          <CardDescription>
            VisualizaciÃÂ³n organizada de todas las plantillas almacenadas, clasificadas por tipo de notificaciÃÂ³n y caso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Cargando plantillas...</div>
          ) : plantillas.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No hay plantillas configuradas.</p>
              <p className="text-sm mt-2">Vaya a la pestaÃÂ±a "Plantillas" para crear nuevas plantillas.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {categoriasOrden.map(categoriaInfo => {
                const categoria = categoriaInfo.key
                const plantillasCategoria = plantillasPorCategoria[categoria] || []

                if (plantillasCategoria.length === 0) return null

                return (
                  <Card key={categoria} className="border-l-4" style={{ borderLeftColor: `var(--color-${categoriaInfo.color}-500)` }}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <span>{categoriaInfo.icon}</span>
                        {categoria}
                        <Badge variant="outline" className="ml-2">
                          {plantillasCategoria.length} plantilla(s)
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Tipo</TableHead>
                              <TableHead>Caso</TableHead>
                              <TableHead>Fecha ActualizaciÃÂ³n</TableHead>
                              <TableHead>Archivo / Plantilla</TableHead>
                              <TableHead>Estado</TableHead>
                              <TableHead className="text-right">Acciones</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {plantillasCategoria.map(plantilla => {
                              const mapeo = mapeoTipos[plantilla.tipo as keyof typeof mapeoTipos]
                              return (
                                <TableRow key={plantilla.id}>
                                  <TableCell className="font-medium">
                                    {mapeo?.categoria || plantilla.tipo}
                                  </TableCell>
                                  <TableCell>
                                    <Badge variant="outline">{mapeo?.caso || plantilla.tipo}</Badge>
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex items-center gap-1 text-sm text-gray-600">
                                      <Calendar className="h-3 w-3" />
                                      {formatearFecha(plantilla.fecha_actualizacion)}
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    <div className="max-w-xs">
                                      <div className="font-medium text-sm truncate" title={plantilla.nombre}>
                                        {plantilla.nombre}
                                      </div>
                                      <div className="text-xs text-gray-500 truncate" title={plantilla.asunto}>
                                        {plantilla.asunto || 'Sin asunto'}
                                      </div>
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    {plantilla.activa ? (
                                      <Badge variant="success">Activa</Badge>
                                    ) : (
                                      <Badge variant="secondary">Inactiva</Badge>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleEditar(plantilla)}
                                        title="Editar plantilla"
                                      >
                                        <Edit2 className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleEliminar(plantilla)}
                                        title="Eliminar plantilla"
                                      >
                                        <Trash2 className="h-4 w-4 text-red-500" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              )
                            })}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

