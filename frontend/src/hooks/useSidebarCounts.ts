import { useState, useEffect } from 'react'
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

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        setLoading(true)
        
        // Obtener KPIs de pagos para cuotas en mora
        const [kpisResponse, notificacionesResponse] = await Promise.allSettled([
          apiClient.get('/api/v1/pagos/kpis'),
          apiClient.get('/api/v1/notificaciones/estadisticas/resumen'),
        ])

        let pagosPendientes = 0
        let cuotasEnMora = 0
        let notificacionesNoLeidas = 0

        // Procesar KPIs de pagos
        if (kpisResponse.status === 'fulfilled') {
          const kpisData = kpisResponse.value.data
          // Cuotas pendientes como pagos pendientes
          pagosPendientes = kpisData?.cuotas_pendientes || 0
          // Clientes en mora como cuotas en mora
          cuotasEnMora = kpisData?.clientes_en_mora || 0
        }

        // Procesar estadísticas de notificaciones
        if (notificacionesResponse.status === 'fulfilled') {
          const notifData = notificacionesResponse.value.data
          notificacionesNoLeidas = notifData?.no_leidas || 0
        }

        setCounts({
          pagosPendientes,
          cuotasEnMora,
          notificacionesNoLeidas,
        })
      } catch (error) {
        // Silenciar errores para no interrumpir la UI
        console.error('Error obteniendo contadores del sidebar:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchCounts()
    
    // Actualizar cada 30 segundos
    const interval = setInterval(fetchCounts, 30000)
    
    return () => clearInterval(interval)
  }, [])

  return { counts, loading }
}

