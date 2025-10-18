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
      
      if (user) {
        console.log('SimpleAuth: Usuario encontrado en almacenamiento, verificando con backend...')
        
        // CRÍTICO: Siempre verificar con el backend al inicializar
        try {
          const freshUser = await authService.getCurrentUser()
          
          if (freshUser) {
            console.log('SimpleAuth: Usuario verificado desde backend:', freshUser)
            set({
              user: freshUser,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            })
            console.log('SimpleAuth: Usuario actualizado desde backend exitosamente')
          } else {
            throw new Error('Usuario no encontrado en backend')
          }
        } catch (error) {
          console.error('SimpleAuth: Error verificando usuario con backend:', error)
          
          // Si hay error, usar datos cacheados pero marcar como posiblemente obsoletos
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: 'Datos posiblemente obsoletos - verificar conexión',
          })
          console.log('SimpleAuth: Usando datos cacheados debido a error de verificación')
        }
      }
    } catch (error) {
      console.error('SimpleAuth: Error al inicializar autenticación:', error)
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
      console.log('SimpleAuth: Iniciando login...')
      
      const response = await authService.login(credentials)
      
      console.log('SimpleAuth: Login exitoso')
      
      // El authService ya guarda los datos de forma segura
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })

      console.log('SimpleAuth: Login completado exitosamente')
      toast.success(`¡Bienvenido, ${response.user.nombre}!`)
    } catch (error: any) {
      console.error('SimpleAuth: Error en login:', error)
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
      console.error('SimpleAuth: Error en logout:', error)
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
      console.log('SimpleAuth: Refrescando usuario desde backend...')
      
      const freshUser = await authService.getCurrentUser()
      
      if (!freshUser) {
        console.error('SimpleAuth: Usuario refrescado es null/undefined')
        throw new Error('Usuario no encontrado en la respuesta del servidor')
      }
      
      console.log('SimpleAuth: Usuario refrescado:', freshUser)
      
      set({
        user: freshUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })
      
      console.log('SimpleAuth: Usuario actualizado exitosamente')
    } catch (error: any) {
      console.error('SimpleAuth: Error al refrescar usuario:', error)
      
      // NO hacer logout automático, solo mostrar error
      set({ 
        error: error.message || 'Error al actualizar usuario',
        isLoading: false 
      })
      
      // Mantener el usuario actual si hay error
      console.log('SimpleAuth: Manteniendo usuario actual debido a error')
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