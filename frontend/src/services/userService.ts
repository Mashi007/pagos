// frontend/src/services/userService.ts
import { apiClient as api } from './api'
import { User, UserRol } from '../types'

export type { User } from '../types'

export interface UserCreate {
  email: string
  nombre: string
  apellido: string
  cargo?: string
  rol: UserRol
  password: string
  is_active: boolean
}

export interface UserUpdate {
  email?: string
  nombre?: string
  apellido?: string
  cargo?: string
  rol?: UserRol
  password?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

export const userService = {
  // Listar usuarios
  listarUsuarios: async (page: number = 1, page_size: number = 50, is_active?: boolean): Promise<UserListResponse> => {
    const params: any = { page, page_size }
    if (is_active !== undefined) {
      params.is_active = is_active
    }
    return await api.get<UserListResponse>('/api/v1/usuarios/', { params })
  },

  // Obtener usuario por ID
  obtenerUsuario: async (userId: number): Promise<User> => {
    return await api.get<User>(`/api/v1/usuarios/${userId}`)
  },

  // Crear usuario
  crearUsuario: async (userData: UserCreate): Promise<User> => {
    return await api.post<User>('/api/v1/usuarios/', userData)
  },

  // Actualizar usuario
  actualizarUsuario: async (userId: number, userData: UserUpdate): Promise<User> => {
    // ✅ CRÍTICO: Validar que userId sea válido
    if (!userId || userId <= 0 || !Number.isInteger(userId)) {
      throw new Error(`ID de usuario inválido: ${userId}`)
    }

    // ✅ CRÍTICO: Logging del endpoint que se está llamando
    const endpoint = `/api/v1/usuarios/${userId}`
    console.log(`📤 [userService] Actualizando usuario - userId: ${userId}, endpoint: ${endpoint}`)

    return await api.put<User>(endpoint, userData)
  },

  // Eliminar usuario
  eliminarUsuario: async (userId: number): Promise<void> => {
    await api.delete(`/api/v1/usuarios/${userId}`)
  },

  // Verificar administradores
  verificarAdmin: async (): Promise<any> => {
    return await api.get('/api/v1/usuarios/verificar-admin')
  },

  // Activar/Desactivar usuario
  toggleActivo: async (userId: number, isActive: boolean): Promise<User> => {
    if (isActive) {
      return await api.post<User>(`/api/v1/usuarios/${userId}/activate`)
    } else {
      return await api.post<User>(`/api/v1/usuarios/${userId}/deactivate`)
    }
  }
}

