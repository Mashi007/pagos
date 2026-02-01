import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

export interface AuditoriaEntry {
  id: number
  usuario: string
  campo_modificado: string
  valor_anterior: string | null
  valor_nuevo: string
  accion: string
  estado_anterior: string | null
  estado_nuevo: string | null
  observaciones: string | null
  fecha_cambio: string
}

export const useAuditoriaPrestamo = (prestamoId: number | null) => {
  return useQuery({
    queryKey: ['auditoria-prestamo', prestamoId],
    queryFn: async (): Promise<AuditoriaEntry[]> => {
      if (!prestamoId) return []
      return await apiClient.get<AuditoriaEntry[]>(`/api/v1/prestamos/auditoria/${prestamoId}`)
    },
    enabled: !!prestamoId,
  })
}

