import { useState, useEffect } from 'react'
import { X, CheckCircle, XCircle, Loader2, Search, Filter, Zap, AlertCircle } from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

interface CalificacionChat {
  id: number
  pregunta: string
  respuesta_ai: string
  calificacion: 'arriba' | 'abajo'
  usuario_email: string | null
  procesado: boolean
  notas_procesamiento: string | null
  mejorado: boolean
  creado_en: string
  actualizado_en: string
}

export function CalificacionesChatTab() {
  const [calificaciones, setCalificaciones] = useState<CalificacionChat[]>([])
  const [cargando, setCargando] = useState(false)
  const [filtroCalificacion, setFiltroCalificacion] = useState<string>('abajo')
  const [filtroProcesado, setFiltroProcesado] = useState<string>('no-procesadas')
  const [busqueda, setBusqueda] = useState('')
  const [mostrarModalProcesar, setMostrarModalProcesar] = useState(false)
  const [calificacionSeleccionada, setCalificacionSeleccionada] = useState<CalificacionChat | null>(null)
  const [procesando, setProcesando] = useState(false)
  const [notasProcesamiento, setNotasProcesamiento] = useState('')

  useEffect(() => {
    cargarCalificaciones()
  }, [filtroCalificacion, filtroProcesado])

  const cargarCalificaciones = async () => {
    setCargando(true)
    try {
      const params = new URLSearchParams()
      if (filtroCalificacion !== 'todas') {
        params.append('calificacion', filtroCalificacion)
      }
      if (filtroProcesado === 'procesadas') {
        params.append('procesado', 'true')
      } else if (filtroProcesado === 'no-procesadas') {
        params.append('procesado', 'false')
      }

      const response = await apiClient.get<{ calificaciones: CalificacionChat[], total: number }>(
        `/api/v1/configuracion/ai/chat/calificaciones?${params.toString()}`
      )
      setCalificaciones(response.calificaciones || [])
    } catch (error: any) {
      console.error('Error cargando calificaciones:', error)
      if (error?.response?.status !== 503) {
        toast.error('Error al cargar las calificaciones')
      }
    } finally {
      setCargando(false)
    }
  }

  const handleProcesar = (calificacion: CalificacionChat) => {
    setCalificacionSeleccionada(calificacion)
    setNotasProcesamiento(calificacion.notas_procesamiento || '')
    setMostrarModalProcesar(true)
  }

  const handleGuardarProcesamiento = async () => {
    if (!calificacionSeleccionada) return

    setProcesando(true)
    try {
      await apiClient.put(
        `/api/v1/configuracion/ai/chat/calificaciones/${calificacionSeleccionada.id}/procesar`,
        { notas: notasProcesamiento }
      )
      toast.success('CalificaciÃ³n marcada como procesada')
      setMostrarModalProcesar(false)
      setCalificacionSeleccionada(null)
      setNotasProcesamiento('')
      cargarCalificaciones()
    } catch (error: any) {
      console.error('Error procesando calificaciÃ³n:', error)
      toast.error(error?.response?.data?.detail || 'Error al procesar calificaciÃ³n')
    } finally {
      setProcesando(false)
    }
  }

  const calificacionesFiltradas = calificaciones.filter(cal => {
    const coincideBusqueda = !busqueda || 
      cal.pregunta.toLowerCase().includes(busqueda.toLowerCase()) ||
      cal.respuesta_ai.toLowerCase().includes(busqueda.toLowerCase())
    return coincideBusqueda
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <X className="h-6 w-6 text-red-600" />
            Calificaciones del Chat AI
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Revisa las respuestas con pulgar abajo para mejorar la precisiÃ³n del sistema
          </p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por pregunta o respuesta..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filtroCalificacion} onValueChange={setFiltroCalificacion}>
              <SelectTrigger className="w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="CalificaciÃ³n" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="arriba">Pulgar Arriba</SelectItem>
                <SelectItem value="abajo">Pulgar Abajo</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filtroProcesado} onValueChange={setFiltroProcesado}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="no-procesadas">No Procesadas</SelectItem>
                <SelectItem value="procesadas">Procesadas</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Lista de Calificaciones */}
      {cargando ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-red-600" />
        </div>
      ) : calificacionesFiltradas.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <X className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600">
              {busqueda || filtroCalificacion !== 'todas' || filtroProcesado !== 'todas'
                ? 'No se encontraron calificaciones con los filtros aplicados'
                : 'No hay calificaciones registradas aÃºn'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {calificacionesFiltradas.map(cal => (
            <Card key={cal.id} className={cal.calificacion === 'abajo' ? 'border-red-200' : 'border-green-200'}>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {cal.calificacion === 'arriba' ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Pulgar Arriba
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                          <X className="h-3 w-3 mr-1" />
                          Pulgar Abajo
                        </Badge>
                      )}
                      {cal.procesado && (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Procesada
                        </Badge>
                      )}
                      {!cal.procesado && cal.calificacion === 'abajo' && (
                        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Pendiente
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(cal.creado_en).toLocaleString('es-ES')}
                    </div>
                  </div>

                  {/* Pregunta */}
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <h4 className="font-medium text-sm text-blue-900 mb-1">Pregunta del Usuario:</h4>
                    <p className="text-blue-800">{cal.pregunta}</p>
                  </div>

                  {/* Respuesta AI */}
                  <div className={`p-3 rounded-lg ${cal.calificacion === 'abajo' ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
                    <h4 className="font-medium text-sm text-gray-900 mb-1">Respuesta del AI:</h4>
                    <p className="text-gray-700 whitespace-pre-wrap">{cal.respuesta_ai}</p>
                  </div>

                  {/* Notas de Procesamiento */}
                  {cal.notas_procesamiento && (
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                      <h4 className="font-medium text-sm text-gray-900 mb-1">Notas de Procesamiento:</h4>
                      <p className="text-gray-700 text-sm">{cal.notas_procesamiento}</p>
                    </div>
                  )}

                  {/* Acciones */}
                  {cal.calificacion === 'abajo' && !cal.procesado && (
                    <div className="flex justify-end gap-2 pt-2 border-t">
                      <Button
                        variant="outline"
                        onClick={() => handleProcesar(cal)}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        <Zap className="h-4 w-4 mr-2" />
                        Procesar y Mejorar
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modal de Procesamiento */}
      <Dialog open={mostrarModalProcesar} onOpenChange={setMostrarModalProcesar}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-600" />
              Procesar CalificaciÃ³n Negativa
            </DialogTitle>
            <DialogDescription>
              Analiza esta interacciÃ³n para mejorar el sistema
            </DialogDescription>
          </DialogHeader>

          {calificacionSeleccionada && (
            <div className="space-y-4 mt-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-medium text-sm text-blue-900 mb-2">Pregunta:</h4>
                <p className="text-blue-800">{calificacionSeleccionada.pregunta}</p>
              </div>

              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <h4 className="font-medium text-sm text-red-900 mb-2">Respuesta del AI:</h4>
                <p className="text-red-800 whitespace-pre-wrap">{calificacionSeleccionada.respuesta_ai}</p>
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">
                  Notas de Procesamiento:
                </label>
                <Textarea
                  value={notasProcesamiento}
                  onChange={(e) => setNotasProcesamiento(e.target.value)}
                  placeholder="Describe quÃ© se mejorÃ³ o quÃ© acciones se tomaron para evitar este error en el futuro..."
                  rows={4}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => {
                  setMostrarModalProcesar(false)
                  setCalificacionSeleccionada(null)
                  setNotasProcesamiento('')
                }}>
                  Cancelar
                </Button>
                <Button
                  onClick={handleGuardarProcesamiento}
                  disabled={procesando}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {procesando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Marcar como Procesada
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
