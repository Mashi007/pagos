// frontend/src/services/userService.ts
import { apiClient as api } from './api'
import { User } from '@/types'  // IMPORTAR desde types centralizado

export interface UserCreate {
  email: string
  nombre: string
  apellido: string
  cargo?: string
  is_admin: boolean  // Cambio clave: rol → is_admin
  password: string
  is_active: boolean
}

export interface UserUpdate {
  email?: string
  nombre?: string
  apellido?: string
  cargo?: string
  is_admin?: boolean  // Cambio clave: rol → is_admin
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
    return await api.get<UserListResponse>('/api/v1/users/', { params })
  },

  // Obtener usuario por ID
  obtenerUsuario: async (userId: number): Promise<User> => {
    return await api.get<User>(`/api/v1/users/${userId}`)
  },

  // Crear usuario
  crearUsuario: async (userData: UserCreate): Promise<User> => {
    return await api.post<User>('/api/v1/users/', userData)
  },

  // Actualizar usuario
  actualizarUsuario: async (userId: number, userData: UserUpdate): Promise<User> => {
    return await api.put<User>(`/api/v1/users/${userId}`, userData)
  },

  // Eliminar usuario
  eliminarUsuario: async (userId: number): Promise<void> => {
    await api.delete(`/api/v1/users/${userId}`)
  },

  // Verificar administradores
  verificarAdmin: async (): Promise<any> => {
    return await api.get('/api/v1/users/verificar-admin')
  }
}

