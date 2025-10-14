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
        // PRIMERO: Verificar si hay tokens en localStorage (recordarme)
        const localToken = localStorage.getItem('access_token')
        const localUser = localStorage.getItem('user')
        
        // SEGUNDO: Si no hay en localStorage, verificar sessionStorage
        const sessionToken = sessionStorage.getItem('access_token')
        const sessionUser = sessionStorage.getItem('user')
        
        // DETERMINAR: Qué storage usar basado en qué tokens existen
        const hasLocalData = !!(localToken && localUser)
        const hasSessionData = !!(sessionToken && sessionUser)
        
        let hasToken, storedUser, rememberMe, storageType
        
        if (hasLocalData) {
          // Hay datos en localStorage - usar recordarme
          hasToken = localToken
          try {
            storedUser = JSON.parse(localUser)
            rememberMe = true
            storageType = 'localStorage'
          } catch (error) {
            console.error('Error parsing localStorage user:', error)
            hasToken = null
            storedUser = null
            rememberMe = false
            storageType = 'none'
          }
        } else if (hasSessionData) {
          // Solo hay datos en sessionStorage - sesión temporal
          hasToken = sessionToken
          try {
            storedUser = JSON.parse(sessionUser)
            rememberMe = false
            storageType = 'sessionStorage'
          } catch (error) {
            console.error('Error parsing sessionStorage user:', error)
            hasToken = null
            storedUser = null
            rememberMe = false
            storageType = 'none'
          }
        } else {
          // No hay datos en ningún lado
          hasToken = null
          storedUser = null
          rememberMe = false
          storageType = 'none'
        }
        
        console.log('📊 Estado de autenticación MEJORADO:', {
          hasLocalData,
          hasSessionData,
          hasToken: !!hasToken,
          hasStoredUser: !!storedUser,
          rememberMe,
          storageType
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
          console.log('✅ Sesión restaurada exitosamente para:', storedUser.nombre)
          
          // Verificar que el token sigue disponible después de restaurar
          setTimeout(() => {
            const tokenAfterRestore = authService.getStoredToken()
            console.log('🔍 Verificación post-restauración:', {
              tokenDisponible: !!tokenAfterRestore,
              tokenLength: tokenAfterRestore?.length || 0
            })
          }, 100)
        } else {
          console.log('❌ No se encontraron datos de autenticación válidos')
          console.log('🔍 Detalles de la verificación:', {
            hasToken: !!hasToken,
            hasStoredUser: !!storedUser,
            tokenValue: hasToken,
            userValue: storedUser
          })
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
  }, [isInitialized, setUser]) // Agregar dependencias correctas

  return {
    isInitialized,
  }
}
