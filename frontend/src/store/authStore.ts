import { create } from 'zustand'
import { User, LoginForm } from '@/types'
import { authService, AuthService } from '@/services/authService'
import toast from 'react-hot-toast'
import { logger } from '@/utils/logger'
import { safeParseUserData } from '@/utils/safeJson'

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
  initializeAuth: () => Promise<void>
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
          logger.log('Store: Iniciando login...')
          
          // 1. HACER API CALL
          const response = await authService.login(credentials)
          
          logger.log('Store: Login exitoso, guardando tokens...')
          
          // 2. GUARDAR TOKENS (RESPONSABILIDAD ÚNICA DEL STORE)
          const rememberMe = credentials.remember || false
          
          // Verificar estructura de respuesta
          logger.log('Store: Estructura de respuesta:', response)
          logger.log('Store: response.access_token:', response.access_token ? 'EXISTS' : 'MISSING')
          logger.log('Store: response.user:', response.user)
          
          // Acceder a tokens directamente (apiClient.post ya devuelve response.data)
          const accessToken = response.access_token
          const refreshToken = response.refresh_token
          const userData = response.user
          
          logger.log('Store: Tokens extraídos:', {
            accessToken: accessToken ? 'EXISTS' : 'MISSING',
            refreshToken: refreshToken ? 'EXISTS' : 'MISSING',
            userData: userData ? 'EXISTS' : 'MISSING'
          })
          
          logger.log('Store: Valores reales:', {
            accessToken: accessToken,
            refreshToken: refreshToken ? 'EXISTS' : 'MISSING',
            userData: userData ? 'EXISTS' : 'MISSING'
          })
          
          // Validar que tenemos los datos necesarios
          if (!accessToken || !refreshToken || !userData) {
            throw new Error('Datos de respuesta incompletos')
          }
          
          // Guardar en el storage apropiado
          if (rememberMe) {
            logger.log('Store: Guardando en localStorage...')
            localStorage.setItem('access_token', accessToken)
            localStorage.setItem('refresh_token', refreshToken)
            // Validar que userData no sea undefined antes de guardar
            if (userData && typeof userData === 'object') {
              localStorage.setItem('user', JSON.stringify(userData))
            } else {
              throw new Error('Datos de usuario inválidos para guardar')
            }
            localStorage.setItem('remember_me', 'true')
            logger.log('Store: Tokens guardados en localStorage')
            logger.log('Store: Verificación localStorage:', {
              access_token: localStorage.getItem('access_token') ? 'GUARDADO' : 'ERROR',
              user: localStorage.getItem('user') ? 'GUARDADO' : 'ERROR',
              remember_me: localStorage.getItem('remember_me')
            })
            
            // Verificación inmediata
            const savedToken = localStorage.getItem('access_token')
            logger.log('Store: Token guardado inmediatamente:', savedToken ? 'EXISTS' : 'ERROR')
          } else {
            sessionStorage.setItem('access_token', accessToken)
            sessionStorage.setItem('refresh_token', refreshToken)
            // Validar que userData no sea undefined antes de guardar
            if (userData && typeof userData === 'object') {
              sessionStorage.setItem('user', JSON.stringify(userData))
            } else {
              throw new Error('Datos de usuario inválidos para guardar')
            }
            localStorage.setItem('remember_me', 'false')
            logger.log('Store: Tokens guardados en sessionStorage')
            logger.log('Store: Verificación sessionStorage:', {
              access_token: sessionStorage.getItem('access_token') ? 'GUARDADO' : 'ERROR',
              user: sessionStorage.getItem('user') ? 'GUARDADO' : 'ERROR'
            })
          }
          
          // 3. ACTUALIZAR ESTADO
          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })

          logger.log('Store: Login completado exitosamente')
          toast.success(`¡Bienvenido, ${userData.nombre}!`)
        } catch (error: any) {
          logger.error('Store: Error en login:', error)
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
          logger.error('Error en logout:', error)
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
        const { user: currentUser } = get()
        
        if (!currentUser) {
          set({ user: null, isAuthenticated: false, isLoading: false })
          return
        }

        set({ isLoading: true })
        
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
          console.warn('Error al refrescar usuario, manteniendo datos actuales:', error)
          // Si falla la actualización, mantener los datos actuales
          set({
            user: currentUser,
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

      // Inicializar autenticación al cargar la aplicación - FIX JSON ERROR
      initializeAuth: async (): Promise<void> => {
        try {
          logger.log('Store: Inicializando autenticación...')
          
          // Verificar si hay tokens guardados
          const rememberMe = localStorage.getItem('remember_me') === 'true'
          const storage = rememberMe ? localStorage : sessionStorage
          
          const accessToken = storage.getItem('access_token')
          const refreshToken = storage.getItem('refresh_token')
          const userData = storage.getItem('user')
          
          logger.log('Store: Tokens encontrados:', {
            accessToken: accessToken ? 'EXISTS' : 'MISSING',
            refreshToken: refreshToken ? 'EXISTS' : 'MISSING',
            userData: userData ? 'EXISTS' : 'MISSING',
            userDataValue: userData, // DEBUG: Ver valor real
            rememberMe
          })
          
          if (accessToken && refreshToken && userData) {
            try {
              // Verificar si el token sigue siendo válido
              // Usar función segura para parsear datos de usuario
              const user = safeParseUserData(userData)
              if (!user) {
                throw new Error('Datos de usuario inválidos o corruptos')
              }
              
              // Actualizar estado con datos guardados
              set({
                user,
                isAuthenticated: true,
                isLoading: false,
                error: null
              })
              
              logger.log('Store: Autenticación restaurada exitosamente')
              
              // Opcional: Verificar con el servidor que el token sigue siendo válido
              try {
                await authService.getCurrentUser()
                logger.log('Store: Token verificado con el servidor')
              } catch (error) {
                logger.log('Store: Token inválido, limpiando almacenamiento')
                // Token inválido, limpiar almacenamiento
                storage.removeItem('access_token')
                storage.removeItem('refresh_token')
                storage.removeItem('user')
                set({
                  user: null,
                  isAuthenticated: false,
                  isLoading: false,
                  error: null
                })
              }
              
            } catch (error) {
              logger.log('Store: Error al parsear datos de usuario:', error)
              // Datos corruptos, limpiar almacenamiento
              storage.removeItem('access_token')
              storage.removeItem('refresh_token')
              storage.removeItem('user')
              set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: null
              })
            }
          } else {
            logger.log('Store: No hay tokens guardados')
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: null
            })
          }
        } catch (error) {
          logger.log('Store: Error al inicializar autenticación:', error)
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: 'Error al inicializar autenticación'
          })
        }
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
    initializeAuth: store.initializeAuth,
  }
}

// Selectores específicos para permisos - SIMPLIFICADOS
export const usePermissions = () => {
  const user = useAuthStore((state) => state.user)
  
  return {
    isAdmin: () => AuthService.isAdmin(user),
    canManagePayments: () => AuthService.canManagePayments(user),
    canViewReports: () => AuthService.canViewReports(user),
    canManageConfig: () => AuthService.canManageConfig(user),
    canViewAllClients: () => AuthService.canViewAllClients(user),
    hasRole: (role: string) => AuthService.hasRole(user, role),
    hasAnyRole: (roles: string[]) => AuthService.hasAnyRole(user, roles),
    userId: user?.id,
    userRole: user?.rol,
    userName: AuthService.getCurrentUserName(user),
    userInitials: AuthService.getCurrentUserInitials(user),
  }
}
