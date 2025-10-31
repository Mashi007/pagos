import { useQuery } from '@tanstack/react-query'
import { pagoService } from '@/services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, año?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, año],
    queryFn: () => pagoService.getKPIs(mes, año),
    staleTime: 2 * 60 * 1000, // 2 minutos
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  })
}

