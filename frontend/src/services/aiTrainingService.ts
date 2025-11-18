import { apiClient } from './api'

// ============================================
// TIPOS E INTERFACES
// ============================================

export interface ConversacionAI {
  id: number
  pregunta: string
  respuesta: string
  contexto_usado?: string
  documentos_usados?: number[]
  modelo_usado?: string
  tokens_usados?: number
  tiempo_respuesta?: number
  calificacion?: number // 1-5
  feedback?: string
  usuario_id?: number
  creado_en: string
}

export interface FineTuningJob {
  id: string
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  modelo_base: string
  modelo_entrenado?: string
  archivo_entrenamiento?: string
  progreso?: number
  error?: string
  creado_en: string
  completado_en?: string
}

export interface DocumentoEmbedding {
  documento_id: number
  embedding: number[]
  chunk_index?: number
  texto_chunk?: string
  similitud?: number
}

export interface ModeloRiesgo {
  id: number
  nombre: string
  version: string
  algoritmo: string
  accuracy?: number
  precision?: number
  recall?: number
  f1_score?: number
  roc_auc?: number
  entrenado_en: string
  activo: boolean
  total_datos_entrenamiento?: number
}

export interface ModeloImpagoCuotas {
  id: number
  nombre: string
  version: string
  algoritmo: string
  accuracy?: number
  precision?: number
  recall?: number
  f1_score?: number
  roc_auc?: number
  entrenado_en: string
  activo: boolean
  total_datos_entrenamiento?: number
}

export interface MetricasEntrenamiento {
  conversaciones: {
    total: number
    con_calificacion: number
    promedio_calificacion: number
    listas_entrenamiento: number
  }
  fine_tuning: {
    jobs_totales: number
    jobs_exitosos: number
    jobs_fallidos: number
    modelo_activo?: string
    ultimo_entrenamiento?: string
  }
  rag: {
    documentos_con_embeddings: number
    total_embeddings: number
    ultima_actualizacion?: string
  }
  ml_riesgo: {
    modelos_disponibles: number
    modelo_activo?: string
    ultimo_entrenamiento?: string
    accuracy_promedio?: number
  }
}

// ============================================
// SERVICIO DE ENTRENAMIENTO AI
// ============================================

class AITrainingService {
  private baseUrl = '/api/v1/ai/training'

  // ============================================
  // FINE-TUNING
  // ============================================

  /**
   * Obtener conversaciones para entrenamiento
   */
  async getConversaciones(params?: {
    page?: number
    per_page?: number
    con_calificacion?: boolean
    fecha_desde?: string
    fecha_hasta?: string
  }): Promise<{ conversaciones: ConversacionAI[]; total: number; page: number; total_pages: number }> {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString())
    if (params?.con_calificacion !== undefined) queryParams.append('con_calificacion', params.con_calificacion.toString())
    if (params?.fecha_desde) queryParams.append('fecha_desde', params.fecha_desde)
    if (params?.fecha_hasta) queryParams.append('fecha_hasta', params.fecha_hasta)

