import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/api'

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

/** Respuesta del backend GET /api/v1/auditoria (items con forma AuditoriaItem). */
interface AuditoriaItemBackend {
  id: number
  usuario_email?: string | null
  accion: string
  modulo?: string | null
  campo?: string | null
  descripcion?: string | null
  datos_anteriores?: unknown
  datos_nuevos?: unknown
  fecha: string
}

function mapAuditoriaItemToEntry(item: AuditoriaItemBackend): AuditoriaEntry {
  const valorAnt = item.datos_anteriores != null ? (typeof item.datos_anteriores === 'string' ? item.datos_anteriores : JSON.stringify(item.datos_anteriores)) : null
  const valorNuevo = item.datos_nuevos != null ? (typeof item.datos_nuevos === 'string' ? item.datos_nuevos : JSON.stringify(item.datos_nuevos)) : ''
  const datosAnt = item.datos_anteriores && typeof item.datos_anteriores === 'object' && item.datos_anteriores !== null ? item.datos_anteriores as Record<string, unknown> : null
  const datosNuevos = item.datos_nuevos && typeof item.datos_nuevos === 'object' && item.datos_nuevos !== null ? item.datos_nuevos as Record<string, unknown> : null
  const estadoAnterior = datosAnt && 'estado' in datosAnt ? String(datosAnt.estado) : null
  const estadoNuevo = datosNuevos && 'estado' in datosNuevos ? String(datosNuevos.estado) : null
  return {
    id: item.id,
    usuario: item.usuario_email ?? '',
    campo_modificado: item.campo ?? '',
    valor_anterior: valorAnt,
    valor_nuevo: valorNuevo,
    accion: item.accion,
    estado_anterior: estadoAnterior,
    estado_nuevo: estadoNuevo,
    observaciones: item.descripcion ?? null,
    fecha_cambio: item.fecha,
  }
}

export const useAuditoriaPrestamo = (prestamoId: number | null) => {
  return useQuery({
    queryKey: ['auditoria-prestamo', prestamoId],
    queryFn: async (): Promise<AuditoriaEntry[]> => {
      if (!prestamoId) return []
      const url = `/api/v1/auditoria?modulo=prestamos&registro_id=${prestamoId}&limit=100&skip=0`
      const response = await apiClient.get<{ items: AuditoriaItemBackend[] }>(url)
      const items = response?.items ?? []
      return items.map(mapAuditoriaItemToEntry)
    },
    enabled: !!prestamoId,
  })
}

