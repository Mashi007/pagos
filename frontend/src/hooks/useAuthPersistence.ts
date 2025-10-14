import { useEffect, useState } from 'react'
import { useAuth } from '@/store/authStore'
import { authService } from '@/services/authService'

/**
 * Hook personalizado para manejar la persistencia de autenticación
 * Se encarga de restaurar la sesión del usuario al cargar la aplicación
 */
export function useAuthPersistence() {
  const { setUser } = useAuth()
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const initializeAuth = async () => {
      console.log('🔄 Inicializando persistencia de autenticación...')
      
      try {
        // Verificar si hay datos de autenticación almacenados
        const hasToken = authService.getStoredToken()
        const storedUser = authService.getStoredUser()
        const rememberMe = localStorage.getItem('remember_me') === 'true'
        
        console.log('📊 Estado de autenticación:', {
          hasToken: !!hasToken,
          hasStoredUser: !!storedUser,
          rememberMe,
          storageType: rememberMe ? 'localStorage' : 'sessionStorage'
        })
        
            // Debug adicional
            console.log('🔍 Datos encontrados en storage:', {
              hasStoredUser: !!storedUser,
              hasToken: !!hasToken,
              rememberMe,
              storageType: rememberMe ? 'localStorage' : 'sessionStorage'
            })
            
            // Debug detallado de localStorage y sessionStorage
            console.log('🔍 Debug detallado de storage:', {
              localStorage: {
                access_token: localStorage.getItem('access_token') ? 'EXISTS' : 'NOT_FOUND',
                refresh_token: localStorage.getItem('refresh_token') ? 'EXISTS' : 'NOT_FOUND',
                user: localStorage.getItem('user') ? 'EXISTS' : 'NOT_FOUND',
                remember_me: localStorage.getItem('remember_me')
              },
              sessionStorage: {
                access_token: sessionStorage.getItem('access_token') ? 'EXISTS' : 'NOT_FOUND',
                refresh_token: sessionStorage.getItem('refresh_token') ? 'EXISTS' : 'NOT_FOUND',
                user: sessionStorage.getItem('user') ? 'EXISTS' : 'NOT_FOUND'
              }
            })
        
        if (hasToken && storedUser) {
          console.log('✅ Datos de autenticación encontrados, restaurando sesión...')
          
          // Restaurar inmediatamente el usuario en el store
          setUser(storedUser)
          console.log('✅ Sesión restaurada exitosamente')
        } else {
          console.log('❌ No se encontraron datos de autenticación válidos')
        }
      } catch (error) {
        console.error('❌ Error crítico al inicializar autenticación:', error)
        // En caso de error crítico, limpiar todo
        authService.logout()
      } finally {
        setIsInitialized(true)
        console.log('✅ Inicialización de autenticación completada')
      }
    }

    // Solo ejecutar una vez al montar el componente
    if (!isInitialized) {
      initializeAuth()
    }
  }, []) // Dependencias vacías para ejecutar solo una vez

  return {
    isInitialized,
  }
}
