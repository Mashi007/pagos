import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clienteService } from '../services/clienteService'
import { Cliente, ClienteForm, ClienteFilters } from '../types'
import toast from 'react-hot-toast'

// Constantes de configuraciiÃÂ³n
const DEFAULT_PER_PAGE = 20
const STALE_TIME_SHORT = 2 * 60 * 1000 // 2 minutos
const STALE_TIME_MEDIUM = 5 * 60 * 1000 // 5 minutos
const STALE_TIME_LONG = 10 * 60 * 1000 // 10 minutos

// Keys para React Query
export const clienteKeys = {
  all: ['clientes'] as const,
  lists: () => [...clienteKeys.all, 'list'] as const,
  list: (filters?: ClienteFilters) => [...clienteKeys.lists(), filters] as const,
  details: () => [...clienteKeys.all, 'detail'] as const,
  detail: (id: string) => [...clienteKeys.details(), id] as const,
  search: (query: string) => [...clienteKeys.all, 'search', query] as const,
  mora: () => [...clienteKeys.all, 'mora'] as const,
  byAsesor: (analistaId: string) => [...clienteKeys.all, 'analista', analistaId] as const,
}

// Hook para obtener lista de clientes
export function useClientes(
  filters?: ClienteFilters,
  page: number = 1,
  perPage: number = DEFAULT_PER_PAGE
) {
  return useQuery({
    queryKey: clienteKeys.list({ ...filters, per_page: perPage }),
    queryFn: () => clienteService.getClientes(filters, page, perPage),
    staleTime: STALE_TIME_SHORT, // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Reducido a 2 minutos para datos mÃÂ¡s frescos
    refetchOnMount: true, // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Refrescar cuando el componente se monta
    refetchOnWindowFocus: true, // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Refrescar cuando el usuario vuelve a la ventana
    refetchInterval: 3 * 60 * 1000, // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Auto-refresh cada 3 minutos
  })
}

// Hook para obtener un cliente especÃÂ­fico
export function useCliente(id: string) {
  return useQuery({
    queryKey: clienteKeys.detail(id),
    queryFn: () => clienteService.getCliente(id),
    enabled: !!id,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para bÃÂºsqueda de clientes
// Por defecto filtra solo clientes ACTIVOS (para formularios de prÃÂ©stamos)
// Para buscar todos los estados, pasar incluirTodosEstados: true
export function useSearchClientes(query: string, incluirTodosEstados: boolean = false) {
  return useQuery({
    queryKey: [...clienteKeys.search(query), incluirTodosEstados ? 'todos' : 'activos'],
    queryFn: () => clienteService.searchClientes(query, incluirTodosEstados),
    enabled: query.length >= 2,
    staleTime: STALE_TIME_SHORT,
  })
}

// Hook para clientes en mora
export function useClientesEnMora() {
  return useQuery({
    queryKey: clienteKeys.mora(),
    queryFn: () => clienteService.getClientesEnMora(),
    staleTime: STALE_TIME_MEDIUM,
  })
}

// Hook para clientes por analista
export function useClientesByAsesor(analistaId: string) {
  return useQuery({
    queryKey: clienteKeys.byAsesor(analistaId),
    queryFn: () => clienteService.getClientesByAnalista(analistaId),
    enabled: !!analistaId,
    staleTime: STALE_TIME_LONG,
  })
}

// Hook para crear cliente
export function useCreateCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ClienteForm) => clienteService.createCliente(data),
    onSuccess: (newCliente) => {
      // Invalidar y refetch queries relacionadas
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
      // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Invalidar tambiÃÂ©n bÃÂºsquedas de clientes (usadas en formularios de prÃÂ©stamos)
      queryClient.invalidateQueries({
        queryKey: ['clientes', 'search'],
        exact: false  // Invalida todas las bÃÂºsquedas: ['clientes', 'search', ...]
      })

      const nombreCompleto = newCliente.nombres?.trim() || 'Sin nombre'
      toast.success(`Cliente ${nombreCompleto} creado exitosamente`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear cliente')
    },
  })
}

// Hook para actualizar cliente
export function useUpdateCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ClienteForm> }) =>
      clienteService.updateCliente(id, data),
    onSuccess: (updatedCliente) => {
      // Actualizar cache especÃÂ­fico del cliente
      queryClient.setQueryData(
        clienteKeys.detail(String(updatedCliente.id)),
        updatedCliente
      )

      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      // ÃÂÃÂ¢ÃÂÃ¢ÂÂÃÂ¢Ã¢ÂÂ¬ÃÂ¦ Invalidar tambiÃÂ©n bÃÂºsquedas de clientes (usadas en formularios de prÃÂ©stamos)
      queryClient.invalidateQueries({
        queryKey: ['clientes', 'search'],
        exact: false  // Invalida todas las bÃÂºsquedas: ['clientes', 'search', ...]
      })

      const nombreCompleto = updatedCliente.nombres?.trim() || 'Sin nombre'
      toast.success(`Cliente ${nombreCompleto} actualizado`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar cliente')
    },
  })
}

// Hook para eliminar cliente
export function useDeleteCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => clienteService.deleteCliente(id),
    onSuccess: (_, deletedId) => {
      // Remover del cache
      queryClient.removeQueries({ queryKey: clienteKeys.detail(deletedId) })

      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })

      toast.success('Cliente eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar cliente')
    },
  })
}

// Hook para cambiar estado de cliente
export function useCambiarEstadoCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: Cliente['estado'] }) =>
      clienteService.cambiarEstado(id, estado),
    onSuccess: (updatedCliente) => {
      // Actualizar cache especÃÂ­fico
      queryClient.setQueryData(
        clienteKeys.detail(String(updatedCliente.id)),
        updatedCliente
      )

      // Invalidar listas y KPIs de clientes (Total, Activos, Inactivos, Finalizados)
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

      toast.success(`Estado del cliente cambiado a ${updatedCliente.estado}`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al cambiar estado')
    },
  })
}

// Hook para validar cÃÂ©dula
export function useValidateCedula() {
  return useMutation({
    mutationFn: (cedula: string) => clienteService.validateCedula(cedula),
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al validar cÃÂ©dula')
    },
  })
}

// Hook para importar clientes
export function useImportClientes() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => clienteService.importarClientes(file),
    onSuccess: (result) => {
      // Invalidar listas para mostrar nuevos datos
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })

      if (result.errors.length > 0) {
        toast.success(
          `ImportaciiÃÂ³n completada: ${result.success} exitosos, ${result.errors.length} errores`
        )
      } else {
        toast.success(`${result.success} clientes importados exitosamente`)
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al importar clientes')
    },
  })
}

