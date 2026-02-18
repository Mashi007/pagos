import { useState } from 'react'
import {
  Brain,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Trash2,
  AlertCircle,
  Download,
  Filter,
} from 'lucide-react'
import { Card, CardContent } from '../../ui/card'
import { Button } from '../../ui/button'
import { Badge } from '../../ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { FineTuningJob } from '../../../services/aiTrainingService'
import { MINIMO_CONVERSACIONES_ENTRENAMIENTO, detectarFeedbackNegativo } from '../../../constants/fineTuning'
import { toast } from 'sonner'

export interface TrainingWorkflowProps {
  jobs: FineTuningJob[]
  cargandoJobs: boolean
  tiempoActual: Date
  conversacionesListasCount: number
  conversacionesDespuesFiltrado: number
  filtrarFeedbackNegativo: boolean
  onCargarJobs: () => Promise<void>
  onPrepararDatos: (conversacionesIds: number[], soloCalificadas: boolean) => Promise<void>
  onIniciarEntrenamiento: (modeloBase: string) => Promise<void>
  onActivarModelo: (modeloId: string) => Promise<void>
  onCancelarJob: (jobId: string) => Promise<void>
  onEliminarJob: (jobId: string) => Promise<void>
  onEliminarTodosJobs: (soloFallidos: boolean) => Promise<void>
  onToggleFiltro: (value: boolean) => void
}

