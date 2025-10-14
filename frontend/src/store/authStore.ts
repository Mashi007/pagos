import { create } from 'zustand'
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

export const useAuthStore = create<AuthState>()((set, get) => ({
      // Estado inicial
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Acción de login - RESPONSABILIDAD ÚNICA: GUARDAR TOKENS Y ESTADO
      login: async (credentials: LoginForm): Promise<void> => {
        set({ isLoading: true, error: null })
        
        try {
          console.log('Store: Iniciando login...')
          
          // 1. HACER API CALL
          const response = await authService.login(credentials)
          
          console.log('Store: Login exitoso, guardando tokens...')
          
          // 2. GUARDAR TOKENS (RESPONSABILIDAD ÚNICA DEL STORE)
          const rememberMe = credentials.remember || false
          const accessToken = response.data.access_token
          const refreshToken = response.data.refresh_token
          const userData = response.user
          
          // Guardar en el storage apropiado
          if (rememberMe) {
            localStorage.setItem('access_token', accessToken)
            localStorage.setItem('refresh_token', refreshToken)
            localStorage.setItem('user', JSON.stringify(userData))
            localStorage.setItem('remember_me', 'true')
            console.log('Store: Tokens guardados en localStorage')
          } else {
            sessionStorage.setItem('access_token', accessToken)
            sessionStorage.setItem('refresh_token', refreshToken)
            sessionStorage.setItem('user', JSON.stringify(userData))
            localStorage.setItem('remember_me', 'false')
            console.log('Store: Tokens guardados en sessionStorage')
          }
          
          // 3. ACTUALIZAR ESTADO
          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })

          console.log('Store: Login completado exitosamente')
          toast.success(`¡Bienvenido, ${userData.nombre}!`)
        } catch (error: any) {
          console.error('Store: Error en login:', error)
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
        set({ isAuthenticated: true })
      },
    })
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
