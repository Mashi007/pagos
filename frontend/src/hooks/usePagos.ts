import { useQuery } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, año?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, año],
    queryFn: ({ signal }) => pagoService.getKPIs(mes, año, { signal }),
    staleTime: 60 * 1000, // ✅ Cache de 1 minuto - datos frescos pero no excesivo polling
    refetchOnMount: true,
    refetchOnWindowFocus: true, // ✅ Refrescar al enfocar ventana
    refetchInterval: 2 * 60 * 1000, // ✅ Auto-refresh cada 2 minutos (reducido de 30s)
  })
}