    const url = `${this.baseUrl}/conversaciones${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
    return await apiClient.get(url)
  }

  /**
   * Guardar conversación para entrenamiento
   */
  async guardarConversacion(conversacion: {
    pregunta: string
    respuesta: string
    contexto_usado?: string
    documentos_usados?: number[]
    modelo_usado?: string
    tokens_usados?: number
    tiempo_respuesta?: number
  }): Promise<ConversacionAI> {
    const response = await apiClient.post<{ conversacion: ConversacionAI }>(`${this.baseUrl}/conversaciones`, conversacion)
    return response.conversacion
  }

  /**
   * Calificar conversación
   */
  async calificarConversacion(
    conversacionId: number,
    calificacion: number,
    feedback?: string
  ): Promise<ConversacionAI> {
    const response = await apiClient.post<{ conversacion: ConversacionAI }>(`${this.baseUrl}/conversaciones/${conversacionId}/calificar`, {
      calificacion,
      feedback,
    })
    return response.conversacion
  }

  /**
   * Actualizar conversación existente
   */
  async actualizarConversacion(
    conversacionId: number,
    conversacion: {
      pregunta: string
      respuesta: string
      contexto_usado?: string
      documentos_usados?: number[]
      modelo_usado?: string
    }
  ): Promise<ConversacionAI> {
    const response = await apiClient.put<{ conversacion: ConversacionAI }>(`${this.baseUrl}/conversaciones/${conversacionId}`, conversacion)
    return response.conversacion
  }

  /**
   * Mejorar pregunta y/o respuesta usando IA
   */
  async mejorarConversacion(params: {
    pregunta?: string
    respuesta?: string
  }): Promise<{
    pregunta_mejorada: string
    respuesta_mejorada: string
    mejoras_aplicadas: string[]
  }> {
    return await apiClient.post(`${this.baseUrl}/conversaciones/mejorar`, params)
  }

  /**
   * Preparar datos para fine-tuning
   */
  async prepararDatosEntrenamiento(
    conversacionIds?: number[],
    filtrarFeedbackNegativo: boolean = true
  ): Promise<{
    archivo_id: string
    total_conversaciones: number
    conversaciones_originales?: number
    conversaciones_excluidas?: number
    detalles_exclusion?: Array<{ id: number; razon: string; feedback: string }>
  }> {
    const response = await apiClient.post<{
      archivo_id: string
      total_conversaciones: number
      conversaciones_originales?: number
      conversaciones_excluidas?: number
      detalles_exclusion?: Array<{ id: number; razon: string; feedback: string }>
    }>(`${this.baseUrl}/fine-tuning/preparar`, {
      conversacion_ids: conversacionIds,
      filtrar_feedback_negativo: filtrarFeedbackNegativo,
    })
    return response
  }

  /**
   * Obtener estadísticas de feedback
   */
  async getEstadisticasFeedback(): Promise<{
    total_conversaciones: number
    conversaciones_calificadas: number
    conversaciones_con_feedback: number
    distribucion_calificaciones: Record<string, number>
    analisis_feedback: {
      positivo: number
      negativo: number
      neutro: number
      total: number
    }
    conversaciones_listas_entrenamiento: {
      total: number
      sin_feedback_negativo: number
      con_feedback_negativo: number
      puede_preparar: boolean
    }
  }> {
    return await apiClient.get(`${this.baseUrl}/conversaciones/estadisticas-feedback`)
  }

  /**
   * Iniciar fine-tuning
   */
  async iniciarFineTuning(params: {
    archivo_id: string
    modelo_base?: string
    epochs?: number
    learning_rate?: number
  }): Promise<FineTuningJob> {
    const response = await apiClient.post<{ job: FineTuningJob }>(`${this.baseUrl}/fine-tuning/iniciar`, params)
    return response.job
  }

  /**
   * Obtener estado de fine-tuning job
   */
  async getEstadoFineTuning(jobId: string): Promise<FineTuningJob> {
    const response = await apiClient.get<{ job: FineTuningJob }>(`${this.baseUrl}/fine-tuning/jobs/${jobId}`)
    return response.job
  }

  /**
   * Listar todos los jobs de fine-tuning
   */
  async listarFineTuningJobs(): Promise<FineTuningJob[]> {
    const response = await apiClient.get<{ jobs: FineTuningJob[] }>(`${this.baseUrl}/fine-tuning/jobs`)
    return response.jobs || []
  }

  /**
   * Activar modelo fine-tuned
   */
  async activarModeloFineTuned(modeloId: string): Promise<{ mensaje: string; modelo_activo: string }> {
    return await apiClient.post(`${this.baseUrl}/fine-tuning/activar`, { modelo_id: modeloId })
  }

  /**
   * Cancelar un job de fine-tuning
   */
  async cancelarFineTuningJob(jobId: string): Promise<{ job: FineTuningJob; mensaje: string }> {
    return await apiClient.post(`${this.baseUrl}/fine-tuning/jobs/${jobId}/cancelar`)
  }

  /**
   * Eliminar un job de fine-tuning
   */
  async eliminarFineTuningJob(jobId: string): Promise<{ mensaje: string }> {
    return await apiClient.delete(`${this.baseUrl}/fine-tuning/jobs/${jobId}`)
  }

  /**
   * Eliminar todos los jobs de fine-tuning (o solo los fallidos)
   */
  async eliminarTodosFineTuningJobs(soloFallidos: boolean = false): Promise<{ mensaje: string; eliminados: number }> {
    return await apiClient.delete(`${this.baseUrl}/fine-tuning/jobs?solo_fallidos=${soloFallidos}`)
  }

  // ============================================
  // RAG MEJORADO (EMBEDDINGS)
  // ============================================

  /**
   * Generar embeddings para documentos
   */
  async generarEmbeddings(documentoIds?: number[]): Promise<{ documentos_procesados: number; total_embeddings: number }> {
    const response = await apiClient.post<{ documentos_procesados: number; total_embeddings: number }>(`${this.baseUrl}/rag/generar-embeddings`, {
      documento_ids: documentoIds,
    })
    return response
  }

  /**
   * Buscar documentos relevantes usando embeddings
   */
  async buscarDocumentosRelevantes(
    pregunta: string,
    topK: number = 3
  ): Promise<{ documentos: DocumentoEmbedding[]; query_embedding?: number[] }> {
    const response = await apiClient.post<{ documentos: DocumentoEmbedding[]; query_embedding?: number[] }>(`${this.baseUrl}/rag/buscar`, {
      pregunta,
      top_k: topK,
    })
    return response
  }

  /**
   * Obtener estado de embeddings
   */
  async getEstadoEmbeddings(): Promise<{
    total_documentos: number
    documentos_con_embeddings: number
    total_embeddings: number
    ultima_actualizacion?: string
  }> {
    return await apiClient.get(`${this.baseUrl}/rag/estado`)
  }

  /**
   * Actualizar embeddings de un documento
   */
  async actualizarEmbeddingsDocumento(documentoId: number): Promise<{ embeddings_generados: number }> {
    const response = await apiClient.post<{ embeddings_generados: number }>(`${this.baseUrl}/rag/documentos/${documentoId}/embeddings`)
    return response
  }

  // ============================================
  // ML DE RIESGO
  // ============================================

  /**
   * Entrenar modelo de riesgo
   */
  async entrenarModeloRiesgo(params?: {
    algoritmo?: string
    test_size?: number
    random_state?: number
  }): Promise<{ job_id: string; mensaje: string }> {
    // Usar timeout extendido (5 minutos) para entrenamiento ML que puede tardar mucho
    const response = await apiClient.post<{ job_id: string; mensaje: string }>(
      `${this.baseUrl}/ml-riesgo/entrenar`,
      params || {},
      { timeout: 300000 } // 5 minutos
    )
    return response
  }

  /**
   * Obtener estado del entrenamiento de ML
   */
  async getEstadoEntrenamientoML(jobId: string): Promise<{
    status: string
    progreso?: number
    modelo?: ModeloRiesgo
    error?: string
  }> {
    return await apiClient.get(`${this.baseUrl}/ml-riesgo/jobs/${jobId}`)
  }

  /**
   * Listar modelos de riesgo disponibles
   */
  async listarModelosRiesgo(): Promise<ModeloRiesgo[] | { modelos: ModeloRiesgo[]; error?: string }> {
    const response = await apiClient.get<{ modelos: ModeloRiesgo[]; error?: string }>(`${this.baseUrl}/ml-riesgo/modelos`)
    // Si hay un error en la respuesta, retornar el objeto completo para que el frontend pueda manejarlo
    if (response.error) {
      return { modelos: response.modelos || [], error: response.error }
    }
    return response.modelos || []
  }

  /**
   * Obtener modelo de riesgo activo
   */
  async getModeloRiesgoActivo(): Promise<ModeloRiesgo | null> {
    try {
      const response = await apiClient.get<{ modelo: ModeloRiesgo }>(`${this.baseUrl}/ml-riesgo/modelo-activo`)
      return response.modelo || null
    } catch {
      return null
    }
  }

  /**
   * Activar modelo de riesgo
   */
  async activarModeloRiesgo(modeloId: number): Promise<{ mensaje: string; modelo_activo: ModeloRiesgo }> {
    const response = await apiClient.post<{ mensaje: string; modelo_activo: ModeloRiesgo }>(`${this.baseUrl}/ml-riesgo/activar`, { modelo_id: modeloId })
    return response
  }

  /**
   * Predecir riesgo de un cliente
   */
  async predecirRiesgo(datosCliente: {
    edad?: number
    ingreso?: number
    deuda_total?: number
    ratio_deuda_ingreso?: number
    historial_pagos?: number
    dias_ultimo_prestamo?: number
    numero_prestamos_previos?: number
  }): Promise<{
    riesgo_level: string
    confidence: number
    recommendation: string
    features_used: Record<string, number>
  }> {
    return await apiClient.post(`${this.baseUrl}/ml-riesgo/predecir`, datosCliente)
  }

  // ============================================
  // MÉTRICAS Y DASHBOARD
  // ============================================

  /**
   * Obtener métricas de entrenamiento
   */
  async getMetricasEntrenamiento(): Promise<MetricasEntrenamiento> {
    return await apiClient.get<MetricasEntrenamiento>(`${this.baseUrl}/metricas`)
  }

  /**
   * Obtener tablas y campos de la base de datos
   */
  async getTablasCampos(): Promise<{
    tablas_campos: Record<string, string[]>
    total_tablas: number
    fecha_consulta: string
  }> {
    return await apiClient.get('/api/v1/configuracion/ai/tablas-campos')
  }

  // ============================================
  // ML PREDICCIÓN DE IMPAGO DE CUOTAS
  // ============================================

  /**
   * Entrenar modelo de predicción de impago de cuotas
   */
  async entrenarModeloImpago(params?: {
    algoritmo?: string
    test_size?: number
    random_state?: number
  }): Promise<{ mensaje: string; modelo: ModeloImpagoCuotas; metricas: any }> {
    try {
      console.log('🔄 [aiTrainingService] Iniciando entrenamiento modelo impago:', params)
      // Usar timeout extendido (5 minutos) para entrenamiento ML que puede tardar mucho
      const resultado = await apiClient.post<{ mensaje: string; modelo: ModeloImpagoCuotas; metricas: any }>(
        `${this.baseUrl}/ml-impago/entrenar`,
        params || {},
        { timeout: 300000 } // 5 minutos
      )
      console.log('✅ [aiTrainingService] Modelo entrenado exitosamente:', resultado)
      return resultado
    } catch (error: any) {
      console.error('❌ [aiTrainingService] Error entrenando modelo impago:', error)
      console.error('Error response:', error?.response)
      console.error('Error response data:', error?.response?.data)
      console.error('Error response status:', error?.response?.status)
      throw error
    }
  }

  /**
   * Listar modelos de impago disponibles
   */
  async listarModelosImpago(): Promise<ModeloImpagoCuotas[] | { modelos: ModeloImpagoCuotas[]; error?: string }> {
    try {
      const response = await apiClient.get<{ modelos: ModeloImpagoCuotas[]; modelo_activo: ModeloImpagoCuotas | null; total: number; error?: string }>(
        `${this.baseUrl}/ml-impago/modelos`,
        { timeout: 60000 } // 60 segundos para listar modelos
      )
      // Si hay un error en la respuesta, retornar el objeto completo para que el frontend pueda manejarlo
      if (response.error) {
        return { modelos: response.modelos || [], error: response.error }
      }
      return response.modelos || []
    } catch (error: any) {
      // Manejar timeout específicamente
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        console.warn('⚠️ [aiTrainingService] Timeout al listar modelos. El servidor puede estar procesando.')
        // Retornar lista vacía con mensaje de error en lugar de lanzar excepción
        return { 
          modelos: [], 
          error: 'La petición está tardando más de lo esperado. Por favor, intenta nuevamente en unos momentos.' 
        }
      }
      throw error
    }
  }

  /**
   * Obtener modelo de impago activo
   */
  async getModeloImpagoActivo(): Promise<ModeloImpagoCuotas | null> {
    try {
      const response = await apiClient.get<{ modelos: ModeloImpagoCuotas[]; modelo_activo: ModeloImpagoCuotas | null }>(
        `${this.baseUrl}/ml-impago/modelos`,
        { timeout: 60000 } // 60 segundos para obtener modelo activo
      )
      return response.modelo_activo || null
    } catch (error: any) {
      // Si es timeout, loggear pero no lanzar error (retornar null)
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        console.warn('⚠️ [aiTrainingService] Timeout al obtener modelo activo.')
      }
      return null
    }
  }

  /**
   * Activar modelo de impago
   */
  async activarModeloImpago(modeloId: number): Promise<{ mensaje: string; modelo_activo: ModeloImpagoCuotas }> {
    try {
      console.log('🔄 [aiTrainingService] Activando modelo impago:', modeloId)
      const resultado = await apiClient.post<{ mensaje: string; modelo_activo: ModeloImpagoCuotas }>(
        `${this.baseUrl}/ml-impago/activar`,
        { modelo_id: modeloId }
      )
      console.log('✅ [aiTrainingService] Modelo activado:', resultado)
      return resultado
    } catch (error: any) {
      console.error('❌ [aiTrainingService] Error activando modelo impago:', error)
      console.error('Error response:', error?.response)
      console.error('Error data:', error?.response?.data)
      throw error
    }
  }

  /**
   * Eliminar modelo de impago (solo inactivos)
   */
  async eliminarModeloImpago(modeloId: number, eliminarArchivo: boolean = false): Promise<{ mensaje: string; modelo_id: number; archivo_eliminado?: boolean }> {
    try {
      console.log('🔄 [aiTrainingService] Eliminando modelo impago:', modeloId, 'eliminarArchivo:', eliminarArchivo)
      const resultado = await apiClient.delete<{ mensaje: string; modelo_id: number; archivo_eliminado?: boolean }>(
        `${this.baseUrl}/ml-impago/modelos/${modeloId}${eliminarArchivo ? '?eliminar_archivo=true' : ''}`
      )
      console.log('✅ [aiTrainingService] Modelo eliminado:', resultado)
      return resultado
    } catch (error: any) {
      console.error('❌ [aiTrainingService] Error eliminando modelo impago:', error)
      console.error('Error response:', error?.response)
      throw error
    }
  }

  /**
   * Predecir impago de cuotas para un préstamo
   */
  async predecirImpago(prestamoId: number): Promise<{
    prestamo_id: number
    probabilidad_impago: number
    probabilidad_pago: number
    prediccion: string
    nivel_riesgo: string
    confidence: number
    recomendacion: string
    features_usadas: Record<string, number>
    modelo_usado: {
      id: number
      nombre: string
      version: string
      algoritmo: string
      accuracy?: number
    }
  }> {
    return await apiClient.post(`${this.baseUrl}/ml-impago/predecir`, { prestamo_id: prestamoId })
  }
}

export const aiTrainingService = new AITrainingService()

