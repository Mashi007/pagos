import { apiClient } from './api'

// Interfaces para configuración general
export interface ConfiguracionGeneral {
  nombre_empresa: string
  ruc: string
  direccion: string
  telefono: string
  email: string
  horario_atencion: string
  zona_horaria: string
  formato_fecha: string
  idioma: string
  moneda: string
  version_sistema: string
  logo_filename?: string  // Nombre del archivo del logo (si existe)
}

export interface ConfiguracionGeneralUpdate {
  nombre_empresa?: string
  ruc?: string
  direccion?: string
  telefono?: string
  email?: string
  horario_atencion?: string
  zona_horaria?: string
  formato_fecha?: string
  idioma?: string
  moneda?: string
  version_sistema?: string
}

class ConfiguracionGeneralService {
  private baseUrl = '/api/v1/configuracion'

  // Obtener configuración general
  async obtenerConfiguracionGeneral(): Promise<ConfiguracionGeneral> {
    return await apiClient.get<ConfiguracionGeneral>(`${this.baseUrl}/general`)
  }

  // Actualizar configuración general
  async actualizarConfiguracionGeneral(data: ConfiguracionGeneralUpdate): Promise<{
    message: string
    configuracion: ConfiguracionGeneral
  }> {
    return await apiClient.put<{
      message: string
      configuracion: ConfiguracionGeneral
    }>(`${this.baseUrl}/general`, data)
  }

  // Obtener formato de fecha actual
  async obtenerFormatoFecha(): Promise<string> {
    const config = await this.obtenerConfiguracionGeneral()
    return config.formato_fecha
  }

  // Actualizar solo formato de fecha
  async actualizarFormatoFecha(formato: string): Promise<void> {
    await this.actualizarConfiguracionGeneral({ formato_fecha: formato })
  }
}

export const configuracionGeneralService = new ConfiguracionGeneralService()