export function TrainingWorkflow({
  jobs,
  cargandoJobs,
  tiempoActual,
  conversacionesListasCount,
  conversacionesDespuesFiltrado,
  filtrarFeedbackNegativo,
  onCargarJobs,
  onPrepararDatos,
  onIniciarEntrenamiento,
  onActivarModelo,
  onCancelarJob,
  onEliminarJob,
  onEliminarTodosJobs,
  onToggleFiltro,
}: TrainingWorkflowProps) {
  const [mostrarFormEntrenamiento, setMostrarFormEntrenamiento] = useState(false)
  const [modeloBase, setModeloBase] = useState('gpt-4o-2024-08-06')
  const [entrenando, setEntrenando] = useState(false)
  const [preparando, setPreparando] = useState(false)

  const puedePreparar = conversacionesListasCount >= MINIMO_CONVERSACIONES_ENTRENAMIENTO
  const puedePrepararDespuesFiltrado =
    conversacionesDespuesFiltrado >= MINIMO_CONVERSACIONES_ENTRENAMIENTO

  const handlePrepararDatos = async () => {
    setPreparando(true)
    try {
      const conversacionesSeleccionadas = Array.from(
        { length: conversacionesListasCount },
        (_, i) => i + 1
      )
      await onPrepararDatos(conversacionesSeleccionadas, filtrarFeedbackNegativo)
    } finally {
      setPreparando(false)
    }
  }

  const handleIniciarEntrenamiento = async () => {
    setEntrenando(true)
    try {
      await onIniciarEntrenamiento(modeloBase)
      setMostrarFormEntrenamiento(false)
    } finally {
      setEntrenando(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: { variant: 'secondary' as const, icon: Clock, text: 'Pendiente' },
      running: { variant: 'default' as const, icon: Loader2, text: 'Ejecutando' },
      succeeded: { variant: 'default' as const, icon: CheckCircle, text: 'Exitoso' },
      failed: { variant: 'destructive' as const, icon: XCircle, text: 'Fallido' },
      cancelled: { variant: 'secondary' as const, icon: XCircle, text: 'Cancelado' },
    }

    const config = variants[status] || variants.pending
    const Icon = config.icon

    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        {status === 'running' && <Icon className="h-3 w-3 animate-spin" />}
        {status !== 'running' && <Icon className="h-3 w-3" />}
        {config.text}
      </Badge>
    )
  }

  const getJobDuration = (job: FineTuningJob) => {
    if (job.status === 'succeeded' || job.status === 'failed' || job.status === 'cancelled') {
      if (job.finalizado_en) {
        const inicio = new Date(job.creado_en).getTime()
        const fin = new Date(job.finalizado_en).getTime()
        const duracionMs = fin - inicio
        const horas = Math.floor(duracionMs / 3600000)
        const minutos = Math.floor((duracionMs % 3600000) / 60000)
        return `${horas}h ${minutos}m`
      }
    } else {
      const ahora = tiempoActual
      const inicio = new Date(job.creado_en)
      const tiempoTranscurridoMs = ahora.getTime() - inicio.getTime()
      const minutosTranscurridos = Math.floor(tiempoTranscurridoMs / 60000)
      const horasTranscurridas = Math.floor(minutosTranscurridos / 60)
      return `${horasTranscurridas}h ${minutosTranscurridos % 60}m`
    }
    return 'N/A'
  }

  return (
    <div className="space-y-6">
      {/* Data Preparation Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <Download className="h-5 w-5" />
              Preparación de Datos
            </h4>

            <div className="space-y-2">
              {conversacionesListasCount > 0 && (
                <Badge variant={puedePreparar ? 'default' : 'secondary'} className="mr-2">
                  {conversacionesListasCount} lista
                  {conversacionesListasCount !== 1 ? 's' : ''} para entrenamiento
                  {!puedePreparar &&
                    conversacionesListasCount < MINIMO_CONVERSACIONES_ENTRENAMIENTO &&
                    ` (${MINIMO_CONVERSACIONES_ENTRENAMIENTO - conversacionesListasCount} más necesaria${MINIMO_CONVERSACIONES_ENTRENAMIENTO - conversacionesListasCount !== 1 ? 's' : ''})`}
                </Badge>
              )}

              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-600 flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={filtrarFeedbackNegativo}
                    onChange={(e) => onToggleFiltro(e.target.checked)}
                    className="rounded"
                  />
                  Filtrar feedback negativo
                </label>
              </div>
            </div>

            <Button
              onClick={handlePrepararDatos}
              disabled={preparando || !puedePreparar}
              variant={puedePreparar ? 'default' : 'outline'}
              className="w-full"
            >
              {preparando ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Preparando...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Preparar Datos para Entrenamiento
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Training Form */}
      {mostrarFormEntrenamiento && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Iniciar Entrenamiento</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Modelo Base</label>
                <Select value={modeloBase} onValueChange={setModeloBase}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4o-2024-08-06">
                      gpt-4o-2024-08-06 (Recomendado)
                    </SelectItem>
                    <SelectItem value="gpt-4o">gpt-4o (Puede no estar disponible)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleIniciarEntrenamiento} disabled={entrenando} className="flex-1">
                  {entrenando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Iniciando...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Iniciar Entrenamiento
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setMostrarFormEntrenamiento(false)}
                  className="flex-1"
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!mostrarFormEntrenamiento && (
        <Button
          onClick={() => setMostrarFormEntrenamiento(true)}
          className="w-full gap-2"
          variant="outline"
        >
          <Play className="h-4 w-4" />
          Iniciar Nuevo Entrenamiento
        </Button>
      )}

      {/* Training Jobs */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Jobs de Entrenamiento
            </h4>
            <div className="flex gap-2">
              {jobs.some((job) => job.status === 'failed' || job.status === 'cancelled') && (
                <Button
                  onClick={() => onEliminarTodosJobs(true)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Eliminar Fallidos
                </Button>
              )}
              {jobs.some(
                (job) => job.status !== 'pending' && job.status !== 'running'
              ) && (
                <Button
                  onClick={() => onEliminarTodosJobs(false)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Limpiar Todo
                </Button>
              )}
              <Button onClick={onCargarJobs} variant="outline" size="sm" disabled={cargandoJobs}>
                {cargandoJobs ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Actualizando...
                  </>
                ) : (
                  'Actualizar'
                )}
              </Button>
            </div>
          </div>

          {jobs.some((job) => job.status === 'pending' || job.status === 'running') && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-800">
                  El entrenamiento puede tardar varias horas. Este proceso continuará en segundo plano
                  incluso si cierras esta página.
                </p>
              </div>
            </div>
          )}

          {jobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No hay jobs de entrenamiento</p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm">{job.id}</span>
                        {getStatusBadge(job.status)}
                      </div>
                      <p className="text-xs text-gray-600">
                        Modelo base: {job.modelo_base || 'N/A'} • Creado: {new Date(job.creado_en).toLocaleString('es-ES')}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{getJobDuration(job)}</p>
                      <p className="text-xs text-gray-500">
                        {job.status === 'running' && 'en progreso'}
                        {job.status === 'pending' && 'en espera'}
                        {job.status === 'succeeded' && job.modelo_id && `Modelo: ${job.modelo_id}`}
                      </p>
                    </div>
                  </div>

                  {job.status === 'succeeded' && job.modelo_id && (
                    <Button
                      onClick={() => onActivarModelo(job.modelo_id!)}
                      size="sm"
                      className="w-full"
                      variant="outline"
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Activar Modelo
                    </Button>
                  )}

                  <div className="flex gap-2 pt-2 border-t">
                    {job.status === 'running' && (
                      <Button
                        onClick={() => onCancelarJob(job.id)}
                        size="sm"
                        variant="destructive"
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                    )}
                    <Button
                      onClick={() => onEliminarJob(job.id)}
                      size="sm"
                      variant="outline"
                      className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      Eliminar
                    </Button>
                  </div>

                  {job.mensaje_error && (
                    <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                      Error: {job.mensaje_error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
