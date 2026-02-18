/**
 * AI Training Types and Interfaces
 */

export interface ConversacionAI {
  id: number
  pregunta: string
  respuesta: string
  calificacion?: number
  feedback?: string
  usuario_creacion?: string
  fecha_creacion?: string
}

export interface FineTuningJob {
  id: number
  nombre?: string
  estado: 'pendiente' | 'en_progreso' | 'completado' | 'fallido'
  fecha_creacion: string
  fecha_inicio?: string
  fecha_fin?: string
  finalizado_en?: string | Date | null
  modelo_id?: string | null
  mensaje_error?: string | null
  archivo_id?: string
  porcentaje_completado?: number
  total_conversaciones?: number
  conversaciones_procesadas?: number
  usuario_creacion?: string
}

export interface ConversationManagementProps {
  conversaciones: ConversacionAI[]
  cargando: boolean
  onAddNew?: () => void
  onEdit?: (conversacionId: number) => void
  onDelete?: (conversacionId: number) => void
  onRate?: (conversacionId: number, calificacion: number) => void
}

export interface ConversationFormsProps {
  mostrarForm: boolean
  cargando: boolean
  onClose?: () => void
  onSubmit?: (data: any) => void
  editandoId?: number | null
}

export interface StatisticsPanelProps {
  estadisticas: any
  cargando: boolean
}

export interface TrainingWorkflowProps {
  jobs: FineTuningJob[]
  cargando: boolean
  onStartTraining?: () => void
  onCancelJob?: (jobId: number) => void
  onDeleteJob?: (jobId: number) => void
  onActivateModel?: (modeloId: string) => void
}

export interface MejoraConversacionRequest {
  tipo: 'pregunta' | 'respuesta' | 'conversacion'
  pregunta?: string
  respuesta?: string
}

export interface PrepararDatosResponse {
  archivo_id: string
  total_conversaciones: number
  num_conversaciones?: number // alias para total_conversaciones
  conversaciones_originales?: number
  conversaciones_excluidas?: number
  detalles_exclusion?: Array<{
    id: number
    razon: string
    feedback: string
  }>
}
