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
    staleTime: 0, // Siempre actualizar
    refetchOnWindowFocus: true, // Refrescar cuando el usuario vuelve a la ventana
    refetchOnMount: true, // Refrescar cuando el componente se monta
    refetchInterval: 60000 // Refrescar cada minuto
  })
}
