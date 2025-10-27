/**
 * Store de autenticación simplificado usando Zustand
 * Gestiona el estado de autenticación del usuario con persistencia segura
 */
// frontend/src/store/simpleAuthStore.ts
import { create } from 'zustand'
import { User, LoginForm } from '@/types'
import { authService } from '@/services/authService'
import toast from 'react-hot-toast'
import { 
  safeGetItem, 
  safeSetItem, 
  safeGetSessionItem, 
  safeSetSessionItem,
  clearAuthStorage 
} from '@/utils/storage'

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

export const useSimpleAuthStore = create<SimpleAuthState>((set) => ({
  // Estado inicial
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Inicializar autenticación desde almacenamiento seguro CON VERIFICACIÓN AUTOMÁTICA
  initializeAuth: async () => {
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
        try {
          const freshUser = await authService.getCurrentUser()
          
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
          // Si hay error, limpiar todo el almacenamiento y marcar como no autenticado
          clearAuthStorage()
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          })
        }
      } else if (!user) {
        // No hay usuario almacenado
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        })
      }
    } catch (error) {
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
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error.response?.data?.message || 'Error al iniciar sesión',
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
}))

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