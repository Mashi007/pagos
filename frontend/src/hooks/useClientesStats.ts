import { useQuery } from '@tanstack/react-query'
import { clienteService } from '@/services/clienteService'

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
      // Obtener estadísticas directamente desde el endpoint del backend
      // Esto es más eficiente que traer todos los clientes
      return await clienteService.getStats()
    },
    staleTime: 2 * 60 * 1000, // Cache de 2 minutos (optimizado)
    refetchOnWindowFocus: true, // Refrescar cuando el usuario vuelve a la ventana
    refetchOnMount: true, // Refrescar cuando el componente se monta
    refetchInterval: 5 * 60 * 1000 // Refrescar cada 5 minutos (optimizado de 1 minuto)
  })
}
