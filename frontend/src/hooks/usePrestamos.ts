import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { prestamoService } from '@/services/prestamoService'
import { Prestamo, PrestamoForm } from '@/types'
import toast from 'react-hot-toast'

// Constantes de configuración
const DEFAULT_PER_PAGE = 20
const STALE_TIME_SHORT = 2 * 60 * 1000 // 2 minutos
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos

// Keys para React Query
export const prestamoKeys = {
  all: ['prestamos'] as const,
  lists: () => [...prestamoKeys.all, 'list'] as const,
  list: (filters?: { search?: string; estado?: string }) => [...prestamoKeys.lists(), filters] as const,
  details: () => [...prestamoKeys.all, 'detail'] as const,
  detail: (id: number) => [...prestamoKeys.details(), id] as const,
  search: (query: string) => [...prestamoKeys.all, 'search', query] as const,
  byCedula: (cedula: string) => [...prestamoKeys.all, 'cedula', cedula] as const,
  auditoria: (prestamoId: number) => [...prestamoKeys.all, 'auditoria', prestamoId] as const,
}

// Hook para obtener lista de préstamos
export function usePrestamos(
  filters?: { search?: string; estado?: string },
  page: number = 1,
  perPage: number = DEFAULT_PER_PAGE
) {
  return useQuery({
    queryKey: prestamoKeys.list(filters),
    queryFn: () => prestamoService.getPrestamos(filters, page, perPage),
    staleTime: STALE_TIME_SHORT, // 2 minutos para reflejar cambios más rápido
  })
}

// Hook para obtener un préstamo específico
export function usePrestamo(id: number) {
  return useQuery({
    queryKey: prestamoKeys.detail(id),
    queryFn: () => prestamoService.getPrestamo(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para búsqueda de préstamos
export function useSearchPrestamos(query: string) {
  return useQuery({
    queryKey: prestamoKeys.search(query),
    queryFn: () => prestamoService.searchPrestamos(query),
    enabled: query.length > 0,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para obtener préstamos por cédula
export function usePrestamosByCedula(cedula: string) {
  return useQuery({
    queryKey: prestamoKeys.byCedula(cedula),
    queryFn: () => prestamoService.getPrestamosByCedula(cedula),
    enabled: cedula.length > 0,
    staleTime: STALE_TIME_MEDIUM,
  })
}

// Hook para obtener auditoría de un préstamo
export function useAuditoriaPrestamo(prestamoId: number) {
  return useQuery({
    queryKey: prestamoKeys.auditoria(prestamoId),
    queryFn: () => prestamoService.getAuditoria(prestamoId),
    enabled: !!prestamoId,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para crear un préstamo
export function useCreatePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PrestamoForm) => prestamoService.createPrestamo(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      toast.success('Préstamo creado exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al crear préstamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para actualizar un préstamo
export function useUpdatePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<PrestamoForm> }) =>
      prestamoService.updatePrestamo(id, data),
    onSuccess: (data, variables) => {
      // Actualizar datos del cache directamente con la respuesta del servidor
      queryClient.setQueryData(prestamoKeys.detail(variables.id), data)
      
      // Invalidar todas las queries para forzar refetch
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
      
      // Refetch específico para asegurar actualización
      queryClient.refetchQueries({ 
        queryKey: prestamoKeys.all,
        exact: false 
      })
      
      toast.success('Préstamo actualizado exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al actualizar préstamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para eliminar un préstamo
export function useDeletePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => prestamoService.deletePrestamo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      toast.success('Préstamo eliminado exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al eliminar préstamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para obtener cuotas de un préstamo (tabla de amortización)
export function useCuotasPrestamo(prestamoId: number) {
  return useQuery({
    queryKey: [...prestamoKeys.detail(prestamoId), 'cuotas'],
    queryFn: () => prestamoService.getCuotasPrestamo(prestamoId),
    enabled: !!prestamoId,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para generar tabla de amortización
export function useGenerarAmortizacion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (prestamoId: number) => prestamoService.generarAmortizacion(prestamoId),
    onSuccess: (data, prestamoId) => {
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.detail(prestamoId), 'cuotas'] })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.detail(prestamoId) })
      toast.success('Tabla de amortización generada exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al generar tabla de amortización'
      toast.error(errorMessage)
    },
  })
}

// Hook para aplicar condiciones de aprobación
export function useAplicarCondicionesAprobacion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ prestamoId, condiciones }: { prestamoId: number; condiciones: any }) =>
      prestamoService.aplicarCondicionesAprobacion(prestamoId, condiciones),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: prestamoKeys.detail(variables.prestamoId) })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      toast.success('Condiciones aplicadas exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al aplicar condiciones'
      toast.error(errorMessage)
    },
  })
}

