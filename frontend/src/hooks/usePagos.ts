import { useQuery } from '@tanstack/react-query'
import { pagoService } from '../services/pagoService'

// Hook para obtener KPIs de pagos
export function usePagosKPIs(mes?: number, año?: number) {
  return useQuery({
    queryKey: ['pagos-kpis', mes, año],
    queryFn: ({ signal }) => pagoService.getKPIs(mes, año, { signal }),
    staleTime: 30 * 1000, // 30 s para que al volver a la pestaña o tras registrar pago se vean datos actualizados
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    refetchInterval: 60 * 1000, // Auto-refresh cada 1 minuto (Monto cobrado mes, Pagos hoy)
  })
}

