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
  // Login de usuario - SOLO API CALL, NO GUARDA TOKENS
  async login(credentials: LoginForm): Promise<LoginResponse> {
    try {
      console.log('AuthService: Enviando credenciales a:', '/api/v1/auth/login')
      
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials)
      
      console.log('AuthService: Respuesta del servidor recibida')
      
      // NO GUARDAR TOKENS AQUÍ - Solo retornar la respuesta
      return response
    } catch (error: any) {
      console.error('AuthService: Error en login:', error)
      
      if (error.code === 'NETWORK_ERROR' || !error.response) {
        const networkError = new Error('Error de conexión con el servidor') as any
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
      // Limpiar datos locales y de sesión
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      localStorage.removeItem('remember_me')
      sessionStorage.removeItem('access_token')
      sessionStorage.removeItem('refresh_token')
      sessionStorage.removeItem('user')
    }
  }

  // Renovar token
  async refreshToken(): Promise<AuthTokens> {
    const rememberMe = localStorage.getItem('remember_me') === 'true'
    const refreshToken = rememberMe 
      ? localStorage.getItem('refresh_token') 
      : sessionStorage.getItem('refresh_token')
      
    if (!refreshToken) {
      throw new Error('No hay refresh token disponible')
    }

    const response = await apiClient.post<ApiResponse<AuthTokens>>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    })

    // Actualizar tokens en el almacenamiento correspondiente
    if (response.data) {
      if (rememberMe) {
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)
      } else {
        sessionStorage.setItem('access_token', response.data.access_token)
        sessionStorage.setItem('refresh_token', response.data.refresh_token)
      }
    }

    return response.data
  }

  // Obtener información del usuario actual
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>('/api/v1/auth/me')
    
    // Actualizar usuario en el almacenamiento correspondiente
    const rememberMe = localStorage.getItem('remember_me') === 'true'
    if (rememberMe) {
      localStorage.setItem('user', JSON.stringify(response.data))
    } else {
      sessionStorage.setItem('user', JSON.stringify(response.data))
    }
    
    return response.data
  }

  // Cambiar contraseña
  async changePassword(data: ChangePasswordRequest): Promise<void> {
    await apiClient.post('/api/v1/auth/change-password', data)
  }

  // MÉTODOS DE TOKEN MANAGEMENT ELIMINADOS - AHORA EN authStore.ts

  // MÉTODOS DE PERMISOS SIMPLIFICADOS - RECIBEN USER COMO PARÁMETRO
  static hasRole(user: User | null, role: string): boolean {
    return user?.rol === role
  }

  static hasAnyRole(user: User | null, roles: string[]): boolean {
    return user ? roles.includes(user.rol) : false
  }

  static isAdmin(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['ADMIN', 'GERENTE', 'DIRECTOR'])
  }

  static canManagePayments(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['ADMIN', 'GERENTE', 'COBRADOR', 'ASESOR_COMERCIAL'])
  }

  static canViewReports(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  static canManageConfig(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['ADMIN', 'GERENTE'])
  }

  static canViewAllClients(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR'])
  }

  static getCurrentUserName(user: User | null): string {
    if (!user) return 'Usuario'
    return `${user.nombre} ${user.apellido}`.trim()
  }

  static getCurrentUserInitials(user: User | null): string {
    if (!user) return 'U'
    
    const firstInitial = user.nombre?.charAt(0)?.toUpperCase() || ''
    const lastInitial = user.apellido?.charAt(0)?.toUpperCase() || ''
    return firstInitial + lastInitial
  }
}

// Instancia singleton del servicio de autenticación
export const authService = new AuthService()
