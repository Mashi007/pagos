/**
 * Store de autenticación simplificado usando Zustand
 * Gestiona el estado de autenticación del usuario con persistencia segura
 */
// frontend/src/store/simpleAuthStore.ts
import { create } from 'zustand'
import { User, LoginForm } from '../types'
import { authService } from '../services/authService'
import toast from 'react-hot-toast'
import {
  safeGetItem,
  safeSetItem,
  safeGetSessionItem,
  safeSetSessionItem,
  clearAuthStorage
} from '../utils/storage'

interface SimpleAuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginForm) => Promise<void>
  logout: () => void
  clearError: () => void
  initializeAuth: () => Promise<void>  // Cambio: ahora es async
  refreshUser: () => Promise<void>
}

// Función para verificar si hay datos de autenticación en almacenamiento
// (maneja contextos inseguros: iframe, storage deshabilitado, "operation is insecure")
const hasAuthData = (): boolean => {
  try {
    const rememberMe = safeGetItem('remember_me', false)
    const user = rememberMe
      ? safeGetItem('user', null)
      : safeGetSessionItem('user', null)
    const token = rememberMe
      ? safeGetItem('access_token', null)
      : safeGetSessionItem('access_token', null)
    return !!(user && token)
  } catch {
    return false
  }
}

export const useSimpleAuthStore = create<SimpleAuthState>((set) => {
  // Verificar si hay datos de auth de forma segura (no lanzar si storage no disponible)
  let hasAuth = false
  try {
    hasAuth = hasAuthData()
  } catch {
    hasAuth = false
  }

  return {
    // Estado inicial - si hay datos de auth, empezar como loading para evitar redirecciones
    user: null,
    isAuthenticated: false,
    isLoading: hasAuth, // ✅ Si hay datos de auth, empezar como loading
    error: null,

  // Inicializar autenticación desde almacenamiento seguro CON VERIFICACIÓN AUTOMÁTICA
  initializeAuth: async () => {
    // ✅ CRÍTICO: Marcar como loading al inicio para evitar redirecciones durante la verificación
    set({ isLoading: true })

    try {
      const rememberMe = safeGetItem('remember_me', false)
      const user = rememberMe
        ? safeGetItem('user', null)
        : safeGetSessionItem('user', null)

      // Verificar que también existe un token de acceso
      const token = rememberMe
        ? safeGetItem('access_token', null)
        : safeGetSessionItem('access_token', null)

      // Si hay usuario pero no hay token, limpiar todo
      if (user && !token) {
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        })
        clearAuthStorage()
        return
      }

      if (user && token) {
        // CRÍTICO: Siempre verificar con el backend al inicializar
        // ✅ Agregar timeout para evitar bloqueos si el backend no responde
        try {
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Timeout: El servidor no respondió')), 8000) // 8 segundos
          })

          const userPromise = authService.getCurrentUser()
          const freshUser = await Promise.race([userPromise, timeoutPromise]) as typeof user

          if (freshUser) {
            set({
              user: freshUser,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            })
          } else {
            throw new Error('Usuario no encontrado en backend')
          }
        } catch (error) {
          // Si hay error (incluyendo timeout), limpiar todo el almacenamiento y marcar como no autenticado
          console.warn('Error al verificar autenticación:', error)
          clearAuthStorage()
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          })
        }
      } else {
        // No hay usuario almacenado - establecer estado inmediatamente
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        })
      }
    } catch (error) {
      console.warn('Error al inicializar autenticación:', error)
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      })
    }
  },

  // Login con persistencia segura
  login: async (credentials: LoginForm): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await authService.login(credentials)

      // El authService ya guarda los datos de forma segura
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })

      toast.success(`¡Bienvenido, ${response.user.nombre}!`)
    } catch (error: any) {
      // Extraer mensaje de error del backend (puede estar en detail o message)
      let errorMessage = 'Error al iniciar sesión'

      if (error.response?.data) {
        // El backend FastAPI devuelve 'detail' para errores HTTP
        errorMessage = error.response.data.detail || error.response.data.message || errorMessage

        // Si es un array (errores de validación), tomar el primer mensaje
        if (Array.isArray(errorMessage)) {
          errorMessage = errorMessage[0]?.msg || errorMessage[0] || errorMessage
        }
      } else if (error.message) {
        errorMessage = error.message
      }

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  },

  // Logout con limpieza segura
  logout: async () => {
    try {
      await authService.logout()
    } catch (error) {
      // Error silencioso en logout
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      })
      toast.success('Sesión cerrada correctamente')
    }
  },

  // Limpiar error
  clearError: () => {
    set({ error: null })
  },

  // REFRESCAR USUARIO DESDE BACKEND - SOLUCIÓN DEFINITIVA AL CACHE
  refreshUser: async () => {
    try {
      const freshUser = await authService.getCurrentUser()

      if (!freshUser) {
        throw new Error('Usuario no encontrado en la respuesta del servidor')
      }

      set({
        user: freshUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })
    } catch (error: any) {
      // NO hacer logout automático, solo mostrar error
      set({
        error: error.message || 'Error al actualizar usuario',
        isLoading: false
      })
    }
  },
  }
})

// Hook simplificado
export const useSimpleAuth = () => {
  const store = useSimpleAuthStore()
  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    login: store.login,
    logout: store.logout,
    clearError: store.clearError,
    initializeAuth: store.initializeAuth,
    refreshUser: store.refreshUser,
  }
}
