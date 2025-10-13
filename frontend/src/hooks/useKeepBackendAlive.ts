import { useEffect } from 'react'

// Hook para mantener el backend activo
export function useKeepBackendAlive() {
  useEffect(() => {
    const pingBackend = async () => {
      try {
        // Ping cada 5 minutos para mantener el backend activo
        await fetch('https://pagos-f2qf.onrender.com/', {
          method: 'GET',
          mode: 'no-cors' // Evitar problemas de CORS
        })
        console.log('Backend ping exitoso')
      } catch (error) {
        console.log('Backend ping falló:', error)
      }
    }

    // Ping inmediato
    pingBackend()

    // Ping cada 5 minutos
    const interval = setInterval(pingBackend, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [])
}
