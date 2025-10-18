// frontend/src/store/simpleAuthStore.ts
import { create } from 'zustand'
import { User, LoginForm } from '@/types'
import { authService } from '@/services/authService'
import toast from 'react-hot-toast'

// Funciones de almacenamiento seguro simplificadas
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

interface SimpleAuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginForm) => Promise<void>
  logout: () => void
  clearError: () => void
  initializeAuth: () => void
  refreshUser: () => Promise<void>  // NUEVA FUNCIÓN
}

export const useSimpleAuthStore = create<SimpleAuthState>((set) => ({
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
        console.log('SimpleAuth: Usuario restaurado desde almacenamiento seguro')
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
      set({ error: error.response?.data?.message || 'Error al actualizar usuario' })
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
    refreshUser: store.refreshUser,  // NUEVA FUNCIÓN EXPUESTA
  }
}
