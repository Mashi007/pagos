// frontend/src/hooks/useModelosVehiculos.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modeloVehiculoService, ModeloVehiculo, ModeloVehiculoCreate, ModeloVehiculoUpdate } from '../services/modeloVehiculoService'
import { hasValidToken } from '../utils/token'
import toast from 'react-hot-toast'

// Constantes de configuraciÃÂ³n
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos
const RETRY_COUNT = 3
const RETRY_DELAY = 1000 // 1 segundo

// Keys para React Query
export const modeloVehiculoKeys = {
  all: ['modelos_vehiculos'] as const,
  lists: () => [...modeloVehiculoKeys.all, 'list'] as const,
  list: (filters?: any) => [...modeloVehiculoKeys.lists(), filters] as const,
  details: () => [...modeloVehiculoKeys.all, 'detail'] as const,
  detail: (id: number) => [...modeloVehiculoKeys.details(), id] as const,
  activos: () => [...modeloVehiculoKeys.all, 'activos'] as const,
}

// Hook para obtener lista de modelos de vehÃÂ­culos
export function useModelosVehiculos(filters?: any) {
  return useQuery({
    queryKey: modeloVehiculoKeys.list(filters),
    queryFn: () => modeloVehiculoService.listarModelos(filters),
    staleTime: STALE_TIME_MEDIUM,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener modelos de vehÃÂ­culos activos (solo cuando hay sesiÃÂ³n vÃÂ¡lida; evita "SesiÃÂ³n expirada" en login)
export function useModelosVehiculosActivos() {
  return useQuery({
    queryKey: modeloVehiculoKeys.activos(),
    queryFn: async () => {
      try {
        return await modeloVehiculoService.listarModelosActivos()
      } catch (error: any) {
        if (error?.message?.includes?.('SesiÃÂ³n expirada')) return []
        console.error('Error obteniendo modelos de vehÃÂ­culos activos:', error)
        return []
      }
    },
    enabled: hasValidToken(),
    staleTime: STALE_TIME_LONG,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener un modelo de vehÃÂ­culo especÃÂ­fico
export function useModeloVehiculo(id: number) {
  return useQuery({
    queryKey: modeloVehiculoKeys.detail(id),
    queryFn: () => modeloVehiculoService.obtenerModelo(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para crear modelo de vehÃÂ­culo
export function useCreateModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ModeloVehiculoCreate) => modeloVehiculoService.crearModelo(data),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })
      toast.success('Modelo de vehÃÂ­culo creado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear modelo de vehÃÂ­culo')
    },
  })
}

// Hook para actualizar modelo de vehÃÂ­culo
export function useUpdateModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ModeloVehiculoUpdate }) =>
      modeloVehiculoService.actualizarModelo(id, data),
    onSuccess: (updatedModeloVehiculo) => {
      // Actualizar cache especÃÂ­fico
      queryClient.setQueryData(
        modeloVehiculoKeys.detail(updatedModeloVehiculo.id),
        updatedModeloVehiculo
      )

      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })

      toast.success('Modelo de vehÃÂ­culo actualizado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar modelo de vehÃÂ­culo')
    },
  })
}

// Hook para eliminar modelo de vehÃÂ­culo
export function useDeleteModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => modeloVehiculoService.eliminarModelo(id),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })
      toast.success('Modelo de vehÃÂ­culo eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar modelo de vehÃÂ­culo')
    },
  })
}

