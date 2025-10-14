// frontend/src/services/userService.ts
import api from './api'

export interface User {
  id: number
  email: string
  nombre: string
  apellido: string
  rol: 'ADMIN' | 'GERENTE' | 'DIRECTOR' | 'COBRANZAS' | 'COMERCIAL' | 'ASESOR' | 'CONTADOR' | 'COMITE'
  is_active: boolean
  created_at: string
  updated_at?: string
  last_login?: string
  full_name?: string
}

export interface UserCreate {
  email: string
  nombre: string
  apellido: string
  rol: 'ADMIN' | 'GERENTE' | 'DIRECTOR' | 'COBRANZAS' | 'COMERCIAL' | 'ASESOR' | 'CONTADOR' | 'COMITE'
  password: string
  is_active: boolean
}

export interface UserUpdate {
  email?: string
  nombre?: string
  apellido?: string
  rol?: 'ADMIN' | 'GERENTE' | 'DIRECTOR' | 'COBRANZAS' | 'COMERCIAL' | 'ASESOR' | 'CONTADOR' | 'COMITE'
  password?: string
  is_active?: boolean
}

export interface UserListResponse {
  users: User[]
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
    const response = await api.get<UserListResponse>('/users/', { params })
    return response.data
  },

  // Obtener usuario por ID
  obtenerUsuario: async (userId: number): Promise<User> => {
    const response = await api.get<User>(`/users/${userId}`)
    return response.data
  },

  // Crear usuario
  crearUsuario: async (userData: UserCreate): Promise<User> => {
    const response = await api.post<User>('/users/', userData)
    return response.data
  },

  // Actualizar usuario
  actualizarUsuario: async (userId: number, userData: UserUpdate): Promise<User> => {
    const response = await api.put<User>(`/users/${userId}`, userData)
    return response.data
  },

  // Eliminar usuario
  eliminarUsuario: async (userId: number): Promise<void> => {
    await api.delete(`/users/${userId}`)
  },

  // Verificar administradores
  verificarAdmin: async (): Promise<any> => {
    const response = await api.get('/users/verificar-admin')
    return response.data
  }
}

