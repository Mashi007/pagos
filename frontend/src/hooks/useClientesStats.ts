import { useQuery } from '@tanstack/react-query'
import { clienteService } from '@/services/clienteService'

interface ClientesStats {
  total: number
  activos: number
  inactivos: number
  finalizados: number
}

export function useClientesStats() {
  return useQuery<ClientesStats>({
    queryKey: ['clientes-stats'],
    queryFn: async () => {
      console.log('📊 Obteniendo estadísticas de clientes...')
      
      // Obtener todos los clientes para calcular estadísticas
      const response = await clienteService.getClientes({}, 1, 1000) // Obtener hasta 1000 clientes
      
      const clientes = response.data
      
      // Calcular estadísticas
      const stats: ClientesStats = {
        total: clientes.length,
        activos: clientes.filter(c => c.estado === 'ACTIVO').length,
        inactivos: clientes.filter(c => c.estado === 'INACTIVO').length,
        finalizados: clientes.filter(c => c.estado === 'FINALIZADO').length
      }
      
      console.log('📊 Estadísticas calculadas:', stats)
      return stats
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    refetchOnWindowFocus: false
  })
}
