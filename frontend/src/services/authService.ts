import { apiClient, ApiResponse } from './api'
import { User, AuthTokens, LoginForm } from '@/types'

// Funciones de almacenamiento seguro simplificadas
const safeSetItem = (key: string, value: any) => {
  try {
    if (value === undefined) return false
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    if (stringValue === 'undefined') return false
    localStorage.setItem(key, stringValue)
    return true
  } catch {
    return false
  }
}

const safeGetItem = (key: string, fallback: any = null) => {
  try {
    const item = localStorage.getItem(key)
    if (item === null || item === '' || item === 'undefined' || item === 'null') {
      return fallback
    }
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  } catch {
    return fallback
  }
}

const safeRemoveItem = (key: string) => {
  try {
    localStorage.removeItem(key)
    return true
  } catch {
    return false
  }
}

const safeClear = () => {
  try {
    localStorage.clear()
    return true
  } catch {
    return false
  }
}

const safeSetSessionItem = (key: string, value: any) => {
  try {
    if (value === undefined) return false
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value)
    if (stringValue === 'undefined') return false
    sessionStorage.setItem(key, stringValue)
    return true
  } catch {
    return false
  }
}

const safeGetSessionItem = (key: string, fallback: any = null) => {
  try {
    const item = sessionStorage.getItem(key)
    if (item === null || item === '' || item === 'undefined' || item === 'null') {
      return fallback
    }
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  } catch {
    return fallback
  }
}

const safeRemoveSessionItem = (key: string) => {
  try {
    sessionStorage.removeItem(key)
    return true
  } catch {
    return false
  }
}

const safeClearSession = () => {
  try {
    sessionStorage.clear()
    return true
  } catch {
    return false
  }
}

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
  // Login de usuario - CON PERSISTENCIA SEGURA
  async login(credentials: LoginForm): Promise<LoginResponse> {
    try {
      console.log('AuthService: Enviando credenciales a:', '/api/v1/auth/login')
      
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials)
      
      console.log('AuthService: Respuesta del servidor recibida')
      
      // Guardar tokens de forma segura
      if (response.access_token) {
        if (credentials.remember) {
          safeSetItem('access_token', response.access_token)
          safeSetItem('refresh_token', response.refresh_token)
          safeSetItem('user', response.user)
          safeSetItem('remember_me', true)
        } else {
          safeSetSessionItem('access_token', response.access_token)
          safeSetSessionItem('refresh_token', response.refresh_token)
          safeSetSessionItem('user', response.user)
        }
      }
      
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

  // Logout de usuario - CON LIMPIEZA SEGURA
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout')
    } catch (error) {
      // Continuar con el logout local aunque falle el servidor
      console.error('Error en logout del servidor:', error)
    } finally {
      // Limpiar datos de forma segura
      safeRemoveItem('access_token')
      safeRemoveItem('refresh_token')
      safeRemoveItem('user')
      safeRemoveItem('remember_me')
      safeRemoveSessionItem('access_token')
      safeRemoveSessionItem('refresh_token')
      safeRemoveSessionItem('user')
    }
  }

  // Renovar token - CON PERSISTENCIA SEGURA
  async refreshToken(): Promise<AuthTokens> {
    const rememberMe = safeGetItem('remember_me', false)
    const refreshToken = rememberMe 
      ? safeGetItem('refresh_token', '') 
      : safeGetSessionItem('refresh_token', '')
      
    if (!refreshToken) {
      throw new Error('No hay refresh token disponible')
    }

    const response = await apiClient.post<ApiResponse<AuthTokens>>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    })

    // Actualizar tokens en el almacenamiento correspondiente
    if (response.data) {
      if (rememberMe) {
        safeSetItem('access_token', response.data.access_token)
        safeSetItem('refresh_token', response.data.refresh_token)
      } else {
        safeSetSessionItem('access_token', response.data.access_token)
        safeSetSessionItem('refresh_token', response.data.refresh_token)
      }
    }

    return response.data
  }

  // Obtener información del usuario actual - CON PERSISTENCIA SEGURA
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>('/api/v1/auth/me')
    
    // Actualizar usuario en el almacenamiento correspondiente
    const rememberMe = safeGetItem('remember_me', false)
    if (rememberMe) {
      safeSetItem('user', response.data)
    } else {
      safeSetSessionItem('user', response.data)
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
    if (role === 'ADMIN') {
      return user?.is_admin || false  // Cambio clave: rol → is_admin
    }
    return !user?.is_admin || false  // Cambio clave: rol → is_admin
  }

  static hasAnyRole(user: User | null, roles: string[]): boolean {
    if (!user) return false
    if (roles.includes('ADMIN') && user.is_admin) return true  // Cambio clave: rol → is_admin
    if (roles.includes('USER') && !user.is_admin) return true  // Cambio clave: rol → is_admin
    return false
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
