import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/api'

interface SidebarCounts {
  pagosPendientes: number
  cuotasEnMora: number
  notificacionesNoLeidas: number
}

/**
 * Hook optimizado que usa React Query para compartir datos con otros componentes
 * Evita llamadas redundantes a las mismas APIs que otros componentes ya estÃÂ¡n usando
 */
export function useSidebarCounts() {
  // ÃÂ¢ÃÂÃ¢ÂÂ¦ OPTIMIZACIÃÂN: Usar React Query para compartir datos con otros componentes
  // Estos queries tienen las mismas queryKeys que otros componentes, asÃÂ­ que React Query
  // compartirÃÂ¡ los datos en cache y evitarÃÂ¡ llamadas redundantes
  
  // Query para KPIs de pagos - compartido con DashboardPagos y otros componentes
  const { data: kpisData, isLoading: loadingKPIs } = useQuery({
    queryKey: ['kpis-pagos'], // ÃÂ¢ÃÂÃ¢ÂÂ¦ Misma queryKey que DashboardPagos usa (sin filtros)
    queryFn: async () => {
      return await apiClient.get('/api/v1/pagos/kpis') as {
        cuotas_pendientes?: number
        clientes_en_mora?: number
        montoCobradoMes?: number
        saldoPorCobrar?: number
        clientesAlDia?: number
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutos - datos no cambian tan rÃÂ¡pido
    refetchOnWindowFocus: false, // ÃÂ¢ÃÂÃ¢ÂÂ¦ No recargar automÃÂ¡ticamente al enfocar ventana
    refetchInterval: 5 * 60 * 1000, // ÃÂ¢ÃÂÃ¢ÂÂ¦ Actualizar cada 5 minutos automÃÂ¡ticamente
    refetchIntervalInBackground: false, // Solo actualizar si la pÃÂ¡gina estÃÂ¡ visible
    retry: 1, // Solo un retry para evitar mÃÂºltiples intentos
  })

  // Query para estadÃÂ­sticas de notificaciones - compartido con otros componentes
  const { data: notificacionesData, isLoading: loadingNotificaciones } = useQuery({
    queryKey: ['notificaciones-estadisticas-resumen'],
    queryFn: async () => {
      return await apiClient.get('/api/v1/notificaciones/estadisticas/resumen') as {
        no_leidas?: number
        total?: number
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    refetchOnWindowFocus: false, // ÃÂ¢ÃÂÃ¢ÂÂ¦ No recargar automÃÂ¡ticamente al enfocar ventana
    refetchInterval: 5 * 60 * 1000, // ÃÂ¢ÃÂÃ¢ÂÂ¦ Actualizar cada 5 minutos automÃÂ¡ticamente
    refetchIntervalInBackground: false, // Solo actualizar si la pÃÂ¡gina estÃÂ¡ visible
    retry: 1,
  })

  // Calcular contadores desde los datos obtenidos
  const counts: SidebarCounts = {
    pagosPendientes: kpisData?.cuotas_pendientes || 0,
    cuotasEnMora: kpisData?.clientes_en_mora || 0,
    notificacionesNoLeidas: notificacionesData?.no_leidas || 0,
  }

  const loading = loadingKPIs || loadingNotificaciones

  return { counts, loading }
}

