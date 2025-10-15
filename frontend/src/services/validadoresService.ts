// frontend/src/services/validadoresService.ts
import { apiClient } from './apiClient'

interface ValidacionResponse {
  validacion: {
    valido: boolean
    valor_original: string
    valor_formateado?: string
    error?: string
    mensaje?: string
  }
}

interface ConfiguracionValidadores {
  cedula_venezuela: {
    descripcion: string
    requisitos: {
      debe_empezar_por: string
      longitud_digitos: string
      sin_caracteres_especiales: string
      ejemplos_validos: string[]
    }
    patron_regex: string
    formato_display: string
    tipos: {
      V: string
      E: string
      J: string
    }
  }
  telefono_venezuela: {
    descripcion: string
    requisitos: {
      debe_empezar_por: string
      longitud_total: number
      primer_digito: string
      digitos_validos: string
    }
    patron_regex: string
    formato_display: string
  }
  email: {
    descripcion: string
    requisitos: {
      formato: string
      normalizacion: string
      dominios_bloqueados: string[]
    }
    patron_regex: string
  }
  fecha: {
    descripcion: string
    requisitos: {
      formato: string
      dia: string
      mes: string
      año: string
    }
    patron_regex: string
  }
  monto: {
    descripcion: string
    requisitos: {
      formato: string
      decimales: string
      separador_miles: string
      simbolo_moneda: string
    }
  }
}

class ValidadoresService {
  private baseUrl = '/api/v1/validadores'

  // Validar campo individual
  async validarCampo(campo: string, valor: string, pais: string = 'VENEZUELA'): Promise<ValidacionResponse> {
    const response = await apiClient.post<ValidacionResponse>(`${this.baseUrl}/validar-campo`, {
      campo,
      valor,
      pais
    })
    return response.data
  }

  // Formatear campo en tiempo real
  async formatearTiempoReal(campo: string, valor: string, pais: string = 'VENEZUELA'): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/formatear-tiempo-real`, {
      campo,
      valor,
      pais
    })
    return response.data
  }

  // Obtener configuración de validadores
  async obtenerConfiguracion(): Promise<ConfiguracionValidadores> {
    const response = await apiClient.get<ConfiguracionValidadores>(`${this.baseUrl}/configuracion-validadores`)
    return response.data
  }

  // Obtener ejemplos de corrección
  async obtenerEjemplos(): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/ejemplos-correccion`)
    return response.data
  }

  // Detectar errores masivos
  async detectarErroresMasivo(): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/detectar-errores-masivo`)
    return response.data
  }

  // Corregir datos de cliente
  async corregirCliente(clienteId: number, correcciones: Record<string, string>, pais: string = 'VENEZUELA'): Promise<any> {
    const response = await apiClient.post(`${this.baseUrl}/corregir-cliente/${clienteId}`, {
      correcciones,
      pais
    })
    return response.data
  }
}

export const validadoresService = new ValidadoresService()
export type { ValidacionResponse, ConfiguracionValidadores }
