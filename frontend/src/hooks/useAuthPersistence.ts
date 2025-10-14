import { useEffect, useState } from 'react'
import { useAuth } from '@/store/authStore'

/**
 * Hook simplificado para restaurar la sesión al cargar la aplicación
 * RESPONSABILIDAD ÚNICA: Solo restaurar datos existentes
 */
export function useAuthPersistence() {
  const { setUser } = useAuth()
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const restoreSession = () => {
      console.log('Restaurando sesión...')
      
      try {
        // Buscar datos en localStorage primero
        const localToken = localStorage.getItem('access_token')
        const localUser = localStorage.getItem('user')
        
        if (localToken && localUser) {
          const user = JSON.parse(localUser)
          setUser(user)
          console.log('Sesión restaurada desde localStorage:', user.nombre)
          setIsInitialized(true)
          return
        }
        
        // Si no hay en localStorage, buscar en sessionStorage
        const sessionToken = sessionStorage.getItem('access_token')
        const sessionUser = sessionStorage.getItem('user')
        
        if (sessionToken && sessionUser) {
          const user = JSON.parse(sessionUser)
          setUser(user)
          console.log('Sesión restaurada desde sessionStorage:', user.nombre)
          setIsInitialized(true)
          return
        }
        
        // No hay sesión para restaurar
        console.log('No hay sesión para restaurar')
        setIsInitialized(true)
        
      } catch (error) {
        console.error('Error restaurando sesión:', error)
        setIsInitialized(true)
      }
    }

    if (!isInitialized) {
      restoreSession()
    }
  }, [isInitialized, setUser])

  return { isInitialized }
}
