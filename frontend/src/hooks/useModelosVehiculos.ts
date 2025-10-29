// frontend/src/hooks/useModelosVehiculos.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modeloVehiculoService, ModeloVehiculo, ModeloVehiculoCreate, ModeloVehiculoUpdate } from '@/services/modeloVehiculoService'
import toast from 'react-hot-toast'

// Constantes de configuración
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

// Hook para obtener lista de modelos de vehículos
export function useModelosVehiculos(filters?: any) {
  return useQuery({
    queryKey: modeloVehiculoKeys.list(filters),
    queryFn: () => modeloVehiculoService.listarModelos(filters),
    staleTime: STALE_TIME_MEDIUM,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener modelos de vehículos activos
export function useModelosVehiculosActivos() {
  return useQuery({
    queryKey: modeloVehiculoKeys.activos(),
    queryFn: async () => {
      try {
        return await modeloVehiculoService.listarModelosActivos()
      } catch (error) {
        console.error('Error obteniendo modelos de vehículos activos:', error)
        return [] // Devolver array vacío en caso de error
      }
    },
    staleTime: STALE_TIME_LONG,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para obtener un modelo de vehículo específico
export function useModeloVehiculo(id: number) {
  return useQuery({
    queryKey: modeloVehiculoKeys.detail(id),
    queryFn: () => modeloVehiculoService.obtenerModelo(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para crear modelo de vehículo
export function useCreateModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ModeloVehiculoCreate) => modeloVehiculoService.crearModelo(data),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })
      toast.success('Modelo de vehículo creado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear modelo de vehículo')
    },
  })
}

// Hook para actualizar modelo de vehículo
export function useUpdateModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ModeloVehiculoUpdate }) =>
      modeloVehiculoService.actualizarModelo(id, data),
    onSuccess: (updatedModeloVehiculo) => {
      // Actualizar cache específico
      queryClient.setQueryData(
        modeloVehiculoKeys.detail(updatedModeloVehiculo.id),
        updatedModeloVehiculo
      )
      
      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })
      
      toast.success('Modelo de vehículo actualizado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar modelo de vehículo')
    },
  })
}

// Hook para eliminar modelo de vehículo
export function useDeleteModeloVehiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => modeloVehiculoService.eliminarModelo(id),
    onSuccess: () => {
      // Invalidar todas las listas
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: modeloVehiculoKeys.activos() })
      toast.success('Modelo de vehículo eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar modelo de vehículo')
    },
  })
}

