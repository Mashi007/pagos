import { useEffect, useRef, useState } from 'react'
import { Brain, Loader2, AlertCircle } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { useFineTuning } from '../../hooks/useFineTuning'
import { ConversationManagement } from './fineTuning/ConversationManagement'
import { ConversationForms } from './fineTuning/ConversationForms'
import { TrainingWorkflow } from './fineTuning/TrainingWorkflow'
import { StatisticsPanel } from './fineTuning/StatisticsPanel'
import { MINIMO_CONVERSACIONES_ENTRENAMIENTO, detectarFeedbackNegativo } from '../../constants/fineTuning'
import { toast } from 'sonner'

export function FineTuningTab() {
  // Main hook for all data and handlers
  const {
    conversaciones,
    jobs,
    estadisticasFeedback,
    cargando,
    cargandoJobs,
    cargandoEstadisticas,
    tiempoActual,
    tablasYCampos,
    cargandoTablasCampos,
    ultimaActualizacion,
    handlers,
  } = useFineTuning()

  // Local UI state
  const [mostrarEstadisticas, setMostrarEstadisticas] = useState(false)
  const [filtrarFeedbackNegativo, setFiltrarFeedbackNegativo] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Calculate statistics for training readiness
  const conversacionesListasCount = conversaciones.filter(
    (c) => c.calificacion && c.calificacion >= 3
  ).length

  let conversacionesConFeedbackNegativo = 0
  let conversacionesDespuesFiltrado = conversacionesListasCount
  if (filtrarFeedbackNegativo && conversacionesListasCount > 0) {
    const conversacionesListas = conversaciones.filter(
      (c) => c.calificacion && c.calificacion >= 3
    )
    conversacionesConFeedbackNegativo = conversacionesListas.filter((c) =>
      detectarFeedbackNegativo(c.feedback || null)
    ).length
    conversacionesDespuesFiltrado = conversacionesListasCount - conversacionesConFeedbackNegativo
  }

  // Load initial data
  useEffect(() => {
    handlers.cargarConversaciones()
    handlers.cargarJobs()
    handlers.cargarEstadisticasFeedback()
    handlers.cargarTablasCampos()
  }, [handlers])

  // Handlers that wrap the main hook handlers
  const handlePrepararDatos = async (conversacionesIds: number[], soloCalificadas: boolean) => {
    try {
      await handlers.prepararDatos(conversacionesIds, soloCalificadas)
    } catch (error) {
      console.error('Error preparing data:', error)
    }
  }

  const handleIniciarEntrenamiento = async (modeloBase: string) => {
    // In real implementation, this would use the archivo_id from prepararDatos
    const archivoId = 'archivo_generado' // This should be stored from prepararDatos
    try {
      await handlers.iniciarEntrenamiento(modeloBase, archivoId)
    } catch (error) {
      console.error('Error starting training:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6" />
            Fine-tuning
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Gestiona conversaciones y entrena modelos personalizados
          </p>
        </div>
        <Button
          variant={mostrarEstadisticas ? 'default' : 'outline'}
          onClick={() => {
            setMostrarEstadisticas(!mostrarEstadisticas)
            if (!mostrarEstadisticas) {
              handlers.cargarEstadisticasFeedback()
            }
          }}
          disabled={cargandoEstadisticas}
        >
          {cargandoEstadisticas ? (
            <>
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              Cargando...
            </>
          ) : (
            'Ver Estadísticas'
          )}
        </Button>
      </div>

      {/* Statistics Panel */}
      <StatisticsPanel
        estadisticasFeedback={estadisticasFeedback}
        mostrar={mostrarEstadisticas}
        onClose={() => setMostrarEstadisticas(false)}
      />

      {/* Data Validation Alert */}
      {conversacionesListasCount > 0 && conversacionesListasCount < MINIMO_CONVERSACIONES_ENTRENAMIENTO && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium mb-1">Conversaciones insuficientes para entrenamiento</p>
              <p>
                Tienes {conversacionesListasCount} conversaciones calificadas. Se necesitan al menos{' '}
                {MINIMO_CONVERSACIONES_ENTRENAMIENTO} para entrenar un modelo.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Conversation Management */}
      <Card>
        <CardContent className="pt-6">
          <h4 className="font-semibold text-lg mb-4">Conversaciones Disponibles</h4>
          <ConversationManagement
            conversaciones={conversaciones}
            cargando={cargando}
            onRate={handlers.calificar}
            onDelete={handlers.eliminarConversacion}
            onEdit={handlers.actualizarConversacion}
            onExport={handlers.exportarConversaciones}
            onImport={handlers.importarConversaciones}
            fileInputRef={fileInputRef}
          />
        </CardContent>
      </Card>

      {/* Conversation Forms */}
      <ConversationForms
        tablasYCampos={tablasYCampos}
        cargandoTablasCampos={cargandoTablasCampos}
        ultimaActualizacion={ultimaActualizacion}
        onCargarTablasCampos={handlers.cargarTablasCampos}
        onCreate={handlers.crearConversacion}
        onMejorarPregunta={handlers.mejorarPregunta}
        onMejorarRespuesta={handlers.mejorarRespuesta}
        onMejorarConversacion={handlers.mejorarConversacionCompleta}
      />

      {/* Training Workflow */}
      <TrainingWorkflow
        jobs={jobs}
        cargandoJobs={cargandoJobs}
        tiempoActual={tiempoActual}
        conversacionesListasCount={conversacionesListasCount}
        conversacionesDespuesFiltrado={conversacionesDespuesFiltrado}
        filtrarFeedbackNegativo={filtrarFeedbackNegativo}
        onCargarJobs={handlers.cargarJobs}
        onPrepararDatos={handlePrepararDatos}
        onIniciarEntrenamiento={handleIniciarEntrenamiento}
        onActivarModelo={handlers.activarModelo}
        onCancelarJob={handlers.cancelarJob}
        onEliminarJob={handlers.eliminarJob}
        onEliminarTodosJobs={handlers.eliminarTodosJobs}
        onToggleFiltro={setFiltrarFeedbackNegativo}
      />
    </div>
  )
}
