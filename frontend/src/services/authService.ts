import { apiClient, ApiResponse } from './api'
import { User, AuthTokens, LoginForm } from '@/types'

export interface LoginResponse extends ApiResponse<AuthTokens> {
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
  confirm_password: string
}

class AuthService {
  // Login de usuario
  async login(credentials: LoginForm): Promise<LoginResponse> {
    try {
      console.log('Enviando credenciales a:', '/api/v1/auth/login')
      console.log('Credenciales:', { email: credentials.email, password: '***' })
      
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials)
      
      console.log('Respuesta del servidor:', response)
      
      // Guardar tokens en localStorage
      if (response.data) {
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)
        localStorage.setItem('user', JSON.stringify(response.user))
        console.log('Tokens guardados en localStorage')
      }
      
      return response
    } catch (error: any) {
      console.error('Error en AuthService.login:', error)
      
      // Mejorar el manejo de errores
      if (error.code === 'NETWORK_ERROR' || !error.response) {
        const networkError = new Error('Error de conexión con el servidor')
        networkError.code = 'NETWORK_ERROR'
        throw networkError
      }
      
      throw error
    }
  }

  // Logout de usuario
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch (error) {
      // Continuar con el logout local aunque falle el servidor
      console.error('Error en logout del servidor:', error)
    } finally {
      // Limpiar datos locales
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    }
  }

  // Renovar token
  async refreshToken(): Promise<AuthTokens> {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('No hay refresh token disponible')
    }

    const response = await apiClient.post<ApiResponse<AuthTokens>>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    })

    // Actualizar tokens
    if (response.data) {
      localStorage.setItem('access_token', response.data.access_token)
      localStorage.setItem('refresh_token', response.data.refresh_token)
    }

    return response.data
  }

  // Obtener información del usuario actual
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>('/api/v1/auth/me')
    
    // Actualizar usuario en localStorage
    localStorage.setItem('user', JSON.stringify(response.data))
    
    return response.data
  }

  // Cambiar contraseña
  async changePassword(data: ChangePasswordRequest): Promise<void> {
    await apiClient.post('/api/v1/auth/change-password', data)
  }

  // Verificar si el usuario está autenticado
  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token')
    const user = localStorage.getItem('user')
    return !!(token && user)
  }

  // Obtener usuario desde localStorage
  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user')
    if (!userStr) return null
    
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  }

  // Obtener token desde localStorage
  getStoredToken(): string | null {
    return localStorage.getItem('access_token')
  }

  // Verificar si el usuario tiene un rol específico
  hasRole(role: string): boolean {
    const user = this.getStoredUser()
    return user?.rol === role
  }

  // Verificar si el usuario tiene alguno de los roles especificados
  hasAnyRole(roles: string[]): boolean {
    const user = this.getStoredUser()
    return user ? roles.includes(user.rol) : false
  }

  // Verificar permisos administrativos
  isAdmin(): boolean {
    return this.hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR'])
  }

  // Verificar permisos de cobranza
  canManagePayments(): boolean {
    return this.hasAnyRole(['ADMIN', 'GERENTE', 'COBRADOR', 'ASESOR_COMERCIAL'])
  }

  // Verificar permisos de reportes
  canViewReports(): boolean {
    return this.hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  // Verificar permisos de configuración
  canManageConfig(): boolean {
    return this.hasAnyRole(['ADMIN', 'GERENTE'])
  }

  // Verificar si puede ver todos los clientes o solo los asignados
  canViewAllClients(): boolean {
    return this.hasAnyRole(['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  // Obtener ID del usuario actual
  getCurrentUserId(): string | null {
    const user = this.getStoredUser()
    return user?.id || null
  }

  // Obtener nombre completo del usuario actual
  getCurrentUserName(): string {
    const user = this.getStoredUser()
    if (!user) return 'Usuario'
    return `${user.nombre} ${user.apellido}`.trim()
  }

  // Obtener iniciales del usuario actual
  getCurrentUserInitials(): string {
    const user = this.getStoredUser()
    if (!user) return 'U'
    
    const firstInitial = user.nombre?.charAt(0)?.toUpperCase() || ''
    const lastInitial = user.apellido?.charAt(0)?.toUpperCase() || ''
    return firstInitial + lastInitial
  }
}

// Instancia singleton del servicio de autenticación
export const authService = new AuthService()
