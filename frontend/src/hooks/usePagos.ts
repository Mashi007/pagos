import { useQuery } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, año?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, año],
    queryFn: ({ signal }) => pagoService.getKPIs(mes, año, { signal }),
    staleTime: 5 * 60 * 1000, // 5 min; sin polling automatico de KPIs
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchInterval: false, // desactivado: ya no GET /pagos/kpis cada minuto
  })
}

