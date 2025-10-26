import { apiClient } from './api'

class LogoService {
  private baseUrl = '/api/v1'

  /**
   * Obtener el logo de la empresa desde el servidor
   */
  async obtenerLogo(): Promise<string | null> {
    try {
      const response = await apiClient.get(this.baseUrl + '/logo', {
        responseType: 'blob',
      })
      if (response instanceof Blob && response.size > 0) {
        const url = URL.createObjectURL(response)
        return url
      }
      return null
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      console.error('Error obteniendo logo:', error)
      return null
    }
  }

  /**
   * Subir el logo de la empresa al servidor
   */
  async subirLogo(file: File): Promise<void> {
    const formData = new FormData()
    formData.append('file', file)

    await apiClient.post(this.baseUrl + '/logo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  /**
   * Eliminar el logo de la empresa
   */
  async eliminarLogo(): Promise<void> {
    await apiClient.delete(this.baseUrl + '/logo')
  }
}

export const logoService = new LogoService()

