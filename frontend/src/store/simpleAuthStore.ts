// frontend/src/store/simpleAuthStore.ts
import { create } from 'zustand'
import { User, LoginForm } from '@/types'
import { authService } from '@/services/authService'
import toast from 'react-hot-toast'
import { logger } from '@/utils/logger'
import { safeGetItem, safeGetSessionItem } from '@/utils/safeStorage'

interface SimpleAuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginForm) => Promise<void>
  logout: () => void
  clearError: () => void
  initializeAuth: () => void
}

export const useSimpleAuthStore = create<SimpleAuthState>((set, get) => ({
  // Estado inicial
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Inicializar autenticación desde almacenamiento seguro
  initializeAuth: () => {
    try {
      const rememberMe = safeGetItem('remember_me', false)
      const user = rememberMe 
        ? safeGetItem('user', null) 
        : safeGetSessionItem('user', null)
      
      if (user) {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        })
        logger.log('SimpleAuth: Usuario restaurado desde almacenamiento seguro')
      }
    } catch (error) {
      logger.error('SimpleAuth: Error al inicializar autenticación:', error)
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
      logger.log('SimpleAuth: Iniciando login...')
      
      const response = await authService.login(credentials)
      
      logger.log('SimpleAuth: Login exitoso')
      
      // El authService ya guarda los datos de forma segura
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })

      logger.log('SimpleAuth: Login completado exitosamente')
      toast.success(`¡Bienvenido, ${response.user.nombre}!`)
    } catch (error: any) {
      logger.error('SimpleAuth: Error en login:', error)
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
      logger.error('SimpleAuth: Error en logout:', error)
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
  }
}
