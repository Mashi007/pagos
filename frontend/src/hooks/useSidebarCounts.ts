import { useState, useEffect, useRef } from 'react'
import { apiClient } from '@/services/api'

interface SidebarCounts {
  pagosPendientes: number
  cuotasEnMora: number
  notificacionesNoLeidas: number
}

export function useSidebarCounts() {
  const [counts, setCounts] = useState<SidebarCounts>({
    pagosPendientes: 0,
    cuotasEnMora: 0,
    notificacionesNoLeidas: 0,
  })
  const [loading, setLoading] = useState(true)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const fetchCounts = async () => {
      // Cancelar petición anterior si existe
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      // Crear nuevo AbortController para esta petición
      abortControllerRef.current = new AbortController()
      const signal = abortControllerRef.current.signal

      try {
        setLoading(true)
        
        // Obtener KPIs de pagos para cuotas en mora
        const [kpisResponse, notificacionesResponse] = await Promise.allSettled([
          apiClient.get('/api/v1/pagos/kpis', { signal }),
          apiClient.get('/api/v1/notificaciones/estadisticas/resumen', { signal }),
        ])

        // Si la petición fue cancelada, no actualizar estado
        if (signal.aborted) return

        let pagosPendientes = 0
        let cuotasEnMora = 0
        let notificacionesNoLeidas = 0

        // Procesar KPIs de pagos
        if (kpisResponse.status === 'fulfilled') {
          const kpisData = kpisResponse.value as any
          // Cuotas pendientes como pagos pendientes
          pagosPendientes = kpisData?.cuotas_pendientes || 0
          // Clientes en mora como cuotas en mora
          cuotasEnMora = kpisData?.clientes_en_mora || 0
        }

        // Procesar estadísticas de notificaciones
        if (notificacionesResponse.status === 'fulfilled') {
          const notifData = notificacionesResponse.value as any
          notificacionesNoLeidas = notifData?.no_leidas || 0
        }

        setCounts({
          pagosPendientes,
          cuotasEnMora,
          notificacionesNoLeidas,
        })
      } catch (error: any) {
        // Ignorar errores de cancelación
        if (error?.name === 'AbortError' || signal.aborted) return
        // Silenciar errores para no interrumpir la UI
        console.error('Error obteniendo contadores del sidebar:', error)
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    // Cargar inmediatamente
    fetchCounts()
    
    // Verificar si la página está visible antes de actualizar
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchCounts()
      }
    }

    // Suscribirse a cambios de visibilidad
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Actualizar cada 2 minutos (120 segundos) en lugar de 30 segundos
    // Esto reduce significativamente la carga del servidor
    const interval = setInterval(() => {
      // Solo actualizar si la página está visible
      if (document.visibilityState === 'visible') {
        fetchCounts()
      }
    }, 120000) // 2 minutos
    
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      // Cancelar petición pendiente al desmontar
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return { counts, loading }
}

