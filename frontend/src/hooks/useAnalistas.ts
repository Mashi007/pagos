// frontend/src/hooks/useAnalistas.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { analistaService, Analista, AnalistaCreate, AnalistaUpdate } from '@/services/analistaService'
import toast from 'react-hot-toast'

// Constantes de configuración
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos
const RETRY_COUNT = 3
const RETRY_DELAY = 1000 // 1 segundo

// Keys para React Query
export const analistaKeys = {
  all: ['analistas'] as const,
  lists: () => [...analistaKeys.all, 'list'] as const,
  list: (filters?: any) => [...analistaKeys.lists(), filters] as const,
  details: () => [...analistaKeys.all, 'detail'] as const,
  detail: (id: number) => [...analistaKeys.details(), id] as const,
  activos: () => [...analistaKeys.all, 'activos'] as const,
}

// Hook para obtener lista de analistas
export function useAnalistas(filters?: any) {
  return useQuery({
    queryKey: analistaKeys.list(filters),
    queryFn: () => analistaService.listarAnalistas(filters),
    staleTime: STALE_TIME_MEDIUM,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener analistas activos
export function useAnalistasActivos() {
  return useQuery({
    queryKey: analistaKeys.activos(),
    queryFn: async () => {
      try {
        return await analistaService.listarAnalistasActivos()
      } catch (error) {
        console.error('Error obteniendo analistas activos:', error)
        return [] // Devolver array vacío en caso de error
      }
    },
    staleTime: STALE_TIME_LONG,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener un analista específico
export function useAnalista(id: number) {
  return useQuery({
    queryKey: analistaKeys.detail(id),
    queryFn: () => analistaService.obtenerAnalista(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para crear analista
export function useCreateAnalista() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: AnalistaCreate) => analistaService.crearAnalista(data),
    onSuccess: () => {
      // Invalidar todas las listas de analistas
      queryClient.invalidateQueries({ queryKey: analistaKeys.lists() })
      queryClient.invalidateQueries({ queryKey: analistaKeys.activos() })
      toast.success('Analista creado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear analista')
    },
  })
}

// Hook para actualizar analista
export function useUpdateAnalista() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AnalistaUpdate }) =>
      analistaService.actualizarAnalista(id, data),
    onSuccess: (updatedAnalista) => {
      // Actualizar cache específico
      queryClient.setQueryData(
        analistaKeys.detail(updatedAnalista.id),
        updatedAnalista
      )

      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: analistaKeys.lists() })
      queryClient.invalidateQueries({ queryKey: analistaKeys.activos() })

      toast.success('Analista actualizado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar analista')
    },
  })
}

// Hook para eliminar analista
export function useDeleteAnalista() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => analistaService.eliminarAnalista(id),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: analistaKeys.lists() })
      queryClient.invalidateQueries({ queryKey: analistaKeys.activos() })
      toast.success('Analista eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar analista')
    },
  })
}
