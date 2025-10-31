import { useQuery } from '@tanstack/react-query'
import { pagoService } from '@/services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, año?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, año],
    queryFn: () => pagoService.getKPIs(mes, año),
    staleTime: 0, // ✅ Sin cache - siempre datos frescos desde BD
    refetchOnMount: true,
    refetchOnWindowFocus: true, // ✅ Refrescar al enfocar ventana
    refetchInterval: 30 * 1000, // ✅ Auto-refresh cada 30 segundos
  })
}

