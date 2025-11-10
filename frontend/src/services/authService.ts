import { apiClient, ApiResponse } from './api'
import { User, AuthTokens } from '@/types'
import { 
  safeSetItem, 
  safeGetItem, 
  safeRemoveItem,
  safeSetSessionItem,
  safeGetSessionItem,
  safeRemoveSessionItem,
  clearAuthStorage
} from '@/utils/storage'

export interface LoginForm {
  email: string
  password: string
  remember?: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
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
      // Normalizar email a minúsculas
      const normalizedCredentials = {
        ...credentials,
        email: credentials.email.toLowerCase().trim()
      }
      
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', normalizedCredentials)
      
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
        
        // ✅ Resetear el flag de refresh token expirado después de login exitoso
        apiClient.resetRefreshTokenExpired()
      }
      
      return response
    } catch (error: any) {
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
      // Error silencioso para evitar loops de logging
    } finally {
      // Limpiar todo el almacenamiento de autenticación
      clearAuthStorage()
    }
  }

  // Refresh token
  async refreshToken(): Promise<AuthTokens> {
    try {
      const refreshToken = safeGetItem('refresh_token') || safeGetSessionItem('refresh_token')
      
      if (!refreshToken) {
        throw new Error('No hay refresh token disponible')
      }

      const response = await apiClient.post<AuthTokens>('/api/v1/auth/refresh', {
        refresh_token: refreshToken
      })

      // Actualizar tokens en almacenamiento
      const rememberMe = safeGetItem('remember_me', false)
      if (rememberMe) {
        safeSetItem('access_token', response.access_token)
        safeSetItem('refresh_token', response.refresh_token)
      } else {
        safeSetSessionItem('access_token', response.access_token)
        safeSetSessionItem('refresh_token', response.refresh_token)
      }

      return response
    } catch (error: any) {
      // Si hay error, limpiar almacenamiento
      clearAuthStorage()
      throw error
    }
  }

  // Obtener información del usuario actual - CON PERSISTENCIA SEGURA
  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>('/api/v1/auth/me')
      
      // El backend retorna directamente el objeto User, no envuelto en ApiResponse
      const user = response
      
      if (!user) {
        throw new Error('Usuario no encontrado en la respuesta')
      }
      
      // Actualizar usuario en el almacenamiento correspondiente
      const rememberMe = safeGetItem('remember_me', false)
      if (rememberMe) {
        safeSetItem('user', user)
      } else {
        safeSetSessionItem('user', user)
      }
      
      return user
    } catch (error: any) {
      throw error
    }
  }

  // Cambiar contraseña
  async changePassword(data: ChangePasswordRequest): Promise<{ requires_reauth: boolean; message?: string }> {
    const response = await apiClient.post<{ message: string; requires_reauth?: boolean }>('/api/v1/auth/change-password', data)
    
    // ✅ Si el backend indica que se requiere reautenticación, cerrar sesión y redirigir
    if (response.requires_reauth) {
      // Limpiar almacenamiento de autenticación
      clearAuthStorage()
      
      // Redirigir al login después de un delay para mostrar mensaje y limpiar storage
      setTimeout(() => {
        window.location.href = '/login'
      }, 500) // Aumentado a 500ms para dar tiempo a mostrar el mensaje
    }
    
    return { 
      requires_reauth: response.requires_reauth || false,
      message: response.message 
    }
  }

  // Verificar si el usuario está autenticado
  isAuthenticated(): boolean {
    const token = safeGetItem('access_token') || safeGetSessionItem('access_token')
    return !!token
  }

  // Obtener token de acceso
  getAccessToken(): string | null {
    return safeGetItem('access_token') || safeGetSessionItem('access_token')
  }

  // Obtener usuario desde almacenamiento
  getStoredUser(): User | null {
    const rememberMe = safeGetItem('remember_me', false)
    return rememberMe 
      ? safeGetItem('user', null) 
      : safeGetSessionItem('user', null)
  }
}

// Instancia singleton
export const authService = new AuthService()