import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, LoginForm } from '@/types'
import { authService } from '@/services/authService'
import toast from 'react-hot-toast'

interface AuthState {
  // Estado
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Acciones
  login: (credentials: LoginForm) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  changePassword: (data: { current_password: string; new_password: string; confirm_password: string }) => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void
  setUser: (user: User) => void
  setTokens: (tokens: any) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Estado inicial
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Acción de login
      login: async (credentials: LoginForm) => {
        set({ isLoading: true, error: null })
        
        try {
          console.log('🔄 Store: Iniciando login con:', {
            email: credentials.email,
            remember: credentials.remember
          })
          
          const response = await authService.login(credentials)
          
          console.log('✅ Store: Login exitoso, respuesta recibida:', response)
          
          // Actualizar estado inmediatamente después del login exitoso
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })

          // Verificar que los tokens se guardaron
          const rememberMe = credentials.remember || false
          const hasToken = rememberMe 
            ? localStorage.getItem('access_token') 
            : sessionStorage.getItem('access_token')
          
          console.log('🔍 Store: Verificación de tokens guardados:', {
            rememberMe,
            hasToken: !!hasToken,
            storageType: rememberMe ? 'localStorage' : 'sessionStorage'
          })

          toast.success(`¡Bienvenido, ${response.user.nombre}!`)
          return response
        } catch (error: any) {
          console.error('❌ Store: Error en login:', error)
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: error.response?.data?.message || 'Error al iniciar sesión',
          })
          throw error
        }
      },

      // Acción de logout
      logout: async () => {
        set({ isLoading: true })
        
        try {
          await authService.logout()
        } catch (error) {
          console.error('Error en logout:', error)
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

      // Refrescar información del usuario
      refreshUser: async () => {
        // Primero verificar si hay tokens en localStorage
        const storedUser = authService.getStoredUser()
        const hasToken = authService.getStoredToken()
        
        if (!hasToken || !storedUser) {
          set({ user: null, isAuthenticated: false, isLoading: false })
          return
        }

        // Si hay datos almacenados, restaurar inmediatamente
        set({ user: storedUser, isAuthenticated: true, isLoading: true })
        
        try {
          // Intentar obtener información actualizada del usuario
          const user = await authService.getCurrentUser()
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          console.warn('Error al refrescar usuario, manteniendo datos almacenados:', error)
          // Si falla la actualización pero tenemos datos almacenados, mantenerlos
          set({
            user: storedUser,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        }
      },

      // Cambiar contraseña
      changePassword: async (data) => {
        set({ isLoading: true, error: null })
        
        try {
          await authService.changePassword(data)
          set({ isLoading: false })
          toast.success('Contraseña cambiada correctamente')
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.message || 'Error al cambiar la contraseña',
          })
          throw error
        }
      },

      // Limpiar error
      clearError: () => {
        set({ error: null })
      },

      // Establecer estado de carga
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      setUser: (user: User) => {
        set({ user, isAuthenticated: true })
      },

      setTokens: (tokens: any) => {
        // Los tokens se guardan en localStorage en el componente
        set({ isAuthenticated: true })
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        console.log('🔄 Rehidratando store de autenticación...', state)
        
        if (!state) {
          console.log('❌ No hay estado para rehidratar')
          return
        }
        
        // Verificar si hay datos almacenados en localStorage/sessionStorage
        const storedUser = authService.getStoredUser()
        const hasToken = authService.getStoredToken()
        const rememberMe = localStorage.getItem('remember_me') === 'true'
        
        console.log('📊 Datos encontrados en storage:', {
          hasStoredUser: !!storedUser,
          hasToken: !!hasToken,
          rememberMe,
          storageType: rememberMe ? 'localStorage' : 'sessionStorage'
        })
        
        if (storedUser && hasToken) {
          // Restaurar datos desde storage
          state.user = storedUser
          state.isAuthenticated = true
          console.log('✅ Usuario restaurado desde storage:', storedUser.nombre)
        } else {
          // Limpiar estado si no hay datos válidos
          state.user = null
          state.isAuthenticated = false
          console.log('🧹 Estado limpiado - no hay datos válidos')
        }
      },
    }
  )
)

// Selectores para facilitar el uso
export const useAuth = () => {
  const store = useAuthStore()
  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    login: store.login,
    logout: store.logout,
    refreshUser: store.refreshUser,
    changePassword: store.changePassword,
    clearError: store.clearError,
    setUser: store.setUser,
  }
}

// Selectores específicos para permisos
export const usePermissions = () => {
  const user = useAuthStore((state) => state.user)
  
  return {
    isAdmin: () => authService.isAdmin(),
    canManagePayments: () => authService.canManagePayments(),
    canViewReports: () => authService.canViewReports(),
    canManageConfig: () => authService.canManageConfig(),
    canViewAllClients: () => authService.canViewAllClients(),
    hasRole: (role: string) => authService.hasRole(role),
    hasAnyRole: (roles: string[]) => authService.hasAnyRole(roles),
    userId: user?.id,
    userRole: user?.rol,
    userName: authService.getCurrentUserName(),
    userInitials: authService.getCurrentUserInitials(),
  }
}
