import { useQuery } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, aÃ±o?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, aÃ±o],
    queryFn: () => pagoService.getKPIs(mes, aÃ±o),
    staleTime: 60 * 1000, // âœ… Cache de 1 minuto - datos frescos pero no excesivo polling
    refetchOnMount: true,
    refetchOnWindowFocus: true, // âœ… Refrescar al enfocar ventana
    refetchInterval: 2 * 60 * 1000, // âœ… Auto-refresh cada 2 minutos (reducido de 30s)
  })
}

