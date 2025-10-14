import { useEffect } from 'react'
import { useAuth } from '@/store/authStore'
import { authService } from '@/services/authService'

/**
 * Hook personalizado para manejar la persistencia de autenticación
 * Se encarga de restaurar la sesión del usuario al cargar la aplicación
 */
export function useAuthPersistence() {
  const { isAuthenticated, refreshUser, setUser } = useAuth()

  useEffect(() => {
    const initializeAuth = async () => {
      // Verificar si hay datos de autenticación almacenados
      const hasToken = authService.getStoredToken()
      const storedUser = authService.getStoredUser()
      
      if (hasToken && storedUser && !isAuthenticated) {
        try {
          // Restaurar inmediatamente el usuario desde el almacenamiento
          setUser(storedUser)
          
          // Intentar verificar la validez del token con el servidor
          await refreshUser()
        } catch (error) {
          console.warn('Error al restaurar sesión:', error)
          // Si falla la verificación, limpiar datos inválidos
          authService.logout()
        }
      }
    }

    initializeAuth()
  }, []) // Solo ejecutar una vez al montar el componente

  return {
    isInitialized: true, // Podríamos agregar un estado de inicialización si es necesario
  }
}
