import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../services/api'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { isAdminRole } from '../utils/rol'

interface SidebarCounts {
  pagosPendientes: number

  cuotasEnMora: number

  notificacionesNoLeidas: number
}

/**





 * Hook optimizado que usa React Query para compartir datos con otros componentes





 * Evita llamadas redundantes a las mismas APIs que otros componentes ya están usando





 */

export function useSidebarCounts() {
  const { user } = useSimpleAuth()
  const adminNotifications = isAdminRole(user?.rol)

  // âœ… OPTIMIZACIÓN: Usar React Query para compartir datos con otros componentes

  // Estos queries tienen las mismas queryKeys que otros componentes, así que React Query

  // compartirá los datos en cache y evitará llamadas redundantes

  // Query para KPIs de pagos - compartido con DashboardPagos y otros componentes

  const { data: kpisData, isLoading: loadingKPIs } = useQuery({
    queryKey: ['kpis-pagos'], // âœ… Misma queryKey que DashboardPagos usa (sin filtros)

    queryFn: async () => {
      return (await apiClient.get('/api/v1/pagos/kpis')) as {
        cuotas_pendientes?: number

        clientes_en_mora?: number

        montoCobradoMes?: number

        saldoPorCobrar?: number

        clientesAlDia?: number
      }
    },

    staleTime: 5 * 60 * 1000, // 5 minutos - datos no cambian tan rápido

    refetchOnWindowFocus: false, // âœ… No recargar automáticamente al enfocar ventana

    refetchInterval: 5 * 60 * 1000, // âœ… Actualizar cada 5 minutos automáticamente

    refetchIntervalInBackground: false, // Solo actualizar si la página está visible

    retry: 1, // Solo un retry para evitar múltiples intentos
  })

  // Query para estadísticas de notificaciones - compartido con otros componentes

  const { data: notificacionesData, isLoading: loadingNotificaciones } =
    useQuery({
      queryKey: ['notificaciones-estadisticas-resumen'],

      queryFn: async () => {
        return (await apiClient.get(
          '/api/v1/notificaciones/estadisticas/resumen'
        )) as {
          no_leidas?: number

          total?: number
        }
      },

      enabled: adminNotifications,

      staleTime: 5 * 60 * 1000, // 5 minutos

      refetchOnWindowFocus: false, // âœ… No recargar automáticamente al enfocar ventana

      refetchInterval: adminNotifications ? 5 * 60 * 1000 : false,

      refetchIntervalInBackground: false, // Solo actualizar si la página está visible

      retry: 1,
    })

  // Calcular contadores desde los datos obtenidos

  const counts: SidebarCounts = {
    pagosPendientes: kpisData?.cuotas_pendientes || 0,

    cuotasEnMora: kpisData?.clientes_en_mora || 0,

    notificacionesNoLeidas: adminNotifications
      ? notificacionesData?.no_leidas || 0
      : 0,
  }

  const loading = loadingKPIs || (adminNotifications && loadingNotificaciones)

  return { counts, loading }
}
