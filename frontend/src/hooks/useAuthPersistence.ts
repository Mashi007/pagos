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
