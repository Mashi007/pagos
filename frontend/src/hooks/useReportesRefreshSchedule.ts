import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

/** Horas de actualización automática (1 AM y 1 PM, hora local del usuario). */
const REFRESH_HOURS = [1, 13]

/** Query keys que se invalidan a la 1 AM y 1 PM para refrescar reportes desde BD. */
const REPORTE_QUERY_KEYS = [
  'reportes-resumen',
  'morosidad-por-rangos',
  'pagos-por-mes',
  'productos-por-mes',
  'asesores-por-mes',
  'cartera-por-mes',
]

/**
 * Hook que invalida las queries de reportes a la 1 AM y 1 PM (hora local)
 * para que los datos se actualicen automáticamente desde la BD.
 */
export function useReportesRefreshSchedule() {
  const queryClient = useQueryClient()
  const lastRefreshHour = useRef<number | null>(null)

  useEffect(() => {
    const checkAndRefresh = () => {
      const now = new Date()
      const hour = now.getHours()

      if (REFRESH_HOURS.includes(hour)) {
        // Evitar múltiples invalidaciones en la misma hora
        if (lastRefreshHour.current !== hour) {
          lastRefreshHour.current = hour
          REPORTE_QUERY_KEYS.forEach((key) => {
            queryClient.invalidateQueries({ queryKey: [key] })
          })
        }
      } else {
        lastRefreshHour.current = null
      }
    }

    checkAndRefresh()
    const interval = setInterval(checkAndRefresh, 60 * 1000) // Revisar cada minuto
    return () => clearInterval(interval)
  }, [queryClient])
}
