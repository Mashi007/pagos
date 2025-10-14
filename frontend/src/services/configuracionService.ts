import { apiClient, ApiResponse } from './api'

// Interfaces para la configuración de validadores
export interface ValidadoresConfig {
  titulo: string
  fecha_consulta: string
  consultado_por: string
  validadores_disponibles: {
    telefono: {
      descripcion: string
      paises_soportados: {
        venezuela: {
          codigo: string
          formato: string
          requisitos: {
            debe_empezar_por: string
            longitud_total: string
            primer_digito: string
            digitos_validos: string
          }
          ejemplos_validos: string[]
          ejemplos_invalidos: string[]
        }
      }
      auto_formateo: boolean
      validacion_tiempo_real: boolean
    }
    cedula: {
      descripcion: string
      paises_soportados: {
        venezuela: {
          prefijos_validos: string[]
          longitud: string
          requisitos: {
            prefijos: string
            dígitos: string
            longitud: string
          }
          ejemplos_validos: string[]
          ejemplos_invalidos: string[]
        }
      }
      auto_formateo: boolean
      validacion_tiempo_real: boolean
    }
    fecha: {
      descripcion: string
      formato_requerido: string
      requisitos: {
        dia: string
        mes: string
        año: string
        separador: string
      }
      ejemplos_validos: string[]
      ejemplos_invalidos: string[]
      auto_formateo: boolean
      validacion_tiempo_real: boolean
      requiere_calendario: boolean
    }
    email: {
      descripcion: string
      caracteristicas: {
        normalizacion: string
        limpieza: string
        validacion: string
        dominios_bloqueados: string[]
      }
      ejemplos_validos: string[]
      ejemplos_invalidos: string[]
      auto_formateo: boolean
      validacion_tiempo_real: boolean
    }
  }
  reglas_negocio: Record<string, string>
  configuracion_frontend: Record<string, string>
  endpoints_validacion: Record<string, string>
}

export interface PruebaValidadores {
  telefono?: string
  pais_telefono?: string
  cedula?: string
  pais_cedula?: string
  fecha?: string
  email?: string
}

export interface ResultadoPrueba {
  titulo: string
  fecha_prueba: string
  datos_entrada: PruebaValidadores
  resultados: Record<string, any>
  resumen: {
    total_validados: number
    validos: number
    invalidos: number
  }
}

class ConfiguracionService {
  private baseUrl = '/api/v1/configuracion'

  // Obtener configuración de validadores
  async obtenerValidadores(): Promise<ValidadoresConfig> {
    const response = await apiClient.get<ValidadoresConfig>(`${this.baseUrl}/validadores`)
    return response.data
  }

  // Probar validadores con datos de ejemplo
  async probarValidadores(datosPrueba: PruebaValidadores): Promise<ResultadoPrueba> {
    const response = await apiClient.post<ResultadoPrueba>(`${this.baseUrl}/validadores/probar`, datosPrueba)
    return response.data
  }

  // Obtener configuración completa del sistema
  async obtenerConfiguracionCompleta(categoria?: string): Promise<any> {
    const params = categoria ? { categoria } : {}
    const response = await apiClient.get(`${this.baseUrl}/sistema/completa`, { params })
    return (response as any).data
  }

  // Obtener configuración por categoría
  async obtenerConfiguracionCategoria(categoria: string): Promise<any> {
    const response = await apiClient.get(`${this.baseUrl}/sistema/categoria/${categoria}`)
    return (response as any).data
  }
}

export const configuracionService = new ConfiguracionService()
