import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { prestamoService } from '../services/prestamoService'
import { Prestamo, PrestamoForm } from '../types'

// Constantes de configuraciÃ³n
const DEFAULT_PER_PAGE = 20
const STALE_TIME_SHORT = 2 * 60 * 1000 // 2 minutos
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos

// Keys para React Query
export const prestamoKeys = {
  all: ['prestamos'] as const,
  lists: () => [...prestamoKeys.all, 'list'] as const,
  list: (filters?: PrestamoFilters, page?: number, perPage?: number) => [...prestamoKeys.lists(), filters, page, perPage] as const,
  details: () => [...prestamoKeys.all, 'detail'] as const,
  detail: (id: number) => [...prestamoKeys.details(), id] as const,
  search: (query: string) => [...prestamoKeys.all, 'search', query] as const,
  byCedula: (cedula: string) => [...prestamoKeys.all, 'cedula', cedula] as const,
  auditoria: (prestamoId: number) => [...prestamoKeys.all, 'auditoria', prestamoId] as const,
}

// Tipo para filtros de prÃ©stamos
export interface PrestamoFilters {
  search?: string
  estado?: string
  cedula?: string
  cliente_id?: number
  analista?: string
  concesionario?: string
  modelo?: string
  fecha_inicio?: string
  fecha_fin?: string
  requiere_revision?: boolean
}

// Hook para obtener lista de prÃ©stamos
export function usePrestamos(
  filters?: PrestamoFilters,
  page: number = 1,
  perPage: number = DEFAULT_PER_PAGE
) {
  return useQuery({
    queryKey: prestamoKeys.list(filters, page, perPage),
    queryFn: () => prestamoService.getPrestamos(filters, page, perPage),
    staleTime: 0, // Siempre refetch cuando se invalida (mejor para actualizaciÃ³n inmediata de estado)
    refetchOnMount: true, // Refetch cuando el componente se monta
    refetchOnWindowFocus: true, // Refetch cuando se enfoca la ventana (mantiene datos actualizados)
  })
}

// Hook para obtener un prÃ©stamo especÃ­fico
export function usePrestamo(id: number) {
  return useQuery({
    queryKey: prestamoKeys.detail(id),
    queryFn: () => prestamoService.getPrestamo(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para bÃºsqueda de prÃ©stamos
export function useSearchPrestamos(query: string) {
  return useQuery({
    queryKey: prestamoKeys.search(query),
    queryFn: () => prestamoService.searchPrestamos(query),
    enabled: query.length > 0,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para obtener prÃ©stamos por cÃ©dula
export function usePrestamosByCedula(cedula: string) {
  return useQuery({
    queryKey: prestamoKeys.byCedula(cedula),
    queryFn: () => prestamoService.getPrestamosByCedula(cedula),
    enabled: cedula.length > 0,
    staleTime: STALE_TIME_MEDIUM,
  })
}

// Hook para obtener auditorÃ­a de un prÃ©stamo
export function useAuditoriaPrestamo(prestamoId: number) {
  return useQuery({
    queryKey: prestamoKeys.auditoria(prestamoId),
    queryFn: () => prestamoService.getAuditoria(prestamoId),
    enabled: !!prestamoId,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para crear un prÃ©stamo
export function useCreatePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PrestamoForm) => prestamoService.createPrestamo(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.all, 'kpis'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      toast.success('PrÃ©stamo creado exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al crear prÃ©stamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para actualizar un prÃ©stamo
export function useUpdatePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<PrestamoForm> }) =>
      prestamoService.updatePrestamo(id, data),
    onSuccess: async (data, variables) => {
      // Actualizar datos del cache directamente con la respuesta del servidor
      queryClient.setQueryData(prestamoKeys.detail(variables.id), data)

      // Si el estado cambiÃ³ a APROBADO, actualizar todas las listas
      if (data.estado === 'APROBADO') {
        // Remover cache stale para forzar refetch
        queryClient.removeQueries({ queryKey: prestamoKeys.lists() })
        queryClient.removeQueries({ queryKey: prestamoKeys.all })
      }

      // Invalidar todas las queries
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.all, 'kpis'], exact: false })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })

      // Forzar refetch inmediato ignorando staleTime
      await queryClient.refetchQueries({
        queryKey: prestamoKeys.all,
        exact: false,
        type: 'active'
      })

      toast.success('PrÃ©stamo actualizado exitosamente. El dashboard se ha actualizado.')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al actualizar prÃ©stamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para eliminar un prÃ©stamo
export function useDeletePrestamo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => prestamoService.deletePrestamo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.all, 'kpis'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      toast.success('PrÃ©stamo eliminado exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al eliminar prÃ©stamo'
      toast.error(errorMessage)
    },
  })
}

// Hook para obtener cuotas de un prÃ©stamo (tabla de amortizaciÃ³n)
export function useCuotasPrestamo(prestamoId: number) {
  return useQuery({
    queryKey: [...prestamoKeys.detail(prestamoId), 'cuotas'],
    queryFn: () => prestamoService.getCuotasPrestamo(prestamoId),
    enabled: !!prestamoId,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para generar tabla de amortizaciÃ³n
export function useGenerarAmortizacion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (prestamoId: number) => prestamoService.generarAmortizacion(prestamoId),
    onSuccess: (data, prestamoId) => {
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.detail(prestamoId), 'cuotas'] })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.detail(prestamoId) })
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })
      toast.success('Tabla de amortizaciÃ³n generada exitosamente')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al generar tabla de amortizaciÃ³n'
      toast.error(errorMessage)
    },
  })
}

