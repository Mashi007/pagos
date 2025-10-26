// frontend/src/services/validadoresService.ts
import { apiClient } from './api'

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
    }
    patron_regex: string
    formato_display: string
  }
  email: {
    descripcion: string
    requisitos: {
      formato: string
      normalizacion: string
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
      rango_minimo: string
      rango_maximo: string
      monedas_soportadas: {
        USD: string
        VES: string
      }
    }
  }
  nombre: {
    descripcion: string
    requisitos: {
      palabras: string
      longitud_minima: string
      longitud_maxima: string
      formato: string
    }
    patron_regex: string
  }
  apellido: {
    descripcion: string
    requisitos: {
      palabras: string
      longitud_minima: string
      longitud_maxima: string
      formato: string
    }
    patron_regex: string
  }
}

class ValidadoresService {
  private baseUrl = '/api/v1/validadores'

  // Validar campo individual
  async validarCampo(campo: string, valor: string, pais: string = 'VENEZUELA', moneda?: string): Promise<ValidacionResponse> {
    const body: any = {
      campo,
      valor,
      pais
    }
    
    // Agregar moneda solo para campos de monto
    if ((campo === 'monto' || campo === 'ingreso_mensual' || campo === 'total_financiamiento') && moneda) {
      body.moneda = moneda
    }
    
    return await apiClient.post<ValidacionResponse>(`${this.baseUrl}/validar-campo`, body)
  }

  // Formatear campo en tiempo real
  async formatearTiempoReal(campo: string, valor: string, pais: string = 'VENEZUELA', moneda?: string): Promise<any> {
    const body: any = {
      campo,
      valor,
      pais
    }
    
    // Agregar moneda solo para campos de monto
    if ((campo === 'monto' || campo === 'ingreso_mensual' || campo === 'total_financiamiento') && moneda) {
      body.moneda = moneda
    }
    
    return await apiClient.post(`${this.baseUrl}/formatear-tiempo-real`, body)
  }

  // Obtener configuración de validadores
  async obtenerConfiguracion(): Promise<ConfiguracionValidadores> {
    return await apiClient.get<ConfiguracionValidadores>(`${this.baseUrl}/configuracion-validadores`)
  }

  // Obtener ejemplos de corrección
  async obtenerEjemplos(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/ejemplos-correccion`)
  }

  // Detectar errores masivos
  async detectarErroresMasivo(): Promise<any> {
    return await apiClient.get(`${this.baseUrl}/detectar-errores-masivo`)
  }

  // Corregir datos de cliente
  async corregirCliente(clienteId: number, correcciones: Record<string, string>, pais: string = 'VENEZUELA'): Promise<any> {
    return await apiClient.post(`${this.baseUrl}/corregir-cliente/${clienteId}`, {
      correcciones,
      pais
    })
  }
}

export const validadoresService = new ValidadoresService()
export type { ValidacionResponse, ConfiguracionValidadores }
