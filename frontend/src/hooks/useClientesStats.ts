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
    staleTime: 1 * 60 * 1000, // ✅ Cache de 1 minuto (reducido para datos más frescos)
    refetchOnWindowFocus: true, // Refrescar cuando el usuario vuelve a la ventana
    refetchOnMount: true, // Refrescar cuando el componente se monta
    refetchInterval: 2 * 60 * 1000 // ✅ Refrescar cada 2 minutos (reducido de 5 minutos)
  })
}
