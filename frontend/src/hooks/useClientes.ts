import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clienteService } from '@/services/clienteService'
import { Cliente, ClienteForm, ClienteFilters } from '@/types'
import toast from 'react-hot-toast'

// Keys para React Query
export const clienteKeys = {
  all: ['clientes'] as const,
  lists: () => [...clienteKeys.all, 'list'] as const,
  list: (filters?: ClienteFilters) => [...clienteKeys.lists(), filters] as const,
  details: () => [...clienteKeys.all, 'detail'] as const,
  detail: (id: string) => [...clienteKeys.details(), id] as const,
  search: (query: string) => [...clienteKeys.all, 'search', query] as const,
  mora: () => [...clienteKeys.all, 'mora'] as const,
  byAsesor: (asesorId: string) => [...clienteKeys.all, 'asesor', asesorId] as const,
}

// Hook para obtener lista de clientes
export function useClientes(
  filters?: ClienteFilters,
  page: number = 1,
  perPage: number = 20
) {
  return useQuery({
    queryKey: clienteKeys.list({ ...filters, per_page: perPage }),
    queryFn: () => clienteService.getClientes(filters, page, perPage),
    staleTime: 5 * 60 * 1000, // 5 minutos
  })
}

// Hook para obtener un cliente específico
export function useCliente(id: string) {
  return useQuery({
    queryKey: clienteKeys.detail(id),
    queryFn: () => clienteService.getCliente(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutos
  })
}

// Hook para búsqueda de clientes
export function useSearchClientes(query: string) {
  return useQuery({
    queryKey: clienteKeys.search(query),
    queryFn: () => clienteService.searchClientes(query),
    enabled: query.length >= 2,
    staleTime: 2 * 60 * 1000, // 2 minutos
  })
}

// Hook para clientes en mora
export function useClientesEnMora() {
  return useQuery({
    queryKey: clienteKeys.mora(),
    queryFn: () => clienteService.getClientesEnMora(),
    staleTime: 5 * 60 * 1000, // 5 minutos
  })
}

// Hook para clientes por asesor
export function useClientesByAsesor(asesorId: string) {
  return useQuery({
    queryKey: clienteKeys.byAsesor(asesorId),
    queryFn: () => clienteService.getClientesByAsesor(asesorId),
    enabled: !!asesorId,
    staleTime: 10 * 60 * 1000, // 10 minutos
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
      
      toast.success(`Cliente ${newCliente.nombre} ${newCliente.apellido} creado exitosamente`)
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
      // Actualizar cache específico del cliente
      queryClient.setQueryData(
        clienteKeys.detail(updatedCliente.id),
        updatedCliente
      )
      
      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      
      toast.success(`Cliente ${updatedCliente.nombre} ${updatedCliente.apellido} actualizado`)
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
      // Actualizar cache específico
      queryClient.setQueryData(
        clienteKeys.detail(updatedCliente.id),
        updatedCliente
      )
      
      // Invalidar listas
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      
      toast.success(`Estado del cliente cambiado a ${updatedCliente.estado}`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al cambiar estado')
    },
  })
}

// Hook para asignar asesor
export function useAsignarAsesor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ clienteId, asesorId }: { clienteId: string; asesorId: string }) =>
      clienteService.asignarAsesor(clienteId, asesorId),
    onSuccess: (updatedCliente) => {
      // Actualizar cache específico
      queryClient.setQueryData(
        clienteKeys.detail(updatedCliente.id),
        updatedCliente
      )
      
      // Invalidar listas y clientes por asesor
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      queryClient.invalidateQueries({ queryKey: [...clienteKeys.all, 'asesor'] })
      
      toast.success('Asesor asignado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al asignar asesor')
    },
  })
}

// Hook para validar cédula
export function useValidateCedula() {
  return useMutation({
    mutationFn: (cedula: string) => clienteService.validateCedula(cedula),
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al validar cédula')
    },
  })
}

// Hook para exportar clientes
export function useExportClientes() {
  return useMutation({
    mutationFn: ({ filters, format }: { filters?: ClienteFilters; format?: 'excel' | 'pdf' }) =>
      clienteService.exportarClientes(filters, format),
    onSuccess: () => {
      toast.success('Exportación iniciada. El archivo se descargará automáticamente.')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al exportar clientes')
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
          `Importación completada: ${result.success} exitosos, ${result.errors.length} errores`
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
