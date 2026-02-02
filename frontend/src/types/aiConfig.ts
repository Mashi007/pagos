/**
 * Tipos para configuración de AI (OpenRouter, documentos, chat de prueba)
 */

export interface AIConfigState {
  configured?: boolean
  provider?: string
  openai_api_key?: string
  modelo_recomendado?: string
  modelo: string
  temperatura: string
  max_tokens: string
  activo: string
}

export interface DocumentoAI {
  id: number
  titulo: string
  descripcion: string | null
  nombre_archivo: string
  tipo_archivo: string
  tamaño_bytes: number | null
  contenido_procesado: boolean
  activo: boolean
  creado_en: string
  actualizado_en: string
}

export interface MensajeChatAI {
  id: string
  tipo: 'user' | 'ai'
  texto: string
  timestamp: Date
  metadata?: {
    tokens?: number
    tiempo?: number
    modelo?: string
    documentos?: number
  }
}
