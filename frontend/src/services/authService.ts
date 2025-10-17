import { apiClient, ApiResponse } from './api'
import { User, AuthTokens, LoginForm } from '@/types'

export interface LoginResponse extends AuthTokens {
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

export class AuthService {
  // Login de usuario - SOLO API CALL, NO GUARDA TOKENS
  async login(credentials: LoginForm): Promise<LoginResponse> {
    try {
      console.log('AuthService: Enviando credenciales a:', '/api/v1/auth/login')
      
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials)
      
      console.log('AuthService: Respuesta del servidor recibida')
      
      // NO GUARDAR TOKENS AQUÍ - Solo retornar los datos
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

  // Logout de usuario - SIN PERSISTENCIA
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch (error) {
      // Continuar con el logout local aunque falle el servidor
      console.error('Error en logout del servidor:', error)
    } finally {
      // NO usar localStorage/sessionStorage para evitar errores JSON
      // Solo limpiar en memoria
    }
  }

  // Renovar token - DESHABILITADO SIN PERSISTENCIA
  async refreshToken(): Promise<AuthTokens> {
    throw new Error('Refresh token deshabilitado - sin persistencia')
  }

  // Obtener información del usuario actual - SIN PERSISTENCIA
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>('/api/v1/auth/me')
    
    // NO guardar en localStorage/sessionStorage para evitar errores JSON
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
    return AuthService.hasAnyRole(user, ['ADMIN'])
  }

  static canManagePayments(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['USER'])
  }

  static canViewReports(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['USER'])
  }

  static canManageConfig(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['USER'])
  }

  static canViewAllClients(user: User | null): boolean {
    return AuthService.hasAnyRole(user, ['USER'])
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
