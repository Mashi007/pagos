// frontend/src/store/simpleAuthStore.ts
import { create } from 'zustand'
import { User, LoginForm } from '@/types'
import { authService } from '@/services/authService'
import toast from 'react-hot-toast'

interface SimpleAuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginForm) => Promise<void>
  logout: () => void
  clearError: () => void
}

export const useSimpleAuthStore = create<SimpleAuthState>((set, get) => ({
  // Estado inicial
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Login simple - SIN PERSISTENCIA
  login: async (credentials: LoginForm): Promise<void> => {
    set({ isLoading: true, error: null })
    
    try {
      console.log('SimpleAuth: Iniciando login...')
      
      const response = await authService.login(credentials)
      
      console.log('SimpleAuth: Login exitoso')
      
      // Solo guardar en memoria - SIN localStorage/sessionStorage
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

  // Logout simple
  logout: () => {
    console.log('SimpleAuth: Logout')
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    toast.success('Sesión cerrada correctamente')
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
  }
}
