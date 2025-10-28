import { useQuery } from '@tanstack/react-query'
import { clienteService } from '@/services/clienteService'

// Constantes de configuración
const MAX_CLIENTES_STATS = 1000
const STALE_TIME_STATS = 5 * 60 * 1000 // 5 minutos

interface ClientesStats {
  total: number
  activos: number
  inactivos: number
  finalizados: number
}

export function useClientesStats() {
  return useQuery({
    queryKey: ['clientes-stats'],
    queryFn: async (): Promise<ClientesStats> => {
      // Obtener todos los clientes para calcular estadísticas
      const response = await clienteService.getClientes({}, 1, MAX_CLIENTES_STATS)
      
      const clientes = response.data
      
      // Calcular estadísticas
      const stats: ClientesStats = {
        total: clientes.length,
        activos: clientes.filter(c => c.estado === 'ACTIVO').length,
        inactivos: clientes.filter(c => c.estado === 'INACTIVO').length,
        finalizados: clientes.filter(c => c.estado === 'FINALIZADO').length
      }
      
      return stats
    },
    staleTime: 0, // Cambiado a 0 para que siempre se actualice
    refetchOnWindowFocus: true, // Refrescar cuando el usuario vuelve a la ventana
    refetchOnMount: true // Refrescar cuando el componente se monta
  })
}