// Hook para aplicar condiciones de aprobaciÃ³n
export function useAplicarCondicionesAprobacion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ prestamoId, condiciones }: { prestamoId: number; condiciones: any }) =>
      prestamoService.aplicarCondicionesAprobacion(prestamoId, condiciones),
    onSuccess: async (data, variables) => {
      // Actualizar datos del cache directamente con la respuesta del servidor
      queryClient.setQueryData(prestamoKeys.detail(variables.prestamoId), data)

      // Remover cache stale para forzar refetch (especialmente importante cuando estado = APROBADO)
      queryClient.removeQueries({ queryKey: prestamoKeys.lists() })
      queryClient.removeQueries({ queryKey: prestamoKeys.all })

      // Invalidar todas las queries
      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({ queryKey: [...prestamoKeys.all, 'kpis'], exact: false })
      queryClient.invalidateQueries({ queryKey: prestamoKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['kpis-principales-menu'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['dashboard-menu'], exact: false })

      // Forzar refetch inmediato ignorando staleTime
      await queryClient.refetchQueries({
        queryKey: prestamoKeys.all,
        exact: false,
        type: 'active'
      })

      toast.success('PrÃ©stamo aprobado exitosamente. La tabla de amortizaciÃ³n ha sido generada. El dashboard se ha actualizado.')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Error al aplicar condiciones'
      toast.error(errorMessage)
    },
  })
}

// Tipo para los KPIs de prÃ©stamos
export interface PrestamosKPIsData {
  totalFinanciamiento: number
  totalPrestamos: number
  promedioMonto: number
  totalCarteraVigente: number
  mes?: number
  anio?: number
}

// Hook para obtener KPIs de prÃ©stamos
export function usePrestamosKPIs(filters?: {
  analista?: string
  concesionario?: string
  modelo?: string
  fecha_inicio?: string
  fecha_fin?: string
}) {
  return useQuery({
    queryKey: [...prestamoKeys.all, 'kpis', filters],
    queryFn: () => prestamoService.getKPIs(filters),
    staleTime: 60 * 1000, // 1 min para actualizar KPIs
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    refetchInterval: 2 * 60 * 1000, // Refrescar cada 2 min
  })
}







