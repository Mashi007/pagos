// frontend/src/hooks/useConcesionarios.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { concesionarioService, Concesionario, ConcesionarioCreate, ConcesionarioUpdate } from '@/services/concesionarioService'
import toast from 'react-hot-toast'

// Constantes de configuración
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos
const RETRY_COUNT = 3
const RETRY_DELAY = 1000 // 1 segundo

// Keys para React Query
export const concesionarioKeys = {
  all: ['concesionarios'] as const,
  lists: () => [...concesionarioKeys.all, 'list'] as const,
  list: (filters?: any) => [...concesionarioKeys.lists(), filters] as const,
  details: () => [...concesionarioKeys.all, 'detail'] as const,
  detail: (id: number) => [...concesionarioKeys.details(), id] as const,
  activos: () => [...concesionarioKeys.all, 'activos'] as const,
}

// Hook para obtener lista de concesionarios
export function useConcesionarios(filters?: any) {
  return useQuery({
    queryKey: concesionarioKeys.list(filters),
    queryFn: () => concesionarioService.listarConcesionarios(filters),
    staleTime: STALE_TIME_MEDIUM,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener concesionarios activos
export function useConcesionariosActivos() {
  return useQuery({
    queryKey: concesionarioKeys.activos(),
    queryFn: () => concesionarioService.listarConcesionariosActivos(),
    staleTime: STALE_TIME_LONG,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener un concesionario específico
export function useConcesionario(id: number) {
  return useQuery({
    queryKey: concesionarioKeys.detail(id),
    queryFn: () => concesionarioService.obtenerConcesionario(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para crear concesionario
export function useCreateConcesionario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ConcesionarioCreate) => concesionarioService.crearConcesionario(data),
    onSuccess: () => {
      // Invalidar todas las listas de concesionarios
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.lists() })
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.activos() })
      toast.success('Concesionario creado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear concesionario')
    },
  })
}

// Hook para actualizar concesionario
export function useUpdateConcesionario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ConcesionarioUpdate }) =>
      concesionarioService.actualizarConcesionario(id, data),
    onSuccess: (updatedConcesionario) => {
      // Actualizar cache específico
      queryClient.setQueryData(
        concesionarioKeys.detail(updatedConcesionario.id),
        updatedConcesionario
      )
      
      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.lists() })
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.activos() })
      
      toast.success('Concesionario actualizado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar concesionario')
    },
  })
}

// Hook para eliminar concesionario
export function useDeleteConcesionario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => concesionarioService.eliminarConcesionario(id),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.lists() })
      queryClient.invalidateQueries({ queryKey: concesionarioKeys.activos() })
      toast.success('Concesionario eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar concesionario')
    },
  })
}

