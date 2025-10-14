import { useEffect, useState } from 'react'
import { useAuth } from '@/store/authStore'
import { authService } from '@/services/authService'

/**
 * Hook personalizado para manejar la persistencia de autenticación
 * Se encarga de restaurar la sesión del usuario al cargar la aplicación
 */
export function useAuthPersistence() {
  const { isAuthenticated, refreshUser, setUser } = useAuth()
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
          isAuthenticated,
          rememberMe,
          storageType: rememberMe ? 'localStorage' : 'sessionStorage'
        })
        
        if (hasToken && storedUser) {
          console.log('✅ Datos de autenticación encontrados, restaurando sesión...')
          
          // Restaurar inmediatamente el usuario en el store
          setUser(storedUser)
          
          try {
            // Intentar verificar la validez del token con el servidor
            await refreshUser()
            console.log('✅ Sesión restaurada exitosamente')
          } catch (error) {
            console.warn('⚠️ Error al verificar token con servidor, manteniendo sesión local:', error)
            // Si falla la verificación pero tenemos datos válidos, mantenerlos
            // El usuario ya está restaurado en el store
          }
        } else {
          console.log('❌ No se encontraron datos de autenticación válidos')
          // Asegurar que el estado esté limpio
          if (isAuthenticated) {
            console.log('🧹 Limpiando estado de autenticación inconsistente')
            authService.logout()
          }
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
