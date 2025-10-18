import { apiClient, ApiResponse } from './api'

export interface Usuario {
  id: number
  nombre: string
  apellido: string
  email: string
  rol: 'USER' | 'ADMIN' | 'GERENTE' | 'COBRANZAS'
  cargo?: string  // Campo separado para cargo en la empresa
  is_active: boolean
  last_login?: string
  created_at: string
  updated_at?: string
}

export interface UsuarioCreate {
  nombre: string
  apellido: string
  email: string
  password: string
  rol: 'USER' | 'ADMIN' | 'GERENTE' | 'COBRANZAS'
  cargo?: string
  is_active?: boolean
}

export interface UsuarioUpdate {
  nombre?: string
  apellido?: string
  email?: string
  password?: string
  rol?: 'USER' | 'ADMIN' | 'GERENTE' | 'COBRANZAS'
  cargo?: string
  is_active?: boolean
}

export interface UsuarioListResponse {
  items: Usuario[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

class UsuarioService {
  private baseUrl = '/api/v1/users'

  // Listar usuarios con paginación y filtros
  async listarUsuarios(params?: {
    skip?: number
    limit?: number
    is_active?: boolean
    search?: string
    rol?: string
  }): Promise<UsuarioListResponse> {
    try {
      console.log('🔍 Parámetros enviados:', params)
      const response = await apiClient.get<UsuarioListResponse>(this.baseUrl, { params })
      console.log('📦 Respuesta recibida:', response)
      
      // Validar que la respuesta tenga la estructura esperada
      if (!response || typeof response !== 'object') {
        throw new Error('Respuesta inválida del servidor')
      }
      
      // Asegurar que tenga la estructura esperada
      const validResponse: UsuarioListResponse = {
        items: response.users || response.items || [],
        total: response.total || 0,
        page: response.page || 1,
        page_size: response.page_size || 10,
        total_pages: response.total_pages || Math.ceil((response.total || 0) / (response.page_size || 10))
      }
      
      return validResponse
    } catch (error) {
      console.error('❌ Error en listarUsuarios:', error)
      
      // Retornar respuesta vacía en caso de error
      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 1
      }
    }
  }

  // Listar solo usuarios activos (para formularios)
  async listarUsuariosActivos(): Promise<Usuario[]> {
    return await apiClient.get<Usuario[]>(`${this.baseUrl}/activos`)
  }

  // Obtener un usuario por ID
  async obtenerUsuario(id: number): Promise<Usuario> {
    return await apiClient.get<Usuario>(`${this.baseUrl}/${id}`)
  }

  // Crear un nuevo usuario
  async crearUsuario(data: UsuarioCreate): Promise<Usuario> {
    return await apiClient.post<Usuario>(this.baseUrl, data)
  }

  // Actualizar un usuario existente
  async actualizarUsuario(id: number, data: UsuarioUpdate): Promise<Usuario> {
    return await apiClient.put<Usuario>(`${this.baseUrl}/${id}`, data)
  }

  // Eliminar un usuario (hard delete)
  async eliminarUsuario(id: number): Promise<{ message: string }> {
    return await apiClient.delete<{ message: string }>(`${this.baseUrl}/${id}`)
  }

  // Activar/Desactivar usuario
  async toggleActivo(id: number, activo: boolean): Promise<Usuario> {
    return await apiClient.put<Usuario>(`${this.baseUrl}/${id}`, { is_active: activo })
  }
}

export const usuarioService = new UsuarioService()
