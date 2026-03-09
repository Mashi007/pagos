import { useQuery } from '@tanstack/react-query'
import { clienteService } from '../services/clienteService'

interface ClientesStats {
  total: number
  activos: number
  inactivos: number
  finalizados: number
  nuevos_este_mes: number
}

export function useClientesStats() {
  return useQuery({
    queryKey: ['clientes-stats'],
    queryFn: async (): Promise<ClientesStats> => {
      // Obtener estadísticas directamente desde el endpoint del backend
      // Esto es más eficiente que traer todos los clientes
      return await clienteService.getStats()
    },
    staleTime: 30 * 1000, // 30 s para que el KPI "Nuevos Clientes este mes" se actualice pronto
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    refetchInterval: 60 * 1000, // Refrescar cada 1 minuto
  })
}
